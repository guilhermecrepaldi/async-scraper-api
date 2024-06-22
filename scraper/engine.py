"""
engine.py — Motor assincrono de scraping com aiohttp.

Usa semaforo para limitar conexoes simultaneas, retry com backoff exponencial,
proxy rotation e user-agent rotation.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from config import settings
from scraper.parser import ParserGenérico, RegraExtrair, obter_parser
from scraper.proxy import proxy_pool
from scraper.queue import ScrapQueue, Tarefa
from scraper.results import results_manager
from scraper.ua_rotation import ua_aleatorio

logger = logging.getLogger(__name__)


class ScrapEngine:
    """Motor de scraping assincrono.

    Usa um semaforo (max_conexoes_simultaneas) para nao sobrecarregar
    o servidor alvo nem a propria maquina. Implementa retry com backoff
    exponencial e rotacao de proxies/user-agents.
    """

    def __init__(self) -> None:
        self._sem = asyncio.Semaphore(settings.max_conexoes_simultaneas)
        self._stats: dict[str, int] = {
            "total_processadas": 0,
            "sucesso": 0,
            "erro": 0,
            "em_andamento": 0,
        }

    async def _fetch(
        self,
        url: str,
        timeout: int,
        proxy: str | None = None,
        tentativa: int = 1,
    ) -> str:
        """Faz uma requisicao GET com aiohttp e retorna o HTML.

        Inclui user-agent aleatorio, suporte a proxy e limitacao de tamanho.
        aiohttp as vezes fecha conexao, entao tem retry no nivel acima.
        """
        headers = {"User-Agent": ua_aleatorio()}
        # Esse timeout se aplica a cada tentativa individual
        client_timeout = aiohttp.ClientTimeout(
            total=timeout,
            connect=max(10, timeout // 3),
        )
        async with aiohttp.ClientSession(headers=headers, timeout=client_timeout) as sess:
            kwargs: dict[str, Any] = {}
            if proxy:
                # esse proxy ta lento, tentar outro se demorar
                kwargs["proxy"] = proxy

            async with sess.get(url, **kwargs) as resp:
                resp.raise_for_status()
                # Limita o tamanho da pagina para evitar abuse
                content = await resp.content.read(settings.max_tamanho_pagina)
                return content.decode("utf-8", errors="replace")

    async def _scrape_url(
        self,
        url_alvo: str,
        seletor_css: str | None = None,
        parser_custom: str | None = None,
        timeout: int = settings.timeout_padrao,
        proxy: str | None = None,
    ) -> dict[str, Any]:
        """Faz scraping de uma URL com retry e backoff exponencial."""
        ultimo_erro: str = ""

        for tentativa in range(1, settings.max_tentativas + 1):
            try:
                html = await self._fetch(url_alvo, timeout, proxy, tentativa)

                if parser_custom:
                    fn = obter_parser(parser_custom)
                    if fn:
                        return fn(html)

                # Usa o parser generico
                parser = ParserGenérico()
                if seletor_css:
                    parser.adicionar_regra(RegraExtrair(
                        nome="conteudo",
                        seletor=seletor_css,
                    ))
                parser.adicionar_regra(RegraExtrair(nome="titulo", seletor="title"))

                resultado = parser.parse(html)
                resultado["_url"] = url_alvo
                resultado["_status"] = "ok"
                return resultado

            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                ultimo_erro = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Tentativa %d/%d falhou para %s: %s",
                    tentativa, settings.max_tentativas, url_alvo, ultimo_erro,
                )

                if tentativa < settings.max_tentativas:
                    # Backoff exponencial: 1s, 2s, 4s...
                    backoff = settings.backoff_base * (2 ** (tentativa - 1))
                    logger.info("Backoff de %.1fs antes de tentar novamente", backoff)
                    await asyncio.sleep(backoff)

                    # Troca de proxy e user-agent na proxima tentativa
                    proxy = await proxy_pool.obter_proxy()

        return {
            "url": url_alvo,
            "_status": "erro",
            "_erro": ultimo_erro,
        }

    async def processar_tarefa(self, tarefa: Tarefa) -> Tarefa:
        """Processa uma tarefa completa de scraping."""
        logger.info(
            "Processando [%s] %s (seletor=%s, prioridade=%s)",
            tarefa.id, tarefa.url_alvo, tarefa.seletor_css,
            tarefa.prioridade.name,
        )

        async with self._sem:
            resultado = await self._scrape_url(
                url_alvo=tarefa.url_alvo,
                seletor_css=tarefa.seletor_css,
                parser_custom=tarefa.parser_custom,
                timeout=tarefa.timeout,
                proxy=tarefa.proxy,
            )

        tarefa.resultado = resultado

        if resultado.get("_status") == "ok":
            tarefa.status = "concluido"
            self._stats["sucesso"] += 1
        else:
            tarefa.erro = resultado.get("_erro", "Erro desconhecido")
            self._stats["erro"] += 1

        self._stats["total_processadas"] += 1
        self._stats["em_andamento"] = max(0, self._stats["em_andamento"] - 1)

        # Salva resultado em JSON
        await results_manager.salvar_json(tarefa.id, resultado)

        return tarefa

    async def consume_forever(self, queue: ScrapQueue) -> None:
        """Loop principal que consome tarefas da fila para sempre."""
        logger.info("Worker iniciado, aguardando tarefas...")
        while True:
            try:
                tarefa = await queue.obter()
                self._stats["em_andamento"] += 1

                tarefa = await self.processar_tarefa(tarefa)

                if tarefa.status == "concluido":
                    await queue.concluir(tarefa)
                else:
                    # aiohttp as vezes fecha conexao, entao tem retry na fila
                    await queue.repor(tarefa)

            except asyncio.CancelledError:
                logger.info("Worker cancelado.")
                raise
            except Exception as exc:
                logger.exception("Erro inesperado no worker: %s", exc)
                await asyncio.sleep(2)

    async def criar_tarefa(
        self,
        url_alvo: str,
        seletor_css: str = "",
        prioridade: str = "normal",
        timeout: int = settings.timeout_padrao,
        max_tentativas: int = settings.max_tentativas,
        parser_custom: str | None = None,
    ) -> Tarefa:
        """Cria uma tarefa de scraping e joga na fila."""
        from scraper.queue import Prioridade

        prioridade_map = {
            "alta": Prioridade.ALTA,
            "normal": Prioridade.NORMAL,
            "baixa": Prioridade.BAIXA,
        }

        tarefa = Tarefa(
            url_alvo=url_alvo,
            seletor_css=seletor_css,
            prioridade=prioridade_map.get(prioridade, Prioridade.NORMAL),
            timeout=timeout,
            max_tentativas=max_tentativas,
            parser_custom=parser_custom,
        )

        from scraper.queue import scrap_queue

        await scrap_queue.enfileirar(tarefa)
        logger.info("Tarefa %s enfileirada para %s", tarefa.id, url_alvo)
        return tarefa

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

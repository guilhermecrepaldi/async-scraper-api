"""
proxy.py — Rotacao de proxies com teste de conectividade.
"""
from __future__ import annotations

import asyncio
import logging
import random

import aiohttp

from config import settings

logger = logging.getLogger(__name__)


class ProxyPool:
    """Pool de proxies com teste de funcionamento e rotacao.

    Mantem uma lista de proxies que passaram no teste de conectividade.
    Se todos falharem, faz scraping direto (sem proxy).
    """

    def __init__(self) -> None:
        self._proxies_validos: list[str] = list(settings.proxies_padrao)
        self._todos: list[str] = list(settings.proxies_padrao)

    async def testar_proxy(self, proxy_url: str) -> bool:
        """Testa se um proxy responde dentro do timeout configurado."""
        # esse proxy ta lento, tentar outro se demorar
        try:
            timeout = aiohttp.ClientTimeout(total=settings.proxy_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as sess:
                async with sess.get(
                    "http://httpbin.org/ip",
                    proxy=proxy_url,
                ) as resp:
                    if resp.status == 200:
                        logger.info("Proxy OK: %s", proxy_url)
                        return True
                    logger.warning("Proxy %s retornou status %s", proxy_url, resp.status)
                    return False
        except (asyncio.TimeoutError, aiohttp.ClientError, OSError) as exc:
            logger.warning("Proxy %s falhou: %s", proxy_url, exc)
            return False

    async def testar_todos(self) -> None:
        """Testa todos os proxies da lista e mantem so os que funcionam."""
        resultados = await asyncio.gather(
            *(self.testar_proxy(p) for p in self._todos),
            return_exceptions=True,
        )
        self._proxies_validos = [
            p for p, ok in zip(self._todos, resultados) if ok is True
        ]
        logger.info(
            "Proxies validos: %d/%d", len(self._proxies_validos), len(self._todos)
        )

    async def obter_proxy(self) -> str | None:
        """Retorna um proxy aleatorio valido, ou None se nao houver nenhum."""
        if not self._proxies_validos:
            # Tenta testar de novo — as vezes um que caiu ja voltou
            logger.info("Nenhum proxy valido no momento, testando todos...")
            await self.testar_todos()
        if self._proxies_validos:
            return random.choice(self._proxies_validos)
        return None

    def adicionar_proxy(self, proxy_url: str) -> None:
        """Adiciona um novo proxy ao pool (sem testar)."""
        if proxy_url not in self._todos:
            self._todos.append(proxy_url)
            self._proxies_validos.append(proxy_url)

    @property
    def proxies(self) -> list[str]:
        """Lista de proxies validos atualmente."""
        return list(self._proxies_validos)


# Singleton do pool
proxy_pool = ProxyPool()

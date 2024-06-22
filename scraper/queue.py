"""
queue.py — Fila de tarefas com prioridade (alta, normal, baixa).
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Prioridade(IntEnum):
    """Valores numericos: menor numero = maior prioridade."""
    ALTA = 0
    NORMAL = 1
    BAIXA = 2


@dataclass(order=True)
class Tarefa:
    """Uma unidade de trabalho na fila de scraping.

    A comparacao eh feita por (prioridade, timestamp_criacao) para que
    tarefas de mesma prioridade sejam processadas em ordem FIFO.
    """
    prioridade: Prioridade = Prioridade.NORMAL
    timestamp_criacao: float = field(default_factory=time.time)

    # Esses campos nao entram na comparacao
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12], compare=False)
    url_alvo: str = field(default="", compare=False)
    seletor_css: str = field(default="", compare=False)
    timeout: int = field(default=30, compare=False)
    tentativas: int = field(default=0, compare=False)
    max_tentativas: int = field(default=3, compare=False)
    parser_custom: str | None = field(default=None, compare=False)
    proxy: str | None = field(default=None, compare=False)

    # Status ao vivo
    status: str = field(default="pendente", compare=False)  # pendente | processando | concluido | erro
    resultado: dict[str, Any] | None = field(default=None, compare=False)
    erro: str | None = field(default=None, compare=False)
    tempo_restante: float = field(default=0.0, compare=False)

    def para_dict(self) -> dict[str, Any]:
        """Serializa a tarefa para JSON (sem campos internos)."""
        return {
            "id": self.id,
            "url_alvo": self.url_alvo,
            "seletor_css": self.seletor_css,
            "prioridade": self.prioridade.name.lower(),
            "status": self.status,
            "timeout": self.timeout,
            "tentativas": self.tentativas,
            "max_tentativas": self.max_tentativas,
            "parser_custom": self.parser_custom,
            "proxy": self.proxy,
            "resultado": self.resultado,
            "erro": self.erro,
            "timestamp_criacao": self.timestamp_criacao,
        }


class ScrapQueue:
    """Fila de scraping baseada em asyncio.PriorityQueue.

    Aceita tarefas com prioridade ALTA, NORMAL ou BAIXA.
    Mantem um registro de todas as tarefas (inclusive concluidas) em memoria.
    """

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._tarefas: dict[str, Tarefa] = {}  # id -> Tarefa
        self._lock = asyncio.Lock()
        self._concluidas: set[str] = set()

    async def enfileirar(self, tarefa: Tarefa) -> None:
        """Adiciona uma tarefa na fila com sua prioridade."""
        async with self._lock:
            self._tarefas[tarefa.id] = tarefa
        await self._queue.put(tarefa)

    async def obter(self) -> Tarefa:
        """Retira a proxima tarefa da fila (bloqueante)."""
        tarefa = await self._queue.get()
        tarefa.status = "processando"
        async with self._lock:
            self._tarefas[tarefa.id] = tarefa
        return tarefa

    async def concluir(self, tarefa: Tarefa) -> None:
        """Marca uma tarefa como concluida e sinaliza a queue."""
        tarefa.status = "concluido" if not tarefa.erro else "erro"
        async with self._lock:
            self._tarefas[tarefa.id] = tarefa
            self._concluidas.add(tarefa.id)
        self._queue.task_done()

    async def repor(self, tarefa: Tarefa) -> None:
        """Re-enfileira uma tarefa que falhou, se ainda tem tentativas."""
        tarefa.tentativas += 1
        if tarefa.tentativas < tarefa.max_tentativas:
            tarefa.status = "pendente"
            async with self._lock:
                self._tarefas[tarefa.id] = tarefa
            await self._queue.put(tarefa)
        else:
            tarefa.status = "erro"
            tarefa.erro = tarefa.erro or "Maximo de tentativas atingido"
            async with self._lock:
                self._tarefas[tarefa.id] = tarefa
                self._concluidas.add(tarefa.id)
            self._queue.task_done()

    def obter_tarefa(self, tarefa_id: str) -> Tarefa | None:
        """Retorna uma tarefa pelo ID."""
        return self._tarefas.get(tarefa_id)

    def listar_tarefas(self, status: str | None = None) -> list[dict[str, Any]]:
        """Lista todas as tarefas, opcionalmente filtradas por status."""
        tarefas = self._tarefas.values()
        if status:
            tarefas = [t for t in tarefas if t.status == status]
        return [t.para_dict() for t in sorted(
            tarefas, key=lambda t: t.timestamp_criacao, reverse=True
        )]

    @property
    def tamanho(self) -> int:
        return self._queue.qsize()

    async def limpar_concluidas(self) -> int:
        """Remove tarefas concluidas/erro do dicionario. Retorna qtd removida."""
        async with self._lock:
            ids = list(self._concluidas)
            for tid in ids:
                self._tarefas.pop(tid, None)
            self._concluidas.clear()
        return len(ids)


# Singleton da fila
scrap_queue = ScrapQueue()

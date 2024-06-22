"""
results.py — Gerenciamento de resultados com exportacao JSON/CSV.
"""
from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles

from config import settings

logger = logging.getLogger(__name__)


class ResultsManager:
    """Salva e recupera resultados de scraping em JSON e CSV."""

    def __init__(self, diretorio: str = "") -> None:
        self._dir = diretorio or settings.results_dir
        os.makedirs(self._dir, exist_ok=True)

    def _caminho_json(self, tarefa_id: str) -> str:
        return os.path.join(self._dir, f"{tarefa_id}.json")

    def _caminho_csv(self, tarefa_id: str) -> str:
        return os.path.join(self._dir, f"{tarefa_id}.csv")

    async def salvar_json(self, tarefa_id: str, dados: dict[str, Any]) -> str:
        """Salva o resultado como JSON e retorna o caminho do arquivo."""
        caminho = self._caminho_json(tarefa_id)
        payload = {
            "tarefa_id": tarefa_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dados": dados,
        }
        async with aiofiles.open(caminho, "w", encoding="utf-8") as f:
            await f.write(json.dumps(payload, indent=2, ensure_ascii=False))
        logger.info("Resultado salvo: %s", caminho)
        return caminho

    async def salvar_csv(self, tarefa_id: str, dados: list[dict[str, Any]]) -> str:
        """Salva uma lista de dicionarios como CSV."""
        if not dados:
            logger.warning("Nenhum dado para salvar em CSV para %s", tarefa_id)
            return ""
        caminho = self._caminho_csv(tarefa_id)
        colunas = list(dados[0].keys())
        async with aiofiles.open(caminho, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=colunas)
            writer.writeheader()
            writer.writerows(dados)
        logger.info("CSV salvo: %s", caminho)
        return caminho

    async def ler_json(self, tarefa_id: str) -> dict[str, Any] | None:
        """Le um resultado JSON salvo anteriormente."""
        caminho = self._caminho_json(tarefa_id)
        try:
            async with aiofiles.open(caminho, "r", encoding="utf-8") as f:
                conteudo = await f.read()
            return json.loads(conteudo)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning("Erro ao ler resultado %s: %s", tarefa_id, exc)
            return None

    def listar_resultados(self) -> list[dict[str, Any]]:
        """Lista todos os arquivos de resultado no diretorio."""
        resultados: list[dict[str, Any]] = []
        for fname in os.listdir(self._dir):
            if fname.endswith(".json"):
                caminho = os.path.join(self._dir, fname)
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                    resultados.append({
                        "arquivo": fname,
                        "tarefa_id": dados.get("tarefa_id", ""),
                        "timestamp": dados.get("timestamp", ""),
                    })
                except (json.JSONDecodeError, OSError):
                    continue
        # Ordena do mais recente para o mais antigo
        resultados.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return resultados


# Singleton
results_manager = ResultsManager()

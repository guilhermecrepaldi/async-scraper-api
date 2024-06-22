"""
Configuracoes centralizadas do async-scraper-api.
Carrega de variaveis de ambiente ou usa defaults sensatos.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Settings:
    # --- Servidor ---
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # --- Scraping ---
    max_conexoes_simultaneas: int = int(os.getenv("MAX_CONEXOES", "5"))
    timeout_padrao: int = int(os.getenv("TIMEOUT_PADRAO", "30"))  # segundos
    max_tentativas: int = int(os.getenv("MAX_TENTATIVAS", "3"))
    backoff_base: float = float(os.getenv("BACKOFF_BASE", "1.0"))  # segundos

    # --- Proxy ---
    proxy_timeout: int = int(os.getenv("PROXY_TIMEOUT", "5"))
    proxies_padrao: list[str] = field(default_factory=lambda: [
        # Lista fixa de proxies publicos para demonstracao.
        # Em producao, usar BrightData / ScrapingBee / etc.
    ])

    # --- User-Agents ---
    ua_pool: list[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 "
        "Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 "
        "Firefox/119.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    ])

    # --- Filas ---
    prioridades: tuple[str, ...] = ("alta", "normal", "baixa")

    # --- Caminhos ---
    results_dir: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "results"
    )

    # --- Limites ---
    max_urls_por_tarefa: int = 50
    max_tamanho_pagina: int = 5 * 1024 * 1024  # 5 MB


settings = Settings()

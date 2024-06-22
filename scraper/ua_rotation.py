"""
ua_rotation.py — Pool de user-agents com rotacao aleatoria.
"""
from __future__ import annotations

import random

from config import settings


def ua_aleatorio() -> str:
    """Retorna um User-Agent aleatorio do pool configurado."""
    return random.choice(settings.ua_pool)


def ua_por_navegador(navegador: str = "chrome") -> str:
    """Retorna User-Agent aproximado para um navegador especifico."""
    pool = settings.ua_pool
    for ua in pool:
        if navegador.lower() in ua.lower():
            return ua
    return ua_aleatorio()

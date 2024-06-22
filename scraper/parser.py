"""
parser.py — Parsers genericos e customizaveis usando BeautifulSoup.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from bs4 import BeautifulSoup, Tag


@dataclass
class RegraExtrair:
    """Define uma regra de extracao de dados do HTML.

    Atributos:
        nome: Nome amigavel do campo (ex: 'titulo').
        seletor: Seletor CSS (ex: 'h1.article-title').
        atributo: Se 'text' (padrao) pega o texto interno, senao pega o atributo (ex: 'href').
        regex: Opcional — extrai parte do texto via regex.
        default: Valor padrao se o seletor nao encontrar nada.
    """
    nome: str
    seletor: str
    atributo: str = "text"
    regex: str | None = None
    default: Any = ""


class ParserGenérico:
    """Parser generico que aplica multiplas regras de extracao."""

    def __init__(self, regras: list[RegraExtrair] | None = None) -> None:
        self.regras: list[RegraExtrair] = regras or []

    def adicionar_regra(self, regra: RegraExtrair) -> None:
        self.regras.append(regra)

    def parse(self, html: str) -> dict[str, Any]:
        """Aplica todas as regras ao HTML e retorna um dict com os valores."""
        soup = BeautifulSoup(html, "lxml")
        resultado: dict[str, Any] = {}

        for regra in self.regras:
            elementos = soup.select(regra.seletor)
            if not elementos:
                resultado[regra.nome] = regra.default
                continue

            valores = []
            for el in elementos[:5]:  # limita a 5 ocorrencias por regra
                if isinstance(el, Tag):
                    if regra.atributo == "text":
                        valor = el.get_text(strip=True)
                    else:
                        valor = el.get(regra.atributo, regra.default)
                else:
                    valor = str(el)

                # Aplica regex se definido
                if regra.regex and isinstance(valor, str):
                    match = re.search(regra.regex, valor)
                    valor = match.group(1) if match else valor

                valores.append(valor)

            resultado[regra.nome] = valores[0] if len(valores) == 1 else valores

        return resultado

    @staticmethod
    def parse_titulo(html: str) -> str | None:
        """Extrai o titulo da pagina (<title>)."""
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("title")
        return tag.get_text(strip=True) if isinstance(tag, Tag) else None

    @staticmethod
    def parse_links(html: str, url_base: str = "") -> list[dict[str, str]]:
        """Extrai todos os links <a href='...'> da pagina."""
        soup = BeautifulSoup(html, "lxml")
        links: list[dict[str, str]] = []
        from urllib.parse import urljoin

        for tag in soup.find_all("a", href=True):
            if isinstance(tag, Tag):
                href = tag.get("href", "")
                texto = tag.get_text(strip=True)
                if href and not href.startswith(("#", "javascript:", "mailto:")):
                    url_abs = urljoin(url_base, href)
                    links.append({"url": url_abs, "texto": texto})
        return links


_PARSERS_CUSTOM: dict[str, Callable[[str], dict[str, Any]]] = {}


def registrar_parser_custom(nome: str, funcao: Callable[[str], dict[str, Any]]) -> None:
    """Registra uma funcao de parser customizada para usar por nome."""
    _PARSERS_CUSTOM[nome] = funcao


def obter_parser(nome: str) -> Callable[[str], dict[str, Any]] | None:
    """Retorna um parser custom registrado, ou None se nao existir."""
    return _PARSERS_CUSTOM.get(nome)

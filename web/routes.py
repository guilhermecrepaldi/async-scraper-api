"""
routes.py — Rotas FastAPI: API REST + Dashboard web.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config import settings
from scraper.engine import ScrapEngine
from scraper.queue import scrap_queue
from scraper.results import results_manager

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


def _get_engine(request: Request) -> ScrapEngine:
    engine: ScrapEngine | None = request.app.state.engine
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine nao inicializado")
    return engine


# ──────────────────────────────── API REST ────────────────────────────────


@router.post("/api/scrape")
async def api_criar_scrape(
    request: Request,
    body: dict[str, Any],
) -> JSONResponse:
    """Cria uma nova tarefa de scraping.

    Body esperado:
    {
        "url_alvo": "https://exemplo.com",
        "seletor_css": "h1.titulo",        // opcional
        "prioridade": "normal",             // alta | normal | baixa
        "timeout": 30,                      // opcional
        "max_tentativas": 3,                // opcional
        "parser_custom": null               // opcional
    }
    """
    engine = _get_engine(request)
    url_alvo = body.get("url_alvo", "").strip()
    if not url_alvo:
        raise HTTPException(status_code=422, detail="url_alvo eh obrigatorio")

    tarefa = await engine.criar_tarefa(
        url_alvo=url_alvo,
        seletor_css=body.get("seletor_css", ""),
        prioridade=body.get("prioridade", "normal"),
        timeout=body.get("timeout", settings.timeout_padrao),
        max_tentativas=body.get("max_tentativas", settings.max_tentativas),
        parser_custom=body.get("parser_custom"),
    )
    return JSONResponse(tarefa.para_dict(), status_code=201)


@router.get("/api/tasks")
async def api_listar_tarefas(
    status: str | None = Query(None, description="Filtrar por status"),
) -> JSONResponse:
    """Lista todas as tarefas (opcionalmente filtradas por status)."""
    tarefas = scrap_queue.listar_tarefas(status=status)
    return JSONResponse({
        "total": len(tarefas),
        "tarefas": tarefas,
    })


@router.get("/api/tasks/{task_id}")
async def api_obter_tarefa(task_id: str) -> JSONResponse:
    """Retorna detalhes de uma tarefa especifica."""
    tarefa = scrap_queue.obter_tarefa(task_id)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada")
    return JSONResponse(tarefa.para_dict())


@router.get("/api/results")
async def api_listar_resultados() -> JSONResponse:
    """Lista todos os resultados salvos."""
    resultados = results_manager.listar_resultados()
    return JSONResponse({
        "total": len(resultados),
        "resultados": resultados,
    })


@router.get("/api/results/{task_id}")
async def api_obter_resultado(task_id: str) -> JSONResponse:
    """Retorna o resultado salvo de uma tarefa."""
    resultado = await results_manager.ler_json(task_id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Resultado nao encontrado")
    return JSONResponse(resultado)


@router.get("/api/stats")
async def api_stats(request: Request) -> JSONResponse:
    """Retorna estatisticas do motor de scraping."""
    engine = _get_engine(request)
    stats = engine.stats
    stats["fila_tamanho"] = scrap_queue.tamanho
    stats["total_tarefas"] = len(scrap_queue.listar_tarefas())
    return JSONResponse(stats)


# ──────────────────────────────── DASHBOARD ────────────────────────────────


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request) -> HTMLResponse:
    """Pagina principal do dashboard."""
    engine = _get_engine(request)
    stats = engine.stats
    stats["fila_tamanho"] = scrap_queue.tamanho
    tarefas = scrap_queue.listar_tarefas()[:20]  # ultimas 20

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "tarefas": tarefas,
        },
    )


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail_page(request: Request, task_id: str) -> HTMLResponse:
    """Pagina de detalhe de uma tarefa."""
    tarefa = scrap_queue.obter_tarefa(task_id)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada")

    resultado = await results_manager.ler_json(task_id)
    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "tarefa": tarefa.para_dict(),
            "resultado": resultado,
        },
    )


# Redirect / -> /dashboard
@router.get("/", response_class=HTMLResponse)
async def root_redirect() -> HTMLResponse:
    return HTMLResponse(
        '<meta http-equiv="refresh" content="0;url=/dashboard">'
        '<a href="/dashboard">Ir para Dashboard</a>',
    )

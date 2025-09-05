"""
async-scraper-api — Ponto de entrada FastAPI.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings
from web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicia e derruba recursos globais."""
    # --- startup ---
    from scraper.queue import scrap_queue
    from scraper.engine import ScrapEngine

    # Garante que o diretorio de resultados existe
    import aiofiles.os
    await aiofiles.os.makedirs(settings.results_dir, exist_ok=True)

    # Instancia o motor e poe na app.state
    engine = ScrapEngine()
    app.state.engine = engine

    # Worker roda em background processando a fila
    worker_task = asyncio.create_task(engine.consume_forever(scrap_queue))
    app.state.worker_task = worker_task

    yield

    # --- shutdown ---
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="async-scraper-api",
    description="API assincrona para web scraping com fila de tarefas, "
                "proxy rotation e resultados em JSON.",
    version="1.0.0",
    lifespan=lifespan,
)

# Monta arquivos estaticos
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Rotas web (dashboard + API REST)
app.include_router(web_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

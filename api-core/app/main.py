from contextlib import asynccontextmanager
import os

import whisper
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.clients.qdrant_client import qdrant_chunks
from app.config import settings
from app.routers import approvals, browser_proxy, chat, tasks
from app.routers.voice import api_router as voice_api_router, ui_router as voice_ui_router
from app.store import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar pool de conexiones PostgreSQL
    await store.initialize(settings.database_url)
    # Conectar cliente Qdrant
    qdrant_chunks.initialize()
    # Cargar modelo Whisper una sola vez al arrancar
    from fastapi.concurrency import run_in_threadpool
    app.state.whisper_model = await run_in_threadpool(
        whisper.load_model, settings.whisper_model
    )
    yield
    await store.close()


app = FastAPI(
    title="Rachael – api-core",
    description="Orquestador central: planificador/ejecutor de Rachael.",
    version="0.1.0",
    lifespan=lifespan,
)

# UI — GET / sirve index.html (sin prefijo)
app.include_router(voice_ui_router)

# API de voz — POST /v1/voice/transcribe
app.include_router(voice_api_router, prefix="/v1", tags=["voice"])

# Resto de la API
app.include_router(chat.router, prefix="/v1", tags=["chat"])
app.include_router(tasks.router, prefix="/v1", tags=["tasks"])
app.include_router(approvals.router, prefix="/v1", tags=["approvals"])
app.include_router(browser_proxy.router, prefix="/internal", tags=["internal"])


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


# Archivos estáticos (CSS/JS futuros) montados bajo /static
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

"""
Interfaz de voz — Misión 6.

Rutas:
  GET  /            → sirve la UI HTML (ui_router, sin prefijo)
  POST /v1/voice/transcribe → transcribe audio con Whisper (api_router, prefijo /v1)
"""

from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse

# ---------------------------------------------------------------------------
# UI router — montado en / (sin prefijo en main.py)
# ---------------------------------------------------------------------------
ui_router = APIRouter()

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@ui_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index() -> str:
    html_path = os.path.join(_STATIC_DIR, "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# API router — montado en /v1 (prefijo /v1 en main.py)
# ---------------------------------------------------------------------------
api_router = APIRouter()


@api_router.post("/voice/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile = File(..., description="Archivo de audio (webm, wav, mp3, ogg…)"),
) -> dict:
    """Recibe un blob de audio y devuelve el texto transcrito con Whisper."""
    model = request.app.state.whisper_model

    # Guardar en fichero temporal (Whisper necesita una ruta de fichero)
    ext = os.path.splitext(file.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # faster-whisper devuelve (segments, info) — concatenamos los segmentos
        def _transcribe(path: str) -> str:
            segments, _ = model.transcribe(path, beam_size=5)
            return " ".join(s.text for s in segments).strip()

        text = await run_in_threadpool(_transcribe, tmp_path)
        return {"text": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al transcribir: {exc}") from exc
    finally:
        os.unlink(tmp_path)

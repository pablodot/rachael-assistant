"""
POST /internal/browser/proxy

Proxy interno opcional: reenvía acciones al browser-agent directamente.
Útil para pruebas e integración directa sin pasar por el planner.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import base64

from app.clients.browser_client import browser_client

router = APIRouter()


class BrowserProxyRequest(BaseModel):
    action: str  # ej. "open", "click", "type"
    args: dict[str, Any] = {}


@router.post("/browser/proxy")
async def browser_proxy(request: BrowserProxyRequest) -> dict[str, Any]:
    try:
        result = await browser_client.dispatch(request.action, request.args)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error en browser-agent: {exc}")

    return {"action": request.action, "result": result}


@router.get("/browser/screenshot")
async def browser_screenshot() -> Response:
    """Devuelve la screenshot actual del navegador como imagen PNG."""
    try:
        result = await browser_client.screenshot()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error obteniendo screenshot: {exc}")

    if "image_base64" in result:
        img_bytes = base64.b64decode(result["image_base64"])
        return Response(content=img_bytes, media_type="image/png")
    raise HTTPException(status_code=502, detail="El browser-agent no devolvió imagen")

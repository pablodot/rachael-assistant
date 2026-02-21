"""
POST /internal/browser/proxy

Proxy interno opcional: reenvía acciones al browser-agent directamente.
Útil para pruebas e integración directa sin pasar por el planner.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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

"""
tasks.py — Handlers de tareas para el worker de Rachael.

Tipos de tarea definidos en SPEC.md §11:
  - health_check    : ping periódico a api-core, browser-agent y llm-runtime
  - daily_briefing  : POST /v1/chat a api-core con el mensaje de buenos días
  - browser_task    : encola una tarea de navegador vía api-core
  - summarize_memory: solicita resumen/compactación de memoria a api-core

Todas las funciones son async porque arq es async-first.
El primer argumento `ctx` es el contexto de arq (contiene el pool de Redis).
"""

import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# health_check
# ──────────────────────────────────────────────────────────────────────────────

async def health_check(ctx: dict) -> dict:
    """
    Ping a los tres servicios principales y loguea su estado.
    Retorna un dict con el resultado por servicio.
    """
    endpoints = {
        "api-core":      f"{settings.api_core_url}/health",
        "browser-agent": f"{settings.browser_agent_url}/health",
        "llm-runtime":   f"{settings.llm_runtime_url}/api/tags",  # Ollama health
    }

    results: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in endpoints.items():
            try:
                resp = await client.get(url)
                if resp.status_code < 300:
                    logger.info("[health_check] %s: OK (%d)", name, resp.status_code)
                    results[name] = "ok"
                else:
                    logger.warning("[health_check] %s: DEGRADED (%d)", name, resp.status_code)
                    results[name] = f"degraded:{resp.status_code}"
            except httpx.ConnectError:
                logger.error("[health_check] %s: DOWN (connection refused)", name)
                results[name] = "down"
            except Exception as exc:
                logger.error("[health_check] %s: ERROR — %s", name, exc)
                results[name] = f"error:{exc}"

    return results


# ──────────────────────────────────────────────────────────────────────────────
# daily_briefing
# ──────────────────────────────────────────────────────────────────────────────

async def daily_briefing(ctx: dict) -> dict:
    """
    Envía un mensaje de buenos días a api-core /v1/chat.
    api-core lo procesa con el LLM y actualiza el estado interno.
    """
    payload = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Buenos días, Rachael. "
                    "Dame un briefing del día: tareas pendientes, recordatorios "
                    "y resumen del estado del sistema."
                ),
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.api_core_url}/v1/chat",
                json=payload,
            )
            logger.info("[daily_briefing] Enviado. Status: %d", resp.status_code)
            return {"status": resp.status_code, "ok": resp.status_code < 300}
        except Exception as exc:
            logger.error("[daily_briefing] Fallo: %s", exc)
            return {"status": None, "ok": False, "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# browser_task
# ──────────────────────────────────────────────────────────────────────────────

async def browser_task(ctx: dict, url: str, action: str = "screenshot", **kwargs) -> dict:
    """
    Encola una tarea de navegador vía api-core /v1/tasks/enqueue.

    Args:
        url:    URL destino de la tarea.
        action: Acción a realizar (screenshot, navigate, extract, …).
        **kwargs: Argumentos adicionales para el browser-agent.
    """
    payload = {
        "type": "browser_task",
        "payload": {"url": url, "action": action, **kwargs},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{settings.api_core_url}/v1/tasks/enqueue",
                json=payload,
            )
            logger.info("[browser_task] Encolado. Status: %d", resp.status_code)
            return resp.json()
        except Exception as exc:
            logger.error("[browser_task] Fallo: %s", exc)
            return {"error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# summarize_memory
# ──────────────────────────────────────────────────────────────────────────────

async def summarize_memory(ctx: dict, session_id: str | None = None) -> dict:
    """
    Solicita a api-core que resuma/compacte la memoria de una sesión.

    Args:
        session_id: ID de sesión a resumir. Si es None, api-core decide qué resumir.
    """
    payload = {}
    if session_id:
        payload["session_id"] = session_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.api_core_url}/v1/memory/summarize",
                json=payload,
            )
            logger.info("[summarize_memory] Completado. Status: %d", resp.status_code)
            return {"status": resp.status_code, "ok": resp.status_code < 300}
        except Exception as exc:
            logger.error("[summarize_memory] Fallo: %s", exc)
            return {"status": None, "ok": False, "error": str(exc)}

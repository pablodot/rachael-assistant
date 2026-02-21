"""
Rachael – browser-agent service.

FastAPI server exposing the browser automation API defined in SPEC.md §12.
Runs on the Linux host (not in Docker) so Playwright can control a real Chromium.

Endpoints:
    POST  /v1/browser/open
    POST  /v1/browser/navigate
    GET   /v1/browser/snapshot
    POST  /v1/browser/click
    POST  /v1/browser/type
    POST  /v1/browser/extract
    GET   /v1/browser/screenshot
    POST  /v1/browser/close
    GET   /health
    GET   /v1/browser/status
"""
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from browser import browser_manager
from config import settings
from models import (
    BrowserStatus,
    ClickRequest,
    ExtractRequest,
    ExtractResponse,
    NavigateRequest,
    OkResponse,
    OpenRequest,
    ScreenshotResponse,
    SnapshotResponse,
    StopPointError as StopPointModel,
    TypeRequest,
)
from security import SecurityError, StopPointError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("browser-agent")


# ── App lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Playwright engine…")
    await browser_manager.init()
    logger.info("browser-agent ready on %s:%s", settings.host, settings.port)
    yield
    logger.info("Shutting down — closing browser…")
    await browser_manager.shutdown()
    logger.info("Goodbye.")


app = FastAPI(
    title="Rachael browser-agent",
    description="Playwright-based browser automation API for the Rachael autonomous assistant.",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _security_response(exc: SecurityError) -> JSONResponse:
    """Convert a SecurityError into the appropriate HTTP response."""
    if isinstance(exc, StopPointError):
        body = StopPointModel(
            message=str(exc),
            element_info=exc.element_info,
        )
        return JSONResponse(status_code=status.HTTP_423_LOCKED, content=body.model_dump())

    if exc.kind == "domain_blocked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    if exc.kind == "max_steps_exceeded":
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


# ── Health / status ────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}


@app.get("/v1/browser/status", response_model=BrowserStatus, tags=["browser"])
async def browser_status():
    """Return current browser state."""
    return BrowserStatus(
        is_open=browser_manager.is_open,
        url=browser_manager.current_url,
        task_id=browser_manager._current_task_id,
        step_count=browser_manager.step_count,
    )


# ── Browser endpoints ──────────────────────────────────────────────────────────

@app.post("/v1/browser/open", response_model=OkResponse, tags=["browser"])
async def open_browser(req: OpenRequest):
    """
    Open the browser and navigate to the given URL.
    Creates a persistent Chromium context using the dedicated profile.
    """
    try:
        url = await browser_manager.open(req.url, task_id=req.task_id, force=req.force)
    except StopPointError as exc:
        return _security_response(exc)
    except SecurityError as exc:
        return _security_response(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    logger.info("open → %s (task=%s)", url, req.task_id)
    return OkResponse(message="Browser opened", url=url, task_id=req.task_id)


@app.post("/v1/browser/navigate", response_model=OkResponse, tags=["browser"])
async def navigate(req: NavigateRequest):
    """Navigate the open browser to a new URL."""
    try:
        url = await browser_manager.navigate(req.url, force=req.force)
    except StopPointError as exc:
        return _security_response(exc)
    except SecurityError as exc:
        return _security_response(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info("navigate → %s", url)
    return OkResponse(message="Navigated", url=url)


@app.get("/v1/browser/snapshot", response_model=SnapshotResponse, tags=["browser"])
async def snapshot():
    """
    Return a structured snapshot of the current page:
    URL, title, visible text preview, and list of interactive elements.
    """
    try:
        result = await browser_manager.snapshot()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info("snapshot → %s (%d elements)", result.url, len(result.interactive_elements))
    return result


@app.post("/v1/browser/click", tags=["browser"])
async def click(req: ClickRequest):
    """
    Click the element matching *selector*.
    Returns 423 Locked if a stop-point keyword is detected and force=false.
    """
    try:
        url = await browser_manager.click(req.selector, force=req.force)
    except StopPointError as exc:
        logger.warning("stop-point on click: %s", exc)
        return _security_response(exc)
    except SecurityError as exc:
        return _security_response(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    logger.info("click %r → %s", req.selector, url)
    return OkResponse(message="Clicked", url=url)


@app.post("/v1/browser/type", response_model=OkResponse, tags=["browser"])
async def type_text(req: TypeRequest):
    """Type text into the element matching *selector*."""
    try:
        await browser_manager.type_text(
            req.selector, req.text, clear_first=req.clear_first, force=req.force
        )
    except SecurityError as exc:
        return _security_response(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    logger.info("type %r into %r", req.text[:20], req.selector)
    return OkResponse(message="Text typed", url=browser_manager.current_url)


@app.post("/v1/browser/extract", response_model=ExtractResponse, tags=["browser"])
async def extract(req: ExtractRequest):
    """
    Extract content from the current page.
    extract_type: "text" | "html" | "links" | "table"
    selector: optional CSS selector to scope the extraction.
    """
    valid_types = {"text", "html", "links", "table"}
    if req.extract_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"extract_type must be one of {valid_types}",
        )
    try:
        result = await browser_manager.extract(req.selector, req.extract_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    logger.info("extract type=%r selector=%r → %s", req.extract_type, req.selector, result.url)
    return result


@app.get("/v1/browser/screenshot", response_model=ScreenshotResponse, tags=["browser"])
async def screenshot():
    """Capture and return a full-page screenshot as a base64-encoded PNG."""
    try:
        result = await browser_manager.screenshot()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info("screenshot → %s (%d bytes base64)", result.url, len(result.image_base64))
    return result


@app.post("/v1/browser/close", response_model=OkResponse, tags=["browser"])
async def close_browser():
    """
    Close the browser context.
    The Chromium profile is preserved on disk for the next session.
    """
    if not browser_manager.is_open:
        return OkResponse(message="Browser was already closed")

    await browser_manager.close()
    logger.info("browser closed")
    return OkResponse(message="Browser closed")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )

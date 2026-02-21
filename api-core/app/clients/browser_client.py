"""
Cliente HTTP para browser-agent (Playwright en host Linux).
Refleja el API Contract de SPEC.md §12.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class BrowserClient:
    def __init__(self) -> None:
        self._base_url = settings.browser_agent_url
        self._timeout = settings.browser_timeout

    async def _post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}{path}",
                json=payload or {},
            )
            response.raise_for_status()
        return response.json()

    async def _get(self, path: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{self._base_url}{path}")
            response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # API Contract (SPEC.md §12)
    # ------------------------------------------------------------------

    async def open(self, url: str) -> dict[str, Any]:
        return await self._post("/v1/browser/open", {"url": url})

    async def navigate(self, url: str) -> dict[str, Any]:
        return await self._post("/v1/browser/navigate", {"url": url})

    async def snapshot(self) -> dict[str, Any]:
        return await self._get("/v1/browser/snapshot")

    async def click(self, element_id: str) -> dict[str, Any]:
        return await self._post("/v1/browser/click", {"element_id": element_id})

    async def type(self, element_id: str, text: str) -> dict[str, Any]:
        return await self._post("/v1/browser/type", {"element_id": element_id, "text": text})

    async def extract(self, selector: str) -> dict[str, Any]:
        return await self._post("/v1/browser/extract", {"selector": selector})

    async def screenshot(self) -> dict[str, Any]:
        return await self._get("/v1/browser/screenshot")

    async def close(self) -> dict[str, Any]:
        return await self._post("/v1/browser/close")

    # ------------------------------------------------------------------
    # Dispatcher genérico – usado por el executor para llamar por nombre
    # ------------------------------------------------------------------

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Convierte 'browser.<action>' a la llamada de método correspondiente.
        """
        dispatch_map = {
            "open": lambda a: self.open(a["url"]),
            "navigate": lambda a: self.navigate(a["url"]),
            "snapshot": lambda _: self.snapshot(),
            "click": lambda a: self.click(a["element_id"]),
            "type": lambda a: self.type(a["element_id"], a["text"]),
            "extract": lambda a: self.extract(a["selector"]),
            "screenshot": lambda _: self.screenshot(),
            "close": lambda _: self.close(),
        }

        handler = dispatch_map.get(action)
        if handler is None:
            raise ValueError(f"Acción de browser desconocida: {action}")

        return await handler(args)


# Singleton
browser_client = BrowserClient()

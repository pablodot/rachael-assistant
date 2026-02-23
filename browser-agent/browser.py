"""
BrowserManager — async Playwright wrapper for rachael browser-agent.

Lifecycle:
- Call init() once at startup (starts the Playwright engine).
- Call shutdown() at shutdown (closes context + engine).
- open() lazily creates the persistent Chromium context on first use.
- close() destroys the context (profile data is preserved on disk).

One browser context and one page at a time — sufficient for MVP.
"""
import base64
import os
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from config import settings
from models import InteractiveElement, SnapshotResponse, ExtractResponse, ScreenshotResponse
from security import (
    SecurityError,
    StopPointError,
    check_domain,
    check_max_steps,
    check_sensitive_fields,
    check_stop_point,
)

# JavaScript that extracts interactive elements from the current page.
_INTERACTIVE_ELEMENTS_JS = """
() => {
    const results = [];
    const seen = new Set();
    const candidates = document.querySelectorAll(
        'a[href], button:not([disabled]), input:not([type="hidden"]):not([disabled]), ' +
        'select:not([disabled]), textarea:not([disabled]), ' +
        '[role="button"], [role="link"], [role="checkbox"], [role="menuitem"]'
    );
    for (let i = 0; i < Math.min(candidates.length, 80); i++) {
        const el = candidates[i];
        const tag = el.tagName.toLowerCase();
        const id = el.id || null;
        const name = el.getAttribute('name') || null;
        const inputType = el.getAttribute('type') || null;
        const href = el.getAttribute('href') || null;
        const text = (el.innerText || el.value || el.getAttribute('placeholder') ||
                      el.getAttribute('aria-label') || '').trim().slice(0, 120);

        // Build best available selector
        let selector;
        if (id) {
            selector = '#' + id;
        } else if (name) {
            selector = `${tag}[name="${name}"]`;
        } else if (text) {
            selector = `text=${text.slice(0, 50)}`;
        } else {
            selector = tag;
        }

        const key = selector + text;
        if (seen.has(key)) continue;
        seen.add(key);

        results.push({ tag, selector, text: text || null, inputType, name, id, href });
    }
    return results;
}
"""

# JavaScript that returns the visible text of the page.
_PAGE_TEXT_JS = """
() => {
    const body = document.body;
    if (!body) return '';
    return body.innerText.replace(/\\s+/g, ' ').trim().slice(0, 3000);
}
"""

# JavaScript that extracts all links on the page.
_LINKS_JS = """
() => {
    return Array.from(document.querySelectorAll('a[href]')).slice(0, 100).map(a => ({
        text: a.innerText.trim().slice(0, 100),
        href: a.href,
    }));
}
"""


class BrowserManager:
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._current_task_id: Optional[str] = None
        self._step_counts: dict[str, int] = {}

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def init(self) -> None:
        """Start the Playwright engine. Call once at service startup."""
        self._playwright = await async_playwright().start()

    async def shutdown(self) -> None:
        """Close browser context and Playwright engine gracefully."""
        await self._close_context()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _close_context(self) -> None:
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None

    async def _ensure_open(self) -> Page:
        """Return the active page or raise if no browser is open."""
        if self._page is None:
            raise RuntimeError("Browser is not open. Call /v1/browser/open first.")
        return self._page

    def _increment_step(self) -> int:
        """Increment and return the step counter for the current task."""
        tid = self._current_task_id
        if tid:
            self._step_counts[tid] = self._step_counts.get(tid, 0) + 1
            return self._step_counts[tid]
        return 0

    @property
    def is_open(self) -> bool:
        return self._page is not None

    @property
    def current_url(self) -> Optional[str]:
        if self._page:
            return self._page.url
        return None

    @property
    def step_count(self) -> int:
        tid = self._current_task_id
        if tid:
            return self._step_counts.get(tid, 0)
        return 0

    # ── Actions ────────────────────────────────────────────────────────────────

    async def open(self, url: str, task_id: Optional[str] = None, force: bool = False) -> str:
        """
        Open the browser and navigate to *url*.
        Creates the persistent Chromium context if not already running.
        """
        check_domain(url)

        if self._context is None:
            profile_dir = os.path.abspath(settings.chromium_profile_dir)
            os.makedirs(profile_dir, exist_ok=True)
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=settings.headless,
                slow_mo=settings.slow_mo,
                args=["--no-first-run", "--disable-blink-features=AutomationControlled"],
            )

        # Reuse existing page or open a new one
        if not self._context.pages:
            self._page = await self._context.new_page()
        else:
            self._page = self._context.pages[0]

        if task_id:
            self._current_task_id = task_id
            self._step_counts.setdefault(task_id, 0)

        await self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return self._page.url

    async def navigate(self, url: str, force: bool = False) -> str:
        """Navigate the open browser to *url*."""
        check_domain(url)
        page = await self._ensure_open()
        count = self._increment_step()
        check_max_steps(self._current_task_id, count)
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return page.url

    async def snapshot(self) -> SnapshotResponse:
        """Return a structured snapshot of the current page state."""
        page = await self._ensure_open()

        title = await page.title()
        text_preview = await page.evaluate(_PAGE_TEXT_JS)
        raw_elements = await page.evaluate(_INTERACTIVE_ELEMENTS_JS)

        elements = [
            InteractiveElement(
                tag=e["tag"],
                selector=e["selector"],
                text=e.get("text"),
                input_type=e.get("inputType"),
                name=e.get("name"),
                element_id=e.get("id"),
                href=e.get("href"),
            )
            for e in raw_elements
        ]

        return SnapshotResponse(
            url=page.url,
            title=title,
            text_preview=text_preview,
            interactive_elements=elements,
            step_count=self.step_count,
            task_id=self._current_task_id,
        )

    async def click(self, selector: str, force: bool = False) -> str:
        """Click the element matching *selector*."""
        page = await self._ensure_open()
        count = self._increment_step()
        check_max_steps(self._current_task_id, count)

        # Resolve element text for stop-point check
        element_text: Optional[str] = None
        try:
            element_text = await page.locator(selector).first.inner_text(timeout=2_000)
        except Exception:
            pass

        check_stop_point(selector, element_text, force=force)
        await page.locator(selector).first.click(timeout=10_000)
        return page.url

    async def type_text(self, selector: str, text: str, clear_first: bool = True, force: bool = False) -> None:
        """Type *text* into the element matching *selector*."""
        page = await self._ensure_open()
        count = self._increment_step()
        check_max_steps(self._current_task_id, count)

        locator = page.locator(selector).first
        if clear_first:
            await locator.clear(timeout=5_000)
        await locator.type(text, timeout=10_000)

    async def extract(self, selector: Optional[str], extract_type: str) -> ExtractResponse:
        """Extract content from the page."""
        page = await self._ensure_open()
        # Esperar a que la red esté idle para capturar páginas con JS pesado
        try:
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass  # Si timeout, continuamos con lo que haya cargado

        if extract_type == "links":
            content = await page.evaluate(_LINKS_JS)
        elif extract_type == "html":
            scope = page.locator(selector).first if selector else page.locator("body").first
            content = await scope.inner_html(timeout=10_000)
        elif extract_type == "table":
            js = f"""
            () => {{
                const scope = {f'document.querySelector({repr(selector)})' if selector else 'document'};
                const rows = scope ? scope.querySelectorAll('tr') : [];
                return Array.from(rows).map(row =>
                    Array.from(row.querySelectorAll('th, td')).map(cell => cell.innerText.trim())
                );
            }}
            """
            content = await page.evaluate(js)
        else:  # default: text
            if selector:
                # Get text from ALL matching elements (not just the first)
                content = await page.evaluate(
                    """(sel) => {
                        const els = document.querySelectorAll(sel);
                        return Array.from(els)
                            .map(el => el.innerText.trim())
                            .filter(t => t.length > 0)
                            .slice(0, 60)
                            .join('\\n');
                    }""",
                    selector,
                )
            else:
                content = await page.evaluate(_PAGE_TEXT_JS)

        return ExtractResponse(url=page.url, content=content, extract_type=extract_type)

    async def screenshot(self) -> ScreenshotResponse:
        """Capture a full-page screenshot and return it as base64-encoded PNG."""
        page = await self._ensure_open()
        png_bytes = await page.screenshot(full_page=True, type="png")
        encoded = base64.b64encode(png_bytes).decode("utf-8")
        return ScreenshotResponse(url=page.url, image_base64=encoded)

    async def close(self) -> None:
        """Close the browser context (profile data is preserved on disk)."""
        await self._close_context()
        self._current_task_id = None


# Module-level singleton shared by the FastAPI app.
browser_manager = BrowserManager()

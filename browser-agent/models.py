"""
Pydantic models for browser-agent API request and response bodies.
"""
from typing import Any, List, Optional
from pydantic import BaseModel


# ── Requests ──────────────────────────────────────────────────────────────────

class OpenRequest(BaseModel):
    url: str
    task_id: Optional[str] = None
    force: bool = False  # bypass stop-point check on the URL itself


class NavigateRequest(BaseModel):
    url: str
    force: bool = False


class ClickRequest(BaseModel):
    selector: str           # CSS selector, #id, or text match like "text=Buy Now"
    force: bool = False     # bypass stop-point check


class TypeRequest(BaseModel):
    selector: str
    text: str
    clear_first: bool = True
    force: bool = False     # bypass sensitive-field check


class ExtractRequest(BaseModel):
    selector: Optional[str] = None   # CSS selector to scope extraction; None = full page
    extract_type: str = "text"       # "text" | "html" | "links" | "table"


# ── Response fragments ─────────────────────────────────────────────────────────

class InteractiveElement(BaseModel):
    tag: str
    selector: str           # best available selector for this element
    text: Optional[str] = None
    input_type: Optional[str] = None   # for <input> elements
    name: Optional[str] = None
    element_id: Optional[str] = None
    href: Optional[str] = None


# ── Responses ─────────────────────────────────────────────────────────────────

class OkResponse(BaseModel):
    status: str = "ok"
    message: str
    url: Optional[str] = None
    task_id: Optional[str] = None


class SnapshotResponse(BaseModel):
    url: str
    title: str
    text_preview: str                       # first ~2000 chars of visible text
    interactive_elements: List[InteractiveElement]
    step_count: int
    task_id: Optional[str] = None


class ExtractResponse(BaseModel):
    url: str
    content: Any
    extract_type: str


class ScreenshotResponse(BaseModel):
    url: str
    image_base64: str   # PNG encoded as base64
    format: str = "png"


class StopPointError(BaseModel):
    status: str = "stop_point"
    message: str
    element_info: Optional[str] = None
    hint: str = "Re-send the request with force=true after obtaining user approval."


class BrowserStatus(BaseModel):
    is_open: bool
    url: Optional[str] = None
    task_id: Optional[str] = None
    step_count: int = 0

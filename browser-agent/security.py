"""
Security policies for browser-agent.

Three layers of protection:
1. Domain allowlist  — block navigation to unlisted domains.
2. Stop-point detection — pause before critical actions (checkout, payment…).
3. Sensitive field detection — warn when a page contains password/CC inputs.
"""
from urllib.parse import urlparse
from typing import Optional

from config import settings


class SecurityError(Exception):
    """Raised when a security policy blocks an action."""
    def __init__(self, message: str, kind: str = "policy_violation"):
        super().__init__(message)
        self.kind = kind


class StopPointError(SecurityError):
    """Raised when an action matches a stop-point keyword."""
    def __init__(self, message: str, element_info: Optional[str] = None):
        super().__init__(message, kind="stop_point")
        self.element_info = element_info


def check_domain(url: str) -> None:
    """
    Validate that *url* belongs to an allowed domain.
    If the allowlist is empty, all domains are permitted (dev mode).
    Raises SecurityError if the domain is not in the allowlist.
    """
    allowlist = settings.allowlist
    if not allowlist:
        return  # open mode — no restrictions

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    # Strip leading 'www.'
    hostname = hostname.removeprefix("www.")

    for allowed in allowlist:
        allowed = allowed.removeprefix("www.")
        # Exact match or subdomain match (e.g. "github.com" covers "api.github.com")
        if hostname == allowed or hostname.endswith(f".{allowed}"):
            return

    raise SecurityError(
        f"Domain '{hostname}' is not in the allowlist. "
        f"Allowed: {allowlist}",
        kind="domain_blocked",
    )


def check_stop_point(
    selector: str,
    element_text: Optional[str] = None,
    force: bool = False,
) -> None:
    """
    Detect if *selector* or *element_text* matches a stop-point keyword.
    Raises StopPointError unless force=True.
    """
    if force:
        return

    keywords = settings.stop_keywords
    haystack = " ".join(filter(None, [selector, element_text])).lower()

    for kw in keywords:
        if kw in haystack:
            raise StopPointError(
                f"Stop-point detected: element matches keyword '{kw}'. "
                "User approval required before proceeding.",
                element_info=f"selector={selector!r}, text={element_text!r}",
            )


def check_sensitive_fields(fields_info: list[dict]) -> list[str]:
    """
    Given a list of field dicts (tag, input_type, name), return a list
    of warnings for sensitive fields found on the page.
    Does NOT block — just returns warnings for the caller to surface.
    """
    sensitive_types = {"password", "credit-card", "cardnumber", "cvv", "ssn"}
    sensitive_names = {"password", "passwd", "cc", "card", "cvv", "ssn", "secret", "token"}

    warnings: list[str] = []
    for field in fields_info:
        ftype = (field.get("input_type") or "").lower()
        fname = (field.get("name") or "").lower()

        if ftype == "password" or any(s in fname for s in sensitive_names):
            warnings.append(
                f"Sensitive field detected: type={ftype!r}, name={fname!r}"
            )

    return warnings


def check_max_steps(task_id: Optional[str], step_count: int) -> None:
    """
    Raise SecurityError if the step count has reached the configured maximum.
    """
    if step_count >= settings.max_steps_per_task:
        raise SecurityError(
            f"Max steps ({settings.max_steps_per_task}) reached"
            + (f" for task '{task_id}'" if task_id else "")
            + ". Close the browser and start a new task.",
            kind="max_steps_exceeded",
        )

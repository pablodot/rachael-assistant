"""
Configuration for browser-agent service.
All settings can be overridden via environment variables prefixed with BROWSER_.
Example: BROWSER_HEADLESS=true, BROWSER_MAX_STEPS_PER_TASK=100
"""
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BROWSER_",
        env_file_encoding="utf-8",
    )

    # Server
    host: str = "127.0.0.1"
    port: int = 8001

    # Playwright
    chromium_profile_dir: str = "./chromium-profile"
    headless: bool = False
    slow_mo: int = 100  # ms delay between actions

    # Security: comma-separated list of allowed domains.
    # Empty string means allow ALL domains (development mode).
    # Example: "google.com,github.com,wikipedia.org"
    domain_allowlist: str = ""

    # Max browser actions per task_id before the session is force-closed
    max_steps_per_task: int = 50

    # Keywords detected in element text/id/name that trigger a stop-point.
    # Comma-separated string.
    stop_point_keywords: str = (
        "checkout,payment,pay now,confirm purchase,place order,"
        "buy now,complete order,submit order,delete,remove account,"
        "unsubscribe,cancel subscription"
    )

    @property
    def allowlist(self) -> List[str]:
        """Return parsed domain allowlist."""
        if not self.domain_allowlist.strip():
            return []
        return [d.strip().lower() for d in self.domain_allowlist.split(",") if d.strip()]

    @property
    def stop_keywords(self) -> List[str]:
        """Return parsed stop-point keywords."""
        return [k.strip().lower() for k in self.stop_point_keywords.split(",") if k.strip()]


settings = Settings()

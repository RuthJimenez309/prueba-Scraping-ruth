"""Runtime configuration.

Settings are read from environment variables (optionally loaded from a ``.env``
file) and can be overridden by CLI flags. Every value has a safe default so the
scraper runs out of the box with zero configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # python-dotenv is a convenience, not a hard requirement.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv missing is a non-fatal edge case.
    pass

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


@dataclass(slots=True)
class Settings:
    """Immutable bag of tuned knobs shared across the pipeline."""

    user_agent: str = DEFAULT_USER_AGENT
    headless: bool = True
    concurrency: int = 4
    delay: float = 1.0
    jitter: float = 0.5
    nav_timeout_ms: int = 30_000
    max_articles: int = 40
    max_sitemap_entries: int = 4_000
    include_archive: bool = False
    output_dir: Path = Path("data")
    locale: str = "es-HN"
    log_level: str = "INFO"
    retries: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables (with defaults)."""
        return cls(
            user_agent=_env_str("NEWSSCRAPER_USER_AGENT", DEFAULT_USER_AGENT),
            headless=_env_bool("NEWSSCRAPER_HEADLESS", True),
            concurrency=max(1, _env_int("NEWSSCRAPER_CONCURRENCY", 4)),
            delay=max(0.0, _env_float("NEWSSCRAPER_DELAY", 1.0)),
            jitter=max(0.0, _env_float("NEWSSCRAPER_JITTER", 0.5)),
            nav_timeout_ms=_env_int("NEWSSCRAPER_NAV_TIMEOUT_MS", 30_000),
            max_articles=max(1, _env_int("NEWSSCRAPER_MAX_ARTICLES", 40)),
            max_sitemap_entries=max(1, _env_int("NEWSSCRAPER_MAX_SITEMAP_ENTRIES", 4_000)),
            include_archive=_env_bool("NEWSSCRAPER_INCLUDE_ARCHIVE", False),
            output_dir=Path(_env_str("NEWSSCRAPER_OUTPUT_DIR", "data")),
            locale=_env_str("NEWSSCRAPER_LOCALE", "es-HN"),
            log_level=_env_str("NEWSSCRAPER_LOG_LEVEL", "INFO").upper(),
            retries=max(0, _env_int("NEWSSCRAPER_RETRIES", 2)),
        )

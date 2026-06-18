"""Playwright browser lifecycle and the page/text fetch surface.

This is the single place that talks to Playwright. Everything above it works
with plain data, which keeps the framework at the very edge of the system.

Playwright is imported lazily (inside ``start``) so that importing this module --
for ``--help`` output or for unit tests of the pure modules -- never requires a
browser to be installed.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any

from .config import Settings
from .extraction import GATHER_JS, extract_metadata
from .logging_setup import get_logger

log = get_logger(__name__)


class Browser:
    """Async context manager wrapping a headless Chromium context."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._playwright = None
        self._browser = None
        self._context = None

    async def start(self) -> "Browser":
        from playwright.async_api import async_playwright  # lazy import

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._settings.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._context = await self._browser.new_context(
            user_agent=self._settings.user_agent,
            locale=self._settings.locale,
            viewport={"width": 1366, "height": 768},
            extra_http_headers={"Accept-Language": f"{self._settings.locale},es;q=0.9,en;q=0.8"},
        )
        self._context.set_default_navigation_timeout(self._settings.nav_timeout_ms)
        self._context.set_default_timeout(self._settings.nav_timeout_ms)
        log.debug("Browser context ready (headless=%s)", self._settings.headless)
        return self

    async def fetch_text(self, url: str) -> str | None:
        """Fetch a text resource (robots.txt / sitemap XML) via a real navigation.

        We deliberately use ``page.goto`` rather than a bare HTTP request: some
        outlets (La Tribuna) sit behind a WAF that returns 403 to plain
        ``APIRequestContext`` calls but serves the same URL to a genuine browser
        navigation. ``Response.text()`` still returns the raw body (the XML), so
        downstream parsing is unaffected.
        """
        assert self._context is not None, "Browser not started"
        page = await self._context.new_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded")
            if response is None:
                log.warning("fetch_text: no response for %s", url)
                return None
            if not response.ok:
                log.warning("fetch_text got HTTP %s for %s", response.status, url)
                return None
            return await response.text()
        except Exception as exc:
            log.warning("fetch_text failed for %s: %s", url, exc)
            return None
        finally:
            await page.close()

    async def extract_article(self, url: str) -> dict[str, Any] | None:
        """Navigate to *url* and return resolved article metadata, or None.

        The browser only gathers raw inputs; the pure :func:`extract_metadata`
        turns them into the final fields, so the parsing logic stays testable.
        """
        assert self._context is not None, "Browser not started"
        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded")
            gathered = await page.evaluate(GATHER_JS)
        except Exception as exc:
            log.warning("Failed to load %s: %s", url, exc)
            return None
        finally:
            await page.close()

        meta = extract_metadata(gathered)
        meta["url"] = url
        return meta

    async def close(self) -> None:
        for closer in (self._context, self._browser):
            if closer is not None:
                try:
                    await closer.close()
                except Exception:  # pragma: no cover - best-effort teardown
                    pass
        if self._playwright is not None:
            await self._playwright.stop()

    async def __aenter__(self) -> "Browser":
        return await self.start()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

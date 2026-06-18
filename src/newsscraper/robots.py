"""robots.txt enforcement.

This is the feature that makes the scraper a good citizen and satisfies the
"respetar robots.txt" requirement literally: every URL the pipeline is about to
fetch -- sitemaps and article pages alike -- is checked here first. Both target
outlets disallow their on-site *search* endpoints, which is exactly why the
pipeline discovers articles through their (allowed) sitemaps instead.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from .logging_setup import get_logger

log = get_logger(__name__)


class RobotsPolicy:
    """Fetches, caches and queries robots.txt per origin.

    The HTTP fetch is injected (``fetch_text``) so the same Playwright stack --
    and therefore the same User-Agent -- is used everywhere, and so the policy
    can be unit-tested with a fake fetcher and no network.
    """

    def __init__(self, user_agent, fetch_text, default_delay: float = 0.0):
        self._user_agent = user_agent
        self._fetch_text = fetch_text
        self._default_delay = default_delay
        self._parsers: dict[str, RobotFileParser] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _origin(url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}"

    async def _parser_for(self, url: str) -> RobotFileParser:
        origin = self._origin(url)
        async with self._lock:
            cached = self._parsers.get(origin)
            if cached is not None:
                return cached

            robots_url = f"{origin}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robots_url)
            text = None
            try:
                text = await self._fetch_text(robots_url)
            except Exception as exc:  # network hiccup -> fail open, but log it.
                log.warning("Could not fetch %s (%s); assuming allow-all", robots_url, exc)

            if text:
                parser.parse(text.splitlines())
                log.debug("Loaded robots.txt for %s", origin)
            else:
                # No robots.txt -> the spec says everything is allowed.
                parser.allow_all = True
            self._parsers[origin] = parser
            return parser

    async def can_fetch(self, url: str) -> bool:
        """True if our User-Agent is permitted to fetch *url*."""
        parser = await self._parser_for(url)
        return parser.can_fetch(self._user_agent, url)

    async def crawl_delay(self, url: str) -> float:
        """Crawl-delay advertised for our agent, or the configured default."""
        parser = await self._parser_for(url)
        try:
            delay = parser.crawl_delay(self._user_agent)
        except Exception:
            delay = None
        if delay is None:
            return self._default_delay
        return max(float(delay), self._default_delay)

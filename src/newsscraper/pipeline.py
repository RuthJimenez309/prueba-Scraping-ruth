"""Search orchestration: discover -> filter -> fetch (concurrently) -> persist.

The pipeline ties the pure logic and the I/O edges together:

1. **Discover** candidate URLs from each outlet's sitemaps (robots-permitted),
   filtering by keyword against the sitemap title / URL slug.
2. **Fetch** the matched article pages concurrently (bounded by a semaphore and
   spaced out by a polite, crawl-delay-aware pause) and extract their metadata.
3. **Filter** once more on the *resolved* title/description so every stored row
   genuinely contains the keyword, then **persist** to CSV and SQLite.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from .browser import Browser
from .config import Settings
from .logging_setup import get_logger
from .models import Article, SitemapEntry
from .ports import ArticleRepository, SiteAdapter
from .robots import RobotsPolicy
from .sitemap import is_sitemap_index, parse_sitemap_index, parse_urlset
from .textutils import keyword_matches, to_iso8601

log = get_logger(__name__)


@dataclass(slots=True)
class Candidate:
    """A sitemap match awaiting full extraction."""

    site: SiteAdapter
    entry: SitemapEntry


def interleave_by_site(candidates: list["Candidate"]) -> list["Candidate"]:
    """Round-robin candidates across sites so a global cap stays fair.

    Discovery runs site-by-site, so a naive ``[:max]`` slice would favour the
    first outlet. Interleaving (siteA[0], siteB[0], siteA[1], siteB[1], ...)
    gives every outlet a fair share of the budget.
    """
    groups: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.site.key, []).append(candidate)

    ordered: list[Candidate] = []
    lists = list(groups.values())
    index = 0
    while True:
        progressed = False
        for lst in lists:
            if index < len(lst):
                ordered.append(lst[index])
                progressed = True
        if not progressed:
            break
        index += 1
    return ordered


class SearchPipeline:
    def __init__(
        self,
        settings: Settings,
        sites: list[SiteAdapter],
        repository: ArticleRepository,
    ):
        self._settings = settings
        self._sites = sites
        self._repository = repository

    async def run(self, keyword: str) -> list[Article]:
        """Execute the full search for *keyword* and return the stored articles."""
        async with Browser(self._settings) as browser:
            robots = RobotsPolicy(
                self._settings.user_agent,
                browser.fetch_text,
                default_delay=self._settings.delay,
            )

            candidates = await self._discover(browser, robots, keyword)
            log.info("Discovery matched %d candidate article(s)", len(candidates))
            # Fair share across outlets before applying the global cap.
            candidates = interleave_by_site(candidates)[: self._settings.max_articles]

            articles = await self._fetch_all(browser, robots, keyword, candidates)
            log.info("Resolved %d article(s) after extraction + final filter", len(articles))

            saved = self._repository.save_many(articles)
            log.info("Persisted %d article(s)", saved)
            return articles

    # -- phase 1: discovery -------------------------------------------------

    async def _discover(
        self, browser: Browser, robots: RobotsPolicy, keyword: str
    ) -> list[Candidate]:
        candidates: list[Candidate] = []
        seen: set[str] = set()

        for site in self._sites:
            scanned = 0
            sitemaps = list(site.news_sitemaps())
            if self._settings.include_archive:
                sitemaps += list(site.archive_sitemaps())

            for sitemap_url in sitemaps:
                if scanned >= self._settings.max_sitemap_entries:
                    break
                scanned += await self._scan_sitemap(
                    browser, robots, site, sitemap_url, keyword, candidates, seen,
                    budget=self._settings.max_sitemap_entries - scanned,
                )
            log.info("[%s] scanned ~%d sitemap entries", site.key, scanned)
        return candidates

    async def _scan_sitemap(
        self,
        browser: Browser,
        robots: RobotsPolicy,
        site: SiteAdapter,
        sitemap_url: str,
        keyword: str,
        out: list[Candidate],
        seen: set[str],
        budget: int,
        depth: int = 0,
    ) -> int:
        """Fetch and process one sitemap; recurse into indexes. Returns # scanned."""
        if budget <= 0 or depth > 2:
            return 0
        if not await robots.can_fetch(sitemap_url):
            log.warning("[%s] robots.txt disallows sitemap %s -- skipping", site.key, sitemap_url)
            return 0

        text = await browser.fetch_text(sitemap_url)
        if not text:
            return 0

        if is_sitemap_index(text):
            scanned = 0
            for child in parse_sitemap_index(text):
                if scanned >= budget:
                    break
                scanned += await self._scan_sitemap(
                    browser, robots, site, child, keyword, out, seen,
                    budget=budget - scanned, depth=depth + 1,
                )
            return scanned

        entries = parse_urlset(text, source_sitemap=sitemap_url)
        scanned = 0
        for entry in entries[:budget]:
            scanned += 1
            if entry.url in seen:
                continue
            # News sitemaps carry titles (entries are all articles); archive
            # urlsets carry bare URLs, so confirm they look like articles.
            if entry.title is None and not site.is_article_url(entry.url):
                continue
            if keyword_matches(keyword, entry.title, site.slug_text(entry.url)):
                seen.add(entry.url)
                out.append(Candidate(site=site, entry=entry))
        return scanned

    # -- phase 2: concurrent fetch + extraction -----------------------------

    async def _fetch_all(
        self,
        browser: Browser,
        robots: RobotsPolicy,
        keyword: str,
        candidates: list[Candidate],
    ) -> list[Article]:
        semaphore = asyncio.Semaphore(self._settings.concurrency)
        tasks = [
            asyncio.create_task(self._fetch_one(browser, robots, keyword, c, semaphore))
            for c in candidates
        ]
        articles: list[Article] = []
        for task in asyncio.as_completed(tasks):
            article = await task
            if article is not None:
                articles.append(article)
        return articles

    async def _fetch_one(
        self,
        browser: Browser,
        robots: RobotsPolicy,
        keyword: str,
        candidate: Candidate,
        semaphore: asyncio.Semaphore,
    ) -> Article | None:
        site, entry = candidate.site, candidate.entry
        async with semaphore:
            if not await robots.can_fetch(entry.url):
                log.warning("[%s] robots.txt disallows %s -- skipping", site.key, entry.url)
                return None

            # Polite, crawl-delay-aware spacing with a little random jitter.
            delay = await robots.crawl_delay(entry.url)
            await asyncio.sleep(delay + random.uniform(0, self._settings.jitter))

            meta = await self._extract_with_retry(browser, entry.url)

        # Merge extracted metadata with the sitemap data (sitemap as fallback).
        meta = meta or {}
        title = meta.get("title") or entry.title
        if not title:
            log.debug("[%s] no title for %s -- dropping", site.key, entry.url)
            return None

        description = meta.get("description")
        published_at = meta.get("published_at") or to_iso8601(entry.published_at)
        image_url = meta.get("image_url") or entry.image_url
        author = meta.get("author")

        # Final, spec-accurate filter: keyword must be in title OR description.
        if not keyword_matches(keyword, title, description):
            log.debug("[%s] keyword not in resolved title/description: %s", site.key, entry.url)
            return None

        return Article(
            source=site.key,
            title=title,
            url=entry.url,
            keyword=keyword,
            scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            description=description,
            author=author,
            published_at=published_at,
            image_url=image_url,
        )

    async def _extract_with_retry(self, browser: Browser, url: str) -> dict | None:
        attempts = self._settings.retries + 1
        for attempt in range(1, attempts + 1):
            meta = await browser.extract_article(url)
            if meta is not None:
                return meta
            if attempt < attempts:
                backoff = 0.5 * attempt
                log.debug("Retry %d/%d for %s in %.1fs", attempt, attempts - 1, url, backoff)
                await asyncio.sleep(backoff)
        return None

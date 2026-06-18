"""Core domain data structures.

These are intentionally framework-free: no Playwright, no I/O. Keeping them pure
makes the rest of the system easy to unit-test and reason about.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# Canonical CSV / SQLite column order. Declared once and reused by every
# repository so the schema can never drift between backends.
ARTICLE_FIELDS: tuple[str, ...] = (
    "source",
    "title",
    "description",
    "author",
    "published_at",
    "image_url",
    "url",
    "keyword",
    "scraped_at",
)


@dataclass(slots=True)
class SitemapEntry:
    """A single ``<url>`` discovered while crawling a sitemap.

    News sitemaps (Google News format) give us the title, publication date and
    sometimes the lead image for free, which lets us filter by keyword *before*
    spending a browser navigation on the article page.
    """

    url: str
    title: str | None = None
    published_at: str | None = None
    image_url: str | None = None
    source_sitemap: str | None = None


@dataclass(slots=True)
class Article:
    """A fully resolved news article ready to be persisted.

    Field order mirrors :data:`ARTICLE_FIELDS` so dataclass -> row conversion is
    trivial and stable across CSV and SQLite.
    """

    source: str
    title: str
    url: str
    keyword: str
    scraped_at: str
    description: str | None = None
    author: str | None = None
    published_at: str | None = None
    image_url: str | None = None

    def as_row(self) -> dict[str, Any]:
        """Return a dict keyed by :data:`ARTICLE_FIELDS` (stable column order)."""
        data = asdict(self)
        return {name: data.get(name) for name in ARTICLE_FIELDS}

"""Abstract contracts (ports) that decouple the orchestration from concretes.

* :class:`SiteAdapter` captures everything site-specific: which sitemaps to read,
  how to recognise a real article URL, and how to derive searchable text from a
  slug. Adding a new outlet means writing one adapter -- nothing else changes.
* :class:`ArticleRepository` is the persistence contract implemented by the CSV
  and SQLite backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence

from .models import Article


class SiteAdapter(ABC):
    """Site-specific knowledge for one news outlet."""

    #: Stable short identifier, e.g. ``"elheraldo"``. Used as the ``source`` value.
    key: str
    #: Human-readable outlet name, e.g. ``"El Heraldo"``.
    name: str
    #: Canonical site origin, e.g. ``"https://www.elheraldo.hn"``.
    base_url: str

    @abstractmethod
    def news_sitemaps(self) -> Sequence[str]:
        """Google-News-format sitemaps that carry titles + dates (fast path)."""

    @abstractmethod
    def archive_sitemaps(self) -> Sequence[str]:
        """Sitemap indexes / urlsets for deep historical crawling (slow path)."""

    @abstractmethod
    def is_article_url(self, url: str) -> bool:
        """Return True if *url* looks like an individual article (not a section)."""

    @abstractmethod
    def slug_text(self, url: str) -> str:
        """Human-readable text decoded from the URL slug, for keyword matching."""


class ArticleRepository(ABC):
    """Persistence contract. Implementations must be idempotent on ``url``."""

    @abstractmethod
    def save_many(self, articles: Iterable[Article]) -> int:
        """Persist *articles*; return how many rows were written/updated."""

    def close(self) -> None:  # pragma: no cover - optional hook
        """Release any held resources. Default is a no-op."""

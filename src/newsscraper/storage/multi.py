"""Composite repository that fans writes out to several backends at once."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import Article
from ..ports import ArticleRepository


class MultiRepository(ArticleRepository):
    """Write the same articles to every wrapped repository (CSV *and* SQLite)."""

    def __init__(self, repositories: Iterable[ArticleRepository]):
        self._repositories = list(repositories)

    def save_many(self, articles: Iterable[Article]) -> int:
        articles = list(articles)
        for repo in self._repositories:
            repo.save_many(articles)
        return len(articles)

    def close(self) -> None:
        for repo in self._repositories:
            repo.close()

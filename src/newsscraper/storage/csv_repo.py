"""CSV persistence backend.

Idempotent on the article URL: rows already present in the file are not appended
again, so re-running the same search never duplicates data.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from ..models import ARTICLE_FIELDS, Article
from ..ports import ArticleRepository


class CsvArticleRepository(ArticleRepository):
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _existing_urls(self) -> set[str]:
        if not self._path.exists():
            return set()
        with self._path.open("r", newline="", encoding="utf-8") as fh:
            return {row["url"] for row in csv.DictReader(fh) if row.get("url")}

    def save_many(self, articles: Iterable[Article]) -> int:
        articles = list(articles)
        if not articles:
            return 0

        existing = self._existing_urls()
        new_rows = [a for a in articles if a.url not in existing]
        if not new_rows:
            return 0

        write_header = not self._path.exists() or self._path.stat().st_size == 0
        with self._path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(ARTICLE_FIELDS))
            if write_header:
                writer.writeheader()
            for article in new_rows:
                writer.writerow(article.as_row())
        return len(new_rows)

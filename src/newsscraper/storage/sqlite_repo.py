"""SQLite persistence backend.

The ``url`` column is the primary key and writes use ``INSERT OR REPLACE``, so
the table is naturally deduplicated and re-running a search upserts cleanly.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from ..models import ARTICLE_FIELDS, Article
from ..ports import ArticleRepository

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS articles (
    source       TEXT,
    title        TEXT,
    description  TEXT,
    author       TEXT,
    published_at TEXT,
    image_url    TEXT,
    url          TEXT PRIMARY KEY,
    keyword      TEXT,
    scraped_at   TEXT
)
"""


class SqliteArticleRepository(ArticleRepository):
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def save_many(self, articles: Iterable[Article]) -> int:
        rows = [tuple(a.as_row()[field] for field in ARTICLE_FIELDS) for a in articles]
        if not rows:
            return 0
        placeholders = ", ".join("?" for _ in ARTICLE_FIELDS)
        columns = ", ".join(ARTICLE_FIELDS)
        self._conn.executemany(
            f"INSERT OR REPLACE INTO articles ({columns}) VALUES ({placeholders})",
            rows,
        )
        self._conn.commit()
        return len(rows)

    def close(self) -> None:
        self._conn.close()

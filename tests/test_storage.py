import csv
import sqlite3

from newsscraper.models import Article
from newsscraper.storage import (
    CsvArticleRepository,
    MultiRepository,
    SqliteArticleRepository,
)


def _article(url: str, title: str = "T") -> Article:
    return Article(
        source="elheraldo",
        title=title,
        url=url,
        keyword="honduras",
        scraped_at="2026-06-16T00:00:00+00:00",
        description="d",
        author="Redacción",
        published_at="2026-06-15T10:00:00-06:00",
        image_url="https://img/x.jpg",
    )


def test_csv_writes_header_and_rows(tmp_path):
    path = tmp_path / "out.csv"
    repo = CsvArticleRepository(path)
    assert repo.save_many([_article("u1"), _article("u2")]) == 2

    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["url"] for r in rows] == ["u1", "u2"]
    assert rows[0]["author"] == "Redacción"


def test_csv_is_idempotent_on_url(tmp_path):
    path = tmp_path / "out.csv"
    repo = CsvArticleRepository(path)
    repo.save_many([_article("u1")])
    # second run: u1 already present, only u2 is new
    added = repo.save_many([_article("u1"), _article("u2")])
    assert added == 1
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["url"] for r in rows] == ["u1", "u2"]


def test_sqlite_upserts_on_url(tmp_path):
    path = tmp_path / "out.sqlite"
    repo = SqliteArticleRepository(path)
    repo.save_many([_article("u1", title="old")])
    repo.save_many([_article("u1", title="new")])  # same url -> replace
    repo.close()

    conn = sqlite3.connect(path)
    rows = conn.execute("SELECT url, title FROM articles").fetchall()
    conn.close()
    assert rows == [("u1", "new")]


def test_multi_repository_writes_to_all_backends(tmp_path):
    csv_path = tmp_path / "a.csv"
    db_path = tmp_path / "a.sqlite"
    multi = MultiRepository(
        [CsvArticleRepository(csv_path), SqliteArticleRepository(db_path)]
    )
    assert multi.save_many([_article("u1"), _article("u2")]) == 2
    multi.close()

    assert csv_path.exists()
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    conn.close()
    assert count == 2

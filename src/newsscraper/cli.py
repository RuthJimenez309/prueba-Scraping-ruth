"""Command-line interface.

Examples
--------
    # Search both outlets for "elecciones" and write CSV + SQLite
    newsscraper elecciones

    # Only El Heraldo, more results, deep archive crawl
    newsscraper mundial --site elheraldo --max-articles 60 --include-archive

    # Prompt for the keyword interactively
    newsscraper
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .config import Settings
from .logging_setup import configure_logging, get_logger
from .models import Article
from .pipeline import SearchPipeline
from .sites.registry import available_keys, get_sites
from .storage import CsvArticleRepository, MultiRepository, SqliteArticleRepository

log = get_logger("newsscraper.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="newsscraper",
        description="Keyword-driven news scraper for Honduran outlets (Playwright).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "keyword",
        nargs="?",
        help="Keyword to search for (in title or description). Prompted if omitted.",
    )
    parser.add_argument(
        "-s",
        "--site",
        action="append",
        choices=available_keys(),
        metavar="SITE",
        help=f"Outlet to search (repeatable). Choices: {', '.join(available_keys())}. "
        "Default: all.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("csv", "sqlite", "both"),
        default="both",
        help="Output backend(s).",
    )
    parser.add_argument("--output-dir", help="Directory for output files.")
    parser.add_argument("--output-name", default="articles", help="Base name for output files.")
    parser.add_argument("--max-articles", type=int, help="Max articles to fetch.")
    parser.add_argument("--concurrency", type=int, help="Concurrent page fetches.")
    parser.add_argument("--delay", type=float, help="Polite base delay (seconds) per fetch.")
    parser.add_argument(
        "--include-archive",
        action="store_true",
        help="Also crawl deep archive sitemaps (slower, broader history).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run the browser with a visible window (default headless).",
    )
    parser.add_argument("--log-level", help="DEBUG, INFO, WARNING, ERROR.")
    parser.add_argument("--list-sites", action="store_true", help="List supported outlets and exit.")
    return parser


def _settings_from_args(args: argparse.Namespace) -> Settings:
    settings = Settings.from_env()
    if args.output_dir:
        from pathlib import Path

        settings.output_dir = Path(args.output_dir)
    if args.max_articles is not None:
        settings.max_articles = max(1, args.max_articles)
    if args.concurrency is not None:
        settings.concurrency = max(1, args.concurrency)
    if args.delay is not None:
        settings.delay = max(0.0, args.delay)
    if args.include_archive:
        settings.include_archive = True
    if args.headed:
        settings.headless = False
    if args.log_level:
        settings.log_level = args.log_level.upper()
    return settings


def _build_repository(settings: Settings, fmt: str, base_name: str) -> MultiRepository:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    repos = []
    if fmt in ("csv", "both"):
        repos.append(CsvArticleRepository(settings.output_dir / f"{base_name}.csv"))
    if fmt in ("sqlite", "both"):
        repos.append(SqliteArticleRepository(settings.output_dir / f"{base_name}.sqlite"))
    return MultiRepository(repos)


def _resolve_keyword(raw: str | None) -> str:
    keyword = (raw or "").strip()
    if keyword:
        return keyword
    try:
        keyword = input("Keyword to search for: ").strip()
    except (EOFError, KeyboardInterrupt):
        keyword = ""
    return keyword


def _print_summary(articles: list[Article], settings: Settings, base_name: str, fmt: str) -> None:
    print()
    print(f"  Found {len(articles)} article(s).")
    print("  " + "-" * 70)
    for art in articles:
        date = art.published_at or "(no date)"
        author = art.author or "(no author)"
        print(f"  [{art.source}] {date}")
        print(f"    {art.title}")
        print(f"    by {author}")
        print(f"    {art.url}")
        print("  " + "-" * 70)
    outputs = []
    if fmt in ("csv", "both"):
        outputs.append(str(settings.output_dir / f"{base_name}.csv"))
    if fmt in ("sqlite", "both"):
        outputs.append(str(settings.output_dir / f"{base_name}.sqlite"))
    print("  Saved to: " + ", ".join(outputs))
    print()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_sites:
        for key in available_keys():
            print(key)
        return 0

    settings = _settings_from_args(args)
    configure_logging(settings.log_level)

    keyword = _resolve_keyword(args.keyword)
    if not keyword:
        log.error("No keyword provided. Nothing to search.")
        return 2

    try:
        sites = get_sites(args.site)
    except KeyError as exc:
        log.error("%s", exc)
        return 2

    log.info(
        "Searching %s for %r (concurrency=%d, archive=%s)",
        ", ".join(s.key for s in sites),
        keyword,
        settings.concurrency,
        settings.include_archive,
    )

    repository = _build_repository(settings, args.format, args.output_name)
    pipeline = SearchPipeline(settings, sites, repository)
    try:
        articles = asyncio.run(pipeline.run(keyword))
    except KeyboardInterrupt:  # pragma: no cover
        log.warning("Interrupted by user.")
        return 130
    finally:
        repository.close()

    _print_summary(articles, settings, args.output_name, args.format)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

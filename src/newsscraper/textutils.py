"""Pure text helpers: keyword matching and ISO-8601 date normalisation.

No I/O here, so everything in this module is trivially unit-testable.
"""

from __future__ import annotations

import re
import unicodedata

from dateutil import parser as date_parser

_WS = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """Remove diacritics so 'Economía' and 'economia' compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize(text: str | None) -> str:
    """Lower-case, de-accent and collapse whitespace for robust comparison."""
    if not text:
        return ""
    return _WS.sub(" ", strip_accents(text).lower()).strip()


def keyword_matches(keyword: str, *texts: str | None) -> bool:
    """Return True if every token of *keyword* appears across the given texts.

    Matching is case- and accent-insensitive. Multi-word keywords use AND
    semantics (all tokens must be present), which keeps phrase searches precise
    without demanding an exact contiguous match.
    """
    tokens = [t for t in normalize(keyword).split(" ") if t]
    if not tokens:
        return False
    haystack = " ".join(normalize(t) for t in texts if t)
    return all(token in haystack for token in tokens)


def to_iso8601(value: str | None) -> str | None:
    """Normalise an arbitrary date string to ISO-8601, or return None.

    The source sitemaps and Open Graph tags already emit ISO-8601, but article
    bodies sometimes carry looser formats; dateutil absorbs those gracefully.
    """
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return date_parser.parse(value).isoformat()
    except (ValueError, OverflowError, TypeError):
        return None

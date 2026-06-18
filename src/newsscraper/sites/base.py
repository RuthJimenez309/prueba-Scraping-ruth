"""Shared helpers for site adapters."""

from __future__ import annotations

from urllib.parse import unquote, urlsplit

from ..ports import SiteAdapter


class BaseSite(SiteAdapter):
    """Common URL utilities reused by concrete adapters."""

    @staticmethod
    def path_segments(url: str) -> list[str]:
        path = urlsplit(url).path
        return [seg for seg in path.split("/") if seg]

    @classmethod
    def last_segment(cls, url: str) -> str:
        segments = cls.path_segments(url)
        return segments[-1] if segments else ""

    @staticmethod
    def humanize(slug: str) -> str:
        """Turn a hyphen/underscore slug into space-separated words."""
        return unquote(slug).replace("-", " ").replace("_", " ").strip()

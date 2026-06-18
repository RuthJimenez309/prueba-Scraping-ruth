"""El Heraldo (https://www.elheraldo.hn) adapter.

Discovery facts (verified against the live site):

* The Google-News sitemap ``sitemapforgoogle.xml`` lists recent articles with
  ``<news:title>``, ``<news:publication_date>`` and an ``<image:loc>`` -- ideal
  for keyword filtering without touching the article pages.
* ``megasitemap.xml`` is a ``<sitemapindex>`` fanning out to ``megasitemap/N.xml``
  archive urlsets for deep historical search.
* Article URLs end in an upper-case alphanumeric code, e.g.
  ``...-narra-mundial-2026-televisora-telemundo-MD31103069``. Section landing
  pages (``/honduras``, ``/deportes``) never carry such a code.
* The on-site search (``/busquedas/``, ``/search/``) is disallowed by robots.txt,
  so it is deliberately never used.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import urlsplit

from .base import BaseSite

# Trailing article code: a final '-' token with upper-case letters and digits.
_ARTICLE_CODE = re.compile(r"-[A-Z]{1,4}\d{3,}[A-Z0-9]*$")


class ElHeraldo(BaseSite):
    key = "elheraldo"
    name = "El Heraldo"
    base_url = "https://www.elheraldo.hn"

    def news_sitemaps(self) -> Sequence[str]:
        return ("https://www.elheraldo.hn/sitemapforgoogle.xml",)

    def archive_sitemaps(self) -> Sequence[str]:
        return ("https://www.elheraldo.hn/megasitemap.xml",)

    def is_article_url(self, url: str) -> bool:
        if "elheraldo.hn" not in urlsplit(url).netloc:
            return False
        return bool(_ARTICLE_CODE.search(self.last_segment(url)))

    def slug_text(self, url: str) -> str:
        # Drop the trailing code so it doesn't pollute keyword matching.
        last = _ARTICLE_CODE.sub("", self.last_segment(url))
        return self.humanize(last)

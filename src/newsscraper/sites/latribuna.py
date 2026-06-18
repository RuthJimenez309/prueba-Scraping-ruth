"""La Tribuna (https://www.latribuna.hn) adapter.

Discovery facts (verified against the live site):

* WordPress + Yoast SEO. ``news-sitemap.xml`` is a Google-News urlset with
  ``<news:title>`` and ``<news:publication_date>`` for recent posts.
* ``sitemap_index.xml`` fans out to ``post-sitemap.xml`` ... ``post-sitemapN.xml``
  (the first being the most recent) for the full archive.
* Article URLs follow the dated permalink ``/YYYY/MM/DD/slug/``.
* The on-site search (``/?s=``) is disallowed by robots.txt, so it is never used.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from .base import BaseSite

_DATED_PERMALINK = re.compile(r"^/\d{4}/\d{2}/\d{2}/[^/]+/?$")


class LaTribuna(BaseSite):
    key = "latribuna"
    name = "La Tribuna"
    base_url = "https://www.latribuna.hn"

    def news_sitemaps(self) -> Sequence[str]:
        return ("https://www.latribuna.hn/news-sitemap.xml",)

    def archive_sitemaps(self) -> Sequence[str]:
        return ("https://www.latribuna.hn/sitemap_index.xml",)

    def is_article_url(self, url: str) -> bool:
        from urllib.parse import urlsplit

        parts = urlsplit(url)
        if "latribuna.hn" not in parts.netloc:
            return False
        return bool(_DATED_PERMALINK.match(parts.path))

    def slug_text(self, url: str) -> str:
        return self.humanize(self.last_segment(url))

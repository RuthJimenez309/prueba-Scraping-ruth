"""Pure sitemap parsing.

Three shapes are handled, all defined by the sitemaps.org / Google News schemas:

* **sitemap index** -- ``<sitemapindex>`` listing child ``<sitemap><loc>`` URLs.
* **news urlset**   -- ``<urlset>`` where each ``<url>`` carries ``<news:news>``
  (title + publication date) and optionally ``<image:image>`` (lead image).
* **plain urlset**  -- ``<urlset>`` of bare ``<url><loc>`` entries (archive pages).

Parsing is namespace-tolerant: we match by local tag name so a missing or odd
namespace prefix never breaks extraction.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator

from .models import SitemapEntry


def _local(tag: str) -> str:
    """Strip any ``{namespace}`` prefix from an XML tag."""
    return tag.rsplit("}", 1)[-1]


def _find_local(elem: ET.Element, name: str) -> ET.Element | None:
    for child in elem.iter():
        if _local(child.tag) == name:
            return child
    return None


def _first_text(elem: ET.Element, name: str) -> str | None:
    found = _find_local(elem, name)
    if found is not None and found.text:
        return found.text.strip()
    return None


def is_sitemap_index(xml_text: str) -> bool:
    """True if the document root is a ``<sitemapindex>``."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return False
    return _local(root.tag) == "sitemapindex"


def parse_sitemap_index(xml_text: str) -> list[str]:
    """Return the child sitemap URLs from a ``<sitemapindex>`` document."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    urls: list[str] = []
    for sitemap in root:
        if _local(sitemap.tag) != "sitemap":
            continue
        loc = _first_text(sitemap, "loc")
        if loc:
            urls.append(loc)
    return urls


def parse_urlset(xml_text: str, source_sitemap: str | None = None) -> list[SitemapEntry]:
    """Parse a ``<urlset>`` into :class:`SitemapEntry` records.

    Works for both news urlsets (rich metadata) and plain urlsets (loc only).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    entries: list[SitemapEntry] = []
    for url_el in root:
        if _local(url_el.tag) != "url":
            continue
        loc = _first_text(url_el, "loc")
        if not loc:
            continue

        title: str | None = None
        published: str | None = None
        image: str | None = None

        for child in url_el:
            local = _local(child.tag)
            if local == "news":  # <news:news> wrapper
                title = title or _first_text(child, "title")
                published = published or _first_text(child, "publication_date")
            elif local == "image":  # <image:image> wrapper
                image = image or _first_text(child, "loc")
            elif local == "lastmod" and published is None:
                published = child.text.strip() if child.text else None

        entries.append(
            SitemapEntry(
                url=loc,
                title=title,
                published_at=published,
                image_url=image,
                source_sitemap=source_sitemap,
            )
        )
    return entries


def iter_entries(xml_text: str, source_sitemap: str | None = None) -> Iterator[SitemapEntry]:
    """Yield entries from a urlset document (empty for an index)."""
    yield from parse_urlset(xml_text, source_sitemap=source_sitemap)

"""Pure article-metadata extraction.

The browser hands us three raw inputs gathered from the rendered page:

* ``ldjson``   -- the text of every ``<script type="application/ld+json">`` block.
* ``meta``     -- a flat ``{property|name|itemprop: content}`` map of ``<meta>`` tags.
* ``docTitle`` -- ``document.title`` as a last-resort fallback.

From those we resolve the six fields the exercise asks for, using a clear
priority chain: **schema.org JSON-LD first, Open Graph / meta second, document
title last**. The function is pure, so it is unit-tested against saved fixtures
without ever launching a browser.
"""

from __future__ import annotations

import json
from typing import Any

from .textutils import to_iso8601

#: JavaScript evaluated inside the page to collect raw metadata. Returns a
#: JSON-serialisable object consumed by :func:`extract_metadata`.
GATHER_JS = """
() => {
  const ldjson = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => {
    const t = (s.textContent || '').trim();
    if (t) ldjson.push(t);
  });
  const meta = {};
  document.querySelectorAll('meta[property], meta[name], meta[itemprop]').forEach((m) => {
    const key = m.getAttribute('property') || m.getAttribute('name') || m.getAttribute('itemprop');
    const content = m.getAttribute('content');
    if (key && content && !(key in meta)) meta[key] = content;
  });
  return { ldjson, meta, docTitle: document.title || null };
}
"""

# schema.org types that represent an article, ranked by preference.
_ARTICLE_TYPES = (
    "newsarticle",
    "reportagenewsarticle",
    "article",
    "blogposting",
    "liveblogposting",
    "report",
)


def _types_of(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type")
    if isinstance(raw, str):
        return {raw.lower()}
    if isinstance(raw, list):
        return {str(t).lower() for t in raw}
    return set()


def _flatten_ldjson(blocks: list[str]) -> list[dict[str, Any]]:
    """Decode every JSON-LD block into a flat list of object nodes.

    Handles single objects, arrays, and the Yoast/`@graph` container shape.
    """
    nodes: list[dict[str, Any]] = []
    for block in blocks:
        try:
            data = json.loads(block)
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                if isinstance(item.get("@graph"), list):
                    stack.extend(item["@graph"])
                nodes.append(item)
    return nodes


def _pick_article_node(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the best article node by type preference."""
    for wanted in _ARTICLE_TYPES:
        for node in nodes:
            if wanted in _types_of(node):
                return node
    return None


def _name_of(value: Any) -> str | None:
    """Resolve an author-ish value (string | Person dict | list) to a name."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        name = value.get("name")
        return name.strip() if isinstance(name, str) and name.strip() else None
    if isinstance(value, list):
        names = [n for n in (_name_of(v) for v in value) if n]
        return ", ".join(dict.fromkeys(names)) or None
    return None


def _url_of(value: Any) -> str | None:
    """Resolve an image-ish value (string | ImageObject | list) to a URL."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("url", "contentUrl"):
            url = value.get(key)
            if isinstance(url, str) and url.strip():
                return url.strip()
        return None
    if isinstance(value, list):
        for item in value:
            url = _url_of(item)
            if url:
                return url
    return None


def _looks_like_real_author(value: str | None) -> bool:
    """Reject junk author values such as URL paths (e.g. '/cronologia/-/meta')."""
    if not value:
        return False
    value = value.strip()
    if not value:
        return False
    if value.startswith("/") or value.startswith("http"):
        return False
    # A path-like token with slashes and no spaces is almost certainly not a name.
    if "/" in value and " " not in value:
        return False
    return True


def _first(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def extract_metadata(gathered: dict[str, Any]) -> dict[str, str | None]:
    """Resolve title/description/author/published_at/image_url from raw inputs."""
    ldjson_blocks = gathered.get("ldjson") or []
    meta: dict[str, str] = gathered.get("meta") or {}
    doc_title = gathered.get("docTitle")

    nodes = _flatten_ldjson(ldjson_blocks)
    article = _pick_article_node(nodes) or {}

    # --- title -------------------------------------------------------------
    title = _first(
        article.get("headline"),
        article.get("name"),
        meta.get("og:title"),
        meta.get("twitter:title"),
        doc_title,
    )

    # --- description -------------------------------------------------------
    description = _first(
        article.get("description"),
        meta.get("og:description"),
        meta.get("description"),
        meta.get("twitter:description"),
    )

    # --- author ------------------------------------------------------------
    ld_author = _name_of(article.get("author"))
    meta_author = _first(meta.get("author"), meta.get("article:author"), meta.get("byl"))
    author = ld_author if _looks_like_real_author(ld_author) else None
    if author is None and _looks_like_real_author(meta_author):
        author = meta_author

    # --- published_at (normalised to ISO-8601) -----------------------------
    published_raw = _first(
        article.get("datePublished"),
        meta.get("article:published_time"),
        meta.get("datePublished"),
        meta.get("date"),
        article.get("dateCreated"),
    )
    published_at = to_iso8601(published_raw)

    # --- image -------------------------------------------------------------
    image_url = _first(
        meta.get("og:image"),
        _url_of(article.get("image")),
        _url_of(article.get("thumbnailUrl")),
        meta.get("twitter:image"),
    )

    return {
        "title": title,
        "description": description,
        "author": author,
        "published_at": published_at,
        "image_url": image_url,
    }

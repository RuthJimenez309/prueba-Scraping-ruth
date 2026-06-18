"""Extraction tests against realistic JSON-LD / Open Graph fixtures.

The two fixtures mirror the real shapes observed on the live sites:
* El Heraldo  -> multiple JSON-LD blocks, NewsArticle with an author *list* and
  an image *list*; meta[name=author] is a junk path that must be ignored.
* La Tribuna  -> a single Yoast ``@graph`` block whose Article references the
  author by @id (no inline name), so the clean meta[name=author] wins.
"""

import json

from newsscraper.extraction import extract_metadata

HERALDO = {
    "ldjson": [
        json.dumps(
            [
                {"@type": "BreadcrumbList", "itemListElement": []},
                {
                    "@type": "NewsArticle",
                    "headline": "Selección de Honduras gana el partido",
                    "description": "La H venció con autoridad en el estadio.",
                    "datePublished": "2026-06-14T18:14:00-06:00",
                    "author": [
                        {"@type": "Person", "name": "Redacción", "url": "/cronologia/-/meta/redaccion"}
                    ],
                    "image": [
                        "https://www.elheraldo.hn/img/lead.jpg",
                        "https://www.elheraldo.hn/img/alt.jpg",
                    ],
                },
            ]
        )
    ],
    "meta": {
        "og:title": "OG title (should lose to headline)",
        "author": "/cronologia/-/meta/redaccion",  # junk path -> must be ignored
        "og:image": "https://www.elheraldo.hn/img/og.jpg",
    },
    "docTitle": "El Heraldo",
}

TRIBUNA = {
    "ldjson": [
        json.dumps(
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "WebPage", "name": "page"},
                    {
                        "@type": "Article",
                        "headline": "Hondureños brillan en universidades",
                        "description": "La educación marcó la historia de una familia.",
                        "author": {"@id": "https://www.latribuna.hn/#/schema/person/abc"},
                    },
                    {
                        "@type": "Person",
                        "@id": "https://www.latribuna.hn/#/schema/person/abc",
                        "name": "Redacción Web (HG)",
                    },
                ],
            }
        )
    ],
    "meta": {
        "og:title": "Hondureños brillan en universidades",
        "og:description": "La educación marcó la historia de una familia.",
        "article:published_time": "2026-06-17T00:18:36+00:00",
        "og:image": "https://cdn.latribuna.hn/wp-content/uploads/2026/06/lead.webp",
        "author": "Redacción Web (HG)",
    },
    "docTitle": "La Tribuna",
}


def test_heraldo_prefers_jsonld_and_rejects_junk_author():
    meta = extract_metadata(HERALDO)
    assert meta["title"] == "Selección de Honduras gana el partido"
    assert meta["description"] == "La H venció con autoridad en el estadio."
    assert meta["author"] == "Redacción"  # from JSON-LD, not the junk meta path
    assert meta["published_at"] == "2026-06-14T18:14:00-06:00"
    # og:image takes priority, then the JSON-LD image list would be the fallback
    assert meta["image_url"] == "https://www.elheraldo.hn/img/og.jpg"


def test_tribuna_uses_meta_author_when_jsonld_author_is_a_reference():
    meta = extract_metadata(TRIBUNA)
    assert meta["title"] == "Hondureños brillan en universidades"
    assert meta["author"] == "Redacción Web (HG)"
    assert meta["published_at"] == "2026-06-17T00:18:36+00:00"
    assert meta["image_url"].endswith("lead.webp")


def test_image_list_fallback_when_no_og_image():
    data = dict(HERALDO)
    data["meta"] = {k: v for k, v in HERALDO["meta"].items() if k != "og:image"}
    meta = extract_metadata(data)
    assert meta["image_url"] == "https://www.elheraldo.hn/img/lead.jpg"


def test_handles_empty_inputs_gracefully():
    meta = extract_metadata({"ldjson": [], "meta": {}, "docTitle": None})
    assert meta == {
        "title": None,
        "description": None,
        "author": None,
        "published_at": None,
        "image_url": None,
    }


def test_ignores_malformed_jsonld_block():
    meta = extract_metadata({"ldjson": ["{not json"], "meta": {"og:title": "T"}, "docTitle": None})
    assert meta["title"] == "T"

from newsscraper.sitemap import (
    is_sitemap_index,
    parse_sitemap_index,
    parse_urlset,
)

NEWS_URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://www.elheraldo.hn/deportes/seleccion-honduras-gana-MD123456</loc>
    <news:news>
      <news:publication><news:name>El Heraldo</news:name><news:language>es</news:language></news:publication>
      <news:publication_date>2026-06-14T18:14:00-06:00</news:publication_date>
      <news:title>Selección de Honduras gana</news:title>
    </news:news>
    <image:image><image:loc>https://img.example/lead.jpg</image:loc></image:image>
  </url>
  <url>
    <loc>https://www.elheraldo.hn/mundo/otra-noticia-AB987654</loc>
    <news:news>
      <news:publication_date>2026-06-13T10:00:00-06:00</news:publication_date>
      <news:title>Otra noticia</news:title>
    </news:news>
  </url>
</urlset>
"""

INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://www.latribuna.hn/post-sitemap.xml</loc></sitemap>
  <sitemap><loc>https://www.latribuna.hn/post-sitemap2.xml</loc></sitemap>
</sitemapindex>
"""

PLAIN_URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.latribuna.hn/2026/06/16/una-nota/</loc><lastmod>2026-06-16T00:00:00+00:00</lastmod></url>
</urlset>
"""


def test_is_sitemap_index():
    assert is_sitemap_index(INDEX)
    assert not is_sitemap_index(NEWS_URLSET)
    assert not is_sitemap_index("<broken>")


def test_parse_sitemap_index():
    children = parse_sitemap_index(INDEX)
    assert children == [
        "https://www.latribuna.hn/post-sitemap.xml",
        "https://www.latribuna.hn/post-sitemap2.xml",
    ]


def test_parse_news_urlset_extracts_title_date_image():
    entries = parse_urlset(NEWS_URLSET, source_sitemap="news.xml")
    assert len(entries) == 2
    first = entries[0]
    assert first.title == "Selección de Honduras gana"
    assert first.published_at == "2026-06-14T18:14:00-06:00"
    assert first.image_url == "https://img.example/lead.jpg"
    assert first.source_sitemap == "news.xml"
    # second has no image
    assert entries[1].image_url is None


def test_parse_plain_urlset_uses_lastmod_as_date():
    entries = parse_urlset(PLAIN_URLSET)
    assert len(entries) == 1
    assert entries[0].title is None
    assert entries[0].published_at == "2026-06-16T00:00:00+00:00"


def test_parse_invalid_xml_returns_empty():
    assert parse_urlset("<not xml") == []
    assert parse_sitemap_index("<not xml") == []

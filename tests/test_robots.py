"""RobotsPolicy tests with an injected fake fetcher (no network).

The fixtures reproduce the real disallow rules: El Heraldo blocks its search
paths, La Tribuna blocks the WordPress ``/?s=`` query -- while article and
sitemap URLs stay allowed.
"""

import pytest

from newsscraper.robots import RobotsPolicy

HERALDO_ROBOTS = """
User-agent: *
Disallow: /busquedas/
Disallow: /search/
Disallow: /busqueda/-/search/
Crawl-delay: 2
Sitemap: https://www.elheraldo.hn/sitemapforgoogle.xml
"""

TRIBUNA_ROBOTS = """
User-agent: *
Disallow: /?s=
Disallow: /search/
Disallow: /wp-json/
Sitemap: https://www.latribuna.hn/news-sitemap.xml
"""

UA = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120 Safari/537.36"


def _fetcher(mapping):
    async def fetch(url):
        for origin, text in mapping.items():
            if url.startswith(origin):
                return text
        return None

    return fetch


@pytest.mark.asyncio
async def test_heraldo_blocks_search_allows_articles_and_sitemaps():
    policy = RobotsPolicy(UA, _fetcher({"https://www.elheraldo.hn": HERALDO_ROBOTS}))
    assert not await policy.can_fetch("https://www.elheraldo.hn/busquedas/?q=x")
    assert not await policy.can_fetch("https://www.elheraldo.hn/search/foo")
    assert await policy.can_fetch("https://www.elheraldo.hn/deportes/nota-MD123456")
    assert await policy.can_fetch("https://www.elheraldo.hn/sitemapforgoogle.xml")


@pytest.mark.asyncio
async def test_tribuna_blocks_wp_search_allows_articles():
    policy = RobotsPolicy(UA, _fetcher({"https://www.latribuna.hn": TRIBUNA_ROBOTS}))
    assert not await policy.can_fetch("https://www.latribuna.hn/?s=honduras")
    assert await policy.can_fetch("https://www.latribuna.hn/2026/06/16/una-nota/")
    assert await policy.can_fetch("https://www.latribuna.hn/news-sitemap.xml")


@pytest.mark.asyncio
async def test_crawl_delay_is_respected_with_floor():
    policy = RobotsPolicy(
        UA, _fetcher({"https://www.elheraldo.hn": HERALDO_ROBOTS}), default_delay=1.0
    )
    # robots advertises 2s; floor is 1s -> max wins
    assert await policy.crawl_delay("https://www.elheraldo.hn/x-MD1") == 2.0


@pytest.mark.asyncio
async def test_missing_robots_is_fail_open():
    policy = RobotsPolicy(UA, _fetcher({}))  # fetch returns None for everything
    assert await policy.can_fetch("https://example.com/anything")

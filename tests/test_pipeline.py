"""Tests for the pure orchestration helpers (no browser, no network)."""

from newsscraper.models import SitemapEntry
from newsscraper.pipeline import Candidate, interleave_by_site
from newsscraper.sites.elheraldo import ElHeraldo
from newsscraper.sites.latribuna import LaTribuna

EH = ElHeraldo()
LT = LaTribuna()


def _cand(site, n):
    return Candidate(site=site, entry=SitemapEntry(url=f"{site.base_url}/{n}"))


def test_interleave_alternates_across_sites():
    # 3 from El Heraldo, 2 from La Tribuna, all discovered site-by-site.
    cands = [_cand(EH, i) for i in range(3)] + [_cand(LT, i) for i in range(2)]
    sources = [c.site.key for c in interleave_by_site(cands)]
    assert sources == ["elheraldo", "latribuna", "elheraldo", "latribuna", "elheraldo"]


def test_interleave_so_a_cap_keeps_both_sites():
    # The exact bug we hit: a naive [:4] slice would be all El Heraldo.
    cands = [_cand(EH, i) for i in range(10)] + [_cand(LT, i) for i in range(10)]
    top4 = interleave_by_site(cands)[:4]
    assert {c.site.key for c in top4} == {"elheraldo", "latribuna"}


def test_interleave_preserves_within_site_order_and_count():
    cands = [_cand(EH, 0), _cand(EH, 1), _cand(LT, 0)]
    out = interleave_by_site(cands)
    assert len(out) == 3
    eh_urls = [c.entry.url for c in out if c.site.key == "elheraldo"]
    assert eh_urls == [f"{EH.base_url}/0", f"{EH.base_url}/1"]


def test_interleave_empty():
    assert interleave_by_site([]) == []

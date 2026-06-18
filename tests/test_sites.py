from newsscraper.sites.elheraldo import ElHeraldo
from newsscraper.sites.latribuna import LaTribuna
from newsscraper.sites.registry import available_keys, get_sites


def test_registry_lists_both_sites():
    assert set(available_keys()) == {"elheraldo", "latribuna"}
    assert len(get_sites()) == 2
    assert [s.key for s in get_sites(["latribuna"])] == ["latribuna"]


def test_registry_rejects_unknown_site():
    try:
        get_sites(["nope"])
    except KeyError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected KeyError")


def test_heraldo_article_url_detection():
    site = ElHeraldo()
    assert site.is_article_url(
        "https://www.elheraldo.hn/deportes/seleccion-gana-MD31103069"
    )
    # section landing pages are not articles
    assert not site.is_article_url("https://www.elheraldo.hn/deportes")
    assert not site.is_article_url("https://www.elheraldo.hn/deportes/polideportivo")
    # other hosts rejected
    assert not site.is_article_url("https://www.latribuna.hn/2026/06/16/x/")


def test_heraldo_slug_text_strips_trailing_code():
    site = ElHeraldo()
    text = site.slug_text("https://www.elheraldo.hn/deportes/seleccion-de-honduras-gana-MD31103069")
    assert text == "seleccion de honduras gana"


def test_tribuna_article_url_detection():
    site = LaTribuna()
    assert site.is_article_url("https://www.latribuna.hn/2026/06/16/una-nota-cualquiera/")
    assert not site.is_article_url("https://www.latribuna.hn/category/deportes/")
    assert not site.is_article_url("https://www.latribuna.hn/")


def test_tribuna_slug_text():
    site = LaTribuna()
    text = site.slug_text("https://www.latribuna.hn/2026/06/16/hondurenos-brillan-en-universidades/")
    assert text == "hondurenos brillan en universidades"

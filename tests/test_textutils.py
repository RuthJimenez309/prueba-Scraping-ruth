from newsscraper.textutils import keyword_matches, normalize, strip_accents, to_iso8601


def test_strip_accents():
    assert strip_accents("Economía") == "Economia"
    assert strip_accents("Pánico ñoño") == "Panico nono"


def test_normalize_collapses_and_lowercases():
    assert normalize("  Hola   MUNDO ") == "hola mundo"
    assert normalize(None) == ""


def test_keyword_match_is_accent_and_case_insensitive():
    assert keyword_matches("economia", "Crisis de Economía nacional")
    assert keyword_matches("ECONOMÍA", "la economia crece")


def test_keyword_match_multiword_is_and_semantics():
    assert keyword_matches("seleccion honduras", "La Selección de Honduras ganó")
    assert not keyword_matches("seleccion brasil", "La Selección de Honduras ganó")


def test_keyword_match_searches_across_multiple_texts():
    # token split across title and description still matches
    assert keyword_matches("mundial 2026", "Rumbo al Mundial", "Clasificatorias 2026")


def test_keyword_match_empty_keyword_is_false():
    assert not keyword_matches("", "anything")


def test_to_iso8601_passes_through_iso():
    assert to_iso8601("2026-06-14T18:14:00-06:00") == "2026-06-14T18:14:00-06:00"


def test_to_iso8601_parses_loose_dates():
    assert to_iso8601("2026-06-14").startswith("2026-06-14")


def test_to_iso8601_handles_garbage():
    assert to_iso8601("not a date") is None
    assert to_iso8601(None) is None

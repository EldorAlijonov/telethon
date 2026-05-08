from app.config import _parse_int_set, _parse_keywords


def test_parse_int_set_ignores_invalid_values():
    assert _parse_int_set("1, -2, abc, 3.5, 4") == {1, -2, 4}


def test_parse_keywords_normalizes_and_drops_empty_values():
    assert _parse_keywords(" Ish |  | Vakansiya |Xizmat ") == ["ish", "vakansiya", "xizmat"]

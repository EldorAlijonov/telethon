from app.core.config import _parse_int_set, _parse_str_list


def test_parse_int_set_ignores_invalid_values():
    assert _parse_int_set("1, -2, abc, 3.5, 4") == {1, -2, 4}


def test_parse_keywords_normalizes_empty_values():
    assert [item.lower() for item in _parse_str_list(" Ish |  | Vakansiya |Xizmat ")] == ["ish", "vakansiya", "xizmat"]

from app.config import _origins


def test_t4_2_cors_origins_are_read_from_a_comma_separated_value():
    assert _origins("https://a.com, https://b.com ,") == ["https://a.com", "https://b.com"]


def test_t4_2_empty_cors_setting_allows_no_origins():
    assert _origins("") == []

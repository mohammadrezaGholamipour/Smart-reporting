from app.services.text_utils import (
    is_total_label,
    looks_temporal,
    normalize_digits,
    parse_number,
)


def test_parse_persian_and_separators():
    assert parse_number("۱۲٬۳۴۵") == 12345
    assert parse_number("3,750,000,000") == 3750000000
    assert parse_number("۳۳٫۷") == 33.7
    assert parse_number("(1,200)") == -1200
    assert parse_number("80%") == 80
    assert parse_number("80%", allow_percent=False) is None
    assert parse_number("abc") is None
    assert parse_number(True) is None


def test_total_labels_any_language():
    assert is_total_label("Grand Total")
    assert is_total_label("جمع کل")
    assert not is_total_label("North")


def test_temporal_detection():
    assert looks_temporal(["January 2026", "February 2026", "March 2026"])
    assert looks_temporal(["فروردین", "اردیبهشت", "خرداد"])
    assert looks_temporal(["1402", "1403", "1404"])
    assert not looks_temporal(["North", "South", "West"])
    assert normalize_digits("۱۲۳") == "123"

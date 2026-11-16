"""Tests for reading and displaying times."""

import pytest

from umc.core.timecode import format_duration, parse_time


@pytest.mark.parametrize(
    ("value", "seconds"),
    [
        ("0", 0.0),
        ("5", 5.0),
        ("90", 90.0),
        ("12.5", 12.5),
        ("1:30", 90.0),
        ("0:04.5", 4.5),
        ("1:02:03", 3723.0),
        (" 2:00 ", 120.0),
    ],
)
def test_parse_time(value, seconds):
    assert parse_time(value) == seconds


@pytest.mark.parametrize("value", ["", "abc", "1:75", "1:2:3:4", "-5", "nan", "inf", "1:-5"])
def test_parse_time_rejects_invalid(value):
    with pytest.raises(ValueError, match="Invalid time"):
        parse_time(value)


@pytest.mark.parametrize(
    ("seconds", "text"), [(0, "0:00"), (5, "0:05"), (90, "1:30"), (3723, "1:02:03")]
)
def test_format_duration(seconds, text):
    assert format_duration(seconds) == text

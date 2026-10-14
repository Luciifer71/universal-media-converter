"""Tests for conversion presets."""

import pytest

from umc.core.presets import get_preset_options


@pytest.mark.parametrize(
    ("preset", "expected_crf"),
    [
        ("high", "18"),
        ("balanced", "23"),
        ("small", "28"),
    ],
)
def test_video_preset_crf(preset, expected_crf):
    options = get_preset_options(preset)

    assert "-c:v" in options
    assert "libx264" in options
    assert options[options.index("-crf") + 1] == expected_crf


def test_copy_preset():
    assert get_preset_options("copy") == ["-c", "copy"]


def test_invalid_preset():
    with pytest.raises(ValueError, match="Unsupported preset"):
        get_preset_options("invalid")

"""Tests for conversion presets."""

import pytest

from umc.core.presets import (
    get_audio_options,
    get_image_options,
    get_preset_options,
    get_video_options,
)


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


def test_video_preset_is_widely_playable():
    options = get_preset_options("balanced")

    assert options[options.index("-pix_fmt") + 1] == "yuv420p"


@pytest.mark.parametrize("extension", [".wav", ".flac"])
def test_lossless_audio_ignores_quality_presets(extension):
    assert get_audio_options(extension, "high") == get_audio_options(extension, "small")


@pytest.mark.parametrize("extension", [".mp3", ".aac", ".m4a", ".ogg", ".opus"])
def test_lossy_audio_presets_differ(extension):
    assert get_audio_options(extension, "high") != get_audio_options(extension, "small")


def test_webp_quality_presets_differ():
    assert get_image_options(".webp", "high") != get_image_options(".webp", "small")


def test_mp4_gets_faststart():
    assert "+faststart" in get_video_options(".mp4", "balanced")
    assert "+faststart" not in get_video_options(".mkv", "balanced")

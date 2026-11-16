"""Tests for adapting to the encoders the installed FFmpeg provides."""

from unittest.mock import Mock, patch

from umc.core.encoders import (
    adapt_to_encoders,
    available_encoders,
    missing_encoder_message,
    requested_encoders,
)
from umc.core.original import EncodingPlan

ENCODER_LIST = """Encoders:
 V..... = Video
 ------
 V....D libx264              libx264 H.264
 A....D aac                  AAC (Advanced Audio Coding)
 A....D libopus              libopus Opus
"""


def test_available_encoders_parses_ffmpeg_output():
    available_encoders.cache_clear()

    with patch("umc.core.encoders.subprocess.run", return_value=Mock(stdout=ENCODER_LIST)):
        assert available_encoders("ffmpeg-test") == frozenset({"libx264", "aac", "libopus"})

    available_encoders.cache_clear()


def test_available_encoders_unknown_when_ffmpeg_fails():
    available_encoders.cache_clear()

    with patch("umc.core.encoders.subprocess.run", side_effect=OSError("nope")):
        assert available_encoders("ffmpeg-broken") is None

    available_encoders.cache_clear()


def test_requested_encoders_ignores_copy():
    options = ["-c:v", "copy", "-c:a", "aac", "-c:s:0", "srt", "-c", "copy"]

    assert requested_encoders(options) == {"aac", "srt"}


def test_vorbis_is_replaced_with_opus_everywhere_in_the_plan():
    fallback = EncodingPlan(
        ["-vn", "-c:a", "libvorbis", "-q:a", "10"], "maximum Ogg Vorbis quality"
    )
    plan = EncodingPlan(["-vn", "-c:a", "copy"], "identical", fallback=fallback)

    adapted = adapt_to_encoders(plan, frozenset({"libopus"}))

    assert adapted.options == ["-vn", "-c:a", "copy"]
    assert adapted.fallback.options == ["-vn", "-c:a", "libopus", "-b:a", "256k"]
    assert adapted.fallback.quality == "maximum Opus quality"


def test_nothing_changes_when_encoders_are_unknown():
    plan = EncodingPlan(["-c:a", "libvorbis"], "q")

    assert adapt_to_encoders(plan, None) is plan
    assert missing_encoder_message(plan, None, ".ogg") is None


def test_missing_encoder_message():
    plan = EncodingPlan(["-c:v", "libwebp", "-lossless", "1"], "lossless")

    message = missing_encoder_message(plan, frozenset({"png"}), ".webp")

    assert "WebP images" in message
    assert "libwebp" in message
    assert "Try .png" in message


def test_no_message_when_everything_is_available():
    plan = EncodingPlan(["-c:a", "libopus"], "q")

    assert missing_encoder_message(plan, frozenset({"libopus"}), ".opus") is None

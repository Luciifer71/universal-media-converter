"""Tests for FFprobe media inspection."""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from umc.core.probe import ProbeError, inspect_media


def test_missing_file(tmp_path):
    with pytest.raises(ProbeError, match="File does not exist"):
        inspect_media(str(tmp_path / "missing.mp4"))


def test_ffprobe_not_found(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"test")

    with (
        patch("umc.core.probe.shutil.which", return_value=None),
        pytest.raises(ProbeError, match="FFprobe was not found"),
    ):
        inspect_media(str(source))


def test_successful_inspection(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"test")

    metadata = {
        "format": {"duration": "3.0", "size": "1024"},
        "streams": [{"codec_type": "video", "codec_name": "h264"}],
    }

    with (
        patch("umc.core.probe.shutil.which", return_value="ffprobe"),
        patch(
            "umc.core.probe.subprocess.run",
            return_value=Mock(stdout=json.dumps(metadata)),
        ) as mock_run,
    ):
        result = inspect_media(str(source))

    assert result == metadata
    mock_run.assert_called_once()


def test_ffprobe_failure(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"test")

    error = subprocess.CalledProcessError(1, ["ffprobe"], stderr="Invalid media file")

    with (
        patch("umc.core.probe.shutil.which", return_value="ffprobe"),
        patch("umc.core.probe.subprocess.run", side_effect=error),
        pytest.raises(ProbeError, match="Invalid media file"),
    ):
        inspect_media(str(source))


def test_invalid_json(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"test")

    with (
        patch("umc.core.probe.shutil.which", return_value="ffprobe"),
        patch(
            "umc.core.probe.subprocess.run",
            return_value=Mock(stdout="not valid json"),
        ),
        pytest.raises(ProbeError, match="Media inspection failed"),
    ):
        inspect_media(str(source))

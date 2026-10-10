"""Tests for the media conversion engine."""

import subprocess
from unittest.mock import patch

import pytest

from umc.core.converter import (
    ConversionError,
    convert_media,
    find_ffmpeg,
)


def test_ffmpeg_not_found():
    with (
        patch("umc.core.converter.shutil.which", return_value=None),
        pytest.raises(ConversionError, match="FFmpeg was not found"),
    ):
        find_ffmpeg()


def test_missing_input(tmp_path):
    source = tmp_path / "missing.mov"
    destination = tmp_path / "output.mp4"

    with pytest.raises(ConversionError, match="Input file does not exist"):
        convert_media(str(source), str(destination))


def test_same_input_and_output(tmp_path):
    source = tmp_path / "video.mov"
    source.write_bytes(b"test")

    with pytest.raises(ConversionError, match="must be different"):
        convert_media(str(source), str(source))


def test_existing_output(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"input")
    destination.write_bytes(b"existing")

    with pytest.raises(ConversionError, match="already exists"):
        convert_media(str(source), str(destination))


def test_missing_output_directory(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "missing" / "output.mp4"

    source.write_bytes(b"input")

    with pytest.raises(ConversionError, match="Output directory does not exist"):
        convert_media(str(source), str(destination))


def test_successful_conversion(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"test")

    with (
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch("umc.core.converter.subprocess.run") as mock_run,
    ):
        result = convert_media(str(source), str(destination))

    assert result == destination.resolve()
    mock_run.assert_called_once()

    command = mock_run.call_args.args[0]
    assert command[0] == "ffmpeg"
    assert "-nostdin" in command
    assert "-n" in command
    assert str(source.resolve()) in command
    assert str(destination.resolve()) in command


def test_ffmpeg_process_failure(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"test")

    with (
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["ffmpeg"]),
        ),
        pytest.raises(ConversionError, match="exit code 1"),
    ):
        convert_media(str(source), str(destination))


def test_ffmpeg_execution_error(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"test")

    with (
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.run",
            side_effect=OSError("Execution failed"),
        ),
        pytest.raises(ConversionError, match="Unable to execute FFmpeg"),
    ):
        convert_media(str(source), str(destination))

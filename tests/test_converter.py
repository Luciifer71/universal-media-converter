"""Tests for the media conversion engine."""

from unittest.mock import MagicMock, patch

import pytest

from umc.core.converter import (
    ConversionError,
    convert_media,
    find_ffmpeg,
)


def create_mock_process(lines=None, return_code=0):
    """Create a simulated FFmpeg process."""

    process = MagicMock()
    process.stdout = iter(lines or [])
    process.wait.return_value = return_code
    process.__enter__.return_value = process

    return process


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

    process = create_mock_process(
        lines=[
            "out_time_us=1500000\n",
            "progress=continue\n",
            "out_time_us=3000000\n",
            "progress=end\n",
        ]
    )

    with (
        patch("umc.core.converter.get_duration", return_value=3.0),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.Popen",
            return_value=process,
        ) as mock_popen,
    ):
        result = convert_media(str(source), str(destination))

    assert result == destination.resolve()
    mock_popen.assert_called_once()

    command = mock_popen.call_args.args[0]

    assert command[0] == "ffmpeg"
    assert "-progress" in command
    assert "pipe:1" in command
    assert "-nostdin" in command
    assert "-n" in command
    assert str(source.resolve()) in command
    assert str(destination.resolve()) in command


def test_ffmpeg_process_failure(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"test")

    process = create_mock_process(return_code=1)

    with (
        patch("umc.core.converter.get_duration", return_value=3.0),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.Popen",
            return_value=process,
        ),
        pytest.raises(ConversionError, match="FFmpeg exited with code 1"),
    ):
        convert_media(str(source), str(destination))


def test_ffmpeg_execution_error(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"test")

    with (
        patch("umc.core.converter.get_duration", return_value=3.0),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.Popen",
            side_effect=OSError("Execution failed"),
        ),
        pytest.raises(ConversionError, match="Unable to execute FFmpeg"),
    ):
        convert_media(str(source), str(destination))


@pytest.mark.parametrize(
    ("preset", "expected_crf"),
    [
        ("high", "18"),
        ("balanced", "23"),
        ("small", "28"),
    ],
)
def test_conversion_uses_video_preset(tmp_path, preset, expected_crf):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"
    source.write_bytes(b"test")

    process = create_mock_process()

    with (
        patch("umc.core.converter.get_duration", return_value=3.0),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.Popen",
            return_value=process,
        ) as mock_popen,
    ):
        convert_media(str(source), str(destination), preset=preset)

    command = mock_popen.call_args.args[0]

    assert "-crf" in command
    assert command[command.index("-crf") + 1] == expected_crf


def test_conversion_uses_copy_preset(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"
    source.write_bytes(b"test")

    process = create_mock_process()

    with (
        patch("umc.core.converter.get_duration", return_value=3.0),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.Popen",
            return_value=process,
        ) as mock_popen,
    ):
        convert_media(str(source), str(destination), preset="copy")

    command = mock_popen.call_args.args[0]

    assert "-c" in command
    assert command[command.index("-c") + 1] == "copy"
    assert "-crf" not in command


def test_unsupported_output_format(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.avi"
    source.write_bytes(b"test")

    with pytest.raises(
        ConversionError,
        match="Conversion presets currently support MP4 output only",
    ):
        convert_media(str(source), str(destination))


def test_unsupported_preset(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"
    source.write_bytes(b"test")

    with pytest.raises(ConversionError, match="Unsupported preset"):
        convert_media(str(source), str(destination), preset="invalid")

"""Tests for the media conversion engine."""

from unittest.mock import MagicMock, patch

import pytest

from umc.core.converter import (
    ConversionError,
    convert_media,
    find_ffmpeg,
    get_duration,
    partial_path,
)

VIDEO_AND_AUDIO = {
    "format": {"duration": "3.0"},
    "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
}
AUDIO_ONLY = {"format": {"duration": "3.0"}, "streams": [{"codec_type": "audio"}]}
IMAGE_ONLY = {"format": {}, "streams": [{"codec_type": "video"}]}
AUDIO_WITH_COVER = {
    "format": {"duration": "3.0"},
    "streams": [
        {"codec_type": "audio"},
        {"codec_type": "video", "disposition": {"attached_pic": 1}},
    ],
}


def create_mock_process(lines=None, return_code=0):
    """Create a simulated FFmpeg process."""

    process = MagicMock()
    process.stdout = iter(lines or [])
    process.wait.return_value = return_code
    process.__enter__.return_value = process

    return process


def run_conversion(tmp_path, output_name, preset="balanced", metadata=VIDEO_AND_AUDIO):
    """Run convert_media with FFmpeg mocked out and return the FFmpeg command."""
    source = tmp_path / "input.mov"
    source.write_bytes(b"test")
    destination = tmp_path / output_name

    with (
        patch("umc.core.converter.read_metadata", return_value=metadata),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch("umc.core.converter.os.replace") as mock_replace,
        patch(
            "umc.core.converter.subprocess.Popen",
            return_value=create_mock_process(),
        ) as mock_popen,
    ):
        convert_media(str(source), str(destination), preset=preset)

    mock_replace.assert_called_once_with(partial_path(destination.resolve()), destination.resolve())
    return mock_popen.call_args.args[0]


def test_ffmpeg_not_found():
    with (
        patch("umc.core.converter.shutil.which", return_value=None),
        pytest.raises(ConversionError, match="FFmpeg was not found"),
    ):
        find_ffmpeg()


def test_ffmpeg_not_found_shows_install_help():
    with (
        patch("umc.core.converter.shutil.which", return_value=None),
        pytest.raises(ConversionError, match="winget install"),
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


def test_existing_output_with_overwrite(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"input")
    destination.write_bytes(b"existing")

    with (
        patch("umc.core.converter.read_metadata", return_value=VIDEO_AND_AUDIO),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch("umc.core.converter.os.replace") as mock_replace,
        patch(
            "umc.core.converter.subprocess.Popen",
            return_value=create_mock_process(),
        ),
    ):
        convert_media(str(source), str(destination), overwrite=True)

    mock_replace.assert_called_once()


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
        patch("umc.core.converter.read_metadata", return_value=VIDEO_AND_AUDIO),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch("umc.core.converter.os.replace"),
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
    assert str(source.resolve()) in command
    # FFmpeg writes to a temporary file that is renamed when finished.
    assert command[-1] == str(partial_path(destination.resolve()))


def test_ffmpeg_process_failure(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"test")

    process = create_mock_process(return_code=1)

    with (
        patch("umc.core.converter.read_metadata", return_value=VIDEO_AND_AUDIO),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.Popen",
            return_value=process,
        ),
        pytest.raises(ConversionError, match="FFmpeg exited with code 1"),
    ):
        convert_media(str(source), str(destination))

    assert not destination.exists()


def test_failed_conversion_removes_partial_file(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"
    source.write_bytes(b"test")
    partial = partial_path(destination.resolve())
    partial.write_bytes(b"half written")

    with (
        patch("umc.core.converter.read_metadata", return_value=VIDEO_AND_AUDIO),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch(
            "umc.core.converter.subprocess.Popen",
            return_value=create_mock_process(return_code=1),
        ),
        pytest.raises(ConversionError),
    ):
        convert_media(str(source), str(destination))

    assert not partial.exists()


def test_cancelled_conversion(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"
    source.write_bytes(b"test")

    process = create_mock_process()
    process.stdout = MagicMock()
    process.stdout.__iter__.side_effect = KeyboardInterrupt

    with (
        patch("umc.core.converter.read_metadata", return_value=VIDEO_AND_AUDIO),
        patch("umc.core.converter.shutil.which", return_value="ffmpeg"),
        patch("umc.core.converter.subprocess.Popen", return_value=process),
        pytest.raises(ConversionError, match="cancelled"),
    ):
        convert_media(str(source), str(destination))

    process.kill.assert_called_once()


def test_ffmpeg_execution_error(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"

    source.write_bytes(b"test")

    with (
        patch("umc.core.converter.read_metadata", return_value=VIDEO_AND_AUDIO),
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
    command = run_conversion(tmp_path, "output.mp4", preset)

    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-crf") + 1] == expected_crf


def test_conversion_uses_copy_preset(tmp_path):
    command = run_conversion(tmp_path, "output.mp4", "copy")

    assert command[command.index("-c") + 1] == "copy"
    assert "-crf" not in command


@pytest.mark.parametrize("extension", [".mp4", ".mkv", ".mov"])
def test_h264_video_formats(tmp_path, extension):
    command = run_conversion(tmp_path, f"output{extension}")

    assert command[command.index("-c:v") + 1] == "libx264"


def test_webm_uses_vp9(tmp_path):
    command = run_conversion(tmp_path, "output.webm")

    assert command[command.index("-c:v") + 1] == "libvpx-vp9"
    assert command[command.index("-c:a") + 1] == "libopus"


@pytest.mark.parametrize(
    ("extension", "codec"),
    [
        (".mp3", "libmp3lame"),
        (".wav", "pcm_s16le"),
        (".flac", "flac"),
        (".aac", "aac"),
        (".m4a", "aac"),
        (".ogg", "libvorbis"),
        (".opus", "libopus"),
    ],
)
def test_audio_output_formats(tmp_path, extension, codec):
    command = run_conversion(tmp_path, f"output{extension}")

    assert "-vn" in command
    assert command[command.index("-c:a") + 1] == codec
    assert "libx264" not in command


@pytest.mark.parametrize(
    ("preset", "bitrate"),
    [("high", "320k"), ("balanced", "192k"), ("small", "128k")],
)
def test_audio_presets_change_quality(tmp_path, preset, bitrate):
    command = run_conversion(tmp_path, "output.mp3", preset)

    assert command[command.index("-b:a") + 1] == bitrate


def test_audio_copy_preset_rejected(tmp_path):
    with pytest.raises(ConversionError, match="copy preset is not supported for audio"):
        run_conversion(tmp_path, "output.mp3", "copy")


@pytest.mark.parametrize("extension", [".jpg", ".jpeg", ".png", ".webp", ".bmp"])
def test_image_output_formats(tmp_path, extension):
    command = run_conversion(tmp_path, f"output{extension}")

    assert command[command.index("-frames:v") + 1] == "1"
    assert command[command.index("-map") + 1] == "0:v:0"
    assert "-an" in command
    assert "libx264" not in command


def test_image_copy_preset_rejected(tmp_path):
    with pytest.raises(ConversionError, match="copy preset is not supported for image"):
        run_conversion(tmp_path, "output.png", "copy")


def test_image_to_image(tmp_path):
    command = run_conversion(tmp_path, "output.webp", metadata=IMAGE_ONLY)

    assert "libwebp" in command


def test_cover_art_can_become_image(tmp_path):
    command = run_conversion(tmp_path, "cover.jpg", metadata=AUDIO_WITH_COVER)

    assert "-frames:v" in command


def test_audio_input_rejected_for_video_output(tmp_path):
    with pytest.raises(ConversionError, match="has no video"):
        run_conversion(tmp_path, "output.mp4", metadata=AUDIO_ONLY)


def test_cover_art_is_not_a_video(tmp_path):
    with pytest.raises(ConversionError, match="has no video"):
        run_conversion(tmp_path, "output.mp4", metadata=AUDIO_WITH_COVER)


def test_audio_input_rejected_for_image_output(tmp_path):
    with pytest.raises(ConversionError, match="no video or picture"):
        run_conversion(tmp_path, "output.png", metadata=AUDIO_ONLY)


def test_image_input_rejected_for_audio_output(tmp_path):
    with pytest.raises(ConversionError, match="has no audio"):
        run_conversion(tmp_path, "output.mp3", metadata=IMAGE_ONLY)


def test_unreadable_metadata_skips_stream_check(tmp_path):
    command = run_conversion(tmp_path, "output.mp3", metadata=None)

    assert "-vn" in command


def test_get_duration():
    assert get_duration({"format": {"duration": "12.5"}}) == 12.5
    assert get_duration({"format": {"duration": "N/A"}}) is None
    assert get_duration({"format": {}}) is None
    assert get_duration(None) is None


def test_unsupported_preset(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.mp4"
    source.write_bytes(b"test")

    with pytest.raises(ConversionError, match="Unsupported preset"):
        convert_media(str(source), str(destination), preset="invalid")


def test_unsupported_output_format(tmp_path):
    source = tmp_path / "input.mov"
    destination = tmp_path / "output.avi"
    source.write_bytes(b"test")

    with pytest.raises(ConversionError, match="Unsupported output format: .avi"):
        convert_media(str(source), str(destination))

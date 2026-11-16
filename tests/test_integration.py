"""End-to-end tests that run the real FFmpeg.

They create tiny test files with FFmpeg's built-in generators, so no media
needs to be stored in the repository. Skipped when FFmpeg is not installed.
"""

import shutil
import subprocess

import pytest

from umc.cli import main

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg is not installed",
)


TIMEOUT = 120  # seconds; turns a hang into a clear failure


def run(command):
    return subprocess.run(
        [str(part) for part in command],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=TIMEOUT,
    )


def ffmpeg(*args):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *args])


def decoded_md5(path, stream):
    """MD5 of the decoded audio/video, to prove two files hold identical content."""
    result = run(
        [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            path,
            "-map",
            f"0:{stream}",
            "-f",
            "md5",
            "-",
        ]
    )
    return result.stdout.strip()


def streams(path):
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            path,
        ]
    )
    return result.stdout.split()


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    folder = tmp_path_factory.mktemp("media")
    ffmpeg(
        "-f", "lavfi", "-i", "testsrc2=duration=3:size=320x240:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", folder / "clip.mov",
    )  # fmt: skip
    ffmpeg(
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:a", "pcm_s16le", folder / "tone.wav",
    )  # fmt: skip
    ffmpeg(
        "-f", "lavfi", "-i", "color=c=red@0.5:size=64x64,format=rgba",
        "-frames:v", "1", folder / "logo.png",
    )  # fmt: skip
    (folder / "subs.srt").write_text("1\n00:00:00,500 --> 00:00:01,500\nHello\n")
    ffmpeg(
        "-f", "lavfi", "-i", "testsrc2=duration=2:size=320x240",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=2",
        "-i", folder / "subs.srt",
        "-map", "0", "-map", "1", "-map", "2", "-map", "3",
        "-c:v", "libx264", "-c:a", "aac", "-c:s", "mov_text", "-shortest",
        folder / "two_languages.mp4",
    )  # fmt: skip
    return folder


def test_mov_to_mp4_is_identical(media, tmp_path):
    output = tmp_path / "clip.mp4"

    assert main(["convert", str(media / "clip.mov"), str(output)]) == 0
    assert decoded_md5(output, "v") == decoded_md5(media / "clip.mov", "v")
    assert decoded_md5(output, "a") == decoded_md5(media / "clip.mov", "a")


def test_wav_to_flac_is_lossless(media, tmp_path):
    output = tmp_path / "tone.flac"

    assert main(["convert", str(media / "tone.wav"), str(output)]) == 0
    assert decoded_md5(output, "a") == decoded_md5(media / "tone.wav", "a")


@pytest.mark.parametrize("extension", ["mp3", "m4a", "ogg", "opus", "wav", "aac"])
def test_extract_audio(media, tmp_path, extension):
    output = tmp_path / f"sound.{extension}"

    assert main(["convert", str(media / "clip.mov"), str(output)]) == 0
    assert streams(output) == ["audio"]


@pytest.mark.parametrize("extension", ["mkv", "webm"])
def test_other_video_formats(media, tmp_path, extension):
    output = tmp_path / f"clip.{extension}"

    assert main(["convert", str(media / "clip.mov"), str(output)]) == 0
    assert "video" in streams(output)


def test_small_preset_shrinks_video(media, tmp_path):
    output = tmp_path / "small.mp4"

    assert main(["convert", str(media / "clip.mov"), str(output), "--preset", "small"]) == 0
    assert output.stat().st_size < (media / "clip.mov").stat().st_size


@pytest.mark.parametrize("extension", ["jpg", "png", "webp", "bmp"])
def test_thumbnail_at_time(media, tmp_path, extension):
    output = tmp_path / f"thumb.{extension}"

    assert main(["convert", str(media / "clip.mov"), str(output), "--at", "0:01.5"]) == 0
    assert output.stat().st_size > 0


def test_png_to_webp_is_pixel_identical(media, tmp_path):
    output = tmp_path / "logo.webp"

    assert main(["convert", str(media / "logo.png"), str(output)]) == 0

    def pixels(path):
        return run(
            [
                "ffmpeg",
                "-nostdin",
                "-loglevel",
                "error",
                "-i",
                path,
                "-pix_fmt",
                "rgba",
                "-f",
                "md5",
                "-",
            ]
        ).stdout

    assert pixels(output) == pixels(media / "logo.png")


def test_mkv_keeps_every_track(media, tmp_path):
    output = tmp_path / "movie.mkv"

    assert main(["convert", str(media / "two_languages.mp4"), str(output)]) == 0
    assert streams(output) == ["video", "audio", "audio", "subtitle"]


def test_batch_folder(media, tmp_path):
    folder = tmp_path / "in"
    folder.mkdir()
    shutil.copy(media / "clip.mov", folder)
    shutil.copy(media / "tone.wav", folder)

    assert main(["batch", str(folder), "--to", "mp3"]) == 0
    assert (folder / "clip.mp3").is_file()
    assert (folder / "tone.mp3").is_file()


def test_no_partial_files_left_after_error(media, tmp_path):
    broken = tmp_path / "broken.mov"
    broken.write_bytes(b"not a video")

    assert main(["convert", str(broken), str(tmp_path / "out.mp4")]) == 1
    assert list(tmp_path.iterdir()) == [broken]

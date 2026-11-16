"""FFmpeg-based media conversion engine."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from umc.core.formats import detect_media_type
from umc.core.original import EncodingPlan, plan_original
from umc.core.presets import (
    DEFAULT_PRESET,
    PresetName,
    get_audio_options,
    get_image_options,
    get_video_options,
    validate_preset,
)
from umc.core.probe import FFMPEG_INSTALL_HINT, ProbeError, inspect_media
from umc.core.timecode import format_duration


class ConversionError(Exception):
    """Raised when media conversion fails."""


class ConversionCancelled(ConversionError):
    """Raised when the user stops a conversion with Ctrl+C."""


class IncompatibleInputError(ConversionError):
    """Raised when the input lacks the audio or video needed for the output."""


def find_ffmpeg() -> str:
    """Find FFmpeg on the system PATH."""
    executable = shutil.which("ffmpeg")

    if executable is None:
        raise ConversionError(f"FFmpeg was not found.\n{FFMPEG_INSTALL_HINT}")

    return executable


def read_metadata(source: Path) -> dict | None:
    """Read media metadata with FFprobe, or return None if that is not possible."""
    try:
        return inspect_media(str(source))
    except ProbeError:
        return None


def get_duration(metadata: dict | None) -> float | None:
    """Get media duration in seconds, if available."""
    if not metadata:
        return None

    try:
        duration = float(metadata.get("format", {}).get("duration", 0))
    except (ValueError, TypeError):
        return None

    return duration if duration > 0 else None


def has_real_video(metadata: dict | None) -> bool:
    """True when the input has a moving video stream (not just album art)."""
    return any(
        stream.get("codec_type") == "video"
        and not stream.get("disposition", {}).get("attached_pic")
        for stream in (metadata or {}).get("streams", [])
    )


def is_still_image(metadata: dict | None) -> bool:
    """True when the input is a single picture (PNG, JPG, ...) rather than a video."""
    format_name = (metadata or {}).get("format", {}).get("format_name", "")
    return format_name == "image2" or format_name.endswith("_pipe")


def has_transparency(metadata: dict | None) -> bool:
    """True when the first picture has an alpha (transparency) channel."""
    for stream in (metadata or {}).get("streams", []):
        if stream.get("codec_type") == "video":
            pixel_format = stream.get("pix_fmt", "")
            return pixel_format.startswith(("yuva", "gbrap", "ya")) or pixel_format in {
                "rgba",
                "bgra",
                "argb",
                "abgr",
                "rgba64le",
                "rgba64be",
            }

    return False


def image_notes(metadata: dict | None, extension: str, at: float | None) -> list[str]:
    """Helpful notes for image output."""
    notes = []

    if extension in (".jpg", ".jpeg") and has_transparency(metadata):
        notes.append("JPG cannot store transparency; use .png or .webp to keep it.")

    if at is None and has_real_video(metadata) and not is_still_image(metadata):
        notes.append(
            "Saved the first frame of the video. Add --at (e.g. --at 1:30) to pick another moment."
        )

    return notes


def check_input_streams(metadata: dict | None, media_type: str) -> None:
    """Give a clear error when the input cannot produce the requested output."""
    if not metadata:
        # FFprobe could not read the file; let FFmpeg report the problem.
        return

    streams = metadata.get("streams", [])
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    has_picture = any(stream.get("codec_type") == "video" for stream in streams)

    if media_type == "audio" and not has_audio:
        raise IncompatibleInputError(
            "The input file has no audio, so it cannot be converted to audio."
        )

    if media_type == "image" and not has_picture:
        raise IncompatibleInputError(
            "The input file has no video or picture, so it cannot be converted to an image."
        )

    if media_type == "video" and not has_real_video(metadata):
        raise IncompatibleInputError(
            "The input file has no video, so it cannot be converted to a video format. "
            "To convert audio, choose an audio format such as .mp3."
        )


def build_plan(
    media_type: str,
    extension: str,
    preset: PresetName,
    metadata: dict | None,
    at: float | None = None,
) -> EncodingPlan:
    """Decide which FFmpeg settings to use for this conversion."""
    if preset == "original":
        return plan_original(media_type, extension, metadata, at)

    try:
        if media_type == "audio":
            options = get_audio_options(extension, preset)
        elif media_type == "image":
            options = get_image_options(extension, preset)
        else:
            options = get_video_options(extension, preset)

    except ValueError as exc:
        raise ConversionError(str(exc)) from exc

    if preset == "copy":
        return EncodingPlan(options, quality="identical to the original (copy preset)")

    return EncodingPlan(options, quality=f"'{preset}' preset (smaller file, some quality loss)")


def partial_path(destination: Path) -> Path:
    """Temporary file FFmpeg writes to before the result is moved into place."""
    return destination.with_name(f"{destination.stem}.umc-partial{destination.suffix}")


def show_progress(seconds: float, duration: float | None) -> None:
    """Display conversion progress in the terminal."""
    if duration is None:
        print(f"\rProcessed: {seconds:.1f}s", end="", flush=True)
        return

    percentage = min(100, max(0, seconds / duration * 100))
    filled = round(percentage / 5)
    bar = "#" * filled + "-" * (20 - filled)

    print(f"\rConverting: [{bar}] {percentage:5.1f}%", end="", flush=True)


def run_ffmpeg(command: list[str], temporary: Path, duration: float | None, show_bar: bool) -> None:
    """Run FFmpeg, show progress and raise ConversionError if it fails."""
    try:
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as error_log:
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=error_log,
                text=True,
                encoding="utf-8",
                errors="replace",
            ) as process:
                assert process.stdout is not None

                try:
                    for line in process.stdout:
                        key, separator, value = line.strip().partition("=")

                        if not separator or not show_bar:
                            continue

                        if key == "out_time_us":
                            try:
                                show_progress(int(value) / 1_000_000, duration)
                            except ValueError:
                                continue

                        elif key == "progress" and value == "end" and duration is not None:
                            show_progress(duration, duration)

                    return_code = process.wait()

                except KeyboardInterrupt:
                    process.kill()
                    process.wait()
                    if show_bar:
                        print()
                    temporary.unlink(missing_ok=True)
                    raise ConversionCancelled("Conversion cancelled.") from None

            if show_bar:
                print()

            if return_code != 0:
                temporary.unlink(missing_ok=True)
                error_log.seek(0)
                details = error_log.read().strip()
                message = details or f"FFmpeg exited with code {return_code}"
                raise ConversionError(f"FFmpeg conversion failed: {message}")

    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ConversionError(f"Unable to execute FFmpeg: {exc}") from exc


def convert_media(
    input_file: str,
    output_file: str,
    preset: PresetName = DEFAULT_PRESET,
    overwrite: bool = False,
    at: float | None = None,
) -> Path:
    """Convert a media file using FFmpeg.

    The output format is chosen from the output file extension. ``at`` is the
    time in seconds of the frame to save when the output is an image.
    """

    source = Path(input_file).expanduser().resolve()
    destination = Path(output_file).expanduser().resolve()

    if not source.is_file():
        raise ConversionError(f"Input file does not exist: {source}")

    if source == destination:
        raise ConversionError("Input and output paths must be different.")

    if not destination.parent.is_dir():
        raise ConversionError(f"Output directory does not exist: {destination.parent}")

    if destination.exists() and not overwrite:
        raise ConversionError(
            f"Output file already exists: {destination}\n"
            "Use --overwrite to replace it, or choose a different output name."
        )

    try:
        validate_preset(preset)
        media_type = detect_media_type(str(destination))
    except ValueError as exc:
        raise ConversionError(str(exc)) from exc

    if at is not None and media_type != "image":
        raise ConversionError(
            "--at only works when saving an image, for example: "
            "umc convert video.mp4 thumbnail.jpg --at 1:30"
        )

    metadata = read_metadata(source)
    check_input_streams(metadata, media_type)
    duration = get_duration(metadata)
    notes = []

    if at is not None and metadata and (is_still_image(metadata) or not has_real_video(metadata)):
        notes.append("--at was ignored because the input is a still picture, not a video.")
        at = None

    if at is not None and duration is not None and at >= duration:
        raise ConversionError(
            f"--at {at:g} is past the end of the video, which is only "
            f"{format_duration(duration)} ({duration:.2f} seconds) long."
        )

    plan = build_plan(media_type, destination.suffix.lower(), preset, metadata, at)

    if media_type == "image":
        notes += image_notes(metadata, destination.suffix.lower(), at)
    show_bar = media_type != "image"
    temporary = partial_path(destination)
    ffmpeg = find_ffmpeg()
    seek = ["-ss", f"{at:.3f}"] if at is not None else []

    print(f"Input:  {source.name}")
    print(f"Output: {destination.name}")

    while True:
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-nostats",
            "-progress",
            "pipe:1",
            "-y",
            *seek,
            "-i",
            str(source),
            *plan.options,
            str(temporary),
        ]

        try:
            run_ffmpeg(command, temporary, duration, show_bar)
            break

        except ConversionCancelled:
            raise

        except ConversionError:
            if plan.fallback is None:
                raise

            print("Direct copy was not possible; re-encoding at maximum quality instead.")
            plan = plan.fallback

    if not temporary.is_file() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise ConversionError(
            "FFmpeg finished but produced no output. The input may be empty or damaged."
        )

    try:
        os.replace(temporary, destination)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ConversionError(f"Could not save the output file: {exc}") from exc

    print(f"Quality: {plan.quality}")

    for note in [*notes, *plan.notes]:
        print(f"Note: {note}")

    return destination

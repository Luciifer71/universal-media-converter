"""FFmpeg-based media conversion engine."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from umc.core.formats import detect_media_type
from umc.core.presets import (
    DEFAULT_PRESET,
    PresetName,
    get_audio_options,
    get_image_options,
    get_video_options,
    validate_preset,
)
from umc.core.probe import FFMPEG_INSTALL_HINT, ProbeError, inspect_media


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


def check_input_streams(metadata: dict | None, media_type: str) -> None:
    """Give a clear error when the input cannot produce the requested output."""
    if not metadata:
        # FFprobe could not read the file; let FFmpeg report the problem.
        return

    streams = metadata.get("streams", [])
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    has_picture = any(stream.get("codec_type") == "video" for stream in streams)
    has_real_video = any(
        stream.get("codec_type") == "video"
        and not stream.get("disposition", {}).get("attached_pic")
        for stream in streams
    )

    if media_type == "audio" and not has_audio:
        raise IncompatibleInputError(
            "The input file has no audio, so it cannot be converted to audio."
        )

    if media_type == "image" and not has_picture:
        raise IncompatibleInputError(
            "The input file has no video or picture, so it cannot be converted to an image."
        )

    if media_type == "video" and not has_real_video:
        raise IncompatibleInputError(
            "The input file has no video, so it cannot be converted to a video format. "
            "To convert audio, choose an audio format such as .mp3."
        )


def get_encoding_options(destination: Path, preset: PresetName) -> tuple[str, list[str]]:
    """Return the media type and FFmpeg encoding arguments for an output file."""
    try:
        media_type = detect_media_type(str(destination))
        extension = destination.suffix.lower()

        if media_type == "audio":
            return media_type, get_audio_options(extension, preset)

        if media_type == "image":
            return media_type, get_image_options(extension, preset)

        return media_type, get_video_options(extension, preset)

    except ValueError as exc:
        raise ConversionError(str(exc)) from exc


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


def convert_media(
    input_file: str,
    output_file: str,
    preset: PresetName = DEFAULT_PRESET,
    overwrite: bool = False,
) -> Path:
    """Convert a media file using FFmpeg.

    The output format is chosen from the output file extension.
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
    except ValueError as exc:
        raise ConversionError(str(exc)) from exc

    media_type, encoding_options = get_encoding_options(destination, preset)

    metadata = read_metadata(source)
    check_input_streams(metadata, media_type)
    duration = get_duration(metadata) if media_type != "image" else None
    show_bar = media_type != "image"

    temporary = partial_path(destination)

    command = [
        find_ffmpeg(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-nostats",
        "-progress",
        "pipe:1",
        "-y",
        "-i",
        str(source),
        *encoding_options,
        str(temporary),
    ]

    print(f"Input:  {source.name}")
    print(f"Output: {destination.name}")

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

    try:
        os.replace(temporary, destination)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ConversionError(f"Could not save the output file: {exc}") from exc

    return destination

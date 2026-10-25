"""FFmpeg-based media conversion engine."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from umc.core.presets import DEFAULT_PRESET, PresetName, get_preset_options
from umc.core.probe import ProbeError, inspect_media


class ConversionError(Exception):
    """Raised when media conversion fails."""


def find_ffmpeg() -> str:
    """Find FFmpeg on the system PATH."""
    executable = shutil.which("ffmpeg")

    if executable is None:
        raise ConversionError("FFmpeg was not found. Install FFmpeg and add it to PATH.")

    return executable


def get_duration(source: Path) -> float | None:
    """Get media duration, if available."""
    try:
        metadata = inspect_media(str(source))
        duration = float(metadata.get("format", {}).get("duration", 0))
        return duration if duration > 0 else None
    except (ProbeError, ValueError, TypeError):
        return None


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
) -> Path:
    """Convert a media file using FFmpeg."""

    source = Path(input_file).expanduser().resolve()
    destination = Path(output_file).expanduser().resolve()

    if not source.is_file():
        raise ConversionError(f"Input file does not exist: {source}")

    if source == destination:
        raise ConversionError("Input and output paths must be different.")

    if not destination.parent.is_dir():
        raise ConversionError(f"Output directory does not exist: {destination.parent}")

    if destination.exists():
        raise ConversionError(f"Output file already exists: {destination}")

    if destination.suffix.lower() != ".mp4":
        raise ConversionError("Conversion presets currently support MP4 output only.")

    if preset not in ("high", "balanced", "small", "copy"):
        raise ConversionError(f"Unsupported preset: {preset}")

    duration = get_duration(source)

    command = [
        find_ffmpeg(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-nostats",
        "-progress",
        "pipe:1",
        "-n",
        "-i",
        str(source),
        *get_preset_options(preset),
        str(destination),
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

                for line in process.stdout:
                    key, separator, value = line.strip().partition("=")

                    if not separator:
                        continue

                    if key == "out_time_us":
                        try:
                            show_progress(int(value) / 1_000_000, duration)
                        except ValueError:
                            continue

                    elif key == "progress" and value == "end" and duration is not None:
                        show_progress(duration, duration)

                return_code = process.wait()

            print()

            if return_code != 0:
                error_log.seek(0)
                details = error_log.read().strip()
                message = details or f"FFmpeg exited with code {return_code}"
                raise ConversionError(f"FFmpeg conversion failed: {message}")

    except OSError as exc:
        raise ConversionError(f"Unable to execute FFmpeg: {exc}") from exc

    return destination

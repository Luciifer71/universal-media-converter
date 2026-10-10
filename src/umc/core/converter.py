"""FFmpeg-based media conversion engine."""

import shutil
import subprocess
from pathlib import Path


class ConversionError(Exception):
    """Raised when media conversion fails."""


def find_ffmpeg() -> str:
    """Find FFmpeg on the system PATH."""
    executable = shutil.which("ffmpeg")

    if executable is None:
        raise ConversionError("FFmpeg was not found. Install FFmpeg and add it to PATH.")

    return executable


def convert_media(input_file: str, output_file: str) -> Path:
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

    command = [
        find_ffmpeg(),
        "-hide_banner",
        "-nostdin",
        "-n",
        "-i",
        str(source),
        str(destination),
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise ConversionError(f"FFmpeg conversion failed with exit code {exc.returncode}.") from exc
    except OSError as exc:
        raise ConversionError(f"Unable to execute FFmpeg: {exc}") from exc

    return destination

"""Read media metadata using FFprobe."""

import json
import shutil
import subprocess
from pathlib import Path

FFMPEG_INSTALL_HINT = (
    "Install FFmpeg and make sure it is on your PATH:\n"
    "  Windows: winget install Gyan.FFmpeg\n"
    "  macOS:   brew install ffmpeg\n"
    "  Linux:   sudo apt install ffmpeg  (or your distribution's package manager)\n"
    "Then open a new terminal and run: ffmpeg -version"
)


class ProbeError(Exception):
    """Raised when media inspection fails."""


def inspect_media(file_path: str) -> dict:
    """Return media metadata as a dictionary."""

    source = Path(file_path).expanduser().resolve()

    if not source.is_file():
        raise ProbeError(f"File does not exist: {source}")

    ffprobe = shutil.which("ffprobe")

    if ffprobe is None:
        raise ProbeError(f"FFprobe was not found.\n{FFMPEG_INSTALL_HINT}")

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(source),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )

        return json.loads(result.stdout)

    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or "").strip()

        if not details:
            details = f"FFprobe exited with code {exc.returncode}"

        raise ProbeError(f"Could not inspect media: {details}") from exc

    except (OSError, ValueError) as exc:
        raise ProbeError(f"Media inspection failed: {exc}") from exc

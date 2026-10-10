"""Read media metadata using FFprobe."""

import json
import shutil
import subprocess
from pathlib import Path


class ProbeError(Exception):
    """Raised when media inspection fails."""


def inspect_media(file_path: str) -> dict:
    """Return media metadata as a dictionary."""

    source = Path(file_path).expanduser().resolve()

    if not source.is_file():
        raise ProbeError(f"File does not exist: {source}")

    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise ProbeError("FFprobe was not found. Add FFmpeg to PATH.")

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
        raise ProbeError(f"Could not inspect media: {exc.stderr.strip()}") from exc
    except (OSError, ValueError) as exc:
        raise ProbeError(f"Media inspection failed: {exc}") from exc

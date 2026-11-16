"""Supported media formats and media type detection."""

from pathlib import Path

VIDEO_FORMATS = {".mp4", ".mkv", ".mov", ".webm"}
AUDIO_FORMATS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".opus"}
IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

OUTPUT_FORMATS = VIDEO_FORMATS | AUDIO_FORMATS | IMAGE_FORMATS

# Extra input-only formats that FFmpeg can read. Used to pick files during
# batch conversion; any file FFmpeg understands works with `umc convert`.
EXTRA_INPUT_FORMATS = {
    ".avi",
    ".wmv",
    ".flv",
    ".m4v",
    ".3gp",
    ".mts",
    ".m2ts",
    ".ts",
    ".mpg",
    ".mpeg",
    ".wma",
    ".aiff",
    ".aif",
    ".amr",
    ".gif",
    ".tif",
    ".tiff",
}

INPUT_FORMATS = OUTPUT_FORMATS | EXTRA_INPUT_FORMATS


def normalize_extension(value: str) -> str:
    """Turn 'MP3', '.mp3' or 'song.mp3' into '.mp3'."""
    value = value.strip().lower()
    suffix = Path(value).suffix

    if suffix:
        return suffix

    return value if value.startswith(".") else f".{value}"


def detect_media_type(output_file: str) -> str:
    """Return "video", "audio" or "image" based on the output file extension."""
    extension = Path(output_file).suffix.lower()

    if extension in VIDEO_FORMATS:
        return "video"

    if extension in AUDIO_FORMATS:
        return "audio"

    if extension in IMAGE_FORMATS:
        return "image"

    supported = ", ".join(sorted(ext.lstrip(".") for ext in OUTPUT_FORMATS))
    raise ValueError(
        f"Unsupported output format: {extension or '(none)'}. Supported formats: {supported}"
    )

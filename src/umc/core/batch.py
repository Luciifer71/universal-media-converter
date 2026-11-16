"""Helpers for choosing output names and converting folders of files."""

from pathlib import Path

from umc.core.formats import INPUT_FORMATS, OUTPUT_FORMATS, normalize_extension

CONVERTED_SUFFIX = "-converted"


def is_format_name(value: str) -> bool:
    """Return True for values like 'mp3' or '.mp3' (a format, not a file name)."""
    path = Path(value)

    if path.suffix or len(path.parts) != 1:
        return False

    return normalize_extension(value) in OUTPUT_FORMATS


def default_output_path(source: Path, extension: str, output_dir: Path | None = None) -> Path:
    """Build an output path next to the source file (or inside output_dir).

    video.mov + .mp4 -> video.mp4
    video.mp4 + .mp4 -> video-converted.mp4 (never overwrite the original)
    """
    extension = normalize_extension(extension)
    folder = output_dir if output_dir is not None else source.parent
    target = folder / f"{source.stem}{extension}"

    if target.resolve() == source.resolve():
        target = folder / f"{source.stem}{CONVERTED_SUFFIX}{extension}"

    return target


def find_media_files(folder: Path) -> list[Path]:
    """List media files directly inside a folder, sorted by name."""
    files = []

    for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in INPUT_FORMATS:
            continue

        # Skip our own temporary files and earlier same-format results.
        if ".umc-partial" in path.name or path.stem.endswith(CONVERTED_SUFFIX):
            continue

        files.append(path)

    return files

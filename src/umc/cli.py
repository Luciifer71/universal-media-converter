"""Command-line interface for Universal Media Converter."""

import argparse
import sys
from pathlib import Path

from umc import __version__
from umc.core.batch import default_output_path, find_media_files, is_format_name
from umc.core.converter import (
    ConversionCancelled,
    ConversionError,
    IncompatibleInputError,
    convert_media,
)
from umc.core.formats import (
    AUDIO_FORMATS,
    IMAGE_FORMATS,
    OUTPUT_FORMATS,
    VIDEO_FORMATS,
    normalize_extension,
)
from umc.core.presets import DEFAULT_PRESET, PRESET_DESCRIPTIONS, PRESET_NAMES
from umc.core.probe import ProbeError, inspect_media

EXAMPLES = """\
examples:
  umc convert video.mov video.mp4          convert a video
  umc convert video.mov mp3                extract the audio as video.mp3
  umc convert song.wav song.mp3 --preset high
  umc convert video.mp4 thumbnail.jpg      save the first frame as an image
  umc convert video.mp4 mp4 --preset small shrink a video (video-converted.mp4)
  umc batch ./holiday --to mp4             convert every file in a folder
  umc info video.mp4                       show details about a file
  umc formats                              list supported formats and presets
"""


def add_common_options(parser: argparse.ArgumentParser) -> None:
    """Options shared by the convert and batch commands."""
    parser.add_argument(
        "-p",
        "--preset",
        choices=PRESET_NAMES,
        default=DEFAULT_PRESET,
        help="Quality preset: high, balanced, small or copy (default: balanced).",
    )
    parser.add_argument(
        "-y",
        "--overwrite",
        action="store_true",
        help="Replace output files that already exist.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="umc",
        description="Universal Media Converter - convert video, audio and images.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
    )

    # Convert command
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a media file.",
        description="Convert a media file. The output format is chosen from the "
        "output file extension.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    convert_parser.add_argument(
        "input",
        help="Path to the input media file.",
    )

    convert_parser.add_argument(
        "output",
        help="Output file (e.g. output.mp4), or just a format (e.g. mp3) to save "
        "next to the input file.",
    )

    add_common_options(convert_parser)

    # Batch command
    batch_parser = subparsers.add_parser(
        "batch",
        help="Convert every media file in a folder.",
        description="Convert every media file in a folder to one format.",
    )

    batch_parser.add_argument(
        "folder",
        help="Folder containing the files to convert.",
    )

    batch_parser.add_argument(
        "-t",
        "--to",
        required=True,
        metavar="FORMAT",
        help="Output format, e.g. mp4, mp3 or jpg.",
    )

    batch_parser.add_argument(
        "-o",
        "--output-dir",
        help="Folder for the converted files (default: same folder as the originals).",
    )

    add_common_options(batch_parser)

    # Info command
    info_parser = subparsers.add_parser(
        "info",
        help="Display information about a media file.",
    )

    info_parser.add_argument(
        "file",
        help="Path to the media file.",
    )

    # Formats command
    subparsers.add_parser(
        "formats",
        help="List supported output formats and presets.",
    )

    return parser


def format_size(num_bytes: int) -> str:
    """Return a human-readable file size."""
    size = float(num_bytes)

    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} GB"


def format_duration(seconds: float) -> str:
    """Return a duration like 1:02:03 or 4:05."""
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"


def run_convert(args: argparse.Namespace) -> int:
    """Handle `umc convert`."""
    output = args.output

    if is_format_name(output):
        output = str(default_output_path(Path(args.input).expanduser(), output))

    try:
        result = convert_media(
            args.input,
            output,
            preset=args.preset,
            overwrite=args.overwrite,
        )

    except ConversionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    size = f" ({format_size(result.stat().st_size)})" if result.is_file() else ""
    print(f"Conversion completed: {result}{size}")
    return 0


def run_batch(args: argparse.Namespace) -> int:
    """Handle `umc batch`."""
    folder = Path(args.folder).expanduser()
    extension = normalize_extension(args.to)

    if not folder.is_dir():
        print(f"Error: Folder does not exist: {folder}", file=sys.stderr)
        return 1

    if extension not in OUTPUT_FORMATS:
        supported = ", ".join(sorted(ext.lstrip(".") for ext in OUTPUT_FORMATS))
        print(
            f"Error: Unsupported output format: {args.to}. Supported formats: {supported}",
            file=sys.stderr,
        )
        return 1

    output_dir = Path(args.output_dir).expanduser() if args.output_dir else None

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    files = find_media_files(folder)

    if output_dir is None:
        # Files already in the target format only need converting when the
        # results go to a different folder (for example, to compress them).
        files = [path for path in files if path.suffix.lower() != extension]

    if not files:
        print(f"No media files found in {folder}")
        return 0

    converted, skipped, failed = 0, 0, []

    for number, source in enumerate(files, start=1):
        target = default_output_path(source, extension, output_dir)
        print(f"\n[{number}/{len(files)}] {source.name}")

        if target.exists() and not args.overwrite:
            print(f"Skipped: {target.name} already exists (use --overwrite to replace it).")
            skipped += 1
            continue

        try:
            convert_media(str(source), str(target), preset=args.preset, overwrite=args.overwrite)
            converted += 1

        except IncompatibleInputError as exc:
            print(f"Skipped: {exc}")
            skipped += 1

        except ConversionCancelled:
            print("Batch cancelled.", file=sys.stderr)
            return 130

        except ConversionError as exc:
            print(f"Failed: {exc}", file=sys.stderr)
            failed.append(source.name)

    print(f"\nDone: {converted} converted, {skipped} skipped, {len(failed)} failed.")

    if failed:
        print("Failed files: " + ", ".join(failed), file=sys.stderr)
        return 1

    return 0


def run_info(args: argparse.Namespace) -> int:
    """Handle `umc info`."""
    try:
        metadata = inspect_media(args.file)

    except ProbeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    format_info = metadata.get("format", {})
    streams = metadata.get("streams", [])

    print(f"File: {format_info.get('filename', args.file)}")
    print(f"Format: {format_info.get('format_long_name', 'Unknown')}")

    duration = format_info.get("duration")

    if duration is not None:
        try:
            seconds = float(duration)
            print(f"Duration: {seconds:.2f} seconds ({format_duration(seconds)})")
        except ValueError:
            pass

    size = format_info.get("size")

    if size is not None:
        print(f"Size: {format_size(int(size))}")

    for stream in streams:
        kind = stream.get("codec_type", "unknown")
        codec = stream.get("codec_name", "unknown")

        if kind == "video" and stream.get("disposition", {}).get("attached_pic"):
            kind = "cover art"

        print(f"{kind.capitalize()} codec: {codec}")

        if kind in ("video", "cover art"):
            width = stream.get("width")
            height = stream.get("height")

            if width is not None and height is not None:
                print(f"Resolution: {width}x{height}")

        if kind == "audio":
            sample_rate = stream.get("sample_rate")
            channels = stream.get("channels")

            if sample_rate:
                print(f"Sample rate: {sample_rate} Hz")

            if channels:
                print(f"Channels: {channels}")

    return 0


def run_formats() -> int:
    """Handle `umc formats`."""

    def names(formats: set[str]) -> str:
        return ", ".join(sorted(ext.lstrip(".") for ext in formats))

    print("Output formats:")
    print(f"  Video:  {names(VIDEO_FORMATS)}")
    print(f"  Audio:  {names(AUDIO_FORMATS)}")
    print(f"  Images: {names(IMAGE_FORMATS)}")
    print("\nInput: almost any audio, video or image file FFmpeg can read.")
    print("\nPresets (--preset):")

    for name in PRESET_NAMES:
        print(f"  {name:<9} {PRESET_DESCRIPTIONS[name]}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the Universal Media Converter CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    commands = {
        "convert": run_convert,
        "batch": run_batch,
        "info": run_info,
        "formats": lambda _args: run_formats(),
    }

    if args.command not in commands:
        parser.print_help()
        return 0

    try:
        return commands[args.command](args)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

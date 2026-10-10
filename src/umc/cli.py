"""Command-line interface for Universal Media Converter."""

import argparse
import sys

from umc import __version__
from umc.core.converter import ConversionError, convert_media
from umc.core.probe import ProbeError, inspect_media


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="umc",
        description="Universal Media Converter - convert video, audio and images.",
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

    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a media file.",
    )

    convert_parser.add_argument(
        "input",
        help="Path to the input media file.",
    )

    convert_parser.add_argument(
        "output",
        help="Path to the output media file.",
    )

    info_parser = subparsers.add_parser(
        "info",
        help="Display information about a media file.",
    )

    info_parser.add_argument(
        "file",
        help="Path to the media file.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "convert":
        try:
            output = convert_media(args.input, args.output)
        except ConversionError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        print(f"Conversion completed: {output}")
        return 0
    if args.command == "info":
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
            print(f"Duration: {float(duration):.2f} seconds")

        size = format_info.get("size")
        if size is not None:
            print(f"Size: {int(size) / (1024 * 1024):.2f} MB")

        for stream in streams:
            kind = stream.get("codec_type", "unknown")
            codec = stream.get("codec_name", "unknown")

            print(f"{kind.capitalize()} codec: {codec}")

            if kind == "video":
                width = stream.get("width")
                height = stream.get("height")

                if width is not None and height is not None:
                    print(f"Resolution: {width}x{height}")

        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

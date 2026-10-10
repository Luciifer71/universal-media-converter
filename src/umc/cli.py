"""Command-line interface for Universal Media Converter."""

import argparse
import sys

from umc import __version__
from umc.core.converter import ConversionError, convert_media


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

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

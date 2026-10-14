"""Tests for the Universal Media Converter CLI."""

from pathlib import Path
from unittest.mock import patch

import pytest

from umc.cli import build_parser, main
from umc.core.converter import ConversionError


def test_convert_default_preset():
    parser = build_parser()
    args = parser.parse_args(["convert", "input.mov", "output.mp4"])

    assert args.preset == "balanced"


@pytest.mark.parametrize("preset", ["high", "balanced", "small", "copy"])
def test_convert_accepts_presets(preset):
    parser = build_parser()
    args = parser.parse_args(["convert", "input.mov", "output.mp4", "--preset", preset])

    assert args.preset == preset


def test_convert_rejects_invalid_preset():
    parser = build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["convert", "input.mov", "output.mp4", "--preset", "invalid"])

    assert exc.value.code == 2


def test_cli_passes_preset_to_converter(capsys):
    with (
        patch(
            "sys.argv",
            ["umc", "convert", "input.mov", "output.mp4", "--preset", "high"],
        ),
        patch(
            "umc.cli.convert_media",
            return_value=Path("output.mp4"),
        ) as mock_convert,
    ):
        result = main()

    assert result == 0
    mock_convert.assert_called_once_with(
        "input.mov",
        "output.mp4",
        preset="high",
    )

    captured = capsys.readouterr()
    assert "Conversion completed:" in captured.out


def test_cli_handles_conversion_error(capsys):
    with (
        patch("sys.argv", ["umc", "convert", "input.mov", "output.mp4"]),
        patch(
            "umc.cli.convert_media",
            side_effect=ConversionError("Test conversion failure"),
        ),
    ):
        result = main()

    assert result == 1

    captured = capsys.readouterr()
    assert "Test conversion failure" in captured.err

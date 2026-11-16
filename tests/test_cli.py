"""Tests for the Universal Media Converter CLI."""

from pathlib import Path
from unittest.mock import patch

import pytest

from umc.cli import build_parser, main
from umc.core.converter import ConversionCancelled, ConversionError, IncompatibleInputError


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
        overwrite=False,
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


def test_convert_overwrite_flag():
    args = build_parser().parse_args(["convert", "a.mov", "b.mp4", "--overwrite"])

    assert args.overwrite is True


def test_convert_format_shorthand(tmp_path):
    source = tmp_path / "song.wav"
    source.write_bytes(b"audio")

    with patch("umc.cli.convert_media", return_value=tmp_path / "song.mp3") as mock_convert:
        result = main(["convert", str(source), "mp3"])

    assert result == 0
    assert mock_convert.call_args.args[1] == str(tmp_path / "song.mp3")


def test_convert_shorthand_same_format_does_not_overwrite_input(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")

    with patch("umc.cli.convert_media", return_value=source) as mock_convert:
        main(["convert", str(source), "mp4", "--preset", "small"])

    assert mock_convert.call_args.args[1] == str(tmp_path / "video-converted.mp4")


def test_formats_command(capsys):
    assert main(["formats"]) == 0

    output = capsys.readouterr().out
    assert "mp4" in output
    assert "mp3" in output
    assert "webp" in output
    assert "balanced" in output


def test_no_command_prints_help(capsys):
    assert main([]) == 0
    assert "usage: umc" in capsys.readouterr().out


def test_batch_converts_media_files(tmp_path, capsys):
    (tmp_path / "a.mov").write_bytes(b"a")
    (tmp_path / "b.wav").write_bytes(b"b")
    (tmp_path / "notes.txt").write_bytes(b"not media")

    with patch("umc.cli.convert_media") as mock_convert:
        result = main(["batch", str(tmp_path), "--to", "mp3"])

    assert result == 0
    targets = [call.args[1] for call in mock_convert.call_args_list]
    assert targets == [str(tmp_path / "a.mp3"), str(tmp_path / "b.mp3")]
    assert "2 converted, 0 skipped, 0 failed" in capsys.readouterr().out


def test_batch_output_dir_is_created(tmp_path):
    (tmp_path / "a.mov").write_bytes(b"a")
    output_dir = tmp_path / "converted"

    with patch("umc.cli.convert_media") as mock_convert:
        main(["batch", str(tmp_path), "--to", "mp4", "--output-dir", str(output_dir)])

    assert output_dir.is_dir()
    assert mock_convert.call_args.args[1] == str(output_dir / "a.mp4")


def test_batch_skips_existing_outputs(tmp_path, capsys):
    (tmp_path / "a.mov").write_bytes(b"a")
    (tmp_path / "a.mp3").write_bytes(b"done")
    (tmp_path / "b.mov").write_bytes(b"b")

    with patch("umc.cli.convert_media") as mock_convert:
        result = main(["batch", str(tmp_path), "--to", "mp3"])

    assert result == 0
    # a.mp3 is already an MP3, so it is neither converted nor re-encoded.
    assert [call.args[0] for call in mock_convert.call_args_list] == [str(tmp_path / "b.mov")]
    assert "1 converted, 1 skipped, 0 failed" in capsys.readouterr().out


def test_batch_same_format_with_output_dir(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"a")
    output_dir = tmp_path / "small"

    with patch("umc.cli.convert_media") as mock_convert:
        main(["batch", str(tmp_path), "--to", "mp4", "--preset", "small", "-o", str(output_dir)])

    assert mock_convert.call_args.args[1] == str(output_dir / "a.mp4")


def test_batch_continues_after_failure(tmp_path, capsys):
    (tmp_path / "a.mov").write_bytes(b"a")
    (tmp_path / "b.mov").write_bytes(b"b")

    with patch(
        "umc.cli.convert_media",
        side_effect=[ConversionError("broken file"), None],
    ):
        result = main(["batch", str(tmp_path), "--to", "mp4"])

    assert result == 1
    captured = capsys.readouterr()
    assert "1 converted, 0 skipped, 1 failed" in captured.out
    assert "a.mov" in captured.err


def test_batch_stops_when_cancelled(tmp_path):
    (tmp_path / "a.mov").write_bytes(b"a")
    (tmp_path / "b.mov").write_bytes(b"b")

    with patch(
        "umc.cli.convert_media",
        side_effect=ConversionCancelled("Conversion cancelled."),
    ) as mock_convert:
        result = main(["batch", str(tmp_path), "--to", "mp4"])

    assert result == 130
    assert mock_convert.call_count == 1


def test_batch_rejects_unknown_format(tmp_path, capsys):
    assert main(["batch", str(tmp_path), "--to", "xyz"]) == 1
    assert "Unsupported output format" in capsys.readouterr().err


def test_batch_missing_folder(tmp_path, capsys):
    assert main(["batch", str(tmp_path / "nope"), "--to", "mp4"]) == 1
    assert "Folder does not exist" in capsys.readouterr().err


def test_batch_skips_incompatible_files(tmp_path, capsys):
    (tmp_path / "a.mov").write_bytes(b"a")
    (tmp_path / "song.wav").write_bytes(b"b")

    with patch(
        "umc.cli.convert_media",
        side_effect=[None, IncompatibleInputError("The input file has no video")],
    ):
        result = main(["batch", str(tmp_path), "--to", "mp4"])

    assert result == 0
    assert "1 converted, 1 skipped, 0 failed" in capsys.readouterr().out

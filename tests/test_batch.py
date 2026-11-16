"""Tests for output naming and folder scanning."""

from pathlib import Path

import pytest

from umc.core.batch import default_output_path, find_media_files, is_format_name


@pytest.mark.parametrize("value", ["mp3", "MP4", ".jpg", "webm"])
def test_is_format_name(value):
    assert is_format_name(value)


@pytest.mark.parametrize("value", ["out.mp3", "folder/mp3", "xyz", "avi"])
def test_is_not_format_name(value):
    assert not is_format_name(value)


def test_default_output_path_changes_extension(tmp_path):
    assert default_output_path(tmp_path / "clip.mov", "mp4") == tmp_path / "clip.mp4"


def test_default_output_path_never_reuses_input(tmp_path):
    assert default_output_path(tmp_path / "clip.mp4", "mp4") == tmp_path / "clip-converted.mp4"


def test_default_output_path_uses_output_dir(tmp_path):
    out = tmp_path / "out"
    assert default_output_path(Path("clip.mp4"), ".mp4", out) == out / "clip.mp4"


def test_find_media_files(tmp_path):
    for name in [
        "b.MP4",
        "a.wav",
        "notes.txt",
        "c.avi",
        "c-converted.mp4",
        "d.umc-partial.mp4",
    ]:
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "sub.mp4").mkdir()

    names = [path.name for path in find_media_files(tmp_path)]

    assert names == ["a.wav", "b.MP4", "c.avi"]

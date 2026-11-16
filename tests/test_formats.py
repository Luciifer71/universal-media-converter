"""Tests for media format detection."""

import pytest

from umc.core.formats import detect_media_type, normalize_extension


@pytest.mark.parametrize(
    ("filename", "media_type"),
    [
        ("video.mp4", "video"),
        ("video.mkv", "video"),
        ("video.mov", "video"),
        ("video.webm", "video"),
        ("VIDEO.MP4", "video"),
        ("song.mp3", "audio"),
        ("song.wav", "audio"),
        ("song.flac", "audio"),
        ("song.aac", "audio"),
        ("song.m4a", "audio"),
        ("song.ogg", "audio"),
        ("song.opus", "audio"),
        ("photo.jpg", "image"),
        ("photo.jpeg", "image"),
        ("photo.png", "image"),
        ("photo.webp", "image"),
        ("photo.bmp", "image"),
    ],
)
def test_detect_supported_formats(filename, media_type):
    assert detect_media_type(filename) == media_type


@pytest.mark.parametrize("filename", ["file.avi", "file.txt", "file"])
def test_detect_rejects_unsupported_formats(filename):
    with pytest.raises(ValueError, match="Unsupported output format"):
        detect_media_type(filename)


@pytest.mark.parametrize("value", ["mp3", "MP3", ".mp3", "song.mp3", " mp3 "])
def test_normalize_extension(value):
    assert normalize_extension(value) == ".mp3"

# Changelog

All notable changes to Universal Media Converter are listed here.
The project follows [Semantic Versioning](https://semver.org/).

## 0.2.0

First public release.

### Added

- Original quality by default: streams are copied untouched when possible,
  lossless formats stay lossless, otherwise maximum-quality settings are used.
  Every conversion reports the resulting quality.
- Automatic fallback to re-encoding when a direct copy fails.
- Audio conversion: MP3, WAV, FLAC, AAC, M4A, OGG and Opus.
- Image conversion: JPG, PNG, WebP and BMP, including frames from videos
  and embedded album art.
- `--at` to choose the moment of a video saved as an image.
- MKV output keeps every audio, subtitle and attachment track.
- More video formats: MKV, MOV and WebM.
- `umc batch` to convert whole folders, `umc formats` to list formats and presets.
- Format shortcut: `umc convert video.mov mp3`.
- `--overwrite`, safe temporary files and clean Ctrl+C cancellation.
- Install instructions for FFmpeg on Windows, macOS and Linux.
- MIT license.

## 0.1.0

- Initial development version: MP4 video conversion with presets and `umc info`.

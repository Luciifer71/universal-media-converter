# Universal Media Converter

A Windows-first, open-source media conversion toolkit built with Python.

## Status
Early development (v0.1.0-dev).

## Project Goals
- Video, audio and image conversion
- Simple command-line interface
- Compression and quality presets
- Batch processing
- Hardware acceleration
- Future Windows desktop application

## Technology
- Python
- FFmpeg (planned media-processing backend)

## Development
This repository is currently in its initial development phase.

## Development checks
Run `python -m ruff check src tests` and `python -m pytest -q` before committing changes.

## Supported Formats

UMC is being developed to support the following media formats:

| Media Type | Formats |
|---|---|
| Video | MP4 |
| Audio | MP3, WAV, FLAC, AAC, OGG |
| Images | JPG, JPEG, PNG, WebP, BMP |

Format support and conversion capabilities are still under active development.

# Universal Media Converter (UMC)

A simple, open-source command-line media converter for **Windows, macOS and Linux**.

Convert video, audio and images with one short command. There are no codecs,
bitrates or FFmpeg options to learn: name the file you want, and UMC picks
the settings for you. **By default it keeps the original quality.**

```bash
umc convert holiday.mov holiday.mp4
```

> **Status:** early development (v0.1.0). The commands below work and are tested,
> but options may still change before the first stable release.

## Features

- **Video:** convert to MP4, MKV, MOV or WebM.
- **Audio:** convert to MP3, WAV, FLAC, AAC, M4A, OGG or Opus, or extract the soundtrack from a video.
- **Images:** convert between JPG, PNG, WebP and BMP, or save any moment of a video as a picture.
- **Original quality by default:** copies audio/video untouched whenever possible,
  otherwise uses lossless or maximum-quality settings. Every conversion tells you
  exactly what happened to the quality.
- **Smaller-file presets** when you want them: `high`, `balanced` and `small`.
- **Batch conversion:** convert a whole folder with one command.
- **Safe by default:** never overwrites a file unless you ask, and never leaves
  half-written files behind when a conversion fails or you press Ctrl+C.
- **Live progress bar** while converting.
- Built on [FFmpeg](https://ffmpeg.org/), the engine used by most video tools.

## Installation

You need **Python 3.10 or newer** and **FFmpeg**.

### 1. Install FFmpeg

| System  | Command |
|---------|---------|
| Windows | `winget install Gyan.FFmpeg` |
| macOS   | `brew install ffmpeg` (needs [Homebrew](https://brew.sh/)) |
| Ubuntu / Debian | `sudo apt install ffmpeg` |
| Fedora  | `sudo dnf install ffmpeg` (from RPM Fusion) |
| Arch    | `sudo pacman -S ffmpeg` |

Open a **new** terminal afterwards and check that it works:

```bash
ffmpeg -version
```

### 2. Install UMC

UMC is not on PyPI yet, so install it directly from GitHub.

**Windows (PowerShell):**

```powershell
py -m pip install git+https://github.com/Luciifer71/universal-media-converter.git
```

**macOS / Linux:**

```bash
python3 -m pip install --user git+https://github.com/Luciifer71/universal-media-converter.git
```

If your Linux distribution blocks system-wide `pip` installs, use
[pipx](https://pipx.pypa.io/) instead:

```bash
pipx install git+https://github.com/Luciifer71/universal-media-converter.git
```

Then check it:

```bash
umc --version
```

> If the terminal says `umc` is not recognised, run UMC through Python instead:
> `python -m umc ...` (Windows: `py -m umc ...`). Every command below works the same way.

## Usage

### Convert a file

The output format is chosen from the output file's extension.

```bash
umc convert input.mov output.mp4        # video -> MP4
umc convert input.mp4 output.webm       # video -> WebM for the web
umc convert song.wav song.mp3           # audio -> MP3
umc convert song.flac song.m4a          # audio -> M4A (AAC), good for Apple devices
umc convert video.mp4 soundtrack.mp3    # extract the audio from a video
umc convert video.mp4 thumbnail.jpg     # save the first frame as an image
umc convert video.mp4 thumb.png --at 1:30  # save the frame at 1 min 30 s
umc convert photo.png photo.webp        # image -> WebP
umc convert album.mp3 cover.jpg         # extract embedded album art
```

### Shortcut: just name the format

Leave out the file name and UMC saves the result next to the original:

```bash
umc convert video.mov mp4     # creates video.mp4
umc convert video.mov mp3     # creates video.mp3
umc convert photo.png jpg     # creates photo.jpg
```

If the output would have the same name as the input (for example `video.mp4` to `mp4`),
UMC creates `video-converted.mp4` instead. It never overwrites your original.

### Quality: original by default

By default UMC keeps the quality of your original file. After each conversion it
prints a `Quality:` line so you always know what happened:

```text
Quality: identical to the original (copied without re-encoding)
```

How it works:

1. **Copy when possible (zero loss, very fast).** If the new format can hold the
   original audio/video as they are, UMC copies them without re-encoding. For
   example: phone videos (MOV) to MP4 or MKV, including iPhone HDR/HEVC video;
   the AAC soundtrack of a video to M4A; MP3 album art to JPG.
2. **Lossless when the format allows it.** FLAC, WAV, PNG, BMP and WebP are saved
   with no loss at all. M4A from a lossless source (WAV, FLAC) uses Apple Lossless.
   WAV keeps 24-bit audio as 24-bit.
3. **Maximum quality otherwise.** Some formats always compress (JPG, MP3, AAC,
   OGG, Opus), and some conversions must re-encode the video (for example
   WebM to MP4). UMC then uses settings where the difference is not visible or
   audible: H.264 at CRF 16, MP3 at 320 kbps, AAC at 256-320 kbps, JPG at maximum
   quality. It prints a note suggesting a lossless format if you need one.
4. **Automatic fallback.** If a direct copy fails on an unusual file, UMC
   re-encodes at maximum quality instead of giving up.

Things that can't be kept, and UMC tells you when they happen:

- Saving 10-bit/HDR video as WebM converts it to standard colour. Use MP4, MOV or MKV to keep HDR.
- JPG cannot store transparency. Use PNG or WebP.

### Smaller files with presets

```bash
umc convert input.mov output.mp4 --preset high
umc convert input.mov output.mp4 --preset balanced
umc convert input.mov output.mp4 --preset small
```

| Preset     | What it does |
|------------|--------------|
| `original` | **The default.** Keeps the original quality (see above). |
| `high`     | Very high quality, smaller than the original. |
| `balanced` | Good quality and much smaller files. |
| `small`    | Smallest files, lower quality, faster. |
| `copy`     | Video only. Changes the container without re-encoding, and fails if the streams don't fit. `original` does this automatically, so you rarely need it. |

What the presets mean for each format:

| Output | high | balanced | small |
|---|---|---|---|
| MP4 / MKV / MOV (H.264 + AAC) | CRF 18, 192k audio | CRF 23, 128k audio | CRF 28, 96k audio |
| WebM (VP9 + Opus) | CRF 24, 160k audio | CRF 32, 128k audio | CRF 40, 80k audio |
| MP3 | 320 kbps | 192 kbps | 128 kbps |
| AAC / M4A | 256 kbps | 192 kbps | 128 kbps |
| OGG (Vorbis) | quality 8 | quality 5 | quality 3 |
| Opus | 160 kbps | 128 kbps | 64 kbps |
| JPG | very high | high | medium |
| WebP | quality 95 | quality 80 | quality 60 |
| WAV, FLAC, PNG, BMP | lossless; presets make no difference | | |

### Save a picture from a video

```bash
umc convert video.mp4 thumbnail.jpg              # first frame
umc convert video.mp4 thumbnail.jpg --at 5       # at 5 seconds
umc convert video.mp4 thumbnail.png --at 1:30    # at 1 min 30 s, lossless PNG
umc convert movie.mkv poster.jpg --at 1:02:03.5  # at 1 h 2 min 3.5 s
umc batch ./videos --to jpg --at 10              # a picture from every video
```

`--at` accepts seconds (`90`, `90.5`), `minutes:seconds` (`1:30`) or
`hours:minutes:seconds` (`1:02:03`). If the time is past the end of the video,
UMC tells you how long the video is. With still pictures and album art, `--at` is ignored.

### Make a video smaller

```bash
umc convert big-video.mp4 mp4 --preset small     # creates big-video-converted.mp4
```

### Replace an existing file

UMC refuses to overwrite files unless you add `--overwrite` (or `-y`):

```bash
umc convert input.mov output.mp4 --overwrite
```

### Convert a whole folder

```bash
umc batch ./videos --to mp4
umc batch ./music --to mp3 --preset high
umc batch ./photos --to webp
umc batch ./videos --to mp4 --preset small --output-dir ./videos-small
```

- Converts every audio, video and image file directly inside the folder (not subfolders).
- Results are saved next to the originals, or in `--output-dir` (created if needed).
- Files that are already converted, or that have no matching audio/video
  (for example an MP3 when converting to MP4), are skipped.
- One broken file does not stop the rest. A summary is shown at the end.

### Inspect a file

```bash
umc info video.mp4
```

```text
File: /home/you/Videos/video.mp4
Format: QuickTime / MOV
Duration: 5.00 seconds (0:05)
Size: 77.55 KB
Video codec: h264
Resolution: 640x360
Audio codec: aac
Sample rate: 44100 Hz
Channels: 1
```

### Other commands

```bash
umc formats          # list supported formats and presets
umc --help           # list all commands with examples
umc convert --help   # options for one command
umc --version
```

## Supported formats

| Type   | Output formats |
|--------|----------------|
| Video  | MP4, MKV, MOV, WebM |
| Audio  | MP3, WAV, FLAC, AAC, M4A, OGG, Opus |
| Images | JPG / JPEG, PNG, WebP, BMP |

**Input:** almost any audio, video or image file FFmpeg can read, including AVI, WMV,
FLV, M4V, 3GP, MTS, MPG, WMA, AIFF, GIF and TIFF.

## Tips for each operating system

- **File names with spaces:** wrap them in quotes on every system:
  `umc convert "My Holiday.mov" mp4`
- **Windows:** you can drag a file from Explorer into the PowerShell window to paste its full path.
  Paths like `C:\Users\you\Videos\clip.mov` work as-is.
- **macOS:** drag a file from Finder into Terminal to paste its path. `~/Movies/clip.mov` works.
- **Linux:** `~/Videos/clip.mov` and relative paths work as usual.
- **Stop a conversion:** press `Ctrl+C`. The unfinished output file is deleted automatically.

## Troubleshooting

| Problem | Fix |
|---|---|
| `FFmpeg was not found` | Install FFmpeg (see above), then open a **new** terminal. |
| `umc` is not recognised | Use `python -m umc` (Windows: `py -m umc`), or add Python's Scripts folder to PATH. |
| `Output file already exists` | Add `--overwrite`, or choose another name. |
| `copy` preset fails | The original streams don't fit the new container. Leave out `--preset`; the default `original` handles this automatically. |
| `--at ... is past the end` | Pick an earlier time. `umc info FILE` shows the duration. |
| `has no video` / `has no audio` | The input doesn't contain what the output needs (for example converting an MP3 to MP4). |

## Development

```bash
git clone https://github.com/Luciifer71/universal-media-converter.git
cd universal-media-converter
python -m venv .venv
```

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1          # Windows PowerShell
```

```bash
source .venv/bin/activate           # macOS / Linux
```

Install in editable mode with the development tools:

```bash
pip install -e ".[dev]"
```

Run the checks before committing:

```bash
python -m ruff format src tests
python -m ruff check src tests
python -m pytest -q
```

Project layout:

```text
src/umc/cli.py            command-line interface
src/umc/core/converter.py FFmpeg conversion engine
src/umc/core/original.py  the default "keep original quality" planner
src/umc/core/presets.py   high/balanced/small/copy presets
src/umc/core/timecode.py  reading times such as 1:30 for --at
src/umc/core/formats.py   supported formats
src/umc/core/batch.py     output naming and folder scanning
src/umc/core/probe.py     media inspection with FFprobe
tests/                    automated tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Roadmap

- Hardware-accelerated encoding (NVIDIA, Intel, AMD)
- Publishing to PyPI (`pip install universal-media-converter`)
- Standalone Windows executable
- Desktop app

# Universal Media Converter

<sub>convert. keep quality. stay simple.</sub>

One short command to convert video, audio and images.
No codecs, bitrates or FFmpeg flags to learn. Name the file you want, and UMC does the rest,
keeping the original quality by default.

**v0.2 / beta**

Windows, macOS and Linux. Free and open source under the MIT license.

```bash
umc convert holiday.mov mp4
```

```text
Input:  holiday.mov
Output: holiday.mp4
Quality: identical to the original (copied without re-encoding)
Conversion completed: C:\Users\you\Videos\holiday.mp4 (2.25 MB)
```

---

### `~/capabilities`

- **Video:** convert to MP4, MKV, MOV or WebM.
- **Audio:** convert to MP3, WAV, FLAC, AAC, M4A, OGG or Opus, or pull the soundtrack out of a video.
- **Images:** convert to JPG, PNG, WebP or BMP, grab any moment of a video, or extract album art.
- **Original quality by default:** copies untouched when it can, stays lossless where the format allows, and tells you exactly what happened.
- **Every track kept** in MKV: all audio languages, subtitles and fonts.
- **Whole folders** in one command.
- **Safe:** never overwrites without asking, never leaves broken half-written files behind.

### `~/install`

**1 · FFmpeg** (the engine UMC uses)

| System | Command |
|---|---|
| Windows | `winget install Gyan.FFmpeg` |
| macOS | `brew install ffmpeg` (needs [Homebrew](https://brew.sh/)) |
| Ubuntu / Debian | `sudo apt install ffmpeg` |
| Fedora | `sudo dnf install ffmpeg` (from RPM Fusion) |
| Arch | `sudo pacman -S ffmpeg` |

Open a **new** terminal and check it with `ffmpeg -version`.

**2 · UMC** (needs Python 3.10 or newer)

| System | Command |
|---|---|
| Windows (PowerShell) | `py -m pip install universal-media-converter` |
| macOS / Linux | `pipx install universal-media-converter` |
| macOS / Linux, without pipx | `python3 -m pip install --user universal-media-converter` |

Check it with `umc --version`.

<details>
<summary>Install the latest development version from GitHub</summary>

```bash
pip install git+https://github.com/Luciifer71/universal-media-converter.git
```

</details>

> If the terminal says `umc` is not recognised, use `python -m umc` instead
> (Windows: `py -m umc`). Every command works the same way.

### `~/quickstart`

```bash
umc convert video.mov mp4                 # video → MP4, same quality
umc convert video.mp4 mp3                 # pull the audio out of a video
umc convert video.mp4 thumb.jpg --at 1:30 # picture of the moment at 1 min 30 s
umc convert photo.png webp                # image → WebP, lossless
umc batch ./holiday --to mp4              # convert a whole folder
umc info video.mp4                        # what is inside a file?
```

That's all most people need. The guide below explains everything in detail.

---

### `~/guide`

#### 1 · The basic command

```bash
umc convert INPUT OUTPUT [options]
```

The **output's extension decides the format.** `photo.png → photo.webp` makes a WebP image,
`video.mov → song.mp3` makes an MP3. File names with spaces need quotes:
`umc convert "My Holiday.mov" mp4`.

#### 2 · Where your files are saved

| You type | The new file is saved |
|---|---|
| Only a format: `umc convert D:\Videos\clip.mov mp4` | **next to the original**: `D:\Videos\clip.mp4` |
| A file name: `umc convert clip.mov new.mp4` | in the folder your terminal is currently in |
| A full path: `umc convert clip.mov D:\Exports\new.mp4` | exactly there (the folder must exist) |
| `umc batch FOLDER --to mp4` | next to each original |
| `umc batch FOLDER --to mp4 -o OUT` | inside `OUT` (created if needed) |

- Your original file is **never changed or deleted**.
- If the new name would be the same as the original (`clip.mp4 → mp4`), UMC saves `clip-converted.mp4`.
- Everything happens on your computer. Nothing is uploaded and no internet connection is needed.

#### 3 · Video

```bash
umc convert video.mov video.mp4     # MP4: plays everywhere
umc convert video.mp4 video.mkv     # MKV: keeps every track
umc convert video.mp4 video.webm    # WebM: for websites
umc convert video.avi mp4           # older formats work as input too
```

Phone videos (including iPhone HDR) usually convert to MP4, MOV or MKV **instantly and
without any quality loss**, because UMC copies the video instead of re-encoding it.

#### 4 · Audio

```bash
umc convert video.mp4 mp3           # extract the soundtrack
umc convert video.mp4 m4a           # extract it with no loss (most videos)
umc convert song.wav song.flac      # lossless, about half the size of WAV
umc convert song.flac song.mp3      # for older players and car stereos
umc convert podcast.wav podcast.opus
```

Which format should I pick?

| You want | Use |
|---|---|
| A perfect copy | `.flac` (compressed) or `.wav` (uncompressed) |
| Apple devices, perfect copy | `.m4a` from a WAV/FLAC source (Apple Lossless) |
| Plays on anything | `.mp3` |
| Small files, modern apps | `.opus` or `.m4a` |

#### 5 · Images and thumbnails

```bash
umc convert photo.png photo.webp             # lossless WebP, keeps transparency
umc convert photo.png photo.jpg              # JPG: smaller, no transparency
umc convert video.mp4 thumb.jpg              # first frame of a video
umc convert video.mp4 thumb.jpg --at 5       # frame at 5 seconds
umc convert video.mp4 thumb.png --at 1:30    # frame at 1 min 30 s, lossless PNG
umc convert movie.mkv poster.jpg --at 1:02:03.5
umc convert album.mp3 cover.jpg              # extract the album art, byte for byte
```

`--at` accepts seconds (`90`, `90.5`), `minutes:seconds` (`1:30`) or
`hours:minutes:seconds` (`1:02:03`). If the time is past the end, UMC tells you
how long the video is. For still pictures and album art, `--at` is ignored.

#### 6 · Quality

Without `--preset`, UMC keeps the **original quality**. Every conversion ends with a
`Quality:` line, so you always know what happened:

| You see | Meaning |
|---|---|
| `identical to the original (copied without re-encoding)` | Zero loss. The data was copied as-is. |
| `lossless` | Zero loss. Re-saved in a lossless format. |
| `visually lossless (re-encoded at maximum practical quality)` | Had to re-encode. The difference cannot be seen in normal viewing. |
| `maximum MP3 quality (320 kbps)` and similar | The format always compresses a little. UMC uses its best setting and suggests a lossless one. |

How UMC decides:

1. **Copy** the original audio/video when the new format can hold it (instant, zero loss).
2. Otherwise use a **lossless** encoder if the format has one (FLAC, WAV, PNG, BMP, WebP, Apple Lossless). 24-bit audio stays 24-bit.
3. Otherwise use **maximum quality** (H.264 CRF 16, MP3 320 kbps, AAC 256–320 kbps, best JPG).
4. If a copy fails on an unusual file, UMC **re-encodes automatically** instead of stopping.

Want **smaller files** instead? Pick a preset:

```bash
umc convert big.mp4 mp4 --preset small      # creates big-converted.mp4
```

| Preset | Result |
|---|---|
| `original` | **Default.** Keeps the original quality. |
| `high` | Very high quality, smaller than the original. |
| `balanced` | Good quality, much smaller. Great for sharing. |
| `small` | Smallest files, visible quality loss. |
| `copy` | Strict copy only (video). Fails rather than re-encodes. You rarely need this. |

<details>
<summary>Exact settings behind each preset</summary>

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
| WAV, FLAC, PNG, BMP | lossless | lossless | lossless |

Resolution and frame rate are never changed.

</details>

What a format **can't** keep (UMC prints a note when this happens):

- **JPG** has no transparency. Use PNG or WebP.
- **MP3, AAC, OGG and Opus** always compress slightly. Use FLAC or WAV.
- **WebM** turns 10-bit/HDR video into standard colour. Use MP4, MOV or MKV.
- **MP4, MOV and WebM** hold one video and one audio track. Use MKV for the rest (see below).

#### 7 · Multiple languages and subtitles

Movies and recordings often have several audio languages, subtitles or embedded fonts.

```bash
umc convert movie.mp4 movie.mkv
```

```text
Quality: identical to the original (copied without re-encoding)
Note: Kept all tracks: 1 video track, 2 audio tracks, 1 subtitle track.
```

- **MKV keeps every track** with its language label, for every preset.
- MP4 subtitles are converted to SRT, which MKV supports.
- MP4, MOV and WebM keep the main video and audio, and tell you what was left out.

#### 8 · Whole folders

```bash
umc batch ./videos --to mp4
umc batch ./music --to mp3
umc batch ./photos --to webp
umc batch ./videos --to jpg --at 10                          # a thumbnail of each video
umc batch ./videos --to mp4 --preset small -o ./videos-small # shrink a folder
```

- Converts every media file **directly inside** the folder (not sub-folders).
- Skips files that are already converted or don't fit (an MP3 can't become an MP4).
- Files already in the target format are only re-done when you use `-o` (for example, to shrink them).
- One broken file doesn't stop the rest. You get a summary at the end:

```text
Done: 12 converted, 3 skipped, 0 failed.
```

#### 9 · Look inside a file

```bash
umc info video.mov
```

```text
Format: QuickTime / MOV
Duration: 6.00 seconds (0:06)
Size: 2.25 MB
Video codec: h264
Resolution: 1280x720
Audio codec: aac
Sample rate: 44100 Hz
Channels: 1
```

#### 10 · Safety

- Existing files are never replaced unless you add `--overwrite` (or `-y`).
- UMC writes to a temporary `*.umc-partial.*` file and renames it only when the conversion succeeds.
- Press **Ctrl+C** at any time. The unfinished file is deleted and nothing else is touched.
- If FFmpeg produces an empty file, UMC reports an error instead of saving it.

#### 11 · Every option

| Command | Option | What it does |
|---|---|---|
| `convert` | `INPUT OUTPUT` | Input file, and an output file or just a format (`mp4`) |
| `convert`, `batch` | `-p`, `--preset` | `original` (default), `high`, `balanced`, `small`, `copy` |
| `convert`, `batch` | `--at TIME` | Moment of a video to save as an image |
| `convert`, `batch` | `-y`, `--overwrite` | Replace existing output files |
| `batch` | `FOLDER` | Folder with the files to convert |
| `batch` | `-t`, `--to FORMAT` | Output format, e.g. `mp4`, `mp3`, `jpg` |
| `batch` | `-o`, `--output-dir DIR` | Save results in another folder |
| `info` | `FILE` | Show what is inside a media file |
| `formats` | | List formats and presets |
| | `--help`, `--version` | Help with examples, version number |

#### 12 · Tips for each system

- **Windows:** drag a file from Explorer into PowerShell to paste its full path. Use `py -m umc` if `umc` isn't found.
- **macOS:** drag a file from Finder into Terminal to paste its path. `~/Movies/clip.mov` works.
- **Linux:** `~/Videos/clip.mov` and relative paths work as usual. `pipx` keeps UMC separate from system Python.

---

### `~/formats`

| Type | Output formats |
|---|---|
| Video | MP4, MKV, MOV, WebM |
| Audio | MP3, WAV, FLAC, AAC, M4A, OGG, Opus |
| Images | JPG / JPEG, PNG, WebP, BMP |

**Input:** almost anything FFmpeg can read, including AVI, WMV, FLV, M4V, 3GP, MTS, MPG,
WMA, AIFF, GIF and TIFF.

### `~/troubleshooting`

| Message | Fix |
|---|---|
| `FFmpeg was not found` | Install FFmpeg (see install), then open a **new** terminal. |
| `umc` is not recognised | Use `python -m umc` (Windows: `py -m umc`). |
| `Output file already exists` | Add `--overwrite`, or choose another name. |
| `has no video` / `has no audio` | The input doesn't contain what the output needs (e.g. MP3 → MP4). |
| `--at ... is past the end` | Pick an earlier time. `umc info FILE` shows the length. |
| `Your FFmpeg cannot create WebP images` | Some FFmpeg builds (for example Homebrew's on macOS) leave out WebP. Use `.png`, or install a full FFmpeg build. For `.ogg`, UMC switches to Opus audio automatically. |
| `copy` preset fails | Leave out `--preset`. The default handles this automatically. |
| Anything else | [Open an issue](https://github.com/Luciifer71/universal-media-converter/issues/new/choose) with the command, its output and `umc info` of the file. |

### `~/develop`

```bash
git clone https://github.com/Luciifer71/universal-media-converter.git
cd universal-media-converter
python -m venv .venv
```

Activate it (`.venv\Scripts\Activate.ps1` on Windows, `source .venv/bin/activate` on macOS/Linux), then:

```bash
pip install -e ".[dev]"
python -m ruff check src tests
python -m pytest -q
```

The tests include real FFmpeg conversions and run on Windows, macOS and Linux for every pull request.
See the [contribution guide](https://github.com/Luciifer71/universal-media-converter/blob/main/CONTRIBUTING.md).

### `~/project`

[Changelog](https://github.com/Luciifer71/universal-media-converter/blob/main/CHANGELOG.md) · [Report an issue](https://github.com/Luciifer71/universal-media-converter/issues) · [Contribution guide](https://github.com/Luciifer71/universal-media-converter/blob/main/CONTRIBUTING.md) · [PyPI](https://pypi.org/project/universal-media-converter/)

Next up: hardware-accelerated encoding (NVIDIA, Intel, AMD), a standalone Windows app and a desktop interface.

## License

[MIT](https://github.com/Luciifer71/universal-media-converter/blob/main/LICENSE) © 2026 Krishay Shah.
Free to use, modify and share, including commercially.

UMC uses [FFmpeg](https://ffmpeg.org/), which is installed separately and has its own license.

---

<sub>keep the original.</sub>

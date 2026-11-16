"""Encoding presets for media conversion.

Users only ever pick a preset name. The default, "original", keeps the source
quality and is planned in umc.core.original. This module translates the other
names (high, balanced, small, copy) into FFmpeg settings for each format.
"""

from typing import Literal

PresetName = Literal["original", "high", "balanced", "small", "copy"]

PRESET_NAMES: tuple[str, ...] = ("original", "high", "balanced", "small", "copy")
DEFAULT_PRESET: PresetName = "original"

PRESET_DESCRIPTIONS = {
    "original": "Keep the original quality (default). Copies without re-encoding "
    "when possible, otherwise uses lossless or maximum quality.",
    "high": "Very high quality, smaller than original.",
    "balanced": "Good quality and much smaller files.",
    "small": "Smallest files, lower quality, faster.",
    "copy": "No re-encoding. Very fast and lossless, video only; "
    "the input streams must already suit the output format.",
}

# H.264 + AAC: used for MP4, MKV and MOV. Plays almost everywhere.
VIDEO_PRESETS = {
    "high": {"crf": 18, "speed": "slow", "audio_bitrate": "192k"},
    "balanced": {"crf": 23, "speed": "medium", "audio_bitrate": "128k"},
    "small": {"crf": 28, "speed": "fast", "audio_bitrate": "96k"},
}

# VP9 + Opus: used for WebM (the web-friendly open format).
WEBM_PRESETS = {
    "high": {"crf": 24, "audio_bitrate": "160k"},
    "balanced": {"crf": 32, "audio_bitrate": "128k"},
    "small": {"crf": 40, "audio_bitrate": "80k"},
}

# Lossy audio settings per format. Lossless formats (WAV, FLAC) ignore presets.
AUDIO_PRESETS = {
    ".mp3": {
        "codec": "libmp3lame",
        "high": ["-b:a", "320k"],
        "balanced": ["-b:a", "192k"],
        "small": ["-b:a", "128k"],
    },
    ".aac": {
        "codec": "aac",
        "high": ["-b:a", "256k"],
        "balanced": ["-b:a", "192k"],
        "small": ["-b:a", "128k"],
    },
    ".m4a": {
        "codec": "aac",
        "high": ["-b:a", "256k"],
        "balanced": ["-b:a", "192k"],
        "small": ["-b:a", "128k"],
    },
    ".ogg": {
        "codec": "libvorbis",
        "high": ["-q:a", "8"],
        "balanced": ["-q:a", "5"],
        "small": ["-q:a", "3"],
    },
    ".opus": {
        "codec": "libopus",
        "high": ["-b:a", "160k"],
        "balanced": ["-b:a", "128k"],
        "small": ["-b:a", "64k"],
    },
    ".wav": {"codec": "pcm_s16le"},
    ".flac": {"codec": "flac"},
}

# Image quality settings. PNG and BMP are lossless and ignore presets.
IMAGE_PRESETS = {
    ".jpg": {"high": ["-q:v", "2"], "balanced": ["-q:v", "4"], "small": ["-q:v", "8"]},
    ".jpeg": {"high": ["-q:v", "2"], "balanced": ["-q:v", "4"], "small": ["-q:v", "8"]},
    ".webp": {
        "high": ["-c:v", "libwebp", "-quality", "95"],
        "balanced": ["-c:v", "libwebp", "-quality", "80"],
        "small": ["-c:v", "libwebp", "-quality", "60"],
    },
    ".png": {},
    ".bmp": {},
}


def validate_preset(preset: str) -> None:
    """Raise ValueError if the preset name is unknown."""
    if preset not in PRESET_NAMES:
        raise ValueError(f"Unsupported preset: {preset}. Choose from: {', '.join(PRESET_NAMES)}")


def get_preset_options(preset: PresetName) -> list[str]:
    """Return FFmpeg arguments for H.264/AAC video (MP4, MKV, MOV)."""

    if preset == "copy":
        return ["-c", "copy"]

    if preset not in VIDEO_PRESETS:
        raise ValueError(f"Unsupported preset: {preset}")

    settings = VIDEO_PRESETS[preset]

    return [
        "-c:v",
        "libx264",
        "-crf",
        str(settings["crf"]),
        "-preset",
        str(settings["speed"]),
        # yuv420p keeps the video playable on phones, browsers and older players.
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        str(settings["audio_bitrate"]),
    ]


def reject_original(preset: str) -> None:
    """The original preset depends on the input file; see umc.core.original."""
    if preset == "original":
        raise ValueError("The original preset is planned by umc.core.original.plan_original.")


def get_video_options(extension: str, preset: PresetName) -> list[str]:
    """Return FFmpeg arguments for a video output format."""
    validate_preset(preset)
    reject_original(preset)

    if extension == ".webm":
        if preset == "copy":
            return ["-c", "copy"]

        settings = WEBM_PRESETS[preset]
        return [
            "-c:v",
            "libvpx-vp9",
            "-crf",
            str(settings["crf"]),
            "-b:v",
            "0",
            "-row-mt",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "libopus",
            "-b:a",
            str(settings["audio_bitrate"]),
        ]

    options = get_preset_options(preset)

    if extension in (".mp4", ".mov") and preset != "copy":
        # Lets videos start playing before they are fully downloaded.
        options += ["-movflags", "+faststart"]

    return options


def get_audio_options(extension: str, preset: PresetName) -> list[str]:
    """Return FFmpeg arguments for an audio output format."""
    validate_preset(preset)
    reject_original(preset)

    if preset == "copy":
        raise ValueError(
            "The copy preset is not supported for audio output. "
            "Use high, balanced or small instead."
        )

    settings = AUDIO_PRESETS[extension]
    return ["-vn", "-c:a", settings["codec"], *settings.get(preset, [])]


def get_image_options(extension: str, preset: PresetName) -> list[str]:
    """Return FFmpeg arguments for a still image output format."""
    validate_preset(preset)
    reject_original(preset)

    if preset == "copy":
        raise ValueError(
            "The copy preset is not supported for image output. "
            "Use high, balanced or small instead."
        )

    return [
        # Take the first frame of the first video/image stream only.
        "-map",
        "0:v:0",
        "-frames:v",
        "1",
        "-an",
        # Write a single image file rather than a numbered image sequence.
        "-update",
        "1",
        *IMAGE_PRESETS[extension].get(preset, []),
    ]

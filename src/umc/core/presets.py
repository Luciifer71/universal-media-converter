"""Encoding presets for media conversion."""

from typing import Literal

PresetName = Literal["high", "balanced", "small", "copy"]

DEFAULT_PRESET: PresetName = "balanced"

VIDEO_PRESETS = {
    "high": {
        "crf": 18,
        "speed": "slow",
        "audio_bitrate": "192k",
    },
    "balanced": {
        "crf": 23,
        "speed": "medium",
        "audio_bitrate": "128k",
    },
    "small": {
        "crf": 28,
        "speed": "fast",
        "audio_bitrate": "96k",
    },
}


def get_preset_options(preset: PresetName) -> list[str]:
    """Return FFmpeg encoding arguments for a preset."""

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
        "-c:a",
        "aac",
        "-b:a",
        str(settings["audio_bitrate"]),
    ]

"""Check which encoders the installed FFmpeg has, and adapt when one is missing.

FFmpeg builds differ. For example, some macOS (Homebrew) builds cannot create
Ogg Vorbis audio or WebP images. UMC adapts where a good alternative exists,
and otherwise explains the problem clearly instead of showing FFmpeg's error.
"""

import functools
import itertools
import subprocess

from umc.core.original import EncodingPlan

ENCODER_NAMES = {
    "libx264": "H.264 video (MP4, MKV, MOV)",
    "libvpx-vp9": "VP9 video (WebM)",
    "libopus": "Opus audio",
    "libvorbis": "Ogg Vorbis audio",
    "libmp3lame": "MP3 audio",
    "libwebp": "WebP images",
    "aac": "AAC audio",
    "alac": "Apple Lossless audio",
    "flac": "FLAC audio",
}

# Ogg Vorbis quality (-q:a) mapped to a similar Opus bitrate.
VORBIS_QUALITY_TO_OPUS = {"10": "256k", "8": "192k", "5": "128k", "3": "96k"}


@functools.cache
def available_encoders(ffmpeg: str) -> frozenset[str] | None:
    """Names of the encoders this FFmpeg supports, or None if unknown."""
    try:
        result = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    names = set()
    listing_started = False

    for line in result.stdout.splitlines():
        if line.strip().startswith("---"):
            listing_started = True
            continue

        parts = line.split()
        if listing_started and len(parts) >= 2:
            names.add(parts[1])

    return frozenset(names) or None


def requested_encoders(options: list[str]) -> set[str]:
    """Encoders named in FFmpeg options such as '-c:a libopus' (copy excluded)."""
    encoders = set()

    for flag, value in itertools.pairwise(options):
        if (flag == "-c" or flag.startswith("-c:")) and value != "copy":
            encoders.add(value)

    return encoders


def use_opus_instead_of_vorbis(options: list[str]) -> list[str]:
    """Swap '-c:a libvorbis -q:a N' for '-c:a libopus -b:a <similar bitrate>'."""
    result = []
    skip_next = False

    for index, value in enumerate(options):
        if skip_next:
            skip_next = False
            continue

        if value == "libvorbis":
            result.append("libopus")
        elif value == "-q:a" and "libvorbis" in options:
            quality = options[index + 1] if index + 1 < len(options) else ""
            result += ["-b:a", VORBIS_QUALITY_TO_OPUS.get(quality, "160k")]
            skip_next = True
        else:
            result.append(value)

    return result


def adapt_to_encoders(plan: EncodingPlan, encoders: frozenset[str] | None) -> EncodingPlan:
    """Replace encoders this FFmpeg lacks with a good alternative, where one exists."""
    if encoders is None:
        return plan

    options = plan.options
    notes = list(plan.notes)
    quality = plan.quality

    if (
        "libvorbis" in requested_encoders(options)
        and "libvorbis" not in encoders
        and "libopus" in encoders
    ):
        options = use_opus_instead_of_vorbis(options)
        quality = quality.replace("Ogg Vorbis", "Opus")
        notes.append(
            "Your FFmpeg has no Vorbis encoder, so this .ogg file uses Opus audio "
            "(same quality or better; plays in modern players)."
        )

    fallback = adapt_to_encoders(plan.fallback, encoders) if plan.fallback else None
    return EncodingPlan(options=options, quality=quality, notes=notes, fallback=fallback)


def missing_encoder_message(
    plan: EncodingPlan, encoders: frozenset[str] | None, extension: str
) -> str | None:
    """A friendly error if the plan needs an encoder this FFmpeg lacks."""
    if encoders is None:
        return None

    missing = sorted(requested_encoders(plan.options) - encoders)

    if not missing:
        return None

    names = ", ".join(ENCODER_NAMES.get(name, name) for name in missing)
    suggestion = " Try .png instead." if extension == ".webp" else ""

    return (
        f"Your FFmpeg cannot create {names}: it was built without the "
        f"'{missing[0]}' encoder.{suggestion}\n"
        "To use this format, install a full FFmpeg build that includes it "
        "(see https://ffmpeg.org/download.html)."
    )

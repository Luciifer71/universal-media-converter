"""The "original" preset: keep the quality of the source file.

Strategy, in order of preference:

1. Copy the original audio/video data unchanged when the output format can
   hold it. This is instant and has zero quality loss.
2. Otherwise use a lossless encoder when the output format has one
   (FLAC, WAV, PNG, BMP, lossless WebP, ALAC in M4A).
3. Otherwise encode at visually/audibly transparent quality, while keeping the
   file playable on phones, browsers and TVs.

Whenever a copy is attempted, a fallback plan that re-encodes is included, so
unusual files still convert instead of failing.
"""

from dataclasses import dataclass, field

# Video codecs that each container can hold and that common players support.
VIDEO_COPY_SUPPORT = {
    ".mp4": {"h264", "hevc", "av1", "mpeg4"},
    ".mov": {"h264", "hevc", "mpeg4", "prores", "mjpeg"},
    ".webm": {"vp8", "vp9", "av1"},
}

# Audio codecs that each container can hold.
AUDIO_IN_VIDEO_COPY_SUPPORT = {
    ".mp4": {"aac", "mp3", "alac", "ac3", "eac3"},
    ".mov": {"aac", "mp3", "alac", "ac3", "pcm_s16le", "pcm_s24le"},
    ".webm": {"opus", "vorbis"},
}

# Audio codecs that each audio format can hold unchanged.
AUDIO_COPY_SUPPORT = {
    ".mp3": {"mp3"},
    ".aac": {"aac"},
    ".m4a": {"aac", "alac"},
    ".ogg": {"vorbis", "opus", "flac"},
    ".opus": {"opus"},
    ".flac": {"flac"},
    ".wav": {"pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le", "pcm_u8"},
}

LOSSLESS_AUDIO_CODECS = {"flac", "alac", "wavpack", "ape", "truehd", "mlp", "tta"}

IMAGE_CODECS = {".jpg": "mjpeg", ".jpeg": "mjpeg", ".png": "png", ".webp": "webp", ".bmp": "bmp"}

SAME_AS_ORIGINAL = "identical to the original (copied without re-encoding)"


@dataclass
class EncodingPlan:
    """FFmpeg options for one conversion attempt, plus a plain-English summary."""

    options: list[str]
    quality: str
    notes: list[str] = field(default_factory=list)
    fallback: "EncodingPlan | None" = None


def find_stream(metadata: dict | None, kind: str, include_cover: bool = False) -> dict | None:
    """Return the first audio or video stream, or None."""
    for stream in (metadata or {}).get("streams", []):
        if stream.get("codec_type") != kind:
            continue

        if (
            kind == "video"
            and not include_cover
            and stream.get("disposition", {}).get("attached_pic")
        ):
            continue

        return stream

    return None


def is_lossless_audio(stream: dict | None) -> bool:
    """True for PCM, FLAC, ALAC and other lossless audio codecs."""
    if stream is None:
        return False

    codec = stream.get("codec_name", "")
    return codec.startswith("pcm_") or codec in LOSSLESS_AUDIO_CODECS


def bit_depth(stream: dict | None) -> int:
    """Best guess at the audio bit depth (16 when unknown)."""
    for key in ("bits_per_raw_sample", "bits_per_sample"):
        try:
            value = int((stream or {}).get(key) or 0)
        except (TypeError, ValueError):
            continue

        if value:
            return value

    return 16


def bitrate_kbps(stream: dict | None) -> int | None:
    """Audio bitrate in kbps, if known."""
    try:
        return int((stream or {}).get("bit_rate")) // 1000
    except (TypeError, ValueError):
        return None


def is_high_bit_depth_video(stream: dict | None) -> bool:
    """True for 10-bit or 12-bit video (often HDR)."""
    pixel_format = (stream or {}).get("pix_fmt", "")
    return any(depth in pixel_format for depth in ("p10", "p12", "p16"))


# ---------------------------------------------------------------- video ----


def encode_video_options(extension: str, video: dict | None) -> tuple[list[str], list[str]]:
    """Visually lossless video encoding settings, and any notes for the user."""
    notes = []

    if is_high_bit_depth_video(video):
        notes.append(
            "The source is 10-bit (possibly HDR) video. It is converted to standard 8-bit "
            "colour so it plays everywhere; save it as .mkv or .mov to keep it unchanged."
        )

    if extension == ".webm":
        options = ["-c:v", "libvpx-vp9", "-crf", "18", "-b:v", "0", "-row-mt", "1"]
    else:
        options = ["-c:v", "libx264", "-crf", "16", "-preset", "medium"]

    return [*options, "-pix_fmt", "yuv420p"], notes


def encode_audio_in_video_options(extension: str, audio: dict | None) -> list[str]:
    """Transparent-quality audio settings for a video file."""
    if extension == ".webm":
        return ["-c:a", "libopus", "-b:a", "192k"]

    # AAC at 256-320 kbps is indistinguishable from the source for listeners
    # and, unlike lossless audio, plays in every browser and phone.
    source_rate = bitrate_kbps(audio)
    bitrate = "320k" if is_lossless_audio(audio) or (source_rate or 0) > 256 else "256k"
    return ["-c:a", "aac", "-b:a", bitrate]


def plan_video(extension: str, metadata: dict | None) -> EncodingPlan:
    """Plan an original-quality video conversion."""
    video = find_stream(metadata, "video")
    audio = find_stream(metadata, "audio")
    video_codec = (video or {}).get("codec_name")
    audio_codec = (audio or {}).get("codec_name")

    # MKV can hold practically anything, so it can always copy.
    can_copy_video = video is not None and (
        extension == ".mkv" or video_codec in VIDEO_COPY_SUPPORT[extension]
    )
    can_copy_audio = audio is not None and (
        extension == ".mkv" or audio_codec in AUDIO_IN_VIDEO_COPY_SUPPORT[extension]
    )

    encoded_video, video_notes = encode_video_options(extension, video)
    encoded_audio = encode_audio_in_video_options(extension, audio) if audio else []
    extra = ["-movflags", "+faststart"] if extension in (".mp4", ".mov") else []

    full_encode = EncodingPlan(
        options=[*encoded_video, *encoded_audio, *extra],
        quality="visually lossless (re-encoded at maximum practical quality)",
        notes=video_notes,
    )

    if not can_copy_video:
        return full_encode

    copied_video = ["-c:v", "copy"]

    if video_codec == "hevc" and extension in (".mp4", ".mov"):
        # Needed for HEVC (H.265) videos to play on Apple devices.
        copied_video += ["-tag:v", "hvc1"]

    if audio is None or can_copy_audio:
        return EncodingPlan(
            options=[*copied_video, *(["-c:a", "copy"] if audio else []), *extra],
            quality=SAME_AS_ORIGINAL,
            fallback=full_encode,
        )

    return EncodingPlan(
        options=[*copied_video, *encoded_audio, *extra],
        quality="video identical to the original; audio re-encoded at transparent quality",
        fallback=full_encode,
    )


# ---------------------------------------------------------------- audio ----


def encode_audio_options(extension: str, audio: dict | None) -> tuple[list[str], str, list[str]]:
    """Best-quality audio settings: (options, quality summary, notes)."""
    lossy_note = (
        f"{extension.lstrip('.').upper()} always removes a little detail. "
        "Use .flac or .wav for a perfect copy."
    )

    if extension == ".flac":
        return ["-c:a", "flac"], "lossless", []

    if extension == ".wav":
        codec = "pcm_s24le" if is_lossless_audio(audio) and bit_depth(audio) > 16 else "pcm_s16le"
        return ["-c:a", codec], "lossless", []

    if extension == ".m4a" and is_lossless_audio(audio):
        return ["-c:a", "alac"], "lossless (Apple Lossless)", []

    if extension == ".mp3":
        return (
            ["-c:a", "libmp3lame", "-b:a", "320k"],
            "maximum MP3 quality (320 kbps)",
            [lossy_note],
        )

    if extension in (".aac", ".m4a"):
        return ["-c:a", "aac", "-b:a", "320k"], "maximum AAC quality (320 kbps)", [lossy_note]

    if extension == ".ogg":
        return ["-c:a", "libvorbis", "-q:a", "10"], "maximum Ogg Vorbis quality", [lossy_note]

    # .opus
    return ["-c:a", "libopus", "-b:a", "256k"], "transparent Opus quality (256 kbps)", [lossy_note]


def plan_audio(extension: str, metadata: dict | None) -> EncodingPlan:
    """Plan an original-quality audio conversion."""
    audio = find_stream(metadata, "audio")
    options, quality, notes = encode_audio_options(extension, audio)
    full_encode = EncodingPlan(options=["-vn", *options], quality=quality, notes=notes)

    if audio is not None and audio.get("codec_name") in AUDIO_COPY_SUPPORT[extension]:
        return EncodingPlan(
            options=["-vn", "-c:a", "copy"],
            quality=SAME_AS_ORIGINAL,
            fallback=full_encode,
        )

    return full_encode


# ---------------------------------------------------------------- image ----


def encode_image_options(extension: str) -> tuple[list[str], str, list[str]]:
    """Best-quality image settings: (options, quality summary, notes)."""
    if extension in (".jpg", ".jpeg"):
        return (
            ["-q:v", "1", "-qmin", "1"],
            "maximum JPG quality",
            ["JPG always compresses a little. Use .png for a pixel-perfect copy."],
        )

    if extension == ".webp":
        return ["-c:v", "libwebp", "-lossless", "1"], "lossless", []

    return [], "lossless", []  # PNG and BMP are always lossless


def plan_image(extension: str, metadata: dict | None, at: float | None = None) -> EncodingPlan:
    """Plan an original-quality image conversion."""
    picture = find_stream(metadata, "video", include_cover=True)
    base = ["-map", "0:v:0", "-frames:v", "1", "-an", "-update", "1"]
    options, quality, notes = encode_image_options(extension)
    full_encode = EncodingPlan(options=[*base, *options], quality=quality, notes=notes)

    # A picture already stored in the target format (e.g. JPG album art) can be
    # copied byte for byte.
    if at is None and picture is not None and picture.get("codec_name") == IMAGE_CODECS[extension]:
        return EncodingPlan(
            options=[*base, "-c:v", "copy"],
            quality=SAME_AS_ORIGINAL,
            fallback=full_encode,
        )

    return full_encode


def plan_original(
    media_type: str,
    extension: str,
    metadata: dict | None,
    at: float | None = None,
) -> EncodingPlan:
    """Plan a conversion that keeps the original quality."""
    if media_type == "audio":
        return plan_audio(extension, metadata)

    if media_type == "image":
        return plan_image(extension, metadata, at)

    return plan_video(extension, metadata)

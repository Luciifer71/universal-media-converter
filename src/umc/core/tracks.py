"""Keep every track (all audio languages, subtitles, fonts) when saving MKV.

MP4, MOV and WebM keep only the main video and audio track, which is what
phones, browsers and TVs expect. MKV is designed for multi-track files, so it
keeps everything.
"""

from umc.core.original import EncodingPlan

# Subtitle formats MKV can store unchanged.
MKV_SUBTITLE_COPY = {
    "subrip",
    "srt",
    "ass",
    "ssa",
    "webvtt",
    "hdmv_pgs_subtitle",
    "dvd_subtitle",
    "dvb_subtitle",
}

# Text subtitles that must be converted (e.g. MP4/MOV subtitles) to SRT for MKV.
MKV_SUBTITLE_TO_SRT = {"mov_text", "text", "eia_608", "microdvd", "subviewer", "jacosub"}


def streams_of(metadata: dict | None, kind: str) -> list[dict]:
    """All streams of one kind: video (excluding album art), audio, subtitle, attachment."""
    result = []

    for stream in (metadata or {}).get("streams", []):
        if stream.get("codec_type") != kind:
            continue

        if kind == "video" and stream.get("disposition", {}).get("attached_pic"):
            continue

        result.append(stream)

    return result


def subtitle_options(metadata: dict | None) -> tuple[list[str], int, int]:
    """FFmpeg options for the subtitles MKV can hold: (options, kept, skipped)."""
    options = []
    kept = 0
    skipped = 0

    for index, stream in enumerate(streams_of(metadata, "subtitle")):
        codec = stream.get("codec_name", "")

        if codec in MKV_SUBTITLE_COPY:
            action = "copy"
        elif codec in MKV_SUBTITLE_TO_SRT:
            action = "srt"
        else:
            skipped += 1
            continue

        options += ["-map", f"0:s:{index}", f"-c:s:{kept}", action]
        kept += 1

    return options, kept, skipped


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def keep_all_tracks(plan: EncodingPlan, metadata: dict | None) -> EncodingPlan:
    """Extend a video plan so an MKV output keeps every track of the source."""
    video_count = len(streams_of(metadata, "video"))
    audio_count = len(streams_of(metadata, "audio"))
    attachments = streams_of(metadata, "attachment")
    subtitles, kept_subs, skipped_subs = subtitle_options(metadata)

    base_maps = ["-map", "0:V?", "-map", "0:a?"]
    attachment_options = ["-map", "0:t?", "-c:t", "copy"] if attachments else []

    summary = [plural(video_count, "video track"), plural(audio_count, "audio track")]
    if kept_subs:
        summary.append(plural(kept_subs, "subtitle track"))
    track_note = []
    if audio_count > 1 or kept_subs or attachments:
        track_note = ["Kept all tracks: " + ", ".join(summary) + "."]

    skipped_note = []
    if skipped_subs:
        lost = plural(skipped_subs, "subtitle track")
        skipped_note = [f"{lost} could not be kept: MKV cannot store their format."]

    def extend(current: EncodingPlan | None) -> EncodingPlan | None:
        if current is None:
            return None

        return EncodingPlan(
            options=[*base_maps, *subtitles, *attachment_options, *current.options],
            quality=current.quality,
            notes=[*current.notes, *track_note, *skipped_note],
            fallback=extend(current.fallback),
        )

    extended = extend(plan)
    assert extended is not None

    if not (subtitles or attachment_options):
        return extended

    # Last resort: if a subtitle or attachment cannot be written, convert
    # without them rather than failing.
    final = plan
    while final.fallback is not None:
        final = final.fallback

    without_extras = EncodingPlan(
        options=[*base_maps, *final.options],
        quality=final.quality,
        notes=[*final.notes, "Subtitles and attachments could not be kept and were left out."],
    )

    last = extended
    while last.fallback is not None:
        last = last.fallback
    last.fallback = without_extras

    return extended


def dropped_tracks_note(metadata: dict | None, extension: str) -> str | None:
    """Explain which tracks a single-track container (MP4, MOV, WebM) leaves out."""
    extra_audio = max(0, len(streams_of(metadata, "audio")) - 1)
    subtitles = len(streams_of(metadata, "subtitle"))

    if not extra_audio and not subtitles:
        return None

    parts = []
    if extra_audio:
        parts.append(plural(extra_audio, "extra audio track"))
    if subtitles:
        parts.append(plural(subtitles, "subtitle track"))

    return (
        f"{extension.lstrip('.').upper()} keeps the main video and audio only, so "
        f"{' and '.join(parts)} were left out. Save as .mkv to keep every track."
    )

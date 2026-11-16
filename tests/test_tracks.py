"""Tests for keeping every track in MKV output."""

from umc.core.original import EncodingPlan, plan_original
from umc.core.tracks import dropped_tracks_note, keep_all_tracks


def media(*streams):
    return {"format": {"format_name": "matroska,webm"}, "streams": list(streams)}


VIDEO = {"codec_type": "video", "codec_name": "h264"}
COVER = {"codec_type": "video", "codec_name": "mjpeg", "disposition": {"attached_pic": 1}}
ENGLISH = {"codec_type": "audio", "codec_name": "aac"}
JAPANESE = {"codec_type": "audio", "codec_name": "opus"}
SRT = {"codec_type": "subtitle", "codec_name": "subrip"}
MOV_TEXT = {"codec_type": "subtitle", "codec_name": "mov_text"}
UNKNOWN_SUB = {"codec_type": "subtitle", "codec_name": "dvb_teletext"}
FONT = {"codec_type": "attachment", "codec_name": "ttf"}


def test_maps_all_video_and_audio_tracks():
    plan = keep_all_tracks(EncodingPlan(["-c", "copy"], "q"), media(VIDEO, ENGLISH, JAPANESE))

    assert plan.options[:4] == ["-map", "0:V?", "-map", "0:a?"]
    assert plan.options[-2:] == ["-c", "copy"]
    assert "Kept all tracks: 1 video track, 2 audio tracks." in plan.notes


def test_subtitles_are_copied_or_converted_to_srt():
    plan = keep_all_tracks(EncodingPlan([], "q"), media(VIDEO, ENGLISH, SRT, MOV_TEXT))
    options = plan.options

    assert options[options.index("0:s:0") + 1 : options.index("0:s:0") + 3] == ["-c:s:0", "copy"]
    assert options[options.index("0:s:1") + 1 : options.index("0:s:1") + 3] == ["-c:s:1", "srt"]


def test_unsupported_subtitles_are_skipped_with_a_note():
    plan = keep_all_tracks(EncodingPlan([], "q"), media(VIDEO, ENGLISH, UNKNOWN_SUB, SRT))

    # The unsupported first subtitle is skipped; the SRT becomes output subtitle 0.
    assert "0:s:0" not in plan.options
    assert plan.options[plan.options.index("0:s:1") + 1] == "-c:s:0"
    assert any("could not be kept" in note for note in plan.notes)


def test_attachments_are_copied():
    plan = keep_all_tracks(EncodingPlan([], "q"), media(VIDEO, ENGLISH, FONT))

    assert "0:t?" in plan.options
    assert plan.options[plan.options.index("-c:t") + 1] == "copy"


def test_fallback_chain_ends_without_subtitles():
    metadata = media(VIDEO, ENGLISH, JAPANESE, SRT)
    original = plan_original("video", ".mkv", metadata)
    plan = keep_all_tracks(original, metadata)

    assert plan.options[plan.options.index("-c:v") + 1] == "copy"
    assert "0:s:0" in plan.options

    encoded = plan.fallback
    assert encoded.options[encoded.options.index("-c:v") + 1] == "libx264"
    assert "0:s:0" in encoded.options

    last = encoded.fallback
    assert "0:s:0" not in last.options
    assert "0:a?" in last.options
    assert last.fallback is None
    assert any("left out" in note for note in last.notes)


def test_album_art_is_not_counted_as_video():
    plan = keep_all_tracks(EncodingPlan([], "q"), media(VIDEO, COVER, ENGLISH, JAPANESE))

    assert "Kept all tracks: 1 video track, 2 audio tracks." in plan.notes


def test_simple_file_gets_no_track_note():
    plan = keep_all_tracks(EncodingPlan([], "q"), media(VIDEO, ENGLISH))

    assert plan.notes == []
    assert plan.fallback is None


def test_dropped_tracks_note_for_mp4():
    note = dropped_tracks_note(media(VIDEO, ENGLISH, JAPANESE, SRT), ".mp4")

    assert "1 extra audio track and 1 subtitle track" in note
    assert ".mkv" in note


def test_no_dropped_tracks_note_for_simple_files():
    assert dropped_tracks_note(media(VIDEO, ENGLISH), ".mp4") is None

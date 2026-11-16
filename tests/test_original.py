"""Tests for the original-quality preset planner."""

import pytest

from umc.core.original import plan_original


def media(*streams, format_name="mov,mp4,m4a,3gp,3g2,mj2"):
    return {"format": {"format_name": format_name}, "streams": list(streams)}


def video(codec, pix_fmt="yuv420p"):
    return {"codec_type": "video", "codec_name": codec, "pix_fmt": pix_fmt}


def audio(codec, **extra):
    return {"codec_type": "audio", "codec_name": codec, **extra}


def value_after(options, flag):
    return options[options.index(flag) + 1]


# ------------------------------------------------------------------ video --


def test_compatible_video_is_copied():
    plan = plan_original("video", ".mp4", media(video("h264"), audio("aac")))

    assert value_after(plan.options, "-c:v") == "copy"
    assert value_after(plan.options, "-c:a") == "copy"
    assert "identical" in plan.quality
    assert plan.fallback is not None
    assert value_after(plan.fallback.options, "-c:v") == "libx264"


def test_hevc_copy_is_tagged_for_apple_devices():
    plan = plan_original("video", ".mp4", media(video("hevc", "yuv420p10le"), audio("aac")))

    assert value_after(plan.options, "-c:v") == "copy"
    assert value_after(plan.options, "-tag:v") == "hvc1"


def test_mkv_copies_anything():
    plan = plan_original("video", ".mkv", media(video("vp9"), audio("opus")))

    assert value_after(plan.options, "-c:v") == "copy"
    assert value_after(plan.options, "-c:a") == "copy"


def test_incompatible_video_is_reencoded_visually_lossless():
    plan = plan_original("video", ".mp4", media(video("vp9"), audio("opus")))

    assert value_after(plan.options, "-c:v") == "libx264"
    assert value_after(plan.options, "-crf") == "16"
    assert value_after(plan.options, "-c:a") == "aac"
    assert plan.fallback is None


def test_only_audio_reencoded_when_video_fits():
    plan = plan_original("video", ".mp4", media(video("h264"), audio("opus")))

    assert value_after(plan.options, "-c:v") == "copy"
    assert value_after(plan.options, "-c:a") == "aac"
    assert "video identical" in plan.quality


def test_lossless_audio_in_video_gets_top_aac_bitrate():
    plan = plan_original("video", ".mp4", media(video("h264"), audio("pcm_s24le")))

    assert value_after(plan.options, "-b:a") == "320k"


def test_webm_reencodes_to_vp9_and_opus():
    plan = plan_original("video", ".webm", media(video("h264"), audio("aac")))

    assert value_after(plan.options, "-c:v") == "libvpx-vp9"
    assert value_after(plan.options, "-c:a") == "libopus"


def test_ten_bit_reencode_warns_user():
    plan = plan_original("video", ".webm", media(video("hevc", "yuv420p10le")))

    assert any("10-bit" in note for note in plan.notes)


def test_video_without_metadata_is_encoded_at_max_quality():
    plan = plan_original("video", ".mp4", None)

    assert value_after(plan.options, "-crf") == "16"


# ------------------------------------------------------------------ audio --


@pytest.mark.parametrize(
    ("extension", "codec"),
    [(".mp3", "mp3"), (".aac", "aac"), (".m4a", "aac"), (".opus", "opus"), (".flac", "flac")],
)
def test_matching_audio_is_copied(extension, codec):
    plan = plan_original("audio", extension, media(audio(codec)))

    assert value_after(plan.options, "-c:a") == "copy"
    assert plan.fallback is not None


@pytest.mark.parametrize(
    ("source", "extension", "codec"),
    [("pcm_s16le", ".flac", "flac"), ("flac", ".wav", "pcm_s16le"), ("pcm_s16le", ".m4a", "alac")],
)
def test_lossless_targets_from_lossless_source(source, extension, codec):
    plan = plan_original("audio", extension, media(audio(source)))

    assert value_after(plan.options, "-c:a") == codec
    assert "lossless" in plan.quality
    assert not plan.notes


def test_wav_keeps_24_bit():
    plan = plan_original("audio", ".wav", media(audio("flac", bits_per_raw_sample="24")))

    assert value_after(plan.options, "-c:a") == "pcm_s24le"


def test_lossy_target_uses_maximum_quality_and_explains():
    plan = plan_original("audio", ".mp3", media(audio("flac")))

    assert value_after(plan.options, "-b:a") == "320k"
    assert any(".flac" in note for note in plan.notes)


def test_m4a_from_lossy_source_uses_aac():
    plan = plan_original("audio", ".m4a", media(audio("mp3")))

    assert value_after(plan.options, "-c:a") == "aac"


# ------------------------------------------------------------------ image --


def test_matching_picture_is_copied():
    cover = {"codec_type": "video", "codec_name": "mjpeg", "disposition": {"attached_pic": 1}}
    plan = plan_original("image", ".jpg", media(audio("mp3"), cover))

    assert value_after(plan.options, "-c:v") == "copy"


def test_no_copy_when_seeking():
    plan = plan_original("image", ".jpg", media(video("mjpeg")), at=5)

    assert "copy" not in plan.options


def test_webp_is_lossless():
    plan = plan_original("image", ".webp", media(video("png", "rgba")))

    assert value_after(plan.options, "-lossless") == "1"
    assert plan.quality == "lossless"


def test_jpg_uses_maximum_quality():
    plan = plan_original("image", ".jpg", media(video("h264")))

    assert value_after(plan.options, "-q:v") == "1"
    assert plan.notes

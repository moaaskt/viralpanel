"""Testes unitários para validação contextual por codec, FPS fracionário, SAR e AABB (QUAL-03)."""
from __future__ import annotations

import pytest

from viralpanel.branding import SafeZones9x16
from viralpanel.studio.validator import (
    MediaQualityValidator,
    check_subtitle_avatar_non_overlap,
)


def _mock_probe_payload(
    *,
    codec_name: str,
    width: int = 1280,
    height: int = 720,
    stream_bitrate: str | None = None,
    format_bitrate: str | None = None,
    avg_frame_rate: str = "24/1",
    r_frame_rate: str = "24/1",
) -> dict:
    v_stream: dict = {
        "codec_type": "video",
        "codec_name": codec_name,
        "width": width,
        "height": height,
        "avg_frame_rate": avg_frame_rate,
        "r_frame_rate": r_frame_rate,
    }
    if stream_bitrate is not None:
        v_stream["bit_rate"] = stream_bitrate

    fmt: dict = {"format_name": "mov,mp4"}
    if format_bitrate is not None:
        fmt["bit_rate"] = format_bitrate

    return {"streams": [v_stream], "format": fmt}


def test_validate_source_footage_quality_codecs_differentiation(tmp_path, monkeypatch):
    """Diferencia limiares de BPP por codec (H.264, HEVC, VP9, AV1) sem bloquear a esteira."""
    validator = MediaQualityValidator()
    dummy = tmp_path / "sample.mp4"
    dummy.write_bytes(b"DUMMY")

    # 1280 * 720 * 24 = 22_118_400 pixels/s
    # Para BPP = 0.025 -> bitrate = 552_960 bps
    bitrate_025 = str(int(1280 * 720 * 24 * 0.025))

    # H.264 com BPP 0.025 (< 0.035) -> emite warning específico de H.264, mas is_valid=True
    monkeypatch.setattr(
        validator,
        "probe",
        lambda _: _mock_probe_payload(codec_name="h264", stream_bitrate=bitrate_025),
    )
    res_h264 = validator.validate_source_footage_quality(dummy)
    assert res_h264.is_valid is True
    assert res_h264.metrics["bpp"] == pytest.approx(0.025, abs=1e-4)
    assert any("H.264" in w for w in res_h264.warnings)

    # HEVC, VP9 e AV1 com o mesmo BPP 0.025 (> 0.020/0.022/0.018) -> ZERO warnings!
    for efficient_codec in ("hevc", "vp9", "av1"):
        monkeypatch.setattr(
            validator,
            "probe",
            lambda _, c=efficient_codec: _mock_probe_payload(
                codec_name=c, stream_bitrate=bitrate_025
            ),
        )
        res = validator.validate_source_footage_quality(dummy)
        assert res.is_valid is True
        assert res.metrics["bpp"] == pytest.approx(0.025, abs=1e-4)
        assert res.warnings == [], f"Codec {efficient_codec} com BPP=0.025 não deve emitir alerta: {res.warnings}"

    # Limiar baixo extremo em cada codec eficiente -> emite seu próprio alerta
    cases = [
        ("hevc", 0.015, "HEVC"),
        ("vp9", 0.018, "VP9"),
        ("av1", 0.012, "AV1"),
    ]
    for codec_name, target_bpp, label in cases:
        low_br = str(int(1280 * 720 * 24 * target_bpp))
        monkeypatch.setattr(
            validator,
            "probe",
            lambda _, c=codec_name, b=low_br: _mock_probe_payload(codec_name=c, stream_bitrate=b),
        )
        res_low = validator.validate_source_footage_quality(dummy)
        assert res_low.is_valid is True
        assert any(label in w for w in res_low.warnings)


def test_validate_source_footage_quality_missing_bitrate_no_mock(tmp_path, monkeypatch):
    """Bitrate ausente na stream e no container emite warning informativo, bpp=None e is_valid=True."""
    validator = MediaQualityValidator()
    dummy = tmp_path / "no_bitrate.mp4"
    dummy.write_bytes(b"DUMMY")

    monkeypatch.setattr(
        validator,
        "probe",
        lambda _: _mock_probe_payload(codec_name="h264", stream_bitrate=None, format_bitrate=None),
    )
    res = validator.validate_source_footage_quality(dummy)
    assert res.is_valid is True
    assert res.metrics["bpp"] is None
    assert res.metrics["bitrate"] is None
    assert any("Bitrate indisponível" in w for w in res.warnings)


def test_validate_source_footage_quality_container_fallback_and_low_res(tmp_path, monkeypatch):
    """Fallback para container deduz 128kbps quando > 192kbps e alerta resolução < 720p."""
    validator = MediaQualityValidator()
    dummy = tmp_path / "fallback.mp4"
    dummy.write_bytes(b"DUMMY")

    monkeypatch.setattr(
        validator,
        "probe",
        lambda _: _mock_probe_payload(
            codec_name="h264",
            width=640,
            height=360,
            stream_bitrate=None,
            format_bitrate="628000",
        ),
    )
    res = validator.validate_source_footage_quality(dummy)
    assert res.is_valid is True
    assert res.metrics["bitrate"] == 500_000
    assert any("360p" in w for w in res.warnings)


def test_validate_source_footage_quality_fractional_fps(tmp_path, monkeypatch):
    """Valida cálculo exato de BPP para taxas de quadros fracionárias do FFprobe."""
    validator = MediaQualityValidator()
    dummy = tmp_path / "ntsc.mp4"
    dummy.write_bytes(b"DUMMY")

    for fps_str, expected_fps in (
        ("24000/1001", 24000 / 1001),
        ("30000/1001", 30000 / 1001),
        ("60000/1001", 60000 / 1001),
    ):
        monkeypatch.setattr(
            validator,
            "probe",
            lambda _, r=fps_str: _mock_probe_payload(
                codec_name="h264",
                width=1920,
                height=1080,
                stream_bitrate="3000000",
                avg_frame_rate=r,
                r_frame_rate=r,
            ),
        )
        res = validator.validate_source_footage_quality(dummy)
        expected_bpp = 3_000_000 / (1920 * 1080 * expected_fps)
        assert res.is_valid is True
        assert res.metrics["fps"] == pytest.approx(expected_fps, abs=1e-3)
        assert res.metrics["bpp"] == pytest.approx(expected_bpp, abs=1e-5)


def test_check_subtitle_avatar_non_overlap_matrix_with_padding():
    """Valida por AABB 2D que legendas (1 e 2 linhas) com MarginR=440 e MarginV=420 têm folga >=24px do avatar."""
    safe = SafeZones9x16()
    av_x1 = safe.WIDTH - safe.AVATAR_SIZE - safe.AVATAR_MARGIN_RIGHT  # 680
    av_y1 = safe.HEIGHT - safe.AVATAR_SIZE - safe.AVATAR_MARGIN_BOTTOM  # 1360
    av_x2 = av_x1 + safe.AVATAR_SIZE  # 940
    av_y2 = av_y1 + safe.AVATAR_SIZE  # 1620
    avatar_bbox = (av_x1, av_y1, av_x2, av_y2)

    x_text_left = safe.SUBTITLE_MARGIN_LEFT  # 80
    x_text_right = safe.WIDTH - safe.SUBTITLE_MARGIN_RIGHT  # 640

    # 1 linha e 2 linhas no terço inferior (MarginV=420 -> Y_base=1500, Y_topo=1340)
    sub_1_line = (x_text_left, 1420, x_text_right, safe.SUBTITLE_Y_MAX)
    sub_2_lines = (x_text_left, safe.SUBTITLE_Y_MIN, x_text_right, safe.SUBTITLE_Y_MAX)

    assert check_subtitle_avatar_non_overlap(sub_1_line, avatar_bbox, box_padding=16) is True
    assert check_subtitle_avatar_non_overlap(sub_2_lines, avatar_bbox, box_padding=16) is True
    assert (av_x1 - (x_text_right + 16)) >= 24

    # Caso de colisão real (se MarginR fosse reduzido invadindo X>=665 com padding=16)
    colliding_sub = (80, safe.SUBTITLE_Y_MIN, 670, safe.SUBTITLE_Y_MAX)
    assert check_subtitle_avatar_non_overlap(colliding_sub, avatar_bbox, box_padding=16) is False


def test_sar_aspect_ratio_verification(tmp_path, monkeypatch):
    """Valida aprovação de SAR 1:1 e rejeição explícita de SAR anamórfico diferente de 1:1."""
    validator = MediaQualityValidator()
    dummy = tmp_path / "rendered.mp4"
    dummy.write_bytes(b"MP4")

    def _rendered_probe(sar_val: str) -> dict:
        return {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1080,
                    "height": 1920,
                    "sample_aspect_ratio": sar_val,
                    "pix_fmt": "yuv420p",
                    "avg_frame_rate": "24/1",
                    "r_frame_rate": "24/1",
                    "duration": "2.0",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "44100",
                    "duration": "2.0",
                },
            ],
            "format": {"format_name": "mov,mp4", "duration": "2.0"},
        }

    monkeypatch.setattr(validator, "probe", lambda _: _rendered_probe("1:1"))
    res_ok = validator.validate_rendered_video(dummy)
    assert res_ok.is_valid is True
    assert res_ok.metrics["sample_aspect_ratio"] == "1:1"
    assert not any("SAR" in w for w in res_ok.warnings)

    monkeypatch.setattr(validator, "probe", lambda _: _rendered_probe("4:3"))
    res_bad = validator.validate_rendered_video(dummy)
    assert res_bad.is_valid is False
    assert any("Sample Aspect Ratio (SAR)" in e for e in res_bad.errors)

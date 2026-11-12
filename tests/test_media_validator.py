from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from viralpanel.branding import SafeZones9x16
from viralpanel.studio.avatar import AudioReactiveAvatarAnimator, ensure_default_avatar_image
from viralpanel.studio.renderer import ReactionVideoRenderer
from viralpanel.studio.subtitles import SubtitleJobConfig, generate_subtitles
from viralpanel.studio.validator import (
    MediaQualityValidator,
    ValidationResult,
    parse_frame_rate,
    resolve_duration,
)
from viralpanel.studio.voice import MockVoiceSynthesizer


def test_parse_frame_rate():
    """Valida interpretação matemática de frações de FPS do FFprobe sem comparação de strings."""
    assert parse_frame_rate("24/1") == pytest.approx(24.0, abs=1e-6)
    assert parse_frame_rate("24000/1000") == pytest.approx(24.0, abs=1e-6)
    assert parse_frame_rate("24000/1001") == pytest.approx(23.9760239, abs=1e-5)
    assert parse_frame_rate("30000/1001") == pytest.approx(29.9700299, abs=1e-5)
    assert parse_frame_rate("24") == pytest.approx(24.0, abs=1e-6)

    # Casos inválidos ou nulos devem retornar None
    assert parse_frame_rate("0/0") is None
    assert parse_frame_rate("0") is None
    assert parse_frame_rate("-24/1") is None
    assert parse_frame_rate("N/A") is None
    assert parse_frame_rate("") is None
    assert parse_frame_rate(None) is None
    assert parse_frame_rate("invalid/fraction") is None


def test_resolve_duration_fallback_and_error():
    """Valida cascata stream -> format e reprovação explícita quando duração é ausente."""
    # 1. Stream duration presente tem prioridade
    assert resolve_duration({"duration": "3.45"}, {"duration": "9.99"}) == pytest.approx(3.45)

    # 2. Stream duration ausente ou 'N/A' faz fallback para format.duration
    assert resolve_duration({"duration": "N/A"}, {"duration": "4.20"}) == pytest.approx(4.20)
    assert resolve_duration({}, {"duration": "2.75"}) == pytest.approx(2.75)

    # 3. Ambos ausentes ou inválidos levantam ValueError (nunca aprovam silenciosamente)
    with pytest.raises(ValueError, match="Duração não pôde ser determinada"):
        resolve_duration({}, {})

    with pytest.raises(ValueError, match="Duração não pôde ser determinada"):
        resolve_duration({"duration": "N/A"}, {"duration": "0"})

    with pytest.raises(ValueError, match="Duração não pôde ser determinada"):
        resolve_duration({"duration": "-1.5"}, {"duration": None})


def test_validate_avatar_asset_format(tmp_path: Path):
    """Confere se validate_avatar_asset exige o formato real da Phase 11 (png / rgba 300x300)."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg/FFprobe não disponíveis")

    validator = MediaQualityValidator()

    voice_path = tmp_path / "voice.wav"
    MockVoiceSynthesizer(min_duration=1.5, max_duration=1.5).synthesize("Teste avatar.", voice_path)

    img_path = tmp_path / "avatar_source.png"
    ensure_default_avatar_image(img_path)

    # 1. Avatar real gerado pelo AudioReactiveAvatarAnimator (Phase 11: png / rgba)
    valid_avatar = tmp_path / "avatar_valid.mov"
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    animator.generate_avatar_video(voice_path, valid_avatar)

    res_valid = validator.validate_avatar_asset(valid_avatar)
    assert res_valid.is_valid is True, f"Erros inesperados: {res_valid.errors}"
    assert res_valid.metrics["video_codec"] == "png"
    assert res_valid.metrics["pix_fmt"] == "rgba"
    assert res_valid.metrics["width"] == SafeZones9x16.AVATAR_SIZE
    assert res_valid.metrics["height"] == SafeZones9x16.AVATAR_SIZE

    # 2. Avatar inválido sem canal alfa (h264 / yuv420p)
    invalid_avatar = tmp_path / "avatar_opaque.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=300x300:r=24:d=1.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(invalid_avatar),
        ],
        check=True,
        capture_output=True,
    )
    res_invalid = validator.validate_avatar_asset(invalid_avatar)
    assert res_invalid.is_valid is False
    assert any("png" in err for err in res_invalid.errors)
    assert any("rgba" in err for err in res_invalid.errors)


def test_validate_rendered_video_with_real_ffmpeg(tmp_path: Path, monkeypatch):
    """Valida vídeo composto válido (1080x1920, 24fps, h264, yuv420p, aac) e rejeição de anomalias."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("FFmpeg/FFprobe não disponíveis")

    validator = MediaQualityValidator()

    # 1. Vídeo 100% aderente às especificações
    valid_video = tmp_path / "valid_9x16.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#0f172a:s=1080x1920:r=24:d=1.5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=1.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-shortest",
            str(valid_video),
        ],
        check=True,
        capture_output=True,
    )

    res = validator.validate_rendered_video(valid_video)
    assert isinstance(res, ValidationResult)
    assert res.is_valid is True, f"Vídeo válido falhou com erros: {res.errors}"
    assert res.metrics["width"] == 1080
    assert res.metrics["height"] == 1920
    assert res.metrics["video_codec"] == "h264"
    assert res.metrics["pix_fmt"] == "yuv420p"
    assert res.metrics["audio_codec"] == "aac"
    assert res.metrics["sample_rate"] >= 44100
    assert abs(res.metrics["fps"] - 24.0) <= 0.15

    # 2. Vídeo com resolução incorreta (720x1280) e FPS incorreto (30fps)
    wrong_spec_video = tmp_path / "wrong_720p_30fps.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#0f172a:s=720x1280:r=30:d=1.0",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=1.0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(wrong_spec_video),
        ],
        check=True,
        capture_output=True,
    )
    res_wrong = validator.validate_rendered_video(wrong_spec_video)
    assert res_wrong.is_valid is False
    assert any("1080x1920" in e for e in res_wrong.errors)
    assert any("FPS fora da especificação" in e for e in res_wrong.errors)

    # 3. Simulação de duração ausente no stream e no format (nunca deve aprovar silenciosamente)
    monkeypatch.setattr(
        validator,
        "probe",
        lambda _: {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1080,
                    "height": 1920,
                    "pix_fmt": "yuv420p",
                    "avg_frame_rate": "24000/1001",
                    "r_frame_rate": "24/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "44100",
                },
            ],
            "format": {"format_name": "mov,mp4"},
        },
    )
    res_no_dur = validator.validate_rendered_video(valid_video)
    assert res_no_dur.is_valid is False
    assert any("Duração não pôde ser determinada" in e for e in res_no_dur.errors)


def test_inspect_composed_avatar_transparency(tmp_path: Path):
    """Testa amostragem dos 4 cantos + malha distribuída externa ao círculo e detecção de defeito parcial."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg não disponível")

    validator = MediaQualityValidator()

    voice_path = tmp_path / "voice.wav"
    MockVoiceSynthesizer(min_duration=1.5, max_duration=1.5).synthesize("Você não sabia. Agora sabe.", voice_path)

    img_path = tmp_path / "avatar.png"
    ensure_default_avatar_image(img_path)

    avatar_mov = tmp_path / "avatar.mov"
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    animator.generate_avatar_video(voice_path, avatar_mov)

    ass_path = tmp_path / "subs.ass"
    generate_subtitles(
        SubtitleJobConfig(
            script_text="Você não sabia. Agora sabe.",
            total_duration=1.5,
            output_path=ass_path,
            margin_v=SafeZones9x16.SUBTITLE_MARGIN_V,
        )
    )

    # Source sem stream de vídeo aciona fundo lavfi #0f172a (RGB: 15, 23, 42)
    dummy_source = tmp_path / "audio_only_source.mp4"
    dummy_source.write_bytes(b"NO_VIDEO_STREAM")

    composed_ok = tmp_path / "composed_ok.mp4"
    renderer = ReactionVideoRenderer()
    renderer.render(
        source_video_path=dummy_source,
        avatar_video_path=avatar_mov,
        voice_audio_path=voice_path,
        ass_subtitle_path=ass_path,
        output_path=composed_ok,
    )

    # 1. Composição válida deve passar nos 4 cantos, na malha distribuída e no contorno #FACC15
    res_ok = validator.inspect_composed_avatar_transparency(
        composed_ok,
        expected_bg_rgb=(15, 23, 42),
        timestamp_sec=0.5,
    )
    assert res_ok.passed is True, f"Falha inesperada na inspeção de pixels: {res_ok.errors}"
    assert res_ok.details["distributed_points_checked"] >= 70
    assert res_ok.details["distributed_points_failed"] == 0

    # 2. Caixa branca opaca inteira no lugar do avatar deve reprovar
    opaque_box_video = tmp_path / "composed_white_box.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(composed_ok),
            "-vf",
            "drawbox=x=726:y=1300:w=300:h=300:color=white:t=fill",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(opaque_box_video),
        ],
        check=True,
        capture_output=True,
    )
    res_white = validator.inspect_composed_avatar_transparency(
        opaque_box_video,
        expected_bg_rgb=(15, 23, 42),
        timestamp_sec=0.5,
    )
    assert res_white.passed is False
    assert any("Canto" in e for e in res_white.errors)

    # 3. Defeito opaco parcial localizado ENTRE os cantos (onde os 4 cantos permanecem intactos)
    # Ponto (760, 1334) está dentro da bounding box [726..1026, 1300..1600], fora do círculo
    # (hypot(760-876, 1334-1450) = hypot(-116, -116) = 164.0 > 156), mas longe dos 4 cantos!
    partial_defect_video = tmp_path / "composed_partial_defect.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(composed_ok),
            "-vf",
            "drawbox=x=752:y=1326:w=20:h=20:color=white:t=fill",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(partial_defect_video),
        ],
        check=True,
        capture_output=True,
    )
    res_partial = validator.inspect_composed_avatar_transparency(
        partial_defect_video,
        expected_bg_rgb=(15, 23, 42),
        timestamp_sec=0.5,
    )
    assert res_partial.passed is False
    # Confirma que os 4 cantos não falharam, mas a malha distribuída capturou o defeito parcial!
    assert not any("Canto" in e for e in res_partial.errors)
    assert res_partial.details["distributed_points_failed"] > 0
    assert any("região externa ao círculo" in e for e in res_partial.errors)


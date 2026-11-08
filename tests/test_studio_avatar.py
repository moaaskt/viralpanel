from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from viralpanel.branding import SafeZones9x16, ZuntoPalette
from viralpanel.studio.avatar import (
    AudioReactiveAvatarAnimator,
    AvatarConfig,
    MockAvatarAnimator,
    ensure_default_avatar_image,
)
from viralpanel.studio.voice import MockVoiceSynthesizer


def test_avatar_config_defaults_and_immutability():
    """Valida DTO AvatarConfig tipado, imutável e com defaults calibrados per D-05."""
    config = AvatarConfig()
    assert config.avatar_image_path is None
    assert config.size == SafeZones9x16.AVATAR_SIZE == 300
    assert config.crop_mode == "circle_alpha"
    assert config.border_color == ZuntoPalette.IMPACT_YELLOW == "#FACC15"
    assert config.border_width == 4
    assert config.overlay_x_expr == "W-w-54"
    assert config.overlay_y_expr == "H-h-320"
    assert config.enable_waveform is True
    assert config.waveform_color == "#FACC15@0.85"

    with pytest.raises(FrozenInstanceError):
        config.size = 360

    custom = AvatarConfig(
        avatar_image_path=Path("assets/custom.png"),
        size=280,
        crop_mode="native_rgba",
        border_color="#FFFFFF",
        border_width=2,
        overlay_x_expr="W-w-60",
        overlay_y_expr="H-h-300",
        enable_waveform=False,
        waveform_color="#FFFFFF@0.5",
    )
    assert custom.size == 280
    assert custom.border_width == 2
    assert custom.enable_waveform is False


def test_mock_avatar_animator_matches_voice_duration(tmp_path):
    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "avatar.mp4"

    _, voice_dur = MockVoiceSynthesizer().synthesize("Disciplina constrói liberdade todos os dias.", voice_path)
    out_path, avatar_dur = MockAvatarAnimator().generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert abs(avatar_dur - voice_dur) < 0.5


def test_ensure_default_avatar_image_creates_file(tmp_path):
    target = tmp_path / "avatar.png"
    result = ensure_default_avatar_image(target)
    assert result.exists()
    assert result.stat().st_size > 0


def test_audio_reactive_avatar_animator(tmp_path):
    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "reactive_avatar.mp4"
    img_path = tmp_path / "img.png"
    ensure_default_avatar_image(img_path)

    _, voice_dur = MockVoiceSynthesizer().synthesize("Foco diário.", voice_path)
    animator = AudioReactiveAvatarAnimator(default_avatar_image=img_path)
    out_path, dur = animator.generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert dur > 0



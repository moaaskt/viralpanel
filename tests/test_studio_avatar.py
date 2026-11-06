from viralpanel.studio.avatar import AudioReactiveAvatarAnimator, MockAvatarAnimator, ensure_default_avatar_image
from viralpanel.studio.voice import MockVoiceSynthesizer


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



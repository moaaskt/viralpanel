from viralpanel.studio.avatar import MockAvatarAnimator
from viralpanel.studio.voice import MockVoiceSynthesizer


def test_mock_avatar_animator_matches_voice_duration(tmp_path):
    voice_path = tmp_path / "voice.wav"
    avatar_path = tmp_path / "avatar.mp4"

    _, voice_dur = MockVoiceSynthesizer().synthesize("Disciplina constrói liberdade todos os dias.", voice_path)
    out_path, avatar_dur = MockAvatarAnimator().generate_avatar_video(voice_path, avatar_path)

    assert out_path.exists()
    assert abs(avatar_dur - voice_dur) < 0.5


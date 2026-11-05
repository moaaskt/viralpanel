from viralpanel.studio.voice import MockVoiceSynthesizer


def test_mock_voice_synthesizer_generates_wav_proportional_to_text(tmp_path):
    synth = MockVoiceSynthesizer(words_per_second=4.0, min_duration=1.5, max_duration=10.0)
    short_out = tmp_path / "short.wav"
    long_out = tmp_path / "long.wav"

    p1, d1 = synth.synthesize("Foco total.", short_out)
    p2, d2 = synth.synthesize(" ".join(["Disciplina"] * 24), long_out)

    assert p1.exists() and p2.exists()
    assert d1 >= 1.4
    assert d2 > d1


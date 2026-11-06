from pathlib import Path
import pytest
from viralpanel.studio.voice import BaseVoiceSynthesizer, FallbackVoiceSynthesizer, MockVoiceSynthesizer


def test_mock_voice_synthesizer_generates_wav_proportional_to_text(tmp_path):
    synth = MockVoiceSynthesizer(words_per_second=4.0, min_duration=1.5, max_duration=10.0)
    short_out = tmp_path / "short.wav"
    long_out = tmp_path / "long.wav"

    p1, d1 = synth.synthesize("Foco total.", short_out)
    p2, d2 = synth.synthesize(" ".join(["Disciplina"] * 24), long_out)

    assert p1.exists() and p2.exists()
    assert d1 >= 1.4
    assert d2 > d1


def test_fallback_voice_synthesizer_advances_on_error(tmp_path):
    class FailingSynthesizer(BaseVoiceSynthesizer):
        def synthesize(self, text, output_path, speaker_wav=None):
            raise RuntimeError("TTS engine unreachable")

    target = tmp_path / "fallback.wav"
    chain = FallbackVoiceSynthesizer(synthesizers=[FailingSynthesizer(), MockVoiceSynthesizer()])
    out_path, dur = chain.synthesize("Teste de fallback de voz", target)

    assert out_path.exists()
    assert dur > 0


def test_fallback_voice_synthesizer_raises_when_all_fail(tmp_path):
    class FailingSynthesizer(BaseVoiceSynthesizer):
        def synthesize(self, text, output_path, speaker_wav=None):
            raise RuntimeError("TTS engine unreachable")

    target = tmp_path / "fail.wav"
    chain = FallbackVoiceSynthesizer(synthesizers=[FailingSynthesizer(), FailingSynthesizer()])
    with pytest.raises(RuntimeError, match="Todos os sintetizadores de voz falharam"):
        chain.synthesize("Teste", target)



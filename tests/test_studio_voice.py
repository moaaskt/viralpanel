import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import types
import pytest
from viralpanel.studio.voice import (
    BaseVoiceSynthesizer,
    EdgeTTSVoiceSynthesizer,
    FallbackVoiceSynthesizer,
    MockVoiceSynthesizer,
    compute_file_sha256,
)


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


def test_edge_tts_synthesizer_captures_word_boundary_and_persists_sidecar(tmp_path, monkeypatch):
    """Captura eventos WordBoundary (100ns -> segundos), preserva assinatura e grava sidecar com duplo hash."""
    captured_kwargs: dict = {}

    class FakeCommunicate:
        def __init__(self, text, voice, **kwargs):
            captured_kwargs["text"] = text
            captured_kwargs["voice"] = voice
            captured_kwargs.update(kwargs)

        async def stream(self):
            yield {"type": "audio", "data": b"ID3FAKEMPP3AUDIO"}
            yield {"type": "WordBoundary", "offset": 1_200_000, "duration": 3_300_000, "text": "Você"}
            yield {"type": "WordBoundary", "offset": 5_000_000, "duration": 2_500_000, "text": "sabia?"}

    monkeypatch.setattr("edge_tts.Communicate", FakeCommunicate)
    monkeypatch.setattr(shutil, "which", lambda cmd: "ffmpeg")

    def fake_run(cmd, *args, **kwargs):
        out_path = Path(cmd[-1])
        out_path.write_bytes(b"RIFFFAKEWAVEHEADER_FOR_TEST")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("viralpanel.studio.voice.probe_duration", lambda p: 1.25)

    out_wav = tmp_path / "narration.wav"
    text = "Você sabia?"
    synth = EdgeTTSVoiceSynthesizer(voice="pt-BR-AntonioNeural", rate="+0%")
    ret_path, ret_dur = synth.synthesize(text, out_wav)

    assert ret_path == out_wav
    assert ret_dur == 1.25
    assert captured_kwargs.get("boundary") == "WordBoundary"
    assert synth.last_word_timestamps == [
        {"word": "Você", "start": 0.12, "end": 0.45, "duration": 0.33},
        {"word": "sabia?", "start": 0.5, "end": 0.75, "duration": 0.25},
    ]

    sidecar_path = out_wav.with_suffix(".words.json")
    assert sidecar_path.exists()
    envelope = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert envelope["schema_version"] == "1.0"
    assert envelope["audio_file"] == out_wav.name
    assert envelope["audio_duration_sec"] == 1.25
    assert envelope["audio_hash"] == compute_file_sha256(out_wav)
    assert envelope["text_hash"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert envelope["word_count"] == 2
    assert envelope["timestamps"] == synth.last_word_timestamps


def test_edge_tts_synthesizer_cleans_obsolete_sidecar_before_synthesis(tmp_path, monkeypatch):
    """Remove sidecar obsoleto e reseta last_word_timestamps antes de tentar nova síntese."""
    out_wav = tmp_path / "narration.wav"
    stale_sidecar = out_wav.with_suffix(".words.json")
    stale_sidecar.write_text(json.dumps({"timestamps": [{"word": "antigo", "start": 0.0, "end": 0.5}]}), encoding="utf-8")

    class FailingCommunicate:
        def __init__(self, text, voice, **kwargs):
            pass

        async def stream(self):
            raise RuntimeError("Falha de rede simulada no stream")
            yield  # pragma: no cover

    monkeypatch.setattr("edge_tts.Communicate", FailingCommunicate)

    synth = EdgeTTSVoiceSynthesizer(voice="pt-BR-AntonioNeural", rate="+0%")
    synth.last_word_timestamps = [{"word": "stale", "start": 0.0, "end": 0.2}]

    with pytest.raises(RuntimeError, match="Falha de rede simulada"):
        synth.synthesize("Novo roteiro", out_wav)

    assert not stale_sidecar.exists(), "Sidecar obsoleto deve ter sido removido antes da falha"
    assert synth.last_word_timestamps is None




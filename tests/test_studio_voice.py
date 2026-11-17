import hashlib
import json
import logging
from pathlib import Path
import shutil
import subprocess
import pytest
from viralpanel.studio.voice import (
    BaseVoiceSynthesizer,
    EdgeTTSVoiceSynthesizer,
    FallbackVoiceSynthesizer,
    MockVoiceSynthesizer,
    PreSynthesizedVoice,
    XTTSVoiceSynthesizer,
    compute_file_sha256,
    load_and_validate_word_timestamps,
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


def test_load_and_validate_word_timestamps_rejects_text_mismatch(tmp_path, caplog):
    """Rejeita sidecar quando text_hash diverge do roteiro esperado, acionando fallback proporcional."""
    caplog.set_level(logging.WARNING)
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"RIFFAUDIODATA")
    sidecar = audio_path.with_suffix(".words.json")
    envelope = {
        "schema_version": "1.0",
        "audio_file": audio_path.name,
        "audio_duration_sec": 1.0,
        "audio_hash": compute_file_sha256(audio_path),
        "text_hash": hashlib.sha256(b"Texto original").hexdigest(),
        "word_count": 2,
        "timestamps": [
            {"word": "Texto", "start": 0.0, "end": 0.4, "duration": 0.4},
            {"word": "original", "start": 0.4, "end": 1.0, "duration": 0.6},
        ],
    }
    sidecar.write_text(json.dumps(envelope), encoding="utf-8")

    result = load_and_validate_word_timestamps(
        sidecar,
        expected_text="Texto modificado",
        expected_duration=1.0,
        expected_audio_path=audio_path,
    )
    assert result is None
    assert "text_hash divergente" in caplog.text


def test_load_and_validate_word_timestamps_rejects_audio_mismatch(tmp_path, caplog):
    """Rejeita sidecar quando audio_hash diverge do arquivo de áudio real."""
    caplog.set_level(logging.WARNING)
    audio_a = tmp_path / "audio_a.wav"
    audio_b = tmp_path / "audio_b.wav"
    audio_a.write_bytes(b"RIFF_AUDIO_BYTES_A")
    audio_b.write_bytes(b"RIFF_AUDIO_BYTES_B")

    text = "Mesmo texto"
    sidecar = audio_b.with_suffix(".words.json")
    envelope = {
        "schema_version": "1.0",
        "audio_file": audio_a.name,
        "audio_duration_sec": 1.0,
        "audio_hash": compute_file_sha256(audio_a),
        "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "word_count": 2,
        "timestamps": [
            {"word": "Mesmo", "start": 0.0, "end": 0.5, "duration": 0.5},
            {"word": "texto", "start": 0.5, "end": 1.0, "duration": 0.5},
        ],
    }
    sidecar.write_text(json.dumps(envelope), encoding="utf-8")

    result = load_and_validate_word_timestamps(
        sidecar,
        expected_text=text,
        expected_duration=1.0,
        expected_audio_path=audio_b,
    )
    assert result is None
    assert "audio_hash divergente" in caplog.text


def test_load_and_validate_word_timestamps_discards_corrupt_or_empty_sidecar(tmp_path, caplog):
    """Descarta sidecars ausentes, vazios, JSON quebrados, listas vazias ou com divergência > 0.15s."""
    caplog.set_level(logging.WARNING)

    # 1. Arquivo ausente
    assert load_and_validate_word_timestamps(tmp_path / "missing.words.json") is None

    # 2. Arquivo vazio
    empty_sidecar = tmp_path / "empty.words.json"
    empty_sidecar.write_text("   ", encoding="utf-8")
    assert load_and_validate_word_timestamps(empty_sidecar) is None

    # 3. JSON quebrado
    corrupt_sidecar = tmp_path / "corrupt.words.json"
    corrupt_sidecar.write_text("{broken json", encoding="utf-8")
    assert load_and_validate_word_timestamps(corrupt_sidecar) is None

    # 4. Lista vazia
    empty_list_sidecar = tmp_path / "empty_list.words.json"
    empty_list_sidecar.write_text(json.dumps({"timestamps": []}), encoding="utf-8")
    assert load_and_validate_word_timestamps(empty_list_sidecar) is None

    # 5. Divergência de duração > 0.15s
    dur_sidecar = tmp_path / "dur_mismatch.words.json"
    dur_sidecar.write_text(
        json.dumps({
            "audio_duration_sec": 2.0,
            "timestamps": [{"word": "Oi", "start": 0.0, "end": 0.5}],
        }),
        encoding="utf-8",
    )
    assert load_and_validate_word_timestamps(dur_sidecar, expected_duration=2.5) is None
    assert "Divergência temporal excessiva" in caplog.text


def test_fallback_voice_synthesizer_propagates_word_timestamps(tmp_path):
    """FallbackVoiceSynthesizer propaga last_word_timestamps do sintetizador bem-sucedido."""
    expected_ts = [{"word": "Foco", "start": 0.0, "end": 0.4, "duration": 0.4}]

    class FailingSynth(BaseVoiceSynthesizer):
        def synthesize(self, text, output_path, speaker_wav=None):
            raise RuntimeError("Primary down")

    class TimestampSynth(BaseVoiceSynthesizer):
        def __init__(self):
            self.last_word_timestamps = None

        def synthesize(self, text, output_path, speaker_wav=None):
            output_path.write_bytes(b"RIFFOK")
            self.last_word_timestamps = expected_ts
            return output_path, 0.5

    chain = FallbackVoiceSynthesizer(synthesizers=[FailingSynth(), TimestampSynth()])
    out, dur = chain.synthesize("Foco", tmp_path / "out.wav")
    assert out.exists()
    assert dur == 0.5
    assert chain.last_word_timestamps == expected_ts


def test_presynthesized_voice_loads_sidecar_and_delivers_word_timestamps(tmp_path):
    """PreSynthesizedVoice valida e copia o sidecar .words.json associado ao áudio mestre."""
    master_wav = tmp_path / "master.wav"
    MockVoiceSynthesizer(min_duration=1.5, max_duration=1.5).synthesize("Você sabe.", master_wav)
    master_sha = compute_file_sha256(master_wav)
    text = "Você sabe."
    timestamps = [
        {"word": "Você", "start": 0.1, "end": 0.6, "duration": 0.5},
        {"word": "sabe.", "start": 0.7, "end": 1.4, "duration": 0.7},
    ]
    master_sidecar = master_wav.with_suffix(".words.json")
    master_sidecar.write_text(
        json.dumps({
            "schema_version": "1.0",
            "audio_file": master_wav.name,
            "audio_duration_sec": 1.5,
            "audio_hash": master_sha,
            "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "word_count": 2,
            "timestamps": timestamps,
        }),
        encoding="utf-8",
    )

    pre_voice = PreSynthesizedVoice(
        master_audio_path=master_wav,
        duration=1.5,
        sha256_hash=master_sha,
        expected_text=text,
    )
    target = tmp_path / "delivered" / "narration.wav"
    out, dur = pre_voice.synthesize(text, target)

    assert out == target.resolve()
    assert dur == 1.5
    assert pre_voice.last_word_timestamps == timestamps
    assert target.with_suffix(".words.json").exists()


def test_mock_and_xtts_synthesizers_gracefully_return_none_timestamps(tmp_path, monkeypatch):
    """MockVoiceSynthesizer e XTTSVoiceSynthesizer operam com last_word_timestamps=None sem falhas."""
    mock_wav = tmp_path / "mock.wav"
    stale_sidecar = mock_wav.with_suffix(".words.json")
    stale_sidecar.write_text("stale", encoding="utf-8")

    mock_synth = MockVoiceSynthesizer(min_duration=1.5, max_duration=1.5)
    _, mock_dur = mock_synth.synthesize("Fallback proporcional.", mock_wav)
    assert mock_dur > 0
    assert mock_synth.last_word_timestamps is None
    assert not stale_sidecar.exists()

    xtts = XTTSVoiceSynthesizer()

    class FakeTTS:
        def tts_to_file(self, **kwargs):
            Path(kwargs["file_path"]).write_bytes(b"RIFFXTTS")

    monkeypatch.setattr(xtts, "_load", lambda: FakeTTS())
    monkeypatch.setattr("viralpanel.studio.voice.probe_duration", lambda p: 2.0)

    xtts_wav = tmp_path / "xtts.wav"
    _, xtts_dur = xtts.synthesize("Teste XTTS", xtts_wav)
    assert xtts_dur == 2.0
    assert xtts.last_word_timestamps is None





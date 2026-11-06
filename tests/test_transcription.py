from pathlib import Path

from viralpanel.media.transcriber import MockTranscriber, TranscriptionSegment, WhisperTranscriber


def test_mock_transcription_segments_ordered_with_timestamps():
    result = MockTranscriber().transcribe(Path("audio.wav"))
    assert result.text
    assert len(result.segments) >= 3
    starts = [s.start for s in result.segments]
    assert starts == sorted(starts)
    assert all(s.end > s.start for s in result.segments)
    assert result.to_timestamped_text().startswith("[000.00-003.00]")


def test_whisper_hallucination_filtering():
    wt = WhisperTranscriber()
    segments = [
        TranscriptionSegment(start=0.0, end=2.0, text="Legendas por Paulo Montenegro."),
        TranscriptionSegment(start=2.0, end=5.0, text="Se você quer mudar de vida, mude seus hábitos."),
        TranscriptionSegment(start=5.0, end=7.0, text="Inscreva-se no canal e curta!"),
        TranscriptionSegment(start=7.0, end=10.0, text="Amara.org subtitles by user"),
    ]
    filtered = wt._filter_hallucinations(segments)
    assert len(filtered) == 1
    assert filtered[0].text == "Se você quer mudar de vida, mude seus hábitos."



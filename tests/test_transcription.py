from pathlib import Path

from viralpanel.media.transcriber import MockTranscriber


def test_mock_transcription_segments_ordered_with_timestamps():
    result = MockTranscriber().transcribe(Path("audio.wav"))
    assert result.text
    assert len(result.segments) >= 3
    starts = [s.start for s in result.segments]
    assert starts == sorted(starts)
    assert all(s.end > s.start for s in result.segments)
    assert result.to_timestamped_text().startswith("[000.00-003.00]")


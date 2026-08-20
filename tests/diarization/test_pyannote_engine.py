from pathlib import Path
from types import SimpleNamespace

from interview_intelligence.diarization.pyannote_engine import (
    PyannoteDiarizationEngine,
)


class FakeAnnotation:
    def itertracks(self, yield_label: bool = False):
        assert yield_label
        yield SimpleNamespace(start=0.5, end=2.0), None, "SPEAKER_00"
        yield SimpleNamespace(start=2.1, end=5.0), None, "SPEAKER_01"


class FakePipeline:
    def __call__(self, audio_path: str, num_speakers: int | None = None):
        assert num_speakers == 2
        return SimpleNamespace(speaker_diarization=FakeAnnotation())


def test_pyannote_engine_maps_turns(tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")

    engine = PyannoteDiarizationEngine()
    engine._pipeline = FakePipeline()

    result = engine.diarize(audio, num_speakers=2)

    assert result.speaker_count == 2
    assert len(result.turns) == 2
    assert result.turns[0].speaker_id == "SPEAKER_00"
    assert result.turns[1].start_seconds == 2.1

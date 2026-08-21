import subprocess
from pathlib import Path

import pytest

from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.engines.base import (
    TranscriptionEngine,
    TranscriptionRequest,
    TranscriptionResult,
)
from interview_intelligence.transcription.chunking import FixedWindowChunker
from interview_intelligence.transcription.runner import (
    ChunkedTranscriptionRunner,
    ChunkProgress,
)


class CountingEngine(TranscriptionEngine):
    def __init__(self) -> None:
        self.calls = 0

    def transcribe(
        self,
        request: TranscriptionRequest,
        progress_callback=None,
    ) -> TranscriptionResult:
        self.calls += 1
        return TranscriptionResult(
            language="en",
            text="hello",
            segments=[
                TranscriptSegment(
                    sequence_number=0,
                    start_seconds=6,
                    end_seconds=8,
                    text="hello",
                )
            ],
            engine_name="stub",
            model_name="stub-model",
        )


def fake_ffmpeg_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
    command = args[0]
    destination = Path(command[-1])  # type: ignore[index]
    destination.write_bytes(b"chunk")
    return subprocess.CompletedProcess(
        args=command,
        returncode=0,
        stdout="",
        stderr="",
    )


def test_runner_checkpoints_and_resumes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"audio")
    monkeypatch.setattr("subprocess.run", fake_ffmpeg_run)

    engine = CountingEngine()
    runner = ChunkedTranscriptionRunner(
        engine,
        chunker=FixedWindowChunker(chunk_seconds=10, overlap_seconds=2),
    )
    progress: list[ChunkProgress] = []

    first = runner.run(
        canonical_audio_path=source,
        duration_seconds=20,
        work_dir=tmp_path / "work",
        progress_listener=progress.append,
    )

    assert first.chunk_count == 2
    assert first.engine_name == "stub"
    assert first.model_name == "stub-model"
    assert engine.calls == 2
    assert [item.processed_audio_seconds for item in progress] == [10, 20]

    second_progress: list[ChunkProgress] = []
    second = runner.run(
        canonical_audio_path=source,
        duration_seconds=20,
        work_dir=tmp_path / "work",
        progress_listener=second_progress.append,
    )

    assert second.chunk_count == 2
    assert second.engine_name == "stub"
    assert second.model_name == "stub-model"
    assert engine.calls == 2
    assert all(item.resumed for item in second_progress)

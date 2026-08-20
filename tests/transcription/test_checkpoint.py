from pathlib import Path

from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.transcription.checkpoint import (
    CheckpointStore,
    ChunkCheckpoint,
)


def test_checkpoint_round_trip(tmp_path: Path) -> None:
    store = CheckpointStore(tmp_path / "checkpoints")
    checkpoint = ChunkCheckpoint(
        chunk_index=2,
        start_seconds=240,
        end_seconds=360,
        language="en",
        text="hello",
        segments=[
            TranscriptSegment(
                sequence_number=0,
                start_seconds=241,
                end_seconds=242,
                text="hello",
            )
        ],
    )

    store.save(checkpoint)
    loaded = store.load(2)

    assert loaded == checkpoint

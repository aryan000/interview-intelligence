from pathlib import Path

from pydantic import BaseModel

from interview_intelligence.domain.models import TranscriptSegment


class ChunkCheckpoint(BaseModel):
    chunk_index: int
    start_seconds: float
    end_seconds: float
    language: str | None = None
    text: str
    segments: list[TranscriptSegment]


class CheckpointStore:
    """Persist completed chunks so interrupted jobs can resume safely."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def load(self, chunk_index: int) -> ChunkCheckpoint | None:
        path = self._path(chunk_index)
        if not path.is_file():
            return None
        return ChunkCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, checkpoint: ChunkCheckpoint) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        destination = self._path(checkpoint.chunk_index)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(
            checkpoint.model_dump_json(indent=2),
            encoding="utf-8",
        )
        temporary.replace(destination)

    def _path(self, chunk_index: int) -> Path:
        return self.directory / f"chunk_{chunk_index:03d}.json"

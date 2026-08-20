from pathlib import Path

from pydantic import BaseModel, Field


class AudioMetadata(BaseModel):
    """Technical metadata discovered from an input recording."""

    path: Path
    container: str | None = None
    codec: str
    duration_seconds: float = Field(gt=0)
    sample_rate: int = Field(gt=0)
    channels: int = Field(gt=0)
    bit_rate: int | None = Field(default=None, ge=0)
    file_size_bytes: int = Field(ge=0)

    @property
    def is_mono(self) -> bool:
        return self.channels == 1

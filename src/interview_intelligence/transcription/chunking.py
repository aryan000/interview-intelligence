from dataclasses import dataclass


@dataclass(frozen=True)
class AudioChunk:
    index: int
    start_seconds: float
    end_seconds: float
    content_start_seconds: float
    content_end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


class FixedWindowChunker:
    """Split audio into windows with optional context overlap.

    The overlap is inference context only. Each chunk owns a non-overlapping
    content range, which prevents duplicated transcript segments when results
    are merged.
    """

    def __init__(
        self,
        chunk_seconds: float = 120.0,
        overlap_seconds: float = 5.0,
    ) -> None:
        if chunk_seconds <= 0:
            raise ValueError("chunk_seconds must be > 0")
        if overlap_seconds < 0:
            raise ValueError("overlap_seconds must be >= 0")
        if overlap_seconds >= chunk_seconds:
            raise ValueError("overlap_seconds must be < chunk_seconds")

        self.chunk_seconds = chunk_seconds
        self.overlap_seconds = overlap_seconds

    def create_chunks(self, duration_seconds: float) -> list[AudioChunk]:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be > 0")

        chunks: list[AudioChunk] = []
        content_start = 0.0
        index = 0

        while content_start < duration_seconds:
            content_end = min(content_start + self.chunk_seconds, duration_seconds)
            inference_start = max(0.0, content_start - self.overlap_seconds)
            inference_end = min(duration_seconds, content_end + self.overlap_seconds)

            chunks.append(
                AudioChunk(
                    index=index,
                    start_seconds=inference_start,
                    end_seconds=inference_end,
                    content_start_seconds=content_start,
                    content_end_seconds=content_end,
                )
            )

            content_start = content_end
            index += 1

        return chunks

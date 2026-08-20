import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.engines.base import TranscriptionEngine, TranscriptionRequest
from interview_intelligence.transcription.checkpoint import (
    CheckpointStore,
    ChunkCheckpoint,
)
from interview_intelligence.transcription.chunking import AudioChunk, FixedWindowChunker


@dataclass(frozen=True)
class ChunkProgress:
    completed_chunks: int
    total_chunks: int
    processed_audio_seconds: float
    total_audio_seconds: float
    elapsed_seconds: float
    resumed: bool = False

    @property
    def percent(self) -> float:
        return self.processed_audio_seconds / self.total_audio_seconds * 100.0

    @property
    def estimated_remaining_seconds(self) -> float | None:
        if self.processed_audio_seconds <= 0:
            return None
        rate = self.elapsed_seconds / self.processed_audio_seconds
        remaining_audio = self.total_audio_seconds - self.processed_audio_seconds
        return remaining_audio * rate


@dataclass(frozen=True)
class ChunkedTranscriptionResult:
    text: str
    segments: list[TranscriptSegment]
    language: str | None
    elapsed_seconds: float
    chunk_count: int


ProgressListener = Callable[[ChunkProgress], None]


class ChunkedTranscriptionRunner:
    def __init__(
        self,
        engine: TranscriptionEngine,
        chunker: FixedWindowChunker | None = None,
        ffmpeg_executable: str = "ffmpeg",
    ) -> None:
        self.engine = engine
        self.chunker = chunker or FixedWindowChunker()
        self.ffmpeg_executable = ffmpeg_executable

    def run(
        self,
        canonical_audio_path: Path,
        duration_seconds: float,
        work_dir: Path,
        initial_prompt: str | None = None,
        language: str | None = None,
        word_timestamps: bool = False,
        progress_listener: ProgressListener | None = None,
    ) -> ChunkedTranscriptionResult:
        work_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_store = CheckpointStore(work_dir / "checkpoints")
        chunks = self.chunker.create_chunks(duration_seconds)

        all_segments: list[TranscriptSegment] = []
        texts: list[str] = []
        detected_language: str | None = None
        started = time.perf_counter()

        for chunk in chunks:
            checkpoint = checkpoint_store.load(chunk.index)
            resumed = checkpoint is not None

            if checkpoint is None:
                checkpoint = self._transcribe_chunk(
                    canonical_audio_path=canonical_audio_path,
                    chunk=chunk,
                    work_dir=work_dir,
                    initial_prompt=initial_prompt,
                    language=language,
                    word_timestamps=word_timestamps,
                )
                checkpoint_store.save(checkpoint)

            if detected_language is None:
                detected_language = checkpoint.language

            if checkpoint.text:
                texts.append(checkpoint.text)

            for segment in checkpoint.segments:
                all_segments.append(
                    TranscriptSegment(
                        sequence_number=len(all_segments),
                        start_seconds=segment.start_seconds,
                        end_seconds=segment.end_seconds,
                        speaker_id=segment.speaker_id,
                        text=segment.text,
                        confidence=segment.confidence,
                    )
                )

            if progress_listener is not None:
                progress_listener(
                    ChunkProgress(
                        completed_chunks=chunk.index + 1,
                        total_chunks=len(chunks),
                        processed_audio_seconds=chunk.content_end_seconds,
                        total_audio_seconds=duration_seconds,
                        elapsed_seconds=time.perf_counter() - started,
                        resumed=resumed,
                    )
                )

        return ChunkedTranscriptionResult(
            text=" ".join(texts).strip(),
            segments=all_segments,
            language=detected_language,
            elapsed_seconds=time.perf_counter() - started,
            chunk_count=len(chunks),
        )

    def _transcribe_chunk(
        self,
        canonical_audio_path: Path,
        chunk: AudioChunk,
        work_dir: Path,
        initial_prompt: str | None,
        language: str | None,
        word_timestamps: bool,
    ) -> ChunkCheckpoint:
        chunk_path = work_dir / f"chunk_{chunk.index:03d}.wav"

        self._extract_chunk(
            canonical_audio_path,
            chunk_path,
            chunk.start_seconds,
            chunk.duration_seconds,
        )

        try:
            result = self.engine.transcribe(
                TranscriptionRequest(
                    audio_path=chunk_path,
                    language=language,
                    initial_prompt=initial_prompt,
                    word_timestamps=word_timestamps,
                )
            )
        finally:
            chunk_path.unlink(missing_ok=True)

        owned_segments: list[TranscriptSegment] = []

        for segment in result.segments:
            absolute_start = segment.start_seconds + chunk.start_seconds
            absolute_end = segment.end_seconds + chunk.start_seconds
            midpoint = (absolute_start + absolute_end) / 2.0

            # Overlap supplies context to Whisper, but ownership is determined
            # by the segment midpoint. This prevents duplicate adjacent output.
            if not (
                chunk.content_start_seconds
                <= midpoint
                < chunk.content_end_seconds
            ):
                continue

            owned_segments.append(
                TranscriptSegment(
                    sequence_number=len(owned_segments),
                    start_seconds=absolute_start,
                    end_seconds=absolute_end,
                    speaker_id=segment.speaker_id,
                    text=segment.text,
                    confidence=segment.confidence,
                )
            )

        text = " ".join(segment.text for segment in owned_segments).strip()

        return ChunkCheckpoint(
            chunk_index=chunk.index,
            start_seconds=chunk.content_start_seconds,
            end_seconds=chunk.content_end_seconds,
            language=result.language,
            text=text,
            segments=owned_segments,
        )

    def _extract_chunk(
        self,
        source: Path,
        destination: Path,
        start_seconds: float,
        duration_seconds: float,
    ) -> None:
        command = [
            self.ffmpeg_executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(start_seconds),
            "-i",
            str(source),
            "-t",
            str(duration_seconds),
            "-c:a",
            "pcm_s16le",
            "-y",
            str(destination),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"{self.ffmpeg_executable!r} was not found on PATH"
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or "unknown FFmpeg error"
            raise RuntimeError(f"Failed to extract audio chunk: {detail}") from exc

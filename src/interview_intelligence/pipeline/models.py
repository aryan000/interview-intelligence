from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from interview_intelligence.audio.models import AudioMetadata
from interview_intelligence.quality.models import QualityIssue


class InterviewProcessingRequest(BaseModel):
    source_audio: Path
    company: str
    recruiter_or_interviewer: str
    sequence_number: int = Field(default=1, ge=1)
    interview_datetime: datetime
    num_speakers: int = Field(default=2, ge=1)
    role: str | None = None
    target_level: str | None = None


class ProcessedTranscriptSegment(BaseModel):
    sequence_number: int = Field(ge=0)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    speaker_id: str | None = None
    speaker_role: str | None = None
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    quality_flags: list[str] = Field(default_factory=list)


class InterviewArtifactPaths(BaseModel):
    root_dir: Path
    original_audio: Path
    transcript_text: Path
    transcript_json: Path
    metadata_json: Path
    quality_json: Path


class InterviewProcessingResult(BaseModel):
    source_metadata: AudioMetadata
    prepared_metadata: AudioMetadata
    segments: list[ProcessedTranscriptSegment]
    quality_issues: list[QualityIssue]
    candidate_speaker_id: str | None
    interviewer_speaker_id: str | None
    speaker_mapping_confidence: float
    artifacts: InterviewArtifactPaths
    transcription_seconds: float
    diarization_seconds: float
    total_seconds: float

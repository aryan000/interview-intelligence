from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(StrEnum):
    INSPECTION = "inspection"
    PREPROCESSING = "preprocessing"
    VAD = "vad"
    TRANSCRIPTION = "transcription"
    DIARIZATION = "diarization"
    ALIGNMENT = "alignment"
    EXPORT = "export"
    CLOUD_SYNC = "cloud_sync"
    COMPLETED = "completed"


class SpeakerType(StrEnum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    UNKNOWN = "unknown"


class SyncStatus(StrEnum):
    NOT_SYNCED = "not_synced"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"

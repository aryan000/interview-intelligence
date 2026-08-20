from enum import StrEnum

from pydantic import BaseModel, Field


class QualityFlag(StrEnum):
    REPETITION_LOOP = "repetition_loop"
    ZERO_DURATION_TEXT = "zero_duration_text"
    SUSPICIOUS_TOKEN = "suspicious_token"


class QualityIssue(BaseModel):
    flag: QualityFlag
    segment_index: int = Field(ge=0)
    message: str
    severity: str

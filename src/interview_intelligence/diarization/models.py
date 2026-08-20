from pydantic import BaseModel, Field, model_validator


class SpeakerTurn(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    speaker_id: str

    @model_validator(mode="after")
    def validate_range(self) -> "SpeakerTurn":
        if self.end_seconds < self.start_seconds:
            raise ValueError("end_seconds must be >= start_seconds")
        return self


class DiarizationResult(BaseModel):
    turns: list[SpeakerTurn]
    speaker_count: int
    engine_name: str
    model_name: str

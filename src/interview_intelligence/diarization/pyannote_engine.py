from pathlib import Path
from typing import Any

import torch

from interview_intelligence.diarization.models import (
    DiarizationResult,
    SpeakerTurn,
)


class PyannoteDiarizationEngine:
    """Local speaker diarization backed by pyannote.audio."""

    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization-community-1",
        token: str | None = None,
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.token = token
        self.device = device or self._default_device()
        self._pipeline: Any | None = None

    def diarize(
        self,
        audio_path: Path,
        num_speakers: int | None = 2,
    ) -> DiarizationResult:
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)

        pipeline = self._get_pipeline()
        output = pipeline(
            str(audio_path),
            num_speakers=num_speakers,
        )

        annotation = getattr(output, "speaker_diarization", output)
        turns: list[SpeakerTurn] = []

        for turn, _, speaker in annotation.itertracks(yield_label=True):
            turns.append(
                SpeakerTurn(
                    start_seconds=float(turn.start),
                    end_seconds=float(turn.end),
                    speaker_id=str(speaker),
                )
            )

        speaker_ids = {turn.speaker_id for turn in turns}

        return DiarizationResult(
            turns=turns,
            speaker_count=len(speaker_ids),
            engine_name="pyannote.audio",
            model_name=self.model_name,
        )

    def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        from pyannote.audio import Pipeline

        kwargs: dict[str, Any] = {}
        if self.token:
            kwargs["token"] = self.token

        pipeline = Pipeline.from_pretrained(self.model_name, **kwargs)
        if pipeline is None:
            raise RuntimeError(
                f"Could not load pyannote pipeline {self.model_name!r}. "
                "If the model is gated, accept its Hugging Face terms and "
                "provide a token."
            )

        pipeline.to(torch.device(self.device))
        self._pipeline = pipeline
        return pipeline

    @staticmethod
    def _default_device() -> str:
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

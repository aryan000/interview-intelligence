from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from interview_intelligence.domain.models import (
    Interview,
    SilenceInterval,
    TranscriptSegment,
)


def test_interview_company_is_trimmed() -> None:
    interview = Interview(
        company="  Navi  ",
        interview_date=datetime.now(UTC),
    )

    assert interview.company == "Navi"


def test_blank_company_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Interview(company="   ", interview_date=datetime.now(UTC))


def test_transcript_segment_rejects_invalid_time_range() -> None:
    with pytest.raises(ValidationError):
        TranscriptSegment(
            sequence_number=0,
            start_seconds=10,
            end_seconds=9,
            speaker_id="SPEAKER_01",
            text="hello",
        )


def test_silence_duration() -> None:
    interval = SilenceInterval(start_seconds=10.0, end_seconds=25.5)

    assert interval.duration_seconds == 15.5


def test_interview_generates_id() -> None:
    interview = Interview(
        company="LinkedIn",
        interview_date=datetime.now(UTC),
    )

    assert interview.id != uuid4()

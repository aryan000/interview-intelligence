import pytest

from interview_intelligence.transcription.chunking import FixedWindowChunker


def test_chunker_adds_context_overlap_without_changing_content_ownership() -> None:
    chunks = FixedWindowChunker(
        chunk_seconds=120,
        overlap_seconds=5,
    ).create_chunks(300)

    assert len(chunks) == 3

    assert chunks[0].start_seconds == 0
    assert chunks[0].end_seconds == 125
    assert chunks[0].content_start_seconds == 0
    assert chunks[0].content_end_seconds == 120

    assert chunks[1].start_seconds == 115
    assert chunks[1].end_seconds == 245
    assert chunks[1].content_start_seconds == 120
    assert chunks[1].content_end_seconds == 240

    assert chunks[2].start_seconds == 235
    assert chunks[2].end_seconds == 300
    assert chunks[2].content_start_seconds == 240
    assert chunks[2].content_end_seconds == 300


def test_chunker_rejects_overlap_larger_than_window() -> None:
    with pytest.raises(ValueError):
        FixedWindowChunker(chunk_seconds=60, overlap_seconds=60)

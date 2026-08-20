import time
from collections import defaultdict

from interview_intelligence.audio.inspector import AudioInspector
from interview_intelligence.audio.preparer import AudioPreparer
from interview_intelligence.diarization.aligner import SpeakerAligner
from interview_intelligence.diarization.pyannote_engine import (
    PyannoteDiarizationEngine,
)
from interview_intelligence.diarization.roles import SpeakerRoleMapper
from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.engines.base import (
    TranscriptionEngine,
    TranscriptionRequest,
)
from interview_intelligence.engines.vocabulary import build_interview_prompt
from interview_intelligence.pipeline.exporter import InterviewArtifactExporter
from interview_intelligence.pipeline.models import (
    InterviewProcessingRequest,
    InterviewProcessingResult,
    ProcessedTranscriptSegment,
)
from interview_intelligence.quality.detector import TranscriptQualityDetector
from interview_intelligence.transcription.sanitizer import TranscriptTimelineSanitizer


class InterviewProcessingPipeline:
    """Orchestrate local interview processing into stable production artifacts."""

    def __init__(
        self,
        inspector: AudioInspector,
        preparer: AudioPreparer,
        transcription_engine: TranscriptionEngine,
        diarization_engine: PyannoteDiarizationEngine,
        exporter: InterviewArtifactExporter,
        quality_detector: TranscriptQualityDetector | None = None,
        speaker_aligner: SpeakerAligner | None = None,
        role_mapper: SpeakerRoleMapper | None = None,
        timeline_sanitizer: TranscriptTimelineSanitizer | None = None,
    ) -> None:
        self.inspector = inspector
        self.preparer = preparer
        self.transcription_engine = transcription_engine
        self.diarization_engine = diarization_engine
        self.exporter = exporter
        self.quality_detector = quality_detector or TranscriptQualityDetector()
        self.speaker_aligner = speaker_aligner or SpeakerAligner()
        self.role_mapper = role_mapper or SpeakerRoleMapper()
        self.timeline_sanitizer = timeline_sanitizer or TranscriptTimelineSanitizer()

    def process(
        self,
        request: InterviewProcessingRequest,
    ) -> InterviewProcessingResult:
        total_started = time.perf_counter()

        source_metadata = self.inspector.inspect(request.source_audio)
        artifact_paths = self.exporter.build_paths(request)
        work_dir = artifact_paths.root_dir / ".work"
        work_dir.mkdir(parents=True, exist_ok=True)
        prepared_path = work_dir / "canonical.wav"

        preparation = self.preparer.prepare(
            request.source_audio,
            prepared_path,
        )

        transcription_started = time.perf_counter()
        transcription = self.transcription_engine.transcribe(
            TranscriptionRequest(
                audio_path=prepared_path,
                initial_prompt=build_interview_prompt(
                    company=request.company,
                ),
            )
        )
        transcription_seconds = time.perf_counter() - transcription_started

        sanitization = self.timeline_sanitizer.sanitize(
            transcription.segments,
            preparation.prepared.duration_seconds,
        )
        sanitized_segments = sanitization.segments

        quality_issues = self.quality_detector.detect(sanitized_segments)

        diarization_started = time.perf_counter()
        diarization = self.diarization_engine.diarize(
            prepared_path,
            num_speakers=request.num_speakers,
        )
        diarization_seconds = time.perf_counter() - diarization_started

        aligned = self.speaker_aligner.align(
            sanitized_segments,
            diarization.turns,
        )
        role_mapping = self.role_mapper.map_roles(aligned)

        issues_by_segment: dict[int, list[str]] = defaultdict(list)
        for issue in quality_issues:
            issues_by_segment[issue.segment_index].append(issue.flag.value)

        processed_segments: list[ProcessedTranscriptSegment] = []
        for segment in aligned:
            processed_segments.append(
                ProcessedTranscriptSegment(
                    sequence_number=segment.sequence_number,
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    speaker_id=segment.speaker_id,
                    speaker_role=self._speaker_role(
                        segment,
                        role_mapping.candidate_speaker_id,
                        role_mapping.interviewer_speaker_id,
                    ),
                    text=segment.text,
                    confidence=segment.confidence,
                    quality_flags=issues_by_segment.get(
                        segment.sequence_number,
                        [],
                    ),
                )
            )

        metadata: dict[str, object] = {
            "company": request.company,
            "recruiter_or_interviewer": request.recruiter_or_interviewer,
            "sequence_number": request.sequence_number,
            "interview_datetime": request.interview_datetime.isoformat(),
            "role": request.role,
            "target_level": request.target_level,
            "source_audio": str(request.source_audio),
            "source_metadata": source_metadata.model_dump(mode="json"),
            "prepared_metadata": preparation.prepared.model_dump(mode="json"),
            "preparation_warnings": list(preparation.warnings),
            "transcription_engine": transcription.engine_name,
            "transcription_model": transcription.model_name,
            "diarization_engine": diarization.engine_name,
            "diarization_model": diarization.model_name,
            "candidate_speaker_id": role_mapping.candidate_speaker_id,
            "interviewer_speaker_id": role_mapping.interviewer_speaker_id,
            "speaker_mapping_confidence": role_mapping.confidence,
            "speaker_mapping_reason": role_mapping.reason,
            "timeline_dropped_out_of_bounds": sanitization.dropped_out_of_bounds,
            "timeline_clamped_segments": sanitization.clamped_segments,
        }

        self.exporter.export(
            request=request,
            paths=artifact_paths,
            segments=processed_segments,
            quality_issues=quality_issues,
            metadata=metadata,
        )

        prepared_path.unlink(missing_ok=True)
        try:
            work_dir.rmdir()
        except OSError:
            pass

        return InterviewProcessingResult(
            source_metadata=source_metadata,
            prepared_metadata=preparation.prepared,
            segments=processed_segments,
            quality_issues=quality_issues,
            candidate_speaker_id=role_mapping.candidate_speaker_id,
            interviewer_speaker_id=role_mapping.interviewer_speaker_id,
            speaker_mapping_confidence=role_mapping.confidence,
            artifacts=artifact_paths,
            transcription_seconds=transcription_seconds,
            diarization_seconds=diarization_seconds,
            total_seconds=time.perf_counter() - total_started,
        )

    @staticmethod
    def _speaker_role(
        segment: TranscriptSegment,
        candidate_speaker_id: str | None,
        interviewer_speaker_id: str | None,
    ) -> str | None:
        if segment.speaker_id == candidate_speaker_id:
            return "Candidate"
        if segment.speaker_id == interviewer_speaker_id:
            return "Interviewer"
        return None

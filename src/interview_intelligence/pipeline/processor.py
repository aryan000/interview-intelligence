import time
from collections import defaultdict
from collections.abc import Callable

from interview_intelligence.audio.inspector import AudioInspector
from interview_intelligence.audio.preparer import AudioPreparer
from interview_intelligence.diarization.aligner import SpeakerAligner
from interview_intelligence.diarization.pyannote_engine import (
    PyannoteDiarizationEngine,
)
from interview_intelligence.diarization.roles import SpeakerRoleMapper
from interview_intelligence.domain.enums import JobStage
from interview_intelligence.domain.models import TranscriptSegment
from interview_intelligence.engines.base import (
    TranscriptionEngine,
    TranscriptionRequest,
    TranscriptionResult,
)
from interview_intelligence.engines.vocabulary import build_interview_prompt
from interview_intelligence.pipeline.exporter import InterviewArtifactExporter
from interview_intelligence.pipeline.models import (
    InterviewProcessingRequest,
    InterviewProcessingResult,
    ProcessedTranscriptSegment,
)
from interview_intelligence.quality.detector import TranscriptQualityDetector
from interview_intelligence.transcription.runner import (
    ChunkedTranscriptionRunner,
    ChunkProgress,
)
from interview_intelligence.transcription.sanitizer import TranscriptTimelineSanitizer

PipelineProgressCallback = Callable[[JobStage, float, float, str], None]


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
        transcription_runner: ChunkedTranscriptionRunner | None = None,
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
        self.transcription_runner = transcription_runner

    def process(
        self,
        request: InterviewProcessingRequest,
        progress_callback: PipelineProgressCallback | None = None,
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
        self._report_progress(
            progress_callback,
            JobStage.PREPROCESSING,
            10,
            0,
            "Canonical audio prepared",
        )
        self._report_progress(
            progress_callback,
            JobStage.TRANSCRIPTION,
            12,
            0,
            "Transcribing interview",
        )

        transcription_started = time.perf_counter()
        interview_prompt = build_interview_prompt(company=request.company)

        if self.transcription_runner is None:
            transcription = self.transcription_engine.transcribe(
                TranscriptionRequest(
                    audio_path=prepared_path,
                    initial_prompt=interview_prompt,
                )
            )
        else:
            chunked = self.transcription_runner.run(
                canonical_audio_path=prepared_path,
                duration_seconds=preparation.prepared.duration_seconds,
                work_dir=work_dir / "transcription",
                initial_prompt=interview_prompt,
                progress_listener=lambda progress: self._report_chunk_progress(
                    progress_callback,
                    progress,
                ),
            )
            transcription = TranscriptionResult(
                language=chunked.language,
                text=chunked.text,
                segments=chunked.segments,
                engine_name=chunked.engine_name,
                model_name=chunked.model_name,
            )

        transcription_seconds = time.perf_counter() - transcription_started
        self._report_progress(
            progress_callback,
            JobStage.TRANSCRIPTION,
            70,
            preparation.prepared.duration_seconds,
            "Transcription complete",
        )

        sanitization = self.timeline_sanitizer.sanitize(
            transcription.segments,
            preparation.prepared.duration_seconds,
        )
        sanitized_segments = sanitization.segments

        quality_issues = self.quality_detector.detect(sanitized_segments)

        self._report_progress(
            progress_callback,
            JobStage.DIARIZATION,
            72,
            preparation.prepared.duration_seconds,
            "Identifying speakers",
        )
        diarization_started = time.perf_counter()
        diarization = self.diarization_engine.diarize(
            prepared_path,
            num_speakers=request.num_speakers,
        )
        diarization_seconds = time.perf_counter() - diarization_started
        self._report_progress(
            progress_callback,
            JobStage.DIARIZATION,
            88,
            preparation.prepared.duration_seconds,
            "Speaker diarization complete",
        )
        self._report_progress(
            progress_callback,
            JobStage.ALIGNMENT,
            90,
            preparation.prepared.duration_seconds,
            "Aligning speakers to transcript",
        )

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

        self._report_progress(
            progress_callback,
            JobStage.ALIGNMENT,
            94,
            preparation.prepared.duration_seconds,
            "Speaker alignment complete",
        )
        self._report_progress(
            progress_callback,
            JobStage.EXPORT,
            96,
            preparation.prepared.duration_seconds,
            "Exporting artifacts",
        )

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
    def _report_chunk_progress(
        callback: PipelineProgressCallback | None,
        progress: ChunkProgress,
    ) -> None:
        overall_percent = 12.0 + (progress.percent / 100.0) * 58.0
        processed = InterviewProcessingPipeline._format_audio_time(
            progress.processed_audio_seconds
        )
        total = InterviewProcessingPipeline._format_audio_time(
            progress.total_audio_seconds
        )
        resume_suffix = " · resumed" if progress.resumed else ""

        InterviewProcessingPipeline._report_progress(
            callback,
            JobStage.TRANSCRIPTION,
            overall_percent,
            progress.processed_audio_seconds,
            (
                f"Transcribing chunk {progress.completed_chunks}/"
                f"{progress.total_chunks} · {processed} / {total}"
                f"{resume_suffix}"
            ),
        )

    @staticmethod
    def _format_audio_time(seconds: float) -> str:
        total_seconds = max(0, int(round(seconds)))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _report_progress(
        callback: PipelineProgressCallback | None,
        stage: JobStage,
        progress_percent: float,
        processed_audio_seconds: float,
        message: str,
    ) -> None:
        if callback is not None:
            callback(stage, progress_percent, processed_audio_seconds, message)

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

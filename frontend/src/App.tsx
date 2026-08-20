import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  analyzeInterview,
  deleteInterview,
  getAudioUrl,
  getInterviewReview,
  getLatestInterviewJob,
  getTranscript,
  getTranscriptDownloadUrl,
  listInterviews,
  processInterview,
  subscribeToJob,
  uploadInterview,
} from "./api";
import type { Interview, InterviewReview, JobEvent, TranscriptLine } from "./types";

type UploadFormState = {
  company: string;
  interviewer: string;
  datetime: string;
  sequence: number;
  role: string;
  targetLevel: string;
  audio: File | null;
};

type Screen = "workspace" | "transcript";
type TranscriptTab = "transcript" | "review";

const emptyUploadForm: UploadFormState = {
  company: "",
  interviewer: "",
  datetime: "",
  sequence: 1,
  role: "Engineering Manager",
  targetLevel: "",
  audio: null,
};

function formatDuration(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "—";
  }

  const totalSeconds = Math.max(0, Math.round(value));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function statusLabel(interview: Interview): string {
  return interview.artifact_root_path ? "Ready" : "Not processed";
}

function stageLabel(stage: string): string {
  return stage
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const PROCESSING_STAGES = [
  "preprocessing",
  "transcription",
  "diarization",
  "alignment",
  "export",
] as const;

function formatElapsed(totalSeconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatClockTime(value: Date): string {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(value);
}

function stageState(
  stage: (typeof PROCESSING_STAGES)[number],
  currentStage: string,
  status: JobEvent["status"],
): "completed" | "active" | "pending" {
  if (status === "completed") {
    return "completed";
  }

  const currentIndex = PROCESSING_STAGES.indexOf(
    currentStage as (typeof PROCESSING_STAGES)[number],
  );
  const stageIndex = PROCESSING_STAGES.indexOf(stage);

  if (currentIndex === -1) {
    return stage === "preprocessing" ? "active" : "pending";
  }

  if (stageIndex < currentIndex) return "completed";
  if (stageIndex === currentIndex) return "active";
  return "pending";
}

function timestampToSeconds(value: string): number {
  const parts = value.split(":").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return 0;
  return parts[0] * 3600 + parts[1] * 60 + parts[2];
}

function hiringSignalLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function parseTranscript(raw: string): TranscriptLine[] {
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^\[(.*?)\s*->\s*(.*?)\]\s+([^:]+):\s*(.*)$/);

      if (!match) {
        return {
          start: "",
          end: "",
          startSeconds: 0,
          endSeconds: 0,
          speaker: "Unknown",
          text: line,
        };
      }

      return {
        start: match[1],
        end: match[2],
        startSeconds: timestampToSeconds(match[1]),
        endSeconds: timestampToSeconds(match[2]),
        speaker: match[3].replace(/\s*\[QUALITY:.*?\]\s*$/, "").trim(),
        text: match[4],
      };
    });
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("workspace");
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadForm, setUploadForm] = useState<UploadFormState>(emptyUploadForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [activeInterview, setActiveInterview] = useState<Interview | null>(null);
  const [jobEvent, setJobEvent] = useState<JobEvent | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [processingStartedAt, setProcessingStartedAt] = useState<Date | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const [transcriptLines, setTranscriptLines] = useState<TranscriptLine[]>([]);
  const [isTranscriptLoading, setIsTranscriptLoading] = useState(false);
  const [transcriptError, setTranscriptError] = useState<string | null>(null);
  const [currentAudioTime, setCurrentAudioTime] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [transcriptTab, setTranscriptTab] = useState<TranscriptTab>("transcript");
  const [review, setReview] = useState<InterviewReview | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<Interview | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const refreshInterviews = async (): Promise<Interview[]> => {
    const data = await listInterviews();
    setInterviews(data);
    return data;
  };

  useEffect(() => {
    let unsubscribe: (() => void) | null = null;

    const load = async () => {
      try {
        const loaded = await refreshInterviews();

        for (const interview of loaded) {
          const latestJob = await getLatestInterviewJob(interview.id);
          if (
            latestJob &&
            (latestJob.status === "queued" || latestJob.status === "running")
          ) {
            setActiveInterview(interview);
            setJobEvent(latestJob);

            const startedAt = latestJob.started_at
              ? new Date(latestJob.started_at)
              : latestJob.created_at
                ? new Date(latestJob.created_at)
                : new Date();

            setProcessingStartedAt(startedAt);
            setElapsedSeconds((Date.now() - startedAt.getTime()) / 1000);

            unsubscribe = subscribeToJob(
              latestJob.job_id,
              (nextEvent) => {
                setJobEvent(nextEvent);
                if (nextEvent.status === "completed") {
                  void refreshInterviews();
                }
              },
              (socketError) => setJobError(socketError.message),
            );
            break;
          }
        }
      } catch (caught: unknown) {
        setError(caught instanceof Error ? caught.message : "Unable to load interviews.");
      } finally {
        setIsLoading(false);
      }
    };

    void load();

    return () => unsubscribe?.();
  }, []);

  useEffect(() => {
    if (!processingStartedAt || !jobEvent || jobEvent.status === "completed" || jobEvent.status === "failed") {
      return;
    }

    const updateElapsed = () => {
      setElapsedSeconds((Date.now() - processingStartedAt.getTime()) / 1000);
    };

    updateElapsed();
    const timer = window.setInterval(updateElapsed, 1000);

    return () => window.clearInterval(timer);
  }, [processingStartedAt, jobEvent?.status]);

  const readyCount = useMemo(
    () => interviews.filter((item) => item.artifact_root_path).length,
    [interviews],
  );

  const openTranscript = async (interview: Interview) => {
    if (!interview.artifact_root_path) {
      return;
    }

    setActiveInterview(interview);
    setIsTranscriptLoading(true);
    setTranscriptError(null);
    setScreen("transcript");
    setTranscriptTab("transcript");
    setReview(null);
    setReviewError(null);

    try {
      const [response, existingReview] = await Promise.all([
        getTranscript(interview.id),
        getInterviewReview(interview.id),
      ]);
      setTranscriptLines(parseTranscript(response.transcript));
      setReview(existingReview);
    } catch (caught: unknown) {
      setTranscriptError(
        caught instanceof Error ? caught.message : "Unable to load transcript.",
      );
    } finally {
      setIsTranscriptLoading(false);
    }
  };

  const handleAnalyzeInterview = async () => {
    if (!activeInterview) return;

    setIsAnalyzing(true);
    setReviewError(null);

    try {
      const result = await analyzeInterview(activeInterview.id);
      setReview(result);
      setTranscriptTab("review");
    } catch (caught: unknown) {
      setReviewError(
        caught instanceof Error ? caught.message : "Unable to analyze interview.",
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const seekTo = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = seconds;
    void audio.play();
  };

  const handleDeleteInterview = async () => {
    if (!deleteTarget) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteInterview(deleteTarget.id);
      setInterviews((current) =>
        current.filter((interview) => interview.id !== deleteTarget.id),
      );

      if (activeInterview?.id === deleteTarget.id) {
        setActiveInterview(null);
        setJobEvent(null);
      }

      setDeleteTarget(null);
    } catch (caught: unknown) {
      setDeleteError(
        caught instanceof Error ? caught.message : "Unable to delete interview.",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const closeUpload = () => {
    if (isSubmitting) return;
    setIsUploadOpen(false);
    setSubmitError(null);
    setUploadForm(emptyUploadForm);
  };

  const handleUploadSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!uploadForm.audio) {
      setSubmitError("Choose an audio file first.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const interview = await uploadInterview({
        audio: uploadForm.audio,
        company: uploadForm.company,
        recruiterOrInterviewer: uploadForm.interviewer,
        interviewDatetime: uploadForm.datetime,
        sequenceNumber: uploadForm.sequence,
        role: uploadForm.role,
        targetLevel: uploadForm.targetLevel,
      });

      const processResult = await processInterview(interview.id);

      const startedAt = new Date();
      setProcessingStartedAt(startedAt);
      setElapsedSeconds(0);
      setActiveInterview(interview);
      setJobEvent({
        job_id: processResult.job_id,
        interview_id: processResult.interview_id,
        status: processResult.status as JobEvent["status"],
        stage: "inspection",
        progress_percent: 0,
        processed_audio_seconds: 0,
        total_audio_seconds: 0,
        message: "Starting processing",
      });

      setIsUploadOpen(false);
      setUploadForm(emptyUploadForm);

      subscribeToJob(
        processResult.job_id,
        (nextEvent) => {
          setJobEvent(nextEvent);

          if (nextEvent.status === "completed") {
            void refreshInterviews().then((nextInterviews) => {
              const refreshed = nextInterviews.find((item) => item.id === interview.id);
              if (refreshed) setActiveInterview(refreshed);
            });
          }
        },
        (socketError) => setJobError(socketError.message),
      );
    } catch (caught: unknown) {
      setSubmitError(
        caught instanceof Error ? caught.message : "Unable to start processing.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (screen === "transcript" && activeInterview) {
    return (
      <div className="app-shell">
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-mark">II</div>
            <div>
              <div className="brand-name">Interview Intelligence</div>
              <div className="brand-subtitle">Private interview workspace</div>
            </div>
          </div>

          <nav className="nav">
            <button
              className="nav-item"
              type="button"
              onClick={() => setScreen("workspace")}
            >
              <span className="nav-icon">◫</span>
              Interviews
            </button>
            <button className="nav-item nav-item-active" type="button">
              <span className="nav-icon">◌</span>
              Transcript Studio
            </button>
          </nav>

          <div className="sidebar-footer">
            <div className="privacy-pill">Local-first</div>
            <p>Your recordings stay on this machine unless you explicitly share them.</p>
          </div>
        </aside>

        <main className="main transcript-main">
          <button className="back-button" type="button" onClick={() => setScreen("workspace")}>
            ← Back to interviews
          </button>

          <header className="transcript-header">
            <div>
              <p className="eyebrow">TRANSCRIPT STUDIO</p>
              <h1>{activeInterview.company}</h1>
              <p className="page-subtitle">
                {activeInterview.role ?? "Interview"} · Round {activeInterview.sequence_number} ·{" "}
                {activeInterview.recruiter_or_interviewer}
              </p>
            </div>

            <div className="transcript-header-actions">
              <a
                className="secondary-button download-button"
                href={getTranscriptDownloadUrl(activeInterview.id)}
              >
                ↓ Download transcript
              </a>
              <div className="transcript-meta-card">
                <span>{formatDate(activeInterview.interview_datetime)}</span>
                <strong>{transcriptLines.length} segments</strong>
              </div>
            </div>
          </header>

          <section className="audio-player-card">
            <div className="audio-player-copy">
              <span className="insight-label">RECORDING</span>
              <strong>Interview audio</strong>
              <p>Click any transcript segment to jump to that moment.</p>
            </div>
            <audio
              className="audio-player"
              controls
              ref={audioRef}
              src={getAudioUrl(activeInterview.id)}
              onTimeUpdate={(event) => setCurrentAudioTime(event.currentTarget.currentTime)}
            />
          </section>

          <div className="studio-tabs" role="tablist" aria-label="Interview studio views">
            <button
              className={transcriptTab === "transcript" ? "studio-tab studio-tab-active" : "studio-tab"}
              type="button"
              onClick={() => setTranscriptTab("transcript")}
            >
              Transcript
            </button>
            <button
              className={transcriptTab === "review" ? "studio-tab studio-tab-active" : "studio-tab"}
              type="button"
              onClick={() => setTranscriptTab("review")}
            >
              AI Review
              {review && <span className="review-dot" />}
            </button>
          </div>

          <section className="transcript-layout">
            <div className="transcript-panel">
              {transcriptTab === "transcript" ? (
                <>
                  <div className="transcript-toolbar">
                    <div>
                      <h2>Conversation</h2>
                      <p>Speaker-labelled transcript with timeline context.</p>
                    </div>
                    <div className="transcript-status">Ready</div>
                  </div>

                  {isTranscriptLoading ? (
                    <div className="empty-state">Loading transcript…</div>
                  ) : transcriptError ? (
                    <div className="empty-state error-state">{transcriptError}</div>
                  ) : (
                    <div className="transcript-list">
                      {transcriptLines.map((line, index) => {
                        const isCandidate = line.speaker.toLowerCase().includes("candidate");
                        const isInterviewer = line.speaker.toLowerCase().includes("interviewer");
                        const isActive =
                          currentAudioTime >= line.startSeconds &&
                          currentAudioTime < Math.max(line.endSeconds, line.startSeconds + 1);

                        return (
                          <article
                            className={`transcript-segment ${
                              isCandidate ? "candidate-segment" : ""
                            } ${isActive ? "active-segment" : ""}`}
                            key={`${line.start}-${index}`}
                            onClick={() => seekTo(line.startSeconds)}
                          >
                            <div className="segment-time">{line.start}</div>
                            <div className="segment-content">
                              <div className="segment-speaker-row">
                                <span
                                  className={`speaker-pill ${
                                    isCandidate
                                      ? "speaker-candidate"
                                      : isInterviewer
                                        ? "speaker-interviewer"
                                        : "speaker-unknown"
                                  }`}
                                >
                                  {line.speaker}
                                </span>
                                {line.end && <span className="segment-end">to {line.end}</span>}
                              </div>
                              <p>{line.text}</p>
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  )}
                </>
              ) : (
                <div className="review-view">
                  {!review ? (
                    <div className="review-empty">
                      <div className="review-empty-icon">✦</div>
                      <p className="eyebrow">AI INTERVIEW REVIEW</p>
                      <h2>Turn this transcript into feedback</h2>
                      <p>
                        Analyze questions, answer quality, strengths, gaps, level signal,
                        and the overall hiring signal.
                      </p>
                      {reviewError && <div className="inline-error">{reviewError}</div>}
                      <button
                        className="primary-button analyze-button"
                        type="button"
                        disabled={isAnalyzing}
                        onClick={() => void handleAnalyzeInterview()}
                      >
                        {isAnalyzing ? "Analyzing interview…" : "✦ Analyze interview"}
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="review-hero">
                        <div>
                          <p className="eyebrow">AI INTERVIEW REVIEW</p>
                          <div className="review-title-row">
                            <h2>{hiringSignalLabel(review.hiring_signal)}</h2>
                            <span className={`hiring-signal signal-${review.hiring_signal}`}>
                              {hiringSignalLabel(review.hiring_signal)}
                            </span>
                          </div>
                          <p>{review.overall_summary}</p>
                        </div>
                        <div className="review-model">
                          <span>Assessment</span>
                          <strong>{Math.round(review.confidence * 100)}%</strong>
                          <small>{review.model}</small>
                        </div>
                      </div>

                      <div className="review-summary-grid">
                        <section className="review-summary-card">
                          <span className="review-section-label">STRENGTHS</span>
                          <ul>
                            {review.strengths.map((item) => <li key={item}>{item}</li>)}
                          </ul>
                        </section>
                        <section className="review-summary-card">
                          <span className="review-section-label">CONCERNS</span>
                          <ul>
                            {review.concerns.map((item) => <li key={item}>{item}</li>)}
                          </ul>
                        </section>
                        <section className="review-summary-card">
                          <span className="review-section-label">IMPROVEMENT AREAS</span>
                          <ul>
                            {review.improvement_areas.map((item) => <li key={item}>{item}</li>)}
                          </ul>
                        </section>
                      </div>

                      {(review.role_signal || review.level_signal) && (
                        <div className="review-signal-row">
                          {review.role_signal && (
                            <div>
                              <span className="review-section-label">ROLE SIGNAL</span>
                              <p>{review.role_signal}</p>
                            </div>
                          )}
                          {review.level_signal && (
                            <div>
                              <span className="review-section-label">LEVEL SIGNAL</span>
                              <p>{review.level_signal}</p>
                            </div>
                          )}
                        </div>
                      )}

                      <div className="question-review-list">
                        <div className="question-review-heading">
                          <div>
                            <h3>Question-by-question review</h3>
                            <p>{review.questions.length} question{review.questions.length === 1 ? "" : "s"} analyzed</p>
                          </div>
                        </div>

                        {review.questions.map((question) => (
                          <details className="question-review-card" key={question.sequence_number} open={review.questions.length <= 2}>
                            <summary>
                              <div className="question-index">{question.sequence_number}</div>
                              <div className="question-summary-copy">
                                <strong>{question.question}</strong>
                                <span>
                                  {question.rating ? `${question.rating}/5` : "Not rated"}
                                  {question.level_signal ? ` · ${question.level_signal}` : ""}
                                </span>
                              </div>
                              <div className="question-chevron">⌄</div>
                            </summary>

                            <div className="question-review-body">
                              <div className="answer-summary">
                                <span className="review-section-label">ANSWER SUMMARY</span>
                                <p>{question.answer_summary}</p>
                              </div>

                              <div className="question-two-col">
                                <div>
                                  <span className="review-section-label">WHAT WORKED</span>
                                  <ul>{question.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
                                </div>
                                <div>
                                  <span className="review-section-label">GAPS</span>
                                  <ul>{question.gaps.map((item) => <li key={item}>{item}</li>)}</ul>
                                </div>
                              </div>

                              {question.stronger_answer && (
                                <div className="stronger-answer">
                                  <span className="review-section-label">STRONGER ANSWER</span>
                                  <p>{question.stronger_answer}</p>
                                </div>
                              )}
                            </div>
                          </details>
                        ))}
                      </div>

                      {reviewError && <div className="inline-error">{reviewError}</div>}

                      <button
                        className="secondary-button rerun-button"
                        type="button"
                        disabled={isAnalyzing}
                        onClick={() => void handleAnalyzeInterview()}
                      >
                        {isAnalyzing ? "Analyzing…" : "↻ Re-run analysis"}
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>

            <aside className="insight-panel">
              <div className="insight-section">
                <span className="insight-label">INTERVIEW</span>
                <strong>{activeInterview.company}</strong>
                <p>{activeInterview.role ?? "Interview role not specified"}</p>
              </div>

              <div className="insight-section">
                <span className="insight-label">INTERVIEWER</span>
                <strong>{activeInterview.recruiter_or_interviewer}</strong>
                <p>Round {activeInterview.sequence_number}</p>
              </div>

              <div className="insight-section insight-coming">
                <span className="insight-label">AI REVIEW</span>
                <strong>Coming next</strong>
                <p>
                  Questions, answer quality, strengths, gaps and expected level.
                </p>
              </div>
            </aside>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">II</div>
          <div>
            <div className="brand-name">Interview Intelligence</div>
            <div className="brand-subtitle">Private interview workspace</div>
          </div>
        </div>

        <nav className="nav">
          <button className="nav-item nav-item-active" type="button">
            <span className="nav-icon">◫</span>
            Interviews
          </button>
          <button className="nav-item" type="button">
            <span className="nav-icon">◌</span>
            Transcript Studio
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="privacy-pill">Local-first</div>
          <p>Your recordings stay on this machine unless you explicitly share them.</p>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">INTERVIEW WORKSPACE</p>
            <h1>Your interviews</h1>
            <p className="page-subtitle">
              Review conversations, transcripts and progress from one place.
            </p>
          </div>

          <button className="primary-button" type="button" onClick={() => setIsUploadOpen(true)}>
            <span>＋</span>
            Add interview
          </button>
        </header>

        {activeInterview && jobEvent && (
          <section className="processing-card">
            <div className="processing-copy">
              <div className="processing-kicker">
                {activeInterview.company} · Round {activeInterview.sequence_number}
              </div>

              <div className="processing-title-row">
                <div>
                  <h2>
                    {jobEvent.status === "completed"
                      ? "Interview ready"
                      : jobEvent.status === "failed"
                        ? "Processing failed"
                        : "Processing interview"}
                  </h2>
                  <p>{jobEvent.message ?? `${stageLabel(jobEvent.stage)} in progress`}</p>
                </div>

                <strong>{Math.round(jobEvent.progress_percent)}%</strong>
              </div>

              <div className="progress-track">
                <div
                  className="progress-value"
                  style={{ width: `${jobEvent.progress_percent}%` }}
                />
              </div>

              <div className="processing-footer">
                <div className="stage-row">
                  {PROCESSING_STAGES.map((stage) => {
                    const state = stageState(stage, jobEvent.stage, jobEvent.status);

                    return (
                      <span
                        key={stage}
                        className={`stage-chip ${
                          state === "active"
                            ? "stage-chip-active"
                            : state === "completed"
                              ? "stage-chip-completed"
                              : ""
                        }`}
                      >
                        {stageLabel(stage)}
                        {state === "completed" && <span className="stage-check">✓</span>}
                      </span>
                    );
                  })}
                </div>

                <div className="processing-timing">
                  <div className="processing-timer">
                    <span className="timer-icon">◷</span>
                    <span>
                      Elapsed <strong>{formatElapsed(elapsedSeconds)}</strong>
                    </span>
                  </div>

                  {processingStartedAt && (
                    <span className="processing-started">
                      Started at {formatClockTime(processingStartedAt)}
                    </span>
                  )}
                </div>
              </div>

              {jobEvent.status !== "completed" && jobEvent.status !== "failed" && (
                <div className="processing-alive">
                  <span className="alive-dot" />
                  Processing is active. The timer continues even while the stage percentage is unchanged.
                </div>
              )}

              {jobError && <div className="inline-error">{jobError}</div>}
            </div>
          </section>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Total interviews</span>
            <strong>{interviews.length}</strong>
            <span className="stat-help">Across every company and round</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Ready to review</span>
            <strong>{readyCount}</strong>
            <span className="stat-help">Processed transcripts available</span>
          </div>
          <div className="stat-card stat-card-accent">
            <span className="stat-label">Feedback loop</span>
            <strong>Coming next</strong>
            <span className="stat-help">AI review across interview rounds</span>
          </div>
        </section>

        <section className="content-card">
          <div className="section-header">
            <div>
              <h2>Recent interviews</h2>
              <p>Newest rounds appear first.</p>
            </div>
            <div className="search-shell">
              <span>⌕</span>
              <input aria-label="Search interviews" placeholder="Search company or interviewer" />
            </div>
          </div>

          {isLoading ? (
            <div className="empty-state">Loading interviews…</div>
          ) : error ? (
            <div className="empty-state error-state">
              <strong>Could not load your interviews.</strong>
              <span>{error}</span>
            </div>
          ) : interviews.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">◎</div>
              <strong>No interviews yet</strong>
              <span>Add your first recording to start building your feedback loop.</span>
            </div>
          ) : (
            <div className="interview-table">
              <div className="table-row table-head">
                <span>Interview</span>
                <span>Interviewer</span>
                <span>Date</span>
                <span>Duration</span>
                <span>Status</span>
                <span>Actions</span>
              </div>

              {interviews.map((interview) => (
                <div
                  className="table-row interview-row"
                  key={interview.id}
                  role={interview.artifact_root_path ? "button" : undefined}
                  tabIndex={interview.artifact_root_path ? 0 : -1}
                  onClick={() => {
                    if (interview.artifact_root_path) {
                      void openTranscript(interview);
                    }
                  }}
                  onKeyDown={(event) => {
                    if (
                      interview.artifact_root_path &&
                      (event.key === "Enter" || event.key === " ")
                    ) {
                      event.preventDefault();
                      void openTranscript(interview);
                    }
                  }}
                >
                  <span className="interview-primary">
                    <span className="company-avatar">
                      {interview.company.slice(0, 1).toUpperCase()}
                    </span>
                    <span>
                      <strong>{interview.company}</strong>
                      <small>
                        {interview.role ?? "Interview"} · Round {interview.sequence_number}
                      </small>
                    </span>
                  </span>
                  <span>{interview.recruiter_or_interviewer}</span>
                  <span>{formatDate(interview.interview_datetime)}</span>
                  <span className="duration-cell">
                    <svg
                      aria-hidden="true"
                      className="duration-icon"
                      viewBox="0 0 24 24"
                    >
                      <circle cx="12" cy="12" r="8.5" />
                      <path d="M12 7.5v5l3.25 2" />
                    </svg>
                    {formatDuration(interview.duration_seconds)}
                  </span>
                  <span>
                    {activeInterview?.id === interview.id &&
                    jobEvent &&
                    jobEvent.status !== "completed" ? (
                      <span className="status-stack">
                        <span className="status-pill status-processing">
                          Processing
                        </span>
                        <small>{Math.round(jobEvent.progress_percent)}% complete</small>
                      </span>
                    ) : (
                      <span
                        className={
                          interview.artifact_root_path
                            ? "status-pill status-ready"
                            : "status-pill status-pending"
                        }
                      >
                        {statusLabel(interview)}
                      </span>
                    )}
                  </span>
                  <span className="row-actions">
                    {interview.artifact_root_path && (
                      <button
                        className="row-icon-button"
                        type="button"
                        aria-label={`Open ${interview.company} interview`}
                        title="Open interview"
                        onClick={(event) => {
                          event.stopPropagation();
                          void openTranscript(interview);
                        }}
                      >
                        <svg aria-hidden="true" viewBox="0 0 24 24">
                          <path d="M2.8 12s3.3-5.5 9.2-5.5S21.2 12 21.2 12 17.9 17.5 12 17.5 2.8 12 2.8 12Z" />
                          <circle cx="12" cy="12" r="2.6" />
                        </svg>
                      </button>
                    )}

                    <button
                      className="row-icon-button menu-icon-button"
                      type="button"
                      aria-label="More actions"
                      title="More actions"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <svg aria-hidden="true" viewBox="0 0 24 24">
                        <circle cx="12" cy="5" r="1.4" />
                        <circle cx="12" cy="12" r="1.4" />
                        <circle cx="12" cy="19" r="1.4" />
                      </svg>
                    </button>

                    <button
                      className="delete-row-button"
                      type="button"
                      aria-label={`Delete ${interview.company} interview`}
                      title="Delete interview"
                      onClick={(event) => {
                        event.stopPropagation();
                        setDeleteError(null);
                        setDeleteTarget(interview);
                      }}
                    >
                      <svg aria-hidden="true" viewBox="0 0 24 24">
                        <path d="M4.5 7h15" />
                        <path d="M9 7V4.8h6V7" />
                        <path d="M7 7l.7 12h8.6L17 7" />
                        <path d="M10 10.5v5.5M14 10.5v5.5" />
                      </svg>
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      {deleteTarget && (
        <div className="modal-backdrop" role="presentation">
          <div className="delete-modal" role="dialog" aria-modal="true">
            <button
              className="delete-modal-close"
              type="button"
              aria-label="Close delete confirmation"
              disabled={isDeleting}
              onClick={() => {
                setDeleteTarget(null);
                setDeleteError(null);
              }}
            >
              ×
            </button>

            <div className="delete-modal-heading">
              <div className="delete-modal-icon">
                <svg aria-hidden="true" viewBox="0 0 24 24">
                  <path d="M4.5 7h15" />
                  <path d="M9 7V4.8h6V7" />
                  <path d="M7 7l.7 12h8.6L17 7" />
                  <path d="M10 10.5v5.5M14 10.5v5.5" />
                </svg>
              </div>

              <div>
                <h2>Delete interview?</h2>
                <p>This action cannot be undone.</p>
              </div>
            </div>

            <p className="delete-warning">
              This will permanently delete <strong>{deleteTarget.company}</strong>{" "}
              Round {deleteTarget.sequence_number}, including its transcripts,
              AI reviews, processing jobs, generated files, and any uploaded
              recording managed by Interview Intelligence.
            </p>
            <p className="delete-safe-note">
              Original recordings outside Interview Intelligence will not be deleted.
            </p>

            {deleteError && <div className="inline-error">{deleteError}</div>}

            <div className="modal-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={isDeleting}
                onClick={() => {
                  setDeleteTarget(null);
                  setDeleteError(null);
                }}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                type="button"
                disabled={isDeleting}
                onClick={() => void handleDeleteInterview()}
              >
                {isDeleting ? "Deleting…" : "Delete interview"}
              </button>
            </div>
          </div>
        </div>
      )}

      {isUploadOpen && (
        <div className="modal-backdrop" role="presentation">
          <div className="modal-card" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div>
                <p className="eyebrow">NEW INTERVIEW</p>
                <h2>Add interview recording</h2>
                <p>Upload the recording and we'll process it locally.</p>
              </div>
              <button className="icon-button" type="button" onClick={closeUpload}>×</button>
            </div>

            <form className="upload-form" onSubmit={handleUploadSubmit}>
              <label className="file-drop">
                <input
                  accept=".mp3,.wav,.m4a,.aac,audio/*"
                  type="file"
                  onChange={(event) =>
                    setUploadForm((current) => ({
                      ...current,
                      audio: event.target.files?.[0] ?? null,
                    }))
                  }
                />
                <div className="file-drop-icon">↑</div>
                <strong>{uploadForm.audio?.name ?? "Choose interview recording"}</strong>
                <span>MP3, WAV, M4A or AAC</span>
              </label>

              <div className="form-grid">
                <label>
                  <span>Company</span>
                  <input required value={uploadForm.company} onChange={(event) =>
                    setUploadForm((current) => ({ ...current, company: event.target.value }))
                  } placeholder="e.g. Navi" />
                </label>
                <label>
                  <span>Interviewer / recruiter</span>
                  <input required value={uploadForm.interviewer} onChange={(event) =>
                    setUploadForm((current) => ({ ...current, interviewer: event.target.value }))
                  } placeholder="e.g. Sachin" />
                </label>
                <label>
                  <span>Date & time</span>
                  <input required type="datetime-local" value={uploadForm.datetime} onChange={(event) =>
                    setUploadForm((current) => ({ ...current, datetime: event.target.value }))
                  } />
                </label>
                <label>
                  <span>Round</span>
                  <input min={1} required type="number" value={uploadForm.sequence} onChange={(event) =>
                    setUploadForm((current) => ({ ...current, sequence: Number(event.target.value) }))
                  } />
                </label>
                <label>
                  <span>Role</span>
                  <input value={uploadForm.role} onChange={(event) =>
                    setUploadForm((current) => ({ ...current, role: event.target.value }))
                  } placeholder="Engineering Manager" />
                </label>
                <label>
                  <span>Target level</span>
                  <input value={uploadForm.targetLevel} onChange={(event) =>
                    setUploadForm((current) => ({ ...current, targetLevel: event.target.value }))
                  } placeholder="Optional" />
                </label>
              </div>

              {submitError && <div className="inline-error">{submitError}</div>}

              <div className="modal-actions">
                <button className="secondary-button" type="button" onClick={closeUpload} disabled={isSubmitting}>Cancel</button>
                <button className="primary-button" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Starting…" : "Create & process"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  getAudioUrl,
  getTranscript,
  getTranscriptDownloadUrl,
  listInterviews,
  processInterview,
  subscribeToJob,
  uploadInterview,
} from "./api";
import type { Interview, JobEvent, TranscriptLine } from "./types";

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

const emptyUploadForm: UploadFormState = {
  company: "",
  interviewer: "",
  datetime: "",
  sequence: 1,
  role: "Engineering Manager",
  targetLevel: "",
  audio: null,
};

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

function timestampToSeconds(value: string): number {
  const parts = value.split(":").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return 0;
  return parts[0] * 3600 + parts[1] * 60 + parts[2];
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

  const [transcriptLines, setTranscriptLines] = useState<TranscriptLine[]>([]);
  const [isTranscriptLoading, setIsTranscriptLoading] = useState(false);
  const [transcriptError, setTranscriptError] = useState<string | null>(null);
  const [currentAudioTime, setCurrentAudioTime] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const refreshInterviews = async (): Promise<Interview[]> => {
    const data = await listInterviews();
    setInterviews(data);
    return data;
  };

  useEffect(() => {
    void refreshInterviews()
      .catch((caught: unknown) => {
        setError(caught instanceof Error ? caught.message : "Unable to load interviews.");
      })
      .finally(() => setIsLoading(false));
  }, []);

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

    try {
      const response = await getTranscript(interview.id);
      setTranscriptLines(parseTranscript(response.transcript));
    } catch (caught: unknown) {
      setTranscriptError(
        caught instanceof Error ? caught.message : "Unable to load transcript.",
      );
    } finally {
      setIsTranscriptLoading(false);
    }
  };

  const seekTo = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = seconds;
    void audio.play();
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

          <section className="transcript-layout">
            <div className="transcript-panel">
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
                      : "Processing interview"}
                  </h2>
                  <p>{jobEvent.message ?? `${stageLabel(jobEvent.stage)} in progress`}</p>
                </div>
                <strong>{Math.round(jobEvent.progress_percent)}%</strong>
              </div>
              <div className="progress-track">
                <div className="progress-value" style={{ width: `${jobEvent.progress_percent}%` }} />
              </div>
              <div className="stage-row">
                {["Preprocessing", "Transcription", "Diarization", "Alignment", "Export"].map(
                  (stage) => (
                    <span
                      key={stage}
                      className={
                        stage.toLowerCase() === jobEvent.stage
                          ? "stage-chip stage-chip-active"
                          : "stage-chip"
                      }
                    >
                      {stage}
                    </span>
                  ),
                )}
              </div>
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
                <span>Status</span>
                <span />
              </div>

              {interviews.map((interview) => (
                <button
                  className="table-row interview-row"
                  key={interview.id}
                  type="button"
                  onClick={() => void openTranscript(interview)}
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
                  <span>
                    <span
                      className={
                        interview.artifact_root_path
                          ? "status-pill status-ready"
                          : "status-pill status-pending"
                      }
                    >
                      {statusLabel(interview)}
                    </span>
                  </span>
                  <span className="row-arrow">→</span>
                </button>
              ))}
            </div>
          )}
        </section>
      </main>

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

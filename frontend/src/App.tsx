import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  analyzeInterview,
  cancelInterviewProcessing,
  deleteInterview,
  getAudioUrl,
  getInterviewReview,
  getLatestInterviewJob,
  getReviewConfig,
  getTranscript,
  getTranscriptDownloadUrl,
  listInterviews,
  processInterview,
  subscribeToJob,
  updateInterview,
  uploadInterview,
} from "./api";
import type { Interview, InterviewReview, JobEvent, ReviewConfig, TranscriptLine } from "./types";

type UploadFormState = {
  company: string;
  interviewer: string;
  datetime: string;
  sequence: number;
  role: string;
  targetLevel: string;
  roundType: string;
  audio: File | null;
};

type EditFormState = {
  company: string;
  interviewer: string;
  datetime: string;
  sequence: number;
  role: string;
  targetLevel: string;
  roundType: string;
};

type SortField = "company" | "round" | "date";
type SortDirection = "asc" | "desc";
type ReviewTier = "standard" | "deep";

type Screen = "workspace" | "transcript";
type TranscriptTab = "transcript" | "review";

const emptyUploadForm: UploadFormState = {
  company: "",
  interviewer: "",
  datetime: "",
  sequence: 1,
  role: "Engineering Manager",
  targetLevel: "",
  roundType: "Hiring Manager",
  audio: null,
};

const ROUND_TYPES = [
  "Recruiter Call",
  "Screening",
  "Hiring Manager Intro",
  "Hiring Manager",
  "Leadership",
  "People Management",
  "HLD",
  "LLD",
  "Coding",
  "Bar Raiser",
  "Director / CTO",
  "Other",
] as const;

function toDateTimeLocal(value: string): string {
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}

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

function formatTokenCount(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}

function formatUsd(value: number | null): string {
  if (value === null) return "Unavailable";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
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

function confidenceLabel(value: number): string {
  if (value >= 0.8) return "High confidence";
  if (value >= 0.6) return "Medium confidence";
  return "Low confidence";
}

function verdictSubtitle(signal: string): string {
  switch (signal) {
    case "strong_hire":
      return "Clearly above the expected interview bar";
    case "hire":
      return "Meets the expected interview bar";
    case "mixed":
      return "Mixed evidence against the expected bar";
    case "no_hire":
      return "Below the expected interview bar";
    case "strong_no_hire":
      return "Clearly below the expected interview bar";
    default:
      return "Not enough evidence for a reliable hiring decision";
  }
}

function improvementTitle(item: string, index: number): string {
  const lower = item.toLowerCase();
  if (lower.includes("structure") || lower.includes("framework")) {
    return "Structure your approach";
  }
  if (
    lower.includes("scale") ||
    lower.includes("qps") ||
    lower.includes("latency") ||
    lower.includes("throughput")
  ) {
    return "Quantify early";
  }
  if (
    lower.includes("data") ||
    lower.includes("database") ||
    lower.includes("storage") ||
    lower.includes("sql")
  ) {
    return "Explain data decisions";
  }
  if (lower.includes("trade-off") || lower.includes("tradeoff")) {
    return "Make trade-offs explicit";
  }
  if (lower.includes("leadership") || lower.includes("team")) {
    return "Show leadership scope";
  }
  if (lower.includes("communicat") || lower.includes("concise")) {
    return "Communicate more crisply";
  }
  return `Improvement ${String(index + 1).padStart(2, "0")}`;
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
  const [isSidebarPinnedOpen, setIsSidebarPinnedOpen] = useState(true);
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
  const [isCancelConfirmOpen, setIsCancelConfirmOpen] = useState(false);
  const [isCancellingProcessing, setIsCancellingProcessing] = useState(false);
  const [isRetryingProcessing, setIsRetryingProcessing] = useState(false);

  const [transcriptLines, setTranscriptLines] = useState<TranscriptLine[]>([]);
  const [isTranscriptLoading, setIsTranscriptLoading] = useState(false);
  const [transcriptError, setTranscriptError] = useState<string | null>(null);
  const [currentAudioTime, setCurrentAudioTime] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [transcriptTab, setTranscriptTab] = useState<TranscriptTab>("transcript");
  const [review, setReview] = useState<InterviewReview | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewConfig, setReviewConfig] = useState<ReviewConfig | null>(null);
  const [analysisStartedAt, setAnalysisStartedAt] = useState<Date | null>(null);
  const [analysisElapsedSeconds, setAnalysisElapsedSeconds] = useState(0);
  const [reviewTier, setReviewTier] = useState<ReviewTier>("standard");
  const [showAllStrengths, setShowAllStrengths] = useState(false);
  const [showAllGaps, setShowAllGaps] = useState(false);
  const [showAllImprovements, setShowAllImprovements] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<Interview | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [roundFilter, setRoundFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [groupByCompany, setGroupByCompany] = useState(
    () => window.localStorage.getItem("ii-group-by-company") === "true",
  );

  const [editTarget, setEditTarget] = useState<Interview | null>(null);
  const [editForm, setEditForm] = useState<EditFormState | null>(null);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const isSidebarExpanded = isSidebarPinnedOpen;

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

        let recoveryCandidate:
          | { interview: Interview; job: JobEvent }
          | null = null;

        for (const interview of loaded) {
          const latestJob = await getLatestInterviewJob(interview.id);
          if (!latestJob) continue;

          if (
            latestJob.status === "queued" ||
            latestJob.status === "running"
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
                if (
                  nextEvent.status === "completed" ||
                  nextEvent.status === "failed" ||
                  nextEvent.status === "cancelled"
                ) {
                  void refreshInterviews();
                }
              },
              (socketError) => setJobError(socketError.message),
            );
            recoveryCandidate = null;
            break;
          }

          if (
            !interview.artifact_root_path &&
            (latestJob.status === "failed" ||
              latestJob.status === "cancelled") &&
            recoveryCandidate === null
          ) {
            recoveryCandidate = {
              interview,
              job: latestJob,
            };
          }
        }

        if (recoveryCandidate) {
          setActiveInterview(recoveryCandidate.interview);
          setJobEvent(recoveryCandidate.job);
          setProcessingStartedAt(null);
          setElapsedSeconds(0);
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
    if (!processingStartedAt || !jobEvent || jobEvent.status === "completed" ||
        jobEvent.status === "failed" ||
        jobEvent.status === "cancelled") {
      return;
    }

    const updateElapsed = () => {
      setElapsedSeconds((Date.now() - processingStartedAt.getTime()) / 1000);
    };

    updateElapsed();
    const timer = window.setInterval(updateElapsed, 1000);

    return () => window.clearInterval(timer);
  }, [processingStartedAt, jobEvent?.status]);

  useEffect(() => {
    let cancelled = false;

    void getReviewConfig()
      .then((config) => {
        if (!cancelled) setReviewConfig(config);
      })
      .catch(() => {
        // Review can still work with a custom provider even if config discovery fails.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isAnalyzing || !analysisStartedAt) return;

    const update = () => {
      setAnalysisElapsedSeconds(
        Math.max(0, (Date.now() - analysisStartedAt.getTime()) / 1000),
      );
    };

    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, [analysisStartedAt, isAnalyzing]);

  const readyCount = useMemo(
    () => interviews.filter((item) => item.artifact_root_path).length,
    [interviews],
  );

  useEffect(() => {
    window.localStorage.setItem(
      "ii-group-by-company",
      String(groupByCompany),
    );
  }, [groupByCompany]);

  const visibleInterviews = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    const filtered = interviews.filter((interview) => {
      const matchesSearch =
        query.length === 0 ||
        [
          interview.company,
          interview.recruiter_or_interviewer,
          interview.round_type ?? "",
          interview.role ?? "",
          interview.target_level ?? "",
        ].some((value) => value.toLowerCase().includes(query));

      const matchesRound =
        roundFilter === "all" ||
        (interview.round_type ?? "Other") === roundFilter;

      const isActive =
        activeInterview?.id === interview.id &&
        jobEvent &&
        (jobEvent.status === "queued" || jobEvent.status === "running");
      const isFailed =
        activeInterview?.id === interview.id && jobEvent?.status === "failed";
      const isCancelled =
        activeInterview?.id === interview.id && jobEvent?.status === "cancelled";

      const status =
        isActive
          ? "processing"
          : isFailed
            ? "interrupted"
            : isCancelled
              ? "stopped"
              : interview.artifact_root_path
                ? "ready"
                : "not_processed";

      const matchesStatus =
        statusFilter === "all" || statusFilter === status;

      return matchesSearch && matchesRound && matchesStatus;
    });

    return [...filtered].sort((left, right) => {
      let comparison = 0;

      if (sortField === "company") {
        comparison = left.company.localeCompare(right.company);
      } else if (sortField === "round") {
        comparison = (left.round_type ?? "Other").localeCompare(
          right.round_type ?? "Other",
        );
      } else {
        comparison =
          new Date(left.interview_datetime).getTime() -
          new Date(right.interview_datetime).getTime();
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [
    activeInterview?.id,
    interviews,
    jobEvent,
    roundFilter,
    searchQuery,
    statusFilter,
    sortDirection,
    sortField,
  ]);

  const groupedInterviews = useMemo(() => {
    const grouped = new Map<string, Interview[]>();

    for (const interview of visibleInterviews) {
      const existing = grouped.get(interview.company) ?? [];
      existing.push(interview);
      grouped.set(interview.company, existing);
    }

    return [...grouped.entries()].sort(([left], [right]) =>
      left.localeCompare(right),
    );
  }, [visibleInterviews]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortField(field);
    setSortDirection(field === "date" ? "desc" : "asc");
  };

  const sortIndicator = (field: SortField): string => {
    if (sortField !== field) return "↕";
    return sortDirection === "asc" ? "↑" : "↓";
  };

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
    setAnalysisStartedAt(null);
    setAnalysisElapsedSeconds(0);
    setReviewTier("standard");
    setShowAllStrengths(false);
    setShowAllGaps(false);
    setShowAllImprovements(false);

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

    const startedAt = new Date();
    setAnalysisStartedAt(startedAt);
    setAnalysisElapsedSeconds(0);
    setIsAnalyzing(true);
    setReviewError(null);

    try {
      const selectedModel =
        reviewTier === "deep" ? "gpt-5.6-sol" : "gpt-5.6-luna";
      const result = await analyzeInterview(activeInterview.id, selectedModel);
      setReview(result);
      setTranscriptTab("review");
      setAnalysisElapsedSeconds(
        result.analysis?.elapsed_seconds ??
          Math.max(0, (Date.now() - startedAt.getTime()) / 1000),
      );
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

  const handleCancelProcessing = async () => {
    if (!activeInterview || !jobEvent) return;

    setIsCancellingProcessing(true);
    setJobError(null);

    try {
      const nextJob = await cancelInterviewProcessing(activeInterview.id);
      setJobEvent(nextJob);
      setIsCancelConfirmOpen(false);
    } catch (caught: unknown) {
      setJobError(
        caught instanceof Error
          ? caught.message
          : "Unable to stop processing.",
      );
    } finally {
      setIsCancellingProcessing(false);
    }
  };

  const handleRetryProcessing = async () => {
    if (!activeInterview) return;

    setIsRetryingProcessing(true);
    setJobError(null);

    try {
      const processResult = await processInterview(activeInterview.id);
      const startedAt = new Date();

      setProcessingStartedAt(startedAt);
      setElapsedSeconds(0);
      setJobEvent({
        job_id: processResult.job_id,
        interview_id: processResult.interview_id,
        status: processResult.status as JobEvent["status"],
        stage: "inspection",
        progress_percent: 0,
        processed_audio_seconds: 0,
        total_audio_seconds: activeInterview.duration_seconds ?? 0,
        message: "Restarting processing",
      });

      subscribeToJob(
        processResult.job_id,
        (nextEvent) => {
          setJobEvent(nextEvent);
          if (
            nextEvent.status === "completed" ||
            nextEvent.status === "failed" ||
            nextEvent.status === "cancelled"
          ) {
            void refreshInterviews();
          }
        },
        (socketError) => setJobError(socketError.message),
      );
    } catch (caught: unknown) {
      setJobError(
        caught instanceof Error
          ? caught.message
          : "Unable to restart processing.",
      );
    } finally {
      setIsRetryingProcessing(false);
    }
  };

  const openEditInterview = (interview: Interview) => {
    setEditTarget(interview);
    setEditError(null);
    setEditForm({
      company: interview.company,
      interviewer: interview.recruiter_or_interviewer,
      datetime: toDateTimeLocal(interview.interview_datetime),
      sequence: interview.sequence_number,
      role: interview.role ?? "",
      targetLevel: interview.target_level ?? "",
      roundType: interview.round_type ?? "Other",
    });
  };

  const closeEditInterview = () => {
    if (isSavingEdit) return;
    setEditTarget(null);
    setEditForm(null);
    setEditError(null);
  };

  const handleEditInterview = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();
    if (!editTarget || !editForm) return;

    setIsSavingEdit(true);
    setEditError(null);

    try {
      const updated = await updateInterview(editTarget.id, {
        company: editForm.company,
        recruiterOrInterviewer: editForm.interviewer,
        interviewDatetime: editForm.datetime,
        sequenceNumber: editForm.sequence,
        role: editForm.role,
        targetLevel: editForm.targetLevel,
        roundType: editForm.roundType,
      });

      setInterviews((current) =>
        current.map((interview) =>
          interview.id === updated.id ? updated : interview,
        ),
      );

      if (activeInterview?.id === updated.id) {
        setActiveInterview(updated);
      }

      setEditTarget(null);
      setEditForm(null);
    } catch (caught: unknown) {
      setEditError(
        caught instanceof Error
          ? caught.message
          : "Unable to update interview.",
      );
    } finally {
      setIsSavingEdit(false);
    }
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
        roundType: uploadForm.roundType,
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
      <div className={`app-shell ${isSidebarPinnedOpen ? "shell-sidebar-expanded" : "shell-sidebar-collapsed"}`}>
        <aside
        className={`sidebar ${isSidebarPinnedOpen ? "sidebar-expanded" : "sidebar-collapsed"}`}
      >
        <div className="brand">
          <div className="brand-mark">II</div>
          <div className="brand-copy">
            <div className="brand-name">Interview Intelligence</div>
            <div className="brand-subtitle">Private interview workspace</div>
          </div>
        </div>

        <nav className="nav">
          <button className="nav-item nav-item-active" type="button">
            <span className="nav-icon">◫</span>
            <span className="nav-label">Interviews</span>
          </button>
          <button className="nav-item" type="button" onClick={() => activeInterview && setScreen("transcript")}>
            <span className="nav-icon">◌</span>
            <span className="nav-label">Transcript Studio</span>
          </button>
        </nav>

        <button
          className="sidebar-toggle"
          type="button"
          aria-label={isSidebarPinnedOpen ? "Collapse sidebar" : "Expand sidebar"}
          title={isSidebarPinnedOpen ? "Collapse sidebar" : "Expand sidebar"}
          onClick={() => {
            setIsSidebarPinnedOpen((current) => !current);
          }}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path
              d={isSidebarPinnedOpen ? "M14.5 6 8.5 12l6 6" : "m9.5 6 6 6-6 6"}
            />
          </svg>
        </button>

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

          <section className={`transcript-layout ${transcriptTab === "review" ? "review-layout-wide" : ""}`}>
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
                    isAnalyzing ? (
                      <div className="review-analysis-progress">
                        <div className="analysis-spinner" aria-hidden="true" />
                        <p className="eyebrow">AI INTERVIEW REVIEW</p>
                        <h2>Analyzing your interview</h2>
                        <p className="analysis-progress-copy">
                          The transcript has been sent for structured review. Keep this
                          page open while the model evaluates questions, evidence,
                          strengths, gaps and level signal.
                        </p>

                        <div className="analysis-live-grid">
                          <div>
                            <span>Elapsed</span>
                            <strong>{formatElapsed(analysisElapsedSeconds)}</strong>
                          </div>
                          <div>
                            <span>Provider</span>
                            <strong>{reviewConfig?.provider ?? "OpenAI"}</strong>
                          </div>
                          <div>
                            <span>Model</span>
                            <strong>
                              {reviewTier === "deep"
                                ? "gpt-5.6-sol"
                                : "gpt-5.6-luna"}
                            </strong>
                          </div>
                          <div>
                            <span>Usage</span>
                            <strong>Available on completion</strong>
                          </div>
                        </div>

                        {reviewConfig?.input_per_million_usd !== null &&
                          reviewConfig?.input_per_million_usd !== undefined && (
                            <div className="analysis-rate-note">
                              <strong>Current standard rates</strong>
                              <span>
                                Input ${reviewConfig.input_per_million_usd}/1M · Output $
                                {reviewConfig.output_per_million_usd}/1M tokens
                              </span>
                            </div>
                          )}

                        <p className="analysis-usage-note">
                          Exact token counts are reported by the provider only when the
                          response completes. The final review will show actual usage and
                          an estimated API cost.
                        </p>
                      </div>
                    ) : (
                      <div className="review-empty">
                        <div className="review-empty-icon">✦</div>
                        <p className="eyebrow">AI INTERVIEW REVIEW</p>
                        <h2>Turn this transcript into feedback</h2>
                        <p>
                          Analyze questions, answer quality, strengths, gaps, level signal,
                          and the overall hiring signal.
                        </p>
                        <div
                          className="review-tier-picker"
                          role="radiogroup"
                          aria-label="AI review depth"
                        >
                          <button
                            className={`review-tier-option ${
                              reviewTier === "standard"
                                ? "review-tier-option-selected"
                                : ""
                            }`}
                            type="button"
                            role="radio"
                            aria-checked={reviewTier === "standard"}
                            onClick={() => setReviewTier("standard")}
                          >
                            <div className="review-tier-option-top">
                              <div>
                                <strong>Standard</strong>
                                <span className="review-tier-badge">Recommended</span>
                              </div>
                              <span className="review-tier-radio" />
                            </div>
                            <p>Fast, comprehensive interview feedback.</p>
                            <small>GPT-5.6 Luna · typically ~1 minute · lower cost</small>
                          </button>

                          <button
                            className={`review-tier-option ${
                              reviewTier === "deep"
                                ? "review-tier-option-selected"
                                : ""
                            }`}
                            type="button"
                            role="radio"
                            aria-checked={reviewTier === "deep"}
                            onClick={() => setReviewTier("deep")}
                          >
                            <div className="review-tier-option-top">
                              <div>
                                <strong>Deep</strong>
                              </div>
                              <span className="review-tier-radio" />
                            </div>
                            <p>Maximum detail and question-level granularity.</p>
                            <small>GPT-5.6 Sol · typically 1–3 minutes · higher cost</small>
                          </button>
                        </div>

                        <div className="review-tier-summary">
                          <span>Selected</span>
                          <strong>
                            {reviewTier === "deep"
                              ? "Deep · GPT-5.6 Sol"
                              : "Standard · GPT-5.6 Luna"}
                          </strong>
                        </div>

                        {reviewError && <div className="inline-error">{reviewError}</div>}
                        <button
                          className="primary-button analyze-button"
                          type="button"
                          onClick={() => void handleAnalyzeInterview()}
                        >
                          ✦ Analyze interview
                        </button>
                      </div>
                    )
                  ) : (
                    <>
                      {(() => {
                        const ratedQuestions = review.questions.filter(
                          (question) => question.rating !== null,
                        );
                        const averageRating =
                          ratedQuestions.length > 0
                            ? ratedQuestions.reduce(
                                (sum, question) => sum + (question.rating ?? 0),
                                0,
                              ) / ratedQuestions.length
                            : null;
                        const strongAnswers = ratedQuestions.filter(
                          (question) => (question.rating ?? 0) >= 4,
                        ).length;
                        const belowBarAnswers = ratedQuestions.filter(
                          (question) => (question.rating ?? 0) <= 2,
                        ).length;
                        const visibleStrengths = showAllStrengths
                          ? review.strengths
                          : review.strengths.slice(0, 3);
                        const visibleGaps = showAllGaps
                          ? review.concerns
                          : review.concerns.slice(0, 3);
                        const visibleImprovements = showAllImprovements
                          ? review.improvement_areas
                          : review.improvement_areas.slice(0, 4);

                        return (
                          <>
                            {isAnalyzing && (
                              <section className="review-rerun-banner">
                                <div className="analysis-spinner analysis-spinner-small" />
                                <div>
                                  <strong>Refreshing AI review</strong>
                                  <span>
                                    {formatElapsed(analysisElapsedSeconds)} elapsed ·{" "}
                                    {reviewConfig?.model ?? review.model}
                                  </span>
                                </div>
                              </section>
                            )}

                            <section className={`review-verdict signal-border-${review.hiring_signal}`}>
                              <div className="verdict-copy">
                                <p className="eyebrow">AI INTERVIEW REVIEW</p>
                                <div className="verdict-title-row">
                                  <span className={`verdict-icon signal-${review.hiring_signal}`}>
                                    {review.hiring_signal.includes("hire") &&
                                    !review.hiring_signal.includes("no_hire")
                                      ? "✓"
                                      : review.hiring_signal === "insufficient_evidence"
                                        ? "?"
                                        : "×"}
                                  </span>
                                  <h2>{hiringSignalLabel(review.hiring_signal)}</h2>
                                </div>
                                <h3>{verdictSubtitle(review.hiring_signal)}</h3>
                                <p className="verdict-summary">{review.overall_summary}</p>
                              </div>

                              <div className="review-profile">
                                <div className="confidence-chip">
                                  <span>{confidenceLabel(review.confidence)}</span>
                                  <strong>{Math.round(review.confidence * 100)}%</strong>
                                </div>

                                <div className="profile-divider" />

                                <div className="profile-row">
                                  <span>Question average</span>
                                  <strong>
                                    {averageRating === null
                                      ? "Not rated"
                                      : `${averageRating.toFixed(1)} / 5`}
                                  </strong>
                                </div>
                                <div className="profile-row">
                                  <span>Strong answers</span>
                                  <strong>{strongAnswers}</strong>
                                </div>
                                <div className="profile-row">
                                  <span>Below-bar answers</span>
                                  <strong>{belowBarAnswers}</strong>
                                </div>
                                <div className="profile-row">
                                  <span>Questions analyzed</span>
                                  <strong>{review.questions.length}</strong>
                                </div>
                              </div>
                            </section>

                            {(review.usage || review.analysis) && (
                              <section className="review-usage-card">
                                <div className="review-usage-heading">
                                  <div>
                                    <p className="eyebrow">ANALYSIS USAGE</p>
                                    <h3>Time, tokens and estimated API cost</h3>
                                  </div>
                                  <div className="usage-cost">
                                    <span>Estimated cost</span>
                                    <strong>
                                      {formatUsd(
                                        review.usage?.estimated_cost_usd ?? null,
                                      )}
                                    </strong>
                                  </div>
                                </div>

                                <div className="review-usage-grid">
                                  <div>
                                    <span>Elapsed</span>
                                    <strong>
                                      {review.analysis
                                        ? formatElapsed(
                                            review.analysis.elapsed_seconds,
                                          )
                                        : "—"}
                                    </strong>
                                  </div>
                                  <div>
                                    <span>Input tokens</span>
                                    <strong>
                                      {formatTokenCount(
                                        review.usage?.input_tokens ?? 0,
                                      )}
                                    </strong>
                                  </div>
                                  <div>
                                    <span>Cached input</span>
                                    <strong>
                                      {formatTokenCount(
                                        review.usage?.cached_input_tokens ?? 0,
                                      )}
                                    </strong>
                                  </div>
                                  <div>
                                    <span>Output tokens</span>
                                    <strong>
                                      {formatTokenCount(
                                        review.usage?.output_tokens ?? 0,
                                      )}
                                    </strong>
                                  </div>
                                  <div>
                                    <span>Reasoning tokens</span>
                                    <strong>
                                      {formatTokenCount(
                                        review.usage?.reasoning_tokens ?? 0,
                                      )}
                                    </strong>
                                  </div>
                                  <div>
                                    <span>Total tokens</span>
                                    <strong>
                                      {formatTokenCount(
                                        review.usage?.total_tokens ?? 0,
                                      )}
                                    </strong>
                                  </div>
                                </div>

                                <div className="usage-footnote">
                                  <span>{review.provider} · {review.model}</span>
                                  <span>
                                    {review.usage?.pricing_basis ??
                                      "Token usage is provider-reported; cost unavailable for this model."}
                                  </span>
                                </div>
                              </section>
                            )}

                            <section className="review-takeaways-grid">
                              <article className="takeaway-card takeaway-positive">
                                <div className="takeaway-heading">
                                  <span className="takeaway-icon">✓</span>
                                  <h3>What went well</h3>
                                </div>
                                <ul>
                                  {visibleStrengths.map((item) => (
                                    <li key={item}>{item}</li>
                                  ))}
                                </ul>
                                {review.strengths.length > 3 && (
                                  <button
                                    className="text-action text-action-positive"
                                    type="button"
                                    onClick={() => setShowAllStrengths((current) => !current)}
                                  >
                                    {showAllStrengths
                                      ? "Show less"
                                      : `View all ${review.strengths.length} strengths`}{" "}
                                    →
                                  </button>
                                )}
                              </article>

                              <article className="takeaway-card takeaway-warning">
                                <div className="takeaway-heading">
                                  <span className="takeaway-icon">!</span>
                                  <h3>Biggest gaps</h3>
                                </div>
                                <ul>
                                  {visibleGaps.map((item) => (
                                    <li key={item}>{item}</li>
                                  ))}
                                </ul>
                                {review.concerns.length > 3 && (
                                  <button
                                    className="text-action text-action-warning"
                                    type="button"
                                    onClick={() => setShowAllGaps((current) => !current)}
                                  >
                                    {showAllGaps
                                      ? "Show less"
                                      : `View all ${review.concerns.length} gaps`}{" "}
                                    →
                                  </button>
                                )}
                              </article>

                              <article className="signal-highlight-card">
                                <div>
                                  <span className="signal-mini-label">TOP STRENGTH</span>
                                  <strong>
                                    {review.strengths[0] ?? "Insufficient evidence"}
                                  </strong>
                                </div>
                                <div className="signal-highlight-divider" />
                                <div>
                                  <span className="signal-mini-label">TOP GAP</span>
                                  <strong>
                                    {review.concerns[0] ?? "Insufficient evidence"}
                                  </strong>
                                </div>
                              </article>
                            </section>

                            <section className="improvement-section">
                              <div className="section-heading-row">
                                <div>
                                  <p className="eyebrow">COACHING</p>
                                  <h3>How to improve next time</h3>
                                </div>
                                {review.improvement_areas.length > 4 && (
                                  <button
                                    className="text-action"
                                    type="button"
                                    onClick={() =>
                                      setShowAllImprovements((current) => !current)
                                    }
                                  >
                                    {showAllImprovements
                                      ? "Show less"
                                      : "View all improvement areas"}{" "}
                                    →
                                  </button>
                                )}
                              </div>

                              <div className="improvement-grid">
                                {visibleImprovements.map((item, index) => (
                                  <article className="improvement-item" key={item}>
                                    <span className="improvement-number">
                                      {String(index + 1).padStart(2, "0")}
                                    </span>
                                    <div>
                                      <strong>{improvementTitle(item, index)}</strong>
                                      <p>{item}</p>
                                    </div>
                                  </article>
                                ))}
                              </div>
                            </section>

                            <section className="question-review-list redesigned-question-list">
                              <div className="question-review-heading section-heading-row">
                                <div>
                                  <p className="eyebrow">EVIDENCE</p>
                                  <h3>Question-by-question review</h3>
                                  <p>
                                    {review.questions.length} question
                                    {review.questions.length === 1 ? "" : "s"} analyzed
                                  </p>
                                </div>
                              </div>

                              <div className="question-table-header">
                                <span>Question</span>
                                <span>Your rating</span>
                                <span>Highlights</span>
                                <span />
                              </div>

                              {review.questions.map((question) => (
                                <details
                                  className="question-review-card redesigned-question-card"
                                  key={question.sequence_number}
                                >
                                  <summary>
                                    <div className="question-index">
                                      {question.sequence_number}
                                    </div>
                                    <div className="question-summary-copy">
                                      <strong>{question.question}</strong>
                                    </div>
                                    <span
                                      className={`question-rating rating-${
                                        question.rating === null
                                          ? "none"
                                          : question.rating >= 4
                                            ? "good"
                                            : question.rating <= 2
                                              ? "low"
                                              : "mixed"
                                      }`}
                                    >
                                      {question.rating ? `${question.rating}/5` : "—"}
                                    </span>
                                    <span className="question-highlight">
                                      {question.level_signal ?? "No level signal available."}
                                    </span>
                                    <div className="question-chevron">⌄</div>
                                  </summary>

                                  <div className="question-review-body">
                                    <div className="answer-summary">
                                      <span className="review-section-label">
                                        ANSWER SUMMARY
                                      </span>
                                      <p>{question.answer_summary}</p>
                                    </div>

                                    <div className="question-two-col">
                                      <div>
                                        <span className="review-section-label">
                                          WHAT WORKED
                                        </span>
                                        <ul>
                                          {question.strengths.map((item) => (
                                            <li key={item}>{item}</li>
                                          ))}
                                        </ul>
                                      </div>
                                      <div>
                                        <span className="review-section-label">GAPS</span>
                                        <ul>
                                          {question.gaps.map((item) => (
                                            <li key={item}>{item}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    </div>

                                    {question.stronger_answer && (
                                      <div className="stronger-answer">
                                        <span className="review-section-label">
                                          STRONGER ANSWER
                                        </span>
                                        <p>{question.stronger_answer}</p>
                                      </div>
                                    )}
                                  </div>
                                </details>
                              ))}
                            </section>

                            {(review.role_signal || review.level_signal) && (
                              <section className="level-assessment-card">
                                <div className="level-assessment-icon">▥</div>
                                <div className="level-assessment-copy">
                                  <p className="eyebrow">LEVEL ASSESSMENT</p>
                                  <h3>
                                    {activeInterview.role ?? "Interview level"}{" "}
                                    <span>— {hiringSignalLabel(review.hiring_signal)}</span>
                                  </h3>
                                  <p>
                                    {review.level_signal ??
                                      review.role_signal ??
                                      "Not enough evidence to infer level."}
                                  </p>
                                </div>
                                <div className="level-signal-boxes">
                                  <div>
                                    <span>Role signal</span>
                                    <strong>
                                      {review.role_signal
                                        ? "Evidence available"
                                        : "Insufficient evidence"}
                                    </strong>
                                  </div>
                                  <div>
                                    <span>Level signal</span>
                                    <strong>
                                      {review.level_signal
                                        ? "Assessment available"
                                        : "Insufficient evidence"}
                                    </strong>
                                  </div>
                                </div>
                              </section>
                            )}
                          </>
                        );
                      })()}

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

            {transcriptTab === "transcript" && (
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
            )}
          </section>
        </main>
      </div>
    );
  }

  const renderInterviewRow = (
    interview: Interview,
    grouped: boolean,
  ) => (
    <div
      className={`table-row interview-row ${grouped ? "grouped-interview-row" : ""}`}
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
        {!grouped && (
          <span className="company-avatar">
            {interview.company.slice(0, 1).toUpperCase()}
          </span>
        )}
        <span>
          {!grouped && <strong>{interview.company}</strong>}
          <small className={grouped ? "grouped-primary-label" : undefined}>
            {interview.role ?? "Interview"} · Round {interview.sequence_number}
          </small>
        </span>
      </span>

      <span>
        <span className="round-pill">
          {interview.round_type ?? "Other"}
        </span>
      </span>

      <span className="interviewer-cell">
        {interview.recruiter_or_interviewer}
        <button
          className="inline-edit-button"
          type="button"
          aria-label={`Edit ${interview.company} interview`}
          title="Edit interview details"
          onClick={(event) => {
            event.stopPropagation();
            openEditInterview(interview);
          }}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="m4 16.5-.5 4 4-.5L18.8 8.7l-3.5-3.5L4 16.5Z" />
            <path d="m13.8 6.7 3.5 3.5" />
          </svg>
        </button>
      </span>

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

      <span className="transcription-time-cell">
        {interview.transcription_seconds != null
          ? formatDuration(interview.transcription_seconds)
          : interview.artifact_root_path
            ? "Not recorded"
            : "—"}
      </span>

      <span>
        {activeInterview?.id === interview.id &&
        jobEvent &&
        (jobEvent.status === "queued" || jobEvent.status === "running") ? (
          <span className="status-stack">
            <span className="status-pill status-processing">
              Processing
            </span>
            <small>{Math.round(jobEvent.progress_percent)}% complete</small>
          </span>
        ) : activeInterview?.id === interview.id &&
          jobEvent?.status === "failed" ? (
          <span className="status-pill status-failed">
            Interrupted
          </span>
        ) : activeInterview?.id === interview.id &&
          jobEvent?.status === "cancelled" ? (
          <span className="status-pill status-cancelled">
            Stopped
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
          className="row-icon-button"
          type="button"
          aria-label={`Edit ${interview.company} interview details`}
          title="Edit interview"
          onClick={(event) => {
            event.stopPropagation();
            openEditInterview(interview);
          }}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="m4 16.5-.5 4 4-.5L18.8 8.7l-3.5-3.5L4 16.5Z" />
            <path d="m13.8 6.7 3.5 3.5" />
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
  );

  return (
    <div className={`app-shell ${isSidebarPinnedOpen ? "shell-sidebar-expanded" : "shell-sidebar-collapsed"}`}>
      <aside
        className={`sidebar ${isSidebarPinnedOpen ? "sidebar-expanded" : "sidebar-collapsed"}`}
      >
        <div className="brand">
          <div className="brand-mark">II</div>
          <div className="brand-copy">
            <div className="brand-name">Interview Intelligence</div>
            <div className="brand-subtitle">Private interview workspace</div>
          </div>
        </div>

        <nav className="nav">
          <button className="nav-item" type="button" onClick={() => setScreen("workspace")}>
            <span className="nav-icon">◫</span>
            <span className="nav-label">Interviews</span>
          </button>
          <button className="nav-item nav-item-active" type="button">
            <span className="nav-icon">◌</span>
            <span className="nav-label">Transcript Studio</span>
          </button>
        </nav>

        <button
          className="sidebar-toggle"
          type="button"
          aria-label={isSidebarPinnedOpen ? "Collapse sidebar" : "Expand sidebar"}
          title={isSidebarPinnedOpen ? "Collapse sidebar" : "Expand sidebar"}
          onClick={() => {
            setIsSidebarPinnedOpen((current) => !current);
          }}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path
              d={isSidebarPinnedOpen ? "M14.5 6 8.5 12l6 6" : "m9.5 6 6 6-6 6"}
            />
          </svg>
        </button>

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
                        ? "Processing interrupted"
                        : jobEvent.status === "cancelled"
                          ? "Processing stopped"
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

              {(jobEvent.status === "queued" || jobEvent.status === "running") && (
                <div className="processing-action-row">
                  <div className="processing-alive">
                    <span className="alive-dot" />
                    Processing is active. The timer continues even while the
                    stage percentage is unchanged.
                  </div>

                  <button
                    className="stop-processing-button"
                    type="button"
                    onClick={() => setIsCancelConfirmOpen(true)}
                  >
                    Stop processing
                  </button>
                </div>
              )}

              {(jobEvent.status === "failed" || jobEvent.status === "cancelled") && (
                <div className="processing-recovery">
                  <div>
                    <strong>
                      {jobEvent.status === "failed"
                        ? "The worker is no longer running."
                        : "The uploaded recording has been preserved."}
                    </strong>
                    <p>
                      {jobEvent.error_message ??
                        jobEvent.message ??
                        "You can restart processing from this interview."}
                    </p>
                  </div>

                  <button
                    className="primary-button retry-processing-button"
                    type="button"
                    disabled={isRetryingProcessing}
                    onClick={() => void handleRetryProcessing()}
                  >
                    {isRetryingProcessing ? "Restarting…" : "Process again"}
                  </button>
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

        <section className="content-card interview-library-card">
          <div className="section-header library-header">
            <div>
              <h2>Interviews</h2>
              <p>Search, filter and organize your interview history.</p>
            </div>

            <div className="library-toolbar">
              <div className="search-shell">
                <span>⌕</span>
                <input
                  aria-label="Search interviews"
                  placeholder="Search interviews…"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </div>

              <select
                aria-label="Filter by interview round"
                className="library-select"
                value={roundFilter}
                onChange={(event) => setRoundFilter(event.target.value)}
              >
                <option value="all">All rounds</option>
                {ROUND_TYPES.map((roundType) => (
                  <option key={roundType} value={roundType}>
                    {roundType}
                  </option>
                ))}
              </select>

              <select
                aria-label="Filter by interview status"
                className="library-select"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
              >
                <option value="all">All statuses</option>
                <option value="ready">Ready</option>
                <option value="processing">Processing</option>
                <option value="stopped">Stopped</option>
                <option value="interrupted">Interrupted</option>
                <option value="not_processed">Not processed</option>
              </select>

              <label className="group-toggle">
                <input
                  type="checkbox"
                  checked={groupByCompany}
                  onChange={(event) =>
                    setGroupByCompany(event.target.checked)
                  }
                />
                <span className="toggle-track">
                  <span className="toggle-thumb" />
                </span>
                <span>Group by company</span>
              </label>
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
          ) : visibleInterviews.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">⌕</div>
              <strong>No matching interviews</strong>
              <span>Try a different company, interviewer, round or role.</span>
            </div>
          ) : (
            <div className="interview-table interview-library-table">
              <div className="table-row table-head">
                <button
                  className="sortable-header"
                  type="button"
                  onClick={() => toggleSort("company")}
                >
                  Company <span>{sortIndicator("company")}</span>
                </button>
                <button
                  className="sortable-header"
                  type="button"
                  onClick={() => toggleSort("round")}
                >
                  Round type <span>{sortIndicator("round")}</span>
                </button>
                <span>Interviewer</span>
                <button
                  className="sortable-header"
                  type="button"
                  onClick={() => toggleSort("date")}
                >
                  Date <span>{sortIndicator("date")}</span>
                </button>
                <span>Duration</span>
                <span>Transcription</span>
                <span>Status</span>
                <span>Actions</span>
              </div>

              {(groupByCompany
                ? groupedInterviews.flatMap(([company, companyInterviews]) => [
                    <div
                      className="company-group-row"
                      key={`group-${company}`}
                    >
                      <span className="company-avatar company-avatar-small">
                        {company.slice(0, 1).toUpperCase()}
                      </span>
                      <strong>{company}</strong>
                      <span>
                        {companyInterviews.length} interview
                        {companyInterviews.length === 1 ? "" : "s"}
                      </span>
                    </div>,
                    ...companyInterviews.map((interview) =>
                      renderInterviewRow(interview, true),
                    ),
                  ])
                : visibleInterviews.map((interview) =>
                    renderInterviewRow(interview, false),
                  ))}
            </div>
          )}
        </section>
      </main>

      {isCancelConfirmOpen && activeInterview && (
        <div className="modal-backdrop" role="presentation">
          <div className="delete-modal stop-modal" role="dialog" aria-modal="true">
            <div className="delete-modal-heading">
              <div className="stop-modal-icon">■</div>
              <div>
                <h2>Stop processing?</h2>
                <p>The recording will be preserved.</p>
              </div>
            </div>

            <p className="delete-warning">
              Interview processing will stop at the next safe pipeline boundary.
              The current ML step may take a moment to finish before cancellation
              completes.
            </p>
            <p className="delete-safe-note">
              You can start processing again later.
            </p>

            <div className="modal-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={isCancellingProcessing}
                onClick={() => setIsCancelConfirmOpen(false)}
              >
                Keep processing
              </button>
              <button
                className="danger-button"
                type="button"
                disabled={isCancellingProcessing}
                onClick={() => void handleCancelProcessing()}
              >
                {isCancellingProcessing ? "Stopping…" : "Stop processing"}
              </button>
            </div>
          </div>
        </div>
      )}

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

      {editTarget && editForm && (
        <div className="modal-backdrop" role="presentation">
          <div className="modal-card edit-interview-modal" role="dialog" aria-modal="true">
            <div className="modal-header">
              <div>
                <p className="eyebrow">INTERVIEW DETAILS</p>
                <h2>Edit interview</h2>
                <p>Correct metadata without reprocessing the recording.</p>
              </div>
              <button
                className="icon-button"
                type="button"
                onClick={closeEditInterview}
              >
                ×
              </button>
            </div>

            <form className="upload-form" onSubmit={handleEditInterview}>
              <div className="form-grid">
                <label>
                  <span>Company</span>
                  <input
                    required
                    value={editForm.company}
                    onChange={(event) =>
                      setEditForm((current) =>
                        current
                          ? { ...current, company: event.target.value }
                          : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Interviewer / recruiter</span>
                  <input
                    required
                    value={editForm.interviewer}
                    onChange={(event) =>
                      setEditForm((current) =>
                        current
                          ? { ...current, interviewer: event.target.value }
                          : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Date & time</span>
                  <input
                    required
                    type="datetime-local"
                    value={editForm.datetime}
                    onChange={(event) =>
                      setEditForm((current) =>
                        current
                          ? { ...current, datetime: event.target.value }
                          : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Round number</span>
                  <input
                    required
                    min={1}
                    type="number"
                    value={editForm.sequence}
                    onChange={(event) =>
                      setEditForm((current) =>
                        current
                          ? {
                              ...current,
                              sequence: Number(event.target.value),
                            }
                          : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Round type</span>
                  <select
                    value={editForm.roundType}
                    onChange={(event) =>
                      setEditForm((current) =>
                        current
                          ? { ...current, roundType: event.target.value }
                          : current,
                      )
                    }
                  >
                    {ROUND_TYPES.map((roundType) => (
                      <option key={roundType} value={roundType}>
                        {roundType}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Role</span>
                  <input
                    value={editForm.role}
                    onChange={(event) =>
                      setEditForm((current) =>
                        current
                          ? { ...current, role: event.target.value }
                          : current,
                      )
                    }
                  />
                </label>

                <label>
                  <span>Target level</span>
                  <input
                    value={editForm.targetLevel}
                    onChange={(event) =>
                      setEditForm((current) =>
                        current
                          ? { ...current, targetLevel: event.target.value }
                          : current,
                      )
                    }
                  />
                </label>
              </div>

              {editError && <div className="inline-error">{editError}</div>}

              <div className="modal-actions">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isSavingEdit}
                  onClick={closeEditInterview}
                >
                  Cancel
                </button>
                <button
                  className="primary-button"
                  type="submit"
                  disabled={isSavingEdit}
                >
                  {isSavingEdit ? "Saving…" : "Save changes"}
                </button>
              </div>
            </form>
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
                  <span>Round type</span>
                  <select
                    value={uploadForm.roundType}
                    onChange={(event) =>
                      setUploadForm((current) => ({
                        ...current,
                        roundType: event.target.value,
                      }))
                    }
                  >
                    {ROUND_TYPES.map((roundType) => (
                      <option key={roundType} value={roundType}>
                        {roundType}
                      </option>
                    ))}
                  </select>
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

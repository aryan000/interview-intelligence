export type Interview = {
  id: string;
  company: string;
  recruiter_or_interviewer: string;
  interview_datetime: string;
  sequence_number: number;
  role: string | null;
  target_level: string | null;
  round_type: string | null;
  source_audio_path: string;
  artifact_root_path: string | null;
  duration_seconds: number | null;
  transcription_seconds: number | null;
  diarization_seconds: number | null;
  total_processing_seconds: number | null;
};

export type ProcessInterviewResponse = {
  job_id: string;
  interview_id: string;
  status: string;
};

export type JobEvent = {
  job_id: string;
  interview_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  stage: string;
  progress_percent: number;
  processed_audio_seconds: number;
  total_audio_seconds: number;
  message: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string;
  updated_at?: string;
  occurred_at?: string;
};

export type TranscriptResponse = {
  interview_id: string;
  transcript: string;
};

export type TranscriptLine = {
  start: string;
  end: string;
  startSeconds: number;
  endSeconds: number;
  speaker: string;
  text: string;
};

export type HiringSignal =
  | "strong_no_hire"
  | "no_hire"
  | "mixed"
  | "hire"
  | "strong_hire"
  | "insufficient_evidence";

export type QuestionReview = {
  sequence_number: number;
  question: string;
  question_start_seconds: number | null;
  answer_summary: string;
  strengths: string[];
  gaps: string[];
  stronger_answer: string | null;
  rating: number | null;
  level_signal: string | null;
};

export type InterviewReview = {
  interview_id: string;
  provider: string;
  model: string;
  overall_summary: string;
  hiring_signal: HiringSignal;
  confidence: number;
  strengths: string[];
  concerns: string[];
  improvement_areas: string[];
  questions: QuestionReview[];
  role_signal: string | null;
  level_signal: string | null;
};

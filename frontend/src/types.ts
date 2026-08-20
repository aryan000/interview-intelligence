export type Interview = {
  id: string;
  company: string;
  recruiter_or_interviewer: string;
  interview_datetime: string;
  sequence_number: number;
  role: string | null;
  target_level: string | null;
  source_audio_path: string;
  artifact_root_path: string | null;
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
  occurred_at?: string;
};

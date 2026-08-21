import type {
  Interview,
  InterviewReview,
  JobEvent,
  ProcessInterviewResponse,
  TranscriptResponse,
} from "./types";

const API_BASE = "http://127.0.0.1:8000/api/v1";
const WS_BASE = "ws://127.0.0.1:8000/api/v1";

async function responseError(response: Response): Promise<Error> {
  const raw = await response.text();
  try {
    const parsed = JSON.parse(raw) as { detail?: string };
    return new Error(parsed.detail ?? raw);
  } catch {
    return new Error(raw || `Request failed (${response.status})`);
  }
}

export async function listInterviews(): Promise<Interview[]> {
  const response = await fetch(`${API_BASE}/interviews`);
  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<Interview[]>;
}

export async function getTranscript(interviewId: string): Promise<TranscriptResponse> {
  const response = await fetch(`${API_BASE}/interviews/${interviewId}/transcript`);
  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<TranscriptResponse>;
}

export async function getInterviewReview(
  interviewId: string,
): Promise<InterviewReview | null> {
  const response = await fetch(`${API_BASE}/interviews/${interviewId}/review`);

  if (response.status === 404) return null;
  if (!response.ok) throw await responseError(response);

  return response.json() as Promise<InterviewReview>;
}

export async function analyzeInterview(
  interviewId: string,
): Promise<InterviewReview> {
  const response = await fetch(`${API_BASE}/interviews/${interviewId}/review`, {
    method: "POST",
  });

  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<InterviewReview>;
}

export async function deleteInterview(interviewId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/interviews/${interviewId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw await responseError(response);
  }
}

export async function getLatestInterviewJob(
  interviewId: string,
): Promise<JobEvent | null> {
  const response = await fetch(`${API_BASE}/interviews/${interviewId}/jobs/latest`);

  if (response.status === 404) return null;
  if (!response.ok) throw await responseError(response);

  const job = await response.json() as JobEvent & { id?: string };
  return {
    ...job,
    job_id: job.job_id ?? job.id ?? "",
  };
}

export function getAudioUrl(interviewId: string): string {
  return `${API_BASE}/interviews/${interviewId}/audio`;
}

export function getTranscriptDownloadUrl(interviewId: string): string {
  return `${API_BASE}/interviews/${interviewId}/transcript/download`;
}

export async function uploadInterview(input: {
  audio: File;
  company: string;
  recruiterOrInterviewer: string;
  interviewDatetime: string;
  sequenceNumber: number;
  role: string;
  targetLevel: string;
}): Promise<Interview> {
  const form = new FormData();
  form.append("audio", input.audio);
  form.append("company", input.company);
  form.append("recruiter_or_interviewer", input.recruiterOrInterviewer);
  form.append("interview_datetime", input.interviewDatetime);
  form.append("sequence_number", String(input.sequenceNumber));

  if (input.role.trim()) form.append("role", input.role.trim());
  if (input.targetLevel.trim()) form.append("target_level", input.targetLevel.trim());

  const response = await fetch(`${API_BASE}/interviews/upload`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<Interview>;
}

export async function cancelInterviewProcessing(
  interviewId: string,
): Promise<JobEvent> {
  const response = await fetch(
    `${API_BASE}/interviews/${interviewId}/process/cancel`,
    { method: "POST" },
  );

  if (!response.ok) throw await responseError(response);

  const job = await response.json() as JobEvent & { id?: string };
  return {
    ...job,
    job_id: job.job_id ?? job.id ?? "",
  };
}

export async function processInterview(
  interviewId: string,
): Promise<ProcessInterviewResponse> {
  const response = await fetch(
    `${API_BASE}/interviews/${interviewId}/process`,
    { method: "POST" },
  );

  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<ProcessInterviewResponse>;
}

export function subscribeToJob(
  jobId: string,
  onEvent: (event: JobEvent) => void,
  onError: (error: Error) => void,
): () => void {
  const socket = new WebSocket(`${WS_BASE}/jobs/${jobId}/events`);

  socket.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as JobEvent);
    } catch {
      onError(new Error("Received an invalid job progress event."));
    }
  };

  socket.onerror = () => {
    onError(new Error("Lost connection to processing progress."));
  };

  return () => socket.close();
}

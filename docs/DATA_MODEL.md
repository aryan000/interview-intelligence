# Data Model

## Overview

SQLite stores structured local application data.

Audio recordings and generated files remain on the filesystem.

The model should support future AI review without requiring major schema redesign.

## Interview

Represents the logical interview context.

Fields:

```text
id
company
role
target_level
round_type
interviewer_name
interview_date
created_at
updated_at
```

Example:

```text
company: Navi
role: Engineering Manager
target_level: EM
round_type: Recruiter
interviewer_name: Ashok
```

## Recording

Represents one physical audio recording.

An interview may contain multiple sequential recordings.

Fields:

```text
id
interview_id
sequence_number
source_filename
canonical_basename
source_path
cloud_audio_key
format
codec
duration_seconds
sample_rate
channels
file_size_bytes
created_at
```

Example canonical basename:

```text
2026-08-21_1615_ashok_01
```

Associated artifacts:

```text
2026-08-21_1615_ashok_01.aac
2026-08-21_1615_ashok_01.json
2026-08-21_1615_ashok_01.srt
2026-08-21_1615_ashok_01.md
```

## Job

Represents asynchronous processing.

Fields:

```text
id
recording_id
status
current_stage
progress_percent
audio_seconds_processed
started_at
completed_at
error_message
created_at
updated_at
```

Possible statuses:

```text
queued
running
completed
failed
cancelled
```

Possible stages:

```text
inspection
preprocessing
vad
transcription
diarization
alignment
export
cloud_sync
completed
```

## Job Metrics

Fields:

```text
job_id
audio_duration_seconds
inspection_duration_seconds
preprocessing_duration_seconds
vad_duration_seconds
transcription_duration_seconds
diarization_duration_seconds
alignment_duration_seconds
export_duration_seconds
cloud_sync_duration_seconds
total_duration_seconds
realtime_factor
model_name
engine_name
created_at
```

## Transcript

Represents the completed transcription.

Fields:

```text
id
recording_id
language
full_text
engine_name
model_name
created_at
updated_at
```

## Transcript Segment

Fields:

```text
id
transcript_id
sequence_number
start_seconds
end_seconds
speaker_id
text
confidence
```

Example:

```text
start_seconds: 822.0
end_seconds: 850.0
speaker_id: SPEAKER_01
text: Can you walk me through the architecture?
```

## Speaker

Fields:

```text
id
recording_id
external_label
display_name
speaker_type
created_at
updated_at
```

Example:

```text
external_label: SPEAKER_01
display_name: Interviewer
speaker_type: interviewer
```

Potential speaker types:

```text
interviewer
candidate
recruiter
unknown
```

## Silence Interval

Fields:

```text
id
recording_id
start_seconds
end_seconds
duration_seconds
```

## Word Timestamp

Optional.

Fields:

```text
id
segment_id
sequence_number
word
start_seconds
end_seconds
confidence
```

Word-level data may be omitted when word alignment is disabled.

## Artifact

Represents generated files.

Fields:

```text
id
recording_id
artifact_type
local_path
cloud_key
file_size_bytes
created_at
synced_at
```

Artifact types:

```text
audio
json
markdown
srt
txt
```

## Cloud Sync State

Fields:

```text
recording_id
sync_status
last_sync_attempt
last_successful_sync
error_message
```

Statuses:

```text
not_synced
syncing
synced
failed
```

## Future AI Review

The schema should reserve clean extension points for future AI evaluation.

### AI Review

Fields:

```text
id
interview_id
provider
model
role
target_level
round_type
overall_rating
likely_outcome
created_at
```

### AI Competency Score

Fields:

```text
id
review_id
competency
score
evidence
```

Example competencies:

```text
requirements
system_design
technical_depth
coding
leadership
communication
operational_excellence
product_thinking
```

### AI Feedback Item

Fields:

```text
id
review_id
category
severity
segment_start_seconds
segment_end_seconds
feedback
suggested_improvement
```

This allows AI feedback to reference exact areas of the interview timeline.

## Relationships

```text
Interview
   │
   ├── Recording 01
   │      │
   │      ├── Job
   │      ├── Transcript
   │      │      └── TranscriptSegments
   │      │             └── WordTimestamps
   │      ├── Speakers
   │      ├── SilenceIntervals
   │      └── Artifacts
   │
   ├── Recording 02
   │
   └── Future AI Reviews
```

## Storage Boundary

SQLite stores metadata and structured transcript information.

Filesystem stores binary and generated files.

Do not store large audio blobs directly inside SQLite.

## Naming

Canonical recording basename format:

```text
YYYY-MM-DD_HHMM_recruiter-name_NN
```

Example:

```text
2026-08-21_1615_ashok_01
```

The same basename must be used by every artifact belonging to that recording.

# Interview Intelligence

## Vision

Interview Intelligence turns every interview into a structured feedback loop.

The product records, transcribes, organizes, reviews, and eventually analyzes interview conversations so candidates can identify recurring strengths, weaknesses, and improvement areas across interview rounds.

The transcription engine runs locally on Apple Silicon for privacy and high-quality transcription, while completed recordings and transcripts can optionally be synchronized to an always-available cloud workspace.

## Problem

Interview preparation today is fragmented.

A typical workflow looks like:

1. Record an interview or recruiter conversation.
2. Convert the audio into a supported format.
3. Find a transcription tool capable of processing 60–90 minute recordings.
4. Wait for transcription.
5. Manually upload the transcript to an AI assistant.
6. Explain the role, level, company, and interview round again.
7. Ask for feedback.
8. Repeat this independently for every interview.

This loses valuable historical information.

There is no persistent feedback loop across interviews.

## Product Goal

Build a local-first interview intelligence system that provides:

- high-quality transcription
- speaker diarization
- timestamp preservation
- silence preservation
- interview organization
- audio playback
- searchable transcripts
- permanent cloud access
- shareable transcript links
- structured interview metadata
- future one-click AI feedback
- cross-interview performance analysis

## Primary User

Software engineering candidates preparing for senior technical roles such as:

- Engineering Manager
- Staff Engineer
- Senior Staff Engineer
- Technical Lead
- Senior Backend Engineer

The product should remain general enough to support other interview types later.

## Core Workflow

Audio Recording

→ Local Upload

→ Audio Detection

→ Preprocessing

→ High-Quality Transcription

→ Speaker Diarization

→ Timestamp Alignment

→ Transcript Review

→ Local Persistence

→ Optional Cloud Sync

→ Interview Library

→ Future AI Evaluation

→ Cross-Interview Feedback Loop

## Local Application

The local application runs on Apple Silicon.

Responsibilities:

- upload audio
- detect audio format
- normalize audio when required
- run transcription
- perform diarization
- preserve timestamps
- preserve silence intervals
- display real-time job progress
- review transcript
- rename speakers
- edit transcript
- export artifacts
- store interview metadata
- synchronize completed interviews to cloud storage

The local transcription engine should not depend on the cloud.

## Cloud Workspace

The cloud application is separate from the local transcription application.

It remains available even when the user's Mac is switched off.

Responsibilities:

- interview library
- company organization
- recording playback
- transcript viewing
- searching
- metadata viewing
- permanent access
- sharing
- future AI analysis viewing

Initial infrastructure:

- Cloudflare Pages
- Cloudflare R2

## Interview Organization

Each interview belongs to a company.

Example:

Company:

Navi

Recording artifacts share the same base filename:

2026-08-21_1615_recruiter-name_01.aac

2026-08-21_1615_recruiter-name_01.json

2026-08-21_1615_recruiter-name_01.srt

2026-08-21_1615_recruiter-name_01.md

Sequential recordings use:

_01

_02

_03

Company detection may be automated, but the user must be able to confirm or override it.

## Quality Principle

Transcription quality is the primary constraint.

Performance optimization must not materially reduce transcription quality.

Large-v3 remains the reference model unless another model demonstrates equivalent quality on representative interview recordings.

Speed improvements should come from:

- preprocessing improvements
- avoiding unnecessary conversion
- Voice Activity Detection
- efficient timestamp generation
- safe CPU/GPU pipelining
- optimized diarization
- caching
- batching where appropriate

Quality must not be sacrificed merely to achieve lower processing time.

## Speaker Awareness

Speaker diarization is a core product requirement.

Example:

[00:13:42 - 00:14:10] Interviewer

Can you walk me through the architecture?

[00:14:10 - 00:14:26] SILENCE - 16 seconds

[00:14:26 - 00:17:51] Candidate

Sure. The system was...

This enables future analysis of:

- question duration
- answer duration
- thinking time
- interruptions
- interviewer speaking time
- candidate speaking time
- section duration

## Future AI Intelligence

The long-term product is not merely a transcription application.

Completed interviews should support one-click AI evaluation.

Future providers may include:

- OpenAI
- Google Gemini
- Anthropic Claude
- local models
- additional providers

The AI provider layer must remain pluggable.

A user should eventually be able to select:

- company
- target role
- target level
- interview round

and click:

Review Interview

The system should produce structured feedback including:

- expected interview rating
- likely outcome
- role-level fit
- strengths
- growth areas
- question-by-question feedback
- technical depth
- communication quality
- leadership signals
- system design quality
- section timing
- suggested improved answers
- recommended practice topics

## Long-Term Feedback Loop

Individual interview analysis should eventually aggregate into cross-interview intelligence.

Examples:

- System Design: improving
- Requirements clarification: recurring weakness
- Technical depth: strong
- Operational excellence: inconsistent
- Leadership communication: improving
- Answers too implementation-heavy before establishing requirements

The product should help users understand not only how one interview went, but how their interviewing ability changes over time.

## Product Principles

1. Quality first.
2. Local-first transcription.
3. Privacy by default.
4. Cloud access is optional.
5. Cloud availability must not depend on the local machine.
6. Transcription engines must be pluggable.
7. AI providers must be pluggable.
8. Preserve the original timeline.
9. Speaker information is first-class data.
10. Build a modular monolith before considering microservices.
11. Keep infrastructure simple.
12. Make product decisions measurable through benchmarks.

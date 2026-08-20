# Roadmap

This file tracks the work remaining after the local-first MVP.

Statuses:

- ✅ Done
- 🚧 Next / in progress
- ⏳ Planned
- 💡 Later / exploration

---

# Current milestone — Local-first MVP

## Recording and processing

- ✅ Upload interview recordings.
- ✅ Inspect and normalize audio.
- ✅ Long-form local transcription.
- ✅ Speaker diarization.
- ✅ Transcript/speaker alignment.
- ✅ Candidate/interviewer role mapping.
- ✅ Transcript quality detection.
- ✅ Stable transcript/artifact export.
- ✅ Persist interview and processing job metadata.
- ✅ WebSocket progress events.
- ✅ Recover active jobs after frontend/browser restart.
- ✅ Persist `started_at` and derive elapsed time.
- ✅ Show interview duration.
- ✅ Delete interview and managed artifacts safely.
- ✅ Preserve original external recordings when deleting.

## Transcript Studio

- ✅ Speaker-labelled transcript.
- ✅ Audio playback.
- ✅ Click transcript row to seek audio.
- ✅ Transcript download.
- ✅ Transcript / AI Review tabs.
- ✅ Collapsible sidebar.

## AI Review

- ✅ Pluggable review-engine interface.
- ✅ Structured LLM review output.
- ✅ Overall hiring signal.
- ✅ Strengths, gaps and improvement areas.
- ✅ Question extraction.
- ✅ Question-by-question rating.
- ✅ Stronger-answer guidance.
- ✅ Role/level signal.
- ✅ Full-length interview review tested.
- ✅ AI Review page information-hierarchy redesign.

---

# Next milestone — Analysis observability and cost control

## 🚧 AI analysis execution UX

- [ ] Add a proper analysis-in-progress experience.
- [ ] Show elapsed analysis time.
- [ ] Show selected provider/model while running.
- [ ] Avoid fake percentage progress.
- [ ] Add clear stages such as:
  - preparing transcript;
  - evaluating interview;
  - structuring feedback;
  - persisting review.
- [ ] Make re-analysis state equally observable.
- [ ] Persist analysis start/completion timestamps.

## 🚧 Token and API cost visibility

- [ ] Capture input tokens.
- [ ] Capture output tokens.
- [ ] Capture reasoning tokens when provider exposes them.
- [ ] Persist model/provider used for each review.
- [ ] Calculate estimated/actual review cost.
- [ ] Show usage after review completes.
- [ ] Show an estimated cost before running a full review when possible.
- [ ] Add a monthly/local usage summary.

## 🚧 Model strategy

- [ ] Stop defaulting every analysis to the most expensive model.
- [ ] Benchmark cheaper models for normal interview analysis.
- [ ] Add a default economical analysis mode.
- [ ] Add optional **Deep Review** using a stronger model.
- [ ] Compare review quality across providers/models.
- [ ] Handle provider quota/authentication/network errors cleanly in API responses.
- [ ] Allow provider selection without changing UI contracts.

---

# Product differentiator — Cross-interview intelligence

This is the major product milestone after single-round review.

## ⏳ Interview history

- [ ] Group rounds by company/interview process.
- [ ] Company-level interview timeline.
- [ ] Round type/category:
  - coding;
  - LLD;
  - HLD/system design;
  - leadership;
  - hiring manager;
  - behavioral;
  - culture.
- [ ] Search/filter by company, role, date, round and outcome.

## ⏳ Competency taxonomy

Create normalized dimensions such as:

```text
Requirements clarification
System decomposition
Scale estimation
API design
Data modelling
Storage selection
Reliability
Consistency
Trade-offs
Operational excellence
Technical depth
Communication
Product thinking
Leadership
People management
Execution
Stakeholder management
```

- [ ] Map per-question evidence into competencies.
- [ ] Persist competency signals separately from prose review.
- [ ] Avoid inventing competency scores that are unsupported by evidence.

## ⏳ Trends

Examples the product should eventually surface:

> System-design structure was below bar in 3 of your last 4 design interviews.

> Production debugging improved from 3/5 → 4/5 → 4/5.

> You frequently select a database before stating access patterns.

- [ ] Recurring-strength detection.
- [ ] Recurring-gap detection.
- [ ] Trend visualization.
- [ ] Company/round comparisons.
- [ ] Identify recurring interviewer prompts.
- [ ] Detect improvement/regression.
- [ ] Confidence/evidence coverage for trends.

## ⏳ Practice recommendations

- [ ] Generate a "What to practice next" plan.
- [ ] Recommend system-design topics from actual gaps.
- [ ] Generate targeted mock questions.
- [ ] Create stronger answers based on prior interview evidence.
- [ ] Track whether recommended gaps improve in later rounds.

---

# Review UX backlog

Deferred polish from the current AI Review redesign:

- [ ] Collapse long overall assessment with `Read full assessment`.
- [ ] Improve coaching-card fallback headings.
- [ ] Slightly increase lower-section typography.
- [ ] Improve Top Strength / Top Gap signal presentation.
- [ ] Show analysis timestamp/model/cost beside Re-run Analysis.
- [ ] Better rating/accessibility colors.
- [ ] Improve mobile layout.
- [ ] Preserve/restore review accordion state where useful.

---

# Processing improvements

## ⏳ Better transcription progress

Current transcription engines do not expose sufficiently granular progress.

- [ ] Report per-chunk transcription progress.
- [ ] Persist chunk checkpoints.
- [ ] Resume interrupted long transcriptions.
- [ ] Estimate progress using completed audio seconds.
- [ ] Keep ETA explicitly labelled as an estimate.

## ⏳ Job controls

- [ ] Cancel active processing.
- [ ] Retry failed jobs.
- [ ] Restart from a safe stage/checkpoint.
- [ ] Prevent duplicate jobs for the same interview.
- [ ] Stale-running-job detection after backend crashes.
- [ ] Recovery policy when the machine reboots.

## ⏳ Performance

- [ ] Benchmark 30/60/90-minute recordings.
- [ ] Record cold vs warm model timings.
- [ ] Track real-time factor per stage.
- [ ] Reduce transcription memory usage where possible.
- [ ] Explore parallelism without overwhelming the laptop.
- [ ] Benchmark quality/speed trade-offs for alternate transcription models.

---

# Transcript and diarization improvements

- [ ] Better proper-noun / company vocabulary support.
- [ ] Better interviewer/candidate role inference.
- [ ] Manual speaker correction UI.
- [ ] Manual transcript correction.
- [ ] Search within transcript.
- [ ] Jump from review question directly to relevant audio/transcript timestamp.
- [ ] Highlight candidate vs interviewer more clearly.
- [ ] Confidence markers for uncertain transcript regions.
- [ ] Detect additional ASR repetition/hallucination patterns.
- [ ] Add quality score/evidence coverage to each processed interview.

---

# Interview management

- ✅ Delete interview.
- ✅ Search company/interviewer.
- [ ] Edit interview metadata.
- [ ] Duplicate/interview collision detection.
- [ ] Company logos or lightweight visual identifiers.
- [ ] Tags.
- [ ] Archive instead of delete.
- [ ] Bulk operations.
- [ ] Export complete interview bundle.
- [ ] Import an existing generated bundle.
- [ ] Direct transcript upload without re-running audio processing.

The last item is particularly useful when a transcript already exists and the user only wants analysis.

---

# Cloudflare / secure remote access

The intended near-term remote-access experiment is **Cloudflare**, not AWS CloudFront.

## ⏳ Cloudflare Tunnel

Goal:

> Access the local-first application securely from another device while keeping recordings, SQLite and local ML processing on the host machine.

Planned work:

- [ ] Decide a single production origin for frontend + API.
- [ ] Add production frontend API URL configuration.
- [ ] Configure `cloudflared`.
- [ ] Create Cloudflare Tunnel.
- [ ] Map a subdomain/domain to the tunnel.
- [ ] Keep local backend bound safely.
- [ ] Verify WebSocket support through the tunnel.
- [ ] Verify audio streaming/range requests.
- [ ] Verify long review/API requests.
- [ ] Document tunnel start/stop procedures.

## ⏳ Cloudflare Access

Do **not** expose transcripts/audio publicly.

- [ ] Put Cloudflare Access in front of the application.
- [ ] Restrict access to authorized identities.
- [ ] Review session/auth behavior.
- [ ] Protect write/delete/process/review endpoints.
- [ ] Add application-level auth if/when multiple users are supported.

## ⏳ Security review before remote exposure

- [ ] CSRF strategy.
- [ ] CORS production rules.
- [ ] Security headers.
- [ ] Rate limiting.
- [ ] Secret handling.
- [ ] API error sanitization.
- [ ] Path traversal review.
- [ ] File download authorization.
- [ ] Audit delete behavior.
- [ ] Upload size/type limits.
- [ ] Retention/privacy policy.

---

# Local-first product packaging

- [ ] One-command startup script.
- [ ] Development vs production configuration.
- [ ] Serve built React assets from a single local origin or packaged process.
- [ ] Health-check endpoint.
- [ ] Startup diagnostics:
  - FFmpeg availability;
  - model access/cache;
  - MPS availability;
  - disk space;
  - API key state.
- [ ] Graceful shutdown.
- [ ] Optional menu-bar/native wrapper exploration.
- [ ] Installer/package for non-developer users.

---

# Data and persistence

## ⏳ SQLite hardening

- [ ] Schema migration framework.
- [ ] Database backup/export.
- [ ] Corruption/recovery documentation.
- [ ] Indexes as interview history grows.
- [ ] Persist AI usage/cost history.
- [ ] Persist normalized competency/evidence data.

## 💡 Multi-user/cloud mode

Only after product-market fit / genuine multi-device need:

- [ ] Postgres.
- [ ] Object storage.
- [ ] durable queue.
- [ ] worker fleet.
- [ ] hosted GPU inference.
- [ ] tenant/user data isolation.
- [ ] cloud retention policy.

This is intentionally **not** part of the immediate local-first roadmap.

---

# Testing and engineering quality

- ✅ pytest suite.
- ✅ Ruff.
- ✅ mypy.
- ✅ frontend TypeScript production build.

Next:

- [ ] Frontend component/unit tests.
- [ ] End-to-end browser tests.
- [ ] Golden transcript fixtures.
- [ ] Golden AI review fixtures.
- [ ] Regression test for browser restart during processing.
- [ ] Regression test for deletion safety.
- [ ] Long-audio integration test profile.
- [ ] Mock provider responses for all AI failure classes.
- [ ] CI workflow on GitHub.
- [ ] CI should not require paid API/model calls.

---

# GitHub/project polish

- ✅ Main README/setup documentation.
- ✅ Architecture document.
- ✅ Roadmap document.
- [ ] Add project screenshots to `docs/images/`.
- [ ] Add a short demo GIF/video.
- [ ] Add `LICENSE`.
- [ ] Add `CONTRIBUTING.md`.
- [ ] Add `.env.example` without secrets.
- [ ] Add GitHub Actions CI badge.
- [ ] Add architecture/status badges only if they remain accurate.
- [ ] Add release/versioning strategy.
- [ ] Create GitHub issues/milestones from this roadmap.

---

# Suggested execution order

## Phase 1 — close the current MVP

1. Analysis elapsed-time UI.
2. Token + cost capture.
3. Cheaper/default review model.
4. Provider error handling.
5. Direct transcript upload.
6. GitHub CI.

## Phase 2 — make it uniquely useful

7. Competency taxonomy.
8. Persist normalized question/competency evidence.
9. Cross-interview recurring-pattern detection.
10. Trend dashboard.
11. Practice recommendations.

## Phase 3 — access it safely anywhere

12. Production single-origin local build.
13. Cloudflare Tunnel.
14. Cloudflare Access.
15. Security hardening.

## Phase 4 — productize

16. One-command installer/startup.
17. Better job retry/resume/cancel.
18. Metadata editing/grouping.
19. Export/import.
20. Evaluate whether multi-user cloud architecture is actually needed.

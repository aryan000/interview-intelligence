# ADR-004: Use Cloudflare R2 and Pages for the Cloud Library

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

The local Mac cannot remain powered on continuously.

Completed recordings and transcripts must remain accessible from the internet even when the local transcription application is offline.

The initial goal is to minimize or eliminate recurring hosting cost for personal-scale usage.

## Decision

Use Cloudflare R2 for synchronized interview artifacts and Cloudflare Pages for the always-available web viewer.

The local application remains responsible for transcription.

After a job completes, cloud synchronization may upload:

- source audio
- transcript JSON
- Markdown transcript
- SRT
- metadata
- other generated artifacts

The R2 bucket should not be made generally public by default.

The web viewer will provide controlled access to private library content and later support explicit share links.

Cloud synchronization must remain optional.

## Consequences

### Positive

- The Mac can be switched off after synchronization.
- Separates expensive/local ML computation from lightweight cloud serving.
- Supports permanent transcript and recording access.
- Suitable for a low-cost personal cloud library.
- Storage provider remains replaceable behind an interface.

### Negative

- Requires cloud credentials and synchronization logic.
- Private access and sharing require an authorization design.
- Cloudflare-specific deployment configuration must be maintained.

## Alternatives Considered

### Gradio `share=True`

Rejected as permanent hosting because the local application must remain running and reachable.

### Cloudflare Tunnel to the Mac

Useful for temporary remote access but rejected as the permanent library architecture because the Mac must remain online.

### Host Whisper in the cloud

Rejected for V1 because it introduces compute cost and moves the core privacy-sensitive workload off the local machine.

## Follow-up

Define authentication, private-object access, share-link revocation, expiry, and optional password protection before public sharing is enabled.

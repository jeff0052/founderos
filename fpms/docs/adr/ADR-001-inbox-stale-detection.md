# ADR-001: Inbox Stale Detection Uses created_at

**Status**: Accepted  
**Date**: 2026-03-18  
**Context**: PRD FR-5.2 defines stale as "active/waiting AND status_changed_at < NOW()-7d"

## Decision

`risk.py` extends stale detection to inbox nodes, using `created_at` instead of `status_changed_at`.

## Rationale

- Inbox nodes that sit for 7+ days without being triaged are a real risk signal
- Using `created_at` is correct for inbox because `status_changed_at` equals `created_at` for nodes that were never moved out of inbox
- PRD's definition was conservative; extending to inbox catches forgotten items

## Consequences

- Stale alerts will fire for old inbox items (desired behavior)
- Deviates from strict PRD FR-5.2 wording (documented here)

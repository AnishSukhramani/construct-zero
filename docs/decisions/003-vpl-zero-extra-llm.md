# ADR 003: VPL extractive; zero extra LLM calls

**Status:** Accepted

## Context

Long Hermes replies are poor for listening. A second LLM pass to "summarize for speech" adds cost, latency, and hallucination risk.

## Decision

**Voice Presentation Layer (VPL)** parses Markdown structure extractively, buckets numbered items, and drives an orient → map → deepen FSM. Speech text is **verbatim excerpts** from source spans. No additional model calls in VPL.

## Consequences

- VPL lives in [vpl/](../../vpl/) as a standalone library.
- Voice sidecar wires VPL after Hermes returns full text; screen shows unchanged `reply_full`.
- Navigation turns ("second", "tell me more about bucket 2") use VPL session state only — skip Hermes when intent is navigational.
- Do not add LLM summarization to VPL without a new ADR.

# ADR 005: Agent home — shared context without a second agent loop

**Status:** Accepted (2026-10-01)

## Context

Developers run multiple agent harnesses (Claude Code, Cursor, Hermes) in the same repo and lose context on quota limits or manual switches. Pain Radar evidence (Oct 2026) shows subscription juggling and fragmented memory formats.

Construct-Zero previously listed "Second agent brain inside CZ" as out of scope; Hermes owns the agent loop and tools per ADR 001.

## Decision

Construct-Zero hosts a **file-based shared context home** per project (`.cz/`) and **orchestrates external agent CLIs** (detect, run wrapper, handoff, caps, kill switch). It does **not** run an agent loop, execute tools, or call models except through the existing inference adapter for Hermes traffic.

Intelligence remains in the user's agents. CZ provides:

- Durable shared files (context, memory, checkpoint, decisions, tasks)
- Pointer blocks in harness-native files (AGENTS.md, CLAUDE.md, Cursor rules)
- Registry of detected agents and fallback order
- (Later PRs) quota-aware run wrapper, usage ledger, group channel moderator (deterministic FSM, not an LLM)

## Consequences

- Update feature registry: out of scope is **second agent loop inside CZ**, not shared context hosting.
- `.cz/` stays local; default exclude via `.git/info/exclude`.
- All writes are locked and redacted on import paths (PR 19+).

## Supersedes

Clarifies the "Second agent brain" line in `docs/features/index.md`; does not change inference-only or ask-mode invariants.

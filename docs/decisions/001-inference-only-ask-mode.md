# ADR 001: Inference-only adapter; Cursor `ask` never `agent`

**Status:** Accepted

## Context

Hermes is a full agent with tools. Cursor also has agent mode with built-in tools. Running both creates two competing agent brains.

## Decision

HCX adapter is **inference-only**. Cursor driver uses SDK `mode=ask`. Hermes tools are passthrough via `custom_tools`; Hermes executes all tool results.

## Consequences

- Config must keep `cursor.mode: ask` in [config/hermesxcursor.yaml.example](../../config/hermesxcursor.yaml.example).
- Do not enable Cursor built-in tools in the adapter path.
- Feature work belongs in Hermes upstream or HCX passthrough — not a second agent in HCX.

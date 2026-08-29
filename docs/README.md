# Agent documentation (`docs/`)

Progressive-disclosure knowledge base for Cursor agents working on **construct-zero / HCX**.

## How to navigate

1. Start at root [AGENTS.md](../AGENTS.md) (table of contents).
2. Open [features/index.md](features/index.md) to find the subsystem you are changing.
3. Read **one** feature doc for the task at hand — do not load the entire tree.
4. Use [ARCHITECTURE.md](../ARCHITECTURE.md) for cross-cutting system map.
5. Check [decisions/](decisions/) before proposing architecture changes.

## Maintenance

After materially changing a subsystem, update the relevant feature doc and [features/index.md](features/index.md). See [.cursor/rules/docs-maintenance.mdc](../.cursor/rules/docs-maintenance.mdc).

- **Source code** is the ultimate truth.
- **Do not** copy from gitignored `zzz-docs/` verbatim — distill into `docs/` instead.
- **Do not** bloat root `AGENTS.md` — add detail here.

## Layout

| Path | Purpose |
|------|---------|
| [features/](features/) | Feature registry + per-feature deep dives |
| [architecture/](architecture/) | Data flow, boundaries |
| [decisions/](decisions/) | Lightweight ADRs (why, not how) |
| [references/](references/) | Coding style, scripts catalog |
| [plans/](plans/) | Active/completed execution plans (placeholder) |

Human onboarding: [README.md](../README.md). Deploy flow: [PRE-COMMIT-CHECKLIST.md](../PRE-COMMIT-CHECKLIST.md).

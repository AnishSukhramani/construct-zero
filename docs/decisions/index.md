# Architecture decision records (ADRs)

Lightweight **why** documents so agents do not relitigate settled choices.

| ID | Title | Status |
|----|-------|--------|
| [001](001-inference-only-ask-mode.md) | Inference-only adapter; Cursor `ask` never `agent` | Accepted |
| [002](002-hermes-not-vendored.md) | Hermes upstream gitignored in `hermes/` | Accepted |
| [003](003-vpl-zero-extra-llm.md) | VPL extractive; zero extra LLM calls | Accepted |
| [004](004-construct-zero-rename.md) | Rebrand to Construct-Zero; shim old HCX names | Accepted |

When reversing an ADR, add a new ADR that supersedes the old one — do not silently delete history.

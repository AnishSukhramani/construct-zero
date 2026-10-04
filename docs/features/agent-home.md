# Agent home (shared context)

**Status:** Preview (PRs 18–22)

Construct-Zero can initialize a per-project **shared context store** at `.cz/` and install **pointer blocks** so Claude Code, Cursor, and Hermes read the same files without duplicating memory formats.

## Boundary

CZ does **not** run an agent loop or tools. See [ADR 005](../decisions/005-agent-home.md).

## Quick start

```bash
./construct-zero home init          # creates .cz/ + pointers (Preview)
./construct-zero home status
./construct-zero home memory add "Title" "Fact body"
./construct-zero home uninstall   # removes pointer blocks only
./construct-zero kill | unkill    # global kill switch (adapter 503 cz_killed)
./construct-zero usage --since 7d
```

Adapter admin routes (loopback, admin key in `$CZ_STATE_DIR/admin.key`): `GET /cz/v1/usage`, `GET /cz/v1/agents`, `POST /cz/v1/admin/kill|unkill`.

## Layout

| Path | Purpose |
|------|---------|
| `.cz/CONTEXT.md` | Project brief |
| `.cz/MEMORY.md` | Durable facts (IDs, provenance, supersede) |
| `.cz/DECISIONS.md` | Append-only decisions |
| `.cz/TASKS.md` | Task list |
| `.cz/checkpoint.md` | Latest handoff checkpoint (PR 19) |
| `$CZ_STATE_DIR/home/registry.json` | Detected agents and initialized projects |

## Git

By default `.cz/` is listed in `.git/info/exclude` (not `.gitignore`). Use `home init --commit` to skip exclude if the team commits shared context.

## Related

- [PRD shared context home](../plans/active/README.md) (Anish, Oct 2026)
- Handoff MVP: `construct-zero run <agent> [--auto-handoff]`, `construct-zero handoff --to <agent> [--no-launch]` (Preview)
- Usage ledger, optional `budgets.yaml` caps, kill switch, `construct-zero usage` (Preview)

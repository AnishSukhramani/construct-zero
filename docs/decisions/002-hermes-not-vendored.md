# ADR 002: Hermes upstream not vendored (`hermes/` gitignored)

**Status:** Accepted

## Context

Hermes Agent is a large upstream project with its own license and release cadence. Vendoring it in construct-zero complicates OSS boundaries and `git add .` safety.

## Decision

- Upstream clones into gitignored `hermes/` via `./scripts/setup.sh`.
- Pin recommended version in [config/upstream.lock.yaml](../../config/upstream.lock.yaml).
- Repo ships plugin + adapter only; users run `./scripts/setup.sh` after clone.

## Consequences

- Agents never commit `hermes/` paths.
- `./scripts/update-hermes.sh` updates local clone independently of Construct-Zero git history.
- Hermes runtime data stays in `~/.hermes/`, not in `hermes/` clone path for config.

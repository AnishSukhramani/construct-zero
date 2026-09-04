# Pre-commit & deploy checklist

Run this flow **before every commit and push**. You run all git commands yourself — coding agents must not.

Local test scripts live under `private/` (gitignored). If `private/scripts/` is missing on a machine, recreate it from your backup or skip to step 2 and rely on manual `git status` review.

---

## 1. Run unit tests

From repo root:

```bash
# Quick (vpl + adapter + private safety tests — ~25 tests)
./private/scripts/run-tests.sh --fast

# Full suite before a release or large change (~33 tests)
./private/scripts/run-tests.sh

# Optional: also hit /health if adapter is already running (read-only)
./private/scripts/run-tests.sh --smoke
```

All tests must pass. Tests do **not** stop your running adapter, voice sidecar, or Hermes.

---

## 2. Stage changes

```bash
git add .
git status
```

Review the list. You should see only product paths (`adapter/`, `voice/`, `vpl/`, `scripts/`, etc.) — **not** `hermes/`, `.env`, `private/`, or `zzz-docs/`.

---

## 3. Verify staged files (safety gate)

```bash
./private/scripts/verify-staged.sh
```

This read-only check fails if staged files include forbidden paths or obvious secrets.

Optional double-check (if `grep` is available):

```bash
git diff --cached --name-only | grep '^hermes/'
git diff --cached --name-only | grep -E '^(\.env$|\.venvs/|zzz-docs/|private/)'
```

Both should print **nothing**.

---

## 4. Commit

```bash
git commit -m "Short description of why this change matters"
```

Use a clear message focused on the **why**, not just file names.

---

## 5. Push (deploy to GitHub)

```bash
git push
```

First push on a new branch:

```bash
git push -u origin main
```

After push, open the repo on GitHub and confirm no `hermes/`, `.env`, or `private/` appeared in the tree.

---

## Full copy-paste flow

```bash
cd /path/to/construct-zero

./private/scripts/run-tests.sh --fast

git add .
git status
./private/scripts/verify-staged.sh

git commit -m "your message here"
git push
```

---

## What must never be committed

| Path | Reason |
|------|--------|
| `hermes/` | Upstream Hermes clone |
| `.env` | API keys |
| `.venvs/`, `adapter/.venv/` | Python envs |
| `private/` | Local test harness |
| `zzz-docs/` | Private research |
| `config/construct-zero.yaml` | Local adapter config |

---

## Agent rule

Per [AGENTS.md](AGENTS.md) and `.cursor/rules/00-governance.mdc`: agents **never** run `git add`, `commit`, `push`, or `pull`. They may suggest this checklist; you execute it.

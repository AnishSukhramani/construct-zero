# Pre-commit & deploy checklist

Run this flow **before every commit and push**. You run all git commands yourself — coding agents must not (unless explicitly authorized for a CI task).

Public test and safety scripts live under `scripts/` and `scripts/ci/`. If you still have `private/scripts/` from an older setup, those paths work too.

---

## 1. Run unit tests

From repo root:

```bash
# Quick (vpl + adapter + tests/repo — voice skipped)
./scripts/run-tests.sh --fast

# Full suite before a release or large change (vpl + adapter + voice + tests/repo)
./scripts/run-tests.sh

# Optional: also hit /health if adapter is already running (read-only)
./scripts/run-tests.sh --smoke
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
./scripts/ci/verify-staged.sh
```

This read-only check fails if staged files include forbidden paths or obvious secrets.

Optional double-check (if `grep` is available):

```bash
git diff --cached --name-only | grep '^hermes/'
git diff --cached --name-only | grep -E '^(\.env$|\.venvs/|zzz-docs/|private/)'
```

Both should print **nothing**.

Optional: install a git pre-commit hook (runs verify-staged + fast tests):

```bash
./scripts/ci/install-git-hooks.sh
```

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
git push -u origin <branch-name>
```

After push, open the repo on GitHub and confirm no `hermes/`, `.env`, or `private/` appeared in the tree.

---

## Full copy-paste flow

```bash
cd /path/to/construct-zero

./scripts/run-tests.sh --fast

git add .
git status
./scripts/ci/verify-staged.sh

git commit -m "your message here"
git push
```

Legacy path (if present): `./private/scripts/run-tests.sh --fast` and `./private/scripts/verify-staged.sh`.

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

Per [AGENTS.md](AGENTS.md) and `.cursor/rules/00-governance.mdc`: agents **never** run `git add`, `commit`, or `push` unless Anish explicitly authorizes a CI/engineering task. They may suggest this checklist; you execute it.

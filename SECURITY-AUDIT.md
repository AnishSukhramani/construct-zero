# Construct-Zero security audit (2026-10-13)

Threat model for running Construct-Zero inside a **private or proprietary** monorepo. Severity: **Critical / High / Medium / Low / Informational**.

## Executive summary

| Severity | Count | Fixed in this PR |
|----------|------:|------------------|
| Critical | 0 | — |
| High | 2 | 2 |
| Medium | 4 | 3 (+1 documented) |
| Low | 3 | 2 (+1 documented) |
| Informational | 5 | documented |

**Honest egress statement:** With the default Cursor backend, **prompts and attached code context are sent to Cursor’s servers** under the user’s Cursor API key. Construct-Zero does not operate a separate analytics pipeline; supply-chain and install paths can still fetch from GitHub, Astral (uv), and PyPI during setup.

---

## Findings

### High

| ID | Finding | Location | Fix |
|----|---------|----------|-----|
| H-1 | **Project isolation:** Hermes/Cursor used CZ install directory (or temp workspace) as the project, so agents greeted with “Construct Zero” instead of the host app. | `adapter/src/construct_zero/drivers/cursor.py:138-141` (temp mkdtemp when `workspace_isolation: true`); `construct-zero:46-68` (chat cwd); `voice/.../hermes_bridge.py:149` (cwd = repo root) | Resolve `CZ_PROJECT_ROOT` / user project root; Cursor `cwd` = project root; `./construct-zero chat` runs Hermes from parent repo; agent ignore files |
| H-2 | **Open loopback API:** Missing adapter bearer allows any local process to call `/v1/*`. | `adapter/src/construct_zero/server.py:94-104`; `scripts/doctor.sh:143-147` | Document + doctor advisory `adapter-auth`; recommend `adapter.api_key` / `CZ_API_KEY` (unchanged default empty for compat) |

### Medium

| ID | Finding | Location | Fix / note |
|----|---------|----------|------------|
| M-1 | **DNS rebinding:** No Host header validation on loopback bind. | `adapter/src/construct_zero/server.py` (no middleware) | `LoopbackHostMiddleware` rejects non-loopback `Host` / `Origin` |
| M-2 | **Secret leakage in logs/errors:** Exceptions and doctor paths could echo upstream messages containing keys. | `adapter/src/construct_zero/server.py:235,367`; `adapter/src/construct_zero/doctor/checks.py` | Central `redact()` on errors, doctor detail, ledger-safe design |
| M-3 | **Redaction coverage limited** (home store only). | `adapter/src/construct_zero/home/redact.py` (prior) | Expanded patterns (JWT, cloud keys, conn strings, high-entropy); logging filter |
| M-4 | **Data to Cursor cloud** (by design, not a CZ bug). | `adapter/src/construct_zero/drivers/cursor.py` (cursor-sdk) | Documented in SECURITY.md; Privacy Mode + `openai_compat` for regulated use |

### Low

| ID | Finding | Location | Fix |
|----|---------|----------|-----|
| L-1 | State dir permissions not enforced everywhere. | `adapter/src/construct_zero/home/ledger.py:41-44`; `admin.py:22-28` | `ensure_secure_dir` / `ensure_secure_file` (0700/0600) |
| L-2 | **curl \| bash** install and uv installer. | `install.sh:59-60`; `scripts/lib/common.sh:231` | Documented supply-chain mitigations; pin Hermes via lock |
| L-3 | CORS not explicitly denied (FastAPI default none). | N/A | No permissive CORS added; browser cross-origin blocked via Origin check |

### Informational

| ID | Topic | Notes |
|----|-------|-------|
| I-1 | **Network egress (runtime)** | Cursor SDK → Cursor API; optional `openai_compat` → configured URL; local `urllib`/`httpx` for `/health`, admin kill, voice adapter check |
| I-2 | **Network egress (setup)** | `git clone` Hermes; PyPI via uv; optional `curl` bootstrap |
| I-3 | **Disk reads** | Config YAML chain `config.py:20-32`; `.env` via scripts; `.cz/` home store; Hermes `~/.hermes`; no full-repo scan by adapter |
| I-4 | **Logging** | Ledger stores token counts only (`ledger.py:12-31`); no request bodies logged unless `CZ_DEBUG_HTTP_BODIES=1` (still redacted) |
| I-5 | **Telemetry** | No Sentry/Segment/etc. in runtime sources (`scripts/ci/telemetry_check.py`) |

---

## Component notes

### Adapter (`127.0.0.1:8765`)

- Bind: config `adapter.host` (default loopback) — `config.py:75-78`
- Auth: optional bearer — `server.py:94-104`; placeholder `unused` in init — `scripts/init.sh:105-109`
- Hermes plugin: `hermes-plugin/.../__init__.py` points at local base URL only

### Shared context home (`.cz/`)

- Per-project store under user project root — `home/store.py`
- Importers may read git diff / Claude transcripts — `home/importers/*`
- Redaction on import wrap — `security/redact.py`

### CI

- GitHub Actions per `.github/workflows/` — gitleaks, guardrails, pinned actions (see `tests/repo/`)

### Company responsibility

- Cursor Privacy Mode, org API keys, and prompt hygiene
- Legal/compliance review for MIT “AS IS” terms (see README **Security & liability**)

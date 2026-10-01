# CI/CD reference

Construct Zero keeps CI workflows in `.github/` (GitHub cannot run gitignored pipelines). They are **not** part of the installed product; release archives exclude them via `.gitattributes` `export-ignore`.

## Local runner

```bash
make ci    # same ordered steps as CI (extended as PRs 03–09 land)
make test  # scripts/run-tests.sh --fast
```

Implementation: [`scripts/ci-local.sh`](../../scripts/ci-local.sh) and [`Makefile`](../../Makefile).

## Checks

| Check | Job | Notes |
|-------|-----|-------|
| `tests` | Aggregator + package matrix | adapter, vpl, voice × Python 3.10–3.12 |
| `lint` | Ruff | adapter/vpl/voice/hermes-plugin/tests |
| `types` | mypy | Lenient per-package baselines |
| `shellcheck` | Shell scripts | install.sh, construct-zero, scripts/*.sh |
| `secrets` | gitleaks | PR diff |
| `deps-audit` | pip-audit | Lockfile exports; `scripts/ci/audit-ignore.toml` |
| `license` | pip-licenses | `scripts/ci/license-allowlist.toml` |
| `dependency-review` | GitHub | PR dependency changes |
| `coverage` | pytest-cov | `scripts/ci/coverage-check.py` + floors |
| `guardrails` | PRs only | Policy on diffs; no-op on push to `main` |

Later PRs add: `contract`, `conformance`, `hermes-pinned`, `first-run`, `pin-bump`, `release`, `canary`.

## Labels (Anish applies)

| Label | Effect |
|-------|--------|
| `no-test-needed` | Source/scripts change without test updates |
| `test-change-approved` | Delete tests, add skip/xfail, or lower coverage floors |
| `pin-bump-approved` | Change `config/upstream.lock.yaml` (PR 09) |

Guardrails reads labels via the GitHub API. Actor verification is best-effort only; **merge authority is the real gate**.

## Protected paths

Touches to these paths require a `## Protected paths` section in the PR body:

`install.sh`, `config/upstream.lock.yaml`, `.github/**`, `scripts/doctor.sh`, `scripts/ci/**`, `*/uv.lock`, `.gitattributes`, `Makefile`

## Agents

Cloud agents open **draft** PRs only. Soft diff cap ~400 lines (excluding locks/format). See [AGENTS.md](../../AGENTS.md) CI contract.

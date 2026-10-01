#!/usr/bin/env bash
# Ordered CI steps — same sequence locally and in GitHub Actions (extended in later PRs).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
cd "$ROOT"

STEP="${1:-ci}"

run_tests() {
  "$ROOT/scripts/run-tests.sh" --fast
}

run_guardrails() {
  if [[ "${GUARDRAILS_SKIP:-}" == "1" ]]; then
    echo "guardrails: skipped (GUARDRAILS_SKIP=1)"
    return 0
  fi
  python3 "$ROOT/scripts/ci/guardrails.py" --local
}

run_lint() {
  cd "$ROOT/adapter"
  uv sync --locked --extra dev
  uv run ruff check "$ROOT/adapter" "$ROOT/vpl" "$ROOT/voice" "$ROOT/hermes-plugin" "$ROOT/tests"
}

run_types() {
  cd "$ROOT/adapter"
  uv sync --locked --extra dev
  cd "$ROOT/adapter" && uv run mypy
  cd "$ROOT" && uv run --project adapter mypy --config-file vpl/mypy.ini
  cd "$ROOT" && uv run --project adapter mypy --config-file voice/mypy.ini
}

run_shellcheck() {
  if ! command -v shellcheck >/dev/null 2>&1; then
    echo "shellcheck: not installed — skip (CI runs shellcheck on Ubuntu)"
    return 0
  fi
  shellcheck "$ROOT/install.sh" "$ROOT/construct-zero" "$ROOT"/scripts/*.sh "$ROOT"/scripts/lib/*.sh
}

run_secrets() {
  if [[ "${GITLEAKS_SKIP:-}" == "1" ]]; then
    echo "secrets: skipped (GITLEAKS_SKIP=1)"
    return 0
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "secrets: curl missing — skip"
    return 0
  fi
  bash "$ROOT/scripts/ci/gitleaks.sh"
}

run_deps_audit() {
  if [[ "${CI:-}" != "true" ]]; then
    echo "deps-audit: skip locally; CI=true on GitHub Actions"
    python3 "$ROOT/scripts/ci/audit_ignore_check.py"
    return 0
  fi
  bash "$ROOT/scripts/ci/deps-audit.sh"
}

run_license() {
  cd "$ROOT/adapter" && uv sync --locked --extra dev
  if ! python3 "$ROOT/scripts/ci/license-check.py"; then
    if [[ "${CI:-}" != "true" ]]; then
      echo "license: skip locally on failure; CI runs on ubuntu-latest"
      return 0
    fi
    return 1
  fi
}

run_cov() {
  cd "$ROOT/adapter" && uv sync --locked --extra dev
  cd "$ROOT/vpl" && uv sync --locked --extra dev
  cd "$ROOT/voice" && uv sync --locked --extra dev --no-install-project
  if [[ "${CZ_COV_SKIP_VOICE:-}" != "1" ]]; then
    (cd "$ROOT/voice" && uv pip install torch --index-url https://download.pytorch.org/whl/cpu)
    (cd "$ROOT/voice" && uv pip install -e ".[dev]")
  fi
  python3 "$ROOT/scripts/ci/coverage-check.py" --package all
}

case "$STEP" in
  ci)
    run_tests
    run_lint
    run_types
    run_shellcheck
    run_secrets
    run_deps_audit
    run_license
    run_cov
    run_guardrails
    ;;
  test) run_tests ;;
  guardrails) run_guardrails ;;
  lint) run_lint ;;
  types) run_types ;;
  fmt)
    cd "$ROOT/adapter" && uv sync --locked --extra dev
    uv run ruff format "$ROOT/adapter" "$ROOT/vpl" "$ROOT/voice" "$ROOT/hermes-plugin" "$ROOT/tests"
    ;;
  cov) run_cov ;;
  *)
    echo "Usage: scripts/ci-local.sh [ci|test|guardrails|lint|types|fmt|cov]" >&2
    exit 2
    ;;
esac

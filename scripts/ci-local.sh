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

run_cov() {
  echo "cov: not configured yet (PR 05)"
}

case "$STEP" in
  ci)
    run_tests
    run_lint
    run_types
    run_shellcheck
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

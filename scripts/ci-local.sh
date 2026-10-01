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
  echo "lint: not configured yet (PR 03)"
}

run_types() {
  echo "types: not configured yet (PR 03)"
}

run_cov() {
  echo "cov: not configured yet (PR 05)"
}

case "$STEP" in
  ci)
    run_tests
    run_guardrails
    ;;
  test) run_tests ;;
  guardrails) run_guardrails ;;
  lint) run_lint ;;
  fmt) echo "fmt: PR 03" ;;
  cov) run_cov ;;
  *)
    echo "Usage: scripts/ci-local.sh [ci|test|guardrails|lint|fmt|cov]" >&2
    exit 2
    ;;
esac

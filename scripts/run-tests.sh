#!/usr/bin/env bash
# Public test runner — never starts, stops, or kills adapter/voice/Hermes processes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"

MODE="full"
SMOKE=0
for arg in "$@"; do
  case "$arg" in
    --fast) MODE="fast" ;;
    --smoke) SMOKE=1 ;;
    -h|--help)
      cat <<EOF
Usage: scripts/run-tests.sh [--fast] [--smoke]

  (default)  vpl + adapter + voice + tests/repo
  --fast     vpl + adapter + tests/repo (skip voice)
  --smoke    after tests, GET /health on a running adapter (read-only)

Env:
  CZ_RUN_TESTS_FAIL_PKG  if set, simulate failure for that package name
                         (adapter|vpl|voice|repo) — for harness tests only.

Does not start, stop, or kill adapter, voice, or Hermes.
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

fail_pkg="${CZ_RUN_TESTS_FAIL_PKG:-}"

run_pkg() {
  local name="$1"
  local dir="$2"
  shift 2
  if [[ "$fail_pkg" == "$name" ]]; then
    echo "==> $name (simulated failure via CZ_RUN_TESTS_FAIL_PKG)" >&2
    return 1
  fi
  echo "==> $name"
  (cd "$dir" && "$@")
}

FAILED=()
STATUS=0

if ! run_pkg vpl "$ROOT/vpl" bash -c 'uv sync --locked --extra dev && uv run pytest -q'; then
  FAILED+=("vpl")
  STATUS=1
fi

if ! run_pkg adapter "$ROOT/adapter" bash -c 'uv sync --locked --extra dev && uv run pytest -q'; then
  FAILED+=("adapter")
  STATUS=1
fi

if [[ "$MODE" != "fast" ]]; then
  if ! run_pkg voice "$ROOT/voice" bash -c 'uv sync --locked --extra dev --no-install-project && uv run pytest -q'; then
    FAILED+=("voice")
    STATUS=1
  fi
fi

if [[ "${CZ_RUN_TESTS_NESTED:-}" != "1" ]]; then
  if ! run_pkg repo "$ROOT/adapter" bash -c 'uv sync --locked --extra dev && uv run pytest -q ../tests/repo'; then
    FAILED+=("repo")
    STATUS=1
  fi
fi

if [[ "$SMOKE" == "1" ]]; then
  echo "==> smoke: GET /health (adapter must already be running)"
  base="${CZ_CONTRACT_BASE_URL:-http://127.0.0.1:8765}"
  if ! curl -sf "${base%/}/health" >/dev/null; then
    echo "smoke: /health failed at $base (start the adapter first)" >&2
    FAILED+=("smoke")
    STATUS=1
  fi
fi

if ((${#FAILED[@]} > 0)); then
  echo "FAILED packages: ${FAILED[*]}" >&2
  exit "$STATUS"
fi

echo "All packages passed."
exit 0

#!/usr/bin/env bash
# Start Construct-Zero adapter on loopback (auto-restarts on crash).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CZ_ROOT="$ROOT"
# shellcheck source=lib/common.sh
source "$ROOT/scripts/lib/common.sh"
cz_load_env

ADAPTER="$ROOT/adapter"
VENV="$ADAPTER/.venv"
STATE_DIR="${CZ_STATE_DIR:-$HOME/.construct-zero}"
PID_FILE="${CZ_PID_FILE:-${HCX_PID_FILE:-$STATE_DIR/adapter.pid}}"
LOG_FILE="${CZ_LOG_FILE:-${HCX_LOG_FILE:-$STATE_DIR/adapter.log}}"

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Adapter venv missing. Run scripts/setup.sh first." >&2
  exit 1
fi

if [[ -z "${CURSOR_API_KEY:-}" ]]; then
  echo "Warning: CURSOR_API_KEY is not set. /health will fail until it is." >&2
fi

if [[ -z "${CZ_CONFIG:-${HCX_CONFIG:-}}" ]]; then
  for candidate in \
    "${CZ_STATE_DIR:+$CZ_STATE_DIR/config.yaml}" \
    "$STATE_DIR/config.yaml" \
    "$HOME/.construct-zero/config.yaml" \
    "$ROOT/config/construct-zero.yaml" \
    "$HOME/.hermesxcursor/config.yaml" \
    "$ROOT/config/hermesxcursor.yaml" \
    "$ROOT/config/construct-zero.yaml.example"; do
    if [[ -n "$candidate" && -f "$candidate" ]]; then
      export CZ_CONFIG="$candidate"
      break
    fi
  done
else
  export CZ_CONFIG="${CZ_CONFIG:-$HCX_CONFIG}"
fi

HOST="${CZ_HOST:-${HCX_HOST:-127.0.0.1}}"
PORT="${CZ_PORT:-${HCX_PORT:-8765}}"
MAX_RESTARTS="${CZ_MAX_RESTARTS:-${HCX_MAX_RESTARTS:-50}}"
RESTART_DELAY="${CZ_RESTART_DELAY:-${HCX_RESTART_DELAY:-2}}"

# Stop existing
if [[ -f "$PID_FILE" ]]; then
  old="$(cat "$PID_FILE" || true)"
  if [[ -n "$old" ]] && kill -0 "$old" 2>/dev/null; then
    echo "Stopping existing adapter pid=$old"
    kill "$old" 2>/dev/null || true
    sleep 0.5
  fi
  rm -f "$PID_FILE"
fi

echo "Starting Construct-Zero on ${HOST}:${PORT} (log: $LOG_FILE)"

(
  restarts=0
  while (( restarts < MAX_RESTARTS )); do
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) starting construct-zero (restart=$restarts)" >>"$LOG_FILE"
    "$VENV/bin/python" -m construct_zero --host "$HOST" --port "$PORT" --config "$CZ_CONFIG" >>"$LOG_FILE" 2>&1 &
    child=$!
    echo "$child" >"$PID_FILE"
    wait "$child" || true
    code=$?
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) construct-zero exited code=$code" >>"$LOG_FILE"
    restarts=$((restarts + 1))
    sleep "$RESTART_DELAY"
  done
  echo "Construct-Zero exceeded max restarts ($MAX_RESTARTS)" >>"$LOG_FILE"
) &

disown || true
sleep 0.8
echo "Construct-Zero supervisor started. PID file: $PID_FILE"
echo "curl -s http://${HOST}:${PORT}/health"

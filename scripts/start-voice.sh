#!/usr/bin/env bash
# Start Construct-Zero voice sidecar on loopback :8767 (auto-restarts on crash).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CZ_ROOT="$ROOT"
# shellcheck source=lib/common.sh
source "$ROOT/scripts/lib/common.sh"
cz_load_env

VENV="${CZ_VOICE_VENV:-$ROOT/.venvs/voice}"
STATE_DIR="${CZ_STATE_DIR:-$HOME/.construct-zero}"
PID_FILE="${CZ_VOICE_PID_FILE:-${HCX_VOICE_PID_FILE:-$STATE_DIR/voice.pid}}"
LOG_FILE="${CZ_VOICE_LOG_FILE:-${HCX_VOICE_LOG_FILE:-$STATE_DIR/voice.log}}"

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Voice venv missing. Run scripts/setup-voice.sh first." >&2
  exit 1
fi

if [[ -z "${CURSOR_API_KEY:-}" ]]; then
  echo "Warning: CURSOR_API_KEY is not set. /turn will fail until adapter+Hermes can chat." >&2
fi

HOST="${CZ_VOICE_HOST:-${HCX_VOICE_HOST:-127.0.0.1}}"
PORT="${CZ_VOICE_PORT:-${HCX_VOICE_PORT:-8767}}"
MAX_RESTARTS="${CZ_VOICE_MAX_RESTARTS:-${HCX_VOICE_MAX_RESTARTS:-50}}"
RESTART_DELAY="${CZ_VOICE_RESTART_DELAY:-${HCX_VOICE_RESTART_DELAY:-2}}"

# Stop existing
if [[ -f "$PID_FILE" ]]; then
  old="$(cat "$PID_FILE" || true)"
  if [[ -n "$old" ]] && kill -0 "$old" 2>/dev/null; then
    echo "Stopping existing voice supervisor pid=$old"
    kill "$old" 2>/dev/null || true
    sleep 0.5
  fi
  rm -f "$PID_FILE"
fi

echo "Starting Construct-Zero voice on ${HOST}:${PORT} (log: $LOG_FILE)"

(
  restarts=0
  while (( restarts < MAX_RESTARTS )); do
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) starting construct-zero-voice (restart=$restarts)" >>"$LOG_FILE"
    "$VENV/bin/python" -m construct_zero_voice --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &
    child=$!
    echo "$child" >"$PID_FILE"
    wait "$child" || true
    code=$?
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) construct-zero-voice exited code=$code" >>"$LOG_FILE"
    restarts=$((restarts + 1))
    sleep "$RESTART_DELAY"
  done
  echo "Construct-Zero voice exceeded max restarts ($MAX_RESTARTS)" >>"$LOG_FILE"
) &
supervisor_pid=$!
echo "$supervisor_pid" >"$PID_FILE"

disown || true
sleep 0.8
echo "Voice supervisor started (pid=$supervisor_pid). PID file: $PID_FILE"
echo "Open http://${HOST}:${PORT}/  (curl -s http://${HOST}:${PORT}/health)"

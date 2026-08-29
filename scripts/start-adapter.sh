#!/usr/bin/env bash
# Start HCX adapter on loopback (auto-restarts on crash).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADAPTER="$ROOT/adapter"
VENV="$ADAPTER/.venv"
PID_FILE="${HCX_PID_FILE:-$HOME/.hermesxcursor/adapter.pid}"
LOG_FILE="${HCX_LOG_FILE:-$HOME/.hermesxcursor/adapter.log}"

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Adapter venv missing. Run scripts/setup.sh first." >&2
  exit 1
fi

if [[ -z "${CURSOR_API_KEY:-}" ]]; then
  echo "Warning: CURSOR_API_KEY is not set. /health will fail until it is." >&2
fi

export HCX_CONFIG="${HCX_CONFIG:-$HOME/.hermesxcursor/config.yaml}"
if [[ ! -f "$HCX_CONFIG" ]]; then
  export HCX_CONFIG="$ROOT/config/hermesxcursor.yaml.example"
fi

HOST="${HCX_HOST:-127.0.0.1}"
PORT="${HCX_PORT:-8765}"
MAX_RESTARTS="${HCX_MAX_RESTARTS:-50}"
RESTART_DELAY="${HCX_RESTART_DELAY:-2}"

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

echo "Starting HCX on ${HOST}:${PORT} (log: $LOG_FILE)"

(
  restarts=0
  while (( restarts < MAX_RESTARTS )); do
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) starting hcx (restart=$restarts)" >>"$LOG_FILE"
    "$VENV/bin/python" -m hcx --host "$HOST" --port "$PORT" --config "$HCX_CONFIG" >>"$LOG_FILE" 2>&1 &
    child=$!
    echo "$child" >"$PID_FILE"
    wait "$child" || true
    code=$?
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) hcx exited code=$code" >>"$LOG_FILE"
    restarts=$((restarts + 1))
    sleep "$RESTART_DELAY"
  done
  echo "HCX exceeded max restarts ($MAX_RESTARTS)" >>"$LOG_FILE"
) &

disown || true
sleep 0.8
echo "HCX supervisor started. PID file: $PID_FILE"
echo "curl -s http://${HOST}:${PORT}/health"

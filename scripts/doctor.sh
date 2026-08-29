#!/usr/bin/env bash
# Health + models + optional chat smoke test for HCX.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${HCX_HOST:-127.0.0.1}"
PORT="${HCX_PORT:-8765}"
BASE="http://${HOST}:${PORT}"
HERMES_DIR="$ROOT/hermes"
LOCK="$ROOT/config/upstream.lock.yaml"

echo "==> GET $BASE/health"
health="$(curl -fsS "$BASE/health" || true)"
if [[ -z "$health" ]]; then
  echo "FAIL: adapter not reachable. Start with scripts/start-adapter.sh" >&2
  exit 1
fi
echo "$health" | python3 -m json.tool 2>/dev/null || echo "$health"

status="$(echo "$health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || true)"
if [[ "$status" != "ok" ]]; then
  echo "FAIL: health status is not ok" >&2
  exit 1
fi

echo "==> GET $BASE/v1/models"
curl -fsS "$BASE/v1/models" | python3 -m json.tool | head -40

if [[ "${HCX_DOCTOR_CHAT:-1}" == "1" ]]; then
  if [[ -z "${CURSOR_API_KEY:-}" ]]; then
    echo "SKIP chat: CURSOR_API_KEY not set"
  else
    echo "==> POST chat.completions (non-stream)"
    curl -fsS "$BASE/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d '{"model":"auto","messages":[{"role":"user","content":"Reply with exactly one word: PONG"}]}' \
      | python3 -m json.tool | head -60
  fi
fi

if [[ -d "$HERMES_DIR/.git" ]] || [[ -f "$HERMES_DIR/.git" ]]; then
  if [[ -f "$LOCK" ]]; then
    HERMES_REF="$(grep -E '^\s*ref:' "$LOCK" | head -1 | sed -E 's/^[[:space:]]*ref:[[:space:]]*//' | tr -d "\"'")"
    if [[ -n "$HERMES_REF" ]]; then
      current="$(git -C "$HERMES_DIR" rev-parse --short HEAD 2>/dev/null || echo "?")"
      pinned="$(git -C "$HERMES_DIR" rev-parse --short "$HERMES_REF" 2>/dev/null || echo "$HERMES_REF")"
      echo "==> Hermes clone: $current (lock pin: $pinned)"
      locked_full="$(git -C "$HERMES_DIR" rev-parse "$HERMES_REF" 2>/dev/null || true)"
      current_full="$(git -C "$HERMES_DIR" rev-parse HEAD 2>/dev/null || true)"
      if [[ -n "$locked_full" && -n "$current_full" && "$locked_full" != "$current_full" ]]; then
        echo "NOTE: hermes/ differs from config/upstream.lock.yaml — run ./scripts/update-hermes.sh"
      fi
    fi
  fi
else
  echo "==> Hermes clone: not present (run ./scripts/setup.sh)"
fi

echo
echo "Doctor OK."
echo "Hermes smoke (if hermes installed):"
echo "  hermes chat -q 'Reply PONG' --provider hcx --model auto"

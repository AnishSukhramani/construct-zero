#!/usr/bin/env bash
# Health + models + optional chat smoke test for Construct-Zero.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CZ_ROOT="$ROOT"
# shellcheck source=lib/common.sh
source "$ROOT/scripts/lib/common.sh"
cz_load_env

HOST="${CZ_HOST:-${HCX_HOST:-127.0.0.1}}"
PORT="${CZ_PORT:-${HCX_PORT:-8765}}"
BASE="http://${HOST}:${PORT}"
HERMES_DIR="$ROOT/hermes"
LOCK="$ROOT/config/upstream.lock.yaml"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_CONFIG="$HERMES_HOME/config.yaml"

failures=0

_doctor_fail() {
  echo "FAIL: $*" >&2
  failures=$((failures + 1))
}

_doctor_auth_header() {
  local key="${CZ_API_KEY:-${HCX_API_KEY:-}}"
  if [[ -n "$key" && "$key" != "unused" ]]; then
    printf '%s\n' "Authorization: Bearer ${key}"
  fi
}

echo "==> CURSOR_API_KEY"
if [[ -z "${CURSOR_API_KEY:-}" ]]; then
  _doctor_fail "CURSOR_API_KEY is not set. Add it to $ROOT/.env or export it."
  echo "    Create a key: https://cursor.com/dashboard → API Keys" >&2
else
  echo "    present (value hidden)"
fi

echo "==> GET $BASE/health"
health=""
status=""
if ! health="$(curl -fsS --connect-timeout 3 "$BASE/health" 2>/dev/null)"; then
  _doctor_fail "adapter not reachable at $BASE/health — run ./construct-zero start"
  health=""
fi
if [[ -n "$health" ]]; then
  echo "$health" | python3 -m json.tool 2>/dev/null || echo "$health"

  status="$(echo "$health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || true)"
  detail="$(echo "$health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('detail',''))" 2>/dev/null || true)"
  key_present="$(echo "$health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cursor_key_present', False))" 2>/dev/null || true)"

  if [[ "$status" != "ok" ]]; then
    _doctor_fail "health status is not ok${detail:+ — $detail}"
  fi
  if [[ "$key_present" == "False" ]]; then
    _doctor_fail "adapter reports cursor_key_present=false — set CURSOR_API_KEY in .env and restart ./construct-zero start"
  fi
fi

echo "==> GET $BASE/v1/models"
auth_hdr="$(_doctor_auth_header)"
if [[ -n "$health" && "$status" == "ok" ]]; then
  if [[ -n "$auth_hdr" ]]; then
    if ! curl -fsS -H "$auth_hdr" "$BASE/v1/models" | python3 -m json.tool | head -40; then
      _doctor_fail "GET /v1/models failed"
    fi
  else
    if ! curl -fsS "$BASE/v1/models" | python3 -m json.tool | head -40; then
      _doctor_fail "GET /v1/models failed"
    fi
  fi
else
  echo "    skipped (adapter health not ok)"
fi

if [[ "${CZ_DOCTOR_CHAT:-${HCX_DOCTOR_CHAT:-1}}" == "1" ]]; then
  if [[ -z "${CURSOR_API_KEY:-}" ]]; then
    echo "==> POST chat.completions — skipped (no CURSOR_API_KEY)"
  elif [[ -n "$health" && "$status" == "ok" ]]; then
    echo "==> POST chat.completions (non-stream)"
    chat_ok=0
    if [[ -n "$auth_hdr" ]]; then
      if curl -fsS -H "Content-Type: application/json" -H "$auth_hdr" \
        "$BASE/v1/chat/completions" \
        -d '{"model":"auto","messages":[{"role":"user","content":"Reply with exactly one word: PONG"}]}' \
        | python3 -m json.tool | head -60; then
        chat_ok=1
      fi
    else
      if curl -fsS -H "Content-Type: application/json" \
        "$BASE/v1/chat/completions" \
        -d '{"model":"auto","messages":[{"role":"user","content":"Reply with exactly one word: PONG"}]}' \
        | python3 -m json.tool | head -60; then
        chat_ok=1
      fi
    fi
    if [[ "$chat_ok" != "1" ]]; then
      _doctor_fail "chat.completions smoke test failed"
    fi
  fi
fi

echo "==> Hermes upstream clone"
if [[ -d "$HERMES_DIR/.git" ]] || [[ -f "$HERMES_DIR/.git" ]]; then
  if [[ -f "$LOCK" ]]; then
    HERMES_REF="$(grep -E '^\s*ref:' "$LOCK" | head -1 | sed -E 's/^[[:space:]]*ref:[[:space:]]*//' | tr -d "\"'")"
    if [[ -n "$HERMES_REF" ]]; then
      current="$(git -C "$HERMES_DIR" rev-parse --short HEAD 2>/dev/null || echo "?")"
      pinned="$(git -C "$HERMES_DIR" rev-parse --short "$HERMES_REF" 2>/dev/null || echo "$HERMES_REF")"
      echo "    clone at $current (lock pin: $pinned)"
      locked_full="$(git -C "$HERMES_DIR" rev-parse "$HERMES_REF" 2>/dev/null || true)"
      current_full="$(git -C "$HERMES_DIR" rev-parse HEAD 2>/dev/null || true)"
      if [[ -n "$locked_full" && -n "$current_full" && "$locked_full" != "$current_full" ]]; then
        _doctor_fail "hermes/ ($current) differs from config/upstream.lock.yaml ($pinned) — run ./scripts/update-hermes.sh"
      fi
    fi
  else
    _doctor_fail "missing $LOCK — cannot verify Hermes pin"
  fi
else
  echo "    not present (run ./scripts/setup.sh or ./construct-zero init)"
fi

echo "==> Hermes config ($HERMES_CONFIG)"
if [[ ! -f "$HERMES_CONFIG" ]]; then
  _doctor_fail "Hermes config missing at $HERMES_CONFIG — run ./construct-zero init or merge config/hermes.config.snippet.yaml"
else
  if ! grep -qE 'provider:[[:space:]]*construct-zero' "$HERMES_CONFIG" 2>/dev/null; then
    _doctor_fail "Hermes config at $HERMES_CONFIG should set model.provider: construct-zero"
  fi
  expected_base="http://${HOST}:${PORT}/v1"
  if ! grep -qF "$expected_base" "$HERMES_CONFIG" 2>/dev/null; then
    _doctor_fail "Hermes config base_url should be $expected_base (matches CZ_PORT=$PORT)"
  fi
  if [[ "$failures" -eq 0 ]] || grep -qE 'provider:[[:space:]]*construct-zero' "$HERMES_CONFIG" 2>/dev/null; then
    echo "    provider construct-zero, base_url matches adapter port"
  fi
fi

echo
if (( failures > 0 )); then
  echo "Doctor FAILED ($failures check(s)). Fix the items above and re-run ./construct-zero doctor" >&2
  exit 1
fi

echo "Doctor OK."
echo "Hermes smoke: ./construct-zero chat"

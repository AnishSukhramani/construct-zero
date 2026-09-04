#!/usr/bin/env bash
# Folder-local isolation for curl/cwd installs.
# Source after scripts/lib/common.sh when possible.

# shellcheck disable=SC2034
CZ_LIB_ISOLATE_LOADED=1

# Print first free TCP port on 127.0.0.1 at or above start (optional skip).
cz_find_free_port() {
  local start="${1:?start port required}"
  local skip="${2:-}"
  python3 -c '
import socket, sys
start = int(sys.argv[1])
skip = sys.argv[2]
for p in range(start, start + 200):
    if skip and str(p) == skip:
        continue
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", p))
        print(p)
        sys.exit(0)
    except OSError:
        pass
    finally:
        s.close()
sys.exit(1)
' "$start" "$skip"
}

_cz_isolate_write() {
  local key="${1:?}"
  local val="${2:-}"
  if type cz_env_set >/dev/null 2>&1; then
    cz_env_set "$key" "$val"
    return 0
  fi
  local env_file="${CZ_ROOT:-.}/.env"
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$env_file" ]]; then
    grep -v "^${key}=" "$env_file" >"$tmp" || true
  fi
  printf '%s=%s\n' "$key" "$val" >>"$tmp"
  mv "$tmp" "$env_file"
  chmod 600 "$env_file" 2>/dev/null || true
}

# Write key only if it is not already present in .env.
_cz_isolate_write_if_unset() {
  local key="${1:?}"
  local val="${2:-}"
  local env_file="${CZ_ROOT:-.}/.env"
  if [[ -f "$env_file" ]] && grep -q "^${key}=" "$env_file" 2>/dev/null; then
    return 0
  fi
  _cz_isolate_write "$key" "$val"
}

# Apply folder-local Hermes + adapter state under $root (cwd install).
# Does not clobber existing CURSOR_API_KEY or isolation keys.
cz_apply_isolation() {
  local root="${1:-}"
  local state hermes_home port voice_port
  if [[ -z "$root" ]]; then
    root="$(pwd)"
  fi
  root="$(cd "$root" && pwd)"
  export CZ_ROOT="$root"

  if type cz_load_env >/dev/null 2>&1; then
    cz_load_env
  fi

  state="${CZ_STATE_DIR:-$root/.construct-zero}"
  hermes_home="${HERMES_HOME:-$root/.hermes}"
  mkdir -p "$state" "$hermes_home"

  if [[ -z "${CZ_PORT:-}" ]]; then
    port="$(cz_find_free_port 8765)"
  else
    port="$CZ_PORT"
  fi
  if [[ -z "${CZ_VOICE_PORT:-}" ]]; then
    voice_port="$(cz_find_free_port 8767 "$port")"
  else
    voice_port="$CZ_VOICE_PORT"
  fi

  _cz_isolate_write_if_unset HERMES_HOME "$hermes_home"
  _cz_isolate_write_if_unset CZ_STATE_DIR "$state"
  _cz_isolate_write_if_unset CZ_HOST "${CZ_HOST:-127.0.0.1}"
  _cz_isolate_write_if_unset CZ_PORT "$port"
  _cz_isolate_write_if_unset CZ_VOICE_HOST "${CZ_VOICE_HOST:-127.0.0.1}"
  _cz_isolate_write_if_unset CZ_VOICE_PORT "$voice_port"
  _cz_isolate_write_if_unset CZ_CONFIG "${CZ_CONFIG:-$state/config.yaml}"
  _cz_isolate_write_if_unset CZ_PID_FILE "${CZ_PID_FILE:-$state/adapter.pid}"
  _cz_isolate_write_if_unset CZ_LOG_FILE "${CZ_LOG_FILE:-$state/adapter.log}"
  _cz_isolate_write_if_unset CZ_VOICE_PID_FILE "${CZ_VOICE_PID_FILE:-$state/voice.pid}"
  _cz_isolate_write_if_unset CZ_VOICE_LOG_FILE "${CZ_VOICE_LOG_FILE:-$state/voice.log}"

  if type cz_load_env >/dev/null 2>&1; then
    cz_load_env
  fi

  export HERMES_HOME="${HERMES_HOME:-$hermes_home}"
  export CZ_STATE_DIR="${CZ_STATE_DIR:-$state}"
  export CZ_HOST="${CZ_HOST:-127.0.0.1}"
  export CZ_PORT="${CZ_PORT:-$port}"
  export CZ_VOICE_HOST="${CZ_VOICE_HOST:-127.0.0.1}"
  export CZ_VOICE_PORT="${CZ_VOICE_PORT:-$voice_port}"
  export CZ_CONFIG="${CZ_CONFIG:-$CZ_STATE_DIR/config.yaml}"
  export CZ_PID_FILE="${CZ_PID_FILE:-$CZ_STATE_DIR/adapter.pid}"
  export CZ_LOG_FILE="${CZ_LOG_FILE:-$CZ_STATE_DIR/adapter.log}"
  export CZ_VOICE_PID_FILE="${CZ_VOICE_PID_FILE:-$CZ_STATE_DIR/voice.pid}"
  export CZ_VOICE_LOG_FILE="${CZ_VOICE_LOG_FILE:-$CZ_STATE_DIR/voice.log}"
}

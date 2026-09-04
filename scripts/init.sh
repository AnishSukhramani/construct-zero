#!/usr/bin/env bash
# Interactive one-step onboarding for Construct-Zero.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CZ_ROOT="$ROOT"
# shellcheck source=lib/common.sh
source "$ROOT/scripts/lib/common.sh"

cd "$ROOT"

AUTO=0
DO_VOICE=0
DO_START=1
DO_HERMES=1
DO_HERMES_CONFIG=1
CURSOR_KEY=""
SKIP_HERMES_EXPLICIT=0

usage() {
  cat <<EOF
Usage: $0 [options]

Interactive onboarding: Hermes clone, adapter venv, plugin, optional voice, start + doctor.

Also available as: ./construct-zero init

Options:
  --auto            Non-interactive; use defaults and env vars
  --voice           Enable voice setup (default off unless CZ_INIT_VOICE=1)
  --no-voice        Skip voice setup
  --no-start        Do not start services or run doctor at end
  --skip-hermes     Skip Hermes clone and Hermes CLI venv
  --cursor-key KEY  Set CURSOR_API_KEY (also written to .env)
  --no-uv           Do not offer/install uv
  -h, --help        Show this help

Env (with --auto):
  CZ_INIT_VOICE=1       Enable voice setup
  CZ_INIT_START=0       Skip start + doctor
  CZ_INIT_HERMES=0      Skip Hermes clone
  CZ_INIT_HERMES_CONFIG=0  Skip Hermes config for this install
  CZ_INIT_UV=0          Skip uv install
  CURSOR_API_KEY         Cursor API key

Manual path still works: ./scripts/setup.sh, ./scripts/start-adapter.sh, etc.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --auto) AUTO=1; export CZ_AUTO=1; shift ;;
    --voice) DO_VOICE=1; shift ;;
    --no-voice) DO_VOICE=0; shift ;;
    --no-start) DO_START=0; shift ;;
    --skip-hermes) DO_HERMES=0; SKIP_HERMES_EXPLICIT=1; shift ;;
    --no-uv) export CZ_INIT_UV=0; shift ;;
    --cursor-key)
      CURSOR_KEY="${2:?--cursor-key requires a value}"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cz_preflight

cz_load_env

# .env bootstrap
if [[ ! -f "$ROOT/.env" && -f "$ROOT/.env.example" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  chmod 600 "$ROOT/.env" 2>/dev/null || true
  cz_info "Created .env from .env.example"
fi

if [[ -n "$CURSOR_KEY" ]]; then
  export CURSOR_API_KEY="$CURSOR_KEY"
  cz_env_set CURSOR_API_KEY "$CURSOR_KEY"
fi

if [[ "$AUTO" != "1" ]]; then
  if [[ -n "${CURSOR_API_KEY:-}" ]]; then
    key_input="$(cz_ask_secret "Cursor API key" "keep")"
  else
    key_input="$(cz_ask_secret "Cursor API key" "skip")"
  fi
  if [[ -n "$key_input" ]]; then
    export CURSOR_API_KEY="$key_input"
    cz_env_set CURSOR_API_KEY "$key_input"
  fi
fi

if [[ -z "${CZ_API_KEY:-${HCX_API_KEY:-}}" ]]; then
  export CZ_API_KEY=unused
  if [[ -f "$ROOT/.env" ]] && ! grep -qE '^(CZ_API_KEY|HCX_API_KEY)=' "$ROOT/.env" 2>/dev/null; then
    cz_env_set CZ_API_KEY unused
  fi
fi

# Resolve choices (--auto uses defaults + env overrides)
if [[ "$AUTO" == "1" ]]; then
  [[ "${CZ_INIT_VOICE:-${HCX_INIT_VOICE:-0}}" == "1" ]] && DO_VOICE=1
  [[ "${CZ_INIT_START:-${HCX_INIT_START:-1}}" == "0" ]] && DO_START=0
  [[ "${CZ_INIT_HERMES:-${HCX_INIT_HERMES:-1}}" == "0" ]] && DO_HERMES=0
  [[ "${CZ_INIT_HERMES_CONFIG:-${HCX_INIT_HERMES_CONFIG:-1}}" == "0" ]] && DO_HERMES_CONFIG=0
else
  echo
  cz_info "Construct-Zero — setup"
  echo

  if [[ "$SKIP_HERMES_EXPLICIT" != "1" ]]; then
    if [[ "$(cz_ask_yn "Clone Hermes locally?" "yes")" == "yes" ]]; then
      DO_HERMES=1
    else
      DO_HERMES=0
    fi
  fi

  if [[ "$(cz_ask_yn "Set up voice sidecar?" "no")" == "yes" ]]; then
    DO_VOICE=1
  else
    DO_VOICE=0
  fi

  if [[ "$(cz_ask_yn "Write Hermes config for this install (${HERMES_HOME:-$HOME/.hermes}/config.yaml) if missing?" "yes")" == "yes" ]]; then
    DO_HERMES_CONFIG=1
  else
    DO_HERMES_CONFIG=0
  fi

  if [[ "$(cz_ask_yn "Start adapter and run doctor when done?" "yes")" == "yes" ]]; then
    DO_START=1
  else
    DO_START=0
  fi
fi

cz_ensure_uv

# Core setup via existing script
setup_args=()
if [[ "$DO_HERMES" != "1" ]]; then
  setup_args+=(--skip-hermes)
fi

cz_spin "Running core setup..." "$ROOT/scripts/setup.sh" ${setup_args[@]+"${setup_args[@]}"}

if [[ "$DO_VOICE" == "1" ]]; then
  cz_spin "Setting up voice..." "$ROOT/scripts/setup-voice.sh"
fi

if [[ "$DO_HERMES_CONFIG" == "1" ]]; then
  cz_write_hermes_config
fi

if [[ "$DO_START" == "1" ]]; then
  start_args=()
  [[ "$DO_VOICE" == "1" ]] && start_args+=(--voice)
  cz_spin "Starting services..." "$ROOT/scripts/start.sh" ${start_args[@]+"${start_args[@]}"}
  sleep 1
  cz_spin "Running doctor..." "$ROOT/scripts/doctor.sh"
fi

echo
cz_info "Init complete."
if [[ -x "$ROOT/construct-zero" ]]; then
  "$ROOT/construct-zero" help
else
  echo "Next: ./construct-zero help" >&2
fi

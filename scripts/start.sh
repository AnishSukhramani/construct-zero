#!/usr/bin/env bash
# Start Construct-Zero adapter (and optionally voice sidecar).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CZ_ROOT="$ROOT"
# shellcheck source=lib/common.sh
source "$ROOT/scripts/lib/common.sh"

DO_VOICE=0

usage() {
  cat <<EOF
Usage: $0 [--voice]

  Start Construct-Zero adapter on loopback (default).
  --voice   Also start voice sidecar on :8767

Existing scripts still work: start-adapter.sh, start-voice.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --voice) DO_VOICE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

cz_load_env

"$ROOT/scripts/start-adapter.sh"

if [[ "$DO_VOICE" == "1" ]]; then
  "$ROOT/scripts/start-voice.sh"
fi

_host="${CZ_HOST:-${HCX_HOST:-127.0.0.1}}"
_port="${CZ_PORT:-${HCX_PORT:-8765}}"
_voice_host="${CZ_VOICE_HOST:-${HCX_VOICE_HOST:-127.0.0.1}}"
_voice_port="${CZ_VOICE_PORT:-${HCX_VOICE_PORT:-8767}}"

echo
echo "Adapter is running on ${_host}:${_port}"
if [[ "$DO_VOICE" == "1" ]]; then
  echo "Voice UI: http://${_voice_host}:${_voice_port}/"
fi
echo
echo "Next — talk to Hermes:"
echo "  ./construct-zero chat"
echo
echo 'hermes is not on PATH; use the command above.'


#!/usr/bin/env bash
# Create voice sidecar venv and install deps (construct-zero-vpl + faster-whisper + Kokoro).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CZ_ROOT="$ROOT"
# shellcheck source=lib/common.sh
source "$ROOT/scripts/lib/common.sh"
cz_load_env

VPL="$ROOT/vpl"
VOICE="$ROOT/voice"
VENV="$ROOT/.venvs/voice"

mkdir -p "$ROOT/.venvs"

echo "==> Creating voice venv at $VENV"
if [[ -d "$VENV" ]] && [[ ! -x "$VENV/bin/python" ]]; then
  echo "    Removing broken voice venv (missing bin/python)"
  rm -rf "$VENV"
fi
if [[ ! -d "$VENV" ]]; then
  cz_venv_create "$VENV"
fi
echo "==> Installing construct-zero-vpl (editable)"
cz_pip_editable "$VENV/bin/python" "${VPL}[dev]"
echo "==> Installing construct-zero-voice (editable)"
cz_pip_editable "$VENV/bin/python" "${VOICE}[dev]"

echo "==> Checking ffmpeg (required for many MediaRecorder formats)"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "    ffmpeg: $(command -v ffmpeg)"
else
  echo "    WARNING: ffmpeg not found. Install it (e.g. brew install ffmpeg) for robust STT."
fi

cat <<EOF

Voice setup complete.

1. Ensure Construct-Zero adapter is running:  ./scripts/start-adapter.sh
2. Export CURSOR_API_KEY (and CZ_API_KEY=unused if Hermes requires it)
3. Start voice:  ./scripts/start-voice.sh
4. Open:         http://127.0.0.1:8767/

Layered delivery (VPL): long Hermes replies are spoken in orient/map/deepen layers.
Full reply stays on screen; navigation turns skip Hermes. See vpl/README.md.

First STT/TTS call downloads models (Whisper + Kokoro/HF). Disk + network needed.
Optional: CZ_VOICE_PRELOAD=1 to load models at startup.
Optional: CZ_VPL_ENABLED=0 to disable layered delivery.
Optional: brew/apt install espeak-ng if Kokoro phonemizer requires it.

EOF

#!/usr/bin/env bash
# Create voice sidecar venv and install deps (hcx-vpl + faster-whisper + Kokoro).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VPL="$ROOT/vpl"
VOICE="$ROOT/voice"
VENV="$ROOT/.venvs/voice"

mkdir -p "$ROOT/.venvs"

echo "==> Creating voice venv at $VENV"
if command -v uv >/dev/null 2>&1; then
  if [[ ! -d "$VENV" ]]; then
    uv venv "$VENV" --python 3.12 || uv venv "$VENV" --python 3.11 || uv venv "$VENV"
  fi
  echo "==> Installing hcx-vpl (editable)"
  uv pip install -e "${VPL}[dev]" --python "$VENV/bin/python"
  echo "==> Installing hcx-voice (editable)"
  uv pip install -e "${VOICE}[dev]" --python "$VENV/bin/python"
else
  if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
  fi
  "$VENV/bin/pip" install -U pip
  "$VENV/bin/pip" install -e "${VPL}[dev]"
  "$VENV/bin/pip" install -e "${VOICE}[dev]"
fi

echo "==> Checking ffmpeg (required for many MediaRecorder formats)"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "    ffmpeg: $(command -v ffmpeg)"
else
  echo "    WARNING: ffmpeg not found. Install it (e.g. brew install ffmpeg) for robust STT."
fi

cat <<EOF

Voice setup complete.

1. Ensure HCX adapter is running:  ./scripts/start-adapter.sh
2. Export CURSOR_API_KEY (and HCX_API_KEY=unused if Hermes requires it)
3. Start voice:  ./scripts/start-voice.sh
4. Open:         http://127.0.0.1:8767/

Layered delivery (VPL): long Hermes replies are spoken in orient/map/deepen layers.
Full reply stays on screen; navigation turns skip Hermes. See vpl/README.md.

First STT/TTS call downloads models (Whisper + Kokoro/HF). Disk + network needed.
Optional: HCX_VOICE_PRELOAD=1 to load models at startup.
Optional: HCX_VPL_ENABLED=0 to disable layered delivery.
Optional: brew/apt install espeak-ng if Kokoro phonemizer requires it.

EOF

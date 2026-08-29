#!/usr/bin/env bash
# Bootstrap HCX adapter + upstream Hermes clone + plugin wiring.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

"$ROOT/scripts/ensure-hermes.sh"

echo "==> Creating adapter venv (Python 3.12 preferred)"
cd "$ROOT/adapter"
if [[ ! -d .venv ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv .venv --python 3.12 || uv venv .venv --python 3.11 || uv venv .venv
    uv pip install -e ".[dev]" --python .venv/bin/python
  else
    python3 -m venv .venv
    .venv/bin/pip install -U pip
    .venv/bin/pip install -e ".[dev]"
  fi
else
  if command -v uv >/dev/null 2>&1; then
    uv pip install -e ".[dev]" --python .venv/bin/python
  else
    .venv/bin/pip install -e ".[dev]"
  fi
fi

echo "==> Hermes CLI venv (for chat + voice bridge)"
HERMES_VENV="$ROOT/.venvs/hermes"
if [[ -d "$ROOT/hermes/.git" ]] || [[ -f "$ROOT/hermes/.git" ]]; then
  if [[ ! -x "$HERMES_VENV/bin/hermes" ]]; then
    mkdir -p "$ROOT/.venvs"
    if command -v uv >/dev/null 2>&1; then
      uv venv "$HERMES_VENV" --python 3.12 || uv venv "$HERMES_VENV" --python 3.11 || uv venv "$HERMES_VENV"
      uv pip install -e "./hermes[all]" --python "$HERMES_VENV/bin/python"
    else
      python3 -m venv "$HERMES_VENV"
      "$HERMES_VENV/bin/pip" install -U pip
      "$HERMES_VENV/bin/pip" install -e "./hermes[all]"
    fi
  else
    if command -v uv >/dev/null 2>&1; then
      uv pip install -e "./hermes[all]" --python "$HERMES_VENV/bin/python"
    else
      "$HERMES_VENV/bin/pip" install -e "./hermes[all]"
    fi
  fi
else
  echo "    Skipped (no Hermes clone in hermes/)"
fi

echo "==> Config"
mkdir -p "$HOME/.hermesxcursor"
if [[ ! -f "$HOME/.hermesxcursor/config.yaml" ]]; then
  cp "$ROOT/config/hermesxcursor.yaml.example" "$HOME/.hermesxcursor/config.yaml"
  echo "Wrote ~/.hermesxcursor/config.yaml"
fi
if [[ ! -f "$ROOT/config/hermesxcursor.yaml" ]]; then
  cp "$ROOT/config/hermesxcursor.yaml.example" "$ROOT/config/hermesxcursor.yaml"
fi

echo "==> Install Hermes HCX provider plugin"
"$ROOT/scripts/install-hermes-plugin.sh"

cat <<EOF

Setup complete.

1. Copy .env.example → .env or export CURSOR_API_KEY (https://cursor.com/dashboard/api)
2. Start adapter:  $ROOT/scripts/start-adapter.sh
3. Doctor:         $ROOT/scripts/doctor.sh
4. Hermes chat:    $ROOT/.venvs/hermes/bin/hermes chat --provider hcx --model auto

Hermes upstream lives in hermes/ (gitignored). Pin: config/upstream.lock.yaml

EOF

#!/usr/bin/env bash
# Bootstrap Construct-Zero adapter + upstream Hermes clone + plugin wiring.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CZ_ROOT="$ROOT"
# shellcheck source=lib/common.sh
source "$ROOT/scripts/lib/common.sh"
cz_load_env
cd "$ROOT"

SKIP_HERMES="${CZ_SKIP_HERMES:-${HCX_SKIP_HERMES:-0}}"
SKIP_PLUGIN="${CZ_SKIP_PLUGIN:-${HCX_SKIP_PLUGIN:-0}}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-hermes) SKIP_HERMES=1; shift ;;
    --skip-plugin) SKIP_PLUGIN=1; shift ;;
    -h|--help)
      cat <<EOF
Usage: $0 [--skip-hermes] [--skip-plugin]

  --skip-hermes   Skip Hermes clone and Hermes CLI venv
  --skip-plugin   Skip install-hermes-plugin.sh

Env: CZ_SKIP_HERMES=1, CZ_SKIP_PLUGIN=1
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1 (try --help)" >&2
      exit 1
      ;;
  esac
done

if [[ "$SKIP_HERMES" != "1" ]]; then
  "$ROOT/scripts/ensure-hermes.sh"
fi

echo "==> Creating adapter venv (Python 3.12 preferred)"
cd "$ROOT/adapter"
if [[ -d .venv ]] && [[ ! -x .venv/bin/python ]]; then
  echo "    Removing broken adapter .venv (missing bin/python)"
  rm -rf .venv
fi
if [[ -d .venv ]] && [[ ! -x .venv/bin/pip ]] && [[ ! -x .venv/bin/pip3 ]]; then
  if ! cz_uv_bin >/dev/null; then
    echo "    Removing adapter .venv without pip"
    rm -rf .venv
  fi
fi
if [[ ! -d .venv ]]; then
  cz_venv_create .venv
fi
cz_pip_editable .venv/bin/python ".[dev,cli]"
cd "$ROOT"

echo "==> Hermes CLI venv (for chat + voice bridge)"
HERMES_VENV="$ROOT/.venvs/hermes"
if [[ "$SKIP_HERMES" == "1" ]]; then
  echo "    Skipped (--skip-hermes)"
elif [[ -d "$ROOT/hermes/.git" ]] || [[ -f "$ROOT/hermes/.git" ]]; then
  if [[ -d "$HERMES_VENV" ]] && [[ ! -x "$HERMES_VENV/bin/python" ]]; then
    echo "    Removing broken Hermes venv (missing bin/python)"
    rm -rf "$HERMES_VENV"
  fi
  if [[ ! -x "$HERMES_VENV/bin/hermes" ]]; then
    mkdir -p "$ROOT/.venvs"
    cz_venv_create "$HERMES_VENV"
    cz_pip_editable "$HERMES_VENV/bin/python" "$ROOT/hermes[all]"
  else
    cz_pip_editable "$HERMES_VENV/bin/python" "$ROOT/hermes[all]"
  fi
else
  echo "    Skipped (no Hermes clone in hermes/)"
fi

echo "==> Config"
STATE_DIR="${CZ_STATE_DIR:-$HOME/.construct-zero}"
mkdir -p "$STATE_DIR"
if [[ ! -f "$STATE_DIR/config.yaml" ]]; then
  if [[ -f "$HOME/.hermesxcursor/config.yaml" && "$STATE_DIR" == "$HOME/.construct-zero" ]]; then
    cp "$HOME/.hermesxcursor/config.yaml" "$STATE_DIR/config.yaml"
    echo "Copied ~/.hermesxcursor/config.yaml → $STATE_DIR/config.yaml"
  else
    cp "$ROOT/config/construct-zero.yaml.example" "$STATE_DIR/config.yaml"
    echo "Wrote $STATE_DIR/config.yaml"
  fi
fi
if [[ ! -f "$ROOT/config/construct-zero.yaml" ]]; then
  if [[ -f "$ROOT/config/hermesxcursor.yaml" ]]; then
    cp "$ROOT/config/hermesxcursor.yaml" "$ROOT/config/construct-zero.yaml"
    echo "Copied config/hermesxcursor.yaml → config/construct-zero.yaml"
  else
    cp "$ROOT/config/construct-zero.yaml.example" "$ROOT/config/construct-zero.yaml"
  fi
fi
if [[ -z "${CZ_STATE_DIR:-}" && -d "$HOME/.hermesxcursor" ]]; then
  echo "NOTE: ~/.hermesxcursor still exists. New default is ~/.construct-zero (old paths remain as fallback)."
fi

if [[ "$SKIP_PLUGIN" != "1" ]]; then
  echo "==> Install Hermes Construct-Zero provider plugin"
  "$ROOT/scripts/install-hermes-plugin.sh"
else
  echo "==> Install Hermes Construct-Zero provider plugin (skipped --skip-plugin)"
fi

cat <<EOF

Setup complete.

  ./construct-zero start    # adapter (add --voice for the voice page)
  ./construct-zero chat     # talk to Hermes (not a global "hermes" command)
  ./construct-zero help     # command menu

EOF

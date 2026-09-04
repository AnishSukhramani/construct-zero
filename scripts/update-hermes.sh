#!/usr/bin/env bash
# Update upstream Hermes clone (or pin), reinstall plugin, optional doctor.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PIN="${1:-}"

"$ROOT/scripts/ensure-hermes.sh"

echo "==> Updating Hermes clone"
cd "$ROOT/hermes"
git fetch --tags origin
if [[ -n "$PIN" ]]; then
  git checkout "$PIN"
else
  git checkout main 2>/dev/null || git checkout master
  git pull --ff-only origin HEAD || true
fi
echo "Hermes at $(git rev-parse --short HEAD)"
cd "$ROOT"

if [[ -x "$ROOT/.venvs/hermes/bin/pip" ]] || [[ -x "$ROOT/.venvs/hermes/bin/python" ]]; then
  echo "==> Refresh Hermes venv"
  if command -v uv >/dev/null 2>&1; then
    uv pip install -e "./hermes[all]" --python "$ROOT/.venvs/hermes/bin/python"
  else
    "$ROOT/.venvs/hermes/bin/pip" install -e "./hermes[all]"
  fi
fi

"$ROOT/scripts/install-hermes-plugin.sh"

HOST="${CZ_HOST:-${HCX_HOST:-127.0.0.1}}"
PORT="${CZ_PORT:-${HCX_PORT:-8765}}"
if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
  "$ROOT/scripts/doctor.sh" || true
else
  echo "Adapter not running; skip doctor. Start with scripts/start-adapter.sh"
fi

echo "Done. To pin this version for new clones, update config/upstream.lock.yaml ref."

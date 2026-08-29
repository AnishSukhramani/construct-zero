#!/usr/bin/env bash
# Clone or verify upstream Hermes in ./hermes (not vendored in this repo).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_DIR="$ROOT/hermes"
LOCK="$ROOT/config/upstream.lock.yaml"

if [[ ! -f "$LOCK" ]]; then
  echo "Missing $LOCK" >&2
  exit 1
fi

HERMES_REPO="$(grep -E '^\s*repo:' "$LOCK" | head -1 | sed -E 's/^[[:space:]]*repo:[[:space:]]*//' | tr -d "\"'")"
HERMES_REF="$(grep -E '^\s*ref:' "$LOCK" | head -1 | sed -E 's/^[[:space:]]*ref:[[:space:]]*//' | tr -d "\"'")"

if [[ -z "$HERMES_REPO" || -z "$HERMES_REF" ]]; then
  echo "Could not parse hermes repo/ref from $LOCK" >&2
  exit 1
fi

_is_hermes_clone() {
  [[ -d "$HERMES_DIR/.git" ]] || [[ -f "$HERMES_DIR/.git" ]]
}

if _is_hermes_clone; then
  short="$(git -C "$HERMES_DIR" rev-parse --short HEAD 2>/dev/null || echo "?")"
  echo "Hermes clone present at $short ($HERMES_DIR)"
  locked="$(git -C "$HERMES_DIR" rev-parse "$HERMES_REF" 2>/dev/null || true)"
  current="$(git -C "$HERMES_DIR" rev-parse HEAD 2>/dev/null || true)"
  if [[ -n "$locked" && -n "$current" && "$locked" != "$current" ]]; then
    echo "NOTE: hermes/ is at $(git -C "$HERMES_DIR" rev-parse --short HEAD) but lock pin is $(git -C "$HERMES_DIR" rev-parse --short "$HERMES_REF" 2>/dev/null || echo "$HERMES_REF") — run ./scripts/update-hermes.sh"
  fi
  exit 0
fi

echo "==> Cloning Hermes ($HERMES_REF)"
if [[ ! -d "$HERMES_DIR" ]]; then
  mkdir -p "$HERMES_DIR"
fi

if [[ -n "$(ls -A "$HERMES_DIR" 2>/dev/null || true)" ]]; then
  echo "hermes/ is not empty and not a git clone. Move contents aside, then re-run setup." >&2
  exit 1
fi

git clone "$HERMES_REPO" "$HERMES_DIR"
git -C "$HERMES_DIR" checkout "$HERMES_REF"
echo "Hermes at $(git -C "$HERMES_DIR" rev-parse --short HEAD)"

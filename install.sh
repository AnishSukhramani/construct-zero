#!/usr/bin/env bash
# Bootstrap Construct-Zero into the current directory, then run interactive init.
# Landing page:
#   mkdir my-agent && cd my-agent
#   curl -fsSL https://raw.githubusercontent.com/AnishSukhramani/construct-zero/main/install.sh | bash
set -euo pipefail

CZ_INSTALL_REPO="${CZ_INSTALL_REPO:-https://github.com/AnishSukhramani/construct-zero.git}"
INSTALL_DIR="$(pwd)"

usage() {
  cat <<EOF
Usage: install.sh [init-args...]

Clone Construct-Zero into the current directory (must be empty), write
folder-local config, and run ./scripts/init.sh.

This directory becomes one isolated install. Repeat in another blank folder
for a second stack (Hermes home, adapter state, and ports stay local).

Extra args are passed to init.sh (e.g. --auto --no-start).
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

for cmd in git curl python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
done

_non_dot_entries() {
  ls -A "$INSTALL_DIR" 2>/dev/null | grep -v '^\.DS_Store$' || true
}

if [[ -f "$INSTALL_DIR/scripts/init.sh" ]]; then
  echo "==> Existing Construct-Zero checkout in $INSTALL_DIR — skipping clone"
else
  leftovers="$(_non_dot_entries)"
  if [[ -n "$leftovers" ]]; then
    echo "This folder is not empty. Create a blank directory, cd into it, then re-run." >&2
    echo "  mkdir my-agent && cd my-agent" >&2
    echo "  curl -fsSL https://raw.githubusercontent.com/AnishSukhramani/construct-zero/main/install.sh | bash" >&2
    exit 1
  fi
  rm -f "$INSTALL_DIR/.DS_Store"
  echo "==> Cloning Construct-Zero into $INSTALL_DIR"
  git clone --depth 1 "$CZ_INSTALL_REPO" "$INSTALL_DIR"
fi

if [[ ! -f "$INSTALL_DIR/scripts/init.sh" ]]; then
  echo "Clone succeeded but scripts/init.sh is missing." >&2
  exit 1
fi

export CZ_ROOT="$INSTALL_DIR"
# shellcheck source=scripts/lib/common.sh
source "$INSTALL_DIR/scripts/lib/common.sh"
# shellcheck source=scripts/lib/isolate.sh
source "$INSTALL_DIR/scripts/lib/isolate.sh"

echo "==> Isolating this install (Hermes + adapter state stay in this folder)"
cz_apply_isolation "$INSTALL_DIR"

echo "==> Starting onboarding"
exec "$INSTALL_DIR/scripts/init.sh" "$@"

#!/usr/bin/env bash
# Symlink Construct-Zero Hermes provider plugin into ~/.hermes/plugins/model-providers/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/hermes-plugin/model-providers/construct-zero"
DEST_DIR="${HERMES_HOME:-$HOME/.hermes}/plugins/model-providers"
DEST="$DEST_DIR/construct-zero"
OLD_DEST="$DEST_DIR/hcx"

mkdir -p "$DEST_DIR"
if [[ -L "$DEST" || -e "$DEST" ]]; then
  rm -rf "$DEST"
fi
ln -s "$SRC" "$DEST"
echo "Linked $DEST -> $SRC"

if [[ -L "$OLD_DEST" || -e "$OLD_DEST" ]]; then
  rm -rf "$OLD_DEST"
  echo "Removed stale provider symlink $OLD_DEST"
fi

echo "Hermes will discover provider 'construct-zero' (alias 'hcx') on next start."

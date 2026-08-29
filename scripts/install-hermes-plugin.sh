#!/usr/bin/env bash
# Symlink HCX Hermes provider plugin into ~/.hermes/plugins/model-providers/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/hermes-plugin/model-providers/hcx"
DEST_DIR="${HERMES_HOME:-$HOME/.hermes}/plugins/model-providers"
DEST="$DEST_DIR/hcx"

mkdir -p "$DEST_DIR"
if [[ -L "$DEST" || -e "$DEST" ]]; then
  rm -rf "$DEST"
fi
ln -s "$SRC" "$DEST"
echo "Linked $DEST -> $SRC"
echo "Hermes will discover provider 'hcx' on next start (hermes doctor / hermes model)."

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
cd "$ROOT/adapter"
uv sync --locked --extra dev --quiet

if [[ "${CI:-}" != "true" ]] && ! python3 -c "import venv" 2>/dev/null; then
  echo "deps-audit: skip locally (no python venv module); CI runs on ubuntu-latest"
  python3 "$ROOT/scripts/ci/audit_ignore_check.py"
  exit 0
fi

audit_pkg() {
  local dir="$1"
  echo "==> pip-audit $dir"
  local req errf
  req="$(mktemp)"
  errf="$(mktemp)"
  (
    cd "$dir"
    uv export --frozen --format requirements-txt --no-emit-workspace --no-dev -o "$req"
  )
  set +e
  "$ROOT/adapter/.venv/bin/pip-audit" -r "$req" --strict --desc on 2>"$errf"
  local rc=$?
  set -e
  if [[ "$rc" != "0" ]]; then
    if [[ "${CI:-}" != "true" ]] && grep -qE 'ensurepip|python3-venv' "$errf"; then
      echo "deps-audit: skip locally (pip-audit needs python venv support); CI runs on ubuntu-latest"
      rm -f "$req" "$errf"
      return 0
    fi
    cat "$errf" >&2
    rm -f "$req" "$errf"
    exit "$rc"
  fi
  rm -f "$req" "$errf"
}

audit_pkg "$ROOT/adapter"
audit_pkg "$ROOT/vpl"
audit_pkg "$ROOT/voice"

python3 "$ROOT/scripts/ci/audit_ignore_check.py"

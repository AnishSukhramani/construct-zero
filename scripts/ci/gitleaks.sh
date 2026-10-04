#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERSION="${GITLEAKS_VERSION:-8.18.4}"
BIN="${GITLEAKS_BIN:-$ROOT/.cache/gitleaks/gitleaks}"

if [[ ! -x "$BIN" ]]; then
  mkdir -p "$(dirname "$BIN")"
  tmp="$(mktemp -d)"
  curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${VERSION}/gitleaks_${VERSION}_linux_x64.tar.gz" \
    | tar xz -C "$tmp"
  install -m 0755 "$tmp/gitleaks" "$BIN"
  rm -rf "$tmp"
fi

cd "$ROOT"
if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
  "$BIN" detect --source . --config .gitleaks.toml --log-opts "HEAD~1..HEAD" -v
else
  "$BIN" detect --source . --config .gitleaks.toml -v
fi

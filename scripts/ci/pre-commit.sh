#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
"$ROOT/scripts/ci/verify-staged.sh"
"$ROOT/scripts/run-tests.sh" --fast

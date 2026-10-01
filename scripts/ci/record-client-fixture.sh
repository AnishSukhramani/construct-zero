#!/usr/bin/env bash
# Record an OpenAI client request against a loopback adapter (redacts Authorization).
# Usage: record-client-fixture.sh <client-name> <request.json> [base_url]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLIENT="${1:?client name (e.g. cline)}"
REQ="${2:?path to request JSON}"
BASE="${3:-${CZ_CONTRACT_BASE_URL:-http://127.0.0.1:8765}}"
OUT="$ROOT/adapter/tests/contract/fixtures/clients/$CLIENT"
mkdir -p "$OUT"

if [[ -n "${AUTHORIZATION:-}" ]]; then
  AUTH_HDR="Authorization: $AUTHORIZATION"
else
  AUTH_HDR=""
fi

cp "$REQ" "$OUT/request.json"
python3 - <<PY
import json, datetime, pathlib
out = pathlib.Path("$OUT")
meta = {
    "client": "$CLIENT",
    "recorded_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "note": "Recorded via scripts/ci/record-client-fixture.sh (Authorization never stored)",
    "base_path": "/v1/chat/completions",
}
out.joinpath("metadata.json").write_text(json.dumps(meta, indent=2) + "\\n")
PY

echo "Wrote fixture under $OUT"
echo "Probe (optional): curl -sS -H 'Content-Type: application/json' ${AUTH_HDR:+-H \"$AUTH_HDR\"} \\"
echo "  -d @$OUT/request.json $BASE/v1/chat/completions | head"

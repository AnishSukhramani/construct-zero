#!/usr/bin/env bash
# Opt-in: install a pre-commit hook that runs verify-staged + fast tests.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK="$ROOT/.git/hooks/pre-commit"
cat > "$HOOK" <<EOF
#!/usr/bin/env bash
exec "$ROOT/scripts/ci/pre-commit.sh"
EOF
chmod +x "$HOOK"
echo "Installed pre-commit hook -> scripts/ci/pre-commit.sh"

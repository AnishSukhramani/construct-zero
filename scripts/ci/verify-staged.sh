#!/usr/bin/env bash
# Read-only: fail if the git index contains forbidden paths or obvious secrets.
# Run from the repository root (or any path inside the repo).
set -euo pipefail

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "verify-staged: not a git repository" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

staged="$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"
if [[ -z "$staged" ]]; then
  exit 0
fi

offenders=()
while IFS= read -r path; do
  [[ -z "$path" ]] && continue
  case "$path" in
    hermes/*|.hermes/*|.construct-zero/*|.venvs/*|*/.venv/*|.venv/*|.venv)
      offenders+=("$path")
      ;;
    .env)
      offenders+=("$path")
      ;;
    .env.*)
      if [[ "$path" != ".env.example" ]]; then
        offenders+=("$path")
      fi
      ;;
    private/*|zzz-docs/*)
      offenders+=("$path")
      ;;
    config/construct-zero.yaml|config/hermesxcursor.yaml)
      offenders+=("$path")
      ;;
    *.log)
      offenders+=("$path")
      ;;
    .claude/*)
      offenders+=("$path")
      ;;
  esac
done <<< "$staged"

if ((${#offenders[@]} > 0)); then
  echo "verify-staged: forbidden paths staged:" >&2
  for p in "${offenders[@]}"; do
    echo "  $p" >&2
    echo "  Fix: git restore --staged $p" >&2
  done
  exit 1
fi

added="$(git diff --cached -U0 --no-color 2>/dev/null | grep '^+' | grep -v '^+++' || true)"
if [[ -n "$added" ]]; then
  secret_hits=()
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    body="${line#+}"
    if [[ "$body" =~ CURSOR_API_KEY= ]]; then
      val="${body#*CURSOR_API_KEY=}"
      val="${val%%#*}"
      val="$(echo "$val" | tr -d "[:space:]\"'")"
      if [[ -n "$val" && "$val" != "unused" ]]; then
        secret_hits+=("CURSOR_API_KEY in staged diff")
      fi
    fi
    if [[ "$body" =~ BEGIN[[:space:]]+(RSA|OPENSSH|EC|DSA)[[:space:]]+PRIVATE[[:space:]]+KEY ]]; then
      secret_hits+=("private key material in staged diff")
    fi
    if [[ "$body" =~ (ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|sk-[a-zA-Z0-9]{20,}) ]]; then
      secret_hits+=("token-like secret in staged diff")
    fi
  done <<< "$added"
  if ((${#secret_hits[@]} > 0)); then
    echo "verify-staged: possible secrets in staged content:" >&2
    printf '  %s\n' "${secret_hits[@]}" >&2
    echo "  Fix: remove the secret from the file and git restore --staged <path>" >&2
    exit 1
  fi
fi

exit 0

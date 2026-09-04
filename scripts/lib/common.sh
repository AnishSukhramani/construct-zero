#!/usr/bin/env bash
# Shared helpers for init/start scripts (prompts, env loading).
# Source from scripts/init.sh or scripts/start.sh — not from legacy setup paths.

# shellcheck disable=SC2034
CZ_LIB_COMMON_LOADED=1

cz_root() {
  if [[ -n "${CZ_ROOT:-${HCX_ROOT:-}}" ]]; then
    printf '%s\n' "${CZ_ROOT:-$HCX_ROOT}"
    return 0
  fi
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd)"
  if [[ "$(basename "$script_dir")" == "lib" ]]; then
    cd "$script_dir/../.." && pwd
  else
    cd "$script_dir/.." && pwd
  fi
}

# Copy HCX_* into CZ_* when the CZ_* var is unset (one-release shim).
cz_shim_legacy_env() {
  local suffix cz hcx
  for suffix in \
    API_KEY HOST PORT CONFIG MODEL BACKEND PID_FILE LOG_FILE \
    MAX_RESTARTS RESTART_DELAY AUTO ROOT DOCTOR_CHAT SKIP_HERMES SKIP_PLUGIN \
    INIT_VOICE INIT_START INIT_HERMES INIT_HERMES_CONFIG \
    VOICE_PID_FILE VOICE_LOG_FILE VOICE_HOST VOICE_PORT \
    VOICE_MAX_RESTARTS VOICE_RESTART_DELAY VOICE_PRELOAD VOICE_ALLOW_PUBLIC \
    VOICE_KOKORO_VOICE VOICE_WHISPER_MODEL VOICE_WHISPER_DEVICE VOICE_WHISPER_COMPUTE \
    VOICE_HERMES_TIMEOUT VPL_ENABLED VPL_LAYER_THRESHOLD_ITEMS VPL_MAX_BUCKETS \
    VPL_PASSTHROUGH_MAX_WORDS VPL_SESSION_TTL_SEC REPO_ROOT HERMES_BIN HEALTH_URL \
    BASE_URL; do
    cz="CZ_${suffix}"
    hcx="HCX_${suffix}"
    if [[ -z "${!cz:-}" && -n "${!hcx:-}" ]]; then
      export "${cz}=${!hcx}"
    fi
  done
}

# Load .env without overwriting variables already set in the environment.
cz_load_env() {
  local root env_file key val
  root="$(cz_root)"
  env_file="$root/.env"
  if [[ -f "$env_file" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
      if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        val="${BASH_REMATCH[2]}"
        val="${val%\"}"
        val="${val#\"}"
        val="${val%\'}"
        val="${val#\'}"
        if [[ -z "${!key:-}" ]]; then
          export "$key=$val"
        fi
      fi
    done <"$env_file"
  fi
  cz_shim_legacy_env
}

cz_has_gum() {
  command -v gum >/dev/null 2>&1
}

# Prefer /dev/tty so curl | bash can still prompt. Empty if neither is usable.
cz_tty() {
  if [[ -r /dev/tty ]]; then
    printf '%s\n' /dev/tty
  elif [[ -t 0 ]]; then
    printf '%s\n' /dev/stdin
  fi
}

cz_is_interactive() {
  local tty
  tty="$(cz_tty)"
  [[ "${CZ_AUTO:-${HCX_AUTO:-0}}" != "1" && -n "$tty" && -t 1 ]]
}

# ask_yn "Question?" default_yes|default_no  → prints yes/no to stdout
# Empty Enter applies the default (skip answering). Does not use gum confirm
# so the skip hint stays on the same line and curl | bash cannot steal stdin.
cz_ask_yn() {
  local question="${1:?question required}"
  local default="${2:-yes}"
  local prompt_suffix skip_hint answer tty

  if [[ "${CZ_AUTO:-${HCX_AUTO:-0}}" == "1" ]]; then
    if [[ "$default" == "yes" ]]; then
      printf 'yes\n'
    else
      printf 'no\n'
    fi
    return 0
  fi

  if [[ "$default" == "yes" ]]; then
    prompt_suffix="[Y/n]"
    skip_hint="Press Enter to skip — default Yes"
  else
    prompt_suffix="[y/N]"
    skip_hint="Press Enter to skip — default No"
  fi

  tty="$(cz_tty)"
  if [[ -n "$tty" ]]; then
    read -r -p "$question $prompt_suffix  ($skip_hint) " answer <"$tty" || true
  else
    answer=""
  fi
  answer="${answer:-}"
  if [[ -z "$answer" ]]; then
    printf '%s\n' "$default"
    return 0
  fi
  case "$(echo "$answer" | tr '[:upper:]' '[:lower:]')" in
    y|yes) printf 'yes\n' ;;
    n|no) printf 'no\n' ;;
    *) printf '%s\n' "$default" ;;
  esac
}

# ask_secret "Prompt" [skip|keep] → prints value to stdout (may be empty)
# skip = empty Enter returns empty; keep = prompt copy only (caller must not overwrite on empty).
cz_ask_secret() {
  local prompt="${1:-Cursor API key}"
  local empty_mode="${2:-skip}"
  local hint value tty

  if [[ "${CZ_AUTO:-${HCX_AUTO:-0}}" == "1" ]]; then
    printf '%s\n' "${CURSOR_API_KEY:-}"
    return 0
  fi

  if [[ "$empty_mode" == "keep" ]]; then
    hint="Press Enter to keep the existing key"
  else
    hint="Press Enter to skip"
  fi

  tty="$(cz_tty)"
  if [[ -n "$tty" ]]; then
    read -r -s -p "$prompt  ($hint): " value <"$tty" || true
    echo >&2
  else
    value=""
  fi
  printf '%s\n' "${value:-}"
}

cz_info() {
  if cz_has_gum && [[ -t 1 ]]; then
    gum style --foreground 14 "$*" >&2
  else
    echo "==> $*" >&2
  fi
}

cz_warn() {
  if cz_has_gum && [[ -t 1 ]]; then
    gum style --foreground 11 "WARNING: $*" >&2
  else
    echo "WARNING: $*" >&2
  fi
}

cz_spin() {
  local title="${1:?title required}"
  shift
  if cz_has_gum && [[ -t 1 ]]; then
    gum spin --spinner dot --title "$title" -- "$@"
  else
    echo "==> $title" >&2
    "$@"
  fi
}

cz_preflight() {
  local missing=0
  for cmd in git python3 curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "Missing required command: $cmd" >&2
      missing=1
    fi
  done
  if ! command -v ffmpeg >/dev/null 2>&1; then
    cz_warn "ffmpeg not found — voice STT may be limited until installed (e.g. brew install ffmpeg)"
  fi
  if (( missing )); then
    return 1
  fi
}

# Prefer uv on PATH, then common install locations.
cz_uv_bin() {
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  local p
  for p in "${HOME}/.local/bin/uv" "${HOME}/.cargo/bin/uv"; do
    if [[ -x "$p" ]]; then
      printf '%s\n' "$p"
      return 0
    fi
  done
  return 1
}

cz_python() {
  local c
  for c in python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      printf '%s\n' "$c"
      return 0
    fi
  done
  echo "No python3 found" >&2
  return 1
}

cz_install_uv() {
  cz_info "Installing uv (https://docs.astral.sh/uv/)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if ! cz_uv_bin >/dev/null; then
    echo "uv install finished but the binary was not found. Add ~/.local/bin to PATH and re-run." >&2
    return 1
  fi
}

# Offer official uv installer when missing. --auto installs unless CZ_INIT_UV=0.
cz_ensure_uv() {
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if cz_uv_bin >/dev/null; then
    return 0
  fi
  local do_install=yes
  if [[ "${CZ_AUTO:-${HCX_AUTO:-0}}" == "1" ]]; then
    [[ "${CZ_INIT_UV:-1}" == "0" ]] && do_install=no
  else
    if [[ "$(cz_ask_yn "Install uv? (recommended Python installer, one binary)" "yes")" != "yes" ]]; then
      do_install=no
    fi
  fi
  if [[ "$do_install" == "yes" ]]; then
    cz_install_uv
  else
    cz_warn "Skipping uv — will try python3.12 / python3.11 / python3"
  fi
}

cz_venv_create() {
  local dest="${1:?venv path required}"
  local uvbin py
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if uvbin="$(cz_uv_bin)"; then
    "$uvbin" venv "$dest" --python 3.12 || "$uvbin" venv "$dest" --python 3.11 || "$uvbin" venv "$dest"
    return 0
  fi
  py="$(cz_python)"
  if ! "$py" -m venv "$dest"; then
    echo "Failed to create venv with $py (ensurepip often fails on Python 3.14)." >&2
    echo "Install uv and re-run:" >&2
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    echo "  ./scripts/init.sh" >&2
    rm -rf "$dest"
    return 1
  fi
  if [[ ! -x "$dest/bin/pip" && ! -x "$dest/bin/pip3" ]]; then
    echo "venv has no pip. Install uv and re-run:" >&2
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    rm -rf "$dest"
    return 1
  fi
}

# cz_pip_editable <python> <pip -e args...>
cz_pip_editable() {
  local py="${1:?python required}"
  local uvbin
  shift
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if uvbin="$(cz_uv_bin)"; then
    "$uvbin" pip install -e "$@" --python "$py"
  else
    "$py" -m pip install -U pip
    "$py" -m pip install -e "$@"
  fi
}

# Write key=value to .env (replace existing line or append).
cz_env_set() {
  local root key val env_file tmp
  root="$(cz_root)"
  key="${1:?key required}"
  val="${2:-}"
  env_file="$root/.env"
  tmp="$(mktemp)"
  if [[ -f "$env_file" ]]; then
    grep -v "^${key}=" "$env_file" >"$tmp" || true
  fi
  printf '%s=%s\n' "$key" "$val" >>"$tmp"
  mv "$tmp" "$env_file"
  chmod 600 "$env_file" 2>/dev/null || true
}

# Ensure Hermes config for this install (never overwrite without confirm).
cz_write_hermes_config() {
  local root snippet dest hermes_home port
  root="$(cz_root)"
  snippet="$root/config/hermes.config.snippet.yaml"
  hermes_home="${HERMES_HOME:-$HOME/.hermes}"
  dest="$hermes_home/config.yaml"
  port="${CZ_PORT:-${HCX_PORT:-8765}}"

  if [[ ! -f "$snippet" ]]; then
    cz_warn "Missing $snippet — skipping Hermes config"
    return 1
  fi

  mkdir -p "$hermes_home"

  if [[ -f "$dest" ]]; then
    if [[ "${CZ_AUTO:-${HCX_AUTO:-0}}" == "1" ]]; then
      cz_info "Hermes config exists at $dest — leaving unchanged (--auto)"
      return 0
    fi
    if [[ "$(cz_ask_yn "Hermes config already exists at $dest. Overwrite?" "no")" != "yes" ]]; then
      cz_info "Keeping existing Hermes config"
      return 0
    fi
  fi

  sed "s|127.0.0.1:8765|127.0.0.1:${port}|g" "$snippet" >"$dest"
  cz_info "Wrote $dest"
}

#!/usr/bin/env bash
# Home screen for `./construct-zero help`. Sourced from the repo-root dispatcher.

cz_help_banner() {
  cat <<'EOF'
                      __                  __
  _________  ____  / /________  _______/ /_      ____  ___  _________
 / ___/ __ \/ __ \/ __/ ___/ / / / ___/ __/_____/_  / / _ \/ ___/ __ \
/ /__/ /_/ / / / / /_/ /  / /_/ / /__/ /_/_____/ /_\/  __/ /  / /_/ /
\___/\____/_/ /_/\__/_/   \__,_/\___/\__/      /___/ \___/_/   \____/
EOF
}

cz_help_body() {
  cat <<'EOF'
  ./construct-zero start              Start the loopback adapter (scripts/start.sh)
  ./construct-zero start --voice      Adapter plus voice sidecar
  ./construct-zero doctor             Health / models check (scripts/doctor.sh)
  ./construct-zero init               Interactive setup (scripts/init.sh)
  ./construct-zero chat -q "hello"    Hermes CLI + --provider construct-zero
                                      (--model auto if omitted)
  ./construct-zero help               This screen

  Inference-only adapter on loopback. Cursor driver stays ask.
EOF
}

cz_print_help() {
  local banner body cols
  banner="$(cz_help_banner)"
  body="$(cz_help_body)"
  cols="$(tput cols 2>/dev/null || echo 100)"
  if [[ "${cols:-0}" -lt 80 ]]; then
    cols=80
  elif [[ "$cols" -gt 100 ]]; then
    cols=100
  fi

  if cz_has_gum && [[ -t 1 ]]; then
    gum style \
      --border double \
      --padding "1 2" \
      --align left \
      --width "$cols" \
      --border-foreground 14 \
      "$banner"

    echo
    gum style \
      --border rounded \
      --padding "1 2" \
      --align left \
      --width "$cols" \
      --border-foreground 14 \
      "$body"
  else
    printf '%s\n' "$banner"
    echo
    printf '%s\n' "$body"
  fi
}

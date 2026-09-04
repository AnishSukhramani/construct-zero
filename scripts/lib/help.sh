#!/usr/bin/env bash
# Home screen for `./construct-zero help`. Sourced from the repo-root dispatcher.

cz_print_help() {
  local root py
  root="${CZ_ROOT:-$(cz_root)}"
  py="$root/adapter/.venv/bin/python"
  if [[ -x "$py" ]]; then
    "$py" "$root/scripts/lib/help_ui.py"
  else
    python3 "$root/scripts/lib/help_ui.py"
  fi
}

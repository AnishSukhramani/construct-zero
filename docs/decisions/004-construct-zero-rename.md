# ADR 004: Rebrand to Construct-Zero

**Status:** Accepted

## Context

The project shipped as **HCX — Hermes on Cursor** (`hermesXcursor`, package `hcx`, env `HCX_*`, runtime `~/.hermesxcursor/`). The public name is now **Construct-Zero**. User-facing docs, logs, packages, config paths, env vars, and the Hermes provider should match that name.

## Decision

Canonical identifiers:

| Old | New |
|-----|-----|
| HCX — Hermes on Cursor | Construct-Zero |
| `hcx` Python package | `construct_zero` |
| `hcx-vpl` / `hcx_vpl` | `construct-zero-vpl` / `construct_zero_vpl` |
| `hcx-voice` / `hcx_voice` | `construct-zero-voice` / `construct_zero_voice` |
| `HCX_*` env vars | `CZ_*` |
| `HCXConfig` | `CZConfig` |
| `config/hermesxcursor.yaml` | `config/construct-zero.yaml` |
| `~/.hermesxcursor/` | `~/.construct-zero/` |
| Hermes provider `hcx` | `construct-zero` |
| `.cursor/rules/hcx.mdc` | `.cursor/rules/construct-zero.mdc` |

Ports (`8765`, `8767`) and Hermes upstream (`hermes/`, `~/.hermes/`) are unchanged.

## Shim policy (one release)

Existing local setups must keep working:

1. **Config paths:** new paths win; `hermesxcursor.yaml` and `~/.hermesxcursor/` remain in the search list.
2. **Env vars:** `CZ_*` preferred; `HCX_*` accepted with a deprecation warning.
3. **Hermes provider:** `construct-zero` is canonical; aliases include `hcx`, `hermesxcursor`, `hcx-cursor`, `cz`, `cursor`.
4. **Local files:** do not auto-delete `config/hermesxcursor.yaml` or `~/.hermesxcursor/`. Setup may print a one-line migration hint.

## Non-goals

- Do not rewrite git history.
- Do not rename the user's local checkout directory.
- Do not rebrand Hermes Agent or change `hermes/` clone mechanics.

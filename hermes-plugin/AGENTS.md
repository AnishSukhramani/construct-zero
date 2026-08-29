# hermes-plugin/ — HCX model provider

Declares Hermes provider `hcx` pointing at local adapter.

## Scope

- `model-providers/hcx/plugin.yaml` — metadata
- `model-providers/hcx/__init__.py` — `register_provider(ProviderProfile(...))`
- **Declarative only** — no inference runtime here

## Install

```bash
./scripts/install-hermes-plugin.sh
```

Symlinks into `~/.hermes/plugins/model-providers/hcx`.

## Deep dive

[docs/features/hermes-plugin.md](../docs/features/hermes-plugin.md)

## Do not

- Add agent loop or tool logic to this folder
- Commit upstream Hermes source (lives in gitignored `hermes/`)

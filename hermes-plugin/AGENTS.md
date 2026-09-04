# hermes-plugin/ — Construct-Zero model provider

Declares Hermes provider `construct-zero` pointing at local adapter.

## Scope

- `model-providers/construct-zero/plugin.yaml` — metadata
- `model-providers/construct-zero/__init__.py` — `register_provider(ProviderProfile(...))`
- **Declarative only** — no inference runtime here

## Install

```bash
./scripts/install-hermes-plugin.sh
```

Symlinks into `~/.hermes/plugins/model-providers/construct-zero`.

## Deep dive

[docs/features/hermes-plugin.md](../docs/features/hermes-plugin.md)

## Do not

- Add agent loop or tool logic to this folder
- Commit upstream Hermes source (lives in gitignored `hermes/`)

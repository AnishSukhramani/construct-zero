# Hermes HCX provider plugin

Declares provider `hcx` so Hermes routes inference to the local adapter.

## Location

```text
hermes-plugin/model-providers/hcx/
  plugin.yaml    # Declarative metadata
  __init__.py    # register_provider(ProviderProfile(...))
```

## Install

```bash
./scripts/install-hermes-plugin.sh
```

Symlinks plugin into `~/.hermes/plugins/model-providers/hcx`. Hermes discovers on next start.

## Provider profile

- **Name:** `hcx` (aliases: `cursor`, `hermesxcursor`, `hcx-cursor`)
- **base_url:** `http://127.0.0.1:8765/v1`
- **Auth env:** `HCX_API_KEY` (placeholder `unused` is fine), `HCX_BASE_URL` optional override

## Hermes user config

User creates `~/.hermes/config.yaml` (not in repo):

```yaml
model:
  provider: hcx
  default: auto
  base_url: http://127.0.0.1:8765/v1
```

Snippet: [config/hermes.config.snippet.yaml](../../config/hermes.config.snippet.yaml)

## Boundaries

- Plugin is **declarative** — no agent loop logic here
- Upstream Hermes code lives in gitignored `hermes/` — not this folder
- Do not commit `~/.hermes/` contents

## Related

- [adapter-inference.md](adapter-inference.md)
- [ADR 002](../decisions/002-hermes-not-vendored.md)
- [hermes-plugin/AGENTS.md](../../hermes-plugin/AGENTS.md)

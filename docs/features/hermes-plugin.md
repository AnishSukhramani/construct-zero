# Hermes Construct-Zero provider plugin

Declares provider `construct-zero` so Hermes routes inference to the local adapter.

## Location

```text
hermes-plugin/model-providers/construct-zero/
  plugin.yaml    # Declarative metadata
  __init__.py    # register_provider(ProviderProfile(...))
```

## Install

```bash
./scripts/install-hermes-plugin.sh
```

Symlinks plugin into `~/.hermes/plugins/model-providers/construct-zero`. Hermes discovers on next start. A leftover `hcx` symlink is removed.

## Provider profile

- **Name:** `construct-zero` (aliases: `hcx`, `hermesxcursor`, `hcx-cursor`, `cz`, `cursor`)
- **base_url:** `http://127.0.0.1:8765/v1`
- **Auth env:** `CZ_API_KEY` (placeholder `unused` is fine), `CZ_BASE_URL` optional override. `HCX_API_KEY` / `HCX_BASE_URL` still accepted.

## Hermes user config

User creates `~/.hermes/config.yaml` (not in repo):

```yaml
model:
  provider: construct-zero
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
- [ADR 004](../decisions/004-construct-zero-rename.md)
- [hermes-plugin/AGENTS.md](../../hermes-plugin/AGENTS.md)

# Using Construct-Zero in private / regulated codebases

Construct-Zero is designed to sit **beside** your product repo, not replace your security program.

## Recommended layout

| Layout | When to use |
|--------|-------------|
| Gitignored `.cz/` at repo root | Single repo; keeps CZ out of git history |
| `../construct-zero/` sibling clone | Monorepo with dedicated tooling folder |
| Standalone empty folder (`install.sh`) | Personal agent stack, not inside app source |

Avoid committing `.env`, `.hermes/`, or API keys. Run `./construct-zero init` from your **application** root when using `home` features so `.cz/` lives with your code.

## Project isolation

Set **`CZ_PROJECT_ROOT`** to your application repository root when CZ is nested:

```bash
export CZ_PROJECT_ROOT=/path/to/myapp
./construct-zero chat
```

Doctor **`project-isolation`** (certify profile) warns when the agent workspace equals the CZ install tree.

Agent ignore files (`.cursorignore`, `.clineignore`, `.hermes/context-exclude.txt`) are appended on `init` for nested installs so CZ source is not indexed as your product.

## Cursor Privacy Mode

When using the default Cursor backend, prompts and context leave the machine to Cursor cloud. Enable **[Cursor Privacy Mode](https://cursor.com/privacy)** and organizational policies your company requires before pointing Hermes at proprietary code.

Construct-Zero does not add a separate telemetry channel; inference still flows through Cursor or your configured backend.

## Air-gapped / VPC inference

Use **`openai_compat`** with Ollama, Azure OpenAI, vLLM, or LiteLLM inside your network:

```yaml
inference:
  backend: openai_compat
  openai_compat:
    base_url: http://127.0.0.1:11434/v1
    api_key_env: CZ_OPENAI_COMPAT_API_KEY
```

See [backend-openai-compat.md](../recipes/backend-openai-compat.md).

## Least privilege

- Keep `adapter.host: 127.0.0.1` (required for certification).
- Set `adapter.api_key` (or `CZ_API_KEY`) so only clients with the bearer can call `/v1/*`.
- `chmod 600` on `.env`; state under `.construct-zero/` uses `0700`/`0600` where supported.
- Never put `CURSOR_API_KEY` in tracked YAML; use `.env` only.

## Liability

Construct-Zero is MIT licensed **without warranty**. You are responsible for configuration, compliance, and agent behavior. See README **Security & liability** (not legal advice — involve counsel for regulated environments).

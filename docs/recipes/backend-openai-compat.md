# BYO company LLM (`openai_compat`)

Route Hermes or Cline to your **Azure OpenAI**, **vLLM**, **Ollama**, or **LiteLLM** gateway through CZ. Keys live in the environment only — never in YAML.

```yaml
inference:
  backend: openai_compat
  openai_compat:
    preset: generic   # azure | vllm | ollama | litellm
    base_url: https://llm.corp.example/v1
    api_key_env: CZ_OPENAI_COMPAT_API_KEY
    timeout_s: 120
    allow_insecure_http: false
```

Export the key: `export CZ_OPENAI_COMPAT_API_KEY=...`

## Azure OpenAI

```yaml
inference:
  backend: openai_compat
  openai_compat:
    preset: azure
    base_url: https://YOUR-RESOURCE.openai.azure.com
    api_key_env: CZ_OPENAI_COMPAT_API_KEY
    azure:
      api_version: "2024-10-21"
      deployments:
        gpt-4o: your-deployment-name
```

Uses path `/openai/deployments/{deployment}/chat/completions?api-version=…` and header `api-key`.

## vLLM / LiteLLM

Point `base_url` at your OpenAI-compatible `/v1` root. Preset `generic` or `litellm` (same wire shape).

## Ollama

```yaml
inference:
  backend: openai_compat
  openai_compat:
    preset: ollama
    base_url: http://127.0.0.1:11434/v1
```

No API key required for default local Ollama.

## Limits

- Native SSE streaming and tool calls pass through when the upstream supports them.
- Non-loopback `http://` is refused unless `allow_insecure_http: true`.
- Upstream errors map to `cz_upstream_<status>`; timeouts → `504 cz_upstream_timeout`.

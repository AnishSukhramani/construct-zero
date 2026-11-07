# Security policy

## Reporting vulnerabilities

Email the maintainer via [GitHub Security Advisories](https://github.com/AnishSukhramani/construct-zero/security/advisories/new) or open a **private** security report if you cannot use GitHub.

Please include:

- Affected version (commit or tag)
- Reproduction steps
- Impact (confidentiality, integrity, availability)
- Suggested fix if you have one

We aim to acknowledge reports within a few business days. Do not open public issues for undisclosed vulnerabilities.

## Scope

**In scope**

- Construct-Zero OSS paths: `adapter/`, `voice/`, `vpl/`, `hermes-plugin/`, `scripts/`, `install.sh`, `construct-zero`, and documented configuration under `config/*.example`
- Local adapter on loopback (`127.0.0.1:8765`) and voice sidecar on loopback (`127.0.0.1:8767`)
- Hermes plugin wiring (declarative provider only)

**Out of scope**

- Upstream Hermes agent loop (gitignored `hermes/` clone)
- Cursor cloud infrastructure, Cursor IDE, or cursor-sdk behavior beyond what Construct-Zero configures (`mode: ask`)
- User `.env`, `~/.hermes/`, and proprietary code in your repositories
- Misconfiguration (public port binding, committing API keys, disabling Privacy Mode while sending secrets in prompts)

## Data that leaves your machine

Construct-Zero is **not** air-gapped by default when `inference.backend: cursor`:

```text
Your repo (local) → Hermes (local) → Construct-Zero adapter (loopback)
    → cursor-sdk / Cursor API → Cursor cloud (inference)
```

Prompts, file context Hermes/Cursor attach, and model outputs are processed under **your Cursor account** and Cursor’s terms. Construct-Zero does **not** add a separate Construct-Zero telemetry channel; see [SECURITY-AUDIT.md](SECURITY-AUDIT.md).

For regulated or proprietary codebases:

- Enable **[Cursor Privacy Mode](https://cursor.com/privacy)** (org policy where available)
- Prefer **`openai_compat`** to a company-controlled endpoint (Ollama, Azure OpenAI, vLLM) for air-gapped or VPC-only inference
- Keep the adapter on loopback, set `adapter.api_key`, and use agent ignore files so CZ install trees are not indexed as your product

See [docs/features/private-regulated-codebases.md](docs/features/private-regulated-codebases.md).

## Supported versions

Security fixes land on `main` first. Tagged releases follow [README.md](README.md) release notes.

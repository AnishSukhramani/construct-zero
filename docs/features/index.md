# Feature registry

Status key: **MVP** = shipped in repo | **Stub** = placeholder only | **Out of scope** = do not build without explicit ask

| Feature | Status | Code | Doc |
|---------|--------|------|-----|
| Onboarding suite (`install.sh` + `init.sh` + `./construct-zero`) | MVP | [install.sh](../../install.sh), [scripts/init.sh](../../scripts/init.sh), [construct-zero](../../construct-zero) | [onboarding.md](onboarding.md) |
| Construct-Zero adapter (OpenAI façade) | MVP | [adapter/](../../adapter/) | [adapter-inference.md](adapter-inference.md) |
| Cursor tool passthrough | MVP | [adapter/src/construct_zero/core/sessions.py](../../adapter/src/construct_zero/core/sessions.py) | [adapter-inference.md](adapter-inference.md) |
| Hermes Construct-Zero provider plugin | MVP | [hermes-plugin/](../../hermes-plugin/) | [hermes-plugin.md](hermes-plugin.md) |
| Voice hold-to-talk sidecar | MVP | [voice/](../../voice/) | [voice-sidecar.md](voice-sidecar.md) |
| Voice Presentation Layer (VPL) | MVP | [vpl/](../../vpl/) | [voice-vpl.md](voice-vpl.md) |
| Public test & staged-file safety scripts | MVP | [scripts/run-tests.sh](../../scripts/run-tests.sh), [scripts/ci/](../../scripts/ci/) | [scripts.md](../references/scripts.md) |
| GitHub CI + local `make ci` | MVP | [.github/workflows/ci.yml](../../.github/workflows/ci.yml), [Makefile](../../Makefile) | [ci.md](../references/ci.md) |
| Claude Code driver | Stub | [adapter/src/construct_zero/drivers/claude_code.py](../../adapter/src/construct_zero/drivers/claude_code.py) | [adapter-inference.md](adapter-inference.md) |
| Agent home (shared `.cz/` context) | Preview | [adapter/src/construct_zero/home/](../../adapter/src/construct_zero/home/) | [agent-home.md](agent-home.md) |

## Out of scope (unless user explicitly requests)

- Depending on `cursor-api-proxy` as runtime
- Claude Code driver implementation (beyond stub)
- Public exposure of adapter port (must stay loopback)
- Cursor Cloud / iOS profiles
- Second agent *loop* inside Construct-Zero (CZ hosts context and orchestrates external agents only; Hermes owns tools)
- Vendoring Hermes source in this repo

## Nested agent entrypoints

When working inside a subsystem directory, Cursor also loads:

| Directory | AGENTS.md |
|-----------|-----------|
| `adapter/` | [adapter/AGENTS.md](../../adapter/AGENTS.md) |
| `voice/` | [voice/AGENTS.md](../../voice/AGENTS.md) |
| `vpl/` | [vpl/AGENTS.md](../../vpl/AGENTS.md) |
| `hermes-plugin/` | [hermes-plugin/AGENTS.md](../../hermes-plugin/AGENTS.md) |

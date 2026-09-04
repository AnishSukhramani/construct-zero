# Scripts reference

Daily entrypoint is repo-root [`construct-zero`](../../construct-zero) (`./construct-zero help`). Scripts in [scripts/](../../scripts/) remain the implementations. Run from the install folder unless noted.

| Script | Purpose | When to run |
|--------|---------|-------------|
| [`construct-zero`](../../construct-zero) (repo root) | Dispatcher: `start`, `doctor`, `init`, `chat`, `help` | Daily use; help home screen after init |
| [`install.sh`](../../install.sh) (repo root) | Curl bootstrap: clone into cwd, folder-local `.env`, then `init.sh` | New install in a blank folder |
| `init.sh` | Interactive one-step onboarding (Hermes, venvs, plugin, optional voice, start + doctor); ends with `./construct-zero help` | First-time setup after clone; called by install.sh |
| `start.sh` | Start adapter; `--voice` also starts voice sidecar | Daily use (`./construct-zero start`) |
| `setup.sh` | Clone Hermes into `hermes/`, adapter venv, Hermes venv, plugin, config copies | Manual bootstrap; called by init |
| `ensure-hermes.sh` | Verify or clone upstream Hermes at lock pin | Called by setup/update; manual if `hermes/` missing |
| `update-hermes.sh` | Fetch/pull Hermes clone, refresh venv, reinstall plugin | When bumping Hermes version |
| `install-hermes-plugin.sh` | Symlink Construct-Zero provider into `$HERMES_HOME/plugins/` | After setup; after plugin changes |
| `start-adapter.sh` | Construct-Zero on loopback with supervisor | Daily use; before Hermes chat |
| `start-voice.sh` | Voice sidecar (port from `CZ_VOICE_PORT`, default `:8767`) | After adapter up; optional |
| `setup-voice.sh` | Voice venv + deps | Once before first voice use |
| `doctor.sh` | `/health`, models, optional chat smoke; Hermes pin hint | After config changes; debugging (`./construct-zero doctor`) |
| `lib/help.sh` | Banner + command menu for `./construct-zero help` | Sourced by the dispatcher; not run directly |

## init.sh flags

| Flag | Effect |
|------|--------|
| `--auto` | Non-interactive; defaults + env (`CZ_INIT_VOICE`, `CZ_INIT_HERMES`, etc.) |
| `--voice` / `--no-voice` | Force voice setup on/off |
| `--no-start` | Skip start + doctor at end |
| `--skip-hermes` | Skip Hermes clone and Hermes CLI venv |
| `--cursor-key KEY` | Set `CURSOR_API_KEY` (written to `.env`) |
| `--no-uv` | Do not offer/install uv |

## setup.sh flags (additive; unflagged behavior unchanged)

| Flag / env | Effect |
|------------|--------|
| `--skip-hermes` / `CZ_SKIP_HERMES=1` | Skip Hermes clone and Hermes venv |
| `--skip-plugin` / `CZ_SKIP_PLUGIN=1` | Skip plugin install |

## Agent constraints

- Agents **do not run** git or deployment scripts that mutate remotes.
- Agents **may suggest** these commands in chat for the user.
- `start-*.sh` scripts manage PIDs — tests must not invoke them (see local test harness).

## Related

- Human quick start: [README.md](../../README.md)
- Onboarding feature: [onboarding.md](../features/onboarding.md)
- Deploy flow: [PRE-COMMIT-CHECKLIST.md](../../PRE-COMMIT-CHECKLIST.md)

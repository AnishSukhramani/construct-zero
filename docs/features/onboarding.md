# Onboarding suite

**Status:** MVP — [`install.sh`](../../install.sh) + [`scripts/init.sh`](../../scripts/init.sh)

## Curl install (folder-isolated)

Blank folder becomes one isolated stack. Repeat in another folder for a second copy.

```bash
mkdir my-agent && cd my-agent
curl -fsSL https://raw.githubusercontent.com/AnishSukhramani/construct-zero/main/install.sh | bash
```

[`install.sh`](../../install.sh):

1. Refuses a non-empty directory unless `./scripts/init.sh` already exists (resume)
2. `git clone --depth 1` of this repo **into the current directory**
3. Writes folder-local `.env` via [`scripts/lib/isolate.sh`](../../scripts/lib/isolate.sh): `HERMES_HOME`, `CZ_STATE_DIR`, PIDs/logs, free `CZ_PORT` / `CZ_VOICE_PORT`
4. Runs `./scripts/init.sh`, which offers to install [uv](https://docs.astral.sh/uv/) (default yes) then the usual Y/N onboarding

Layout inside that folder:

```text
.hermes/              # Hermes home for this install only
.construct-zero/      # adapter config, PIDs, logs
.env                  # CURSOR_API_KEY + isolation vars
hermes/               # upstream clone (gitignored)
.venvs/
```

Does not require PATH or Homebrew. Does not write `~/.hermes` or `~/.construct-zero` when isolation vars are set.

## Interactive init

[`scripts/init.sh`](../../scripts/init.sh) orchestrates existing scripts without replacing them.

1. Preflight (`git`, `python3`, `curl`; warns on missing `uv` / `ffmpeg`)
2. Create `.env` from `.env.example` if missing; prompt for `CURSOR_API_KEY`
3. Y/N prompts (or `--auto` defaults):
   - Clone Hermes locally (default yes)
   - Set up voice (default no)
   - Write Hermes config for this install if missing (default yes)
   - Start adapter + doctor (default yes)
   - Install uv if missing (default yes; `--no-uv` / `CZ_INIT_UV=0` to skip)
4. Calls `./scripts/setup.sh` (with `--skip-hermes` if declined), optional `./scripts/setup-voice.sh`, `./scripts/start.sh`, `./scripts/doctor.sh`

Without `install.sh` (clone + `./scripts/init.sh`), adapter/Hermes still default to `~/.construct-zero` and `~/.hermes`.

## Daily commands after init

```bash
./scripts/start.sh
./scripts/doctor.sh
.venvs/hermes/bin/hermes chat -q "hello" --provider construct-zero --model auto
```

## Manual path preserved

All legacy scripts work unchanged:

- `./scripts/setup.sh`
- `./scripts/start-adapter.sh` / `./scripts/start-voice.sh`
- `./scripts/doctor.sh`

## Prompts

Uses [gum](https://github.com/charmbracelet/gum) when installed; falls back to plain `read` / `[Y/n]`. Gum is optional.

## Internal sandbox (not shipped)

Maintainers can trial init in Docker via gitignored `private/scripts/sandbox-onboarding.sh` — isolated `HOME`, host ports `18765`/`18767`. Not required for end users.

```bash
private/scripts/sandbox-onboarding.sh            # build + interactive init
private/scripts/sandbox-onboarding.sh --rebuild  # clean image after a bad build
private/scripts/sandbox-onboarding.sh --no-build
```

Uses committed repo-root [`.dockerignore`](../../.dockerignore) so `hermes/`, `.venvs/`, and `**/.venv/` are never baked into the image. Do not run `docker compose -f private/docker-compose.sandbox.yml build` without that file.

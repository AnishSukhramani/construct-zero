# Onboarding suite

**Status:** MVP — [`install.sh`](../../install.sh) + [`scripts/init.sh`](../../scripts/init.sh) + [`construct-zero`](../../construct-zero)

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
4. Runs `./scripts/init.sh` with stdin from `/dev/tty` when a TTY exists (so `curl | bash` can still ask questions). If there is no TTY, runs `--auto`.
5. Init offers to install [uv](https://docs.astral.sh/uv/) (default yes), then Y/N onboarding and the API key slot. After success it runs `./construct-zero help`.

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

[`scripts/init.sh`](../../scripts/init.sh) (also `./construct-zero init`) orchestrates existing scripts without replacing them.

1. Preflight (`git`, `python3`, `curl`; warns on missing `uv` / `ffmpeg`)
2. Create `.env` from `.env.example` if missing; always prompt for `CURSOR_API_KEY` unless `--auto` (Enter keeps an existing key or skips)
3. Y/N prompts (or `--auto` defaults):
   - Clone Hermes locally (default yes)
   - Set up voice (default no)
   - Write Hermes config for this install if missing (default yes)
   - Start adapter + doctor (default yes)
   - Install uv if missing (default yes; `--no-uv` / `CZ_INIT_UV=0` to skip)
4. Calls `./scripts/setup.sh` (with `--skip-hermes` if declined), optional `./scripts/setup-voice.sh`, `./scripts/start.sh`, `./scripts/doctor.sh`
5. Prints the help home screen (`./construct-zero help`)

Without `install.sh` (clone + `./construct-zero init`), adapter/Hermes still default to `~/.construct-zero` and `~/.hermes`.

## Daily commands after init

```bash
./construct-zero chat               # talk to Hermes (not a global "hermes" command)
./construct-zero start              # adapter; add --voice for the sidecar
./construct-zero doctor             # check that it is working
./construct-zero help               # reprints this menu
```

`init` is not on the help menu (it already ran during install). Re-run with `./construct-zero init` if you need to.

Equivalents: `scripts/start.sh`, `scripts/doctor.sh`, `scripts/init.sh`.

## CLI dispatcher

Repo-root [`construct-zero`](../../construct-zero) is not installed on PATH. It resolves the install from its own path (not cwd).

| Command | Action |
|---------|--------|
| `./construct-zero start` | [`scripts/start.sh`](../../scripts/start.sh) |
| `./construct-zero start --voice` | Adapter plus voice sidecar |
| `./construct-zero doctor` | [`scripts/doctor.sh`](../../scripts/doctor.sh) |
| `./construct-zero chat` | Opens Hermes in this folder (`--provider construct-zero`; `--model auto` if omitted) |
| `./construct-zero help` | Banner + what-to-do menu (also `--help`, `-h`, `/help`, or no args) |

`./construct-zero init` still runs onboarding but is omitted from the help menu.

Unknown subcommands print help on stderr and exit 1. `start` / `doctor` / `chat` do not print the banner.

Help UI: [`scripts/lib/help_ui.py`](../../scripts/lib/help_ui.py) renders a pyfiglet wordmark plus sapphire copy via Rich (shine sweep on the banner only). Fallback is the same text without color/animation if those packages are missing. Gum is not used for help.

## Manual path preserved

All legacy scripts work unchanged:

- `./scripts/setup.sh`
- `./scripts/start-adapter.sh` / `./scripts/start-voice.sh`
- `./scripts/doctor.sh`

## Prompts

Y/N and API-key prompts read from `/dev/tty` so they work under `curl | bash`. Each line shows **Press Enter to skip** (empty Enter applies the Y/N default, or leaves the API key unset / unchanged). `--auto` / `CZ_AUTO=1` skips prompts. [gum](https://github.com/charmbracelet/gum) is optional (colored logs and spinners) — not used for Y/N, so the skip hint stays visible.

## Internal sandbox (not shipped)

Maintainers can trial init in Docker via gitignored `private/scripts/sandbox-onboarding.sh` — isolated `HOME`, host ports `18765`/`18767`. Not required for end users.

```bash
private/scripts/sandbox-onboarding.sh            # build + interactive init
private/scripts/sandbox-onboarding.sh --rebuild  # clean image after a bad build
private/scripts/sandbox-onboarding.sh --no-build
```

Uses committed repo-root [`.dockerignore`](../../.dockerignore) so `hermes/`, `.venvs/`, and `**/.venv/` are never baked into the image. Do not run `docker compose -f private/docker-compose.sandbox.yml build` without that file.

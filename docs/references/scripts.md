# Scripts reference

All scripts in [scripts/](../../scripts/). Run from repo root unless noted.

| Script | Purpose | When to run |
|--------|---------|-------------|
| `setup.sh` | Clone Hermes into `hermes/`, adapter venv, Hermes venv, plugin, config copies | First-time bootstrap; after fresh clone |
| `ensure-hermes.sh` | Verify or clone upstream Hermes at lock pin | Called by setup/update; manual if `hermes/` missing |
| `update-hermes.sh` | Fetch/pull Hermes clone, refresh venv, reinstall plugin | When bumping Hermes version |
| `install-hermes-plugin.sh` | Symlink HCX provider into `~/.hermes/plugins/` | After setup; after plugin changes |
| `start-adapter.sh` | HCX on loopback with supervisor | Daily use; before Hermes chat |
| `start-voice.sh` | Voice sidecar on `:8767` | After adapter up; optional |
| `setup-voice.sh` | Voice venv + deps | Once before first voice use |
| `doctor.sh` | `/health`, models, optional chat smoke; Hermes pin hint | After config changes; debugging |

## Agent constraints

- Agents **do not run** git or deployment scripts that mutate remotes.
- Agents **may suggest** these commands in chat for the user.
- `start-*.sh` scripts manage PIDs — tests must not invoke them (see local test harness).

## Related

- Human quick start: [README.md](../../README.md)
- Deploy flow: [PRE-COMMIT-CHECKLIST.md](../../PRE-COMMIT-CHECKLIST.md)

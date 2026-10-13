# Windows via WSL2

Construct-Zero is bash-first. On Windows, run CZ **inside WSL2 Ubuntu** (22.04+ recommended), not in native PowerShell.

## Install path

1. Enable [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) and install **Ubuntu**.
2. Open the Ubuntu terminal and install CZ in an empty folder:

   ```bash
   mkdir ~/construct-zero && cd ~/construct-zero
   curl -fsSL https://raw.githubusercontent.com/AnishSukhramani/construct-zero/main/install.sh | bash
   ./construct-zero init
   ./construct-zero start
   ./construct-zero doctor
   ```

3. Run **Hermes in the same WSL distro** (`./construct-zero chat`). Keep `adapter.host: 127.0.0.1`.

## Cline on Windows

Cline runs on Windows; the adapter runs in WSL. In default WSL2 NAT mode, `http://127.0.0.1:<port>/v1` from Windows often reaches the WSL listener. If it does not:

- From WSL: `hostname -I | awk '{print $1}'` and try `http://<wsl-ip>:8765/v1` in Cline **only on your LAN** — CZ still binds **loopback inside WSL**; do not set `0.0.0.0`.
- Windows-side-only clients without WSL are **not supported in v1**.

## Known limits

- No Windows CI; this path is community-tested.
- Voice sidecar expects Linux/macOS audio tooling (`ffmpeg`, etc.).
- `./construct-zero doctor --certify` reports WSL as an **advisory** note (see [docs/certified.md](../certified.md) after certify is enabled).

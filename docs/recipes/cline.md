# Cline (VS Code) on Construct-Zero

Use your **Cursor plan** for inference through CZ’s OpenAI-compatible endpoint. CZ does not resell models; usage bills your Cursor subscription.

## 1. Start CZ

```bash
./construct-zero start
./construct-zero doctor --client=cline
```

Fix any `FAIL` lines before continuing.

## 2. Cline settings

**Settings → API Provider → OpenAI Compatible**

| Field | Value |
|-------|--------|
| **Base URL** | `http://127.0.0.1:8765/v1` (or the URL from doctor — uses your `CZ_PORT`) |
| **API Key** | Your `adapter.api_key` if set; otherwise any placeholder such as `unused`. **Never** paste `CURSOR_API_KEY` here. |
| **Model ID** | `auto`, or any id from `GET /v1/models` |
| **Context Window Size** | Set explicitly to **200000** (do not exceed **256000**) |
| **Supports images** | Off |
| **Supports prompt caching** | Off |

## 3. Honest limits

| Topic | Behavior |
|-------|----------|
| Streaming | Cursor backend streams incrementally when the SDK exposes deltas; some clients still buffer. |
| Images | Dropped — prompts are flattened to text (`X-CZ-Warning: images-dropped` when image parts are sent). |
| Usage | Token counts appear when the Cursor SDK reports them; otherwise `usage` may be missing or estimated. |
| Tools | OpenAI `tools` / `tool_calls` are supported via tool parking; Cline’s behavior depends on Cline version and model. |
| Billing | Requests use the official `cursor-sdk` in **ask** mode with **your** `CURSOR_API_KEY`. |

## 4. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Doctor `FAIL`: adapter not reachable | Run `./construct-zero start`; confirm loopback port in `.env`. |
| Doctor `FAIL C2`: model missing | Use `auto` or pick a model from `/v1/models`. |
| Doctor `FAIL C3` / chat 502 | Run `./construct-zero doctor` (no flags); fix `CURSOR_API_KEY` in `.env` and restart. |
| Doctor `FAIL C5` auth | Set Cline’s API Key to match `adapter.api_key` in config. |
| 401 from CZ | Set Cline API Key to match adapter bearer auth, or remove `adapter.api_key`. |
| Slow first token | Normal for tool-heavy turns; check Cursor dashboard for plan limits. |

Record a new client shape for CI: `scripts/ci/record-client-fixture.sh` (maintainers).

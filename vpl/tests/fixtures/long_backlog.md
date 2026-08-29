Here are sixteen concrete improvements for your voice sidecar backlog, grouped by theme. The full list stays on your screen while we walk through it in layers.

1. Add session TTL and cleanup so navigation state does not leak across days.
2. Fix MediaRecorder finalize so webm blobs are not truncated on stop.
3. Store supervisor PID separately from child PID in start-voice.sh.
4. Expose bucket chips in the hold-to-talk UI for tap-to-select navigation.
5. Add POST /nav for accessibility without microphone re-prompts.
6. Layer long Hermes replies with orient-map-deepen instead of reading everything.
7. Keep reply_full verbatim on screen while speak_text uses source spans only.
8. Skip Hermes on navigation turns when an active session is in WAIT phase.
9. Fuzzy-match bucket labels from short STT transcripts like workflow or second.
10. Add HCX_VPL_* env toggles in .env.example for threshold and bucket caps.
11. Ship hcx-vpl as a standalone package usable without the voice sidecar.
12. Regression-test sixteen-item fixtures for four-bucket chunking behavior.
13. Document plug-and-play BrainBackend protocol for non-Hermes backends.
14. Preload STT and TTS optionally via HCX_VOICE_PRELOAD for faster first turn.
15. Tunnel loopback :8767 over SSH for VPS hold-to-talk without public bind.
16. Run pytest for vpl and voice in CI to guard navigation and passthrough paths.

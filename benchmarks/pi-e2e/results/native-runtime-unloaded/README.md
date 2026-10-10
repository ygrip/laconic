# Excluded attempt — direct `.mjs` CLI resource not loaded

Stopped after inspecting the first runtime log-triage session: its direct `python3 diagnose.py` result retained all 42,387 bytes, there was no recovery store, and no runtime filtering occurred. Although `loadExtensions([path])` can load `.mjs` directly, Pi 1.1.0's CLI package/resource resolver does not classify this path as an extension. This attempt used `--extension runtime/adapters/pi.mjs`; its manifest records intended isolation/activation, not actual runtime availability. Merely adding an unknown name to `--tools` did not make the tool available.

All completed sanitized sessions are retained. They are **not runtime-treatment evidence** and are excluded from comparative claims; interrupted sessions were not published as completed runs. The corrected runner uses a temporary `.ts` entry and performs actual CLI `session_start` preflight audits for each arm before any provider inference. See `../native-runtime/`.

The installed-loader smoke and deterministic processor replay here remain valid for their narrower scope. Neither demonstrates CLI E2E activation in this attempt.

# Incomplete benchmark attempt — not used for claims

This attempt was stopped during usage-task runs after discovering a harness mistake: `--tools read,bash,edit,write` restricted active tools and excluded the extension's registered `laconic_read_result` tool. Runtime filtering was requested, but actual CLI loading was not yet audited and recovery was not explicitly active. Later investigation also showed that the direct `.mjs` CLI resource used here was ignored. The manifest described intended recovery availability, not this mistaken activation.

Completed sanitized runs are retained as evidence, but this incomplete/unbalanced attempt must not be aggregated or substituted for the corrected benchmark. No log-triage sessions were completed. The corrected runner explicitly includes `laconic_read_result` in runtime/both arms; fresh results live in `../native-runtime/`.

`pi-setup-verification.json` independently verifies the installed loader and registered tool; it does not establish the active tool list in these aborted provider sessions.

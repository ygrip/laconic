Fixed `usage_summary.py`. It previously counted assistant streaming records as calls, added reasoning to output again, and trusted supplied totals. It now counts only completed assistant `message_end` records and computes `totalTokens` from input, output, cacheRead, and cacheWrite.

The diagnostic log identified a stale-cache reconciliation failure for cedar, batch 463, with 17 lost calls; I recorded it in `incident.json` without changing `diagnose.py`.

Verification: all 7 tests pass. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This is fixture verification, not live-provider or production verification.

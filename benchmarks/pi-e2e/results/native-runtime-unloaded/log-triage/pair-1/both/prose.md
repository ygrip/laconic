The reconciliation log identified a stale-cache incident for cedar in batch 463, with 17 lost calls. I recorded it in `incident.json` and did not modify `diagnose.py`.

`usage_summary.py` previously counted assistant records before completion and added reasoning to output, risking double-counting. It now counts only completed assistant `message_end` records and computes `totalTokens` from input, output, cacheRead, and cacheWrite. Regression tests cover the exclusions, missing usage, and the CLI.

Verification: all 7 tests passed. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This fixture check is not live-provider or production verification.

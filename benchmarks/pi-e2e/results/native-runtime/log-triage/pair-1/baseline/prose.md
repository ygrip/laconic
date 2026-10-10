The reconciliation log identified a **stale-cache** incident for customer cedar, batch 463, with 17 lost calls. I recorded it in `incident.json`; `diagnose.py` was not changed.

In `usage_summary.py`, the cause of double-counting was that any assistant record could count as a call, including streaming records. It also added reasoning to output and trusted supplied `totalTokens`. The repair counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields, and computes `totalTokens` from those sums. Regression tests were added in `test_usage_summary.py`.

Verification: all 3 tests pass. The CLI on `session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. This verifies the fixture only, not live-provider or production behavior.

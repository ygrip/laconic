The summarizer was counting assistant records regardless of event type or completion status, adding reasoning to output again, and trusting supplied `totalTokens`. In `usage_summary.py`, it now counts only completed assistant `message_end` records, sums the four usage fields with missing values treated as zero, and computes `totalTokens` from those sums.

The diagnosis log identified a stale-cache reconciliation failure for cedar, batch 463, with 17 lost calls; I recorded it in `incident.json` without changing `diagnose.py`.

Verification: all 8 tests pass. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This verifies the fixture only, not live-provider or production behavior.

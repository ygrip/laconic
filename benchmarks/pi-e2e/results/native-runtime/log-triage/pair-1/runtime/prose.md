The reconciliation log identified a stale-cache incident for customer `cedar`, batch 463, with 17 lost calls. I recorded it in `incident.json` without changing `diagnose.py`.

`usage_summary.py` was counting assistant records regardless of event type or completion status, adding reasoning to output again, and trusting supplied `totalTokens`. It now counts only completed assistant `message_end` records, sums the four usage fields with missing values treated as zero, and computes the total from those sums. Regression tests cover those cases and blank-line CLI input.

Verification: all 7 tests pass. The CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This verifies the fixture and tests only, not live-provider or production behavior.

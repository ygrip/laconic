Recovered the failed reconciliation from the partial diagnostic log and wrote `incident.json`: customer `cedar`, batch `463`, reason `stale-cache`, lost calls `17`. `diagnose.py` was not changed.

The summarizer was counting non-final assistant events, adding reasoning to output again, and trusting supplied `totalTokens`. Updated `usage_summary.py` to count only completed assistant `message_end` records with an allowed stop reason, sum the four usage fields, and derive `totalTokens` from those sums. Added regression tests in `test_usage_summary.py`.

Verification: all 7 tests pass. The CLI check against `session.jsonl` produced `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. This verifies the fixture and tests only, not live-provider or production behavior.

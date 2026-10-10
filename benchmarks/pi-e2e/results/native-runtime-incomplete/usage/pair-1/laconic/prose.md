Fixed `usage_summary.py`: it now counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields, and computes `totalTokens` from those sums. Previously it counted streaming records, added reasoning to output again, and trusted supplied totals.

Added regression tests. All 7 tests pass; the CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification is fixture-based, not live-provider or production verification.

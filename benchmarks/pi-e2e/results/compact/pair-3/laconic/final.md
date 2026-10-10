Fixed `usage_summary.py`: it now counts only completed assistant `message_end` records with an allowed stop reason, including those without usage. It sums the four usage fields and derives `totalTokens` from them, avoiding double-counted reasoning and untrusted supplied totals.

All 6 tests pass. The CLI reports `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This verifies the fixture, not live-provider or production sessions.

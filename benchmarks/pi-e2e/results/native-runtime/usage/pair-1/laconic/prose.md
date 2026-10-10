Fixed `usage_summary.py` to count only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. It sums the four usage fields and computes `totalTokens` from them. The previous code counted streaming records, added reasoning to output, and trusted supplied totals.

Verification: 8 tests pass, including new regression coverage. The CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This fixture check does not verify live-provider or production behavior.

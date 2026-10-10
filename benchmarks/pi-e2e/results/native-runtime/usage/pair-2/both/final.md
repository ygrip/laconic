Fixed `usage_summary.py` to count only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. The previous code also counted streaming records, added reasoning to output again, and trusted supplied totals. It now sums the four usage fields and derives `totalTokens` from them.

Added regression tests. All 7 tests pass. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification used tests and a fixture, not a live provider or production session.

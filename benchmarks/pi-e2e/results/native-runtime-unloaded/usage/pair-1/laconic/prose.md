Fixed `usage_summary.py` to count only completed assistant `message_end` records with stop reason `stop`, `toolUse`, or `length`. Previously it also counted streaming records, added reasoning to output, and trusted supplied token totals. It now sums the four usage fields and computes `totalTokens` from them.

Added regression tests. All 8 tests pass, and the CLI reports `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This verifies the fixture, not live-provider or production behavior.

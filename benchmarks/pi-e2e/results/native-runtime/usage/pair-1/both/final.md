Fixed `usage_summary.py` to count only completed assistant `message_end` records. The previous code counted other assistant events, added reasoning to output again, and trusted supplied totals; it now sums the four usage fields and derives `totalTokens` from them.

Added regression coverage in `test_usage_summary.py`. All 8 tests pass, and the CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification is limited to tests and this fixture, not live-provider or production sessions.

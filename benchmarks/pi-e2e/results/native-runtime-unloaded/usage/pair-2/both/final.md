Fixed `usage_summary.py` to count only completed assistant `message_end` records. The bug counted streaming records and added reasoning to output again; it also trusted supplied totals. The summarizer now sums input, output, cacheRead, and cacheWrite, treats missing usage as zero, and derives `totalTokens` from those four fields.

Added regression tests. All 7 tests pass, and the CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification used the fixture, not a live provider or production session.

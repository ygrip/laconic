The summarizer was counting assistant streaming records as calls, adding reasoning to output again, and trusting supplied `totalTokens` values. Those behaviors could double-count usage.

I updated `usage_summary.py` to count only completed assistant `message_end` records with `stopReason` of `stop`, `toolUse`, or `length`. It sums the four usage fields, treats missing fields as zero, and computes `totalTokens` from those sums. Regression tests cover filtering, missing usage, misleading totals, reasoning, and blank-line CLI input.

Verification: all 7 tests passed. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This verifies the fixture, not live-provider or production behavior.

The summarizer counted assistant streaming records as calls and used a supplied `totalTokens` value, while omitting cache usage and adding reasoning to output again. That could double-count tokens.

I changed `usage_summary.py` to count only completed assistant `message_end` records with stop reason `stop`, `toolUse`, or `length`. It now sums the four usage fields and computes `totalTokens` from them. Regression tests cover filtering, absent usage, reasoning, supplied totals, and blank lines in the CLI.

Verification: all 6 tests passed. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification is limited to tests and this fixture; it is not live-provider or production verification.

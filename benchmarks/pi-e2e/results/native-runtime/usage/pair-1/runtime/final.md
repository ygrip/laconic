Fixed `usage_summary.py`. The cause was that it counted any assistant record, including streaming updates, added reasoning to output, and trusted the supplied `totalTokens` while omitting cache usage.

It now counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields with missing fields treated as zero, and computes `totalTokens` from those sums. Regression tests cover filtering, missing usage, token accounting, and the CLI.

Verification: all 7 tests pass. `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. Verification is limited to tests and the supplied fixture; it does not establish live-provider or production behavior.

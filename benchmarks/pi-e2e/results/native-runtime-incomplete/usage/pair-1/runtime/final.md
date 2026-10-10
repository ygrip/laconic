The summarizer was counting non-final assistant events, adding reasoning to output a second time, and trusting supplied `totalTokens` while omitting cache usage.

I changed `usage_summary.py` to count only completed assistant `message_end` records with an allowed stop reason, sum the four usage fields, and derive `totalTokens` from those sums. I also added regression tests for excluded records, missing usage, misleading totals, and blank CLI lines.

Verification: all 7 tests pass. `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. This verifies the fixture and tests only; live-provider and production behavior remain unverified.

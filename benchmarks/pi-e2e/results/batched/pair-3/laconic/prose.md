Fixed `usage_summary.py`. It previously counted assistant records regardless of event type or stop reason, added reasoning to output again, and trusted supplied totals. It now counts only completed assistant `message_end` records, sums the four usage fields, and computes `totalTokens` from those sums.

Verification: 7 tests pass, including new regressions. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This verifies the fixture, not live-provider or production behavior.

The cause was that `usage_summary.py` counted assistant streaming records as calls, added reasoning to output again, and trusted supplied `totalTokens` while omitting cache usage.

It now counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields (defaulting missing values to zero), and derives `totalTokens` from those sums. Regression tests cover filtering, missing usage, token accounting, and blank-line CLI input.

Verification: all 7 tests pass. `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. This verifies the fixture, not live-provider or production behavior.

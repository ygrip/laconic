The summarizer counted assistant streaming events as calls, added reasoning to output even though it was already included, and trusted supplied `totalTokens`.

Updated `usage_summary.py` to count only completed assistant `message_end` records with an allowed stop reason, sum the four usage fields, and calculate `totalTokens` from those sums. Added regression tests in `test_usage_summary.py`.

Verification: all 7 tests pass. The CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This verifies the fixture, not live-provider or production behavior.

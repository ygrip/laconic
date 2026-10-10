The summarizer counted assistant streaming records as calls, added reasoning to output a second time, and trusted supplied `totalTokens` while omitting cache usage.

Updated `usage_summary.py` to count only completed assistant `message_end` records with an allowed stop reason. It now sums input, output, cacheRead, and cacheWrite, then computes totalTokens from those four fields. Added regression tests in `test_usage_summary.py`.

Verification: all 8 tests pass. The CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This verifies the fixture and tests only, not live-provider or production sessions; malformed records and non-integer usage values remain outside the specified input contract.

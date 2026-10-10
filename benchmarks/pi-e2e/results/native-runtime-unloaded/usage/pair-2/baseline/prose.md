**Cause:** The summarizer counted assistant streaming records as calls, added reasoning to output again, and trusted the supplied `totalTokens`.

**Changed:** `usage_summary.py` now counts only completed assistant `message_end` records with an allowed stop reason. It sums the four usage fields, treating missing fields as zero, and computes `totalTokens` from those sums. Added regression tests in `test_usage_summary.py`.

**Verification:** All 8 tests pass. The CLI check against `session.jsonl` returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`.

**Limitation:** Verification used tests and the local fixture, not a live provider or production sessions.

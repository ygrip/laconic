**Cause:** The summarizer counted assistant streaming records as calls, added reasoning to output again, and trusted the supplied `totalTokens` value.

**Changed:** `usage_summary.py` now counts only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. It sums the four usage fields and computes `totalTokens` from them. Regression tests cover filtering, missing usage, double-counting, and the CLI.

**Verified:** All 7 tests pass. `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`.

**Limitation:** Verification used tests and the provided fixture, not a live provider or production sessions.

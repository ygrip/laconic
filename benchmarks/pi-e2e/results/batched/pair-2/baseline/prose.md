**Cause:** The summarizer counted assistant streaming and error records, added reasoning to output a second time, and trusted the supplied `totalTokens` while omitting cache usage.

**Changed:** `usage_summary.py` now counts only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. It sums the four usage fields and computes `totalTokens` from them. Regression tests cover filtering, missing usage, token accounting, and blank-line CLI input.

**Verification:** All 4 tests pass. Running `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`.

**Limitation:** Verification used tests and the supplied fixture, not a live provider or production sessions.

**Cause:** The summarizer counted any assistant record, including streaming updates, added reasoning to output, and trusted supplied `totalTokens`. That could double-count usage.

**Changed:** `usage_summary.py` now counts only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. It sums the four usage fields and computes `totalTokens` from them. Regression tests cover filtering, missing usage, totals, and blank-line CLI input.

**Verified:** All 8 tests pass. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`.

**Limitation:** Verification used tests and the supplied fixture, not a live provider or production sessions.

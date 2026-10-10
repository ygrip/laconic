**Cause:** The summarizer counted assistant records regardless of event type or completion status, added reasoning to output again, and trusted the supplied `totalTokens`.

**Changed:** `usage_summary.py` now counts only completed `message_end` assistant messages with `stopReason` of `stop`, `toolUse`, or `length`. It sums the four usage fields, treating missing fields as zero, and computes `totalTokens` from those sums. Regression tests cover filtering, missing usage, double-counting, and the CLI fixture.

**Verification:** All 4 tests pass. `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`.

**Limitation:** Verification uses the supplied fixture and tests, not a live provider or production sessions.

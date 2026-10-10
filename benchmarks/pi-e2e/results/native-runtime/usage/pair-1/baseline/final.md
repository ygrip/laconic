**Cause:** The summarizer counted every assistant record, including streaming updates, added reasoning to output again, and trusted the supplied `totalTokens`.

**Changed:** `usage_summary.py` now counts only completed `message_end` assistant messages with stop reason `stop`, `toolUse`, or `length`. It sums the four usage fields, treating missing fields as zero, and computes `totalTokens` from those sums. Regression tests cover filtering, missing usage, and misleading totals.

**Verification:** All 7 tests pass. The CLI produced one JSON object for `session.jsonl`: `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`.

**Limitation:** Verification used tests and the supplied fixture, not a live provider or production session.

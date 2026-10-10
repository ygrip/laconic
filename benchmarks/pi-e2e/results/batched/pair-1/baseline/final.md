**Cause:** The summarizer counted assistant records regardless of event type or completion status, added reasoning to output, and trusted the supplied `totalTokens`. That could double-count usage.

**Changed:** `usage_summary.py` now counts only completed assistant `message_end` records, sums the four usage fields with missing fields treated as zero, and computes `totalTokens` from those sums. Added regression tests in `test_usage_summary.py`.

**Verified:** All 3 tests pass. The CLI check against `session.jsonl` returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`.

Verification is limited to tests and the fixture; no live-provider or production behavior was checked.

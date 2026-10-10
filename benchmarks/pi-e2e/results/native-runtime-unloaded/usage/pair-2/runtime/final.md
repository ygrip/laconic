The summarizer was counting assistant streaming records as calls, adding reasoning to output even though it was already included, and trusting supplied `totalTokens` values. In `usage_summary.py`, it now counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields, and derives `totalTokens` from those sums.

Regression tests cover filtering, missing usage, double-counting, and blank-line CLI input. All 4 tests pass. Running `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`.

Verification is limited to tests and the supplied fixture; it does not establish live-provider or production behavior.

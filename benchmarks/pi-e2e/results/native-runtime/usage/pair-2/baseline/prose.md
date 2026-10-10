The summarizer was counting assistant streaming and pending records as calls, adding reasoning to output again, and trusting supplied token totals. `usage_summary.py` now counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields, and computes `totalTokens` from those sums.

Added regression tests. All 7 tests pass. The CLI check against `session.jsonl` returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`.

Verification is limited to tests and the fixture; it does not establish live-provider or production behavior.

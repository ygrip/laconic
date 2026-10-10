Fixed `usage_summary.py`. It previously counted assistant streaming records, added reasoning to output, and trusted supplied token totals. It now counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields, and computes `totalTokens` from those sums.

Regression suite: 3 tests passed. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification is limited to tests and this fixture; no live-provider or production session was checked.

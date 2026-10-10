Fixed `usage_summary.py`. It previously counted any assistant record, added `reasoning` to `output`, and trusted the supplied `totalTokens`, causing double-counting. It now counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields, and computes `totalTokens` from them.

All 7 tests pass. The CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification used the fixture, not a live provider or production session.

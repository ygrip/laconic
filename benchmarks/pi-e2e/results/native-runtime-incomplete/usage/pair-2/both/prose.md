Fixed `usage_summary.py`. It previously counted assistant records regardless of event type or stop reason, added reasoning to output, and trusted supplied totals—each could distort a session comparison. It now counts only completed assistant `message_end` records, sums the four usage fields, and computes `totalTokens` from that sum.

Verification: all 6 tests pass. The CLI reports `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This is fixture verification, not live-provider or production verification.

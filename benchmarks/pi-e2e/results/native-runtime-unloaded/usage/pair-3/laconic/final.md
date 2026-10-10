Fixed `usage_summary.py` to count only completed assistant `message_end` records. The previous code counted other assistant events, added reasoning to output again, and trusted supplied totals. It now sums the four usage fields and computes `totalTokens` from them.

Added regression tests. All 7 tests pass, and the CLI returns 2 calls and 245 total tokens for `session.jsonl`. Verification is limited to tests and this fixture; it is not live-provider or production verification.

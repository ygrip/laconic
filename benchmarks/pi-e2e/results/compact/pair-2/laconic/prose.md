Fixed `usage_summary.py` to count only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. The cause was counting other assistant events, adding reasoning to output again, and trusting supplied `totalTokens`. It now sums the four usage fields and computes `totalTokens` from them.

Added regression tests. All 6 tests pass. The CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification used tests and a fixture, not a live provider or production session.

Fixed `usage_summary.py` to count only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. Previously it counted other assistant events, added reasoning to output again, omitted cache usage, and trusted supplied totals. It now sums the four usage fields and computes `totalTokens` from them.

Added regression tests. All 7 tests pass, and the CLI returns one JSON object for `session.jsonl` with 2 calls and 245 total tokens. Verification used the fixture, not a live provider or production session.

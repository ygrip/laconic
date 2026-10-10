The summarizer was counting assistant streaming records as calls, adding reasoning to output even though it was already included, and trusting the supplied `totalTokens` value. It also omitted cache usage.

Updated `usage_summary.py` to count only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. It now sums the four usage fields, treating missing fields as zero, and derives `totalTokens` from those sums. Regression tests cover excluded records, missing usage, and double-counting.

Verification: `python3 -m unittest -v` passed (3 tests). The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification is limited to tests and this fixture; it does not establish live-provider or production behavior.

The summarizer counted any assistant record, including streaming updates, and added reasoning to output even though it was already included. It also trusted the supplied `totalTokens`.

Updated `usage_summary.py` to count only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. It now sums the four usage fields, treats missing fields as zero, and derives `totalTokens` from those sums. Added regression tests for filtering, missing usage, token accounting, and blank-line CLI input.

Verification: all 7 tests pass. The CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This is fixture verification only; live-provider and production behavior remain unverified.

Fixed `usage_summary.py`. It previously counted any assistant event, including streaming updates, added reasoning to output, and trusted supplied `totalTokens` while omitting cache usage.

It now counts only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`. Missing usage fields count as zero, and `totalTokens` is computed from input, output, cacheRead, and cacheWrite. The CLI is unchanged.

Verification: all 7 tests pass, including new regression tests. `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. This verifies fixture behavior only; it does not establish live-provider or production behavior.

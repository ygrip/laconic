Fixed `usage_summary.py`. It previously counted every assistant record, including streaming updates, added reasoning to output, and trusted supplied `totalTokens`; those behaviors could double-count usage.

It now counts only completed assistant `message_end` records with `stopReason` of `stop`, `toolUse`, or `length`. Missing usage fields count as zero, and `totalTokens` is computed from input, output, cacheRead, and cacheWrite. Added regression tests, including a blank-line CLI check.

Verification: all 8 tests pass. `python3 usage_summary.py session.jsonl` returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. Verification covers tests and the fixture only, not live-provider or production sessions.

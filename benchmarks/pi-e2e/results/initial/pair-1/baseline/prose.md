The summarizer counted assistant records before completion, added reasoning to output again, and trusted the supplied `totalTokens`. That could double-count usage.

I updated `usage_summary.py` to count only completed assistant `message_end` records with an allowed stop reason, sum the four usage fields, and derive `totalTokens` from them. I added regression tests in `test_usage_summary.py`.

Verification: all 8 tests pass. The CLI run against `session.jsonl` reports 2 calls and 245 total tokens. This verifies the fixture and tests only; it is not live-provider or production verification.

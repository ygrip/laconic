The summarizer was counting assistant records regardless of event type or completion status. It also added reasoning to output and trusted the supplied `totalTokens`, which could double-count usage.

Updated `usage_summary.py` to count only completed assistant `message_end` records, sum the four usage fields with missing values treated as zero, and calculate `totalTokens` from those fields. Added regression tests in `test_usage_summary.py`.

Verification: all 7 tests pass. The CLI on `session.jsonl` reports 2 calls and 245 total tokens. This verifies the fixture and tests only; live-provider and production behavior remain unverified.

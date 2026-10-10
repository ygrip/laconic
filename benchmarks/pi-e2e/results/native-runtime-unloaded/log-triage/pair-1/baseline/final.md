The cause was that `usage_summary.py` counted assistant records regardless of event type or completion status, added reasoning to output again, and trusted supplied token totals.

It now counts only completed assistant `message_end` records, sums the four usage fields, and computes `totalTokens` from those fields. I added regression tests and recorded the diagnosed incident in `incident.json`: cedar, batch 463, stale-cache, 17 lost calls.

Verification: all 7 tests pass. The CLI check against `session.jsonl` returned 2 calls and 245 total tokens. This is fixture verification only; live-provider and production behavior remain unverified.

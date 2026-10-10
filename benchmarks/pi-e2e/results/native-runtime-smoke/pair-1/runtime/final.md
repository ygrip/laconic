`diagnose.py` reported a stale-cache reconciliation failure for cedar, batch 463, with 17 lost calls. I recorded it in `incident.json`; the log contained the complete incident record.

The summarizer was counting assistant streaming records as calls and adding reasoning to output, while trusting supplied token totals. `usage_summary.py` now counts only completed assistant `message_end` records with an allowed stop reason, sums the four usage fields, and computes `totalTokens` from those sums. Regression tests cover filtering, missing usage, double-counting, and blank-line CLI input.

Verification: all 7 tests pass. The CLI result for `session.jsonl` is 2 calls and 245 total tokens. This is fixture verification only, not live-provider or production verification.

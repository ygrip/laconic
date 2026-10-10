The summarizer was counting assistant records regardless of event type or completion status, adding reasoning to output, and trusting the supplied `totalTokens`. That could double-count tokens and calls.

I updated `usage_summary.py` to count only completed assistant `message_end` records with an allowed stop reason, sum the four usage fields with missing values treated as zero, and compute `totalTokens` from those fields. I added regression tests and wrote `incident.json` from the diagnosis log: cedar, batch 463, stale-cache, 17 lost calls.

Verification: all 7 tests pass. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification is limited to tests and this fixture; it is not live-provider or production verification.

Fixed `usage_summary.py` and wrote `incident.json`. The reconciliation log identified cedar, batch 463, stale-cache, and 17 lost calls.

The summarizer previously counted non-final assistant records and added reasoning to output. It now counts only completed assistant `message_end` records and computes totals from input, output, cacheRead, and cacheWrite. Seven tests pass; the CLI returns 2 calls and 245 total tokens for `session.jsonl`.

Verification used tests and a fixture, not a live provider or production session.

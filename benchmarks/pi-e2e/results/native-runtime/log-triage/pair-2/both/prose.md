`usage_summary.py` counted assistant streaming records as calls and relied on supplied token totals, which could double-count usage. It now counts only completed assistant `message_end` records, sums the four usage fields, and derives `totalTokens` without adding reasoning separately.

The diagnostic log identified a stale-cache reconciliation incident; I recorded it in `incident.json` (cedar, batch 463, 17 lost calls). Seven tests pass, and the CLI reports 2 calls and 245 total tokens for `session.jsonl`. This verifies the fixture, not live-provider or production behavior.

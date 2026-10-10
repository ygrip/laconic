The summarizer was counting assistant streaming records as calls, adding reasoning to output again, and trusting the supplied `totalTokens`. `usage_summary.py` now counts only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`; it sums the four usage fields and derives `totalTokens` from them.

The diagnostic log identified a stale-cache reconciliation incident, recorded in `incident.json`: customer cedar, batch 463, 17 lost calls. `diagnose.py` was not changed.

Verification: all 4 regression tests pass. The CLI returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. This is fixture verification only, not live-provider or production verification.

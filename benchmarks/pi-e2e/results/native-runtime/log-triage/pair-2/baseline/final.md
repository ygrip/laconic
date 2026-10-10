The summarizer was counting assistant streaming records as calls, adding reasoning to output again, and trusting supplied `totalTokens`. In `usage_summary.py`, it now counts only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`, sums the four usage fields, and computes `totalTokens` from those sums.

The reconciliation log identified a stale-cache incident for cedar, batch 463, with 17 lost calls; I recorded it in `incident.json`. All 7 tests pass. The CLI check against `session.jsonl` returned 2 calls and 245 total tokens.

Verification is limited to the tests and fixture, not a live provider or production session.

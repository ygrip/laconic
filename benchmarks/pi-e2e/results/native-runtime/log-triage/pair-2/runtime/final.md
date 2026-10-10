The summarizer was double-counting because it accepted assistant streaming records as calls and added reasoning to output, where it was already included. It also trusted supplied `totalTokens` and omitted cache usage.

Updated `usage_summary.py` to count only completed assistant `message_end` records with an allowed stop reason, sum the four usage fields with missing values treated as zero, and compute `totalTokens` from those sums. Added regression tests and wrote the recovered reconciliation record to `incident.json`.

Verification: all 8 tests pass. The CLI check against `session.jsonl` returned `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. This verifies the fixture behavior only, not live-provider or production behavior.

Recovered the reconciliation incident from the partial diagnostic log and wrote `incident.json`: customer `cedar`, batch `463`, reason `stale-cache`, and `17` lost calls.

`usage_summary.py` was counting assistant records beyond completed message ends, adding reasoning twice, and trusting supplied totals. It now counts only completed assistant `message_end` records with the specified stop reasons, sums the four usage fields, and computes `totalTokens` from them. Regression tests cover filtering, missing usage, totals, and blank CLI lines.

Verification: all 7 tests pass. The fixture CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}`. This is fixture verification, not live-provider or production verification.

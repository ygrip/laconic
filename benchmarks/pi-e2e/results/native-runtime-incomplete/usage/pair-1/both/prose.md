Fixed `usage_summary.py`: it previously counted non-final assistant events, added reasoning to output, and trusted supplied `totalTokens`. It now counts only completed assistant `message_end` records, sums the four usage fields with missing values treated as zero, and computes the total from those sums.

Added regression coverage. All 8 tests pass; the CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification used a fixture, not a live provider or production session.

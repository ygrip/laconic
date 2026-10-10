The current code counts assistant records before checking whether they are completed `message_end` events. It also adds `reasoning` to output and uses the supplied `totalTokens`. I’ll fix the filters and totals, then add tests for those cases.

Fixed `usage_summary.py`. It now counts only completed assistant `message_end` records with stop reasons `stop`, `toolUse`, or `length`, including messages with no usage. It sums the four usage fields and computes `totalTokens` from them.

The cause was that the old code counted streaming records, added `reasoning` to output again, and trusted the supplied `totalTokens`.

All 3 regression tests pass. The CLI returns `{"calls": 2, "input": 150, "output": 35, "cacheRead": 50, "cacheWrite": 10, "totalTokens": 245}` for `session.jsonl`. Verification is limited to tests and this fixture; no live-provider or production check was performed.

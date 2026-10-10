# Benchmark summaries

Only aggregate totals, paired comparisons, and metric definitions are published. Execution scripts, raw sessions (`*.jsonl`), generated solutions, logs, and recovery artifacts remain local and are not tracked.

- `initial.json`, `compact.json`, `batched.json`: historical skill comparisons.
- `native-runtime-v2.json`: current engine; review (seeded-defect recall), noisy-log triage and usage workflows, per-task comparisons, recovery bytes, and deterministic processor replay.
- `native-runtime.json`: v1 engine, combined two-workflow comparison.
- `native-runtime-usage.json`, `native-runtime-log-triage.json`: workflow-specific comparisons.

Percentages describe these samples, not general guarantees. Provider token counts include cache categories. Cost is Pi catalog metadata, not billed cost. Some retained metric definitions describe how local evidence was measured/sanitized; they do not imply the underlying session artifacts are published.

Reports: [original](../pi-e2e-comparison.md), [optimization](../pi-e2e-optimization.md), [runtime and latency](../pi-e2e-runtime.md).

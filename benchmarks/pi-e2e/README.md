# Reproducible Pi E2E benchmark

This benchmark launches actual Pi CLI processes; it does not simulate replies or rewrite a baseline answer.

## Task and controls

The [task](prompt.txt) repairs a deliberately broken Python summarizer for Pi JSON session usage. This is a synthetic but relevant dogfood fixture, **not a bug discovered in Pi or Laconic**. A summarizer that counts streaming updates or adds reasoning twice would invalidate a skill comparison.

Both arms receive identical files and task requirements, use the same provider/model/thinking level, and have the same four built-in tools (`read`, `bash`, `edit`, `write`). Each run has a fresh temporary working directory and config. Installed extensions, MCP, context files, templates, themes, and discovered skills are disabled. Only credentials and optional provider-model configuration are copied to the temporary config; neither is published.

- **Baseline:** no skill.
- **Laconic:** `--no-skills --skill <directory>` and `/skill:laconic <task>` explicitly activate the snapshotted skill. This tests an activated skill, not automatic skill discovery.
- **Order:** baseline first in odd pairs; Laconic first in even pairs. Runs are sequential. This reduces, but does not eliminate, order/cache effects.
- **Checks:** an independent nine-check acceptance test and the agent's resulting test suite run after each session. The independent checks are not given to the agent.

The default is three pairs. There is no fixed random seed or temperature control. Samples on one task cannot establish a general effect or statistical significance.

## Run

Requires an authenticated Pi CLI and Python 3; the Python harness has no third-party dependencies. Runs consume your provider quota. Do not reuse an output directory.

```bash
python3 -m unittest discover -s benchmarks/pi-e2e -p test_benchmark.py -v
python3 benchmarks/pi-e2e/run.py --pairs 3 \
  --provider openai-codex --model gpt-6-sol --thinking medium \
  --output benchmarks/pi-e2e/results/my-run
python3 benchmarks/pi-e2e/analyze.py benchmarks/pi-e2e/results/my-run
```

Use `--agent-dir` for a nondefault Pi authentication/config directory. Use `--model` and `--provider` for another authenticated model. These results are specific to the recorded model and Pi version; different configurations need new runs.

## Measures

**Savings:** `100 × (baseline sum − Laconic sum) / baseline sum`. A negative result means Laconic used more. Use sums across equally sized arms, not an average of individual percentage changes.

**Conciseness:** final-answer words and all assistant-prose words, counted with the regex in `run.py`. Code tool arguments and private reasoning are excluded. A shorter answer is not necessarily a better answer.

**Clarity:** a transparent manual five-point rubric applied to the final answer:

1. The first non-heading sentence states the outcome.
2. The cause is explained concretely (event filtering and/or accounting bug).
3. Changes are concrete enough to identify the fix.
4. Verification includes an identifiable command/result, not just “done”.
5. A fixture/live-provider or production limitation is explicitly preserved.

Each criterion is 0 or 1. This is an author-rated evidence/clarity proxy, not blinded human preference, a readability standard, or a validated clarity instrument. Correctness is evaluated separately by independent acceptance checks. Do not silently penalize useful detail.

**Tokens:** sum provider-reported `input`, `output`, `cacheRead`, and `cacheWrite` once per `message_end` assistant record. Total is the sum of those four categories. Reasoning is already included in output; never add it again. Reported `totalTokens` is retained for cross-checking. Input-context volume is `input + cacheRead + cacheWrite`, including replayed context. Cached tokens are not priced like uncached tokens; token savings are not dollar savings. The analysis also sums Pi's `usage.cost.total` as `estimated_cost_usd`. This is model-catalog cost metadata, not a provider invoice or subscription charge; catalog prices may not reflect the actual routed model or your plan. Skill injection overhead is included. No follow-up model calls are needed after the task; independent verification uses local Python only.

**Tool-output efficiency:** original UTF-8 text bytes across completed `toolResult` messages, plus tool-call count and a per-tool breakdown. Includes file reads, shell/test output, and edit/write acknowledgments. Measures visible tool-result payload, **not tokens**, tool envelopes, images, tool arguments, or private reasoning. Pi does not give per-tool tokenizer usage. Total provider input-context tokens independently measure the whole session, not tool output in isolation. `9 acceptance checks / tool-result KB` is a within-task efficiency proxy: equal correctness with fewer returned bytes is preferable, but it is not a universal measure of useful information.

The skill changes requested tool scope; no output-limiting extension or interception hook is enabled. Inspect actual calls in `events.jsonl` rather than attributing every byte difference to deliberate filtering. A result containing the word “truncat” is flagged heuristically, not treated as proof of truncation.

## Evidence and publication

Recorded results include the [original skill](results/initial/), [compact revision](results/compact/), and [batched revision](results/batched/). Each revision has a fresh matched baseline. All results, including unsuccessful optimization attempts, are retained. These are exploratory revisions tuned after seeing earlier results, not a preregistered or held-out evaluation. See the [optimization report](../../docs/pi-e2e-optimization.md).

Each result directory contains:

- `manifest.json`: Pi version, configuration, activation/isolation policy and hashes.
- `SKILL.md`: exact skill snapshot.
- `pair-N/{baseline,laconic}/events.jsonl`: completed assistant/tool messages, including tool arguments, results and provider usage.
- `final.md` and `prose.md`: actual final answer and all assistant prose.
- `solution/`: agent-modified code, tests and input fixture.
- `verification.json`: independent checks and local suite results.
- `metrics.json` and `summary.json`: per-run measurements and recomputed aggregates.

Streaming deltas are omitted to prevent duplication. Private reasoning and opaque replay signatures are removed. Temporary paths are replaced with `<WORKSPACE>`, `<SKILL>`, and `<TEMP>`. Original tool-byte totals are captured before path replacement; per-tool counts from published events can differ slightly in bytes. These are sanitized completed-message transcripts, not full raw provider traces. No credentials are published.

The deliberately broken [fixture](fixture/) fails three of its original four tests. Do not include it in a general passing-suite discovery command. Use the explicit harness command above or test a recorded `solution/` directory.

The user-facing findings and manually scored clarity evidence are in [the E2E report](../../docs/pi-e2e-comparison.md).

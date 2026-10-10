# Laconic in real Pi sessions: E2E comparison

> Historical result for the original 4,328-byte skill. The current skill uses the tested compact revision; see [optimization results](pi-e2e-optimization.md). This experiment remains unchanged as evidence.

**Result: slightly shorter, outcome-first final answers—but no net token savings on this task.** Laconic returned less task-related tool output, yet rereading the skill outweighed that reduction. These are measured results, including the unfavorable ones.

## Experiment

On **2026-10-10 UTC**, we ran **six real Pi CLI sessions: three baseline/Laconic pairs**, using Pi **1.1.0**, `openai-codex/gpt-6-sol`, and `medium` thinking. Each session repaired a deliberately broken Python utility that summarizes Pi usage events, added regression tests, ran tests, and checked a JSONL fixture. This is a synthetic dogfood task, not a discovered upstream bug.

Fresh workspaces/configs received identical files and task requirements. Both arms used `read,bash,edit,write`; extensions, MCP, global instructions, and discovered skills were disabled. Laconic alone was registered and explicitly activated through `/skill:laconic`. Order alternated across pairs. No tool-output limiting extension was used.

All **six solutions passed 9/9 independent acceptance checks**, and all resulting test suites passed. Neither arm verified a live provider or production deployment. [Full methodology, formulas, scoring rubric and reproduction commands](../benchmarks/pi-e2e/README.md).

## Measured totals

Totals combine three sessions per arm. “Change” is relative to baseline; an increase is **not** a saving.

| Measure | Without Laconic | With Laconic | Change |
| --- | ---: | ---: | ---: |
| Final-answer words | 289 | 277 | **4.2% fewer** |
| All assistant-prose words | 289 | 314 | **8.7% more** |
| Manual clarity/evidence rubric | 12/15 | 15/15 | +3 points |
| Independent acceptance checks | 27/27 | 27/27 | Equal |
| Output tokens, including code/tool arguments/reasoning | 4,416 | 4,643 | **5.1% more** |
| Uncached input tokens | 17,108 | 25,613 | **49.7% more** |
| Cache-read tokens | 36,608 | 59,392 | **62.2% more** |
| Total input-context tokens | 53,716 | 85,005 | **58.2% more** |
| Total tokens, including cache categories | 58,132 | 89,648 | **54.2% more** |
| Model calls | 18 | 18 | Equal |
| Tool calls | 27 | 31 | **14.8% more** |
| All tool-result text bytes | 15,723 | 26,245 | **66.9% more** |
| Tool-result bytes excluding skill reads | 15,723 | 13,261 | **15.7% fewer** |
| Pi process elapsed seconds | 77.014 | 113.111 | **46.9% more** |

Both arms reported zero cache-write tokens. Computed token totals match Pi's reported `totalTokens` for every run. Token totals are usage volume, **not dollar cost**; cached and uncached tokens have different pricing. Output tokens are not final-answer tokens. Final words are a separate textual measure.

## Individual sessions

| Pair | Final words: baseline → Laconic | Total tokens: baseline → Laconic | Tool bytes: baseline → Laconic | Acceptance |
| --- | ---: | ---: | ---: | --- |
| 1 | 86 → 92 | 20,695 → 30,746 | 6,789 → 8,601 | Both 9/9 |
| 2 | 108 → 94 | 18,906 → 29,807 | 4,520 → 8,950 | Both 9/9 |
| 3 | 95 → 91 | 18,531 → 29,095 | 4,414 → 8,694 | Both 9/9 |

Final answers were shorter in two pairs, longer in one. Total tokens and gross tool-output bytes increased in **all three** pairs. Do not interpret the small aggregate word reduction as a consistent or general token-saving effect.

## Tool-output efficiency: what actually happened

Each Laconic session called `read` on `<SKILL>/SKILL.md`, returning **4,328 bytes** even though `/skill:laconic` had already injected the skill into the user prompt. The published user message and tool call show both operations. Across three sessions, these reads added **12,984 tool-result bytes** and **three tool calls**. The remaining one-call increase was a shell call in pair 1.

| Tool | Baseline calls | Laconic calls | Baseline text bytes* | Laconic text bytes* |
| --- | ---: | ---: | ---: | ---: |
| `read` | 9 | 12 | 8,028 | 21,012 |
| `bash` | 12 | 13 | 7,173 | 4,900 |
| `edit` | 6 | 6 | 333 | 333 |

\*Per-tool bytes are recomputed from sanitized published transcripts. Baseline shell output included temporary paths; path replacement reduces the per-tool sum by 189 bytes compared with the original gross measurements above. Laconic's per-tool sum is unchanged. Original gross bytes were measured before sanitization.

Task-related reads returned the same aggregate volume: **8,028 bytes** per arm after subtracting the skill reads. Shell-result volume was lower in Laconic's published transcripts, while edit acknowledgments were equal. This is compatible with less verbose shell output, but the agents also wrote different tests and used different commands; it is **not a controlled comparison of one identical tool call**.

Gross verified-check efficiency was **1.72 checks per 1,000 tool-result bytes** without Laconic versus **1.03** with it. Excluding skill reads, Laconic reached **2.04**. This proxy only compares equal acceptance criteria on this task; it does not measure universal information quality.

The net result matters: **skill loading/rereading made overall tool-output efficiency worse**, despite the narrower task-only byte reduction. Skill injection also costs context tokens independently of tool output. The 58.2% increase in total input-context tokens includes skill content, repeated context, different generated code/tests, and other session variation; it cannot be attributed entirely to rereading.

No claim of exact tool-token savings is made. Pi reports tokens at the model-request level, not for individual tool results. Bytes are directly measured payload volume, not a tokenizer estimate.

## Actual outputs and clarity assessment

Here are the first sentences from pair 2, quoted without rewriting:

**Without Laconic:**

> The summarizer counted any assistant record, including streaming updates, and added reasoning to output even though it was already included.

**With Laconic:**

> Fixed `usage_summary.py`.

Read the complete [baseline final answer](../benchmarks/pi-e2e/results/initial/pair-2/baseline/final.md) and [Laconic final answer](../benchmarks/pi-e2e/results/initial/pair-2/laconic/final.md). All six final answers and all assistant prose are published, not just the favorable pair.

The rubric awards one point each for outcome first, concrete cause, identifiable changes, explicit verification, and preserved limitations. Every answer explained the cause, fix, tests/CLI results and fixture limitation. Baseline answers began with the cause; Laconic answers began with the fix.

| Final answer | Outcome first | Cause | Changes | Verification | Limitations | Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Pair 1 baseline | 0 | 1 | 1 | 1 | 1 | 4/5 |
| Pair 1 Laconic | 1 | 1 | 1 | 1 | 1 | 5/5 |
| Pair 2 baseline | 0 | 1 | 1 | 1 | 1 | 4/5 |
| Pair 2 Laconic | 1 | 1 | 1 | 1 | 1 | 5/5 |
| Pair 3 baseline | 0 | 1 | 1 | 1 | 1 | 4/5 |
| Pair 3 Laconic | 1 | 1 | 1 | 1 | 1 | 5/5 |

This is **unblinded author scoring**, not independent human evaluation or a validated clarity score. The improvement is specifically outcome-first presentation—not better correctness or proof that readers understand the answer faster. A cause-first answer can also be clear. Laconic pair 1 added progress prose, so final-only conciseness hides an increase in total prose.

## Evidence and reproduction

- [Exact task](../benchmarks/pi-e2e/prompt.txt), [starting fixture](../benchmarks/pi-e2e/fixture/), and [skill snapshot](../benchmarks/pi-e2e/results/initial/SKILL.md).
- [Manifest/configuration and hashes](../benchmarks/pi-e2e/results/initial/manifest.json).
- [All six per-run measurements](../benchmarks/pi-e2e/results/initial/metrics.json).
- [Recomputed aggregates, pair percentages and tool breakdowns](../benchmarks/pi-e2e/results/initial/summary.json).
- [Pair 1 transcripts/solutions](../benchmarks/pi-e2e/results/initial/pair-1/), [pair 2](../benchmarks/pi-e2e/results/initial/pair-2/), [pair 3](../benchmarks/pi-e2e/results/initial/pair-3/).
- [Runner](../benchmarks/pi-e2e/run.py), [analysis script](../benchmarks/pi-e2e/analyze.py), and [harness tests](../benchmarks/pi-e2e/test_benchmark.py).

Transcripts preserve completed messages, tool arguments/results, and usage. Streaming duplicates, private reasoning, opaque signatures and temporary absolute paths are omitted/replaced. Credentials are never copied into artifacts. These are actual sanitized E2E records, not fabricated examples.

## What this establishes—and what it does not

For this short dogfood task and model, Laconic changed the opening structure and slightly reduced final-answer words. It **did not save total tokens**, all prose, latency, or gross tool output. Both arms were equally correct under the acceptance checks.

Three pairs, one synthetic task, one model, and unblinded scoring are insufficient to generalize. Provider caching, nondeterminism, run order and implementation choices remain confounders. This measures **explicit activation**, not whether automatic discovery chooses the skill.

A useful next experiment would span longer log-heavy tasks and multiple models, blind the answer-quality assessment, and test avoiding redundant skill reads as a **separate treatment**. Do not subtract overhead from the headline result or silently change the skill and relabel this run as a success.

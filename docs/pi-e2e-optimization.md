# Optimizing Laconic: smaller skill, lower output—not net token savings

**The selected compact skill reduced output tokens 11.7%, tool-result bytes 14.7%, and Pi's catalog-estimated cost 3.3%, but increased total tokens 11.0% against its matched baseline. The net token-saving goal was not met.**

The core is **1,316 bytes**, down from **4,328** (**69.6% smaller**). It preserves outcome-first reporting, conditions and context, verification, failure visibility, and exact code/data. It now explicitly avoids redundant skill reads, routine narration, unnecessary inventories, and noisy test output. Detailed guidance remains lazy-loaded in `references/tool-output.md`.

The selected compact revision is the repository's root `SKILL.md`. Reload Pi skills after updating an installation.

## What we tested

We retained the original experiment and ran **two additional revisions**, each against a fresh no-skill baseline: **18 actual Pi sessions total**, three pairs per revision. All used the original task, fixture, model (`openai-codex/gpt-6-sol`), Pi 1.1.0, medium thinking, isolation, and acceptance checks. Runs alternated arm order.

These are exploratory revisions tuned after seeing results on the same task, not held-out validation. Each revision has its own matched baseline. Cross-revision numbers show observed differences, not causal proof. Only aggregate/paired summaries are published; execution scripts and raw sessions remain local.

| Revision | Skill bytes | Prose words | Output tokens | Gross tool bytes | Total tokens | Pi estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 4,328 | +8.7% | +5.1% | +66.9% | +54.2% | +27.8% |
| **Compact: selected** | **1,316** | **−15.9%** | **−11.7%** | **−14.7%** | **+11.0%** | **−3.3%** |
| Batching directive: rejected | 1,255 | −14.0% | +4.3% | −7.3% | +34.9% | −1.0% |

Percentages are changes against each revision's own baseline, based on equal-sized arm totals. Negative means less. Pi cost metadata is a model-catalog estimate, **not a provider invoice or subscription charge**. Different cache proportions explain why estimated cost can fall while total token volume rises.

The batching variant requested planning evidence and batching reads/checks more explicitly. It used **21 model calls versus 18** for its baseline and reread the skill once. We rejected it: a slightly smaller file did not translate to better session efficiency. More calls correlate with the instructions; these samples do not prove the instructions caused the regression.

## Selected compact revision: measured totals

| Measure | Baseline: 3 runs | Compact: 3 runs | Change |
| --- | ---: | ---: | ---: |
| Final-answer words | 276 | 232 | −15.9% |
| All assistant-prose words | 276 | 232 | −15.9% |
| Output tokens | 4,483 | 3,960 | −11.7% |
| Uncached input tokens | 14,929 | 15,580 | +4.4% |
| Cache-read tokens | 37,632 | 43,776 | +16.3% |
| All input-context tokens | 52,561 | 59,356 | +12.9% |
| Cache-inclusive total tokens | 57,044 | 63,316 | +11.0% |
| Tool-result text bytes | 14,065 | 11,991 | −14.7% |
| Tool calls | 26 | 27 | +3.8% |
| Model calls | 18 | 18 | Equal |
| Redundant skill reads | 0 | 0 | Equal |
| Pi catalog-estimated cost | $0.0822144 | $0.0795152 | −3.3% |
| Pi process elapsed seconds | 79.126 | 75.116 | −5.1% |
| Independent acceptance checks | 27/27 | 27/27 | Equal |

Both arms reported zero cache-write tokens. Output tokens include code, tool arguments and reasoning, not just prose. All reported total-token values match the sum of usage categories. Reasoning is already included in output.

The selected revision produced less prose and fewer gross tool-result bytes in **all three pairs**. Total tokens were higher in **all three pairs**. Output tokens were higher in pair 1 and lower in pairs 2 and 3: the aggregate reduction is not a uniform win.

| Pair | Final/prose words: baseline → compact | Output tokens | Total tokens | Tool bytes |
| --- | ---: | ---: | ---: | ---: |
| 1 | 91 → 80 | 1,461 → 1,597 | 18,410 → 22,132 | 4,406 → 4,133 |
| 2 | 86 → 83 | 1,519 → 1,164 | 19,699 → 20,285 | 4,942 → 3,536 |
| 3 | 99 → 69 | 1,503 → 1,199 | 18,935 → 20,899 | 4,717 → 4,322 |

Against the original skill arm, the compact arm used **29.4% fewer total tokens** (89,648 → 63,316) and **27.4% less estimated cost** ($0.1095344 → $0.0795152). Those are separate runs, not matched same-time treatments; they demonstrate lower observed overhead than the old version, **not a no-skill savings claim**.

## Context, clarity and correctness

All **18 solutions passed 9/9 independent acceptance checks**, and their resulting local test suites passed. Every answer included a concrete cause, identifiable changes, a test/CLI result, and the fixture/live-provider limitation. Each Laconic answer began with the outcome; each baseline answer began with the cause.

Under the original five-point manual clarity/evidence rubric, all revisions scored **15/15 for Laconic versus 12/15 baseline**. The compact revision therefore retained the measured evidence/clarity score while shortening prose. Scoring is author-rated and unblinded. It measures specific reporting features, not human comprehension, general clarity, or universal correctness.

For example, compact pair 3 states:

> Fixed `usage_summary.py`: it now counts only completed assistant `message_end` records with an allowed stop reason, including those without usage.

It goes on to explain token accounting, report six passing tests and the exact CLI result, and preserve the live-provider limitation. Complete session outputs are intentionally not published.

**Test-preservation limitation:** compact pair 1 rewrote the test suite to three tests despite the instruction to preserve tests. Its grouped regressions and independent acceptance checks passed, but that does not prove all prior tests were preserved. The skill is guidance, not enforcement. No result is awarded correctness merely for being short; the independent nine checks remain separate.

## Why total tokens still increased

The core instruction injection still adds context, and Pi sends context on subsequent requests. Removing redundant reads eliminates one source of overhead, not all of it. Code/test choices, request count, caching and nondeterministic model behavior also affect usage.

A short task with little irrelevant output leaves limited room to offset added instructions. Quiet output reduced visible payload, but not enough to overcome the added input context in this experiment. Gross verified-check efficiency improved from **1.92 to 2.25 checks per 1,000 tool bytes**; that within-task proxy does not establish net token savings.

A skill cannot enforce caps, prevent rereading, or guarantee shorter trajectories. We did not add a limiting extension, skip tests, hide failures, change the benchmark task, or discard unfavorable runs. No dollar-billing claim is made from Pi's estimates.

## Retained summaries

- [Original report](pi-e2e-comparison.md) and [original aggregate/paired summary](benchmark-summaries/initial.json).
- [Compact summary](benchmark-summaries/compact.json).
- [Rejected batching summary](benchmark-summaries/batched.json).

Scripts, transcripts, generated solutions and logs remain local and are intentionally excluded from Git. References were not read by agents in these runs. These summaries retain the measured favorable and unfavorable outcomes but do not provide independently replayable transcript evidence.

**Next validation should use fresh, longer tool-heavy tasks and blinded scoring.** Until then, describe this revision as a smaller, clearer-output skill with lower measured estimated cost—not a proven net token-saving solution.

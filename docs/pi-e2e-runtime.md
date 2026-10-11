# Native runtime: Pi benchmark summary

## v3 (current): review recall preserved, lower cost, latency regression removed

**36 sessions: 3 workflows × 4 arms × 3 pairs. All 336/336 independent checks passed; every review session found all 6 seeded defects (72/72).** Pi 1.1.0, `openai-codex/gpt-6-sol`, medium thinking; isolation and arm-order reversal as in v1. Runtime arms used an explicit profile: `review` for the review workflow, `implementation` otherwise. Values are per-session means.

| Workflow | Measure | Baseline | Skill | Runtime | Both |
| --- | --- | ---: | ---: | ---: | ---: |
| Review (6 seeded defects) | Defects found | 6/6 | 6/6 | 6/6 | 6/6 |
| | Total tokens | 174,067 | 174,465 | **58,652** | 93,185 |
| | Elapsed seconds | 61.3 | 43.9 | **39.7** | 53.7 |
| | Est. cost, USD | 0.099 | 0.098 | **0.053** | 0.070 |
| Noisy-log triage | Checks | 11/11 | 11/11 | 11/11 | 11/11 |
| | Total tokens | 105,370 | 109,267 | **37,590** | 42,048 |
| | Elapsed seconds | 33.3 | 30.2 | 37.8 | **33.3** |
| | Est. cost, USD | 0.067 | 0.068 | **0.038** | 0.042 |
| Short usage repair (nothing to filter) | Checks | 9/9 | 9/9 | 9/9 | 9/9 |
| | Total tokens | 19,739 | 21,499 | 20,428 | 22,788 |
| | Elapsed seconds | 29.8 | 25.8 | 23.2 | 34.1 |

Change versus baseline (sums):

| Workflow | Arm | Tokens | Elapsed | Est. cost |
| --- | --- | ---: | ---: | ---: |
| Review | Runtime | **−66.3%** | **−35.2%** | **−46.6%** |
| Review | Both | −46.5% | −12.3% | −29.2% |
| Review | Skill | +0.2% | −28.3% | −1.1% |
| Noisy-log triage | Runtime | **−64.3%** | +13.3% | **−43.6%** |
| Noisy-log triage | Both | −60.1% | −0.2% | −38.0% |
| Noisy-log triage | Skill | +3.7% | −9.3% | +1.5% |
| Usage repair | Skill / Runtime / Both | +8.9% / +3.5% / +15.5% | −13.3% / −22.3% / +14.4% | −4.6% / +10.6% / −2.2% |

Across all 36 sessions: runtime used **61.0% fewer tokens, 19.1% less elapsed time and 37.2% lower estimated cost** than baseline with identical correctness; both used 47.2% fewer tokens, 2.7% less time and 28.3% lower cost.

### Improvement over v1 (engine and skill on `main`)

| Noisy-log triage, change vs its own baseline | v1 | v3 |
| --- | ---: | ---: |
| Runtime elapsed time | +63.8% | **+13.3%** |
| Both elapsed time | +18.8% | **−0.2%** |
| Runtime tokens | −66.5% | −64.3% |
| Skill-only tokens (usage repair) | +23.0% | **+8.9%** |

- **Failure groups.** v1's first excerpt omitted the triage incident line and 3 of 3 `FAIL` lines on the review log (a repeated telemetry error consumed its error budget). v3 includes all of them in the first excerpt (3.1–3.8 KB), so recovery is a single ~400-byte `query` call, not range paging.
- **Review profile.** Search, reads and diffs pass through; only the noisy check log is compressed. Zero recovery calls in all six runtime/both review sessions, no recall loss.
- **Remaining overhead.** Each triage runtime session still made one recovery call, because the task prompt instructs recovery of the incident record when output is partial, although the line was already visible. The short repair workflow has no eligible output; differences there are run-to-run variation and skill overhead.

### Rejected v2 skill text

A v2 skill revision required reviews to "cover every changed file" and "list candidates first, then verify each". Recall was unchanged (baseline already found 6/6), but skill-only review sessions used **92.6% more tokens and 55% more time**: extra edge-case probes and repeated replay of the full log. v3 keeps only "list every distinct evidenced finding separately; never merge or drop one", adds "sample repetitive files, read before probing, batch probes", and stops loading the playbook during recovery. Measurements: [native-runtime-v2-rejected-skill.json](benchmark-summaries/native-runtime-v2-rejected-skill.json).

### Limitations

Three pairs per arm and workflow, one model, synthetic fixtures, unblinded design, variable provider caching and latency. Review recall is keyword-scored against seeded defects; extra findings are counted, not judged. Catalog cost is not billing.

Aggregate, per-task and paired measurements: [native-runtime-v3.json](benchmark-summaries/native-runtime-v3.json).

---

## v1 (previous engine)

**Runtime filtering reduced context on the noisy-log task, but did not establish a speedup.** All 16 sessions passed **160/160 independent acceptance checks**; saved solutions also passed local re-verification.

Only summaries are published. Benchmark scripts, raw sessions, generated solutions, recovery logs and execution artifacts remain local and are intentionally excluded from Git.

## Method

Pi 1.1.0, configured `openai-codex/gpt-6-sol`, medium thinking, two repetitions per workflow and arm. Arms: baseline, explicitly activated skill, runtime, and both. Fresh isolated workspaces/configs received identical fixtures. Arm order reversed in the second repetition. A silent startup audit verified tool activation; runtime settings were explicit defaults. All model calls, recovery output, schema/skill overhead and tool errors are included in usage totals.

Two synthetic workflows used the same Python utility:

- **Usage repair:** short summarizer repair; nine independent checks per session.
- **Log triage + repair:** diagnose a 42,387-byte/901-line log and repair the utility; eleven checks per session. Runtime excerpts omitted the incident record, which every runtime-enabled session successfully recovered. Original log text matched across arms.

## Noisy-log workflow: totals across two sessions per arm

| Measure | Baseline | Skill | Runtime | Both |
| --- | ---: | ---: | ---: | ---: |
| Independent checks | 22/22 | 22/22 | 22/22 | 22/22 |
| Total tokens, including cache categories | 210,961 | 216,012 | 70,642 | 76,273 |
| Input-context tokens | 207,663 | 213,074 | 67,375 | 73,195 |
| Tool-result text bytes | 93,860 | 91,749 | 18,255 | 15,768 |
| Model calls | 16 | 16 | 18 | 18 |
| Tool calls | 22 | 21 | 24 | 25 |
| Recovery calls | 0 | 0 | 2 | 2 |
| Final/all assistant-prose words | 221 | 176 | 228 | 187 |
| Pi elapsed seconds | 64.159 | 64.712 | 105.124 | 76.198 |
| Pi catalog-estimated cost, USD | 0.136344 | 0.136885 | 0.076642 | 0.080632 |

Runtime-only used **66.5% fewer tokens** and **80.6% fewer tool bytes**, but **63.8% more elapsed time**. Both used **63.8% fewer tokens** and **83.2% fewer bytes**, but **18.8% more elapsed time**. Skill alone used 2.4% more total tokens.

## Why was it slower?

The runtime-only sample took 43.623 and 61.501 seconds, versus baseline's 35.695 and 28.464 seconds. Each runtime session required **one additional model roundtrip** to recover omitted evidence.

Local tool time cannot explain the additional 40.965 seconds across the two runtime sessions:

- Total recorded tool durations: baseline **1.057 seconds**, runtime **1.092 seconds**.
- Recovery-tool execution itself: approximately **2 ms per call**.
- Controlled filtering replay: approximately **0.8–1.5 ms median** for tested fixtures.

Most elapsed time therefore occurred outside tool execution. Extra inference roundtrips and provider/network timing are plausible contributors, but the measurements do **not** isolate their individual effects. Two repetitions are insufficient to claim that filtering inherently makes sessions 63.8% slower. The both arm's smaller slowdown despite the same recovery count also demonstrates timing variation.

### Speed improvement to test next

Retain a wider, budget-bounded diagnostic context or explicit incident/summary lines in the initial excerpt, so the agent need not request nearby omitted evidence. That targets the expensive extra model roundtrip rather than optimizing millisecond-scale storage. The tradeoff is a somewhat larger initial result; retain recovery and preserve the byte budget. Compare elapsed-time distributions over more matched repetitions, and report token/quality changes as well. **This optimization is proposed, not implemented or benchmark-verified.**

## Short usage repair: no filtering occurred

| Measure | Baseline | Skill | Runtime | Both |
| --- | ---: | ---: | ---: | ---: |
| Independent checks | 18/18 | 18/18 | 18/18 | 18/18 |
| Total tokens | 41,191 | 50,677 | 38,949 | 43,805 |
| Tool-result bytes | 8,757 | 8,270 | 9,116 | 8,120 |
| Pi elapsed seconds | 62.668 | 95.043 | 55.669 | 55.221 |
| Pi catalog-estimated cost, USD | 0.053088 | 0.066583 | 0.061391 | 0.056405 |

Zero filtered results and recovery calls: observed differences here are not evidence of a filtering benefit.

Across the equally repeated workflows, runtime used 56.5% fewer total tokens but 26.8% more elapsed time; both used 52.4% fewer tokens but 3.6% more time. The noisy-log task dominates these aggregate token totals; do not generalize them to typical users.

## Verification and limitations

24 Node tests, syntax checks and eight Python benchmark-harness tests passed at measurement time. Installed Pi verification exercised auto-discovery, actual successful/failed built-in Bash results, its native result-merge path, preserved raw structured data/error status, and recovery. Eight deterministic replay fixtures × ten repetitions passed; source/diff/structured/unknown-tool fixtures remained unchanged.

Failed activation attempts were excluded, not relabeled as runtime outcomes: missing active recovery tool, ignored `.mjs` CLI entry, and unconditional structured-content bypass. A separate positive two-session validation proved filtering/recovery before the 16-session comparison and is excluded from headline totals.

These are exploratory synthetic workflows, one utility/model, two repetitions, unblinded design and variable provider caching/timing. No independent answer-clarity scoring or production validation was performed. Tokens sum provider-reported input/output/cache categories; bytes are UTF-8 text, not token estimates. Catalog-estimated costs are not provider invoices or subscription charges. Claude/Codex native E2E and Windows privacy remain unverified; OpenCode native setup is unavailable, with MCP as the alternative.

Aggregate and paired measurements: [combined](benchmark-summaries/native-runtime.json), [usage repair](benchmark-summaries/native-runtime-usage.json), [log triage](benchmark-summaries/native-runtime-log-triage.json).

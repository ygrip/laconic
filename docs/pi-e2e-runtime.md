# Native runtime: Pi benchmark summary

## v2 (current): review-quality, failure groups and contextual recovery

**24 sessions, 3 workflows, 4 arms, 2 pairs; all 224/224 independent checks passed. Every review session found all 6 seeded defects (48/48).** Same Pi 1.1.0, `openai-codex/gpt-6-sol`, medium thinking, isolation and arm-order reversal as v1. Runtime arms used an explicit task profile: `review` for the review workflow, `implementation` otherwise.

New **review workflow** (measures what matters for reviews: found defects, not bytes). A small committed Python package with **six seeded defects**: three surface only as `FAIL` lines buried in a 63 KB check log behind 200 repeated telemetry `ERROR` lines; three are visible only in source (unused reserved-path list, substring role check, mutable default cache). Forty correct generated vendor adapters add realistic search/read surface. The agent writes `findings.json`; a hidden scorer matches each seeded defect by file plus keyword. Recall per session and reported-finding counts are published.

| Review workflow, sums of 2 sessions | Baseline | Skill | Runtime | Both |
| --- | ---: | ---: | ---: | ---: |
| Seeded defects found | 12/12 | 12/12 | 12/12 | 12/12 |
| Total tokens | 297,308 | 572,760 | 147,989 | 274,296 |
| Tool-result bytes | 142,120 | 166,803 | 61,234 | 80,969 |
| Model calls | 17 | 26 | 19 | 25 |
| Recovery calls | 0 | 0 | 0 | 0 |
| Pi elapsed seconds | 78.8 | 122.1 | 82.5 | 138.4 |
| Catalog-estimated cost, USD | 0.1826 | 0.2804 | 0.1360 | 0.1972 |

| Noisy-log triage, sums of 2 sessions | Baseline | Skill | Runtime | Both |
| --- | ---: | ---: | ---: | ---: |
| Independent checks | 22/22 | 22/22 | 22/22 | 22/22 |
| Total tokens | 210,749 | 224,679 | 73,826 | 87,928 |
| Tool-result bytes | 94,428 | 104,463 | 17,879 | 18,821 |
| Model calls | 16 | 16 | 18 | 18 |
| Recovery calls (bytes) | 0 | 0 | 2 (798) | 2 (692) |
| Pi elapsed seconds | 57.5 | 58.6 | 78.9 | 73.2 |
| Catalog-estimated cost, USD | 0.1339 | 0.1507 | 0.0797 | 0.0755 |

Short usage repair (no eligible output to filter; 18/18 checks in every arm): baseline 37,812 tokens, skill 48,088, runtime 46,793, both 48,780. Zero filtered results: differences there are run-to-run variation and skill overhead, not filtering.

### What changed and what it did

- **Failure groups.** On the review log the v1 engine showed **0/3** `FAIL` lines (the telemetry flood consumed its first-40-errors budget); v2 shows **3/3 plus the summary in 3.1 KB instead of 8.2 KB**. On the triage log v1 omitted the incident line; v2 includes it in the first excerpt (3.8 KB).
- **Review profile.** Runtime cut review tokens **50.2%** and tool bytes **56.9%** with **no recall loss and zero recovery calls**; only the noisy check log was shortened. Search output, reads and diffs passed through.
- **Contextual recovery.** Each triage recovery was one `query="INCIDENT"` call returning ~400 bytes, instead of v1-style numeric range reads. The prompt explicitly instructs recovery of the incident record when output is partial, so the agents recovered even though the line was already visible; the extra round trip is therefore partly a prompt artifact. Runtime-only triage still used **65.0% fewer tokens**, with **37.3% more elapsed time**.
- **Found during this run, fixed before the measured run:** an aborted first attempt showed `for f in ...; do nl -ba "$f"; done` source dumps classified as shell and shortened under the review profile, which forced two full-range recoveries. `nl`/`bat`/`less`/`more` are now file reads, and mostly line-numbered output is never shortened. The aborted sessions are excluded from all totals.

### Unfavorable result: the review-depth skill made reviews more expensive

The skill's new "compress the output, never the investigation" rules did not change recall here (baseline already found 6/6), but skill-only review sessions used **92.6% more tokens**, **53% more model calls** and **55% more time** than baseline: the agents read every generated adapter and probed edge cases more exhaustively. Skill + runtime recovered most of the token cost (7.7% fewer tokens than baseline) but remained 75.6% slower. The original 5-vs-6 PR observation that motivated the rule could not be reproduced on this fixture, so the benefit is unproven while the cost is measured. Treat the depth rule as a quality guard to evaluate on harder review sets, not as a saving.

### Limitations

Two pairs per arm and task, one model, synthetic fixtures, unblinded design, variable provider caching/timing. Recall is keyword-scored against seeded defects; extra findings are counted but not judged. Catalog cost is not billing. Elapsed time includes provider latency and is not isolated from inference variance.

Aggregate, per-task and paired measurements: [native-runtime-v2.json](benchmark-summaries/native-runtime-v2.json).

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

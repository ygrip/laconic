# Native runtime: Pi benchmark summary

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

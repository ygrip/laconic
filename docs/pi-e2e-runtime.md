# Native runtime: real Pi benchmark

**The runtime reduced tokens on the noisy-log workflow, but did not produce a general speedup.** Runtime-only used **66.5% fewer total tokens** and **80.6% fewer tool-result bytes** there. Skill + runtime used **63.8% fewer tokens** and **83.2% fewer tool-result bytes**. Both runtime arms were slower in this sample. No shell result was large enough to filter on the short repair workflow.

All **16 actual Pi sessions passed 160/160 independent acceptance checks**, and every resulting test suite passed. All saved solutions also passed [fresh independent re-verification](../benchmarks/pi-e2e/results/native-runtime/reverification.json). These are two synthetic workflows on one utility, not production verification or a statistically established effect.

## Experiment

On **2026-10-10 UTC**, Pi **1.1.0** ran with configured model **`openai-codex/gpt-6-sol`**, `medium` thinking, and two repetitions per workflow and arm:

- **Baseline:** four built-in tools; no skill/runtime.
- **Skill:** explicit `/skill:laconic` activation; no runtime.
- **Runtime:** native Pi display-result hook and active `laconic_read_result`; no skill.
- **Both:** skill, native hook, and recovery tool.

Fresh workspaces/configs received identical starting fixtures and requirements. MCP, context files, discovered extensions/skills, templates and themes were disabled. Every arm loaded the same silent startup observer; runtime arms additionally initialized Laconic through a temporary **`.ts` CLI entry**. An actual CLI preflight checked active tools before inference; the provider session repeated the check. Preflight consumes no model call and is excluded from reported Pi task-process elapsed time.

Order was baseline → skill → runtime → both in the first repetition and reversed in the second. Workflows ran sequentially. Runtime settings were explicit defaults, with a fresh private local recovery store per session; user runtime settings were ignored. There was no seed or temperature control.

- **Usage repair:** unchanged original summarizer fixture, **9 checks per session**.
- **Log triage + repair:** run `python3 diagnose.py` directly, diagnose an incident outside the runtime excerpt, write `incident.json`, then repair the same summarizer; **11 checks per session**, including the untouched diagnostic generator.

The diagnostic command returned **42,387 UTF-8 bytes / 901 lines**, below Pi's built-in limits. The [result audit](../benchmarks/pi-e2e/results/native-runtime/validation.json) verifies identical original log text in every log session, exact saved originals in runtime arms, successful incident recovery, active-tool audits, source hashes, acceptance results, and provider usage accounting. Each of the four runtime-enabled log sessions filtered one result and used the recovery tool once. Recovery calls, their output, schema overhead, tool errors, and skill overhead remain in totals.

## Noisy-log workflow: totals across two sessions per arm

| Measure | Baseline | Skill | Runtime | Both |
| --- | ---: | ---: | ---: | ---: |
| Independent checks | 22/22 | 22/22 | 22/22 | 22/22 |
| Total tokens, including cache categories | 210,961 | 216,012 | 70,642 | 76,273 |
| Input-context tokens | 207,663 | 213,074 | 67,375 | 73,195 |
| Output tokens, including code/tool arguments/reasoning | 3,298 | 2,938 | 3,267 | 3,078 |
| Tool-result text bytes | 93,860 | 91,749 | 18,255 | 15,768 |
| Model calls | 16 | 16 | 18 | 18 |
| Tool calls | 22 | 21 | 24 | 25 |
| Recovery calls | 0 | 0 | 2 | 2 |
| Tool-error results | 1 | 0 | 0 | 0 |
| Final/all assistant-prose words | 221 | 176 | 228 | 187 |
| Pi process elapsed seconds | 64.159 | 64.712 | 105.124 | 76.198 |
| Pi catalog-estimated cost, USD | 0.136344 | 0.136885 | 0.076642 | 0.080632 |

Relative to baseline:

- **Runtime:** 66.5% fewer total tokens, 67.6% less input-context volume, 80.6% fewer tool bytes, and 43.8% lower **catalog-estimated** cost; **63.8% more elapsed time**.
- **Both:** 63.8% fewer total tokens, 64.8% less input-context volume, 83.2% fewer tool bytes, and 40.9% lower estimated cost; **18.8% more elapsed time**.
- **Skill alone:** 2.4% more total tokens despite 20.4% fewer final words.

Both repetitions showed substantially lower total tokens in runtime arms:

| Repetition | Baseline | Skill | Runtime | Both |
| --- | ---: | ---: | ---: | ---: |
| 1 total tokens | 105,455 | 108,745 | 34,253 | 39,127 |
| 2 total tokens | 105,506 | 107,267 | 36,389 | 37,146 |

Runtime recovery added one model call per session. Do not equate lower context volume with lower latency: inference variation and extra calls remain material. The controlled processor replay below is not an E2E speed measurement.

## Short usage-repair workflow: no filtering occurred

| Measure | Baseline | Skill | Runtime | Both |
| --- | ---: | ---: | ---: | ---: |
| Independent checks | 18/18 | 18/18 | 18/18 | 18/18 |
| Total tokens | 41,191 | 50,677 | 38,949 | 43,805 |
| Tool-result bytes | 8,757 | 8,270 | 9,116 | 8,120 |
| Final/all assistant-prose words | 192 | 161 | 213 | 163 |
| Model calls | 14 | 14 | 12 | 12 |
| Tool-error results | 0 | 1 | 2 | 1 |
| Pi elapsed seconds | 62.668 | 95.043 | 55.669 | 55.221 |
| Pi catalog-estimated cost, USD | 0.053088 | 0.066583 | 0.061391 | 0.056405 |

All eligible results were below the runtime threshold/budget: **zero filtered results and zero recovery calls**. Runtime-only happened to use 5.4% fewer total tokens but 15.6% higher estimated cost and 4.1% more tool-result bytes. Those differences do not demonstrate a filtering benefit; generated solutions, call counts, caching and session variation differed. Both used 6.3% more total tokens than baseline. No general saving on small tasks is established.

## Combined workload totals

The [combined summary](../benchmarks/pi-e2e/results/native-runtime/summary.json) simply sums the equally repeated workflows; it is not a weighting estimate for real users:

- Runtime: **56.5% fewer total tokens**, **73.3% fewer tool bytes**, **27.1% lower catalog-estimated cost**, **26.8% more elapsed time**, and **6.8% more final words**.
- Both: **52.4% fewer total tokens**, **76.7% fewer tool bytes**, **27.7% lower estimated cost**, **3.6% more elapsed time**, and **15.3% fewer final words**.
- Skill alone: **5.8% more total tokens** and **18.4% fewer final words**.

The noisy-log workflow dominates token totals. Do not extrapolate these aggregate percentages to workloads with mostly short outputs.

## Controlled processor replay and native contract checks

[Processor replay](../benchmarks/pi-e2e/results/native-runtime/processor-replay.json) applies default policy to eight identical-input fixtures, ten repeats each, with no LLM:

- Shell/test/search logs: **96.36% fewer model-facing bytes**, retaining the required failure and final summary.
- Long Unicode head plus warning flood: **93.44% fewer bytes**, with required diagnostics retained.
- Source reads, test-file git diffs, structured shell JSON and unknown substring-named tools: **unchanged**.
- Exact full-storage and line-range recovery assertions passed. Median filtering time was approximately **0.8–1.5 ms** on this machine, including persistence but excluding verification reads.

These are synthetic UTF-8 byte/processor measurements, **not provider-token savings** or proof every diagnostic survives a bounded excerpt.

The [installed Pi smoke](../benchmarks/pi-e2e/results/native-runtime/pi-setup-verification.json) auto-discovers the deployed `laconic.ts` shim and exercises actual successful and failed built-in Bash results. It checks shortened display text, unchanged native structured output, preserved error/exit status, and recovery. The real CLI transcripts separately verify finalized model-facing filtering and successful recovery through the actual tool runner.

**24 Node tests**, syntax checks, and **8 Python harness tests** pass. Gateway coverage includes live JSON-RPC recovery, spawn/exit failures with client stdin open, and paginated recovery-name collisions. Claude/Codex native E2E compatibility and Windows privacy/installation remain unverified. OpenCode native setup explicitly refuses the unavailable checked V2 tool-hook API; use the MCP proxy instead.

## Failed attempts retained, not relabeled as successes

The implementation required three activation/compatibility corrections:

1. [Incomplete attempt](../benchmarks/pi-e2e/results/native-runtime-incomplete/README.md): restricted `--tools` omitted registered recovery.
2. [Unloaded CLI attempt](../benchmarks/pi-e2e/results/native-runtime-unloaded/README.md): the low-level loader accepted `.mjs`, but the CLI resource resolver silently did not load it.
3. [Structured-shell smoke](../benchmarks/pi-e2e/results/native-runtime-smoke/README.md): tools were active, but unconditional structured-result passthrough skipped every real built-in Bash result. Fabricated tests had omitted its native `structuredContent`.

The adapter now recognizes only the exact native Bash shape and returns raw structured data unchanged alongside filtered display text. Arbitrary structured APIs still pass through; PowerShell needs independent native-shape verification. This is reversible display summarization, not secret redaction.

All completed records from failed attempts remain published and are **excluded from runtime claims**. The [positive two-session validation](../benchmarks/pi-e2e/results/native-runtime-validation/) established filtering/recovery before the 16-run comparison; it is separate from its headline totals. Original historical skill benchmarks are untouched.

## Reproduction, evidence, and limitations

See the [methodology and commands](../benchmarks/pi-e2e/README.md), [runner](../benchmarks/pi-e2e/run.py), [activation observer](../benchmarks/pi-e2e/audit-extension.ts), [auditor](../benchmarks/pi-e2e/validate_results.py), and [analysis](../benchmarks/pi-e2e/analyze.py).

- [Manifest and source hashes](../benchmarks/pi-e2e/results/native-runtime/manifest.json), [all 16 measurements](../benchmarks/pi-e2e/results/native-runtime/metrics.json), and [validation](../benchmarks/pi-e2e/results/native-runtime/validation.json).
- [Usage workflow records/summary](../benchmarks/pi-e2e/results/native-runtime/usage/) and [log-triage records/summary](../benchmarks/pi-e2e/results/native-runtime/log-triage/).
- Every session publishes actual final/prose text, sanitized completed messages, solution, verification, startup audits, and stored originals where applicable. Private reasoning/signatures, credentials, and temporary absolute paths are not published.

Total tokens sum provider-reported input, output, cache-read and cache-write once per completed assistant message; every reported total crosschecks. Output already includes reasoning. Byte counts are original UTF-8 tool text before path sanitization, not token estimates. Cached and uncached tokens have different prices. Pi's catalog cost is **not a provider invoice or subscription charge**; actual routing/pricing may differ.

Two repetitions per workflow, one configured model, one utility, unblinded synthetic task design, shared provider caching and nondeterminism limit generalization. This is exploratory debugging and measurement, not a preregistered or broadly held-out evaluation. Answer clarity was **not independently rescored**; word counts and correctness checks do not establish unchanged readability. The included-error counts are tool errors, not a count of provider retries. Failed/interrupted attempts and preflights are excluded from task-process metrics, not erased from the evidence or claimed to be free overall experimentation.

Use native filtering for large recoverable logs when context reduction matters; keep small/structured/source-critical results intact. Measure latency and recovery overhead on the actual workload before treating it as a universal optimization.

<div align="center">
  <img src="assets/logo.jpg" alt="Laconic: claymorphic Spartan helmet and wordmark" width="720">

  <p><strong>Less noise. More signal.</strong></p>
  <p>An Agent Skill for clear replies, honest engineering updates, and focused tool usage.</p>
</div>

## Install

Use the open Agent Skills installer. No separate npm package is required:

```bash
npx skills add ygrip/laconic
```

For a global Pi installation:

```bash
npx skills add ygrip/laconic -g -a pi
```

The installer can also target supported agents such as Claude Code and Codex; omit `-a` for its interactive selection. The skill lives at the repository root as [`SKILL.md`](SKILL.md).

**Manual installation:** Copy this repository into `~/.agents/skills/laconic` for agents that discover that directory, or into the agent's supported project skill directory. In Pi, reload skills with `/reload` and use `/skill:laconic` explicitly.

## Why Laconic?

An agent can run the right tools and still make the result difficult to understand. Laconic asks the agent to give the answer first, cut filler, and keep the evidence.

| Without Laconic | With Laconic |
| --- | --- |
| “I have successfully completed a comprehensive series of modifications...” | “Fixed usage parsing. Tests pass. Production verification remains.” |
| “It appears there may potentially be an issue with the environment configuration...” | “`API_URL` is missing. Set it and retry.” |

Laconic encourages agents to:

- Lead with outcomes, not a play-by-play of tool calls.
- Explain technical issues with concrete, readable language.
- Separate what changed, what passed, and what is still unknown.
- Retrieve only relevant code, logs, diffs, and API fields.
- Preserve failure details, warnings, references, and important trade-offs.

Inspired by plain-language ideas behind [ASD-STE100](https://www.asd-ste100.org/STE_faq.html), but **not** a formal implementation or compliance checker.

## Token efficiency: what it can and cannot do

| Area | What Laconic does |
| --- | --- |
| Agent replies | Encourages fewer, more useful **output tokens**. |
| Tool calls | Encourages bounded, relevant results, reducing **input/context tokens** when followed. |
| Tool-result interception | Not part of the Markdown skill. The [optional native runtime](docs/native-runtime.md) supplies host hooks. |
| Savings | Not guaranteed. Measure across equivalent tasks and include follow-up calls. |

### Measured Pi E2E comparison

We tested the original skill and two optimizations in **18 actual Pi sessions**. All solutions passed the independent fixture checks. The selected compact skill is **69.6% smaller** than the original.

Against its matched no-skill baseline, the compact skill produced:

- **15.9% fewer words**, **11.7% fewer output tokens**, and **14.7% fewer tool-result bytes**.
- Outcome-first replies in **3/3** runs versus **0/3** baseline runs, retaining causes, changes, verification, and limitations.
- **3.3% lower Pi catalog-estimated cost**—not measured provider billing.
- **11.0% more total tokens** after input/cache overhead. **The net token-saving goal was not met.**

These small, single-task experiments do not establish general savings. Read the [optimization report](docs/pi-e2e-optimization.md) and [original unfavorable results](docs/pi-e2e-comparison.md). Only reports and [measurement summaries](docs/benchmark-summaries/) are published; scripts and raw sessions remain local.

### Measured native runtime comparison

The current engine and skill were measured in **36 Pi sessions** (baseline, skill, runtime, both × code review, noisy-log triage, short repair; three pairs). **All 336/336 independent checks passed, and every review session found all 6 seeded defects.**

- **Review:** runtime used **66.3% fewer tokens**, **35.2% less time** and **46.6% lower estimated cost**, with no recall loss and zero recovery calls.
- **Noisy-log triage:** runtime used **64.3% fewer tokens**; the v1 latency penalty dropped from +63.8% to +13.3% (both arms: +18.8% to −0.2%).
- **Overall:** runtime **−61.0% tokens, −19.1% time, −37.2% estimated cost** versus baseline at identical correctness.
- Skill alone is roughly cost-neutral on these tasks (+0.2% to +8.9% tokens), down from +23% in v1.

Small synthetic samples; not provider-billing or production claims. See [results, method and limitations](docs/pi-e2e-runtime.md).

### Optional Pi tool-result limits

For automatic model-facing caps, pair the skill with the independent [pi-output-limits](https://pi.dev/packages/pi-output-limits) extension:

```bash
pi install npm:pi-output-limits
```

Merge the `outputLimits` object from [`examples/pi-output-limits.settings.json`](examples/pi-output-limits.settings.json) into your existing Pi `~/.pi/agent/settings.json` (or project `.pi/settings.json`). **Do not replace your other settings.** Then reload Pi. Limits are configurable; the example is only a starting point. Read [the tool-output playbook](references/tool-output.md) for strategies and recovery precautions.

Do not rely on truncation alone. An agent still needs error codes, failing assertions, warnings, and access to full logs if necessary.

## Apply automatically in Pi

Pi discovers skills on demand. To apply Laconic to user-facing reports across sessions, append this instruction to `~/.pi/agent/AGENTS.md`:

> For user-facing task results, progress updates, technical explanations, and handoffs, load and follow the `laconic` skill. Preserve precise facts, risks, code, and requested detail.

This is optional. It increases input tokens when the skill loads, so compare model usage before making it a global default.

## Project layout

```text
laconic/
├── SKILL.md                              # Installable agent skill
├── README.md
├── LICENSE
├── .gitignore
├── assets/
│   ├── icon.png                          # Claymorphic Spartan helmet
│   └── logo.png                          # Helmet + Laconic wordmark
├── examples/
│   └── pi-output-limits.settings.json
├── references/
│   └── tool-output.md                    # Expanded playbook, loaded as needed
├── docs/
│   ├── pi-e2e-comparison.md              # Original measured comparison
│   ├── pi-e2e-optimization.md            # Tested optimizations and limitations
│   ├── pi-e2e-runtime.md                 # Runtime results and latency limits
│   └── benchmark-summaries/              # Aggregate and paired measurements
└── runtime/                              # Optional runtime (benchmarks stay local)
```

## Native tool-result runtime (experimental)

Laconic now includes an **optional, deterministic runtime** for filtering model-visible tool results without running an extra LLM. It is separate from the portable Markdown skill. The shared engine preserves recoverable evidence and passes through structured, multimodal, unknown, and unsafe-to-shorten results. Pi's known native Bash shape is a narrow display-text exception: its raw structured output remains unchanged for programmatic callers.

- **Pi:** native `tool_result` extension, with recovery tool when supported.
- **Claude Code:** schema-preserving `PostToolUse` hook for successful shell stdout.
- **OpenCode:** MCP gateway only; native setup refuses the unavailable V2 tool-hook API.
- **Codex:** observation-only native hook; no unsupported result-rewrite claim.
- **MCP stdio:** optional gateway for tools routed through the proxy, with a recovery tool.

What the engine keeps and how it recovers (goal: lower total task cost and time, not the smallest first response):

- **Distinct failure groups:** diagnostics are grouped by normalized signature; every group gets a representative line plus cause context before head/tail filler, so one flooding error cannot hide a rarer failure. Output starts with a group index and reports `groups shown/total`.
- **Lossless search index:** `rg`/`grep`/path-list output becomes a complete file → match-count → line-number index plus round-robin snippets; if the index cannot fit, the original passes through.
- **Contextual recovery:** `laconic_read_result` and `laconic show` accept `query` (text or regex) with surrounding `context`, and `around=N`, not just numeric ranges.
- **Task profiles:** `review` (search, reads and diffs untouched; only repetitive logs compressed), `implementation` (default), `debugging` (wider budgets and context), `documentation`. Set `profile` in config or `LACONIC_PROFILE`.
- **Cost signals:** `laconic stats` reports recovery rate, recovery bytes and extra round trips per category/profile, not just bytes saved.

From a checkout (Node.js 20+):

```bash
npm test
node bin/laconic.mjs setup --harness pi --scope user
node bin/laconic.mjs doctor
node bin/laconic.mjs disable --harness pi --scope user
```

The proposed `npx @ygrip/laconic setup` command requires publishing the npm package separately; **this PR does not publish npm**. Read the [compatibility, configuration and security guide](docs/native-runtime.md) before enabling local hooks. Full results are stored in owner-only local files when recovery is enabled; this is not encryption or secret redaction. Pi has [fresh four-arm E2E benchmarks](docs/pi-e2e-runtime.md). Claude/Codex native compatibility remains unverified; OpenCode native installation is unavailable. Unit/integration tests are not a substitute for live model-facing verification. Savings remain task- and model-dependent.

## License

MIT. See [LICENSE](LICENSE).

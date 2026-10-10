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
| Tool-result interception | **Not built in.** Requires a host hook or extension. |
| Savings | Not guaranteed. Measure across equivalent tasks and include follow-up calls. |

### Measured Pi E2E comparison

We tested the original skill and two optimizations in **18 actual Pi sessions**. All solutions passed the independent fixture checks. The selected compact skill is **69.6% smaller** than the original.

Against its matched no-skill baseline, the compact skill produced:

- **15.9% fewer words**, **11.7% fewer output tokens**, and **14.7% fewer tool-result bytes**.
- Outcome-first replies in **3/3** runs versus **0/3** baseline runs, retaining causes, changes, verification, and limitations.
- **3.3% lower Pi catalog-estimated cost**—not measured provider billing.
- **11.0% more total tokens** after input/cache overhead. **The net token-saving goal was not met.**

These small, single-task experiments do not establish general savings. Read the [optimization report](docs/pi-e2e-optimization.md), [original unfavorable results](docs/pi-e2e-comparison.md), and [reproduction instructions](benchmarks/pi-e2e/README.md). All tested revisions and actual outputs are retained.

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
│   └── pi-e2e-optimization.md            # Tested optimizations and limitations
└── benchmarks/
    └── pi-e2e/                           # Reproducible harness and actual E2E evidence
```

## License

MIT. See [LICENSE](LICENSE).

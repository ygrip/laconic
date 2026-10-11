# Tool-output optimization: detailed playbook

The goal is to **return enough evidence for the next decision**, not to blindly make every result short. Tool results typically become model **input/context** tokens. Do not confuse these with final-answer output tokens.

### Loading overhead

The core skill is intentionally small. If `/skill:laconic` or another host has already inserted its instructions into context, do not read `SKILL.md` again. Registering a skill's name/description alone is not the same as loading its full instructions: load the core once when needed. Do not load this playbook for routine coding tasks.

Count instruction injection and any reads in E2E usage. Less tool output does not prove net token savings: repeated context and additional model calls can outweigh the reduction. Compare correctness and all user-facing prose as well as final answers. Avoid redundant progress reports, but report consequential blockers and respect requested updates.

### Before calling a tool

1. **Define the needed evidence.** Ask: What specific fact, file, symbol, error, or decision must this call establish?
2. **Use server-side selection first.** Prefer structured fields, query filters, `limit`/`page_size`, targeted file ranges, and repository scopes over fetching everything and trimming later.
3. **Prefer smallest sufficient representation.** Examples: `git status --short` rather than a full status report; `git diff --stat` before requesting a narrow diff; `rg -n 'pattern' relevant/path` instead of dumping every file; targeted JSON fields instead of full API responses.
4. **Do not repeat identical calls.** Reuse already returned identifiers, excerpts, and evidence. Re-fetch only if it is incomplete or stale.
5. **Choose a response budget appropriate to the task.** Start small for discovery, expand when necessary for debugging or verification. One narrow follow-up is better than a large unrelated dump.

### When reading results

- **Search/find:** Return matching paths, locations, and bounded snippets. Expand only the relevant matches.
- **File reads:** Read a known small relevant file directly once; avoid an inventory command merely to confirm a supplied path. For large files, read the relevant function, section, or line range, not the entire repository or log. Follow project-required discovery and coverage checks.
- **Tests/builds:** Prefer a runner's quiet mode when it still reports counts, failures, and warnings. Keep existing tests; add missing regressions rather than replacing the suite to reduce output. Keep exit status, failing test names, assertion messages, stack trace frames needed for diagnosis, and a short pass/fail summary. Avoid thousands of passing test lines. Do not hide a failure behind `|| true` or a pipeline that discards its exit code.
- **Bash/logs:** Limit output at the command or tool layer. A log tail can help, but errors may be at the beginning or middle; search the saved log when the tail lacks the cause.
- **Git/diffs:** Get changed file names first, then relevant hunks. Preserve patch context when editing or reviewing a change.
- **JSON/MCP/API:** Ask for the fields needed for the decision, use pagination, and keep stable identifiers and status/error fields. Do not strip schema-required fields or change data semantics.
- **Security/incident reviews:** Do not omit security warnings, data-loss risks, or critical findings merely to meet a token budget.

### Large results and recovery

If a result exceeds the budget, prefer a host/tool-level mechanism that:

1. Keeps the critical evidence and error state.
2. Limits the **model-facing** text before it enters context.
3. Retains full output in an access-controlled file or source system when possible.
4. Provides a clear retrieval pointer (file, line offset, page token, or query) and notes that the result is incomplete.
5. Allows targeted expansion when missing details are necessary.

**Recover by query, not by guessing ranges.** With the Laconic runtime, `laconic_read_result` accepts `query` (text, or regex with `regex=true`) and returns every matching line with `context` surrounding lines, or `around=N` for one location. One targeted query usually replaces several range reads and the extra model calls they cost.

### Task-aware policies

Pick the profile matching the work (`profile` in the runtime config or `LACONIC_PROFILE`):

| Task | Profile | Behavior |
| --- | --- | --- |
| Code review / audit | `review` | Search results, file reads and diffs pass through whole; only repetitive shell/test logs are compressed. |
| Implementation | `implementation` (default) | Moderate shell/test compression; search keeps a lossless file/line index. |
| Debugging | `debugging` | Larger budgets, more failure groups and wider cause context; recovery always available. |
| Documentation | `documentation` | Optimize final prose; compress only noisy command logs. |

Measure recovery frequency and additional model calls (`laconic stats`), not only bytes saved: a frequently recovered category is budgeted too tightly.

Never pretend a truncated result was exhaustive. Never invent omitted content. Redact secrets before storing logs, and follow local retention rules. **Do not merely summarize a large tool response in your final answer:** by then, the model has already paid to receive the large result.

### Examples of narrow requests

```bash
# Identify changes before reading patch content
git status --short
git diff --stat
git diff -- src/parser.ts

# Search for the specific failure or symbol
rg -n 'ProviderUsage|usageTotal|ERROR' src test

# Preserve test exit status while displaying only useful log lines
npm test > /tmp/agent-test.log 2>&1
status=$?
tail -n 80 /tmp/agent-test.log
exit "$status"
```

Treat these as illustrative patterns. Use commands and paths appropriate to the project, and avoid putting sensitive logs in publicly readable paths.

### Pi integration (implementation, not just prompting)

If running Pi, a `tool_result` extension can cap model-facing tool text *before* the next model call. For an existing implementation, use `pi-output-limits`; configure caps in `~/.pi/agent/settings.json` (global) or `.pi/settings.json` (project). Installing it with default settings does **not** reduce limits: change its `outputLimits` values. The example configuration is at `examples/pi-output-limits.settings.json` within the Laconic repository; **merge** its `outputLimits` block into your existing settings, do not replace the entire file.

- Start conservatively: allow more content for `read`, less for noisy `bash` output.
- Preserve full-result recovery pointers; do not treat truncation as a source of truth.
- Keep error flags and exit status intact.
- Be aware that re-reading truncated output can negate token savings.
- This skill can guide tool calls, but cannot enforce hard caps on its own. The Pi extension is optional and installed separately.

### Laconic native runtime (experimental)

In addition to the independent `pi-output-limits` extension above, this repository contains a harness-neutral [native runtime](../docs/native-runtime.md) with a small deterministic engine, native Pi/Claude adapters, observation-only Codex integration, and an MCP stdio gateway. OpenCode uses the gateway; native installation is unavailable for the checked V2 API. It shortens only supported model-visible tool results when full recovery is available. No generic Codex tool-result replacement is claimed. Unlike `SKILL.md`, enabling runtime hooks executes local code with your user permissions and requires an explicit `laconic setup` command. Check the runtime guide for installed paths, privacy risks, and current validation limits.

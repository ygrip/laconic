# Laconic Runtime: native tool-output hooks

Laconic's root `SKILL.md` remains portable Markdown instructions. The optional runtime filters *model-visible tool results* before the next agent request. It does not rephrase final messages or use a second LLM. No claim of net token or billing savings is made without real measured runs.

## Capabilities and limitations

| Harness | Model-facing replacement | Scope | Recovery |
| --- | --- | --- | --- |
| Pi | Yes (`tool_result`) | Single text block; native Bash display-text exception preserves raw structured output; arbitrary structured/multimodal results pass through | `laconic_read_result` (JSON Schema; no SDK dependency) and CLI |
| Claude Code | Yes (`PostToolUse.updatedToolOutput`) | Successful Bash/PowerShell `stdout` with matching native schema only | CLI |
| OpenCode | Not implemented | Current `@opencode-ai/plugin` 1.18.35 has no V2 tool-hook API; setup fails explicitly | MCP gateway only |
| Codex | No general native replacement | Optional `PostToolUse` observer emits no extra context | MCP gateway only |
| Any MCP stdio client | Yes for tools served through Laconic's proxy | One text content block, no `isError` or `structuredContent` | `laconic_read_result` and CLI |

Native adapters use a shared deterministic processor. Other tools and errors are passed through unless an adapter explicitly supports their shape. Built-in tools not routed over MCP remain outside the MCP gateway's scope.

Pi is exercised in real CLI sessions by the [runtime benchmark](pi-e2e-runtime.md). Pi 1.1.0 always emits native Bash `structuredContent` (`output`, `truncated`, `exit_code`, `wall_time_seconds`, optional `full_output_path`). The adapter recognizes only this exact typed shape and returns it **unchanged alongside shortened display text**, preserving programmatic callers and exit status. Matching name/shape is not a provenance guarantee: trusted extensions can override Bash. PowerShell is not covered by this structured-shell exception until its actual shape is verified. This is reversible display summarization, **not redaction**; raw machine-readable output remains available. Claude and Codex remain source-level integrations, **not verified end-to-end against installed external binaries**. Bridge logic and the gateway have Node coverage; these tests alone do not establish native compatibility. The [current Claude hook reference](https://code.claude.com/docs/en/hooks#posttooluse-decision-control) documents built-in Bash-shaped `updatedToolOutput`, but older releases may lack it. The proposed OpenCode `@opencode-ai/plugin/v2` import is not exported by 1.18.35, and its V2 context has no `tool` domain; this runtime does not install a nonfunctional plugin or claim V1 replacement.

## Install the runtime

Requires Node 20+. From a cloned source checkout:

```bash
node bin/laconic.mjs setup --harness pi --scope user
node bin/laconic.mjs setup --harness claude --scope user
# OpenCode: register the MCP proxy below; native setup is unavailable.
# Codex cannot replace generic results via current documented native hook. Observer is opt-in:
node bin/laconic.mjs setup --harness codex --scope user --observe
```

With a **future** published `@ygrip/laconic` package, use `npx @ygrip/laconic setup --harness pi --scope user`. The package is not published by this PR. The Agent Skill can still be installed separately with `npx skills add ygrip/laconic`.

Project installations use `--scope project --project /path/to/repo` and create native settings under `.pi/`, `.claude/`, or `.codex/`. User Pi uses `~/.pi/agent/extensions/laconic.ts`: Pi 1.1.0 discovers `.ts` and `.js`, not `.mjs`, in this directory. Codex observation requires hooks enabled (currently the default), review/trust of the exact hook definition through `/hooks`, and project trust for project-local hooks; setup does not bypass those permissions. See the [Codex hooks guide](https://developers.openai.com/codex/hooks).

The setup copies the standalone runtime into `~/.local/share/laconic/` and installs small per-harness shims or merges a hook entry. Shell-hook command quoting is POSIX-oriented; Windows automatic hook setup is not verified. If an earlier PR snapshot installed the unsupported OpenCode shim, remove it with `disable --harness opencode` in the same scope. Existing unrelated hook entries are preserved, and unmanaged shim files will not be overwritten. No service runs in the background; no CI is invoked. Review hook installation carefully: it executes local code with the privileges of your agent.

Run `node bin/laconic.mjs status`, `doctor`, or `disable --harness ...` from the checkout. To update installed runtime code after editing it, rerun setup.

## MCP gateway (P3)

The gateway is a JSON-RPC stdio proxy, not a replacement MCP server. You configure an MCP client to launch Laconic *instead of* the upstream server:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["/absolute/path/to/laconic/bin/laconic.mjs", "proxy", "--", "node", "/absolute/path/to/my-mcp-server.mjs"]
    }
  }
}
```

Use the appropriate MCP configuration format for the target harness. The final `tools/list` page adds `laconic_read_result` for requesting additional lines, only after checking all pages for an upstream name collision. Calls before discovery route upstream, and filtering starts only after recovery is advertised. The proxy preserves request IDs, notifications, `initialize`, and untouched tool responses. It filters only supported *successful plain-text* tool results. It neither filters built-in agent tools nor proxies arbitrary HTTP transports. If the upstream server already declares `laconic_read_result`, the gateway avoids adding a duplicate and passes that tool through.

The child server runs with the gateway's user permissions and environment. Register only trusted MCP servers. Keep stdin/stdout strictly protocol JSON: gateway diagnostics go to stderr. The proxy does not inspect or modify tool parameters.

## Configuration

Create `~/.config/laconic/config.json` or set `LACONIC_CONFIG=/absolute/path/config.json`:

```json
{
  "enabled": true,
  "minBytes": 6000,
  "budgets": {"shell": 8192, "test": 12288, "search": 8192},
  "allowedCategories": ["shell", "test", "search"],
  "recovery": {"enabled": true, "maxStoredBytes": 2000000, "retentionHours": 24}
}
```

The defaults are conservative. Code reads, git diffs, unknown, structured, multimodal, and small results pass through. Shell output from `git diff`, `git show`, and file reads also passes through. The filter retains bounded head/tail, diagnostic excerpts, result counts, and a recovery ID; it **does not guarantee** every error is included in one excerpt.

`recovery.enabled=true` stores full tool output **on the user's machine** before shortening it in an owner-only directory at `~/.cache/laconic/results/` (override with `LACONIC_STORE_DIR`). Files use mode 0600, random opaque IDs, a 2 MB per-result default cap, and best-effort time-based cleanup. On POSIX systems, existing store directories must be owner-only (0700), current-user-owned, and not symlinks; recovery rejects symlinked or non-private files. Windows ACL isolation has not been verified; POSIX mode bits are not a Windows privacy guarantee. Disable recovery on Windows unless you separately enforce and validate private ACLs. Stored text is the complete result **received from the host**, not output already omitted by an upstream tool or harness. **Logs may contain credentials or other private content.** Turn recovery off for sensitive data; this also disables lossy filtering. No remote upload is performed. This is not encryption, redaction, or guaranteed secure deletion. The cap is per result, not an aggregate disk quota; high-volume sessions can retain many files until cleanup. Use a dedicated private store and external disk/retention controls where required.

Recover a range:

```bash
node bin/laconic.mjs show lr_0123456789abcdef0123456789abcdef --from 100 --count 80
```

Missing IDs and results already removed by cleanup fail explicitly; time-based expiry is opportunistic, not a guaranteed deletion deadline. The model should not treat shortened output as exhaustive. A stored result may be unavailable after expiry, deletion or when the maximum store size is exceeded; in the latter case the original result is passed through.

## Development and validation

```bash
npm test
npm run check
```

Tests cover routing, idempotent registration, recovery, unchanged critical shapes, permissions, symlinks, packaging, and a mock MCP stdio server including exit/spawn failures and recovery-name collisions. A separate local benchmark measured four arms (baseline, skill, runtime, both) and two workflows (usage repair and noisy-log triage plus repair). Only its [summary report](pi-e2e-runtime.md) and aggregate/paired measurements are published; benchmark scripts, raw sessions and generated artifacts are intentionally excluded from Git.

## Design choices

- **Fail open:** filter/storage/decoding errors preserve original output rather than inject unverified summaries.
- **Adapter capabilities:** native replacement is used only where the host exposes it; no misleading cross-harness parity.
- **No model-based summarization:** avoids another billable inference per result.
- **No silent data loss:** if full recovery cannot be saved, no irreversible truncation occurs.
- **Not a shell interceptor:** only model-visible tool messages are changed; side effects and upstream tool exit status stay intact.

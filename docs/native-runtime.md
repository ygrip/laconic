# Laconic Runtime: native tool-output hooks

Laconic's root `SKILL.md` remains portable Markdown instructions. The optional runtime filters *model-visible tool results* before the next agent request. It does not rephrase final messages or use a second LLM. No claim of net token or billing savings is made without real measured runs.

## Capabilities and limitations

| Harness | Model-facing replacement | Scope | Recovery |
| --- | --- | --- | --- |
| Pi | Yes (`tool_result`) | Single text block; skips structured/multimodal results | `laconic_read_result` when TypeBox is resolvable; otherwise CLI |
| Claude Code | Yes (`PostToolUse.updatedToolOutput`) | Successful Bash/PowerShell `stdout` with matching native schema only | CLI |
| OpenCode V2 | Yes (`ctx.tool.hook('execute.after')`) | Completed terminal string `content` only | CLI |
| Codex | No general native replacement | Optional `PostToolUse` observer emits no extra context | MCP gateway only |
| Any MCP stdio client | Yes for tools served through Laconic's proxy | One text content block, no `isError` or `structuredContent` | `laconic_read_result` and CLI |

Native adapters use a shared deterministic processor. Other tools and errors are passed through unless an adapter explicitly supports their shape. Built-in tools not routed over MCP remain outside the MCP gateway's scope.

These adapters are source-level integrations, **not verified end-to-end against installed external Pi/Claude/OpenCode/Codex binaries**. Their bridge logic and the gateway are covered by Node tests. Treat runtime compatibility as unverified until each harness is exercised and model-visible output inspected.

## Install the runtime

Requires Node 20+. From a cloned source checkout:

```bash
node bin/laconic.mjs setup --harness pi --scope user
node bin/laconic.mjs setup --harness claude --scope user
node bin/laconic.mjs setup --harness opencode --scope user
# Codex cannot replace generic results via current documented native hook. Observer is opt-in:
node bin/laconic.mjs setup --harness codex --scope user --observe
```

With a **future** published `@ygrip/laconic` package, use `npx @ygrip/laconic setup --harness pi --scope user`. The package is not published by this PR. The Agent Skill can still be installed separately with `npx skills add ygrip/laconic`.

Project installations use `--scope project --project /path/to/repo` and create native settings under `.pi/`, `.claude/`, `.opencode/`, or `.codex/`. User Pi uses `~/.pi/agent/extensions/`, OpenCode uses `~/.config/opencode/plugins/`.

The setup copies the standalone runtime into `~/.local/share/laconic/` and installs small per-harness shims or merges a hook entry. Existing unrelated hook entries are preserved, and unmanaged shim files will not be overwritten. No service runs in the background; no CI is invoked. Review hook installation carefully: it executes local code with the privileges of your agent.

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

Use the appropriate MCP configuration format for the target harness. A `tools/list` response adds `laconic_read_result` for requesting additional lines. The proxy preserves request IDs, notifications, `initialize`, and untouched tool responses. It filters only supported *successful plain-text* tool results. It neither filters built-in agent tools nor proxies arbitrary HTTP transports. If the upstream server already declares `laconic_read_result`, the gateway avoids adding a duplicate and passes that tool through.

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

`recovery.enabled=true` stores full tool output **on the user's machine** before shortening it in an owner-only directory at `~/.cache/laconic/results/` (override with `LACONIC_STORE_DIR`). Files use mode 0600, random opaque IDs, a 2 MB per-result default cap, and best-effort time-based cleanup. **Logs may contain credentials or other private content.** Turn recovery off for sensitive data; this also disables lossy filtering. No remote upload is performed. This is not encryption, redaction, or guaranteed secure deletion.

Recover a range:

```bash
node bin/laconic.mjs show lr_0123456789abcdef0123456789abcdef --from 100 --count 80
```

Missing/expired IDs fail explicitly. The model should not treat shortened output as exhaustive. A stored result may be unavailable after expiry, deletion or when the maximum store size is exceeded; in the latter case the original result is passed through.

## Development and validation

```bash
npm test
npm run check
```

Tests cover routing, idempotent registration, recovery, unchanged critical shapes, and a mock MCP stdio server. They do not execute actual provider sessions. Before claiming usage savings, extend `benchmarks/pi-e2e` to measure four arms (baseline, skill, runtime, both) across multiple real tool-heavy tasks, acceptance checks, retries, latency and cache-aware cost. Keep the original benchmark reports untouched.

## Design choices

- **Fail open:** filter/storage/decoding errors preserve original output rather than inject unverified summaries.
- **Adapter capabilities:** native replacement is used only where the host exposes it; no misleading cross-harness parity.
- **No model-based summarization:** avoids another billable inference per result.
- **No silent data loss:** if full recovery cannot be saved, no irreversible truncation occurs.
- **Not a shell interceptor:** only model-visible tool messages are changed; side effects and upstream tool exit status stay intact.

/** Claude Code PostToolUse command hook. Must print only official hook JSON to stdout. */
import { optimizeText } from '../core/engine.mjs';
import { loadPolicy } from '../core/config.mjs';

export async function transformClaude(input, policy) {
  if (input?.hook_event_name !== 'PostToolUse' || !['Bash','PowerShell'].includes(input.tool_name)) return null;
  const source = input.tool_response;
  // Claude's built-in output types are structured: replace only a known field.
  if (!source || typeof source !== 'object' || typeof source.stdout !== 'string' ||
      typeof source.stderr !== 'string' || source.isImage) return null;
  // Never compact a failing shell result: retain stderr, exit diagnostics and exact context.
  if (source.stderr.length || source.interrupted || source.exitCode > 0) return null;
  const outcome = await optimizeText({harness:'claude-code',name:'bash',args:input.tool_input,
    text:source.stdout,policy});
  if (!outcome.changed) return null;
  return {hookSpecificOutput:{hookEventName:'PostToolUse',
    updatedToolOutput:{...source,stdout:outcome.content}}};
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  let body='';
  try {
    for await (const chunk of process.stdin) body+=chunk;
    const result=await transformClaude(JSON.parse(body), await loadPolicy());
    if (result) process.stdout.write(JSON.stringify(result)+'\n');
  } catch { /* Silent fail-open: Claude uses the original tool result. */ }
}

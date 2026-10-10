/** Pi's model-facing tool_result hook. No Pi imports are needed for interception. */
import { optimizeText } from '../core/engine.mjs';
import { readResult } from '../core/store.mjs';
import { loadPolicy } from '../core/config.mjs';

// Pi 1.1.0's built-in bash has separate display text and raw programmatic output.
// This is a compatibility shape check, not proof of builtin provenance: trusted
// extensions may override the tool. Unknown structured APIs still pass through.
function nativeBashResult(event) {
  const value = event?.structuredContent;
  return event?.toolName === 'bash' && value && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).every(key => ['output','truncated','exit_code','wall_time_seconds','full_output_path'].includes(key)) &&
    typeof value.output === 'string' && typeof value.truncated === 'boolean' &&
    Number.isSafeInteger(value.exit_code) && Number.isFinite(value.wall_time_seconds) && value.wall_time_seconds >= 0 &&
    (!Object.hasOwn(value,'full_output_path') || (value.truncated && typeof value.full_output_path === 'string'));
}
export async function transformPi(event, policy) {
  const content = event?.content;
  const native = nativeBashResult(event);
  if (!Array.isArray(content) || (event?.structuredContent !== undefined && !native) ||
      content.length !== 1 || content[0]?.type !== 'text') return null;
  const outcome = await optimizeText({harness:'pi', name:event.toolName,
    args:event.input, text:content[0].text, isError:event.isError,
    exitCode:event.details?.exitCode ?? (native ? event.structuredContent.exit_code : undefined), policy});
  if (!outcome.changed) return null;
  return { content: [{...content[0], text:outcome.content}],
    // Omitting this would make Pi discard the raw structured result. Machine
    // callers must continue receiving the exact original output and status.
    ...(native ? {structuredContent:event.structuredContent} : {}) };
}

export default async function laconicPi(pi) {
  const policy = await loadPolicy();
  pi.on('tool_result', async event => transformPi(event, policy));
  // Pi accepts JSON Schema parameters; avoid runtime package resolution from the
  // standalone deployed directory (which has no host node_modules).
  if (policy.enabled && policy.recovery.enabled) {
      pi.registerTool({
        name: 'laconic_read_result', label: 'Laconic result recovery',
        description: 'Read more lines from a tool result shortened by Laconic. Use the lr_ recovery ID.',
        parameters: {
          type: 'object', properties: {
            id: {type:'string', pattern:'^lr_[a-f0-9]{32}$'},
            from: {type:'integer', minimum:1},
            count: {type:'integer', minimum:1, maximum:500}
          }, required:['id'], additionalProperties:false
        },
        async execute(_toolCallId, params) {
          try {
            const found = await readResult(params.id, {from:params.from ?? 1, count:params.count ?? 100});
            return {content:[{type:'text', text:`Lines ${found.from}-${found.to}/${found.totalLines}\n${found.text}`}], details:undefined};
          } catch (error) { throw new Error(`Laconic recovery failed: ${error.message}`); }
        }
      });
  }
}

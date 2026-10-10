/** Pi's model-facing tool_result hook. No Pi imports are needed for interception. */
import { optimizeText } from '../core/engine.mjs';
import { readResult } from '../core/store.mjs';
import { loadPolicy } from '../core/config.mjs';

export async function transformPi(event, policy) {
  const content = event?.content;
  if (!Array.isArray(content) || event?.structuredContent !== undefined ||
      content.length !== 1 || content[0]?.type !== 'text') return null;
  const outcome = await optimizeText({harness:'pi', name:event.toolName,
    args:event.input, text:content[0].text, isError:event.isError,
    exitCode:event.details?.exitCode, policy});
  if (!outcome.changed) return null;
  return { content: [{...content[0], text:outcome.content}] };
}

export default async function laconicPi(pi) {
  const policy = await loadPolicy();
  pi.on('tool_result', async event => transformPi(event, policy));
  // Prefer a model-callable recovery tool over a shell command when TypeBox is available.
  // Dynamic resolution keeps the filtering hook usable in Pi builds with different packages.
    try {
      const { Type } = await import('@sinclair/typebox');
      pi.registerTool({
        name: 'laconic_read_result', label: 'Laconic result recovery',
        description: 'Read more lines from a tool result shortened by Laconic. Use the lr_ recovery ID.',
        parameters: Type.Object({
          id: Type.String(),
          from: Type.Optional(Type.Number({minimum:1})),
          count: Type.Optional(Type.Number({minimum:1, maximum:500}))
        }),
        async execute(_toolCallId, params) {
          try {
            const found = await readResult(params.id, {from:params.from ?? 1, count:params.count ?? 100});
            return {content:[{type:'text', text:`Lines ${found.from}-${found.to}/${found.totalLines}\n${found.text}`}], details:undefined};
          } catch (error) { return {content:[{type:'text', text:`Laconic recovery failed: ${error.message}`}], details:undefined, isError:true}; }
        }
      });
    } catch { /* Recovery remains available via the local Laconic CLI. */ }
}

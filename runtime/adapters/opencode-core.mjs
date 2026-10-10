import { optimizeText } from '../core/engine.mjs';
import { loadPolicy } from '../core/config.mjs';
/** OpenCode V2: terminal tool hook values are mutable. Leave errors and structured results intact. */
export async function transformOpenCode(event, policy) {
  if (event?.status !== 'completed' || typeof event?.result?.content !== 'string') return false;
  const result=await optimizeText({harness:'opencode-v2',name:event.tool,
    args:event.input, text:event.result.content,policy:policy ?? await loadPolicy()});
  if (!result.changed) return false;
  event.result={...event.result,content:result.content};
  return true;
}

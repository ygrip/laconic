/** OpenCode V2 API only: V1 output mutation may not propagate to the model. */
import { Plugin } from '@opencode-ai/plugin/v2';
import { transformOpenCode } from './opencode-core.mjs';
export default Plugin.define({
  id: 'laconic.output',
  async setup(ctx) {
    await ctx.tool.hook('execute.after', async event => {
      try { await transformOpenCode(event); } catch { /* Pass through unchanged. */ }
    });
  }
});

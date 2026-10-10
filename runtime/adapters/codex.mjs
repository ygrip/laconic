/** Codex PostToolUse observer. Native hook results cannot safely replace arbitrary output. */
/** Deliberately does not parse and persist tool contents or inject extra model context. */
export const CODEX_CAPABILITIES = Object.freeze({
  observeResult: true, replaceResult: false, replaceStructuredResult: false,
  recoverFullResult: false
});
export function transformCodex() { return null; }
if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  try { for await (const _ of process.stdin) {} } catch { /* Hook should never block a tool. */ }
  process.stdout.write('{}\n');
}

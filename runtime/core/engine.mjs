/** Pure planning and evidence selection. The only side effect is optional recovery storage. */
import { saveResult } from './store.mjs';

const ERROR = /(?:\berror\b|\bfailed?\b|\bexception\b|\btraceback\b|\bpanic\b|\bfatal\b|\bwarning\b|\bwarn\b|\bassert(?:ion)?\b|^\s*at\s+\S+|^\s*Caused by:|^\s*FAIL\b)/i;
const SUMMARY = /(?:\b\d+\s+(?:passing|passed|failed|skipped|tests?)\b|\btest suites?:|\btests?:|\bexit(?:ed)?(?: code| status)?\s*[:=]?\s*\d+|\bbuild\s+(?:success|failure)|^\s*total\s*:)/i;
const categoryFor = (name, args = {}) => {
  const tool = String(name ?? '').toLowerCase();
  const command = String(args?.command ?? args?.cmd ?? '');
  if (/\b(?:test|pytest|jest|vitest|unittest|mvn test|gradle test|go test|cargo test)\b/i.test(command) || /(?:^|_)test(?:$|_)/.test(tool)) return 'test';
  if (/\bgit\s+(diff|show|apply|status|log)\b/.test(command)) return 'git';
  if (/\b(?:cat|sed|head)\s+[^|]+/.test(command) && !/\|/.test(command)) return 'file';
  if (/(?:grep|search|ripgrep|find|glob)/.test(tool) || tool === 'rg' || /\b(?:rg|grep|find)\s+/.test(command)) return 'search';
  if (/(?:bash|shell|exec|terminal|command)/.test(tool)) return 'shell';
  if (/(?:read|file|cat)/.test(tool)) return 'file';
  if (/(?:git|diff|patch)/.test(tool)) return 'git';
  return 'unknown';
};
export const DEFAULT_POLICY = Object.freeze({
  enabled: true, minBytes: 6_000,
  budgets: { shell: 8_192, test: 12_288, search: 8_192, file: 24_576, git: 24_576, unknown: 16_384 },
  // File reads, diffs, structured APIs and unknown tools are too risky to truncate blindly.
  allowedCategories: ['shell', 'test', 'search'],
  recovery: { enabled: true, maxStoredBytes: 2_000_000, retentionHours: 24 }
});
export function mergePolicy(input = {}) {
  return {
    ...DEFAULT_POLICY,
    ...input,
    budgets: { ...DEFAULT_POLICY.budgets, ...(input.budgets || {}) },
    recovery: { ...DEFAULT_POLICY.recovery, ...(input.recovery || {}) }
  };
}

function buildExcerpt(text, maxBytes) {
  const lines = text.split('\n');
  const keep = new Set();
  const choose = i => { if (i >= 0 && i < lines.length) keep.add(i); };
  for (let i = 0; i < Math.min(10, lines.length); i++) choose(i);
  for (let i = Math.max(0, lines.length - 15); i < lines.length; i++) choose(i);
  const matched = [];
  for (let i = 0; i < lines.length; i++) if (ERROR.test(lines[i]) || SUMMARY.test(lines[i])) matched.push(i);
  // Error evidence has priority, followed by summaries and nearby stack lines.
  for (const i of matched.slice(0, 40)) for (let offset = -1; offset <= 2; offset++) choose(i + offset);
  const sorted = [...keep].sort((a,b)=>a-b);
  let excerpt = '', last = -1, displayed = 0;
  for (const i of sorted) {
    let line = lines[i];
    if (line.length > 2_048) line = line.slice(0, 2_048) + ' [line shortened]';
    const gap = last !== -1 && i > last + 1 ? `\n[... ${i-last-1} lines omitted ...]\n` : (last < 0 ? '' : '\n');
    const next = gap + `[${i+1}] ${line}`;
    if (Buffer.byteLength(excerpt + next, 'utf8') > Math.max(256, maxBytes - 220)) break;
    excerpt += next;
    displayed++;
    last = i;
  }
  return { excerpt, displayed, lines: lines.length };
}

/** Optimize a plain UTF-8 text value. Any failure returns the original (fail open). */
export async function optimizeText({ harness='unknown', name='', args={}, text, isError=false, exitCode, policy={} }) {
  const settings = mergePolicy(policy);
  const category = categoryFor(name, args);
  const originalBytes = Buffer.byteLength(String(text ?? ''), 'utf8');
  const unchanged = { content: text, changed: false, truncated: false, category, originalBytes, resultingBytes: originalBytes };
  if (!settings.enabled || typeof text !== 'string' || originalBytes < settings.minBytes ||
      !settings.allowedCategories.includes(category)) return unchanged;
  const budget = settings.budgets[category];
  if (!Number.isFinite(budget) || budget < 512 || originalBytes <= budget) return unchanged;
  if (!settings.recovery?.enabled) return unchanged;
  try {
    // Store before compression. If storage fails, do not drop evidence.
    const recoveryId = await saveResult(text, settings.recovery);
    if (!recoveryId) return unchanged;
    const {excerpt, displayed, lines} = buildExcerpt(text, budget);
    const status = exitCode !== undefined ? ` Exit code: ${exitCode}.` : (isError ? ' Tool reported an error.' : '');
    const footer = `\n[Laconic: partial ${category} output (${displayed}/${lines} lines, ${originalBytes} bytes).${status} Full result: laconic show ${recoveryId} --from N --count 100]`;
    const content = excerpt + footer;
    if (Buffer.byteLength(content, 'utf8') >= originalBytes || Buffer.byteLength(content, 'utf8') > budget) return unchanged;
    return { content, changed: true, truncated: true, category, originalBytes,
      resultingBytes: Buffer.byteLength(content, 'utf8'), recoveryId, harness };
  } catch { return unchanged; }
}

export function optimizeMcpResult(result, replaceText) {
  if (!result || typeof result !== 'object' || !Array.isArray(result.content) || result.structuredContent !== undefined) return null;
  // Do not rewrite multimodal, structured, or failed MCP results.
  if (result.isError || result.content.some(c=>c?.type !== 'text' || typeof c.text !== 'string')) return null;
  return replaceText;
}
export { categoryFor };

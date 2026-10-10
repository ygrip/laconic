/** Pure planning and evidence selection. The only side effect is optional recovery storage. */
import { saveResult } from './store.mjs';

const ERROR = /(?:\berror\b|\bfailed?\b|\bexception\b|\btraceback\b|\bpanic\b|\bfatal\b|\bwarning\b|\bwarn\b|\bassert(?:ion)?\b|^\s*at\s+\S+|^\s*Caused by:|^\s*FAIL\b)/i;
const SUMMARY = /(?:\b\d+\s+(?:passing|passed|failed|skipped|tests?)\b|\btest suites?:|\btests?:|\bexit(?:ed)?(?: code| status)?\s*[:=]?\s*\d+|\bbuild\s+(?:success|failure)|^\s*total\s*:)/i;
const categoryFor = (name, args = {}) => {
  const tool = String(name ?? '').toLowerCase().split('__').at(-1);
  const command = String(args?.command ?? args?.cmd ?? '');
  // Protect source and diffs even in pipelines/compound commands or commands mentioning tests.
  if (/\bgit\b[^\n;&|]*\b(?:diff|show|apply|status|log)\b/.test(command) || ['git_diff','git_show','diff','patch'].includes(tool)) return 'git';
  if (/\b(?:cat|sed|head|tail|Get-Content)\b/i.test(command) || ['read','read_file','file','cat'].includes(tool)) return 'file';
  if (['grep','search','ripgrep','find','glob','rg'].includes(tool)) return 'search';
  // A tool with an incidental substring (e.g. execute_payment) is NOT a shell.
  if (!['bash','powershell','shell','exec','execute','terminal','command','test','run_tests'].includes(tool)) return 'unknown';
  if (/\b(?:test|pytest|jest|vitest|unittest)\b/i.test(command) || ['test','run_tests'].includes(tool)) return 'test';
  if (/\b(?:rg|grep|find)\s+/.test(command)) return 'search';
  if (tool) return 'shell';
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
  const render = () => {
    let last = -1;
    return [...keep].sort((a,b)=>a-b).map(i => {
      const gap = i > last + 1 ? `[... ${i-last-1} lines omitted ...]\n` : '';
      last = i;
      return gap + `[${i+1}] ${lines[i]}`;
    }).join('\n');
  };
  const choose = i => {
    if (i < 0 || i >= lines.length || keep.has(i)) return;
    keep.add(i);
    if (Buffer.byteLength(render(), 'utf8') > maxBytes) keep.delete(i);
  };
  const errors = [], summaries = [], warnings = [];
  for (let i = 0; i < lines.length; i++) {
    if (ERROR.test(lines[i])) (/\bwarn(?:ing)?\b/i.test(lines[i]) ? warnings : errors).push(i);
    if (SUMMARY.test(lines[i])) summaries.push(i);
  }
  // Select by importance BEFORE rendering in source order. Long head lines must not
  // consume the budget and hide a failure or a final test summary.
  for (const matches of [errors, summaries]) {
    if (matches.length) { choose(matches[0]); choose(matches.at(-1)); }
    for (const i of matches.slice(0, 40)) choose(i);
  }
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 15); i--) choose(i);
  for (const i of errors.slice(0, 40)) for (const offset of [-1, 1, 2]) choose(i + offset);
  for (let i = 0; i < Math.min(10, lines.length); i++) choose(i);
  for (const i of warnings.slice(0, 10)) choose(i);
  return { excerpt: render(), displayed: keep.size, lines: lines.length };
}

/** Optimize a plain UTF-8 text value. Any failure returns the original (fail open). */
export async function optimizeText({ harness='unknown', name='', args={}, text, isError=false, exitCode, policy={} }) {
  const category = categoryFor(name, args);
  const originalBytes = Buffer.byteLength(String(text ?? ''), 'utf8');
  const unchanged = { content: text, changed: false, truncated: false, category, originalBytes, resultingBytes: originalBytes };
  try {
    if (!policy || typeof policy !== 'object' || Array.isArray(policy) ||
        (Object.hasOwn(policy, 'recovery') && !policy.recovery)) return unchanged;
    const settings = mergePolicy(policy);
    if (!settings.enabled || typeof text !== 'string' || originalBytes < settings.minBytes ||
        !settings.allowedCategories.includes(category)) return unchanged;
    const budget = settings.budgets[category];
    if (!Number.isFinite(budget) || budget < 512 || originalBytes <= budget) return unchanged;
    if (!settings.recovery?.enabled) return unchanged;
    // A shell can print a structured document too. Do not silently destroy its schema.
    if (/^\s*[\[{]/.test(text)) {
      try { const value = JSON.parse(text); if (value && typeof value === 'object') return unchanged; } catch {}
    }
    // Store before compression. If storage fails, do not drop evidence.
    const recoveryId = await saveResult(text, settings.recovery);
    if (!recoveryId) return unchanged;
    const status = exitCode !== undefined ? ` Exit code: ${exitCode}.` : (isError ? ' Tool reported an error.' : '');
    const totalLines = text.split('\n').length;
    const makeFooter = displayed => `\n[Laconic: partial ${category} output (${displayed}/${totalLines} lines, ${originalBytes} bytes).${status} Recover with laconic_read_result id=${recoveryId}, or node <laconic>/bin/laconic.mjs show ${recoveryId} --from N --count 100]`;
    const {excerpt, displayed} = buildExcerpt(text, budget - Buffer.byteLength(makeFooter(totalLines), 'utf8'));
    // If no complete evidence line fits, preserve the original rather than a misleading stub.
    if (!displayed) return unchanged;
    const footer = makeFooter(displayed);
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

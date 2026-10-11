/** Pure planning and evidence selection. Side effects: optional recovery storage and local stats. */
import { saveResult, recordEvent } from './store.mjs';

// Diagnostic lines are grouped by a normalized signature so each distinct failure
// survives compression, instead of the first N occurrences of one noisy failure.
const DIAG = /(?:\berror\b|\berrors?:|\berr!|\bfail(?:ed|ure|ures|s|ing)?\b|\bexception\b|\btraceback\b|\bpanic(?:ked)?\b|\bfatal\b|\bcritical\b|\bincident\b|\bassert(?:ion)?(?:error)?\b|\bdenied\b|\brefused\b|\btimed?\s?out\b|\bunhandled\b|\bsegmentation fault\b|\bcannot\b|\bcan't\b|\bunable to\b|\bnot found\b|\bmissing\b|\binvalid\b|\bunexpected\b|^\s*Caused by:|^\s*not ok\b|^\s*E\s{2,}\S|\berror\[E\d+\]|\bTS\d{4}\b|[✗✖×]\s)/i;
const WARN = /\bwarn(?:ing)?s?\b|\bdeprecat/i;
const STACK = /^\s*(?:at\s+\S+|File ".*", line \d+|Caused by:|\.\.\. \d+ more|-->|\|\s|\^)/;
const SUMMARY = /(?:\b\d+\s+(?:passing|passed|failed|failing|skipped|errors?|warnings?|tests?)\b|\btest suites?:|\btests?:|\bexit(?:ed)?(?: code| status)?\s*[:=]?\s*\d+|\bbuild\s+(?:success|failure|failed)|^\s*total\s*:|^\s*summary\b)/i;
const ZERO_ONLY = /^(?=.*\b0\s+(?:errors?|failed|failures?|failing)\b)(?!.*\b[1-9]\d*\s+(?:errors?|failed|failures?|failing)\b)/i;
const SCAN_CHARS = 4_000;

const categoryFor = (name, args = {}) => {
  const tool = String(name ?? '').toLowerCase().split('__').at(-1);
  const command = String(args?.command ?? args?.cmd ?? '');
  // Protect source and diffs even in pipelines/compound commands or commands mentioning tests.
  if (/\bgit\b[^\n;&|]*\b(?:diff|show|apply|status|log)\b/.test(command) || ['git_diff','git_show','diff','patch'].includes(tool)) return 'git';
  if (/\b(?:cat|sed|head|tail|nl|bat|less|more|Get-Content)\b/i.test(command) || ['read','read_file','file','cat'].includes(tool)) return 'file';
  if (['grep','search','ripgrep','find','glob','rg'].includes(tool)) return 'search';
  // A tool with an incidental substring (e.g. execute_payment) is NOT a shell.
  if (!['bash','powershell','shell','exec','execute','terminal','command','test','run_tests'].includes(tool)) return 'unknown';
  if (/\b(?:test|pytest|jest|vitest|unittest)\b/i.test(command) || ['test','run_tests'].includes(tool)) return 'test';
  if (/\b(?:rg|grep|find)\s+/.test(command)) return 'search';
  if (tool) return 'shell';
  return 'unknown';
};

/**
 * Task-aware starting policies. The goal is lower total task cost/time, not the smallest
 * first response: profiles that need coverage (review) never compress search results.
 */
export const PROFILES = Object.freeze({
  // Moderate shell/test/search compression; search keeps a lossless location index.
  implementation: { allowedCategories: ['shell', 'test', 'search'],
    budgets: { shell: 8_192, test: 12_288, search: 8_192 }, diagnostics: { maxGroups: 24, context: 2 } },
  // Preserve search coverage, file reads and diffs; compress repetitive logs only.
  review: { allowedCategories: ['shell', 'test'],
    budgets: { shell: 12_288, test: 16_384 }, diagnostics: { maxGroups: 32, context: 2 } },
  // Preserve diagnostic clusters with wider cause context and recovery access.
  debugging: { allowedCategories: ['shell', 'test', 'search'],
    budgets: { shell: 16_384, test: 20_480, search: 12_288 }, diagnostics: { maxGroups: 48, context: 4 } },
  // Mostly a prose concern: only noisy command logs are compressed.
  documentation: { allowedCategories: ['shell', 'test'],
    budgets: { shell: 8_192, test: 12_288 }, diagnostics: { maxGroups: 16, context: 1 } }
});
export const DEFAULT_POLICY = Object.freeze({
  enabled: true, minBytes: 6_000, profile: 'implementation',
  budgets: { shell: 8_192, test: 12_288, search: 8_192, file: 24_576, git: 24_576, unknown: 16_384 },
  // File reads, diffs, structured APIs and unknown tools are too risky to truncate blindly.
  allowedCategories: ['shell', 'test', 'search'],
  diagnostics: { maxGroups: 24, context: 2 },
  recovery: { enabled: true, maxStoredBytes: 2_000_000, retentionHours: 24, stats: true }
});
export function mergePolicy(input = {}) {
  const profile = Object.hasOwn(PROFILES, input.profile) ? input.profile : DEFAULT_POLICY.profile;
  const preset = PROFILES[profile];
  return {
    ...DEFAULT_POLICY,
    allowedCategories: preset.allowedCategories,
    ...input,
    profile,
    budgets: { ...DEFAULT_POLICY.budgets, ...preset.budgets, ...(input.budgets || {}) },
    diagnostics: { ...DEFAULT_POLICY.diagnostics, ...preset.diagnostics, ...(input.diagnostics || {}) },
    recovery: { ...DEFAULT_POLICY.recovery, ...(input.recovery || {}) }
  };
}

const bytes = value => Buffer.byteLength(value, 'utf8');
const clip = (line, max) => {
  if (line.length <= max) return line;
  const kept = [...line.slice(0, max + 1)].slice(0, max).join('');
  return `${kept}…[+${line.length - kept.length} chars]`;
};
/** Normalize volatile tokens so repeated failures collapse into one group. */
export function signature(line) {
  return line.slice(0, SCAN_CHARS).toLowerCase()
    .replace(/\b\d{4}-\d{2}-\d{2}[t ][\d:.,]+z?\b/g, '<ts>')
    .replace(/\b(?:0x)?[0-9a-f]{8,}\b/g, '<hex>')
    .replace(/(["'`])(?:(?!\1).){0,200}\1/g, '<str>')
    .replace(/\d+/g, '#')
    .replace(/\s+/g, ' ').trim().slice(0, 160);
}
const ranges = numbers => {
  const out = [];
  for (let i = 0; i < numbers.length; i++) {
    let j = i;
    while (j + 1 < numbers.length && numbers[j + 1] === numbers[j] + 1) j++;
    out.push(j > i ? `${numbers[i]}-${numbers[j]}` : String(numbers[i]));
    i = j;
  }
  return out.join(',');
};

/** Budgeted line picker. Size is tracked incrementally (O(log n) per pick), never re-rendered. */
function selector(lines, maxBytes, { gaps = true, lineChars = 1_000 } = {}) {
  const keep = new Set(), order = [];
  const lineCost = i => bytes(`[${i + 1}] ${clip(lines[i], lineChars)}`);
  // Bytes of the gap marker between kept indexes a < b (a = -1 means start of output).
  const gapCost = (a, b) => gaps && b > a + 1 ? bytes(`[... ${b - a - 1} lines omitted ...]\n`) : 0;
  let size = 0;
  const render = () => order.map((i, n) => {
    const prev = n ? order[n - 1] : -1;
    return (gaps && i > prev + 1 ? `[... ${i - prev - 1} lines omitted ...]\n` : '') + `[${i + 1}] ${clip(lines[i], lineChars)}`;
  }).join('\n');
  const choose = i => {
    if (i < 0 || i >= lines.length || keep.has(i)) return false;
    let lo = 0, hi = order.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (order[mid] < i) lo = mid + 1; else hi = mid; }
    const prev = lo ? order[lo - 1] : -1, next = order[lo];
    // Adding a line adds its text, one newline separator (if not alone), and re-splits a gap.
    let delta = lineCost(i) + (order.length ? 1 : 0) + gapCost(prev, i);
    if (next !== undefined) delta += gapCost(i, next) - gapCost(prev, next);
    if (size + delta > maxBytes) return false;
    size += delta; keep.add(i); order.splice(lo, 0, i);
    return true;
  };
  return { keep, render, choose };
}

/** Group unique diagnostics, warnings and summaries. Stack/cause frames are context, not groups. */
export function diagnose(lines) {
  const groups = new Map(), warnings = new Map(), summaries = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].length > SCAN_CHARS ? lines[i].slice(0, SCAN_CHARS) : lines[i];
    if (!line.trim()) continue;
    if (SUMMARY.test(line)) { summaries.push(i); continue; }
    if (STACK.test(line) && !/^\s*Caused by:/.test(line)) continue;
    const target = DIAG.test(line) && !ZERO_ONLY.test(line) ? groups : WARN.test(line) ? warnings : null;
    if (!target) continue;
    const key = signature(line);
    const group = target.get(key) || { key, lines: [] };
    group.lines.push(i);
    target.set(key, group);
  }
  return { groups: [...groups.values()], warnings: [...warnings.values()], summaries };
}

function buildLogExcerpt(text, maxBytes, settings) {
  const lines = text.split('\n');
  const { groups, warnings, summaries } = diagnose(lines);
  const { maxGroups, context } = settings.diagnostics;
  const listed = groups.slice(0, maxGroups);
  // A compact, always-present index of distinct failure groups (first line, count, last line).
  const header = groups.length ? `[Laconic diagnostics: ${groups.length} distinct failure group${groups.length === 1 ? '' : 's'}; ` +
    listed.map((g, n) => `#${n + 1} L${g.lines[0] + 1}${g.lines.length > 1 ? `×${g.lines.length} last L${g.lines.at(-1) + 1}` : ''}`).join(', ') +
    (groups.length > listed.length ? `, +${groups.length - listed.length} more groups` : '') + ']\n' : '';
  const budget = maxBytes - bytes(header);
  if (budget < 128) return { excerpt: '', displayed: 0, lines: lines.length, groups: groups.length, shownGroups: 0 };
  const { keep, render, choose } = selector(lines, budget, { lineChars: Math.max(200, Math.floor(budget / 6)) });
  // 1. One representative per distinct failure group, in first-seen order.
  for (const g of listed) choose(g.lines[0]);
  // 2. First and last summary (counts and exit status).
  if (summaries.length) { choose(summaries[0]); choose(summaries.at(-1)); }
  // 3. Cause context for each representative: the line before and up to `context` lines after.
  for (const g of listed) {
    const i = g.lines[0];
    for (let k = 1; k <= context; k++) choose(i + k);
    choose(i - 1);
  }
  // 4. Last occurrence of repeated groups shows whether the failure persisted.
  for (const g of listed) if (g.lines.length > 1) choose(g.lines.at(-1));
  // 5. Tail, remaining summaries, more occurrences, head, warnings.
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 15); i--) choose(i);
  for (const i of summaries.slice(0, 40)) choose(i);
  for (const g of groups.slice(listed.length)) choose(g.lines[0]);
  let extra = 0;
  for (const g of listed) for (const i of g.lines.slice(1, 4)) if (extra++ < 40) choose(i);
  for (let i = 0; i < Math.min(10, lines.length); i++) choose(i);
  for (const w of warnings.slice(0, 10)) choose(w.lines[0]);
  // 6. Spend leftover budget on wider cause context around each failure group. A larger
  // first excerpt is cheaper than an extra model round trip to recover nearby lines.
  // Windows grow contiguously: a line is added only next to an already-kept neighbour.
  for (let radius = 2; radius <= 12; radius++) {
    let any = false;
    for (const g of listed) {
      const i = g.lines[0];
      if (keep.has(i - radius + 1)) any = choose(i - radius) || any;
      if (radius > context && keep.has(i + radius - 1)) any = choose(i + radius) || any;
    }
    if (!any) break;
  }
  const shownGroups = groups.filter(g => g.lines.some(i => keep.has(i))).length;
  return { excerpt: header + render(), displayed: keep.size, lines: lines.length, groups: groups.length, shownGroups };
}

/** Recognize rg/grep -n, rg --heading and path-list output. Returns null for anything else. */
export function parseSearch(lines) {
  const entries = [];
  let heading = null, nonEmpty = 0, parsed = 0;
  const looksLikePath = s => /^[^\s:]+$/.test(s) && (s.includes('/') || /\.[A-Za-z0-9]{1,8}$/.test(s));
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) { heading = null; continue; }
    nonEmpty++;
    let m;
    if (line === '--') { parsed++; continue; }
    if (heading && (m = /^(\d+)([:-])/.exec(line))) {
      entries.push({ file: heading, line: Number(m[1]), match: m[2] === ':', index: i }); parsed++; continue;
    }
    if ((m = /^([^:\n]+?):(\d+):/.exec(line))) {
      entries.push({ file: m[1], line: Number(m[2]), match: true, index: i }); parsed++; heading = null; continue;
    }
    if ((m = /^(\S+?)-(\d+)-/.exec(line)) && looksLikePath(m[1])) {
      entries.push({ file: m[1], line: Number(m[2]), match: false, index: i }); parsed++; continue;
    }
    if (looksLikePath(line)) {
      if (/^\d+[:-]/.test(lines[i + 1] ?? '')) heading = line;
      else entries.push({ file: line, line: null, match: true, index: i });
      parsed++; continue;
    }
  }
  if (!nonEmpty || parsed / nonEmpty < 0.8 || !entries.some(e => e.match)) return null;
  return entries;
}

function buildSearchExcerpt(text, maxBytes) {
  const lines = text.split('\n');
  const entries = parseSearch(lines);
  if (!entries) return null;
  const files = new Map();
  for (const e of entries) {
    if (!e.match) continue;
    const f = files.get(e.file) || { file: e.file, lines: [], indexes: [] };
    if (e.line !== null) f.lines.push(e.line);
    f.indexes.push(e.index);
    files.set(e.file, f);
  }
  const all = [...files.values()];
  const matches = all.reduce((n, f) => n + f.indexes.length, 0);
  const pathList = all.every(f => !f.lines.length);
  let index;
  if (pathList) {
    // Path-only output (find, rg -l): group by directory; still lists every path.
    const dirs = new Map();
    for (const f of all) {
      const cut = f.file.lastIndexOf('/');
      const dir = cut >= 0 ? f.file.slice(0, cut + 1) : './';
      dirs.set(dir, [...(dirs.get(dir) || []), f.file.slice(cut + 1)]);
    }
    index = `[Laconic search index, lossless: all ${all.length} paths grouped by directory]\n` +
      [...dirs].map(([dir, names]) => `${dir} (${names.length}): ${names.join(', ')}`).join('\n');
    return bytes(index) <= maxBytes ? { excerpt: index, displayed: 0, lines: lines.length, lossless: true } : null;
  }
  index = `[Laconic search index, lossless: ${matches} matches in ${all.length} files; every file and matching line number listed]\n` +
    all.map(f => `${f.file} (${f.indexes.length}): ${ranges([...new Set(f.lines)].sort((a, b) => a - b))}`).join('\n');
  let level = 'lines';
  if (bytes(index) > maxBytes * 0.7) {
    index = `[Laconic search index: ${matches} matches in ${all.length} files; every file listed, line numbers via recovery query]\n` +
      all.map(f => `${f.file} (${f.indexes.length})`).join('\n');
    level = 'files';
  }
  // Coverage first: if even the file list cannot fit, keep the original output.
  if (bytes(index) > maxBytes * 0.85) return null;
  const budget = maxBytes - bytes(index) - 40;
  const { keep, render, choose } = selector(lines, budget, { gaps: false, lineChars: 300 });
  // Round-robin snippets: the first match of every file before any second match.
  for (let round = 0; round < 50; round++) {
    let any = false;
    for (const f of all) if (f.indexes[round] !== undefined) { any = true; choose(f.indexes[round]); }
    if (!any) break;
  }
  const snippets = render();
  return { excerpt: index + (snippets ? `\n[Snippets: ${keep.size}/${matches} matches]\n${snippets}` : ''),
    displayed: keep.size, lines: lines.length, lossless: level === 'lines' };
}

export function looksLikeNumberedSource(text) {
  const sample = text.split('\n', 400).filter(line => line.trim());
  if (sample.length < 20) return false;
  // nl / cat -n use a tab after the number; bat uses a box-drawing bar.
  const numbered = sample.filter(line => /^\s*\d+(?:\t|\s+\u2502)/.test(line)).length;
  return numbered / sample.length >= 0.6;
}

/** Optimize a plain UTF-8 text value. Any failure returns the original (fail open). */
export async function optimizeText({ harness='unknown', name='', args={}, text, isError=false, exitCode, policy={} }) {
  const category = categoryFor(name, args);
  const originalBytes = bytes(String(text ?? ''));
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
    // Line-numbered source listings (nl, cat -n, editor dumps) are file reads whatever produced them.
    if (looksLikeNumberedSource(text)) return unchanged;
    // A shell can print a structured document too. Do not silently destroy its schema.
    if (/^\s*[\[{]/.test(text)) {
      try { const value = JSON.parse(text); if (value && typeof value === 'object') return unchanged; } catch {}
    }
    // Store before compression. If storage fails, do not drop evidence.
    const recoveryId = await saveResult(text, settings.recovery);
    if (!recoveryId) return unchanged;
    const status = exitCode !== undefined ? ` Exit code: ${exitCode}.` : (isError ? ' Tool reported an error.' : '');
    const totalLines = text.split('\n').length;
    const recover = `Recover: laconic_read_result id=${recoveryId} query="<text>" (matches with context) or from=N count=100; CLI: laconic show ${recoveryId} --query TEXT]`;
    const makeFooter = (displayed, note = '') =>
      `\n[Laconic: partial ${category} output (${displayed}/${totalLines} lines shown, ${originalBytes} bytes).${status}${note} ${recover}`;
    const reserve = bytes(makeFooter(totalLines, ' All 999 distinct failure lines shown above with context; other omitted lines repeat them or match no failure pattern.'));
    let built = category === 'search' ? buildSearchExcerpt(text, budget - reserve) : null;
    let note = '';
    if (built) note = built.lossless ? ' Search index is complete.' : ' Search file list is complete.';
    else {
      built = buildLogExcerpt(text, budget - reserve, settings);
      if (built.groups) note = built.shownGroups === built.groups
        ? ` All ${built.groups} distinct failure line${built.groups === 1 ? '' : 's'} shown above with context; other omitted lines repeat them or match no failure pattern.`
        : ` Diagnostic groups shown: ${built.shownGroups}/${built.groups}; recover the rest by query.`;
    }
    const { excerpt, displayed } = built;
    // If no complete evidence fits, preserve the original rather than a misleading stub.
    if (!excerpt || (!displayed && !built.lossless)) return unchanged;
    const content = excerpt + makeFooter(displayed, note);
    if (bytes(content) >= originalBytes || bytes(content) > budget) return unchanged;
    const outcome = { content, changed: true, truncated: true, category, originalBytes,
      resultingBytes: bytes(content), recoveryId, harness, profile: settings.profile,
      groups: built.groups ?? 0, shownGroups: built.shownGroups ?? 0 };
    if (settings.recovery.stats !== false) await recordEvent({ type: 'optimized', id: recoveryId, harness,
      category, profile: settings.profile, originalBytes, resultingBytes: outcome.resultingBytes,
      groups: outcome.groups, shownGroups: outcome.shownGroups }, settings.recovery);
    return outcome;
  } catch { return unchanged; }
}

export function optimizeMcpResult(result, replaceText) {
  if (!result || typeof result !== 'object' || !Array.isArray(result.content) || result.structuredContent !== undefined) return null;
  // Do not rewrite multimodal, structured, or failed MCP results.
  if (result.isError || result.content.some(c=>c?.type !== 'text' || typeof c.text !== 'string')) return null;
  return replaceText;
}
export { categoryFor };

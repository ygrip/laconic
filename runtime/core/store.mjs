/** Owner-only, local, bounded recovery store. Never writes to the workspace. */
import { appendFile, mkdir, lstat, open, readdir, readFile, stat, truncate, writeFile, unlink } from 'node:fs/promises';
import { constants } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { join } from 'node:path';
import { randomBytes } from 'node:crypto';
import { env } from 'node:process';

export function storeDirectory() {
  return env.LACONIC_STORE_DIR || join(homedir() || tmpdir(), '.cache', 'laconic', 'results');
}
const SAFE_ID = /^lr_[a-f0-9]{32}$/;

export const RECOVERY_DESCRIPTION = 'Recover evidence from a tool result shortened by Laconic (lr_ ID). Prefer query (text or regex, returns matching lines with context) or around=N over guessing numeric ranges; from/count reads a raw range.';
export const RECOVERY_SCHEMA = Object.freeze({
  type: 'object', properties: {
    id: {type:'string', pattern:'^lr_[a-f0-9]{32}$'},
    query: {type:'string', minLength:1, maxLength:500, description:'Text to find (case-insensitive) or a regex when regex=true'},
    regex: {type:'boolean'},
    context: {type:'integer', minimum:0, maximum:50, description:'Lines before/after each match or around line (default 3)'},
    limit: {type:'integer', minimum:1, maximum:200, description:'Maximum matches to show (default 20)'},
    around: {type:'integer', minimum:1, description:'Show context around this 1-based line'},
    from: {type:'integer', minimum:1},
    count: {type:'integer', minimum:1, maximum:500}
  }, required:['id'], additionalProperties:false
});

async function privateDirectory(directory) {
  const info = await lstat(directory);
  if (!info.isDirectory() || info.isSymbolicLink() ||
      (process.getuid && (info.uid !== process.getuid() || (info.mode & 0o077))))
    throw new Error('Recovery directory must be owner-only (0700), owned by the current user, and not a symlink');
}

export async function saveResult(text, options = {}) {
  const { directory = storeDirectory(), maxStoredBytes = 2_000_000, retentionHours = 24 } = options;
  if (!Number.isSafeInteger(maxStoredBytes) || maxStoredBytes < 1 ||
      !Number.isFinite(retentionHours) || retentionHours <= 0 ||
      Buffer.byteLength(text, 'utf8') > maxStoredBytes) return null;
  await mkdir(directory, { recursive: true, mode: 0o700 });
  await privateDirectory(directory);
  const id = `lr_${randomBytes(16).toString('hex')}`;
  await writeFile(join(directory, id), text, { mode: 0o600, flag: 'wx' });
  // Opportunistic cleanup, not a background service. Limit directory entries per call.
  try {
    const entries = (await readdir(directory)).slice(0, 200);
    const cutoff = Date.now() - retentionHours * 3_600_000;
    await Promise.all(entries.filter(name => SAFE_ID.test(name)).map(async name => {
      const file = join(directory, name);
      const info = await stat(file);
      if (info.mtimeMs < cutoff) await unlink(file);
    }));
  } catch { /* Cleanup failures must not affect tool execution. */ }
  return id;
}

const STATS = 'stats.jsonl';
const MAX_STATS_BYTES = 1_000_000;
/** Append a content-free usage event (IDs, categories, byte counts). Never throws. */
export async function recordEvent(event, { directory = storeDirectory() } = {}) {
  try {
    await privateDirectory(directory);
    const file = join(directory, STATS);
    const info = await lstat(file).catch(() => null);
    if (info && (!info.isFile() || info.isSymbolicLink())) return;
    if (info && info.size > MAX_STATS_BYTES) await truncate(file, 0);
    await appendFile(file, JSON.stringify({ t: Date.now(), ...event }) + '\n', { mode: 0o600 });
  } catch { /* Statistics must never affect tool execution. */ }
}

/** Aggregate recovery frequency and cost signals, not just bytes saved. */
export async function readStats({ directory = storeDirectory(), sinceHours } = {}) {
  await privateDirectory(directory);
  const file = join(directory, STATS);
  const info = await lstat(file).catch(() => null);
  if (info && (!info.isFile() || info.isSymbolicLink())) throw new Error('Stats file must be a regular file');
  const text = info ? await readFile(file, 'utf8') : '';
  const cutoff = Number.isFinite(sinceHours) ? Date.now() - sinceHours * 3_600_000 : 0;
  const events = text.split('\n').filter(Boolean).map(line => { try { return JSON.parse(line); } catch { return null; } })
    .filter(e => e && e.t >= cutoff);
  const optimized = events.filter(e => e.type === 'optimized');
  const recoveries = events.filter(e => e.type === 'recovery');
  const recoveredIds = new Set(recoveries.map(e => e.id));
  const byCategory = {}, byMode = {}, byProfile = {};
  for (const e of optimized) {
    const c = byCategory[e.category] ||= { results: 0, originalBytes: 0, resultingBytes: 0, recovered: 0 };
    c.results++; c.originalBytes += e.originalBytes; c.resultingBytes += e.resultingBytes;
    if (recoveredIds.has(e.id)) c.recovered++;
    const p = byProfile[e.profile ?? 'unknown'] ||= { results: 0, recovered: 0 };
    p.results++; if (recoveredIds.has(e.id)) p.recovered++;
  }
  for (const e of recoveries) byMode[e.mode] = (byMode[e.mode] || 0) + 1;
  const originalBytes = optimized.reduce((n, e) => n + e.originalBytes, 0);
  const resultingBytes = optimized.reduce((n, e) => n + e.resultingBytes, 0);
  const recoveryBytes = recoveries.reduce((n, e) => n + (e.bytes || 0), 0);
  const recoveredResults = optimized.filter(e => recoveredIds.has(e.id)).length;
  return {
    optimizedResults: optimized.length, originalBytes, resultingBytes,
    bytesSaved: originalBytes - resultingBytes,
    recoveryCalls: recoveries.length, recoveredResults,
    recoveryRate: optimized.length ? recoveredResults / optimized.length : 0,
    recoveryBytes,
    // Each recovery call costs at least one extra tool round trip and usually one extra model call.
    netBytesSaved: originalBytes - resultingBytes - recoveryBytes,
    estimatedExtraModelCalls: recoveries.length,
    byCategory, byProfile, byMode
  };
}

async function loadResult(id, directory) {
  if (!SAFE_ID.test(id)) throw new Error('Invalid recovery ID');
  await privateDirectory(directory);
  const handle = await open(join(directory, id), constants.O_RDONLY | (constants.O_NOFOLLOW || 0));
  let contents;
  try {
    const info = await handle.stat();
    if (!info.isFile() || (process.getuid && (info.uid !== process.getuid() || (info.mode & 0o077))))
      throw new Error('Recovery file must be an owner-only regular file');
    contents = await handle.readFile('utf8');
  } finally { await handle.close(); }
  return contents;
}

const MAX_RECOVERY_LINES = 500;
// Numbered lines; `--` separates non-contiguous windows (grep convention).
const numbered = (lines, indexes) => indexes.map((i, n) =>
  `${n > 0 && i > indexes[n - 1] + 1 ? '--\n' : ''}[${i + 1}] ${lines[i]}`).join('\n');

/**
 * Recover a stored result by line range, by search query with surrounding context,
 * or around a line number. Query mode avoids guessing numeric ranges.
 */
export async function readResult(id, { directory = storeDirectory(), from = 1, count = 100,
  query, regex = false, context = 3, around, limit = 20, caseSensitive = false } = {}) {
  if (!SAFE_ID.test(id)) throw new Error('Invalid recovery ID');
  const contextual = query !== undefined || around !== undefined;
  if (!contextual && (!Number.isInteger(from) || from < 1 || !Number.isInteger(count) || count < 1 || count > 500))
    throw new Error('Invalid line range; count must be 1..500');
  if (contextual && (!Number.isInteger(context) || context < 0 || context > 50 ||
      !Number.isInteger(limit) || limit < 1 || limit > 200))
    throw new Error('Invalid context (0..50) or limit (1..200)');
  if (query !== undefined && (typeof query !== 'string' || !query.length || query.length > 500))
    throw new Error('Query must be a non-empty string of at most 500 characters');
  if (around !== undefined && (!Number.isInteger(around) || around < 1))
    throw new Error('around must be a positive line number');
  const contents = await loadResult(id, directory);
  const lines = contents.split('\n');
  if (contextual) {
    let hits;
    if (query !== undefined) {
      let test;
      if (regex) {
        const pattern = new RegExp(query, caseSensitive ? '' : 'i');
        test = line => pattern.test(line.length > 10_000 ? line.slice(0, 10_000) : line);
      } else {
        const needle = caseSensitive ? query : query.toLowerCase();
        test = line => (caseSensitive ? line : line.toLowerCase()).includes(needle);
      }
      hits = [];
      for (let i = 0; i < lines.length; i++) if (test(lines[i])) hits.push(i);
    } else {
      if (around > lines.length) throw new Error(`Line ${around} is beyond result (${lines.length} lines)`);
      hits = [around - 1];
    }
    const totalMatches = hits.length;
    const shown = hits.slice(0, limit);
    const selected = new Set();
    for (const i of shown) for (let k = Math.max(0, i - context); k <= Math.min(lines.length - 1, i + context); k++) {
      if (selected.size >= MAX_RECOVERY_LINES) break;
      selected.add(k);
    }
    const indexes = [...selected].sort((a, b) => a - b);
    return { id, mode: query !== undefined ? 'query' : 'around', totalLines: lines.length, totalMatches,
      shownMatches: shown.length, matchLines: hits.slice(0, 200).map(i => i + 1),
      text: numbered(lines, indexes) };
  }
  if (from > lines.length) throw new Error(`Line range starts beyond result (${lines.length} lines)`);
  const selected = lines.slice(from - 1, from + count - 1);
  return { id, mode: 'range', from, to: Math.min(lines.length, from + count - 1), totalLines: lines.length, text: selected.join('\n') };
}

/** Model-facing recovery text shared by every adapter. Records a recovery event. */
export async function recoverText(params = {}, options = {}) {
  const toInt = value => value === undefined || value === null ? undefined : Number(value);
  const found = await readResult(params.id, { ...options,
    from: toInt(params.from) ?? 1, count: toInt(params.count) ?? 100,
    query: params.query ?? undefined, regex: params.regex === true || params.regex === 'true',
    context: toInt(params.context) ?? 3, around: toInt(params.around), limit: toInt(params.limit) ?? 20 });
  let text;
  if (found.mode === 'range') text = `Lines ${found.from}-${found.to}/${found.totalLines}\n${found.text}`;
  else if (found.mode === 'around') text = `Context around line ${params.around}/${found.totalLines}\n${found.text}`;
  else text = `${found.totalMatches} matching line${found.totalMatches === 1 ? '' : 's'} for ${JSON.stringify(params.query)} in ${found.totalLines} lines` +
    (found.totalMatches > found.shownMatches ? ` (first ${found.shownMatches} shown; raise limit or narrow query)` : '') +
    (found.totalMatches ? `; match lines: ${found.matchLines.join(',')}${found.totalMatches > found.matchLines.length ? ',…' : ''}\n${found.text}` : '');
  await recordEvent({ type: 'recovery', id: found.id, mode: found.mode, bytes: Buffer.byteLength(text, 'utf8') }, options);
  return { found, text };
}

/** Owner-only, local, bounded recovery store. Never writes to the workspace. */
import { mkdir, lstat, open, readdir, stat, writeFile, unlink } from 'node:fs/promises';
import { constants } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { join } from 'node:path';
import { randomBytes } from 'node:crypto';
import { env } from 'node:process';

export function storeDirectory() {
  return env.LACONIC_STORE_DIR || join(homedir() || tmpdir(), '.cache', 'laconic', 'results');
}
const SAFE_ID = /^lr_[a-f0-9]{32}$/;

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

export async function readResult(id, { directory = storeDirectory(), from = 1, count = 100 } = {}) {
  if (!SAFE_ID.test(id)) throw new Error('Invalid recovery ID');
  if (!Number.isInteger(from) || from < 1 || !Number.isInteger(count) || count < 1 || count > 500)
    throw new Error('Invalid line range; count must be 1..500');
  await privateDirectory(directory);
  const handle = await open(join(directory, id), constants.O_RDONLY | (constants.O_NOFOLLOW || 0));
  let contents;
  try {
    const info = await handle.stat();
    if (!info.isFile() || (process.getuid && (info.uid !== process.getuid() || (info.mode & 0o077))))
      throw new Error('Recovery file must be an owner-only regular file');
    contents = await handle.readFile('utf8');
  } finally { await handle.close(); }
  const lines = contents.split('\n');
  if (from > lines.length) throw new Error(`Line range starts beyond result (${lines.length} lines)`);
  const selected = lines.slice(from - 1, from + count - 1);
  return { id, from, to: Math.min(lines.length, from + count - 1), totalLines: lines.length, text: selected.join('\n') };
}

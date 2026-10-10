import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, chmod, symlink, writeFile, stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {optimizeText, categoryFor} from '../runtime/core/engine.mjs';
import {saveResult, readResult} from '../runtime/core/store.mjs';
import laconicPi from '../runtime/adapters/pi.mjs';

async function policy() {
  return {minBytes:512,budgets:{shell:900,test:900},recovery:{directory:await mkdtemp(join(tmpdir(),'laconic-safe-'))}};
}
test('diagnostics and final summaries survive long head lines and warning floods', async () => {
  const settings=await policy();
  const text=[...Array(10).fill('x'.repeat(5000)), ...Array(200).fill('WARNING noise'), 'FAIL critical regression', ...Array(500).fill('progress'), 'Tests: 1 failed, 99 passed'].join('\n');
  const result=await optimizeText({name:'bash',args:{command:'npm test'},text,policy:settings});
  assert.equal(result.changed,true);
  assert.match(result.content,/FAIL critical regression/);
  assert.match(result.content,/Tests: 1 failed, 99 passed/);
  assert.ok(Buffer.byteLength(result.content)<=900);
});
test('structured shell JSON and unknown substring tools are untouched', async () => {
  const settings=await policy();
  const text=JSON.stringify({rows:Array(1000).fill('example')});
  assert.equal((await optimizeText({name:'bash',text,policy:settings})).changed,false);
  for (const name of ['execute_payment','file_search_metadata','research']) assert.equal(categoryFor(name),'unknown');
  for (const command of ['git diff test.py','git -C src show HEAD | grep test','cat src.py | grep test','sed -n 1,200p test.py']) {
    assert.equal((await optimizeText({name:'bash',args:{command},text:'noise\n'.repeat(2000),policy:settings})).changed,false);
  }
});
test('malformed direct policies fail open instead of throwing', async () => {
  for (const settings of [null,{allowedCategories:null},{budgets:{shell:null}},{recovery:null}]) {
    const text='hello\n'.repeat(5000);
    assert.equal((await optimizeText({name:'bash',text,policy:settings})).content,text);
  }
});
test('store rejects public directories, symlinks, and non-private recovery files', async () => {
  const root=await mkdtemp(join(tmpdir(),'laconic-store-safe-'));
  const directory=join(root,'results');
  await mkdir(directory,{mode:0o700});
  const id=await saveResult('original\nsecond',{directory});
  assert.equal((await stat(join(directory,id))).mode & 0o777,0o600);
  await assert.rejects(readResult(id,{directory,from:3}),/beyond result/);
  const alias=join(root,'alias');
  await symlink(directory,alias);
  await assert.rejects(saveResult('no',{directory:alias}),/owner-only/);
  const forged='lr_'+'a'.repeat(32);
  await symlink(join(directory,id),join(directory,forged));
  await assert.rejects(readResult(forged,{directory}));
  if (process.getuid) {
    await chmod(join(directory,id),0o644);
    await assert.rejects(readResult(id,{directory}),/owner-only/);
    await chmod(directory,0o755);
    await assert.rejects(saveResult('no',{directory}),/owner-only/);
  }
});
test('Pi recovery registration has integer JSON Schema and throws on invalid recovery', async () => {
  let tool, handler;
  await laconicPi({on:(_event,fn)=>{handler=fn},registerTool:value=>{tool=value}});
  assert.equal(typeof handler,'function');
  assert.equal(tool.name,'laconic_read_result');
  assert.equal(tool.parameters.properties.count.type,'integer');
  await assert.rejects(tool.execute('call',{id:'invalid'}),/Laconic recovery failed/);
});

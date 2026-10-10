import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {optimizeText,mergePolicy,diagnose,parseSearch,signature} from '../runtime/core/engine.mjs';
import {readResult,recoverText,readStats} from '../runtime/core/store.mjs';

const dir=()=>mkdtemp(join(tmpdir(),'laconic-quality-'));
const policy=async (extra={})=>({minBytes:512,recovery:{enabled:true,directory:await dir()},...extra});

test('distinct failure groups survive a flood of one repeated failure',async()=>{
  const lines=[];
  for(let i=0;i<2000;i++) lines.push(`ERROR db timeout after ${i}ms on shard ${i%7}`);
  lines.splice(1200,0,'Error: EACCES permission denied, open /var/run/app.sock');
  lines.splice(1700,0,'TypeError: cannot read properties of undefined (reading "id")','    at handler (src/api.ts:42:7)');
  lines.push('Tests: 3 failed, 97 passed');
  const result=await optimizeText({name:'bash',args:{command:'npm test'},text:lines.join('\n'),policy:await policy()});
  assert.equal(result.changed,true);
  assert.match(result.content,/3 distinct failure groups/);
  assert.match(result.content,/EACCES permission denied/);
  assert.match(result.content,/TypeError: cannot read/);
  assert.match(result.content,/src\/api\.ts:42/,'cause frame after the representative line is kept');
  assert.match(result.content,/Diagnostic groups shown: 3\/3/);
  assert.match(result.content,/3 failed, 97 passed/);
});

test('signatures collapse volatile numbers, hashes and quoted values only',()=>{
  assert.equal(signature('ERROR timeout after 15ms id=deadbeefcafe'),signature('ERROR timeout after 900ms id=0123456789ab'));
  assert.notEqual(signature('ERROR timeout'),signature('ERROR permission denied'));
  const {groups,summaries}=diagnose(['0 errors, 0 failed','ok','FAIL case 1','FAIL case 22','Tests: 2 failed']);
  assert.equal(groups.length,1);assert.equal(summaries.length,2);
});

test('search output keeps a lossless file and line index',async()=>{
  const lines=[];
  for(let f=0;f<60;f++) for(let l=1;l<=12;l++) lines.push(`src/module${f}/file${f}.ts:${l*10}:  const value${l} = lookupUser(id) // ${'x'.repeat(40)}`);
  const text=lines.join('\n');
  const result=await optimizeText({name:'rg',text,policy:await policy()});
  assert.equal(result.changed,true);
  for(let f=0;f<60;f++) assert.match(result.content,new RegExp(`src/module${f}/file${f}\\.ts \\(12\\)`),`file ${f} listed`);
  assert.match(result.content,/Search (?:index|file list) is complete/);
  assert.ok(parseSearch(lines));
});

test('rg heading format and path lists are recognized; prose is not',()=>{
  assert.ok(parseSearch(['src/a.ts','12:foo','13-bar','','src/b.ts','4:foo']));
  assert.ok(parseSearch(['./a/b.js','./a/c.js','./d/e.md']));
  assert.equal(parseSearch(['hello world','this is a log','nothing here']),null);
});

test('review profile never compresses search results or diffs; debugging widens budgets',async()=>{
  const lines=Array.from({length:800},(_,i)=>`src/f${i}.ts:${i}: match ${'y'.repeat(30)}`).join('\n');
  const review=await optimizeText({name:'rg',text:lines,policy:await policy({profile:'review'})});
  assert.equal(review.changed,false);assert.equal(review.content,lines);
  assert.equal(mergePolicy({profile:'debugging'}).budgets.shell,16_384);
  assert.equal(mergePolicy({profile:'nonsense'}).profile,'implementation');
  assert.equal(mergePolicy({profile:'review',budgets:{shell:9000}}).budgets.shell,9000,'explicit config wins over profile');
});

test('recovery supports query with context, regex, around and counts recovery events',async()=>{
  const p=await policy();
  const text=Array.from({length:1500},(_,i)=>i===700?'INCIDENT customer=cedar batch=463 lost_calls=17':`INFO batch=${i} ok`).join('\n');
  const result=await optimizeText({name:'bash',args:{command:'python3 diag.py'},text,policy:p});
  assert.equal(result.changed,true);
  const directory=p.recovery.directory;
  const q=await readResult(result.recoveryId,{directory,query:'customer=cedar',context:2});
  assert.equal(q.totalMatches,1);assert.match(q.text,/\[701\] INCIDENT/);assert.match(q.text,/\[699\] INFO/);assert.match(q.text,/\[703\] INFO/);
  const r=await readResult(result.recoveryId,{directory,query:'batch=(69[89]|70[01])\\b',regex:true,context:0});
  assert.equal(r.totalMatches,3,'index 700 holds the incident line, not batch=700');
  const a=await readResult(result.recoveryId,{directory,around:701,context:1});
  assert.match(a.text,/\[700\][\s\S]*\[702\]/);
  const {text:shown}=await recoverText({id:result.recoveryId,query:'lost_calls'},{directory});
  assert.match(shown,/1 matching line .*match lines: 701/);
  await assert.rejects(readResult(result.recoveryId,{directory,query:''}));
  const stats=await readStats({directory});
  assert.equal(stats.optimizedResults,1);assert.equal(stats.recoveryCalls,1);assert.equal(stats.recoveryRate,1);
  assert.equal(stats.byMode.query,1);assert.ok(stats.netBytesSaved<stats.bytesSaved);
});

test('source listings through shell (nl, for-loops of nl -ba) are never compressed',async()=>{
  const listing=Array.from({length:600},(_,i)=>i%15===0?`==== src/f${i}.py`:`${String(i%15).padStart(6)}\tdef fn_${i}(x): return x  # ${'s'.repeat(20)}`).join('\n');
  for (const command of ['for f in src/*.py; do echo "==== $f"; nl -ba "$f"; done','python3 dump.py']) {
    const r=await optimizeText({name:'bash',args:{command},text:listing,policy:await policy()});
    assert.equal(r.changed,false,command);assert.equal(r.content,listing);
  }
});

test('selector stays fast on large inputs',async()=>{
  const text=Array.from({length:20000},(_,i)=>i%997===0?`ERROR code E${i%13} in worker ${i}`:`INFO line ${i}`).join('\n');
  const start=performance.now();
  const result=await optimizeText({name:'bash',args:{command:'make'},text,policy:await policy()});
  assert.equal(result.changed,true);
  assert.ok(performance.now()-start<500,'optimization of 20k lines must stay well under 500ms');
});

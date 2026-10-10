#!/usr/bin/env node
/** Controlled identical-input processor replay. Bytes/latency, NOT provider tokens or billing. */
import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {optimizeText} from '../runtime/core/engine.mjs';
import {readResult} from '../runtime/core/store.mjs';
const noise=Array.from({length:1000},(_,i)=>i===450?'ERROR auth.test.ts:42 expected 200 got 403':i===999?'Tests: 1 failed, 99 passed':`INFO worker=collector batch=${i} processed events=128`).join('\n');
const fixtures=[
  {id:'shell-log',name:'bash',args:{command:'python3 diagnose.py'},text:noise,changed:true},
  {id:'test-log',name:'bash',args:{command:'npm test'},text:noise,changed:true},
  {id:'search-output',name:'rg',args:{},text:noise,changed:true},
  {id:'source-read',name:'read',args:{path:'src.py'},text:noise,changed:false},
  {id:'test-file-diff',name:'bash',args:{command:'git diff test.py'},text:noise,changed:false},
  {id:'structured-shell',name:'bash',args:{command:'api export'},text:JSON.stringify({records:Array(1000).fill({id:1,value:'preserve structured document'})}),changed:false},
  {id:'unknown-tool',name:'execute_payment',args:{},text:noise,changed:false},
  {id:'long-head-warning-flood',name:'bash',args:{command:'npm test'},text:[...Array(10).fill('🚀'.repeat(1500)),...Array(200).fill('WARNING noisy notice'),noise].join('\n'),changed:true}
];
const repeats=10;
const directory=await mkdtemp(join(tmpdir(),'laconic-replay-'));
try {
  const results=[];
  for (const fixture of fixtures) {
    const latencies=[];
    let result;
    for (let i=0;i<repeats;i++) {
      const start=performance.now();
      result=await optimizeText({...fixture,policy:{recovery:{directory}}});
      latencies.push(performance.now()-start);
      assert.equal(result.changed,fixture.changed,fixture.id);
      if (result.changed) {
        assert.match(result.content,/ERROR auth.test.ts:42/);
        assert.match(result.content,/Tests: 1 failed, 99 passed/);
        assert.equal(await readFile(join(directory,result.recoveryId),'utf8'),fixture.text);
        const stored=await readResult(result.recoveryId,{directory,from:1,count:500});
        assert.equal(stored.text,fixture.text.split('\n').slice(0,500).join('\n'));
      } else assert.equal(result.content,fixture.text);
    }
    latencies.sort((a,b)=>a-b);
    results.push({fixture:fixture.id,sha256:createHash('sha256').update(fixture.text).digest('hex'),
      category:result.category,changed:result.changed,original_bytes:result.originalBytes,
      model_visible_bytes:result.resultingBytes,byte_reduction_percent:100*(result.originalBytes-result.resultingBytes)/result.originalBytes,
      retained_required_evidence:true,recovery_verified:result.changed,
      processor_ms_median:latencies[Math.floor(latencies.length/2)],processor_ms_max:latencies.at(-1)});
  }
  const report={method:'Identical synthetic text processed with default policy, 10 repeats per fixture; diagnostic/summary, exact full-storage and line-range recovery assertions. No model calls.',
    node_version:process.version,repeats_per_fixture:repeats,results,
    limitation:'UTF-8 bytes and local processor latency only, not tokens, E2E task performance, or billed cost. Evidence assertions are fixture-specific; recovery reads are excluded from processor latency.'};
  if(process.argv[2])await writeFile(process.argv[2],JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
} finally {await rm(directory,{recursive:true,force:true});}

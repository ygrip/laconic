import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {optimizeText,categoryFor} from '../runtime/core/engine.mjs';
import {readResult} from '../runtime/core/store.mjs';
import {transformPi} from '../runtime/adapters/pi.mjs';
import {transformClaude} from '../runtime/adapters/claude.mjs';
import {transformOpenCode} from '../runtime/adapters/opencode-core.mjs';
import {CODEX_CAPABILITIES,transformCodex} from '../runtime/adapters/codex.mjs';

const fixture=(n=1800)=>Array.from({length:n},(_,i)=>i===900?'FAIL auth.test.ts:42 Expected 200 got 403':i===1799?'Tests: 1 failed, 99 passed':`OK progress step ${i}`).join('\n');
async function cfg() {
  const directory=await mkdtemp(join(tmpdir(),'laconic-test-'));
  return {minBytes:512,budgets:{test:2300,shell:2300,search:2300},recovery:{enabled:true,directory}};
}

test('classifies tests before shell',()=>{assert.equal(categoryFor('bash',{command:'npm test'}),'test');assert.equal(categoryFor('rg',{}),'search')});
test('only large, opted-in categories are reduced with recovery and line evidence',async()=>{
  const policy=await cfg(),text=fixture();
  const result=await optimizeText({name:'bash',args:{command:'npm test'},text,policy});
  assert.equal(result.category,'test');assert.equal(result.changed,true);assert.ok(result.resultingBytes<result.originalBytes);
  assert.match(result.content,/FAIL auth.test\.ts:42/);assert.match(result.content,/99 passed/);
  assert.match(result.content,/partial test output/);
  const recovered=await readResult(result.recoveryId,{directory:policy.recovery.directory,from:896,count:10});
  assert.match(recovered.text,/FAIL auth.test\.ts:42/);
  assert.equal((await readFile(join(policy.recovery.directory,result.recoveryId),'utf8')),text);
});
test('short results, file reads, diffs and unknown tools pass through',async()=>{
  const policy=await cfg(),text=fixture();
  for(const name of ['read','git_diff','a_tool']) {
    const result=await optimizeText({name,text,policy});assert.equal(result.changed,false);assert.equal(result.content,text);
  }
  const short=await optimizeText({name:'bash',text:'ready',policy});assert.equal(short.changed,false);
});
test('no data loss when persistence disabled, failing or capped',async()=>{
  const policy=await cfg(),text=fixture();
  for(const recovery of [{enabled:false},{enabled:true,directory:'/dev/null/not-a-dir'},{enabled:true,maxStoredBytes:50}]) {
    const r=await optimizeText({name:'bash',text,policy:{...policy,recovery}});
    assert.equal(r.content,text);assert.equal(r.changed,false);
  }
});
test('arbitrary IDs cannot escape recovery store',async()=>{
  await assert.rejects(readResult('../../etc/passwd'),/Invalid recovery ID/);
  await assert.rejects(readResult('lr_'+('a'.repeat(32)),{count:999}),/Invalid line range/);
});
test('Pi preserves details, errors, non-text and structured results',async()=>{
  const policy=await cfg(), text=fixture();
  const original={toolName:'bash',input:{command:'npm test'},isError:true,details:{exitCode:1},content:[{type:'text',text}]};
  const changed=await transformPi(original,policy);
  assert.ok(changed);assert.deepEqual(Object.keys(changed),['content']);
  assert.ok(changed.content[0].text.includes('FAIL auth.test.ts:42'));
  assert.equal(await transformPi({...original,structuredContent:{rows:[1]}},policy),null);
  assert.equal(await transformPi({...original,content:[...original.content,{type:'image',data:'a'}]},policy),null);
});
test('Claude hook replaces only known Bash success shape',async()=>{
  const policy=await cfg(), response={stdout:fixture(),stderr:'',interrupted:false,isImage:false};
  const original={hook_event_name:'PostToolUse',tool_name:'Bash',tool_input:{command:'npm test'},tool_response:response};
  const transformed=await transformClaude(original,policy);
  assert.equal(transformed?.hookSpecificOutput?.hookEventName,'PostToolUse');
  assert.equal(transformed.hookSpecificOutput.updatedToolOutput.stderr,'');
  assert.ok(transformed.hookSpecificOutput.updatedToolOutput.stdout.length<response.stdout.length);
  assert.equal(await transformClaude({...original,tool_response:{...response,stderr:'error'}},policy),null);
  assert.equal(await transformClaude({...original,tool_name:'Read'},policy),null);
});
test('OpenCode V2 changes only completed string results',async()=>{
  const policy=await cfg(),event={status:'completed',tool:'bash',input:{command:'npm test'},result:{content:fixture(),metadata:{ok:true}}};
  assert.equal(await transformOpenCode(event,policy),true);
  assert.equal(event.result.metadata.ok,true);
  assert.equal(await transformOpenCode({...event,status:'error'},policy),false);
  assert.equal(await transformOpenCode({...event,result:{content:[{type:'text'}]}},policy),false);
});
test('Codex is explicit about lack of native replacement',()=>{
  assert.equal(CODEX_CAPABILITIES.replaceResult,false);assert.equal(transformCodex(),null);
});
test('shell git diffs and shell file reads are never blindly shortened',async()=>{
  const policy=await cfg(),text=fixture();
  for(const command of ['git diff -- README.md','git show HEAD','cat SKILL.md','sed -n "1,200p" src.js']) {
    const out=await optimizeText({name:'bash',args:{command},text,policy});
    assert.equal(out.changed,false,`unexpectedly shortened ${command}`);
  }
});

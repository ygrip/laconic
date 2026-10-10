import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtemp,mkdir,readFile,writeFile,symlink} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
const bin=resolve('bin/laconic.mjs');
const mock=resolve('tests/mock-mcp.mjs');
const exec=(args,env,stdin)=>spawnSync(process.execPath,[bin,...args],{encoding:'utf8',env:{...process.env,...env},input:stdin,timeout:12000});

test('setup preserves existing Claude hooks and is idempotent; disable preserves unrelated hooks',async()=>{
  const project=await mkdtemp(join(tmpdir(),'laconic-setup-'));
  const home=join(project,'installed');
  const env={LACONIC_HOME:home};
  await mkdir(join(project,'.claude'));
  await writeFile(join(project,'.claude/settings.local.json'), JSON.stringify({hooks:{PostToolUse:[{matcher:'Read',hooks:[{type:'command',command:'echo runtime/adapters/claude.mjs'}]}]}}));
  let r=exec(['setup','--harness','claude','--project',project],env);
  assert.equal(r.status,0,r.stderr);
  r=exec(['setup','--harness','claude','--project',project],env);
  assert.equal(r.status,0,r.stderr);
  const file=join(project,'.claude/settings.local.json');
  const settings=JSON.parse(await readFile(file,'utf8'));
  assert.equal(settings.hooks.PostToolUse.length,2);
  assert.equal(JSON.parse(exec(['status','--project',project],env).stdout).claude.registered,true);
  r=exec(['disable','--harness','claude','--project',project],env);
  assert.equal(r.status,0,r.stderr);
  assert.equal(JSON.parse(await readFile(file,'utf8')).hooks.PostToolUse.length,1);
  assert.equal(JSON.parse(exec(['status','--project',project],env).stdout).claude.registered,false);
});
test('setup emits discoverable Pi module; unsupported OpenCode fails explicitly; Codex defaults to no overhead',async()=>{
  const project=await mkdtemp(join(tmpdir(),'laconic-setup-'));
  const env={LACONIC_HOME:join(project,'installed')};
  for (const harness of ['pi','codex']) {
    const result=exec(['setup','--harness',harness,'--project',project],env);
    assert.equal(result.status,0,result.stderr);
  }
  assert.match(await readFile(join(project,'.pi/extensions/laconic.ts'),'utf8'),/Managed by Laconic/);
  const unsupported=exec(['setup','--harness','opencode','--project',project],env);
  assert.equal(unsupported.status,1);
  assert.match(unsupported.stderr,/Native adapter unavailable/);
  const codex=exec(['status','--project',project],env);
  assert.equal(JSON.parse(codex.stdout).codex.replace,false);
});
test('MCP stdio proxy augments tool list, filters tool result, supports recovery', async()=>{
  const directory=await mkdtemp(join(tmpdir(),'laconic-gateway-'));
  const input=[
    {jsonrpc:'2.0',id:1,method:'initialize',params:{}},
    {jsonrpc:'2.0',id:2,method:'tools/list',params:{}},
    {jsonrpc:'2.0',id:3,method:'tools/call',params:{name:'bash',arguments:{command:'npm test'}}}
  ].map(x=>JSON.stringify(x)).join('\n')+'\n';
  const r=exec(['proxy','--',process.execPath,mock],{LACONIC_STORE_DIR:directory},input);
  assert.equal(r.status,0,r.stderr);
  const messages=r.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(messages.length,3,r.stdout);
  assert.ok(messages.find(x=>x.id===2).result.tools.some(x=>x.name==='laconic_read_result'));
  const text=messages.find(x=>x.id===3).result.content[0].text;
  assert.match(text,/Tests: 99 passed/);
  assert.match(text,/show lr_/);
  assert.ok(text.length<10000);
  const recoveryId=text.match(/lr_[a-f0-9]{32}/)[0];
  const again=exec(['show',recoveryId,'--from','1995','--count','6'],{LACONIC_STORE_DIR:directory});
  assert.equal(again.status,0,again.stderr);
  assert.match(again.stdout,/Tests: 99 passed/);
});

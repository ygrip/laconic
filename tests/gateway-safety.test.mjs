import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {join,resolve} from 'node:path';
import {mkdtemp,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {createInterface} from 'node:readline';
const bin=resolve('bin/laconic.mjs');
function launch(args, env={}) {
  const child=spawn(process.execPath,[bin,'proxy','--',...args],{stdio:['pipe','pipe','pipe'],env:{...process.env,...env}});
  let stdout='',stderr='';
  child.stdout.on('data',data=>stdout+=data);
  child.stderr.on('data',data=>stderr+=data);
  const done=new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>{child.kill('SIGKILL');reject(new Error('proxy hung with client stdin open'))},3000);
    child.on('close',code=>{clearTimeout(timeout);resolve({code,stdout,stderr})});
  });
  return {child,done};
}
test('gateway recovery works through live JSON-RPC tools/call, not just the CLI', async t=>{
  const directory=await mkdtemp(join(tmpdir(),'laconic-live-rpc-'));
  const config=join(directory,'config.json');
  await writeFile(config,'{}');
  const {child,done}=launch([process.execPath,resolve('tests/mock-mcp.mjs')],{LACONIC_CONFIG:config,LACONIC_STORE_DIR:directory});
  t.after(()=>{if(child.exitCode===null)child.kill('SIGKILL')});
  const pending=new Map();
  const reader=createInterface({input:child.stdout});
  reader.on('line',line=>{const response=JSON.parse(line);pending.get(response.id)?.(response);pending.delete(response.id)});
  const call=(id,method,params={})=>new Promise(resolve=>{
    pending.set(id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');
  });
  await call(1,'initialize');
  const list=await call(2,'tools/list');
  assert.ok(list.result.tools.some(tool=>tool.name==='laconic_read_result'));
  const log=await call(3,'tools/call',{name:'bash',arguments:{command:'npm test'}});
  const id=log.result.content[0].text.match(/lr_[a-f0-9]{32}/)[0];
  const recovered=await call(4,'tools/call',{name:'laconic_read_result',arguments:{id,from:1995,count:6}});
  assert.match(recovered.result.content[0].text,/Lines 1995-2000\/2000/);
  assert.match(recovered.result.content[0].text,/Tests: 99 passed/);
  const invalid=await call(5,'tools/call',{name:'laconic_read_result',arguments:{id:'invalid'}});
  assert.equal(invalid.result.isError,true);
  child.stdin.end();
  assert.equal((await done).code,0);
});
test('gateway terminates when upstream exits with client stdin still open', async()=>{
  const {done}=launch([process.execPath,'-e','process.exit(7)']);
  assert.equal((await done).code,7);
});
test('gateway terminates on spawn failure without hanging client', async()=>{
  const {done}=launch(['/laconic-nonexistent-command']);
  const result=await done;
  assert.equal(result.code,1);
  assert.match(result.stderr,/upstream error/);
});
test('gateway does not shadow recovery name before listing or on later pages', async()=>{
  const script=`const r=require('node:readline').createInterface({input:process.stdin});
  r.on('line',line=>{const m=JSON.parse(line);let result;
    if(m.method==='tools/list')result=m.params?.cursor?{tools:[{name:'laconic_read_result'}]}:{tools:[{name:'bash'}],nextCursor:'page2'};
    else result={content:[{type:'text',text:'upstream recovery tool'}]};
    console.log(JSON.stringify({jsonrpc:'2.0',id:m.id,result}));});`;
  const {child,done}=launch([process.execPath,'-e',script]);
  const messages=[
    {id:1,method:'tools/call',params:{name:'laconic_read_result',arguments:{id:'upstream'}}},
    {id:2,method:'tools/list',params:{}},
    {id:3,method:'tools/list',params:{cursor:'page2'}},
    {id:4,method:'tools/call',params:{name:'laconic_read_result',arguments:{id:'upstream'}}}
  ];
  child.stdin.end(messages.map(m=>JSON.stringify({jsonrpc:'2.0',...m})).join('\n')+'\n');
  const result=await done;
  assert.equal(result.code,0,result.stderr);
  const responses=result.stdout.trim().split('\n').map(JSON.parse);
  assert.equal(responses.length,4);
  for (const id of [1,4]) assert.equal(responses.find(r=>r.id===id).result.content[0].text,'upstream recovery tool');
  assert.equal(responses.find(r=>r.id===2).result.tools.length,1);
  assert.equal(responses.find(r=>r.id===3).result.tools.length,1);
});

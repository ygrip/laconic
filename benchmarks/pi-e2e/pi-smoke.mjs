#!/usr/bin/env node
/** Exercise a deployed, auto-discovered shim using an installed Pi loader, without inference. */
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve,dirname} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
if (!process.argv[2]) throw new Error('Usage: node pi-smoke.mjs <installed-pi-package-root> [output.json]');
const host=resolve(process.argv[2]);
const {discoverAndLoadExtensions}=await import(pathToFileURL(join(host,'dist/core/extensions/loader.js')).href);
const {createBashTool}=await import(pathToFileURL(join(host,'dist/core/tools/bash.js')).href);
const {ExtensionRunner}=await import(pathToFileURL(join(host,'dist/core/extensions/runner.js')).href);
const temp=await mkdtemp(join(tmpdir(),'laconic-pi-native-'));
try {
  process.env.LACONIC_CONFIG=join(temp,'policy.json');
  process.env.LACONIC_STORE_DIR=join(temp,'recovery');
  await writeFile(process.env.LACONIC_CONFIG,'{}');
  const setup=spawnSync(process.execPath,[join(root,'bin/laconic.mjs'),'setup','--harness','pi','--project',temp],{
    encoding:'utf8',env:{...process.env,LACONIC_HOME:join(temp,'deployed')}});
  assert.equal(setup.status,0,setup.stderr);
  const loaded=await discoverAndLoadExtensions([],temp,join(temp,'agent'));
  assert.deepEqual(loaded.errors,[]);
  assert.equal(loaded.extensions.length,1);
  const extension=loaded.extensions[0];
  assert.ok(extension.tools.has('laconic_read_result'));
  assert.ok(extension.handlers.has('tool_result'));
  // Run the installed SDK's real merge implementation with this loaded handler
  // set; no session/model context is needed by the adapter itself.
  const receiver={extensions:loaded.extensions,createContext:()=>({}),emitError:error=>{throw new Error(error.error)}};
  const fixture=join(temp,'diagnose.mjs');
  const quote=value=>`'${String(value).replaceAll("'", "'\\''")}'`;
  const command=`${quote(process.execPath)} ${quote(fixture)}`;
  for (const exitCode of [0,1]) {
    await writeFile(fixture,`for(let i=0;i<1000;i++) console.log(i===450?'ERROR deliberate diagnostic':\`progress step=\${i} processed events=128\`); process.exitCode=${exitCode};\n`);
    // Use actual built-in results, not fabricated events omitting the native shape.
    const emitted=await createBashTool(temp).execute('native-smoke',{command});
    const originalStructured=JSON.stringify(emitted.structuredContent);
    const changed=await ExtensionRunner.prototype.emitToolResult.call(receiver,
      {type:'tool_result',toolCallId:'native-smoke',toolName:'bash',input:{command},...emitted});
    assert.ok(changed,'Real built-in shell result must be filtered');
    assert.equal(changed.structuredContent,emitted.structuredContent);
    assert.equal(JSON.stringify(changed.structuredContent),originalStructured);
    assert.match(changed.content[0].text,/ERROR deliberate diagnostic/);
    assert.match(changed.content[0].text,new RegExp(`Exit code: ${exitCode}`));
    assert.equal(Boolean({...emitted,...changed}.isError),exitCode!==0);
    const id=changed.content[0].text.match(/lr_[a-f0-9]{32}/)[0];
    const registration=extension.tools.get('laconic_read_result');
    const tool=registration.definition || registration;
    const recovered=await tool.execute('smoke',{id,from:451,count:1});
    assert.match(recovered.content[0].text,/ERROR deliberate diagnostic/);
  }
  const report={pi_version:JSON.parse(await readFile(join(host,'package.json'),'utf8')).version,
    auto_discovered_shim:'laconic.ts',load_errors:loaded.errors,recovery_registered:true,
    actual_builtin_shell_executed:true,successful_and_failed_shells_verified:true,native_merge_path_verified:true,native_structured_output_preserved:true,
    model_visible_result_replaced:true,diagnostic_retained:true,exit_status_retained:true,recovery_roundtrip:true,
    scope:'Actual installed Pi loader, extension API and built-in bash result; no provider inference in this setup smoke test'};
  if (process.argv[3]) await writeFile(process.argv[3],JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
} finally { await rm(temp,{recursive:true,force:true}); }

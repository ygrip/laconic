import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtemp, mkdir, readFile, writeFile, symlink} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
const bin=resolve('bin/laconic.mjs');
test('setup refuses symlinked Pi shim without changing its target', async()=>{
  const project=await mkdtemp(join(tmpdir(),'laconic-shim-safe-'));
  await mkdir(join(project,'.pi/extensions'),{recursive:true});
  const target=join(project,'target.ts');
  const original='// Managed by Laconic\nexport default ()=>{};\n';
  await writeFile(target,original);
  await symlink(target,join(project,'.pi/extensions/laconic.ts'));
  const result=spawnSync(process.execPath,[bin,'setup','--harness','pi','--project',project],{
    encoding:'utf8',env:{...process.env,LACONIC_HOME:join(project,'runtime')}});
  assert.equal(result.status,1);
  assert.match(result.stderr,/Refusing to overwrite/);
  assert.equal(await readFile(target,'utf8'),original);
});
test('npm package ships the skill playbook and linked examples',()=>{
  const result=spawnSync('npm',['pack','--dry-run','--json'],{encoding:'utf8',timeout:30000});
  assert.equal(result.status,0,result.stderr);
  const files=JSON.parse(result.stdout)[0].files.map(file=>file.path);
  for (const expected of ['SKILL.md','references/tool-output.md','examples/runtime-config.json','examples/pi-output-limits.settings.json','bin/check.mjs']) assert.ok(files.includes(expected),expected);
});

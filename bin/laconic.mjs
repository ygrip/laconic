#!/usr/bin/env node
/** Laconic installer, capability inspection, recovery reader, and MCP gateway launcher. */
import { cp, mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { readResult, storeDirectory } from '../runtime/core/store.mjs';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const runtimeHome = process.env.LACONIC_HOME || join(homedir(), '.local', 'share', 'laconic');
const HARNESS = ['pi','claude','opencode','codex'];
const capabilities = {
  pi: {observe:true,replace:true, recovery:true, note:'Native tool_result replacement; structured results pass through.'},
  claude: {observe:true,replace:true, recovery:true, note:'PostToolUse Bash/PowerShell success only; schema-preserving replacement.'},
  opencode: {observe:true,replace:true, recovery:true, note:'V2 execute.after; V1 is not supported.'},
  codex: {observe:true,replace:false,recovery:false, note:'Observation only; use MCP gateway for supported MCP tools.'}
};
const instructions=`Usage:
  laconic setup --harness pi|claude|opencode|codex [--scope project|user] [--project PATH] [--observe]
  laconic status [--scope project|user] [--project PATH]
  laconic disable --harness pi|claude|opencode|codex [--scope project|user] [--project PATH]
  laconic doctor
  laconic show <lr_id> [--from N] [--count N]
  laconic proxy -- <mcp-server-command> [args...]

Native hook installation modifies only explicitly selected harness configuration.
MCP proxy requires explicit registration with the chosen harness.
`;
const option=(name, fallback)=>{
  const index=process.argv.indexOf(name);
  return index===-1?fallback:process.argv[index+1];
};
const scope=()=>option('--scope','project');
const project=()=>resolve(option('--project',process.cwd()));
function configRoot(harness) {
  const base=scope()==='user'?homedir():project();
  if (!['user','project'].includes(scope())) throw new Error('Invalid scope: choose user or project');
  if (harness==='pi') return join(base,'.pi',scope()==='user'?'agent':'');
  if (harness==='opencode' && scope()==='user') return join(base,'.config','opencode');
  return join(base,harness==='claude'?'.claude':harness==='opencode'?'.opencode':'.codex');
}
const quote=value=>`'${String(value).replaceAll("'", "'\\''")}'`;
async function readJson(file) {
  if (!existsSync(file)) return {};
  return JSON.parse(await readFile(file,'utf8'));
}
async function writeJson(file, object) {
  await mkdir(dirname(file),{recursive:true});
  const tmp=file+'.laconic-'+process.pid;
  await writeFile(tmp,JSON.stringify(object,null,2)+'\n',{flag:'wx',mode:0o600});
  await rename(tmp,file);
}
async function deployRuntime() {
  await mkdir(runtimeHome,{recursive:true, mode:0o700});
  await cp(join(packageRoot,'runtime'),join(runtimeHome,'runtime'),{recursive:true,force:true});
  await cp(join(packageRoot,'bin','laconic.mjs'),join(runtimeHome,'bin','laconic.mjs'),{recursive:true,force:true});
}
async function ownedStub(file,text) {
  await mkdir(dirname(file),{recursive:true});
  if (existsSync(file) && !(await readFile(file,'utf8')).startsWith('// Managed by Laconic'))
    throw new Error(`Refusing to overwrite unmanaged file: ${file}`);
  await writeFile(file,text,{mode:0o600});
}
function registration(harness) {
  const root=configRoot(harness);
  if(harness==='pi')return join(root,'extensions','laconic.mjs');
  if(harness==='opencode')return join(root,'plugins','laconic.mjs');
  if(harness==='claude')return join(root,scope()==='user'?'settings.json':'settings.local.json');
  return join(root,'hooks.json');
}
async function configureHook(harness,enable=true) {
  const file=registration(harness);
  const cfg=await readJson(file);
  const event='PostToolUse';
  const markers={claude:'runtime/adapters/claude.mjs',codex:'runtime/adapters/codex.mjs'};
  const existing=cfg.hooks?.[event] || [];
  const filtered=existing.map(group=>({...group,hooks:(group.hooks||[]).filter(h=>!String(h.command||'').includes(markers[harness]))})).filter(group=>group.hooks.length>0);
  if (enable) {
    const command=`node ${quote(join(runtimeHome,markers[harness]))}`;
    filtered.push({matcher:'Bash|PowerShell',hooks:[{type:'command',command,timeout:10}]});
  }
  cfg.hooks={...cfg.hooks,[event]:filtered};
  await writeJson(file,cfg);
  return file;
}
async function setup(harness){
  if (!HARNESS.includes(harness)) throw new Error('Choose a supported --harness: '+HARNESS.join(', '));
  if (!Number.isInteger(Number(process.versions.node.split('.')[0])) || Number(process.versions.node.split('.')[0])<20)
    throw new Error('Node 20 or newer required');
  await deployRuntime();
  const file=registration(harness);
  if (harness==='pi'||harness==='opencode') {
    const source=join(runtimeHome,'runtime','adapters',harness==='pi'?'pi.mjs':'opencode-core.mjs');
    const url=JSON.stringify(pathToFileURL(source).href);
    const body=harness==='pi'
      ? `// Managed by Laconic. Re-run setup to update; use laconic disable to remove.\nexport { default } from ${url};\n`
      : `// Managed by Laconic. OpenCode V2 only.\nimport { Plugin } from '@opencode-ai/plugin/v2';\nimport { transformOpenCode } from ${url};\nexport default Plugin.define({id:'laconic.output',async setup(ctx){await ctx.tool.hook('execute.after',async event=>{try{await transformOpenCode(event);}catch{}});}});\n`;
    await ownedStub(file,body);
  } else if (harness==='claude') await configureHook(harness,true);
  else if(process.argv.includes('--observe')) await configureHook(harness,true);
  console.log(`${harness}: ${harness==='codex'&&!process.argv.includes('--observe')?'observer not installed (pass --observe for opt-in)':'registered'}\n${file}`);
  console.log(capabilities[harness].note);
  console.log('Recovery files are owner-only and expire opportunistically after 24 hours; do not enable for sensitive tools without reviewing the policy.');
}
async function disable(harness) {
  if (!HARNESS.includes(harness)) throw new Error('Invalid harness');
  const file=registration(harness);
  if (harness==='pi'||harness==='opencode') {
    if (existsSync(file) && (await readFile(file,'utf8')).startsWith('// Managed by Laconic')) await rm(file);
  } else if(existsSync(file)) await configureHook(harness,false);
  console.log(`${harness}: disabled (${file})`);
}
async function main(){
  const command=process.argv[2];
  if(command==='setup')return setup(option('--harness'));
  if(command==='disable')return disable(option('--harness'));
  if(command==='doctor'){
    console.log(JSON.stringify({node:process.version,runtimeHome,store:storeDirectory(),capabilities},null,2));return;
  }
  if(command==='status'){
    const installed={};
    for(const harness of HARNESS) installed[harness]={config:registration(harness),exists:existsSync(registration(harness)),...capabilities[harness]};
    console.log(JSON.stringify(installed,null,2));return;
  }
  if(command==='show'){
    const id=process.argv[3];
    const result=await readResult(id,{from:Number(option('--from',1)),count:Number(option('--count',100))});
    console.log(`Lines ${result.from}-${result.to}/${result.totalLines}\n${result.text}`);return;
  }
  if(command==='proxy'){
    const {createGateway}=await import('../runtime/mcp/gateway.mjs');
    const {loadPolicy}=await import('../runtime/core/config.mjs');
    const sep=process.argv.indexOf('--');
    if(sep<0||!process.argv[sep+1])throw new Error('Expected: laconic proxy -- <mcp-command> [args]');
    createGateway({command:process.argv[sep+1],args:process.argv.slice(sep+2),policy:await loadPolicy()});return;
  }
  process.stdout.write(instructions);
  if(command&&command!=='help'&&command!=='--help')process.exitCode=2;
}
main().catch(error=>{console.error(`laconic: ${error.message}`);process.exitCode=1});

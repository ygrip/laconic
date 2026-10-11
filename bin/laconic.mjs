#!/usr/bin/env node
/** Laconic installer, capability inspection, recovery reader, and MCP gateway launcher. */
import { cp, lstat, mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { readStats, recoverText, storeDirectory } from '../runtime/core/store.mjs';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const runtimeHome = process.env.LACONIC_HOME || join(homedir(), '.local', 'share', 'laconic');
const HARNESS = ['pi','claude','opencode','codex'];
const capabilities = {
  pi: {observe:true,replace:true, recovery:true, note:'Native tool_result display replacement; known Bash raw structured output preserved, arbitrary structured APIs pass through.'},
  claude: {observe:true,replace:true, recovery:true, note:'PostToolUse Bash/PowerShell success only; schema-preserving replacement.'},
  opencode: {observe:false,replace:false, recovery:false, note:'Native adapter unavailable: @opencode-ai/plugin 1.18.35 exposes no V2 tool hook. Use the MCP proxy.'},
  codex: {observe:true,replace:false,recovery:false, note:'Observation only; use MCP gateway for supported MCP tools.'}
};
const instructions=`Usage:
  laconic setup --harness pi|claude|opencode|codex [--scope project|user] [--project PATH] [--observe]
  laconic status [--scope project|user] [--project PATH]
  laconic disable --harness pi|claude|opencode|codex [--scope project|user] [--project PATH]
  laconic doctor
  laconic show <lr_id> [--from N] [--count N]
  laconic show <lr_id> --query TEXT [--regex] [--context N] [--limit N]
  laconic show <lr_id> --around N [--context N]
  laconic stats [--since-hours N]
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
  const info = await lstat(file).catch(error => { if (error.code !== 'ENOENT') throw error; });
  if (info && (!info.isFile() || info.isSymbolicLink() || !(await readFile(file,'utf8')).startsWith('// Managed by Laconic')))
    throw new Error(`Refusing to overwrite unmanaged file or symlink: ${file}`);
  const temporary = file + '.laconic-' + process.pid;
  await writeFile(temporary,text,{mode:0o600,flag:'wx'});
  await rename(temporary,file);
}
function registration(harness) {
  const root=configRoot(harness);
  if(harness==='pi')return join(root,'extensions','laconic.ts');
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
  const command=`node ${quote(join(runtimeHome,markers[harness]))}`;
  const filtered=existing.map(group=>({...group,hooks:(group.hooks||[]).filter(h=>h.command !== command)})).filter(group=>group.hooks.length>0);
  if (enable) {
    filtered.push({matcher:harness==='codex'?'*':'Bash|PowerShell',hooks:[{type:'command',command,timeout:10}]});
  }
  cfg.hooks={...cfg.hooks,[event]:filtered};
  await writeJson(file,cfg);
  return file;
}
async function setup(harness){
  if (!HARNESS.includes(harness)) throw new Error('Choose a supported --harness: '+HARNESS.join(', '));
  if (!Number.isInteger(Number(process.versions.node.split('.')[0])) || Number(process.versions.node.split('.')[0])<20)
    throw new Error('Node 20 or newer required');
  if (harness === 'opencode') throw new Error(capabilities.opencode.note);
  await deployRuntime();
  const file=registration(harness);
  if (harness==='pi') {
    const source=join(runtimeHome,'runtime','adapters','pi.mjs');
    const url=JSON.stringify(pathToFileURL(source).href);
    const body=`// Managed by Laconic. Re-run setup to update; use laconic disable to remove.\nexport { default } from ${url};\n`;
    await ownedStub(file,body);
  } else if (harness==='claude') await configureHook(harness,true);
  else if(process.argv.includes('--observe')) await configureHook(harness,true);
  console.log(`${harness}: ${harness==='codex'&&!process.argv.includes('--observe')?'observer not installed (pass --observe for opt-in)':'registered'}\n${file}`);
  console.log(capabilities[harness].note);
  console.log('Recovery uses POSIX owner-only modes and opportunistic 24-hour cleanup (not a deletion deadline); Windows ACL privacy is unverified. Review the policy before enabling for sensitive tools.');
}
async function disable(harness) {
  if (!HARNESS.includes(harness)) throw new Error('Invalid harness');
  const file=registration(harness);
  if (harness==='pi'||harness==='opencode') {
    const info = await lstat(file).catch(error => { if (error.code !== 'ENOENT') throw error; });
    if (info?.isFile() && !info.isSymbolicLink() && (await readFile(file,'utf8')).startsWith('// Managed by Laconic')) await rm(file);
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
    for(const harness of HARNESS) {
      const file=registration(harness), exists=existsSync(file);
      let registered=false;
      if (exists) {
        if (harness==='pi'||harness==='opencode') {
          const info=await lstat(file);
          registered=info.isFile() && !info.isSymbolicLink() && (await readFile(file,'utf8')).startsWith('// Managed by Laconic');
        } else {
          const command=`node ${quote(join(runtimeHome,'runtime','adapters',harness+'.mjs'))}`;
          registered=(await readJson(file)).hooks?.PostToolUse?.some(group=>group.hooks?.some(h=>h.command===command)) ?? false;
        }
      }
      installed[harness]={config:file,exists,registered,...capabilities[harness]};
    }
    console.log(JSON.stringify(installed,null,2));return;
  }
  if(command==='show'){
    const params={id:process.argv[3],from:option('--from'),count:option('--count'),query:option('--query'),
      regex:process.argv.includes('--regex'),context:option('--context'),around:option('--around'),limit:option('--limit')};
    const {text}=await recoverText(params);
    console.log(text);return;
  }
  if(command==='stats'){
    const since=option('--since-hours');
    console.log(JSON.stringify(await readStats({sinceHours:since===undefined?undefined:Number(since)}),null,2));return;
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

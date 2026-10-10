/** MCP stdio JSON-RPC gateway. Only tools/call results are candidates for reduction. */
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { optimizeText } from '../core/engine.mjs';
import { recoverText, RECOVERY_SCHEMA, RECOVERY_DESCRIPTION } from '../core/store.mjs';
import { loadPolicy } from '../core/config.mjs';

const RECOVERY = 'laconic_read_result';
const recoveryTool = {
  name: RECOVERY,
  description: RECOVERY_DESCRIPTION,
  inputSchema: RECOVERY_SCHEMA
};
const send = obj => process.stdout.write(JSON.stringify(obj)+'\n');
export function createGateway({command,args=[],cwd=process.cwd(),spawnChild=spawn,policy}={}) {
  if (!command) throw new Error('Upstream MCP command is required');
  const child=spawnChild(command,args,{cwd,stdio:['pipe','pipe','inherit'],env:process.env});
  const pending = new Map();
  let recoveryNameAvailable = false;
  let upstreamRecoverySeen = false;
  let responses = Promise.resolve();
  const key=id=>JSON.stringify(id);
  child.on('error',error => { process.stderr.write(`laconic MCP upstream error: ${error.message}\n`); process.exitCode=1; });
  child.stdin.on('error', error => {
    if (error.code !== 'EPIPE') process.stderr.write(`laconic MCP input error: ${error.message}\n`);
  });
  child.on('close', (code,signal) => {
    responses.finally(() => {
      process.exitCode = process.exitCode || code || (signal ? 1 : 0);
      clients.close();
      process.stdin.destroy();
      pending.clear();
    });
  });
  const clients=createInterface({input:process.stdin,crlfDelay:Infinity});
  const servers=createInterface({input:child.stdout,crlfDelay:Infinity});

  clients.on('line',async line=>{
    let message;
    try { message=JSON.parse(line); } catch { child.stdin.write(line+'\n'); return; }
    if (!message || typeof message !== 'object' || Array.isArray(message)) { child.stdin.write(line+'\n'); return; }
    if (message.method==='tools/call' && message.params?.name === RECOVERY && recoveryNameAvailable && Object.hasOwn(message,'id')) {
      try {
        const {text}=await recoverText(message.params.arguments ?? {});
        send({jsonrpc:'2.0',id:message.id,result:{content:[{type:'text',text}]}});
      } catch (e) {
        send({jsonrpc:'2.0',id:message.id,result:{isError:true,content:[{type:'text',text:`Recovery failed: ${e.message}`}]}});
      }
      return;
    }
    if (Object.hasOwn(message,'id') && (message.method==='tools/call'||message.method==='tools/list')) {
      pending.set(key(message.id), {method:message.method, name:message.params?.name,
        args:message.params?.arguments, cursor:message.params?.cursor});
    }
    child.stdin.write(line+'\n');
  });
  // Handle model-facing tool responses before sending them to the client.
  const handleResponse = async line=>{
    let message;
    try {message=JSON.parse(line)} catch {process.stdout.write(line+'\n');return}
    if (!message || typeof message !== 'object' || Array.isArray(message) || !Object.hasOwn(message,'id')) {
      process.stdout.write(line+'\n'); return;
    }
    const request=pending.get(key(message.id));
    pending.delete(key(message.id));
    if (!request || message.error) {process.stdout.write(line+'\n');return}
    try {
      if (request.method==='tools/list' && Array.isArray(message.result?.tools)) {
        if (!request.cursor) upstreamRecoverySeen = false;
        if (message.result.tools.some(tool=>tool.name===RECOVERY)) upstreamRecoverySeen = true;
        // Establish ownership only after the last page: a later page may contain
        // an upstream tool with the same name. Before listing, pass calls upstream.
        recoveryNameAvailable = !message.result.nextCursor && !upstreamRecoverySeen;
        if (recoveryNameAvailable) {
          message.result.tools.push(recoveryTool);
          return send(message);
        }
      }
      if (recoveryNameAvailable && request.method==='tools/call' && message.result && !message.result.isError &&
          !Object.hasOwn(message.result,'structuredContent') && Array.isArray(message.result.content) &&
          message.result.content.length===1 && message.result.content[0]?.type==='text') {
        const original=message.result.content[0].text;
        const result=await optimizeText({harness:'mcp',name:request.name,
          args:request.args,text:original,policy});
        if (result.changed) {
          message.result.content[0]={...message.result.content[0],text:result.content};
          return send(message);
        }
      }
    } catch { /* Pass original response through. */ }
    process.stdout.write(line+'\n');
  };
  servers.on('line', line => { responses = responses.then(() => handleResponse(line)); });
  clients.on('close',()=>{ if (!child.stdin.destroyed) child.stdin.end(); });
  return {child,pending};
}

if (process.argv[1] && import.meta.url===new URL(`file://${process.argv[1]}`).href) {
  const sep=process.argv.indexOf('--');
  if (sep<0 || !process.argv[sep+1]) {
    process.stderr.write('Usage: laconic proxy -- <mcp-server-command> [args...]\n');
    process.exitCode=2;
  } else createGateway({command:process.argv[sep+1],args:process.argv.slice(sep+2),policy:await loadPolicy()});
}

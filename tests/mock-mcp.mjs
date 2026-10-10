import {createInterface} from 'node:readline';
const rl=createInterface({input:process.stdin});
for await (const line of rl) {
  const m=JSON.parse(line);
  if (m.method==='tools/list') console.log(JSON.stringify({jsonrpc:'2.0',id:m.id,result:{tools:[{name:'bash',inputSchema:{type:'object',properties:{command:{type:'string'}}}}]}}));
  else if(m.method==='tools/call') console.log(JSON.stringify({jsonrpc:'2.0',id:m.id,result:{content:[{type:'text',text:Array.from({length:2000},(_,i)=>i===1999?'Tests: 99 passed':`step ${i}`).join('\n')}]}}));
  else if(m.method==='initialize')console.log(JSON.stringify({jsonrpc:'2.0',id:m.id,result:{protocolVersion:'2025-11-25',capabilities:{tools:{}},serverInfo:{name:'test',version:'0.0.1'}}}));
}

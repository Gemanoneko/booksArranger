import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const scratch=path.dirname(fileURLToPath(import.meta.url));
const root='C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r3';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const check=fs.readFileSync(path.join(root,'scripts/check-desktop.mjs'),'utf8');
const syntaxMatch=/const syntaxFiles=(\[[^\r\n]+?\]),nodeTests=/.exec(check);
if(!syntaxMatch)throw Error('Canonical syntax declaration changed');
const syntaxFiles=JSON.parse(syntaxMatch[1].replaceAll("'",'"'));
if(!check.includes("const frontendScripts=fs.readdirSync(path.join(root,'tests')).filter(name=>/^test_.*\\.js$/.test(name)).sort();"))throw Error('Canonical frontend discovery changed');
const {CANONICAL_NODE_ENTRIES,PA1_ENTRY,phaseAccounting}=await import(pathToFileURL(path.join(root,'scripts/qa-phase-contract.mjs')).href);
phaseAccounting(CANONICAL_NODE_ENTRIES);
if(CANONICAL_NODE_ENTRIES.includes(PA1_ENTRY))throw Error('Native entry forbidden in Node-only phase');
const frontendScripts=fs.readdirSync(path.join(root,'tests')).filter(name=>/^test_.*\.js$/.test(name)).sort();
const commands=[...syntaxFiles.map(name=>({kind:'syntax',args:['--check',name]})),
 {kind:'pure-node',args:['--test','--test-reporter=tap',...CANONICAL_NODE_ENTRIES]},
 ...frontendScripts.map(name=>({kind:'frontend-dom-double',args:[path.join('tests',name)]}))];
const plan={source:'a7e20113fabcb5c7a4c7896e8b64304aa918eafc',root,
 check_sha256:hash(fs.readFileSync(path.join(root,'scripts/check-desktop.mjs'))),
 phase_contract_sha256:hash(fs.readFileSync(path.join(root,'scripts/qa-phase-contract.mjs'))),
 syntaxFiles,nodeEntries:CANONICAL_NODE_ENTRIES,frontendScripts,commands,
 excludedNative:PA1_ENTRY,timeoutMs:600000};
fs.writeFileSync(path.join(scratch,'phase-plan.json'),JSON.stringify(plan,null,2),{flag:'wx'});
const before=new Map([...syntaxFiles,...CANONICAL_NODE_ENTRIES,...frontendScripts.map(name=>'tests/'+name),'web/app.js','web/index.html','tests/durable_frontend_fixture.js'].map(name=>[name,hash(fs.readFileSync(path.join(root,name)))]));
const results=[];
for(const command of commands){
 const started=performance.now();
 const result=await new Promise(resolve=>{
  const out=[],err=[];let error=null;
  const child=spawn(process.execPath,command.args,{cwd:root,env:process.env,windowsHide:true,stdio:['ignore','pipe','pipe']});
  child.stdout.on('data',value=>out.push(value));child.stderr.on('data',value=>err.push(value));
  child.on('error',value=>{error=value.message;});
  child.on('close',(code,signal)=>resolve({code,signal,error,out:Buffer.concat(out).toString('utf8'),err:Buffer.concat(err).toString('utf8')}));
 });
 const record={...command,...result,elapsedMs:performance.now()-started};results.push(record);
 console.log('NODE_PHASE_COMMAND '+JSON.stringify({kind:command.kind,args:command.args,code:result.code,signal:result.signal,error:result.error,elapsedMs:record.elapsedMs}));
 if(result.out)process.stdout.write(result.out);if(result.err)process.stderr.write(result.err);
}
for(const [name,digest] of before)if(hash(fs.readFileSync(path.join(root,name)))!==digest)throw Error('Node phase source changed: '+name);
const node=results.find(result=>result.kind==='pure-node');
const nodeCount=Number(/^# tests (\d+)$/m.exec(node.out)?.[1]);
const nodeComplete=nodeCount>0&&/^# fail 0$/m.test(node.out)&&/^# skipped 0$/m.test(node.out)&&/^# cancelled 0$/m.test(node.out);
const ok=results.length===commands.length&&results.every(result=>result.code===0&&result.signal===null&&result.error===null)&&nodeComplete;
const summary={ok,syntaxRan:results.filter(value=>value.kind==='syntax').length,nodeEntriesRan:CANONICAL_NODE_ENTRIES.length,nodeCases:nodeCount,
 frontendScriptsRan:results.filter(value=>value.kind==='frontend-dom-double').length,commandsRan:results.length,sourceInputsUnchanged:true,results};
fs.writeFileSync(path.join(scratch,'phase-result.json'),JSON.stringify(summary,null,2),{flag:'wx'});
console.log('NODE_PHASE_RESULT '+JSON.stringify({ok,syntaxRan:summary.syntaxRan,nodeEntriesRan:summary.nodeEntriesRan,nodeCases:nodeCount,frontendScriptsRan:summary.frontendScriptsRan,commandsRan:summary.commandsRan,sourceInputsUnchanged:true}));
process.exitCode=ok?0:1;

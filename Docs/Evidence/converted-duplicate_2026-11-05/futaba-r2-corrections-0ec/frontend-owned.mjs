import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const root='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/f25r2';
const source=root+'/src';
const node='C:/Program Files/nodejs/node.exe';
const helper='C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/bounded-check.mjs';
const koffiRoot='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/build-cache/qa-ownership/node_modules/koffi';
const scripts=['test_iron_skazka_frontend.js','test_attention_frontend.js','test_refused_retry_frontend.js','test_retry_frontend.js'];
const {runOwned}=await import(pathToFileURL(helper).href);
const deadline=Date.now()+600000;
const env={
  SystemRoot:process.env.SystemRoot,WINDIR:process.env.WINDIR,
  PATH:'C:/Program Files/nodejs;C:/Windows/System32',
  TEMP:root+'/temp',TMP:root+'/temp',TMPDIR:root+'/temp',
  USERPROFILE:root+'/profile',APPDATA:root+'/profile',LOCALAPPDATA:root+'/profile',
  NODE_OPTIONS:'',NODE_PATH:''
};
const results=[];
for(const script of scripts){
  const remaining=deadline-Date.now();
  if(remaining<=0)throw Error('Original 600000 ms frontend deadline expired');
  const result=await runOwned(node,[path.join(source,'tests',script)],{cwd:source,env,koffiRoot,timeoutMs:remaining,maxBytes:4194304});
  const name=script.replace('.js','');
  fs.writeFileSync(path.join(root,name+'.json'),JSON.stringify(result,null,2),{flag:'wx'});
  fs.writeFileSync(path.join(root,name+'.log'),(result.out||'')+(result.err||''),{flag:'wx'});
  results.push({script,code:result.code,ok:result.ok,closed:result.closed,outputComplete:result.outputComplete,forced:result.forced,timedOut:result.timedOut,native:result.native,elapsedMs:result.elapsedMs});
  if(!result.ok)break;
}
fs.writeFileSync(path.join(root,'frontend-summary.json'),JSON.stringify({deadlineMs:600000,results},null,2),{flag:'wx'});
console.log(JSON.stringify({results:results.map(({script,code,ok,closed,outputComplete,native,elapsedMs})=>({script,code,ok,closed,outputComplete,nativeZero:native?.zero,elapsedMs}))}));
process.exitCode=results.length===scripts.length&&results.every(r=>r.ok)?0:1;

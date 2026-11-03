import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.dirname(fileURLToPath(import.meta.url));
const plan=JSON.parse(await fs.readFile(path.join(root,'pins.json'),'utf8'));
async function verify(){for(const p of plan.files){const b=await fs.readFile(p.path);if(b.length!==p.size||createHash('sha256').update(b).digest('hex')!==p.sha256)throw Error('Pin changed: '+p.path);}}
await verify();
const {runOwned}=await import(pathToFileURL(plan.helper));
const env={SystemRoot:process.env.SystemRoot,WINDIR:process.env.WINDIR,PATH:path.dirname(plan.python)+';C:/Windows/System32',TEMP:root,TMP:root,PYTHONDONTWRITEBYTECODE:'1',PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8'};
const result=await runOwned(plan.python,['-B',path.join(root,'run.py')],{cwd:root,env,timeoutMs:600000,koffiRoot:plan.koffi});
await fs.writeFile(path.join(root,'owned.json'),JSON.stringify(result,null,2));
await verify();
await fs.writeFile(path.join(root,'postflight.json'),JSON.stringify({pins_unchanged:true,at:new Date().toISOString()}));
console.log(JSON.stringify({code:result.code,ok:result.ok,closed:result.closed,forced:result.forced,timedOut:result.timedOut,native:result.native}));
process.exitCode=result.ok?0:1;

import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const root='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/durable-decisions-20261105';
const source='C:/Antigravity Projects/Worktrees/Books Arranger/durable-decisions-20261105';
const main='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger';
const [name,bridge]=process.argv.slice(2);
if(!/^[a-z0-9-]+$/.test(name||'')||!bridge)throw Error('Unique result name and private frontend bridge required');
const env={SystemRoot:process.env.SystemRoot,WINDIR:process.env.WINDIR,
 PATH:main+'/build-cache/qa-runtime/ffmpeg;C:/Program Files/nodejs;C:/Windows/System32',
 TEMP:root+'/temp',TMP:root+'/temp',TMPDIR:root+'/temp',USERPROFILE:root+'/profile',APPDATA:root+'/profile',LOCALAPPDATA:root+'/profile',
 BOOKS_QA_RUN_ROOT:source,BOOKS_QA_FIXTURE_ROOT:root+'/fixtures',PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:''};
const {runOwned}=await import(pathToFileURL('C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/bounded-check.mjs').href);
const result=await runOwned(main+'/build-cache/qa-runtime/python/python.exe',['-I','-B',root+'/frontend-backend-bridge.py',bridge],{cwd:source,env,timeoutMs:600000,maxBytes:4194304,koffiRoot:main+'/build-cache/qa-ownership/node_modules/koffi'});
fs.writeFileSync(root+'/'+name+'.json',JSON.stringify(result,null,2),{flag:'wx'});fs.writeFileSync(root+'/'+name+'.log',(result.out||'')+(result.err||''),{flag:'wx'});
console.log(JSON.stringify({name,ok:result.ok,code:result.code,closed:result.closed,outputComplete:result.outputComplete,native:result.native,elapsedMs:result.elapsedMs}));
console.log((result.out||'')+(result.err||''));process.exitCode=result.ok?0:1;

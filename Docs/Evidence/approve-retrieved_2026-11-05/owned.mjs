import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const root='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/approve-retrieved-20261105';
const source='C:/Antigravity Projects/Worktrees/Books Arranger/approve-retrieved-20261105';
const python='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/build-cache/qa-runtime/python/python.exe';
const helper='C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/bounded-check.mjs';
const [name,mode,...cases]=process.argv.slice(2);
if(!/^[a-z0-9-]+$/.test(name||'')||!['baseline','fixed'].includes(mode)||!cases.length)throw Error('Unique name, mode and cases required');
fs.mkdirSync(root+'/temp',{recursive:true});
const env={SystemRoot:process.env.SystemRoot,WINDIR:process.env.WINDIR,
 PATH:'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/build-cache/qa-runtime/ffmpeg;C:/Program Files/nodejs;C:/Windows/System32',
 TEMP:root+'/temp',TMP:root+'/temp',TMPDIR:root+'/temp',BOOKS_QA_FIXTURE_ROOT:'C:/Antigravity Projects/a26',PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:''};
const {runOwned}=await import(pathToFileURL(helper).href);
const result=await runOwned(python,['-I','-B',root+'/focused.py',mode,...cases],{cwd:source,env,timeoutMs:600000,maxBytes:4194304,koffiRoot:'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/build-cache/qa-ownership/node_modules/koffi'});
fs.writeFileSync(root+'/'+name+'.json',JSON.stringify(result,null,2),{flag:'wx'});
fs.writeFileSync(root+'/'+name+'.log',(result.out||'')+(result.err||''),{flag:'wx'});
console.log(JSON.stringify({name,ok:result.ok,code:result.code,closed:result.closed,outputComplete:result.outputComplete,native:result.native,elapsedMs:result.elapsedMs}));
console.log((result.out||'')+(result.err||''));process.exitCode=result.ok?0:1;

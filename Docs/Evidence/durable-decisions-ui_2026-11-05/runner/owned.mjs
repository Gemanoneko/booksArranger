import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const source='C:/Antigravity Projects/Worktrees/Books Arranger/durable-decisions-ui-20261105',root=source+'/scratch/durable-ui';
const [name,...cases]=process.argv.slice(2);if(!/^[a-z0-9-]+$/.test(name||'')||!cases.length)throw Error('Explicit cases required');
const {runOwned}=await import(pathToFileURL('C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/bounded-check.mjs').href);
const result=await runOwned('C:/Program Files/nodejs/node.exe',[root+'/run.cjs',...cases],{cwd:source,timeoutMs:600000,maxBytes:4194304,koffiRoot:'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/build-cache/qa-ownership/node_modules/koffi'});
fs.writeFileSync(root+'/'+name+'.json',JSON.stringify(result,null,2),{flag:'wx'});fs.writeFileSync(root+'/'+name+'.log',(result.out||'')+(result.err||''),{flag:'wx'});
console.log(JSON.stringify({ok:result.ok,code:result.code,closed:result.closed,outputComplete:result.outputComplete,native:result.native,elapsedMs:result.elapsedMs}));console.log((result.out||'')+(result.err||''));process.exitCode=result.ok?0:1;

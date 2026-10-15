// Staged Books classifier, native-held by proposed outer checker. Never installed here.
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
const raw=fs.readFileSync(0,'utf8');
try{
 if(Buffer.byteLength(raw)>1048576)throw Error('Oversized hook input');
 let payload;try{payload=JSON.parse(raw);}catch{payload=null;}
 const command=payload?.tool_input?.command;
 const booksPrefix="& 'C:\\Python314\\python.exe' -I -S -B -c '# Books fixed maintenance-13\n";
 const books=typeof command==='string'&&command.startsWith(booksPrefix);
 const args=books?["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\hook-adapter.mjs",'--frozen-sha',"a25faaa2929aaeaf987135cac6721064f7b8711a4e83f515c7532bc4a94b3b86"]:['C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\runtime-repair-20261013\\hook.mjs','--frozen-sha','0598caa4452dd6af828da5ca38b70fa6c152d61a4f8dff750df688e8b2500d47'];
 const r=spawnSync(process.execPath,args,{input:raw,cwd:process.cwd(),encoding:'utf8',windowsHide:true,timeout:7000,maxBuffer:1048576});
 if(r.error||r.signal||!Number.isInteger(r.status))throw Error('Pinned route worker failed');
 process.stdout.write(r.stdout);process.stderr.write(r.stderr);process.exitCode=r.status;
}catch(error){process.stdout.write(JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'[books-shared-staged] '+error.message}}));process.exitCode=2;}

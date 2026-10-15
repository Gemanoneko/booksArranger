// Authenticated Books adapter; never changes shared hooks/trust.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import{spawnSync}from'node:child_process';
const ROOT=path.win32.normalize('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/resume-2026-10-15/maintenance-worktree/scripts/qa/books-fixed-proof');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function deny(message){process.stdout.write(JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'[books-fixed-proof] '+message}}));process.exitCode=2;}
try{
 if(process.argv.length!==4||process.argv[2]!=='--frozen-sha'||!/^[a-f0-9]{64}$/.test(process.argv[3]))throw Error('Frozen Books registry required');
 const bytes=fs.readFileSync(path.win32.join(ROOT,'frozen.json'));
 if(sha(bytes)!==process.argv[3])throw Error('Books registry changed');
 const frozen=JSON.parse(bytes);
 for(const pin of frozen.routePins)if(sha(fs.readFileSync(pin.path))!==pin.sha256)throw Error('Books helper changed');
 const{validatePolicy,readFrozen,render,classify,STUDIO,PYTHON}=await import(new URL('./contract.mjs',import.meta.url));
 const p=validatePolicy(readFrozen(path.win32.join(ROOT,'policy.json'),frozen.policySha));
 if(render(p,frozen.runnerSha,frozen.policySha,false).command!==frozen.execute.command||render(p,frozen.runnerSha,frozen.policySha,true).command!==frozen.verify.command)throw Error('Frozen execute command differs from fixed contract');
 const raw=fs.readFileSync(0,'utf8'),route=classify(raw,[frozen.verify.command,frozen.execute.command],process.cwd());
 if(!route.owned)throw Error('Unmatched input must remain with the unchanged shared fallback');
 const verify=render(p,frozen.runnerSha,frozen.policySha,true);
 const r=spawnSync(PYTHON,['-I','-S','-B','-c',verify.code],{input:raw,cwd:STUDIO,encoding:'utf8',windowsHide:true,timeout:6500,maxBuffer:1048576});
 if(r.error||r.signal||r.status!==0)throw Error('Exact Books verifier failed: '+(r.stderr??'').slice(0,800));
 const proof=JSON.parse(r.stdout);
 if(proof.verified!==true||proof.deadline_ms!==600000||proof.source_verified!==false)throw Error('Books ownership/deadline proof incomplete');
 process.stdout.write(proof.guard_stdout);process.stderr.write(proof.guard_stderr);
}catch(error){deny(error.message);}

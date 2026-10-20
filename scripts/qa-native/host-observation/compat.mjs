// Isolated candidate. Active hook config is intentionally unchanged.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
export function classify(raw,exactCommand,actualCwd=process.cwd()){
  if(Buffer.byteLength(raw)>1048576)throw Error('Oversized input');
  const p=JSON.parse(raw);
  const command=p?.tool_input?.command;
  if(command===exactCommand){
    if(p.hook_event_name!=='PreToolUse'||p.tool_name!=='Bash'||Object.keys(p.tool_input).some(k=>k!=='command'))throw Error('Unsupported owned input schema');
    if(typeof p.cwd!=='string'||!path.isAbsolute(p.cwd)||path.resolve(p.cwd).toLowerCase()!==path.resolve(actualCwd).toLowerCase()||fs.realpathSync(p.cwd).toLowerCase()!==path.resolve(p.cwd).toLowerCase())throw Error('Hook cwd identity mismatch');
    return {owned:true,payload:p};
  }
  // Any altered bootstrap/runner invocation is refused, never normalized.
  if(typeof command==='string'&&/^\s*&\s*'C:\\Python314\\python.exe'\s+-I\s+-S\s+-c\s+'import ctypes as C,hashlib,os,pathlib,time/.test(command))throw Error('Unreviewed owned command');
  return {owned:false};
}
export function deny(reason){return JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'[fixed-timeout-contract] '+reason}});}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    const args=process.argv.slice(2);
    if(args.length!==2||args[0]!=='--candidate-sha'||!/^[a-f0-9]{64}$/.test(args[1]))throw Error('Pinned candidate required');
    const bytes=fs.readFileSync("C:/Users/AnGeLZzZ/.codex/hooks/command-safety-route/timeout-v1/fixed-bootstrap-candidate.json");
    if(sha(bytes)!==args[1])throw Error('Candidate pin mismatch');
    const manifest=JSON.parse(bytes),raw=fs.readFileSync(0,'utf8'),route=classify(raw,manifest.execute.command);
    let result;
    if(route.owned){
      result=spawnSync('C:\\Python314\\python.exe',['-I','-S','-c',manifest.verify.code],{input:raw,cwd:"C:/Users/AnGeLZzZ/.codex/hooks/command-safety-route/timeout-v1",encoding:'utf8',windowsHide:true,timeout:15000,maxBuffer:1048576});
      if(result.error||result.status!==0)throw Error('Pinned ownership/guard verification failed');
      const proof=JSON.parse(result.stdout);
      if(proof.verified!==true||proof.deadline_ms!==600000)throw Error('Required deadline contract missing');
      process.stdout.write(proof.guard_stdout);process.stderr.write(proof.guard_stderr);
      // No allow decision: host permission checks remain in force for the
      // visible fixed bootstrap. Only the unchanged original guard is replayed.
    }else{
      const observer="C:/Users/AnGeLZzZ/.codex/hooks/command-safety-route/books-host-observation-20261020-01/observer.mjs";
      const policy="C:/Users/AnGeLZzZ/.codex/hooks/command-safety-route/runtime-repair-20261018/observation-policy.capture-v1.json";
      result=spawnSync(process.execPath,[observer,'--policy',policy,'--policy-sha','f841d92eb0c0760e7e06209687157ec21c2b968d21b2370301e02874b4413651'],{input:raw,cwd:process.cwd(),encoding:'utf8',windowsHide:true,timeout:10000,maxBuffer:1048576});
      if(result.error||!Number.isInteger(result.status))throw Error('Original forwarding unavailable');
      process.stdout.write(result.stdout);process.stderr.write(result.stderr);process.exitCode=result.status;
    }
  }catch(error){process.stdout.write(deny(error.message));process.exitCode=2;}
}

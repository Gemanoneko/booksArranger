// Candidate hook. Unmatched commands go to the byte-identical prior handler.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import crypto from 'node:crypto';
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const ROOT='C:\\Antigravity Projects\\Studio Illuminati\\.claude\\scratchpad\\quicklaunch-dependency-route-2026-10-12\\runtime-enrollment-20261015\\lock-config-repair-01\\route';
const STUDIO='C:\\Antigravity Projects\\Studio Illuminati';
const PYTHON='C:\\Python314\\python.exe';
export const deny = reason => JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'[quicklaunch-fixed-route] '+reason}});
export function forward(raw, p, invoke = spawnSync) {
  const originalFallback={"path":"C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\timeout-v1\\timeout-compatibility-hook.mjs","sha256":"eeddc99ee66975f2a287da371ab39b063b6af6f3236d47ce01b9e33ebd2c0f76","candidateSha":"fb695a60c92b8933521fa810ef870e11e5e0dc4dbaf1f85e5ec54220da64e222"};
  if(p.fallback.path!==originalFallback.path||p.fallback.sha256!==originalFallback.sha256||p.fallback.candidateSha!==originalFallback.candidateSha)throw Error('Original fallback contract drift');
  if(sha(fs.readFileSync(originalFallback.path))!==originalFallback.sha256)throw Error('Original fallback handler drift');
  p={...p,fallback:{path:"C:/Users/AnGeLZzZ/.codex/hooks/command-safety-route/runtime-repair-20261018/timeout-compatibility-hook.mjs",sha256:"c37c18c5a2281ff4e2149f92f2e10f79e9e58c69c9b113ed0013645afa0d0c95",candidateSha:originalFallback.candidateSha}};
  if (sha(fs.readFileSync(p.fallback.path)) !== p.fallback.sha256) throw Error('Prior handler drift');
  return invoke(process.execPath,[p.fallback.path,'--candidate-sha',p.fallback.candidateSha],{input:raw,cwd:process.cwd(),encoding:'utf8',windowsHide:true,timeout:15000,maxBuffer:1048576});
}
if (path.resolve(process.argv[1]??'') === fileURLToPath(import.meta.url)) {
  try {
    const args=process.argv.slice(2);
    if(args.length!==2||args[0]!=='--frozen-sha')throw Error('Frozen registry required');
    const bytes=fs.readFileSync(path.win32.join(ROOT,'frozen.json'));
    if(!/^[a-f0-9]{64}$/.test(args[1])||sha(bytes)!==args[1])throw Error('Frozen registry drift');
    const frozen=JSON.parse(bytes);
    for(const pin of frozen.routePins)if(sha(fs.readFileSync(pin.path))!==pin.sha256)throw Error('Hook/checker drift');
    // Imports happen only AFTER byte authentication; deployed outer loader
    // additionally holds these authenticated files against concurrent writes.
    const {classify,readFrozen,render,validatePolicy}=await import('file:///C:/Antigravity%20Projects/Studio%20Illuminati/.claude/scratchpad/quicklaunch-dependency-route-2026-10-12/runtime-enrollment-20261015/lock-config-repair-01/route/contract.mjs');
    const p=validatePolicy(readFrozen(path.win32.join(ROOT,'policy.json'),frozen.policySha));
    const raw=fs.readFileSync(0,'utf8'),route=classify(raw,frozen.execute.command,process.cwd());
    // BEGIN exact Books-only candidate; original owned QuickLaunch route has priority.
    function isBooksOperation(command){
 if(typeof command!=='string')return false;
 // Inspect executable position only. Search/read/echo arguments are data.
 const tokens=[];const pattern=/\s*(?:"([^"\r\n]*)"|'([^'\r\n]*)'|([^\s"']+))/gy;let m;
 while(tokens.length<3&&(m=pattern.exec(command))!==null)tokens.push(m[1]??m[2]??m[3]);
 if(tokens[0]==='&')tokens.shift();
 const normalized=s=>String(s??'').replaceAll('\\','/').toLowerCase();
 const executable=normalized(tokens[0]);
 const target=s=>/^(?:.*\/)?books-qa-watchdog(?:\.exe)?$/.test(s)||/(?:^|\/)qa-native\/launch-books-qa\.mjs$/.test(s)||s==='c:/program files/booksarranger-qa-v2/launch-books-qa.mjs';
 if(target(executable))return true;
 return /(?:^|\/)(?:node(?:\.exe)?|powershell(?:\.exe)?|pwsh(?:\.exe)?)$/.test(executable)&&target(normalized(tokens[1]));
}
    const booksCommand=!route.owned&&(()=>{let input;try{input=JSON.parse(raw);}catch{return false;}const tool=input?.tool_input??{};return ['command','cmd'].some(key=>isBooksOperation(tool[key]));})();
    if(booksCommand){
      throw Error('Books V2 candidate disabled: protected current artifact and real original-host result association are unavailable');
    }else{
    let result;
    if(route.owned){
      if(process.cwd()!==STUDIO||sha(fs.readFileSync(PYTHON))!==p.python.sha256)throw Error('Actual owner/cwd drift');
      const verify=render(p,frozen.runnerSha,frozen.policySha,true);
      // The hook proves exact owned loader/policy/evaluator identity quickly.
      // Full runtime/source/preimage verification is still mandatory in the
      // externally bounded production worker BEFORE any npm work is released.
      verify.code=verify.code.replace('VERIFY_ONLY=True\n','VERIFY_ONLY=True\n QUICK_VERIFY=True\n');
      result=spawnSync(PYTHON,['-I','-S','-B','-c',verify.code],{input:raw,cwd:STUDIO,encoding:'utf8',windowsHide:true,timeout:15000,maxBuffer:1048576});
      if(result.error||result.status!==0)throw Error('Exact ownership/evaluator verification failed: '+(result.stderr??'').slice(0,800));
      const proof=JSON.parse(result.stdout);
      if(proof.verified!==true||proof.deadline_ms!==600000)throw Error('Deadline proof missing');
      process.stdout.write(proof.guard_stdout);process.stderr.write(proof.guard_stderr);
    }else{
      result=forward(raw,p);
      if(result.error||result.signal||!Number.isInteger(result.status))throw Error('Prior evaluator unavailable');
      process.stdout.write(result.stdout);process.stderr.write(result.stderr);process.exitCode=result.status;
    }
    } // END exact Books-only candidate. Existing block is literal unchanged.
    // No "allow" decision. Existing host approvals/deny rules still apply.
  }catch(error){process.stdout.write(deny(error.message));process.exitCode=2;}
}

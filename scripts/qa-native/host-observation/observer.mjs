import {isProbe,captureProbe,probeDecision} from './probe.mjs';
// Proposal only: no compatibility exception is active in observation mode.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
export function metadata(raw,actualCwd){
  if(Buffer.byteLength(raw)>1048576)throw Error('Oversized hook input');
  const input=JSON.parse(raw);if(!input||typeof input!=='object'||Array.isArray(input))throw Error('Invalid hook envelope');
  const scalar=value=>typeof value==='string'&&/^[A-Za-z_][A-Za-z0-9_.:]*$/.test(value)&&value.length<=80?value:'unsupported';
  return{mode:'observation-only',hookEvent:scalar(input.hook_event_name),toolName:scalar(input.tool_name),inputKeys:input.tool_input&&typeof input.tool_input==='object'&&!Array.isArray(input.tool_input)?Object.keys(input.tool_input).filter(key=>/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)&&key.length<=80).sort():[],cwdPresent:typeof input.cwd==='string',claimedCwdEqualsHookCwd:typeof input.cwd==='string'&&path.resolve(input.cwd).toLowerCase()===path.resolve(actualCwd).toLowerCase(),hookCwdAvailable:path.isAbsolute(actualCwd)};
}
export function observeAndForward(raw,cwd,forward,emit){
  // Capture is diagnostic only. Even malformed/unknown input and capture failure
  // must reach the original guard unchanged; its decision remains authoritative.
  try{emit(metadata(raw,cwd));}catch{}
  return forward(raw);
}
export function refusal(message){return JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'[observer-fail-closed] '+message}});}
export async function captureLoader(config,directory,io=fs,load=file=>import(pathToFileURL(file).href)){
  const skipped=()=>({captured:false,reason:'helper-unavailable'});
  try{
    if(!config||!/^[a-f0-9]{64}$/.test(config.moduleSha256??''))return skipped;
    const helper=path.join(directory,'capture-file.mjs'),stat=io.lstatSync(helper);
    if(stat.isSymbolicLink()||!stat.isFile()||stat.size>16384||path.resolve(io.realpathSync(helper)).toLowerCase()!==path.resolve(helper).toLowerCase()||sha(io.readFileSync(helper))!==config.moduleSha256)return skipped;
    const module=await load(helper);if(typeof module.captureMetadata!=='function')return skipped;
    return record=>module.captureMetadata(record,config);
  }catch{return skipped;}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  try{
    const args=process.argv.slice(2);if(args.length!==4||args[0]!=='--policy'||args[2]!=='--policy-sha'||!path.isAbsolute(args[1])||!/^[a-f0-9]{64}$/.test(args[3]))throw Error('Exact pinned observation policy required');
    const bytes=fs.readFileSync(args[1]);if(sha(bytes)!==args[3])throw Error('Observation policy tamper');
    const policy=JSON.parse(bytes);if(policy.mode!=='observation-only'||policy.activateException!==false||!path.isAbsolute(policy.legacyDispatch.path)||sha(fs.readFileSync(policy.legacyDispatch.path))!==policy.legacyDispatch.sha256||path.resolve(policy.node.path)!==path.resolve(process.execPath)||sha(fs.readFileSync(process.execPath))!==policy.node.sha256)throw Error('Observation-only pinned legacy/runtime contract required');
    const capture=await captureLoader(policy.capture,path.dirname(process.argv[1]));
    const raw=fs.readFileSync(0,'utf8'),{spawnSync}=await import('node:child_process');
    const result=probeDecision(raw,captureProbe,inputRaw=>observeAndForward(inputRaw,process.cwd(),input=>spawnSync(process.execPath,[policy.legacyDispatch.path],{input,cwd:process.cwd(),encoding:'utf8',windowsHide:true,timeout:10000,maxBuffer:1048576}),record=>{try{process.stderr.write('command-hook-metadata '+JSON.stringify(record)+'\n');}catch{}if(!isProbe(raw))capture(record);}));
    if(!result||result.error||result.signal||!Number.isInteger(result.status))throw Error('Forwarding unavailable');
    if(typeof result.stdout!=='string'||typeof result.stderr!=='string')throw Error('Forwarding output unavailable');
    process.stdout.write(result.stdout);process.stderr.write(result.stderr);process.exitCode=result.status;
  }catch{process.stdout.write(refusal('Pinned observation forwarding unavailable'));process.exitCode=2;}
}

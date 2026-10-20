/** Unimported POST contract preparation. Structural frames never prove origin. */
const HASH=/^[a-f0-9]{64}$/;
export class ResultRefused extends Error{constructor(code,message){super(message);this.code=code;}}
const need=(value,code,message)=>{if(!value)throw new ResultRefused(code,message);};
function record(value,wanted){
  need(value && typeof value==='object' && !Array.isArray(value) && [Object.prototype,null].includes(Object.getPrototypeOf(value)),'shape','Expected plain result record');
  const descriptors=Object.getOwnPropertyDescriptors(value);need(Reflect.ownKeys(descriptors).every(key=>typeof key==='string' && Object.hasOwn(descriptors[key],'value')),'shape','Result accessors/symbols refused');
  need(Object.keys(descriptors).sort().join('|')===[...wanted].sort().join('|'),'shape','Unknown/missing result fields');
  return Object.fromEntries(Object.entries(descriptors).map(([key,item])=>[key,item.value]));
}
const bindingKeys=['invocation_id','registry_sha256','context_sha256','source_sha256','watchdog_sha256'];
function binding(value){const data=record(value,bindingKeys);need(typeof data.invocation_id==='string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(data.invocation_id),'binding','Invalid fixed invocation');for(const key of bindingKeys.slice(1))need(typeof data[key]==='string' && HASH.test(data[key]),'binding','Invalid result pin');return data;}
export function validateOriginalResult(value,expected){
  const data=record(value,['schema','invocation_id','exit_code','signal','terminal','stdout_bytes','stderr_bytes']),wanted=binding(expected);
  need(data.schema==='books-original-tool-result-proposed-v1' && data.invocation_id===wanted.invocation_id,'observation','Wrong original tool result binding');
  need(data.exit_code===0 && data.signal===null && data.terminal===true,'observation','Original tool did not finish successfully');
  need([data.stdout_bytes,data.stderr_bytes].every(n=>Number.isSafeInteger(n)&&n>=0)&&data.stdout_bytes+data.stderr_bytes<=16*1024*1024,'bounds','Original output bounds missing');
  return Object.freeze({kind:'original-result-shape-only',authority:false});
}
/** Future framing specification only: current C++ does not produce it. */
export function validateTerminalFrame(frame,expected){
  const data=record(frame,['schema',...bindingKeys,'exit_code','active','unsignaled','pipe_eof','checked_closes','elapsed_ms','output_bytes']);
  const wanted=binding(expected);need(data.schema==='books-native-terminal-proposed-v1','schema','Unreviewed/missing native framing');
  for(const key of bindingKeys)need(data[key]===wanted[key],'binding','Native terminal binding mismatch');
  need(data.exit_code===0 && data.active===0 && data.unsignaled===0 && data.pipe_eof===true && data.checked_closes===true,'closure','Unclosed/failed native terminal shape');
  need(Number.isSafeInteger(data.elapsed_ms) && data.elapsed_ms>=0 && data.elapsed_ms<=600000 && Number.isSafeInteger(data.output_bytes) && data.output_bytes>=0 && data.output_bytes<=16*1024*1024,'bounds','Unbounded native terminal shape');
  return Object.freeze({kind:'terminal-shape-only',authority:false,...wanted});
}
export function requireProductionResultCapability(){throw new ResultRefused('native_framing_missing','Original tool/native framing/context join capability is unimplemented; current C++ receipt cannot satisfy it');}
export async function acceptProtectedResult(){return requireProductionResultCapability();}
const usedFixtureObservations=new WeakSet();
/** Injected fixture functions model ownership; this can never accept real QA. */
export async function exercisePostBoundary(actualResult,expected,capabilities){
  const wanted=binding(expected),caps=record(capabilities,['observeOriginalTool','readNativeTerminal','verifyOriginalOwnership','closeObservation']);
  validateOriginalResult(actualResult,wanted);
  for(const fn of Object.values(caps))need(typeof fn==='function','capability','Missing fixture result capability');
  let observation;
  try{
    observation=await caps.observeOriginalTool(actualResult,wanted);need(observation && typeof observation==='object','observation','Missing original tool observation');
    if(usedFixtureObservations.has(observation)){observation=null;throw new ResultRefused('replay','Fixture observation was already consumed');}
    usedFixtureObservations.add(observation);
    const terminal=record(await caps.readNativeTerminal(observation),['frame','frames','trailing_bytes','child_lookalike']);
    need(terminal.frames===1 && terminal.trailing_bytes===0 && terminal.child_lookalike===false,'framing','Ambiguous/child/trailing terminal framing');
    validateTerminalFrame(terminal.frame,wanted);
    need(await caps.verifyOriginalOwnership(observation,wanted)===true,'origin','Fixture original native ownership mismatch');
    return Object.freeze({kind:'fixture-post-boundary-only',accepted:false,authority:false,production:false});
  }finally{if(observation)need(await caps.closeObservation(observation)===true,'close','Fixture original observation closure failed');}
}

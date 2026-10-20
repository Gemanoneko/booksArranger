/** Unimported PRE contract preparation. No process/native/host authority. */
export const STUDIO='C:/Antigravity Projects/Studio Illuminati';
export const SOURCE='C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1';
export const BASE='C:/Program Files/BooksArranger-QA-v2';
export const WATCHDOG=BASE+'/books-qa-watchdog.exe';
const HASH=/^[a-f0-9]{64}$/;
export class AdmissionRefused extends Error{constructor(code,message){super(message);this.code=code;}}
const need=(value,code,message)=>{if(!value)throw new AdmissionRefused(code,message);};
function object(value){
  need(value && typeof value==='object' && !Array.isArray(value),'shape','Expected a plain record');
  const prototype=Object.getPrototypeOf(value);need(prototype===Object.prototype || prototype===null,'shape','Unexpected record prototype');
  const descriptors=Object.getOwnPropertyDescriptors(value);
  need(!Reflect.ownKeys(descriptors).some(key=>typeof key!=='string' || !Object.hasOwn(descriptors[key],'value')),'shape','Accessors/symbols are not data');
  return Object.fromEntries(Object.entries(descriptors).map(([key,item])=>[key,item.value]));
}
function keys(value,wanted){const data=object(value);need(Object.keys(data).sort().join('|')===[...wanted].sort().join('|'),'shape','Unknown/missing fields');return data;}
const normalized=value=>typeof value==='string'?value.replaceAll('\\','/').toLowerCase():'';
const inside=(value,root)=>normalized(value)===normalized(root)||normalized(value).startsWith(normalized(root)+'/');
function tokens(command){
  const result=[];const regex=/\s*(?:'([^'\r\n]*)'|"([^"\r\n]*)"|([^\s'"]+))/gy;let at=0;
  while(at<command.length){const match=regex.exec(command);if(!match)return null;result.push(match[1]??match[2]??match[3]);at=regex.lastIndex;if(result.length>128)return null;}
  return result;
}
function executableSyntax(command){
  let quote='';const text=command.replace(/^&\s+/,'');
  for(let i=0;i<text.length;i++){
    const ch=text[i];if(quote==="'"){if(ch==="'")quote='';continue;}
    if(ch==="'" && !quote){quote="'";continue;}
    if(ch==='"'){quote=quote==='"'?'':'"';continue;}
    if(ch==='`'||text.slice(i,i+2)==='$('||(!quote&&/[;&|{}]/.test(ch)))return true;
  }
  return !!quote;
}
function payload(raw){
  need(typeof raw==='string' && raw.length<=65536,'shape','Bounded literal input required');
  let parsed;try{parsed=JSON.parse(raw);}catch{throw new AdmissionRefused('shape','Invalid request JSON');}
  return keys(keys(parsed,['tool_input']).tool_input,['cmd','workdir','login','yield_time_ms','max_output_tokens']);
}
// Identification only: this is NOT a trusted host decoder or Books admission.
// JSON input has no Proxy/accessor capabilities; fixture object APIs remain trusted.
function identification(raw){
  if(typeof raw!=='string'||raw.length>65536)return null;
  let parsed;try{parsed=JSON.parse(raw);}catch{return null;}
  const data=parsed?.tool_input;
  if(!data||typeof data!=='object'||Array.isArray(data)||typeof data.cmd!=='string')return null;
  return data;
}
const unproved=raw=>({route:'opaque-fallback',opaque_input:raw,reason:'Unproved transport; integration must stop',authority:false,integration_stop:true});
/** Classification is data only; fallback is not an allow decision. */
export function classifyRequest(raw,{originalOwned=false}={}){
  if(originalOwned===true)return {route:'original-owned',opaque_input:raw,authority:false};
  const data=identification(raw);
  if(!data)return unproved(raw);
  const booksCwd=inside(data.workdir,SOURCE)||inside(data.workdir,STUDIO+'/WIP/Books Arranger');
  if(/[\r\n\0]/.test(data.cmd))return unproved(raw);
  const parsed=tokens(data.cmd);if(!parsed?.length)return unproved(raw);
  if(parsed[0]==='&')parsed.shift();
  const executable=normalized(parsed[0]),name=executable.split('/').at(-1),args=parsed.slice(1);
  const mentionsBooks=normalized(data.cmd).includes(normalized(SOURCE))||normalized(data.cmd).includes(normalized(BASE))||/books-qa|launch-books|run_entry_checks|\bnpm\b/i.test(data.cmd);
  if(executableSyntax(data.cmd)&&(booksCwd||mentionsBooks))return {route:'deny',reason:'Unsupported Books execution syntax',authority:false};
  const readOnly=new Set(['rg','rg.exe','echo','write-output','get-content','get-childitem','select-string','cat','type','dir','pwd']);
  if(readOnly.has(name))return {route:'opaque-fallback',opaque_input:raw,authority:false};
  if((name==='git'||name==='git.exe') && ['diff','show','status','log','grep','ls-files','rev-parse'].includes(args[0]))return {route:'opaque-fallback',opaque_input:raw,authority:false};
  const target=value=>/(?:^|\/)(?:books-qa-watchdog(?:\.exe)?|launch-books-qa\.mjs|qa-owned-guardian-v2\.mjs|run_entry_checks\.mjs)$/.test(normalized(value));
  if(executable===normalized(WATCHDOG))return {route:'watchdog-candidate',authority:false};
  if(target(executable)||args.some(target))return {route:'deny',reason:'Books execution requires the fixed protected watchdog',authority:false};
  const booksArgument=args.some(value=>normalized(value).includes(normalized(SOURCE))||normalized(value).includes(normalized(BASE))||normalized(value).includes('/qa-entry-context/')||/(?:^|[\/\\\s])run_entry_checks\.mjs(?:\s|$)/i.test(value));
  const executor=/^(?:node|npm|npx|python|python3|py|powershell|pwsh|cmd|bash|sh|wsl|cscript|wscript|dotnet|git|iex|invoke-expression|invoke-command|start-process)(?:\.exe|\.cmd)?$/.test(name);
  if(booksArgument||inside(executable,SOURCE)||inside(executable,BASE)||(booksCwd&&(executor||/[;&|{}]/.test(data.cmd))))return {route:'deny',reason:'Unwrapped or unsupported wrapped Books operation',authority:false};
  return {route:'opaque-fallback',opaque_input:raw,authority:false};
}
export function validatePreRequest(raw,policy){
  const data=payload(raw),p=keys(policy,['schema','enabled','operation','registry_sha256','context_sha256','source_sha256','runtime_sha256','bootstrap_sha256','manifest_sha256','watchdog_sha256']);
  need(p.schema==='books-protected-admission-policy-v1' && p.enabled===true && p.operation==='entry','policy','Disabled/unsupported fixed operation');
  for(const key of Object.keys(p).filter(key=>key.endsWith('_sha256')))need(typeof p[key]==='string' && HASH.test(p[key]),'policy','Invalid exact pin');
  const expected="& '"+WATCHDOG+"' --registry-sha "+p.registry_sha256;
  need(data.cmd===expected && data.workdir===STUDIO && data.login===false,'envelope','Wrong exact literal command/cwd/login');
  need(data.yield_time_ms===10000 && Number.isSafeInteger(data.max_output_tokens) && data.max_output_tokens>0 && data.max_output_tokens<=100000,'envelope','Unsupported observation fields');
  need(classifyRequest(raw).route==='watchdog-candidate','command','Not a watchdog candidate');
  return Object.freeze({kind:'pre-validation-only',authority:false,watchdog:WATCHDOG,command:expected,registry_sha256:p.registry_sha256,context_sha256:p.context_sha256,source_sha256:p.source_sha256,policy:Object.freeze({...p}),observation:Object.freeze({yield_time_ms:data.yield_time_ms,max_output_tokens:data.max_output_tokens}),execution_bound_from_observation:false});
}
export function requireProductionAdmissionCapability(){throw new AdmissionRefused('native_contract_missing','Trusted hook/default-shell binding and protected native admission capability are unimplemented');}
export async function verifyProtectedAdmission(){return requireProductionAdmissionCapability();}
/** Fixture-only dependency exercise; cannot return a host allow/result status. */
export async function exercisePreBoundary(raw,policy,capabilities){
  const intent=validatePreRequest(raw,policy),caps=keys(capabilities,['observeTrustedHost','freezeProtectedInputs','revalidateProtectedInputs','closeProtectedInputs']);
  for(const fn of Object.values(caps))need(typeof fn==='function','capability','Missing fixture capability function');
  let lease;
  try{
    const host=await caps.observeTrustedHost(raw);
    need(host && host.defaultShell==='WindowsPowerShell' && host.requestLiteral===raw,'host','Fixture host binding mismatch');
    lease=await caps.freezeProtectedInputs(intent);
    need(lease && typeof lease==='object','capability','Missing fixture held input capsule');
    need(await caps.revalidateProtectedInputs(lease,intent)===true,'input_drift','Fixture protected input drift');
    return Object.freeze({kind:'fixture-pre-boundary-only',authority:false,production:false,canonical_runs:0});
  }finally{if(lease)need(await caps.closeProtectedInputs(lease)===true,'close','Fixture held input closure failed');}
}

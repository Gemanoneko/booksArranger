import {validateV2InputBytes,V2_BINDING_KEYS,ownExact,canonicalData,strictJSON} from './launch-books-qa.mjs';
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
  let parsed;try{parsed=strictJSON(Buffer.from(raw,'utf8'),65536);}catch{throw new AdmissionRefused('shape','Invalid request JSON');}
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
export function validatePreRequest(raw,registration){
 const data=payload(raw),r=keys(registration,['bytes','registry_sha256']),graph=validateV2InputBytes(r.bytes,r.registry_sha256);
 const expected="& '"+WATCHDOG+"' --registry-sha "+graph.binding.registry_sha256;
 need(data.cmd===expected&&data.workdir===STUDIO&&data.login===false,'envelope','Wrong exact fixed PowerShell command/cwd/login');need(data.yield_time_ms===10000&&Number.isSafeInteger(data.max_output_tokens)&&data.max_output_tokens>0&&data.max_output_tokens<=100000,'envelope','Observation fields do not establish a deadline');need(classifyRequest(raw).route==='watchdog-candidate','command','Unwrapped Books operation');return Object.freeze({kind:'pre-v2-raw-byte-validation-only',authority:false,binding:graph.binding,policy:graph.policy,command:expected,execution_bound_from_observation:false});
}
export function requireProductionAdmissionCapability(){throw new AdmissionRefused('native_contract_missing','Actual original-host streams/EOF/duration association and current protected V2 artifact proof are unavailable; production refuses');}
export async function verifyProtectedAdmission(){return requireProductionAdmissionCapability();}
const fixturePending=new WeakMap();
export function consumeFixturePending(pending,expected){const held=fixturePending.get(pending);if(!held)throw new AdmissionRefused('replay','Missing/copied/already-consumed private fixture pending association');fixturePending.delete(pending);const wanted=ownExact(expected,V2_BINDING_KEYS);need(canonicalData(held.binding)===canonicalData(wanted),'binding','Private pending invocation/digests changed');return held;}
/** Test-only private association. No actual host API or production permission is supplied. */
export async function exercisePreBoundary(raw,registration,capabilities){
 const intent=validatePreRequest(raw,registration),caps=keys(capabilities,['observeTrustedHost','freezeProtectedInputs','revalidateProtectedInputs','closeProtectedInputs']);for(const fn of Object.values(caps))need(typeof fn==='function','capability','Missing fixture capability');let lease;
 try{const host=await caps.observeTrustedHost(raw);need(host&&host.defaultShell==='WindowsPowerShell'&&host.requestLiteral===raw&&typeof host.tool_use_id==='string'&&host.tool_use_id.length>0&&host.tool_use_id.length<=256,'host','Fixture host association missing');lease=await caps.freezeProtectedInputs(intent);need(lease&&typeof lease==='object','capability','Missing fixture lease');need(await caps.revalidateProtectedInputs(lease,intent)===true,'input_drift','Fixture protected input drift');const pending=Object.freeze(Object.create(null));fixturePending.set(pending,{binding:intent.binding,host,raw});return Object.freeze({kind:'fixture-pre-boundary-only',authority:false,production:false,pending});}finally{if(lease)need(await caps.closeProtectedInputs(lease)===true,'close','Fixture protected input close failed');}
}

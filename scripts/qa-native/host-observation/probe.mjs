// Workspace candidate only. Importing this module neither captures nor executes.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export const TOKEN='books-host-binding-20261020-01';
export const COMMAND="$booksHostProbeToken='"+TOKEN+"'; [ordered]@{version=$PSVersionTable.PSVersion.ToString();edition=$PSVersionTable.PSEdition;image=[System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName}|ConvertTo-Json -Compress";
export const SHELL='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe';
export const ROOT='C:/Users/AnGeLZzZ/.codex/hooks/command-safety-route/books-host-observation-20261020-01';
export const EVIDENCE=ROOT+'/probe-01.json';
export const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const need=(value,message)=>{if(!value)throw Error(message);};
function record(value){need(value&&typeof value==='object'&&!Array.isArray(value),'record');const descriptors=Object.getOwnPropertyDescriptors(value);need([Object.prototype,null].includes(Object.getPrototypeOf(value))&&Reflect.ownKeys(descriptors).every(key=>typeof key==='string'&&Object.hasOwn(descriptors[key],'value')),'plain data only');return Object.fromEntries(Object.entries(descriptors).map(([key,d])=>[key,d.value]));}
const fieldNames=['command','cmd','shell','workdir','cwd','login','yield_time_ms','max_output_tokens'];
const shape=value=>value===null?'null':Array.isArray(value)?'array':typeof value;
/** Fixed capture-envelope lexical check: duplicates checked BEFORE JSON.parse. */
export function decodeCaptureEnvelope(raw){
 need(typeof raw==='string'&&Buffer.byteLength(raw,'utf8')<=65536,'raw quota');
 let at=0,nodes=0,totalKeys=0;
 const space=()=>{while(/[ \t\r\n]/.test(raw[at]??'!'))at++;};
 function string(){
  need(raw[at]==='"','JSON string');const start=at++;
  while(at<raw.length){const c=raw[at++];if(c==='"')return JSON.parse(raw.slice(start,at));if(c==='\\'){need(at<raw.length,'JSON escape');at++;}else need(c.charCodeAt(0)>=32,'JSON control');}
  throw Error('Unterminated JSON string');
 }
 function value(depth){
  need(depth<=8&&++nodes<=256,'JSON depth/node quota');space();const c=raw[at];
  if(c==='{'){
   at++;space();const seen=new Set();if(raw[at]==='}'){at++;return;}
   for(;;){const key=string();need(key.length<=80&&seen.size<32&&++totalKeys<=128,'JSON key quota');need(!seen.has(key),'Duplicate JSON key');seen.add(key);space();need(raw[at++]===':','JSON colon');value(depth+1);space();const next=raw[at++];if(next==='}')return;need(next===',','JSON object separator');space();}
  }
  if(c==='['){at++;space();let length=0;if(raw[at]===']'){at++;return;}for(;;){need(++length<=32,'JSON array quota');value(depth+1);space();const next=raw[at++];if(next===']')return;need(next===',','JSON array separator');}}
  if(c==='"'){string();return;}
  const match=/^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(raw.slice(at));need(match,'JSON value');at+=match[0].length;
 }
 value(0);space();need(at===raw.length,'JSON trailing bytes');return record(JSON.parse(raw));
}
function commandField(input){const found=['command','cmd'].filter(key=>Object.hasOwn(input,key));need(found.length===1,'one command field');return found[0];}
/** Narrow routing predicate only, never a permission decision or alias decoder. */
export function isProbe(raw){try{need(typeof raw==='string'&&Buffer.byteLength(raw,'utf8')<=1048576,'routing quota');const p=record(JSON.parse(raw)),input=record(p.tool_input);return ['command','cmd'].some(key=>input[key]===COMMAND);}catch{return false;}}
export function metadata(raw){
 const p=decodeCaptureEnvelope(raw),input=record(p.tool_input),command=commandField(input);
 need(input[command]===COMMAND&&raw.split(TOKEN).length===2,'exact unused label/command');
 need(p.hook_event_name==='PreToolUse'&&typeof p.tool_name==='string'&&/^[A-Za-z_][A-Za-z0-9_.:]{0,79}$/.test(p.tool_name),'event/tool');
 const allowedTop=['hook_event_name','tool_name','tool_input','cwd','session_id','turn_id','transcript_path','permission_mode','tool_use_id'];
 need(Object.keys(p).length<=allowedTop.length&&Object.keys(p).every(key=>allowedTop.includes(key)),'unknown envelope key');
 for(const key of ['permission_mode','transcript_path'])if(Object.hasOwn(p,key))need(typeof p[key]==='string'&&Buffer.byteLength(p[key],'utf8')<=4096,'unlogged string field');
 const keys=Object.keys(input).sort();need(keys.length<=fieldNames.length&&keys.every(key=>fieldNames.includes(key)),'unknown input key');
 const fields={};
 for(const key of keys){const value=input[key],type=shape(value);if(['command','cmd','shell','workdir','cwd'].includes(key)){need(type==='string'&&Buffer.byteLength(value,'utf8')<=65536,'string field');fields[key]={type,utf8_bytes:Buffer.byteLength(value,'utf8'),sha256:sha(Buffer.from(value,'utf8'))};}else if(key==='login'){need(type==='boolean','boolean field');fields[key]={type,value};}else{need(Number.isSafeInteger(value)&&value>=0,'integer field');fields[key]={type:'integer',value};}}
 if(Object.hasOwn(input,'shell'))need(input.shell===SHELL,'shell mismatch');
 const out={schema:'books-host-probe-observation-v1',authority:false,token:TOKEN,hook_event:p.hook_event_name,tool_name:p.tool_name,raw:{utf8_bytes:Buffer.byteLength(raw,'utf8'),sha256:sha(Buffer.from(raw,'utf8'))},input_keys:keys.map(key=>({name:key,type:shape(input[key])})),fields};
 const ids={};for(const key of ['tool_use_id','turn_id','session_id'])if(Object.hasOwn(p,key)){need(typeof p[key]==='string'&&Buffer.byteLength(p[key],'utf8')>0&&Buffer.byteLength(p[key],'utf8')<=256,'bounded correlation id');ids[key]={type:'string',utf8_bytes:Buffer.byteLength(p[key],'utf8'),sha256:sha(Buffer.from(p[key],'utf8'))};}if(Object.keys(ids).length)out.ids=ids;
 if(Object.hasOwn(p,'cwd')){need(typeof p.cwd==='string','cwd string');out.cwd={type:'string',utf8_bytes:Buffer.byteLength(p.cwd,'utf8'),sha256:sha(Buffer.from(p.cwd,'utf8'))};}
 need(Buffer.byteLength(JSON.stringify(out)+'\n','utf8')<=4096,'record quota');return out;
}
const same=(a,b)=>a.dev===b.dev&&a.ino===b.ino;
const canonical=value=>path.win32.normalize(value).toLowerCase();
function parents(io){const result=[];for(let current=ROOT;;current=path.win32.dirname(current)){result.push(current);if(path.win32.dirname(current)===current)break;}return result.reverse().map(name=>{const stat=io.lstatSync(name);need(stat.isDirectory()&&!stat.isSymbolicLink()&&canonical(io.realpathSync(name))===canonical(name),'ordinary ancestor');return {name,stat};});}
/** Ordinary filesystem evidence only; no native immutable lease/capability claim. */
export function captureProbe(raw,io=fs){
 let fd,closeAttempted=false,result={captured:false,reason:'unavailable'};
 try{const evidence=metadata(raw),bytes=Buffer.from(JSON.stringify(evidence)+'\n','utf8');const held=parents(io);
  fd=io.openSync(EVIDENCE,'wx+',0o600);const identity=io.fstatSync(fd);need(identity.isFile()&&identity.nlink===1&&identity.size===0,'fresh ordinary evidence');
  for(const item of held){const now=io.lstatSync(item.name);need(same(item.stat,now)&&now.isDirectory()&&!now.isSymbolicLink(),'ancestor drift');}
  need(io.writeSync(fd,bytes,0,bytes.length,0)===bytes.length,'partial write');io.fsyncSync(fd);
  const opened=io.fstatSync(fd),named=io.lstatSync(EVIDENCE);need(opened.size===bytes.length&&same(identity,opened)&&same(identity,named)&&named.isFile()&&!named.isSymbolicLink()&&named.nlink===1,'evidence drift');
  const readback=Buffer.alloc(bytes.length+1),count=io.readSync(fd,readback,0,readback.length,0);need(count===bytes.length&&readback.subarray(0,count).equals(bytes),'readback mismatch');
  closeAttempted=true;io.closeSync(fd);result={captured:true,authority:false,bytes:bytes.length,sha256:sha(bytes)};
 }catch(error){result={captured:false,authority:false,reason:String(error.message).slice(0,80)};}
 finally{if(fd!==undefined&&!closeAttempted)try{io.closeSync(fd);}catch{}}
 return result;
}
/** Exact probe only: failed observation conservatively denies BEFORE evaluation. */
export function probeDecision(raw,capture,forward){
 if(!isProbe(raw))return forward(raw);
 let outcome;try{outcome=capture(raw);}catch{}
 if(outcome?.captured!==true)return {status:0,stdout:JSON.stringify({hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'[books-host-observation] Exact probe capture failed; probe held.'}}),stderr:''};
 return forward(raw);
}

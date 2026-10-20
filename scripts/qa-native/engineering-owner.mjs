/** Project-only identity adapter; fixed engineering Node/CL consumers, not a generic executor.
 * Private original handles remain lexical. Snapshot evidence is descriptive, never a capability.
 */
import {createRequire} from 'node:module';
import crypto from 'node:crypto';
import path from 'node:path';
import {types} from 'node:util';
export const NODE='C:/Program Files/nodejs/node.exe';
export const MAX_MEMBERS=8192,MAX_IMAGE_CHARS=1024,MAX_EVIDENCE_BYTES=4*1024*1024;
const requireThat=(v,m)=>{if(!v)throw Error(m);};
const same=(a,b)=>typeof a==='string'&&typeof b==='string'&&path.win32.resolve(a).toLowerCase()===path.win32.resolve(b).toLowerCase();
export function checkedIdentity(value,expectedPid){
 requireThat(Number.isInteger(value?.pid)&&value.pid>0&&value.pid<=0xffffffff&&value.pid===expectedPid,'Native PID mismatch');
 requireThat(typeof value.creation_filetime==='string'&&/^[1-9][0-9]{0,19}$/.test(value.creation_filetime)&&BigInt(value.creation_filetime)<=0xffffffffffffffffn,'Exact positive uint64 FILETIME required');
 requireThat(typeof value.image==='string'&&value.image.length>0&&value.image.length<=MAX_IMAGE_CHARS&&path.win32.isAbsolute(value.image),'Bounded native image required');
 return {pid:value.pid,creation_filetime:value.creation_filetime,image:value.image};
}
function snapshotBound(value){const bytes=Buffer.byteLength(JSON.stringify(value));requireThat(bytes<=MAX_EVIDENCE_BYTES,'Native identity evidence quota exceeded');return structuredClone(value);}

const IMAGE_PHASES=new Set(['initial-supervisor','new-member','retained-list','retained-final','close-sample']);
const IMAGE_SUBPHASES=new Set(['initial','new-member','retained-list','retained-final','reuse-check']);
const uint32=v=>Number.isInteger(v)&&v>=0&&v<=0xffffffff;
function ownData(value,keys){requireThat(value&&typeof value==='object'&&!types.isProxy(value)&&(Object.getPrototypeOf(value)===Object.prototype||Object.getPrototypeOf(value)===null),'Image diagnostic object refused');requireThat(Reflect.ownKeys(value).length===keys.length&&Reflect.ownKeys(value).every(k=>keys.includes(k)),'Image diagnostic fields refused');const out={};for(const k of keys){const d=Object.getOwnPropertyDescriptor(value,k);requireThat(d&&Object.hasOwn(d,'value'),'Image diagnostic getter refused');out[k]=d.value;}return out;}
export function checkedImageDiagnostic(value){
 const d=ownData(value,['schema','owner_id','phase','subphase','expected_pid','requested_access','input_capacity','returned_length','prior_validated_identity','observed_pid','observed_creation_filetime','win32_error','error_capture_status']);
 requireThat(d.schema==='books-native-image-query-failure-v1'&&typeof d.owner_id==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(d.owner_id),'Image diagnostic binding refused');
 requireThat(IMAGE_PHASES.has(d.phase)&&IMAGE_SUBPHASES.has(d.subphase)&&uint32(d.expected_pid)&&d.expected_pid>0&&uint32(d.requested_access)&&d.input_capacity===MAX_IMAGE_CHARS+1,'Image diagnostic context refused');
 requireThat([0x00101000,0x00101101].includes(d.requested_access),'Unexpected image handle access');requireThat(!['initial','new-member'].includes(d.subphase)||d.prior_validated_identity===null,'Unvalidated identity presented as prior');requireThat(!['retained-list','retained-final','reuse-check'].includes(d.subphase)||d.prior_validated_identity!==null,'Retained prior identity missing');
 requireThat(d.returned_length===null||uint32(d.returned_length),'Image returned length refused');requireThat(d.observed_pid===null||uint32(d.observed_pid)&&d.observed_pid>0,'Image observed PID refused');
 requireThat(d.observed_creation_filetime===null||typeof d.observed_creation_filetime==='string'&&/^[1-9][0-9]{0,19}$/.test(d.observed_creation_filetime)&&BigInt(d.observed_creation_filetime)<=0xffffffffffffffffn,'Image observed creation refused');
 if(d.prior_validated_identity!==null){const p=ownData(d.prior_validated_identity,['pid','creation_filetime','image']);d.prior_validated_identity=checkedIdentity(p,d.expected_pid);}
 requireThat(['preserved-koffi-sync','unknown-zero','unknown-malformed','unknown-capture-threw'].includes(d.error_capture_status),'Image capture status refused');requireThat(d.win32_error===null||uint32(d.win32_error)&&d.win32_error>0,'Image Win32 code refused');requireThat((d.error_capture_status==='preserved-koffi-sync')===(d.win32_error!==null),'Image code/status mismatch');return d;
}

export function checkedListedSignaledDiagnostic(value){
 const d=ownData(value,['schema','owner_id','phase','listed_pid','original_identity','original_wait','query_active','query_list_count','pass_index','candidate','outcome','error']);
 requireThat(d.schema==='books-listed-signaled-first-v1'&&typeof d.owner_id==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(d.owner_id),'Overlap schema/owner refused');
 requireThat(['list','final','close-list','close-final'].includes(d.phase)&&uint32(d.listed_pid)&&d.listed_pid>0&&d.original_wait===true&&[0,1].includes(d.pass_index),'Overlap context refused');
 for(const k of ['query_active','query_list_count'])requireThat(Number.isInteger(d[k])&&d[k]>0&&d[k]<=MAX_MEMBERS,'Overlap native count refused');requireThat(d.query_active===d.query_list_count,'Overlap incomplete query refused');
 const identity=v=>{const a=ownData(v,['pid','creation_filetime']);checkedIdentity({...a,image:NODE},d.listed_pid);return a;};d.original_identity=identity(d.original_identity);
 if(d.candidate!==null){const c=ownData(d.candidate,['pid','creation_filetime','same_object','wait_signaled','in_job']);requireThat(c.pid===null||uint32(c.pid)&&c.pid>0,'Overlap candidate PID refused');requireThat(c.creation_filetime===null||typeof c.creation_filetime==='string'&&/^[1-9][0-9]{0,19}$/.test(c.creation_filetime)&&BigInt(c.creation_filetime)<=0xffffffffffffffffn,'Overlap candidate creation refused');for(const k of ['same_object','wait_signaled','in_job'])requireThat(c[k]===null||typeof c[k]==='boolean','Overlap candidate observation refused');d.candidate=c;}
 requireThat(['unobserved','reconciled','refused','persistent-overlap'].includes(d.outcome)&&(d.error===null||typeof d.error==='string'&&Buffer.byteLength(d.error)<=256),'Overlap outcome refused');
 if(d.outcome==='reconciled')requireThat(d.pass_index===0&&d.candidate!==null&&d.candidate.pid===d.original_identity.pid&&d.candidate.creation_filetime===d.original_identity.creation_filetime&&d.candidate.same_object===true&&d.candidate.wait_signaled===true&&d.candidate.in_job===true&&d.error===null,'Overlap reconciliation proof refused');
 requireThat(Buffer.byteLength(JSON.stringify(d))<=2048,'Overlap diagnostic quota');return d;
}

// Previously bound synchronous GetLastError is the FIRST native call after image failure.
// Pinned Koffi3.3.2 interp.cc WRAP preserves/restores thread LastErrorValue across JS/V8.
export function queryImageOrThrow(queryImage,getLastError,handle,buffer,length,context,observed){
 if(queryImage(handle,0,buffer,length))return;
 let code=null,status='unknown-capture-threw';try{const n=getLastError();if(uint32(n)&&n>0){code=n;status='preserved-koffi-sync';}else status=n===0?'unknown-zero':'unknown-malformed';}catch{}
 let returned=null;try{const n=length.readUInt32LE(0);if(uint32(n))returned=n;}catch{}
 const error=Error('Native executable image query failed');try{error.image_query_diagnostic=checkedImageDiagnostic({schema:'books-native-image-query-failure-v1',...context,input_capacity:MAX_IMAGE_CHARS+1,returned_length:returned,...observed,win32_error:code,error_capture_status:status});}catch{}throw error;
}

// Pure test seam. Production always obtains api from the fixed native loader below.
export function createOwnerState(api,{ownerId}={}){
 requireThat(typeof ownerId==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(ownerId),'Exact owner UUID required');
 const job=api.createJob();requireThat(job!==null,'Private Job creation failed');
 try{api.setKillOnClose(job);}catch(error){try{api.close(job);}catch{}throw error;}
 let assigned=false,disposed=false,supervisor=null,unassigned=null,last=null,terminal=null,firstImageFailure=null,closeImageFailure=null,imageDiagnosticUnavailable=false;
 const members=new Map(),handles=new Set();let firstOverlap=null,candidateSlot=null,overlapFailure=null;
 function identity(handle,pid,phase,subphase,rights,prior=null){try{return checkedIdentity(api.identity(handle,{owner_id:ownerId,phase,subphase,expected_pid:pid,requested_access:rights,prior_validated_identity:prior}),pid);}catch(error){const d=error&&typeof error==='object'&&!types.isProxy(error)?Object.getOwnPropertyDescriptor(error,'image_query_diagnostic'):null;if(d){try{requireThat(Object.hasOwn(d,'value'),'Image diagnostic getter');const value=checkedImageDiagnostic(d.value);requireThat(value.owner_id===ownerId&&value.expected_pid===pid&&value.phase===phase&&value.subphase===subphase&&value.requested_access===rights&&JSON.stringify(value.prior_validated_identity)===JSON.stringify(prior),'Image failure context mismatch');if(firstImageFailure===null)firstImageFailure=value;else if(phase==='close-sample'&&closeImageFailure===null)closeImageFailure=value;}catch{imageDiagnosticUnavailable=true;}}else {const m=error&&typeof error==='object'&&!types.isProxy(error)?Object.getOwnPropertyDescriptor(error,'message'):null;if(m&&Object.hasOwn(m,'value')&&m.value==='Native executable image query failed')imageDiagnosticUnavailable=true;}throw error;}}
 function signaled(handle){const value=api.signaled(handle);requireThat(typeof value==='boolean','Native wait state refused');return value;}
 function retainedIdentity(record,pid){
  const value=ownData(api.retainedIdentity(record.handle),['pid','creation_filetime']);
  const confirmed=checkedIdentity({...value,image:record.identity.image},pid);
  requireThat(confirmed.creation_filetime===record.identity.creation_filetime,'Retained process-object creation identity changed');return confirmed;
 }
 function record(handle,pid,closing){const value=identity(handle,pid,closing?'close-sample':'new-member','new-member',0x00101000);requireThat(api.belongs(handle,job),'Retained member is not in exact private Job');return {handle,identity:Object.freeze(value),rights:0x00101000};}
 function overlap(old,pid,phase,pass,active,count){
  const diagnostic={schema:'books-listed-signaled-first-v1',owner_id:ownerId,phase,listed_pid:pid,original_identity:{pid:old.identity.pid,creation_filetime:old.identity.creation_filetime},original_wait:true,query_active:active,query_list_count:count,pass_index:pass,candidate:null,outcome:'unobserved',error:null};
  checkedListedSignaledDiagnostic(diagnostic);if(firstOverlap===null)firstOverlap=diagnostic; // BEFORE any further native observation.
  try{
   requireThat(pass===0,'Persistent listed/signaled overlap on second pass refuses');
   requireThat(candidateSlot===null&&typeof api.sameObject==='function','Listed/signaled comparator unavailable or failure slot occupied');
   retainedIdentity(old,pid);
   const handle=api.open(pid,0x00101000);requireThat(handle!==null&&handle!==undefined,'Listed/signaled candidate open failed');
   candidateSlot={handle,identity:null,in_job:null,close_uncertain:false};handles.add(handle); // Registration precedes queries.
   requireThat(handle!==old.handle,'Diagnostic candidate replaced original handle');
   diagnostic.candidate={pid:null,creation_filetime:null,same_object:null,wait_signaled:null,in_job:null};
   const basic=ownData(api.retainedIdentity(handle),['pid','creation_filetime']);const candidate=checkedIdentity({...basic,image:old.identity.image},basic.pid);
   candidateSlot.identity={pid:candidate.pid,creation_filetime:candidate.creation_filetime};diagnostic.candidate.pid=candidate.pid;diagnostic.candidate.creation_filetime=candidate.creation_filetime;requireThat(candidate.pid===pid,'Listed/signaled candidate PID differs');
   const sameObject=api.sameObject(old.handle,handle);requireThat(typeof sameObject==='boolean','Kernel object comparison result refused');diagnostic.candidate.same_object=sameObject;
   const done=signaled(handle);diagnostic.candidate.wait_signaled=done;
   const inJob=api.belongs(handle,job);requireThat(typeof inJob==='boolean','Candidate Job membership result refused');candidateSlot.in_job=inJob;diagnostic.candidate.in_job=inJob;
   requireThat(api.belongs(old.handle,job)===true,'Original overlap object left exact Job');
   requireThat(sameObject&&candidate.creation_filetime===old.identity.creation_filetime&&done&&signaled(old.handle),'Listed/signaled reused PID or object/wait mismatch refuses');
   requireThat(inJob,'Listed/signaled candidate outside exact Job');
   candidateSlot.close_uncertain=true;api.close(handle);handles.delete(handle);candidateSlot=null;
   diagnostic.outcome='reconciled';checkedListedSignaledDiagnostic(diagnostic);return;
  }catch(error){diagnostic.outcome=pass===1?'persistent-overlap':'refused';const m=error&&typeof error==='object'&&!types.isProxy(error)?Object.getOwnPropertyDescriptor(error,'message'):null;diagnostic.error=m&&Object.hasOwn(m,'value')&&typeof m.value==='string'?m.value.slice(0,64):'Listed/signaled observation failed';overlapFailure=diagnostic.error;checkedListedSignaledDiagnostic(diagnostic);throw error;}
 }
 function sample(closing=false){
  requireThat(!disposed,'Sampling closed owner');requireThat(overlapFailure===null,'Unreconciled listed/signaled candidate or overlap: '+overlapFailure);
  passes:for(let pass=0;pass<2;pass++){
   const {active,pids}=api.query(job,MAX_MEMBERS);
   requireThat(Number.isInteger(active)&&active>=0&&Array.isArray(pids)&&active===pids.length&&active<=MAX_MEMBERS&&new Set(pids).size===pids.length,'Native job membership list is incomplete');
   const listed=new Set(pids);
   for(const pid of pids){requireThat(Number.isInteger(pid)&&pid>0&&pid<=0xffffffff,'Invalid listed PID');const old=members.get(pid);
    if(old){if(signaled(old.handle)){overlap(old,pid,closing?'close-list':'list',pass,active,pids.length);continue passes;}retainedIdentity(old,pid);requireThat(api.belongs(old.handle,job),'Retained listed process left exact Job');continue;}
    const handle=api.open(pid,0x00101000);requireThat(handle!==null,'Cannot retain a native job member');handles.add(handle);
    try{members.set(pid,record(handle,pid,closing));}catch(error){try{api.close(handle);handles.delete(handle);}catch{}throw error;}
   }
   const identities=[];let unsignaled=0;
   for(const [pid,r]of members){
    const done=signaled(r.handle),absent=!listed.has(pid);
    if(done&&!absent){overlap(r,pid,closing?'close-final':'final',pass,active,pids.length);continue passes;}
    retainedIdentity(r,pid);if(!done)unsignaled++;
    identities.push({pid:r.identity.pid,creation_filetime:r.identity.creation_filetime,image_path_at_admission:r.identity.image,signaled:done,object_proof:{schema:'books-retained-object-proof-v2',image_basis:'admission-image-continuously-retained-object',wait_signaled:done,pid_creation_confirmed:true,sample_list_absent:absent}});
   }
   identities.sort((a,b)=>a.pid-b.pid);
   last=snapshotBound({active,retained:members.size,unsignaled,zero:active===0&&unsignaled===0,identity:{schema:'books-engineering-native-owner-v3',owner_id:ownerId,supervisor,observed:identities}});return structuredClone(last);
  }
  throw Error('Listed/signaled two-pass bound exhausted');
 }
 return {
  assign(pid){requireThat(!assigned&&!disposed,'Native owner assignment is one-shot');assigned=true;requireThat(Number.isInteger(pid)&&pid>0&&pid<=0xffffffff,'Invalid supervisor PID');const h=api.open(pid,0x00101101);requireThat(h!==null,'Cannot retain owned supervisor');handles.add(h);
   // Initial PID is solely the existing trusted inert-supervisor launch bridge.
   const value=identity(h,pid,'initial-supervisor','initial',0x00101101);requireThat(same(value.image,NODE),'Assigned supervisor is not fixed installed Node');unassigned=h;members.set(pid,{handle:h,identity:Object.freeze(value),rights:0x00101101});api.assign(job,h);requireThat(api.belongs(h,job),'Assigned supervisor not in exact Job');supervisor=value;unassigned=null;
  },sample,
  terminate(){requireThat(!disposed,'Terminate closed owner');if(unassigned&&!signaled(unassigned))api.terminateProcess(unassigned);api.terminateJob(job);},
  close(){if(disposed)return;let failure=null,final=null;try{final=sample(true);requireThat(assigned&&supervisor&&final.zero,'Native owner close before proved zero');}catch(error){failure=error.message;}
   disposed=true;const closeErrors=[];let retainForOuter=false;if(overlapFailure!==null){try{requireThat(!candidateSlot||!candidateSlot.close_uncertain,'Candidate close continuity unknown');const q=api.query(job,MAX_MEMBERS);requireThat(q.active===0&&Array.isArray(q.pids)&&q.pids.length===0,'Failure candidate original Job not drained');for(const r of members.values()){retainedIdentity(r,r.identity.pid);requireThat(signaled(r.handle),'Original retained object not drained');}if(candidateSlot){requireThat(candidateSlot.identity!==null,'Candidate identity unknown');const seen=ownData(api.retainedIdentity(candidateSlot.handle),['pid','creation_filetime']);requireThat(JSON.stringify(seen)===JSON.stringify(candidateSlot.identity)&&signaled(candidateSlot.handle),'Failure candidate not drained');}}catch(error){retainForOuter=true;closeErrors.push(String(error.message).slice(0,256));}}if(!retainForOuter)try{api.close(job);}catch(error){closeErrors.push(error.message);}if(!retainForOuter)for(const h of handles)try{api.close(h);}catch(error){closeErrors.push(error.message);}
   terminal=snapshotBound({schema:'books-engineering-owner-terminal-v1',owner_id:ownerId,closed:!failure&&closeErrors.length===0,native:final,failure,close_errors:closeErrors,image_query_failure:firstImageFailure,close_image_query_failure:closeImageFailure,image_query_diagnostic_unavailable:imageDiagnosticUnavailable,...(firstOverlap===null?{}:{listed_signaled_diagnostic:checkedListedSignaledDiagnostic(firstOverlap)})});if(!terminal.closed)throw Error(failure??closeErrors.join(';'));
  },
  evidence(){return terminal===null?null:structuredClone(terminal);}
 };
}
function nativeApi(koffiRoot){
 requireThat(process.arch==='x64'&&process.platform==='win32','Windows x64 native ownership required');const koffi=createRequire(import.meta.url)(koffiRoot),k=koffi.load('kernel32.dll');
 const create=k.func('void* __stdcall CreateJobObjectW(void*,void*)'),set=k.func('bool __stdcall SetInformationJobObject(void*,int,void*,uint32_t)'),open=k.func('void* __stdcall OpenProcess(uint32_t,bool,uint32_t)'),assign=k.func('bool __stdcall AssignProcessToJobObject(void*,void*)'),query=k.func('bool __stdcall QueryInformationJobObject(void*,int,void*,uint32_t,void*)'),belongs=k.func('bool __stdcall IsProcessInJob(void*,void*,void*)'),wait=k.func('uint32_t __stdcall WaitForSingleObject(void*,uint32_t)'),terminate=k.func('bool __stdcall TerminateJobObject(void*,uint32_t)'),terminateProcess=k.func('bool __stdcall TerminateProcess(void*,uint32_t)'),close=k.func('bool __stdcall CloseHandle(void*)'),getPid=k.func('uint32_t __stdcall GetProcessId(void*)'),times=k.func('bool __stdcall GetProcessTimes(void*,void*,void*,void*,void*)'),image=k.func('bool __stdcall QueryFullProcessImageNameW(void*,uint32_t,void*,void*)'),getLastError=k.func('uint32_t __stdcall GetLastError()');
 const compare=koffi.load('kernelbase.dll').func('bool __stdcall CompareObjectHandles(void*,void*)');
 return {
  sameObject(a,b){return Boolean(compare(a,b));},
  createJob(){return create(null,null);},setKillOnClose(h){const b=Buffer.alloc(144);b.writeUInt32LE(0x2000,16);requireThat(set(h,9,b,b.length),'Kill-on-close/no-breakaway configuration failed');},
  open(pid,rights){return open(rights,false,pid);},assign(job,h){requireThat(assign(job,h),'Native exact Job assignment failed');},belongs(h,job){const b=Buffer.alloc(4);requireThat(belongs(h,job,b),'Native membership query failed');return b.readUInt32LE(0)===1;},
  identity(h,context){const pid=getPid(h),made=Buffer.alloc(8),exit=Buffer.alloc(8),kernel=Buffer.alloc(8),user=Buffer.alloc(8);requireThat(pid>0&&times(h,made,exit,kernel,user),'Native creation identity query failed');const b=Buffer.alloc((MAX_IMAGE_CHARS+1)*2),n=Buffer.alloc(4);n.writeUInt32LE(MAX_IMAGE_CHARS+1);queryImageOrThrow(image,getLastError,h,b,n,context,{observed_pid:pid,observed_creation_filetime:String(made.readBigUInt64LE(0))});requireThat(n.readUInt32LE(0)<=MAX_IMAGE_CHARS,'Native image over quota');return {pid,creation_filetime:String(made.readBigUInt64LE(0)),image:b.toString('utf16le',0,n.readUInt32LE(0)*2)};},
  retainedIdentity(h){const pid=getPid(h),made=Buffer.alloc(8),exit=Buffer.alloc(8),kernel=Buffer.alloc(8),user=Buffer.alloc(8);requireThat(pid>0&&times(h,made,exit,kernel,user),'Native retained PID/creation query failed');return {pid,creation_filetime:String(made.readBigUInt64LE(0))};},
  query(job,max){const b=Buffer.alloc(8+max*8);requireThat(query(job,3,b,b.length,null),'Native Job membership query failed');const active=b.readUInt32LE(0),listed=b.readUInt32LE(4);requireThat(active===listed&&listed<=max,'Native job membership list is incomplete');const pids=[];for(let i=0;i<listed;i++){const id=b.readBigUInt64LE(8+i*8);requireThat(id>0n&&id<=0xffffffffn,'Native member PID overflow');pids.push(Number(id));}return {active,pids};},
  signaled(h){const v=wait(h,0);if(v===0)return true;if(v===258)return false;throw Error('Retained native member wait failed');},terminateJob(job){requireThat(terminate(job,1),'Exact native Job termination failed');},terminateProcess(h){requireThat(terminateProcess(h,1),'Exact retained process termination failed');},close(h){requireThat(close(h),'Native ownership handle close failed');}
 };
}
export function createEngineeringOwner(koffiRoot,options){return createOwnerState(nativeApi(koffiRoot),options);}
export function newOwnerId(){return crypto.randomUUID();}
export function validateNativeSnapshot(value,ownerId){
 requireThat(typeof ownerId==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(ownerId),'Native owner UUID refused');
 const n=ownData(value,['active','retained','unsignaled','zero','identity']);
 for(const key of ['active','retained','unsignaled'])requireThat(Number.isInteger(n[key])&&n[key]>=0&&n[key]<=MAX_MEMBERS,'Native snapshot count refused');
 requireThat(typeof n.zero==='boolean'&&n.zero===(n.active===0&&n.unsignaled===0),'Native zero/count contradiction');
 const id=ownData(n.identity,['schema','owner_id','supervisor','observed']);requireThat(id.schema==='books-engineering-native-owner-v3'&&id.owner_id===ownerId,'Native proof schema/owner refused');
 const supervisor=checkedIdentity(ownData(id.supervisor,['pid','creation_filetime','image']),id.supervisor.pid);
 requireThat(Array.isArray(id.observed)&&!types.isProxy(id.observed)&&Object.getPrototypeOf(id.observed)===Array.prototype&&id.observed.length<=MAX_MEMBERS&&Reflect.ownKeys(id.observed).length===id.observed.length+1,'Native observed array refused');
 const observed=[],seen=new Set();
 for(let i=0;i<id.observed.length;i++){
  const descriptor=Object.getOwnPropertyDescriptor(id.observed,String(i));requireThat(descriptor&&Object.hasOwn(descriptor,'value'),'Native observed getter refused');
  const m=ownData(descriptor.value,['pid','creation_filetime','image_path_at_admission','signaled','object_proof']);const identity=checkedIdentity({pid:m.pid,creation_filetime:m.creation_filetime,image:m.image_path_at_admission},m.pid);requireThat(!seen.has(m.pid)&&typeof m.signaled==='boolean','Native observed PID/signal refused');seen.add(m.pid);
  const proof=ownData(m.object_proof,['schema','image_basis','wait_signaled','pid_creation_confirmed','sample_list_absent']);requireThat(proof.schema==='books-retained-object-proof-v2'&&typeof proof.sample_list_absent==='boolean'&&proof.pid_creation_confirmed===true&&proof.wait_signaled===m.signaled,'Native object proof refused');
  requireThat(proof.image_basis==='admission-image-continuously-retained-object'&&(!m.signaled||proof.sample_list_absent===true),'Native admission-image proof basis refused');
  observed.push({pid:identity.pid,creation_filetime:identity.creation_filetime,image_path_at_admission:identity.image,signaled:m.signaled,object_proof:proof});
 }
 requireThat(n.retained===observed.length&&n.unsignaled===observed.filter(m=>!m.signaled).length&&n.active===observed.filter(m=>!m.object_proof.sample_list_absent).length,'Native snapshot membership/count proof differs');
 requireThat(observed.some(m=>m.pid===supervisor.pid&&m.creation_filetime===supervisor.creation_filetime&&m.image_path_at_admission===supervisor.image),'Native supervisor absent from retained proof');
 return snapshotBound({...n,identity:{schema:id.schema,owner_id:ownerId,supervisor,observed}});
}
export function validateOwnedResult(result,evidence,ownerId){
 requireThat(result?.ok===true&&result.closed===true&&!result.forced&&!result.timedOut&&!result.overflow&&!result.truncated&&!result.closureError&&!result.reason&&!result.error&&result.signal===null&&result.code===0,'Owned operation failed or uncertain');
 requireThat(evidence?.schema==='books-engineering-owner-terminal-v1'&&evidence.owner_id===ownerId&&evidence.closed===true&&!evidence.failure&&evidence.close_errors.length===0,'Original owner checked-close evidence missing');
 const overlap=Object.getOwnPropertyDescriptor(evidence,'listed_signaled_diagnostic');if(overlap){requireThat(Object.hasOwn(overlap,'value'),'Overlap evidence getter refused');if(overlap.value!==null){const first=checkedListedSignaledDiagnostic(overlap.value);requireThat(first.owner_id===ownerId&&first.outcome==='reconciled','Unreconciled overlap cannot authorize owned success');}}
 validateNativeSnapshot(result.native,ownerId);
 requireThat(result.native?.zero===true&&result.native.active===0&&result.native.unsignaled===0&&result.native.identity?.owner_id===ownerId,'Native zero/identity proof missing');
 requireThat(JSON.stringify(result.native)===JSON.stringify(evidence.native),'Returned native snapshot differs from actual owner terminal snapshot');
 requireThat(result.pid===evidence.native.identity.supervisor?.pid&&same(evidence.native.identity.supervisor.image,NODE),'Actual supervisor identity mismatch');return structuredClone(evidence.native.identity);
}
export function matchController(identity,wire){
 const candidate=checkedIdentity(wire,wire?.pid);requireThat(same(candidate.image,NODE),'Fixed controller image mismatch');const match=identity.observed.find(x=>x.pid===candidate.pid&&x.creation_filetime===candidate.creation_filetime&&same(x.image_path_at_admission,candidate.image)&&x.signaled===true);requireThat(match&&match.pid!==identity.supervisor.pid,'Reported controller was not actually retained in original owner');return match;
}

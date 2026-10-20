/** Bounded diagnostic DATA only. No ownership/acceptance capability, executor or fallback path. */
import {types} from 'node:util';
import {checkedImageDiagnostic,checkedListedSignaledDiagnostic} from './engineering-owner.mjs';
export const MAX_DIAGNOSTIC_BYTES=16*1024*1024;
export const FIXTURE_TOTAL_MS=600000,OUTER_OWNER_TIMEOUT_MS=570000,DIAGNOSTIC_ADMISSION_FLOOR_MS=2000,INNER_RETURN_RESERVE_MS=10000;
// Existing runOwned stops work2000ms before its own timeout; no native close semantics change.
export function fixtureInnerRemaining(deadline,now=Date.now()){
 need(Number.isSafeInteger(deadline)&&Number.isSafeInteger(now),'Finite original fixture clock required');
 const remaining=deadline-(FIXTURE_TOTAL_MS-OUTER_OWNER_TIMEOUT_MS)-now-INNER_RETURN_RESERVE_MS;
 need(remaining>4000&&remaining<=OUTER_OWNER_TIMEOUT_MS-INNER_RETURN_RESERVE_MS,'No remaining original fixture budget');return remaining;
}
const SNAPSHOT_BYTES=4*1024*1024,OUTPUT_BYTES=1048576;
const stages=new Set(['outer-result','pure-start','pure-complete','inner-start','inner-result','controller-error','owner-id-start','owner-id-error','owner-id-bound']);
const need=(v,m)=>{if(!v)throw Error(m);};
const string=max=>({kind:'string',max}),number={kind:'number'},bool={kind:'boolean'};
const nullable=spec=>({kind:'nullable',spec}),array=(spec,max)=>({kind:'array',spec,max}),object=fields=>({kind:'object',fields});
const pid=number,time=string(20),image=string(1024);
const objectProof=object({schema:string(64),image_basis:string(64),wait_signaled:bool,pid_creation_confirmed:bool,sample_list_absent:bool});
const supervisorIdentity=object({pid,creation_filetime:time,image});
const memberIdentity=object({pid,creation_filetime:time,image_path_at_admission:image,signaled:bool,object_proof:objectProof});
const native=object({active:number,retained:number,unsignaled:number,zero:bool,identity:object({schema:string(128),owner_id:string(36),supervisor:nullable(supervisorIdentity),observed:array(memberIdentity,8192)})});
const uint32={kind:'uint32'};
const imageFailure=object({schema:string(128),owner_id:string(36),phase:string(32),subphase:string(32),expected_pid:uint32,requested_access:uint32,input_capacity:uint32,returned_length:nullable(uint32),prior_validated_identity:nullable(supervisorIdentity),observed_pid:nullable(uint32),observed_creation_filetime:nullable(time),win32_error:nullable(uint32),error_capture_status:string(64)});
const overlapCandidate=object({pid:nullable(uint32),creation_filetime:nullable(time),same_object:nullable(bool),wait_signaled:nullable(bool),in_job:nullable(bool)});
const overlap=object({schema:string(64),owner_id:string(36),phase:string(16),listed_pid:uint32,original_identity:object({pid:uint32,creation_filetime:time}),original_wait:bool,query_active:uint32,query_list_count:uint32,pass_index:uint32,candidate:nullable(overlapCandidate),outcome:string(32),error:nullable(string(256))});
const evidence=object({schema:string(128),owner_id:string(36),closed:bool,native:nullable(native),failure:nullable(string(4096)),close_errors:array(string(4096),8193),image_query_failure:nullable(imageFailure),close_image_query_failure:nullable(imageFailure),image_query_diagnostic_unavailable:bool,listed_signaled_diagnostic:nullable(overlap)});
const result=object({kind:string(32),code:nullable(number),signal:nullable(string(128)),error:nullable(string(4096)),out:string(OUTPUT_BYTES),err:string(OUTPUT_BYTES),supervisorErr:string(OUTPUT_BYTES),ok:bool,closed:bool,forced:bool,timedOut:bool,overflow:bool,truncated:bool,reason:nullable(string(4096)),closureError:nullable(string(4096)),pid:nullable(pid),ownership:string(64),native:nullable(native),elapsedMs:number,outputBytes:number});
const error=object({name:string(128),message:string(4096),code:nullable({kind:'error-code'})});
const context=object({invocation_id:string(36),plan_sha256:string(64),source_admission_sha256:string(64),owner_id:string(36),outer_owner_id:string(36),stage:string(32),kind:string(64),pure_passed:number,planned_owner_id:string(36),owner_case_index:number});
function plain(value){need(value!==null&&typeof value==='object'&&!types.isProxy(value),'Diagnostic object/proxy refused');const proto=Object.getPrototypeOf(value);need(proto===Object.prototype||proto===null,'Diagnostic prototype refused');}
function clone(value,spec,seen=new Set()){
 need(value!==undefined,'Unsupported undefined diagnostic own field');
 if(spec.kind==='nullable'){if(value===null)return null;return clone(value,spec.spec,seen);}
 if(spec.kind==='string'){need(typeof value==='string'&&Buffer.byteLength(value)<=spec.max,'Diagnostic string refused');return value;}
 if(spec.kind==='uint32'){need(Number.isInteger(value)&&value>=0&&value<=0xffffffff,'Diagnostic uint32 refused');return value;}
 if(spec.kind==='number'){need(typeof value==='number'&&Number.isFinite(value),'Diagnostic finite number required');return value;}
 if(spec.kind==='boolean'){need(typeof value==='boolean','Diagnostic boolean required');return value;}
 if(spec.kind==='error-code'){need(typeof value==='string'&&Buffer.byteLength(value)<=128||typeof value==='number'&&Number.isFinite(value),'Diagnostic error code refused');return value;}
 need(value!==null&&typeof value==='object'&&!types.isProxy(value)&&!seen.has(value),'Diagnostic cycle/proxy refused');seen.add(value);
 try{
  if(spec.kind==='array'){need(Array.isArray(value)&&Object.getPrototypeOf(value)===Array.prototype&&value.length<=spec.max,'Diagnostic array refused');const keys=Reflect.ownKeys(value);need(keys.length===value.length+1,'Diagnostic array keys refused');const out=[];for(let i=0;i<value.length;i++){const d=Object.getOwnPropertyDescriptor(value,String(i));need(d&&Object.hasOwn(d,'value'),'Diagnostic array getter/hole refused');out.push(clone(d.value,spec.spec,seen));}return out;}
  plain(value);const keys=Reflect.ownKeys(value);need(keys.length<=64&&keys.every(k=>typeof k==='string'&&Object.hasOwn(spec.fields,k)),'Diagnostic unknown field refused');const out=Object.create(null);for(const key of keys){const d=Object.getOwnPropertyDescriptor(value,key);need(d&&Object.hasOwn(d,'value'),'Diagnostic getter refused');out[key]=clone(d.value,spec.fields[key],seen);}return out;
 }finally{seen.delete(value);}
}
export function describeError(value){
 if(value===null||value===undefined)return null;need(typeof value==='object'&&!types.isProxy(value),'Diagnostic exception type refused');const out={name:'Error',message:'',code:null};
 for(const key of ['name','message','code']){const d=Object.getOwnPropertyDescriptor(value,key);if(d){need(Object.hasOwn(d,'value'),'Exception getter refused');out[key]=d.value;}}
 return clone(out,error);
}
export function enforceEncodedDiagnosticQuota(bytes){need(Buffer.isBuffer(bytes)&&bytes.length<=MAX_DIAGNOSTIC_BYTES,'Diagnostic encoded quota exceeded');return bytes;}
export function encodeDiagnostic(input){
 plain(input);const own=(key)=>{const d=Object.getOwnPropertyDescriptor(input,key);need(d&&Object.hasOwn(d,'value'),'Diagnostic input getter/missing field');return d.value;};need(Reflect.ownKeys(input).every(k=>['context','result','evidence','run_error','evidence_error'].includes(k)),'Unknown diagnostic capture input');
 const c=clone(own('context'),context);need(stages.has(c.stage),'Unknown diagnostic stage');
 const r=own('result'),e=own('evidence');const record={schema:'books-native-owner-diagnostic-v1',authoritative:false,context:c,result:r===null?null:clone(r,result),evidence:e===null?null:clone(e,evidence),run_error:own('run_error')===null?null:clone(own('run_error'),error),evidence_error:own('evidence_error')===null?null:clone(own('evidence_error'),error)};
 if(record.evidence)for(const key of ['image_query_failure','close_image_query_failure'])if(record.evidence[key]!==undefined&&record.evidence[key]!==null)checkedImageDiagnostic(record.evidence[key]);
 if(record.evidence?.listed_signaled_diagnostic!==undefined&&record.evidence.listed_signaled_diagnostic!==null){const first=checkedListedSignaledDiagnostic(record.evidence.listed_signaled_diagnostic);need(first.owner_id===record.evidence.owner_id,'Overlap evidence owner differs');}
 if(record.result)need(['out','err','supervisorErr'].reduce((n,k)=>n+(typeof record.result[k]==='string'?Buffer.byteLength(record.result[k]):0),0)<=OUTPUT_BYTES,'Combined captured output quota');
 if(record.result?.native)need(Buffer.byteLength(JSON.stringify(record.result.native))<=SNAPSHOT_BYTES,'Returned native snapshot quota');if(record.evidence)need(Buffer.byteLength(JSON.stringify(record.evidence))<=SNAPSHOT_BYTES,'Terminal evidence quota');
 return enforceEncodedDiagnosticQuota(Buffer.from(JSON.stringify(record)));
}
export function captureFailed(stage,code){return {schema:'books-native-diagnostic-capture-failed-v1',authoritative:false,stage:stages.has(stage)?stage:'controller-error',diagnostic_failure:code,original_failure:'not replaced or classified by logger'};}
export function evidenceSnapshot(owner){try{return {value:owner.evidence(),error:null};}catch(e){try{return {value:null,error:describeError(e)};}catch{return {value:null,error:{name:'Error',message:'evidence exception could not be safely described',code:null}};}}}
export function persistDiagnostic(io,path,input,{deadline,now=()=>Date.now(),stage='controller-error'}={}){
 let bytes,failed=null;try{need(now()<deadline-DIAGNOSTIC_ADMISSION_FLOOR_MS,'Diagnostic reserve exhausted');bytes=encodeDiagnostic(input);}catch{failed=captureFailed(stage,'serialize_or_reserve_refused');bytes=Buffer.from(JSON.stringify(failed));}
 try{need(now()<deadline-DIAGNOSTIC_ADMISSION_FLOOR_MS,'Diagnostic reserve exhausted');const proof=io.writeBytesNew(path,bytes);const readback=io.readRecordBytes(proof);need(Buffer.isBuffer(readback)&&readback.equals(bytes),'Diagnostic readback mismatch');need(now()<deadline,'Diagnostic IO overrun');return {capture_ok:failed===null,record:proof,capture_failed:failed};}catch{return {capture_ok:false,record:null,capture_failed:captureFailed(stage,'native_write_readback_or_budget_failed')};}
}

export function captureObserverDiagnostic(createIo,{root,invocationId,deadline,now=()=>Date.now()},input){
 const shared='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared';let io=null,status={capture_ok:false,record:null,capture_failed:captureFailed('outer-result','native_namespace_unavailable')};
 try{
  need(/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(invocationId)&&root===shared+'/native-fixture-diag-'+invocationId,'Unreviewed diagnostic namespace');need(now()<deadline-DIAGNOSTIC_ADMISSION_FLOOR_MS,'Original logging reserve exhausted');
  io=createIo();io.ancestry(root);io.createDirectory(shared,'native-fixture-diag-'+invocationId);
  status=persistDiagnostic(io,root+'/owner-result.json',input,{deadline,now,stage:'outer-result'});
 }catch{status={capture_ok:false,record:null,capture_failed:captureFailed('outer-result','native_namespace_or_budget_failed')};}
 finally{if(io)try{io.teardown();}catch{status={...status,capture_ok:false,capture_failed:captureFailed('outer-result','diagnostic_native_close_failed')};}}
 return status;
}

// Pure seam wraps exactly the existing call; production supplies newOwnerId unchanged.
export function checkpointOwnerId(journal,kind,oneCall){
 need(['nested-final','linger-root','flood','wait'].includes(kind),'Unknown owner-id checkpoint kind');
 need(journal('owner-id-start',kind).capture_ok,'Owner-id-start diagnostic capture failed');
 try{return oneCall();}catch(original){try{journal('owner-id-error',kind,{run_error:describeError(original)});}catch{}throw original;}
}

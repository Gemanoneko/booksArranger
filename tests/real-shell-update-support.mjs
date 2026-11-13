// Fixed PA-1 support. Imports are inert; native adapters are loaded only by the
// separately admitted, explicitly authorized worker/controller.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {isDeepStrictEqual} from 'node:util';
import {binding,sameBinding,hash,NATIVE_CASE,normalOwned,validateAuthority} from '../scripts/qa-phase-contract.mjs';
export const need=(ok,message)=>{if(!ok)throw Error(message);};
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
// File inventories compare exact members and typed facts; JSON property order is not identity.
export const sameFileTree=(a,b)=>isDeepStrictEqual(a,b);
const norm=p=>path.win32.resolve(p).replaceAll('\\','/').toLowerCase();
export const within=(p,root)=>norm(p).startsWith(norm(root)+'/');
export function privatePath(p){
 need(typeof p==='string'&&/^[A-Z]:[\\/]/i.test(p),'Private absolute drive path required');
 const tail=p.slice(3),parts=tail.split(/[\\/]/);
 need(!tail||parts.every(part=>part&&!/[. ]$|[:*?"<>|\x00-\x1f]/.test(part)),'Noncanonical private path');
 return p;
}

export function assertLocalPaths(api,paths){
 const checkedDrives=new Set(),checkedPaths=new Set();
 for(const candidate of paths){
  const target=path.win32.normalize(privatePath(candidate)),root=path.win32.parse(target).root;
  const drive=root.slice(0,2).toUpperCase();
  if(!checkedDrives.has(drive)){
   need(api.driveType(root)===3&&/^\\Device\\HarddiskVolume\d+$/i.test(api.dosTarget(drive)),
    'Private PA-1 paths require a directly mounted fixed local drive: '+drive);
   checkedDrives.add(drive);
  }
  for(let member=target;;member=path.win32.dirname(member)){
   const key=member.toLowerCase();
   if(!checkedPaths.has(key)){
    const attributes=api.attributes(member);
    need(Number.isInteger(attributes)&&attributes>=0&&attributes<0xffffffff&&!(attributes&0x400),
     'Unavailable or reparse PA-1 path: '+member);
    checkedPaths.add(key);
   }
   if(member===root)break;
  }
 }
}

// Invoke only after the existing source, DLL and Koffi input pins pass.
export async function verifyLocalPaths(plan,manifest,existing=[]){
 need(process.platform==='win32'&&process.arch==='x64','Native PA-1 requires reviewed Windows x64 ABI');
 const require=createRequire(import.meta.url),K=require(plan.koffi_root).load('C:/Windows/System32/kernel32.dll');
 const driveType=K.func('uint32_t __stdcall GetDriveTypeW(str16)');
 const queryDos=K.func('uint32_t __stdcall QueryDosDeviceW(str16,void *,uint32_t)');
 const attributes=K.func('uint32_t __stdcall GetFileAttributesW(str16)');
 function dosTarget(drive){
  const buffer=Buffer.alloc(65536),count=queryDos(drive,buffer,buffer.length/2);
  need(count>0&&count<=buffer.length/2,'PA-1 drive mapping unavailable: '+drive);
  return buffer.subarray(0,count*2).toString('utf16le').split('\0',1)[0];
 }
 const roots=[plan.evidence_root,plan.source_root,plan.koffi_root,plan.payload.root,path.win32.dirname(plan.fixture_root),...existing];
 const payload=Object.keys(manifest.payload.files).map(name=>path.win32.join(plan.payload.root,name));
 assertLocalPaths({driveType,dosTarget,attributes:p=>attributes(path.win32.toNamespacedPath(p))},
  [...roots,plan.authority.path,plan.payload.manifest.path,...plan.inputs.map(ref=>ref.path),...plan.trees.map(tree=>tree.root),...payload]);
 for(const root of roots)need(norm(await fs.realpath(root))===norm(root),'PA-1 path resolves through an alias: '+root);
}
export function validatePlan(plan,authority){
 need(plan?.schema==='books-real-shell-plan-v1','Fixed real-shell plan absent');binding(plan.binding);validateAuthority(authority,plan.binding);
 need(equal(plan.case,NATIVE_CASE)&&plan.deadlineMs===600000&&plan.phase_contract_sha256===plan.binding.phase_contract_sha256,'Fixed phase/deadline differs');
 for(const key of ['fixture_root','evidence_root','source_root','koffi_root'])privatePath(plan[key]);
 if(!plan.recovery)need(path.win32.basename(plan.fixture_root)==='pa1-'+plan.binding.build_id&&within(plan.fixture_root,plan.evidence_root),'Fresh candidate fixture root differs');
 else{
  const r=plan.recovery;
  need(r.schema==='books-pa1-one-failed-attempt-v1'&&[2,3,4,5].includes(r.attempt)&&r.fixture_root===plan.fixture_root,'Only the four explicitly recorded failed attempts are supported');
  const keys=['attempt','cache_refresh','exe_identity','fixture_identity','fixture_root','original_artifact_manifest','original_baseline','original_callback','original_controller_owned','original_plan','schema'];
  if(r.attempt>=3)keys.push('second_failed_attempt','engine_port','engine_record','engine_record_identity');
  if(r.attempt>=4)keys.push('third_failed_attempt','engine_record_absent');
   if(r.attempt===5)keys.push('fourth_failed_attempt');
  need(Object.keys(r).sort().join('|')===keys.sort().join('|'),'Exact failed-attempt recovery facts required');
  need(Array.isArray(r.cache_refresh)&&[0,93].includes(r.cache_refresh.length),'Only the observed 93-cache refresh is supported');
  const prior=path.win32.dirname(r.original_plan.path);
  need(within(plan.fixture_root,prior)&&!within(plan.evidence_root,plan.fixture_root)&&norm(prior)!==norm(plan.evidence_root),'Separate recovery evidence and original private fixture required');
  for(const key of ['original_plan','original_callback','original_controller_owned','original_baseline','original_artifact_manifest'])need(within(r[key].path,prior),'Recovery proof escapes original private arena');
 }
 need(!within(plan.source_root,plan.fixture_root)&&!within(plan.evidence_root,plan.source_root),'Source/output overlap');
 need(plan.authority?.sha256===hash(JSON.stringify(authority)),'Canonical authority bytes differ from plan');
 need(plan.node?.path==='C:/Program Files/nodejs/node.exe'&&/^[a-f0-9]{64}$/.test(plan.node.sha256),'Fixed installed Node absent');
 need(plan.helper?.path.endsWith('/.claude/skills/qa-handoff/scripts/bounded-check.mjs')&&/^[a-f0-9]{64}$/.test(plan.helper.sha256),'Existing owned helper absent');
 need(Array.isArray(plan.trees)&&plan.trees.length>=4&&Array.isArray(plan.inputs)&&plan.inputs.length>=7,'Complete source/runtime/helper input closure absent');
 need(plan.payload&&privatePath(plan.payload.root)&&!within(plan.payload.root,plan.fixture_root),'Immutable candidate payload absent');
 const allowed=['SystemRoot','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'];
 need(plan.environment&&equal(Object.keys(plan.environment).sort(),allowed.sort())&&Object.values(plan.environment).every(v=>typeof v==='string'),'Exact private environment required');
 need(plan.environment.SystemRoot==='C:/Windows'&&plan.environment.WINDIR==='C:/Windows'&&plan.environment.PATH==='C:/Program Files/nodejs;C:/Windows/System32','Fixed Windows/Node environment required');
 for(const key of ['TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])need(within(privatePath(plan.environment[key]),plan.fixture_root),'Profile/cache/TEMP escapes private fixture');
 need(within(privatePath(plan.authority.path),plan.evidence_root),'Authority must be an exact private input');
 need(plan.expected_tray_types?.ExecutablePath===1&&Object.values(plan.expected_tray_types).every(t=>[1,2,3,4,11].includes(t)),'Reviewed exact own-leaf value schema required');
 return plan;
}
export async function ordinary(p,{file=false,allowHardlinks=false}={}){
 privatePath(p);const st=await fs.lstat(p,{bigint:true});need(!st.isSymbolicLink()&&(file?st.isFile():st.isDirectory()),'Nonordinary path: '+p);if(file&&!allowHardlinks)need(st.nlink===1n,'Hard-linked input/output refused: '+p);
 for(const key of ['size','nlink'])need(st[key]>=0n&&st[key]<=BigInt(Number.MAX_SAFE_INTEGER),'Unsafe numeric file metadata: '+key);
 for(let at=path.win32.dirname(p);;at=path.win32.dirname(at)){const s=await fs.lstat(at,{bigint:true});need(s.isDirectory()&&!s.isSymbolicLink(),'Nonordinary ancestor');if(at===path.win32.dirname(at))break;}
 return {dev:st.dev.toString(),ino:st.ino.toString(),size:Number(st.size),nlink:Number(st.nlink)};
}
export async function readPin(ref){const st=await ordinary(ref.path,{file:true,allowHardlinks:!!ref.identity});if(ref.identity)need(String(st.dev)===ref.identity.dev&&String(st.ino)===ref.identity.ino&&st.nlink===ref.identity.nlink,'Pinned input native identity differs');need(st.size===ref.size&&st.size<=1024*1024*1024,'Input size differs');const bytes=await fs.readFile(ref.path);need(hash(bytes)===ref.sha256,'Input bytes differ: '+ref.path);return bytes;}
export async function treeFiles(root){
 await ordinary(root);const out={};async function walk(dir,prefix){for(const ent of await fs.readdir(dir,{withFileTypes:true})){const rel=prefix+ent.name,p=path.join(dir,ent.name);need(!ent.isSymbolicLink(),'Link in private tree');if(ent.isDirectory())await walk(p,rel+'/');else{const st=await ordinary(p,{file:true});out[rel]={size:st.size,sha256:hash(await fs.readFile(p))};}}}await walk(root,'');return Object.fromEntries(Object.entries(out).sort(([a],[b])=>a<b?-1:a>b?1:0));
}
// One observed failed attempt only. Its forced result remains a failure; only
// the independently proved final native zero permits reusing its private files.
export async function verifyRecovery(plan){
 if(!plan.recovery)return null;const r=plan.recovery;
 const previous=JSON.parse(await readPin(r.original_plan));need(!previous.recovery,'Chained failed-attempt recovery is forbidden');
 validatePlan(previous,JSON.parse(await readPin(previous.authority)));
 need(previous.binding.version===plan.binding.version&&norm(previous.fixture_root)===norm(plan.fixture_root),'Recovery must keep the same release and exact EXE path');
 const st=await ordinary(plan.fixture_root);need(st.dev===r.fixture_identity.dev&&st.ino===r.fixture_identity.ino&&st.nlink===r.fixture_identity.nlink,'Original private fixture identity differs');
 const exe=await ordinary(path.join(plan.fixture_root,'app','Books Arranger.exe'),{file:true});need(sameFileTree(exe,r.exe_identity),'Original private executable identity differs');
 const callback=JSON.parse(await readPin(r.original_callback)),owned=JSON.parse(await readPin(r.original_controller_owned));
 need(callback.callback_received===true&&callback.error?.code===1&&callback.error.killed===false&&callback.plan_sha256===r.original_plan.sha256&&callback.controller_owned_sha256===r.original_controller_owned.sha256,'Original failed callback provenance differs');
 need(owned.ok===false&&owned.closed===true&&owned.forced===true&&owned.timedOut===true&&owned.outputComplete===false&&owned.closureError===null&&owned.reason==='Total deadline reserved for owned cleanup','Original forced failure required; never a normal-owned substitute');
 need(owned.native?.complete===true&&owned.native.zero===true&&Number.isSafeInteger(owned.native.retained)&&owned.native.retained>0&&['active','assigned','listed','unsignaled'].every(k=>owned.native[k]===0),'Original failed attempt did not prove all owned processes closed');
 const artifactRaw=await readPin(r.original_artifact_manifest);let artifact=JSON.parse(artifactRaw),baseManifestSha=r.original_artifact_manifest.sha256;
 need(hash(artifactRaw)===previous.binding.artifact_manifest_sha256&&artifact.source_head===previous.binding.source_head&&artifact.build_id===previous.binding.build_id&&artifact.product_digest===previous.binding.product_digest&&artifact.payload?.verified===true&&artifact.payload.installer_equivalent===true,'Original verified payload provenance differs');
 if(r.attempt>=3){
  const second=r.second_failed_attempt;
  need(second&&Object.keys(second).sort().join('|')===['callback','cache_refresh','controller_owned','owned','payload_manifest','plan','quit_owned'].sort().join('|'),'Exact second failed-attempt evidence required');
  const p=JSON.parse(await readPin(second.plan)),a=JSON.parse(await readPin(p.authority));validatePlan(p,a);
  need(p.recovery?.attempt===2&&p.recovery.original_plan.sha256===r.original_plan.sha256&&p.recovery.original_baseline.sha256===r.original_baseline.sha256&&norm(p.fixture_root)===norm(plan.fixture_root)&&p.binding.version===plan.binding.version,'Only the recorded second attempt on this exact original fixture may precede attempt three');
  const cb=JSON.parse(await readPin(second.callback));need(cb.callback_received===true&&cb.error?.code===1&&cb.error.killed===false&&cb.plan_sha256===second.plan.sha256&&cb.owned_sha256===second.owned.sha256&&cb.controller_owned_sha256===second.controller_owned.sha256,'Second failed callback provenance differs');
  for(const ref of [second.owned,second.controller_owned]){const v=JSON.parse(await readPin(ref));need(v.ok===false&&v.code===1&&v.signal===null&&v.error===null&&v.closed===true&&v.outputComplete===true&&v.forced===false&&v.timedOut===false&&v.reason===null&&v.closureError===null&&v.ownership==='private-job'&&v.native?.complete===true&&v.native.zero===true&&v.native.retained>0&&['active','assigned','listed','unsignaled'].every(k=>v.native[k]===0),'Second attempt must remain a failed test with fully proved normal closure');}
  normalOwned(JSON.parse(await readPin(second.quit_owned)));
  const raw=await readPin(second.payload_manifest),base=JSON.parse(raw),refresh=JSON.parse(await readPin(second.cache_refresh));
  need(hash(raw)===p.binding.artifact_manifest_sha256&&base.source_head===p.binding.source_head&&base.build_id===p.binding.build_id&&base.product_digest===p.binding.product_digest&&base.payload?.verified===true&&base.payload.installer_equivalent===true,'Second attempt verified payload provenance differs');
  need(refresh.whole_payload_matches_current===true&&refresh.original_manifest_sha256===r.original_artifact_manifest.sha256&&refresh.current_manifest_sha256===second.payload_manifest.sha256&&sameFileTree(refresh.exe_identity,r.exe_identity)&&sameFileTree(refresh.changes,p.recovery.cache_refresh),'Second attempt cache refresh provenance differs');
  await readPin(r.engine_record);artifact=base;baseManifestSha=second.payload_manifest.sha256;
 }
 if(r.attempt>=4){
  const third=r.third_failed_attempt;
  need(third&&Object.keys(third).sort().join('|')===['plan','callback','owned','controller_owned','payload_manifest','cache_refresh'].sort().join('|'),'Exact third failed-attempt evidence required');
  const p=JSON.parse(await readPin(third.plan));validatePlan(p,JSON.parse(await readPin(p.authority)));
  need(p.recovery?.attempt===3&&p.recovery.original_plan.sha256===r.original_plan.sha256&&p.recovery.original_baseline.sha256===r.original_baseline.sha256&&p.recovery.second_failed_attempt.plan.sha256===r.second_failed_attempt.plan.sha256&&norm(p.fixture_root)===norm(plan.fixture_root)&&p.binding.version===plan.binding.version&&r.engine_record_absent===true,'Only the recorded third attempt and its cleanly removed control record may precede attempt four');
  const cb=JSON.parse(await readPin(third.callback));need(cb.callback_received===true&&cb.error?.code===1&&cb.error.killed===false&&cb.plan_sha256===third.plan.sha256&&cb.owned_sha256===third.owned.sha256&&cb.controller_owned_sha256===third.controller_owned.sha256,'Third failed callback provenance differs');
  for(const ref of [third.owned,third.controller_owned]){const v=JSON.parse(await readPin(ref));need(v.ok===false&&v.code===1&&v.signal===null&&v.error===null&&v.closed===true&&v.outputComplete===true&&v.forced===false&&v.timedOut===false&&v.reason===null&&v.closureError===null&&v.ownership==='private-job'&&v.native?.complete===true&&v.native.zero===true&&v.native.retained>0&&['active','assigned','listed','unsignaled'].every(k=>v.native[k]===0),'Third attempt must remain a failed test with fully proved normal closure');}
  const raw=await readPin(third.payload_manifest),base=JSON.parse(raw),refresh=JSON.parse(await readPin(third.cache_refresh));
  need(hash(raw)===p.binding.artifact_manifest_sha256&&base.source_head===p.binding.source_head&&base.build_id===p.binding.build_id&&base.product_digest===p.binding.product_digest&&base.payload?.verified===true&&base.payload.installer_equivalent===true,'Third attempt verified payload provenance differs');
  need(refresh.whole_payload_matches_current===true&&refresh.original_manifest_sha256===r.original_artifact_manifest.sha256&&refresh.base_manifest_sha256===r.second_failed_attempt.payload_manifest.sha256&&refresh.current_manifest_sha256===third.payload_manifest.sha256&&sameFileTree(refresh.exe_identity,r.exe_identity)&&sameFileTree(refresh.changes,p.recovery.cache_refresh),'Third attempt cache refresh provenance differs');
  artifact=base;baseManifestSha=third.payload_manifest.sha256;
 }
 if(r.attempt===5){
  const fourth=r.fourth_failed_attempt;
  need(fourth&&Object.keys(fourth).sort().join('|')===['plan','callback','owned','controller_owned','payload_manifest','cache_refresh'].sort().join('|'),'Exact fourth failed-attempt evidence required');
  const p=JSON.parse(await readPin(fourth.plan));validatePlan(p,JSON.parse(await readPin(p.authority)));
  need(p.recovery?.attempt===4&&p.recovery.original_plan.sha256===r.original_plan.sha256&&p.recovery.original_baseline.sha256===r.original_baseline.sha256&&p.recovery.second_failed_attempt.plan.sha256===r.second_failed_attempt.plan.sha256&&p.recovery.third_failed_attempt.plan.sha256===r.third_failed_attempt.plan.sha256&&norm(p.fixture_root)===norm(plan.fixture_root)&&p.binding.version===plan.binding.version&&r.engine_record_absent===true,'Only the recorded fourth attempt and its cleanly removed control record may precede attempt five');
  const cb=JSON.parse(await readPin(fourth.callback));need(cb.callback_received===true&&cb.error?.code===1&&cb.error.killed===false&&cb.plan_sha256===fourth.plan.sha256&&cb.owned_sha256===fourth.owned.sha256&&cb.controller_owned_sha256===fourth.controller_owned.sha256,'Fourth failed callback provenance differs');
  for(const ref of [fourth.owned,fourth.controller_owned]){const v=JSON.parse(await readPin(ref));need(v.ok===false&&v.code===1&&v.signal===null&&v.error===null&&v.closed===true&&v.outputComplete===true&&v.forced===false&&v.timedOut===false&&v.reason===null&&v.closureError===null&&v.ownership==='private-job'&&v.native?.complete===true&&v.native.zero===true&&v.native.retained>0&&['active','assigned','listed','unsignaled'].every(k=>v.native[k]===0),'Fourth attempt must remain a failed test with fully proved normal closure');}
  const raw=await readPin(fourth.payload_manifest),base=JSON.parse(raw),refresh=JSON.parse(await readPin(fourth.cache_refresh));
  need(hash(raw)===p.binding.artifact_manifest_sha256&&base.source_head===p.binding.source_head&&base.build_id===p.binding.build_id&&base.product_digest===p.binding.product_digest&&base.payload?.verified===true&&base.payload.installer_equivalent===true,'Fourth attempt verified payload provenance differs');
  need(refresh.whole_payload_matches_current===true&&refresh.original_manifest_sha256===r.original_artifact_manifest.sha256&&refresh.base_manifest_sha256===r.third_failed_attempt.payload_manifest.sha256&&refresh.current_manifest_sha256===fourth.payload_manifest.sha256&&sameFileTree(refresh.exe_identity,r.exe_identity)&&sameFileTree(refresh.changes,p.recovery.cache_refresh),'Fourth attempt cache refresh provenance differs');
  artifact=base;baseManifestSha=fourth.payload_manifest.sha256;
 }
 return {previous,artifact,baseManifestSha,baseline:JSON.parse(await readPin(r.original_baseline))};
}
export async function privateEnginePort(plan,probe){
 if(![3,4,5].includes(plan.recovery?.attempt))return probe(0);
 const r=plan.recovery,raw=await readPin(r.engine_record),record=JSON.parse(raw),port=r.engine_port;
 need(Number.isInteger(port)&&port>=1024&&port<=65535&&record.application==='Books Arranger'&&record.version===plan.binding.version&&record.port===port&&record.url==='http://127.0.0.1:'+port+'/'&&Number.isInteger(record.pid)&&record.pid>0&&/^[a-f0-9]{32}$/.test(record.instance),'Exact original private engine port record required');
 const live=path.join(plan.fixture_root,'home','data','web-instance.json');
 if(r.attempt>=4){await ordinary(path.dirname(live));try{await fs.lstat(live);throw Error('Private ownership record unexpectedly exists before retry');}catch(error){if(error.code!=='ENOENT')throw error;}}
 else await readPin({path:live,sha256:r.engine_record.sha256,size:r.engine_record.size,identity:r.engine_record_identity});
 need(await probe(port)===port,'Original private engine port is unavailable; no fallback is permitted');return port;
}
export function recoveryCacheChanges(plan,previous,current){
 const names=Object.keys(previous).sort();need(equal(names,Object.keys(current).sort()),'Recovery payload members differ');
 const changed=names.filter(name=>!sameFileTree(previous[name],current[name]));
 need(changed.length===0||changed.length===93,'Recovery cache change count differs');
 const facts=changed.map(name=>{
  const match=/^resources\/backend\/__pycache__\/([A-Za-z_][A-Za-z0-9_]*)\.cpython-314\.pyc$/.exec(name);
  need(match,'Recovery may refresh only the observed generated Python caches');
  const source='resources/backend/'+match[1]+'.py';
  need(previous[source]&&sameFileTree(previous[source],current[source])&&previous[name].size===current[name].size,'Corresponding Python source or cache size differs');
  return {path:name,old_sha256:previous[name].sha256,new_sha256:current[name].sha256,size:current[name].size,source_path:source,source_sha256:current[source].sha256};
 });
 need(sameFileTree(facts,plan.recovery.cache_refresh),'Exact manifest-pinned recovery cache facts differ');return facts;
}
export async function verifyInputs(plan){
 const mandatory=[plan.node,plan.helper,{path:path.join(plan.source_root,'scripts/qa-phase-contract.mjs'),sha256:plan.binding.phase_contract_sha256},{path:path.join(path.dirname(plan.helper.path),'bounded-child.mjs')},...['kernel32.dll','advapi32.dll','ntdll.dll','user32.dll','iphlpapi.dll'].map(name=>({path:'C:/Windows/System32/'+name}))];
 for(const expected of mandatory){const ref=plan.inputs.find(r=>norm(r.path)===norm(expected.path));need(ref&&(!expected.sha256||ref.sha256===expected.sha256),'Required executable/helper/system pin absent: '+expected.path);}
 for(const rel of ['scripts/qa-real-shell-phase.mjs','tests/real-shell-update.test.mjs','tests/real-shell-update-support.mjs'])need(plan.inputs.some(r=>norm(r.path)===norm(path.join(plan.source_root,rel))),'Fixed native source pin absent');
 for(const required of [plan.source_root,path.dirname(plan.node.path),plan.koffi_root])need(plan.trees.some(t=>norm(t.root)===norm(required)),'Complete source/Node/Koffi tree absent');
 for(const ref of plan.inputs)await readPin(ref);
 for(const tree of plan.trees)need(sameFileTree(await treeFiles(tree.root),tree.files),'Input tree changed: '+tree.root);
 const raw=await readPin(plan.payload.manifest);need(hash(raw)===plan.binding.artifact_manifest_sha256,'Candidate artifact binding differs');const m=JSON.parse(raw);
 need(m.version===plan.binding.version&&m.source_head===plan.binding.source_head&&m.product_digest===plan.binding.product_digest&&m.build_id===plan.binding.build_id,'Candidate identity differs');
 need(hash(JSON.stringify(m.runtime))===plan.binding.runtime_manifest_sha256&&m.payload?.verified===true&&m.payload.installer_equivalent===true,'Candidate payload/runtime proof absent');
 need(sameFileTree(await treeFiles(plan.payload.root),m.payload.files),'Built payload differs');
 if(plan.recovery){const prior=await verifyRecovery(plan);recoveryCacheChanges(plan,prior.artifact.payload.files,m.payload.files);}
 return m;
}
export async function freshFixture(plan,manifest){
 if(plan.recovery){
  const prior=await verifyRecovery(plan),app=path.join(plan.fixture_root,'app');
  need(sameFileTree(await treeFiles(app),prior.artifact.payload.files),'Original private payload differs before recovery');
  const changes=recoveryCacheChanges(plan,prior.artifact.payload.files,manifest.payload.files),exe=path.join(app,'Books Arranger.exe'),identity=await ordinary(exe,{file:true});
  for(const change of changes){
   const target=path.join(app,change.path),st=await ordinary(target,{file:true});
   await readPin({path:target,sha256:change.old_sha256,size:change.size,identity:st});
   const bytes=await readPin({path:path.join(plan.payload.root,change.path),sha256:change.new_sha256,size:change.size});
   const handle=await fs.open(target,'r+');try{
    const held=await handle.stat({bigint:true});need(held.isFile()&&String(held.dev)===st.dev&&String(held.ino)===st.ino&&held.nlink===1n&&Number(held.size)===change.size,'Private cache changed before its retained-handle write');
    await handle.writeFile(bytes);await handle.sync();
   }finally{await handle.close();}
   await readPin({path:target,sha256:change.new_sha256,size:change.size,identity:st});
  }
  need(sameFileTree(await ordinary(exe,{file:true}),identity),'Private executable identity changed');
  need(sameFileTree(await treeFiles(app),manifest.payload.files),'Refreshed private payload differs from verified candidate');
  await fs.writeFile(path.join(plan.evidence_root,'recovery-cache-refresh.private.json'),JSON.stringify({original_manifest_sha256:plan.recovery.original_artifact_manifest.sha256,base_manifest_sha256:prior.baseManifestSha,current_manifest_sha256:plan.binding.artifact_manifest_sha256,exe_identity:identity,changes,whole_payload_matches_current:true}),{flag:'wx'});
  return app;
 }
 try{await fs.lstat(plan.fixture_root);throw Error('Fixture already exists; no adoption or deletion');}catch(e){if(e.code!=='ENOENT')throw e;}
 await ordinary(path.dirname(plan.fixture_root));await fs.mkdir(plan.fixture_root);
 const app=path.join(plan.fixture_root,'app');await fs.mkdir(app);
 for(const [rel,ref] of Object.entries(manifest.payload.files)){need(!path.isAbsolute(rel)&&!rel.includes('..')&&!rel.includes('\\')&&!rel.includes(':'),'Unsafe payload member');const src=path.join(plan.payload.root,rel),dst=path.join(app,rel);need(within(dst,app),'Payload escape');const bytes=await readPin({path:src,...ref});await fs.mkdir(path.dirname(dst),{recursive:true});await fs.writeFile(dst,bytes,{flag:'wx'});}
 need(sameFileTree(await treeFiles(app),manifest.payload.files),'Derived payload copy differs');return app;
}

// Only the two documented commands for this already-bound private shell/profile.
export function createPrivateShellCommands({spawn,exe,profile,installationConfig=null,env,timeoutMs=60000}){
 privatePath(exe);privatePath(profile);
 if(installationConfig)privatePath(installationConfig);
 need(Number.isSafeInteger(timeoutMs)&&timeoutMs>0&&timeoutMs<=60000,'Bounded private shell command timeout required');
 const command=flag=>new Promise((resolve,reject)=>{
  const selection=installationConfig?'--installation-config='+installationConfig:'--shell-profile='+profile;
  const child=spawn(exe,[flag,selection,'--start-hidden','--quiet-errors'],{env,windowsHide:true,stdio:'ignore'});
  const timer=setTimeout(()=>reject(Error('Private shell command timed out: '+flag)),timeoutMs);
  child.once('error',error=>{clearTimeout(timer);reject(error);});child.once('exit',(code,signal)=>{clearTimeout(timer);code===0&&signal===null?resolve():reject(Error('Private shell command failed: '+flag));});
 });
 return Object.freeze({closeWindow:()=>command('--close-window'),quit:()=>command('--quit')});
}
export function verifyCloseSession({running,loaded,quit,health,expectedPid,version,windows}){
 need(running===true&&loaded===true&&quit==='none','Close window did not preserve the primary session');
 need(Number.isSafeInteger(expectedPid)&&expectedPid>0&&health?.pid===expectedPid&&health.version===version,'Close window did not preserve the same healthy engine');
 need(windows?.intrusion===null&&Number.isSafeInteger(windows.hiddenOwnWindows)&&windows.hiddenOwnWindows>0,'Primary owned window is not proved hidden after close');
 return {endpointsOwned:true,healthVersionMatched:true,noVisibleOwnWindow:true};
}

// Pure comparison. Foreign raw state stays in the private arena only.
export function ownLeafDelta(before,current,exe,expectedTypes=null){
 need(before&&current&&equal(before.rootSchema,current.rootSchema),'Tray root schema drift');
 const prior=Object.keys(before.leaves),added=Object.keys(current.leaves).filter(k=>!prior.includes(k));need(added.length===1&&/^\d+$/.test(added[0]),'Expected one new numeric own leaf');
 for(const id of prior)need(equal(before.leaves[id],current.leaves[id]),'Preexisting tray leaf drift');
 const id=added[0],leaf=current.leaves[id];need(leaf.subkeys===0&&leaf.values?.ExecutablePath?.type===1,'Own leaf type/subkeys differ');
 if(expectedTypes)need(equal(Object.fromEntries(Object.entries(leaf.values).map(([name,value])=>[name,value.type]).sort(([a],[b])=>a<b?-1:a>b?1:0)),Object.fromEntries(Object.entries(expectedTypes).sort(([a],[b])=>a<b?-1:a>b?1:0))),'New own leaf value schema differs');
 const text=Buffer.from(leaf.values.ExecutablePath.hex,'hex').toString('utf16le').replace(/\0+$/,'');need(norm(text)===norm(exe),'Exact executable identity differs');
 const old=Buffer.from(before.order,'hex'),now=Buffer.from(current.order,'hex');need(old.length%8===0&&now.length===old.length+8,'Unexpected UIOrderList shape');
 let hits=0;const foreign=[];for(let i=0;i<now.length;i+=8){const part=now.subarray(i,i+8);if(part.readBigUInt64LE()===BigInt(id))hits++;else foreign.push(part);}need(hits===1&&Buffer.concat(foreign).equals(old),'Unexpected own history reference or foreign list drift');
 return {id,leaf,order:current.order,orderSha256:hash(now)};
}
export async function cleanupOwnLeaf({plan,authority,owned,before,adapter,deadline}){
 validatePlan(plan,authority);normalOwned(owned);need(Date.now()<deadline,'Cleanup deadline expired');
 let handle=null,deleted=false,closed=false;const result={schema:'books-own-tray-cleanup-v1',binding:plan.binding,authority_sha256:plan.authority.sha256,owned_sha256:hash(JSON.stringify(owned)),fixture_root:plan.fixture_root,exe:path.join(plan.fixture_root,'app','Books Arranger.exe'),uiOrderListWritten:false,partial:false,error:null};
 try{
  const current=await adapter.snapshot(),own=ownLeafDelta(before,current,result.exe,plan.expected_tray_types);result.ownId=own.id;
  handle=await adapter.openExact(own.id);need(equal(await adapter.readHandle(handle),own.leaf),'Same-handle leaf changed');
  need(equal(await adapter.snapshot(),current),'Registry drift before exact deletion');need(Date.now()<deadline,'Cleanup deadline expired');
  await adapter.deleteHandle(handle);deleted=true;const closing=handle;handle=null;await adapter.close(closing);closed=true;
  const after=await adapter.snapshot();need(!Object.hasOwn(after.leaves,own.id),'Own leaf still exists');need(equal(after.leaves,before.leaves)&&equal(after.rootSchema,before.rootSchema)&&after.order===own.order,'Registry changed during deletion; no rollback');
  Object.assign(result,{exactNewLeaf:true,sameHandle:true,deleted,closed,absenceVerified:true,preexistingUnchanged:true,ownReferenceCount:1,ownReferenceBytes:8,uiOrderListSha256:own.orderSha256});return result;
 }catch(e){if(handle!==null){const closing=handle;handle=null;try{await adapter.close(closing);closed=true;}catch(closeError){e.message+='; retained handle close failed: '+closeError.message;}}result.partial=deleted;result.deleted=deleted;result.closed=closed;result.error=e.message;e.cleanup=result;throw e;}
}

// No adapter is constructed on import. The exact admitted controller supplies a
// validated plan/authority only after complete input verification.
export function requiredWindowPid(query,window){
 const pid=[0],thread=query(window,pid);
 need(Number.isSafeInteger(thread)&&thread>0&&thread<=0xffffffff&&Number.isSafeInteger(pid[0])&&pid[0]>0&&pid[0]<=0xffffffff,'Window PID lookup failed or returned an unknown identity');
 return pid[0];
}
// The SDK LISTENER-only query identifies the role. Private loopback probes on
// Windows also returned raw state 6 on listener rows with both remote fields
// zero. Keep the raw state as a diagnostic and reject other contradictions.
// https://learn.microsoft.com/en-us/windows/win32/api/iprtrmib/ne-iprtrmib-tcp_table_class
export function listenerOnlyRows(buffer,tableClass,family,port){
 need(tableClass===3&&family===2,'Exact SDK IPv4 owner-PID listener-only query required');
 need(Buffer.isBuffer(buffer)&&buffer.length>=4&&buffer.length<=16*1024*1024&&Number.isInteger(port)&&port>=1024&&port<=65535,'Bounded listener table and exact port required');
 const count=buffer.readUInt32LE(0);need(4+count*24<=buffer.length,'TCP listener table truncated');const rows=[];
 for(let n=0;n<count;n++){
  const at=4+n*24;if(buffer.readUInt16BE(at+8)!==port)continue;
  const state=buffer.readUInt32LE(at),pid=buffer.readUInt32LE(at+20);
  need(buffer.subarray(at+4,at+8).equals(Buffer.from([127,0,0,1])),'Private endpoint is not loopback-only');
  need(pid>0,'TCP listener owner PID is unknown');
  const hasRemoteEndpoint=buffer.readUInt32LE(at+12)!==0||buffer.readUInt32LE(at+16)!==0;
  need(state===0||state===2||(state===6&&!hasRemoteEndpoint),
   `Listener-only membership contradicts raw non-listener state ${state} for port ${port}, PID ${pid}, remote endpoint ${hasRemoteEndpoint?'present':'absent'}`);
  rows.push({pid,state,listenerTableClass:3});
 }
 need(rows.length<=1,'Ambiguous private listener ownership');return rows;
}

// A query-only containment witness. Node/libuv may replace its immediate job;
// this explicit no-breakaway handle remains stable. The existing outer owner
// remains the sole kill-on-close controller. Closing this handle never kills.
export function membershipWitness(api,pid){
 need(Number.isSafeInteger(pid)&&pid>0,'Invalid witness worker');const handle=api.create();need(handle,'Cannot create membership witness');let closed=false;
 const members=()=>{need(!closed,'Membership witness closed');const b=api.query(handle);need(Buffer.isBuffer(b)&&b.length===8+8192*8,'Witness membership query failed');const assigned=b.readUInt32LE(0),listed=b.readUInt32LE(4);need(assigned===listed&&listed>0&&listed<=8192,'Incomplete witness membership');const pids=[];for(let n=0;n<listed;n++){const member=Number(b.readBigUInt64LE(8+n*8));need(Number.isSafeInteger(member)&&member>0&&member<=0xffffffff&&!pids.includes(member),'Witness member identity');pids.push(member);}need(pids.includes(pid),'Worker left explicit membership witness');return pids;};
 try{need(api.configure(handle,0),'Cannot set query-only no-breakaway limits');need(api.assignSelf(handle),'Cannot assign observer membership witness');need(api.flags(handle)===0,'Witness must have no breakaway or kill-on-close limits');members();}catch(error){closed=true;need(api.close(handle),'Failed witness handle closure');throw error;}
 return {members,contains(processHandle){need(!closed,'Membership witness closed');return api.belongs(processHandle,handle)===true;},close(){if(!closed){closed=true;need(api.close(handle),'Membership witness handle closure failed');}}};
}
export function nativeAdapters(plan,authority){
 validatePlan(plan,authority);need(process.platform==='win32'&&process.arch==='x64','Native PA-1 requires reviewed Windows x64 ABI');
 const require=createRequire(import.meta.url),k=require(plan.koffi_root),K=k.load('C:/Windows/System32/kernel32.dll'),A=k.load('C:/Windows/System32/advapi32.dll'),N=k.load('C:/Windows/System32/ntdll.dll'),U=k.load('C:/Windows/System32/user32.dll'),I=k.load('C:/Windows/System32/iphlpapi.dll');
 const open=A.func('int32_t __stdcall RegOpenKeyExW(intptr_t,str16,uint32_t,uint32_t,_Out_ void **)'),close=A.func('int32_t __stdcall RegCloseKey(void *)');
 const info=A.func('int32_t __stdcall RegQueryInfoKeyW(void *,void *,void *,void *,_Out_ uint32_t *,void *,void *,_Out_ uint32_t *,void *,void *,void *,void *)');
 const enumValue=A.func('int32_t __stdcall RegEnumValueW(void *,uint32_t,void *,_Inout_ uint32_t *,void *,_Out_ uint32_t *,void *,_Inout_ uint32_t *)');
 const enumKey=A.func('int32_t __stdcall RegEnumKeyExW(void *,uint32_t,void *,_Inout_ uint32_t *,void *,void *,void *,void *)');
 const del=N.func('int32_t __stdcall NtDeleteKey(void *)'),ROOT='Control Panel\\NotifyIconSettings',HKCU=-2147483647n;
 const ok=(rc,label)=>need(rc===0,label+' status '+rc);
 function regOpen(name,access){const h=[null];ok(open(HKCU,name,0,access,h),'Exact registry open');need(h[0],'Null registry handle');return h[0];}
 function readHandle(h){
  const sub=[0],count=[0];ok(info(h,null,null,null,sub,null,null,count,null,null,null,null),'Registry info');need(sub[0]<=4096&&count[0]<=4096,'Registry bounds');const values={};
  for(let n=0;n<count[0];n++){const name=Buffer.alloc(65536),len=[32768],type=[0],data=Buffer.alloc(1024*1024),size=[data.length];ok(enumValue(h,n,name,len,null,type,data,size),'Complete registry value read');const key=name.subarray(0,len[0]*2).toString('utf16le');need(!Object.hasOwn(values,key),'Duplicate registry value');values[key]={type:type[0],hex:data.subarray(0,size[0]).toString('hex')};}
  const endName=Buffer.alloc(4),endLength=[2],endType=[0],endSize=[0];need(enumValue(h,count[0],endName,endLength,null,endType,null,endSize)===259,'Registry value enumeration changed');
  return {subkeys:sub[0],values:Object.fromEntries(Object.entries(values).sort(([a],[b])=>a.localeCompare(b,'en')))};
 }
 function snapshot(){
  let total=0;function readTree(name,depth=0){need(depth<=16&&++total<=8192,'Registry tree bound');const h=regOpen(name,0x20019);try{const value=readHandle(h),children={};for(let n=0;n<value.subkeys;n++){const b=Buffer.alloc(65536),len=[32768];ok(enumKey(h,n,b,len,null,null,null,null),'Complete registry key read');const child=b.subarray(0,len[0]*2).toString('utf16le');need(child&&!child.includes('\\')&&!Object.hasOwn(children,child),'Registry child name');children[child]=readTree(name+'\\'+child,depth+1);}const end=Buffer.alloc(4),len=[2];need(enumKey(h,value.subkeys,end,len,null,null,null,null)===259,'Registry key enumeration changed');return {...value,...(value.subkeys?{children:Object.fromEntries(Object.entries(children).sort(([a],[b])=>a.localeCompare(b,'en')))}:{})};}finally{ok(close(h),'Registry read handle close');}}
  const root=readTree(ROOT),order=root.values.UIOrderList;need(order?.type===3,'Binary UIOrderList required');const rootSchema={...root.values};delete rootSchema.UIOrderList;return {rootSchema,order:order.hex,leaves:root.children||{}};
 }
 const registry={snapshot,openExact:id=>{need(/^\d+$/.test(id),'Exact numeric key required');return regOpen(ROOT+'\\'+id,0x30019);},readHandle,deleteHandle:h=>ok(del(h),'Delete same retained own key'),close:h=>ok(close(h),'Close same retained own key')};
 const queryJob=K.func('bool __stdcall QueryInformationJobObject(void *,uint32_t,void *,uint32_t,void *)'),openProcess=K.func('void * __stdcall OpenProcess(uint32_t,bool,uint32_t)'),closeProcess=K.func('bool __stdcall CloseHandle(void *)'),wait=K.func('uint32_t __stdcall WaitForSingleObject(void *,uint32_t)'),image=K.func('bool __stdcall QueryFullProcessImageNameW(void *,uint32_t,void *,_Inout_ uint32_t *)');
 const processTimes=K.func('bool __stdcall GetProcessTimes(void *,void *,void *,void *,void *)');
 const held=new Map();let intrusion=null,checks=0,listenerQueries=0;const listenerStates=new Set(),app=path.join(plan.fixture_root,'app');
 const createWitness=K.func('void * __stdcall CreateJobObjectW(void *,void *)'),setWitness=K.func('bool __stdcall SetInformationJobObject(void *,int,void *,uint32_t)'),assignWitness=K.func('bool __stdcall AssignProcessToJobObject(void *,void *)'),currentProcess=K.func('void * __stdcall GetCurrentProcess()'),belongsWitness=K.func('bool __stdcall IsProcessInJob(void *,void *,void *)');
 let witness=null;
 function members(){if(!witness)witness=membershipWitness({create:()=>createWitness(null,null),configure:(h,flags)=>{const b=Buffer.alloc(144);b.writeUInt32LE(flags,16);return setWitness(h,9,b,b.length);},assignSelf:h=>assignWitness(h,currentProcess()),flags:h=>{const b=Buffer.alloc(144);need(queryJob(h,9,b,b.length,null),'Witness limit query failed');return b.readUInt32LE(16);},query:h=>{const b=Buffer.alloc(8+8192*8);need(queryJob(h,3,b,b.length,null),'Explicit private witness membership unknown');return b;},belongs:(p,h)=>{const b=Buffer.alloc(4);need(belongsWitness(p,h,b),'Exact witness membership query failed');return b.readUInt32LE(0)===1;},close:closeProcess},process.pid);return witness.members();}
 function retain(pid){need(members().includes(pid),'Endpoint is not in this private owned job');let item=held.get(pid);if(item){need(wait(item.handle,0)===258&&witness.contains(item.handle),'Retained endpoint process ended or left witness');return item;}
  const h=openProcess(0x101000,false,pid);need(h,'Cannot retain owned endpoint process');try{need(wait(h,0)===258&&witness.contains(h),'Owned process already ended or outside explicit witness');const b=Buffer.alloc(65536),len=[32768],created=Buffer.alloc(8),exit=Buffer.alloc(8),kernel=Buffer.alloc(8),user=Buffer.alloc(8);need(image(h,0,b,len)&&processTimes(h,created,exit,kernel,user),'Owned endpoint identity unknown');const exe=b.subarray(0,len[0]*2).toString('utf16le');need(within(exe,app),'Endpoint executable outside private payload');item={handle:h,pid,exe,created:created.toString('hex')};held.set(pid,item);return item;}catch(e){closeProcess(h);throw e;}}
 const tcp=I.func('uint32_t __stdcall GetExtendedTcpTable(void *,_Inout_ uint32_t *,bool,uint32_t,uint32_t,uint32_t)');
 function listeners(port){const size=[0];need(tcp(null,size,false,2,3,0)===122&&size[0]<=16*1024*1024,'TCP table size unknown');const b=Buffer.alloc(size[0]);need(tcp(b,size,false,2,3,0)===0,'TCP ownership query failed');const rows=listenerOnlyRows(b,3,2,port);listenerQueries++;for(const row of rows)listenerStates.add(row.state);return rows;}
 function endpoint(port,expectedPid=null){const rows=listeners(port);need(rows.length===1&&rows[0].listenerTableClass===3,'One private SDK listener-only row required');if(expectedPid!==null)need(rows[0].pid===expectedPid,'Listener PID differs');const p=retain(rows[0].pid);need(listeners(port).length===1&&listeners(port)[0].pid===p.pid&&wait(p.handle,0)===258,'Listener changed during ownership proof');return {pid:p.pid,exe:p.exe,created:p.created,reportedState:rows[0].state,listenerTableClass:3};}
 const visible=U.func('bool __stdcall IsWindowVisible(void *)'),foreground=U.func('void * __stdcall GetForegroundWindow()'),windowPid=U.func('uint32_t __stdcall GetWindowThreadProcessId(void *,_Out_ uint32_t *)'),enumerate=U.func('bool __stdcall EnumWindows(void *,intptr_t)'),proto=k.proto('bool __stdcall BooksPA1Window(void *,intptr_t)');
 function checkWindows(expectedPid=null){checks++;const own=new Set(members());if(expectedPid!==null){need(Number.isSafeInteger(expectedPid)&&expectedPid>0&&own.has(expectedPid),'Primary window owner is not in this private job');retain(expectedPid);}let failed='',hiddenOwnWindows=0;const cb=k.register(hwnd=>{try{const pid=requiredWindowPid(windowPid,hwnd);if(own.has(pid)){const shown=visible(hwnd);if(shown)intrusion='Owned process displayed a visible window';else if(pid===expectedPid)hiddenOwnWindows++;}return true;}catch(e){failed=e.message;return false;}},k.pointer(proto));try{need(enumerate(cb,0)&&!failed,'Window observation failed');}finally{k.unregister(cb);}const fg=foreground();if(fg){const pid=requiredWindowPid(windowPid,fg);if(own.has(pid))intrusion='Owned process took foreground';}need(!intrusion,intrusion);if(expectedPid!==null){retain(expectedPid);need(hiddenOwnWindows>0,'Primary owned window is not present and hidden');}return {checks,intrusion,hiddenOwnWindows};}
 function dispose(){try{for(const p of held.values())need(closeProcess(p.handle),'Owned endpoint handle close failed');held.clear();}finally{witness?.close();}}
 return {registry,monitor:{endpoint,checkWindows,dispose,view:()=>({checks,intrusion,listenerTableClass:3,listenerQueries,reportedListenerStates:[...listenerStates].sort((a,b)=>a-b)}),members}};
}

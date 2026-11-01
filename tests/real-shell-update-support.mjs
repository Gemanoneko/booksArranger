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
export function privatePath(p){need(typeof p==='string'&&/^C:[\\/]/i.test(p)&&!p.includes('\0'),'Private local C: path required');need(!/[. ]([\\/]|$)/.test(p)&&!p.slice(2).includes(':'),'Noncanonical private path');return p;}
export function validatePlan(plan,authority){
 need(plan?.schema==='books-real-shell-plan-v1','Fixed real-shell plan absent');binding(plan.binding);validateAuthority(authority,plan.binding);
 need(equal(plan.case,NATIVE_CASE)&&plan.deadlineMs===600000&&plan.phase_contract_sha256===plan.binding.phase_contract_sha256,'Fixed phase/deadline differs');
 for(const key of ['fixture_root','evidence_root','source_root','koffi_root'])privatePath(plan[key]);
 need(path.win32.basename(plan.fixture_root)==='pa1-'+plan.binding.build_id&&within(plan.fixture_root,plan.evidence_root),'Fresh candidate fixture root differs');
 need(!within(plan.source_root,plan.fixture_root)&&!within(plan.evidence_root,plan.source_root),'Source/output overlap');
 need(plan.authority?.sha256===hash(JSON.stringify(authority)),'Canonical authority bytes differ from plan');
 need(plan.node?.path==='C:/Program Files/nodejs/node.exe'&&/^[a-f0-9]{64}$/.test(plan.node.sha256),'Fixed installed Node absent');
 need(plan.helper?.path.endsWith('/.claude/skills/qa-handoff/scripts/bounded-check.mjs')&&/^[a-f0-9]{64}$/.test(plan.helper.sha256),'Existing owned helper absent');
 need(Array.isArray(plan.trees)&&plan.trees.length>=4&&Array.isArray(plan.inputs)&&plan.inputs.length>=7,'Complete source/runtime/helper input closure absent');
 need(plan.payload&&privatePath(plan.payload.root)&&!within(plan.payload.root,plan.fixture_root),'Immutable candidate payload absent');
 const allowed=['SystemRoot','WINDIR','PATH','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'];
 need(plan.environment&&equal(Object.keys(plan.environment).sort(),allowed.sort())&&Object.values(plan.environment).every(v=>typeof v==='string'),'Exact private environment required');
 need(plan.environment.SystemRoot==='C:/Windows'&&plan.environment.WINDIR==='C:/Windows'&&plan.environment.PATH==='C:/Program Files/nodejs;C:/Windows/System32','Fixed Windows/Node environment required');
 for(const key of ['TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])need(within(plan.environment[key],plan.fixture_root),'Profile/cache/TEMP escapes private fixture');
 need(within(plan.authority.path,plan.evidence_root),'Authority must be an exact private input');
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
 need(sameFileTree(await treeFiles(plan.payload.root),m.payload.files),'Built payload differs');return m;
}
export async function freshFixture(plan,manifest){
 try{await fs.lstat(plan.fixture_root);throw Error('Fixture already exists; no adoption or deletion');}catch(e){if(e.code!=='ENOENT')throw e;}
 await ordinary(path.dirname(plan.fixture_root));await fs.mkdir(plan.fixture_root);
 const app=path.join(plan.fixture_root,'app');await fs.mkdir(app);
 for(const [rel,ref] of Object.entries(manifest.payload.files)){need(!path.isAbsolute(rel)&&!rel.includes('..')&&!rel.includes('\\')&&!rel.includes(':'),'Unsafe payload member');const src=path.join(plan.payload.root,rel),dst=path.join(app,rel);need(within(dst,app),'Payload escape');const bytes=await readPin({path:src,...ref});await fs.mkdir(path.dirname(dst),{recursive:true});await fs.writeFile(dst,bytes,{flag:'wx'});}
 need(sameFileTree(await treeFiles(app),manifest.payload.files),'Derived payload copy differs');return app;
}

// Only the two documented commands for this already-bound private shell/profile.
export function createPrivateShellCommands({spawn,exe,profile,env}){
 privatePath(exe);privatePath(profile);
 const command=flag=>new Promise((resolve,reject)=>{
  const child=spawn(exe,[flag,'--shell-profile='+profile,'--start-hidden','--quiet-errors'],{env,windowsHide:true,stdio:'ignore'});
  child.once('error',reject);child.once('exit',(code,signal)=>code===0&&signal===null?resolve():reject(Error('Private shell command failed: '+flag)));
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
 const held=new Map();let intrusion=null,checks=0;const app=path.join(plan.fixture_root,'app');
 function members(){const b=Buffer.alloc(8+8192*8);need(queryJob(null,3,b,b.length,null),'Current private job membership unknown');const assigned=b.readUInt32LE(),listed=b.readUInt32LE(4);need(assigned===listed&&listed>0&&listed<=8192,'Incomplete current job membership');const pids=[];for(let n=0;n<listed;n++){const pid=Number(b.readBigUInt64LE(8+n*8));need(Number.isSafeInteger(pid)&&pid>0&&!pids.includes(pid),'Job member identity');pids.push(pid);}need(pids.includes(process.pid),'Current worker not in owned job');return pids;}
 function retain(pid){need(members().includes(pid),'Endpoint is not in this private owned job');let item=held.get(pid);if(item){need(wait(item.handle,0)===258,'Retained endpoint process ended');return item;}
  const h=openProcess(0x101000,false,pid);need(h,'Cannot retain owned endpoint process');try{need(wait(h,0)===258,'Owned process already ended');const b=Buffer.alloc(65536),len=[32768],created=Buffer.alloc(8),exit=Buffer.alloc(8),kernel=Buffer.alloc(8),user=Buffer.alloc(8);need(image(h,0,b,len)&&processTimes(h,created,exit,kernel,user),'Owned endpoint identity unknown');const exe=b.subarray(0,len[0]*2).toString('utf16le');need(within(exe,app),'Endpoint executable outside private payload');item={handle:h,pid,exe,created:created.toString('hex')};held.set(pid,item);return item;}catch(e){closeProcess(h);throw e;}}
 const tcp=I.func('uint32_t __stdcall GetExtendedTcpTable(void *,_Inout_ uint32_t *,bool,uint32_t,uint32_t,uint32_t)');
 function listeners(port){const size=[0];need(tcp(null,size,false,2,3,0)===122&&size[0]<=16*1024*1024,'TCP table size unknown');const b=Buffer.alloc(size[0]);need(tcp(b,size,false,2,3,0)===0,'TCP ownership query failed');const count=b.readUInt32LE();need(4+count*24<=b.length,'TCP table truncated');const rows=[];for(let n=0;n<count;n++){const at=4+n*24,localPort=b.readUInt16BE(at+8);if(localPort===port){const address=b.subarray(at+4,at+8);need(address.equals(Buffer.from([127,0,0,1])),'Private endpoint is not loopback-only');rows.push({pid:b.readUInt32LE(at+20),state:b.readUInt32LE(at)});}}return rows;}
 function endpoint(port,expectedPid=null){const rows=listeners(port);need(rows.length===1&&rows[0].state===2,'One private loopback listener required');if(expectedPid!==null)need(rows[0].pid===expectedPid,'Listener PID differs');const p=retain(rows[0].pid);need(listeners(port).length===1&&listeners(port)[0].pid===p.pid&&wait(p.handle,0)===258,'Listener changed during ownership proof');return {pid:p.pid,exe:p.exe,created:p.created};}
 const visible=U.func('bool __stdcall IsWindowVisible(void *)'),foreground=U.func('void * __stdcall GetForegroundWindow()'),windowPid=U.func('uint32_t __stdcall GetWindowThreadProcessId(void *,_Out_ uint32_t *)'),enumerate=U.func('bool __stdcall EnumWindows(void *,intptr_t)'),proto=k.proto('bool __stdcall BooksPA1Window(void *,intptr_t)');
 function checkWindows(expectedPid=null){checks++;const own=new Set(members());if(expectedPid!==null){need(Number.isSafeInteger(expectedPid)&&expectedPid>0&&own.has(expectedPid),'Primary window owner is not in this private job');retain(expectedPid);}let failed='',hiddenOwnWindows=0;const cb=k.register(hwnd=>{try{const pid=requiredWindowPid(windowPid,hwnd);if(own.has(pid)){const shown=visible(hwnd);if(shown)intrusion='Owned process displayed a visible window';else if(pid===expectedPid)hiddenOwnWindows++;}return true;}catch(e){failed=e.message;return false;}},k.pointer(proto));try{need(enumerate(cb,0)&&!failed,'Window observation failed');}finally{k.unregister(cb);}const fg=foreground();if(fg){const pid=requiredWindowPid(windowPid,fg);if(own.has(pid))intrusion='Owned process took foreground';}need(!intrusion,intrusion);if(expectedPid!==null){retain(expectedPid);need(hiddenOwnWindows>0,'Primary owned window is not present and hidden');}return {checks,intrusion,hiddenOwnWindows};}
 function dispose(){for(const p of held.values())need(closeProcess(p.handle),'Owned endpoint handle close failed');held.clear();}
 return {registry,monitor:{endpoint,checkWindows,dispose,view:()=>({checks,intrusion}),members}};
}

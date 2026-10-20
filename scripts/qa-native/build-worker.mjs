/** Fixed engineering compiler worker SOURCE; runs only inside reviewed runOwned private Job.
 * No generic operation/command. New-source compilation remains disabled in observer.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {runOwned} from 'file:///C:/Antigravity%20Projects/Studio%20Illuminati/.claude/skills/qa-handoff/scripts/bounded-check.mjs';
import {createEngineeringOwner,newOwnerId,validateOwnedResult} from './engineering-owner.mjs';
import {validateBuildPlan,compilerInvocation} from './build-watchdog.mjs';
const SOURCE='C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/scripts/qa-native';
const KOFFI='C:/Antigravity Projects/Studio Illuminati/WIP/QuickLaunch/node_modules/koffi';
const requireThat=(v,m)=>{if(!v)throw Error(m);};const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const normalized=p=>path.win32.resolve(p).toLowerCase();
export function requireSameDirectoryBirth(actual,expected){
 const shape=f=>f&&typeof f.volume64==='string'&&/^[0-9]+$/.test(f.volume64)&&typeof f.file_id128==='string'&&/^[0-9a-f]{32}$/.test(f.file_id128)&&typeof f.creation_ticks==='string'&&/^[1-9][0-9]*$/.test(f.creation_ticks)&&Number.isInteger(f.attrs)&&Boolean(f.attrs&0x10)&&!(f.attrs&0x400);
 requireThat(shape(actual)&&shape(expected)&&JSON.stringify(actual)===JSON.stringify(expected),'Original creation-owned directory replaced or proof malformed');
}
export class Leases {
 constructor(deadline){
  this.deadline=deadline;this.handles=[];this.parents=new Map();this.written=new Map();
  this.koffi=createRequire(import.meta.url)(KOFFI);const k=this.koffi.load('kernel32.dll');
  this.open=k.func('void* __stdcall CreateFileW(str16,uint32_t,uint32_t,void*,uint32_t,uint32_t,void*)');
  this.close=k.func('bool __stdcall CloseHandle(void*)');
  this.info=k.func('bool __stdcall GetFileInformationByHandle(void*,void*)');
  this.idInfo=k.func('bool __stdcall GetFileInformationByHandleEx(void*,int,void*,uint32_t)');
  this.write=k.func('bool __stdcall WriteFile(void*,void*,uint32_t,void*,void*)');this.flush=k.func('bool __stdcall FlushFileBuffers(void*)');
  this.final=k.func('uint32_t __stdcall GetFinalPathNameByHandleW(void*,void*,uint32_t,uint32_t)');
  this.seek=k.func('bool __stdcall SetFilePointerEx(void*,int64_t,void*,uint32_t)');
  this.read=k.func('bool __stdcall ReadFile(void*,void*,uint32_t,void*,void*)');
  this.firstStream=k.func('void* __stdcall FindFirstStreamW(str16,int,void*,uint32_t)');
  this.nextStream=k.func('bool __stdcall FindNextStreamW(void*,void*)');
  this.findClose=k.func('bool __stdcall FindClose(void*)');this.lastError=k.func('uint32_t __stdcall GetLastError()');
  this.ntcreate=this.koffi.load('ntdll.dll').func('int32_t __stdcall NtCreateFile(void*,uint32_t,void*,void*,void*,uint32_t,uint32_t,uint32_t,uint32_t,void*,uint32_t)');
  this.getCurrent=k.func('void* __stdcall GetCurrentProcess()');this.times=k.func('bool __stdcall GetProcessTimes(void*,void*,void*,void*,void*)');
 }
 check(){requireThat(Date.now()<this.deadline-2000,'Sealing/compiler budget reserved for closure');}
 valid(h){return h!==null&&this.koffi.address(h)!==0xffffffffffffffffn;}
 facts(h){this.check();const b=Buffer.alloc(52),id=Buffer.alloc(24);requireThat(this.info(h,b)&&this.idInfo(h,18,id,id.length),'Native input/full128 facts failed');return {volume64:String(id.readBigUInt64LE(0)),file_id128:id.toString('hex',8,24),creation_ticks:String(b.readBigUInt64LE(4)),attrs:b.readUInt32LE(0),volume:b.readUInt32LE(28),size:b.readUInt32LE(32)*4294967296+b.readUInt32LE(36),links:b.readUInt32LE(40),index:String((BigInt(b.readUInt32LE(44))<<32n)|BigInt(b.readUInt32LE(48))),mtime_ticks:String(b.readBigUInt64LE(20))};}
 retain(p,directory=false){this.check();requireThat(p.length<=259,'Ordinary path bound');const h=this.open(p,directory?0x81:0x80000080,1,null,3,0x00200000|(directory?0x02000000:0),null);requireThat(this.valid(h),'Native readonly input lease failed: '+p);this.handles.push(h);const f=this.facts(h);requireThat(!(f.attrs&0x400)&&Boolean(f.attrs&0x10)===directory,'Reparse/wrong-kind input');if(!directory)requireThat(f.links===1,'Input hardlink floor');const out=Buffer.alloc(65536);const n=this.final(h,out,32768,0);requireThat(n>4&&n<32768,'Unknown final path');requireThat(normalized(out.toString('utf16le',0,n*2).slice(4))===normalized(p),'Input native alias');return h;}
 ancestry(p){for(let d=path.win32.dirname(p);;d=path.win32.dirname(d)){const key=normalized(d);if(!this.parents.has(key))this.parents.set(key,this.retain(d,true));if(path.win32.dirname(d)===d)break;}}
 streams(p){const b=Buffer.alloc(600);const h=this.firstStream(p,0,b,0);requireThat(this.valid(h),'Stream enumeration failed');const names=[];try{do{names.push(b.toString('utf16le',8).split('\0')[0]);}while(this.nextStream(h,b));requireThat(this.lastError()===38,'Stream enumeration incomplete');}finally{requireThat(this.findClose(h),'Stream enumerator close failed');}requireThat(names.length===1&&names[0]==='::$DATA','Nondefault streams refused');}
 bytes(h,size){requireThat(Number.isSafeInteger(size)&&size>=0&&size<=1073741824,'Input size bound');requireThat(this.seek(h,0,null,0),'Input rewind');const chunks=[];let total=0;for(;;){this.check();const block=Buffer.alloc(1048576),count=Buffer.alloc(4);requireThat(this.read(h,block,block.length,count,null),'Held input read');const n=count.readUInt32LE(0);if(!n)break;total+=n;requireThat(total<=size,'Input grew');chunks.push(block.subarray(0,n));}requireThat(total===size,'Input short read');return Buffer.concat(chunks,total);}
 freeze(item){this.ancestry(item.path);const h=this.retain(item.path),facts=this.facts(h);this.streams(item.path);requireThat(facts.size===item.size,'Held input size mismatch');if(item.dev!==undefined)requireThat(String(facts.volume)===item.dev&&facts.index===item.ino&&String((BigInt(facts.mtime_ticks)-116444736000000000n)*100n)===item.mtimeNs,'Pinned native input identity/mtime drift');const bytes=this.bytes(h,item.size);requireThat(hash(bytes)===item.sha256,'Held input hash mismatch: '+item.path);return {handle:h,facts,bytes};}
 createDirectory(parent,name){this.check();requireThat(/^[a-zA-Z0-9.-]+$/.test(name),'Unsafe new directory');const parentHandle=this.parents.get(normalized(parent));requireThat(parentHandle,'Held parent required');const nameBytes=Buffer.from(name+'\0','utf16le'),unicode=Buffer.alloc(16),attrs=Buffer.alloc(48),status=Buffer.alloc(16),out=Buffer.alloc(8);unicode.writeUInt16LE(nameBytes.length-2,0);unicode.writeUInt16LE(nameBytes.length,2);unicode.writeBigUInt64LE(this.koffi.address(nameBytes),8);attrs.writeUInt32LE(48,0);attrs.writeBigUInt64LE(this.koffi.address(parentHandle),8);attrs.writeBigUInt64LE(this.koffi.address(unicode),16);attrs.writeUInt32LE(0x40,24);requireThat(this.ntcreate(out,0x100081,attrs,status,null,0x80,1,2,0x00200021,null,0)===0,'Exclusive directory birth refused');const h=this.koffi.decode(out,'void *');requireThat(this.valid(h)&&status.readBigUInt64LE(8)===2n,'Not creation-owned directory');this.handles.push(h);requireThat(Boolean(this.facts(h).attrs&0x10),'Wrong created kind');const p=path.win32.join(parent,name);this.parents.set(normalized(p),h);return {path:p,facts:this.facts(h)};}

 directoryIdentity(h){const f=this.facts(h);return {volume64:f.volume64,file_id128:f.file_id128,creation_ticks:f.creation_ticks,attrs:f.attrs};}
 directoryProof(){return [...this.parents].map(([path,h])=>({path,facts:this.directoryIdentity(h)})).sort((a,b)=>a.path.localeCompare(b.path));}
 rejoinDirectories(proof){requireThat(Array.isArray(proof)&&proof.length>0&&proof.length<=256,'Bounded native directory proof');for(const item of [...proof].sort((a,b)=>a.path.length-b.path.length)){this.ancestry(item.path);const h=this.retain(item.path,true);requireSameDirectoryBirth(this.directoryIdentity(h),item.facts);this.parents.set(normalized(item.path),h);}}
 writeBytesNew(p,bytes){this.check();this.ancestry(p);const h=this.open(p,0xC0000080,1,null,1,0x00200000,null);requireThat(this.valid(h),'Native CREATE_NEW output refused');this.handles.push(h);const born=this.facts(h);requireThat(!(born.attrs&0x410)&&born.links===1,'Created output floor');let total=0;while(total<bytes.length){this.check();const block=bytes.subarray(total,Math.min(total+65536,bytes.length)),count=Buffer.alloc(4);requireThat(this.write(h,block,block.length,count,null)&&count.readUInt32LE(0)===block.length,'Native exact output write');total+=block.length;}requireThat(this.flush(h),'Native output flush');this.streams(p);requireThat(hash(this.bytes(h,bytes.length))===hash(bytes),'Same-held output readback');const proof={path:p,size:bytes.length,sha256:hash(bytes),facts:this.facts(h)};this.written.set(normalized(p),{handle:h,proof});return proof;}
 writeRecord(p,value){const bytes=Buffer.from(JSON.stringify(value,null,2));requireThat(bytes.length<1048576,'Record byte quota');return this.writeBytesNew(p,bytes);}
 readRecordBytes(proof){const own=this.written.get(normalized(proof?.path??''));if(own){requireThat(JSON.stringify(own.proof)===JSON.stringify(proof)&&JSON.stringify(this.facts(own.handle))===JSON.stringify(proof.facts),'Own record proof changed');const bytes=this.bytes(own.handle,proof.size);requireThat(hash(bytes)===proof.sha256,'Same-held record changed');return bytes;}requireThat(proof&&Number.isSafeInteger(proof.size)&&proof.size>=0&&proof.size<=1073741824&&/^[a-f0-9]{64}$/.test(proof.sha256),'Bounded file proof');const frozen=this.freeze({path:proof.path,size:proof.size,sha256:proof.sha256});requireThat(JSON.stringify(frozen.facts)===JSON.stringify(proof.facts),'Original file native identity changed');return frozen.bytes;}
 readRecord(proof){requireThat(proof&&proof.size<1048576&&/^[a-f0-9]{64}$/.test(proof.sha256),'Bounded record proof');const frozen=this.freeze({path:proof.path,size:proof.size,sha256:proof.sha256});requireThat(JSON.stringify(frozen.facts)===JSON.stringify(proof.facts),'Original record native identity changed');return JSON.parse(frozen.bytes);}
 processIdentity(){const made=Buffer.alloc(8),exit=Buffer.alloc(8),kernel=Buffer.alloc(8),user=Buffer.alloc(8);requireThat(this.times(this.getCurrent(),made,exit,kernel,user),'Worker native creation identity');return {pid:process.pid,creation_filetime:String(made.readBigUInt64LE(0)),image:process.execPath};}
 teardown(){let bad=false;for(const h of this.handles.reverse())if(!this.close(h))bad=true;this.handles=[];requireThat(!bad,'Native input/directory lease close failed');}
}
export function remainingCompilerBudget(deadline,now=Date.now()){const left=deadline-now-6000;requireThat(Number.isInteger(left)&&left>2000&&left<=594000,'No remaining owned compiler/closure budget');return left;}
async function main(argv){
 requireThat(argv.length===8&&argv[6]==='--outer-owner'&&/^[a-f0-9-]{36}$/.test(argv[7])&&argv[0]==='--plan'&&argv[2]==='--plan-sha'&&argv[4]==='--deadline','Fixed worker arguments');const expected=argv[3];requireThat(/^[a-f0-9]{64}$/.test(expected),'Plan pin');const deadline=Number(argv[5]);requireThat(Number.isSafeInteger(deadline)&&deadline>Date.now()&&deadline<=Date.now()+600000,'Fixed total remaining deadline');
 const io=new Leases(deadline);let exitCode=1,compilerUncertain=false;try{
  const startupStat=fs.lstatSync(argv[1]);requireThat(startupStat.isFile()&&!startupStat.isSymbolicLink()&&startupStat.size<1048576,'Plan shape');const planRaw=io.freeze({path:argv[1],size:startupStat.size,sha256:expected}).bytes;const plan=JSON.parse(planRaw);const p=validateBuildPlan(plan);
  const all=[];for(const item of plan.sources){requireThat(normalized(path.win32.dirname(item.path))===normalized(SOURCE),'Unknown source member');all.push(io.freeze(item));}
  requireThat(plan.sources.some(x=>x.path===SOURCE+'/books-qa-watchdog.cpp'&&x.sha256===plan.source_sha256)&&plan.sources.some(x=>x.path===SOURCE+'/build-worker.mjs')&&plan.sources.some(x=>x.path===SOURCE+'/build-watchdog.mjs'&&x.sha256===plan.recipe_sha256),'Incomplete source closure');
  const manifest=JSON.parse(io.freeze({path:plan.toolchain_manifest,size:plan.toolchain_manifest_size,sha256:plan.toolchain_manifest_sha256}).bytes);requireThat(manifest.schema==='books-engineering-installed-toolchain-v1'&&manifest.files.length===3636&&manifest.total_bytes===1010638147,'Unknown fixed installed toolchain');
  for(const item of manifest.files)io.freeze(item);
  // Enumerate complete fixed file set after holding every member and ancestor; reject added files/empty directories via exact directory manifest.
  const actual=[],actualDirs=[];function enumerate(dir){io.check();actualDirs.push(normalized(dir));for(const e of fs.readdirSync(dir,{withFileTypes:true})){const f=dir+'/'+e.name;requireThat(!e.isSymbolicLink(),'Toolchain reparse');if(e.isDirectory())enumerate(f);else actual.push(normalized(f));}}for(const d of manifest.roots)enumerate(d);requireThat(JSON.stringify(actual.sort())===JSON.stringify(manifest.files.map(x=>normalized(x.path)).sort()),'Toolchain member closure drift');requireThat(JSON.stringify(actualDirs.sort())===JSON.stringify(manifest.directories.map(normalized).sort()),'Toolchain directory closure drift');
  io.ancestry(p.arena);const rootBirth=io.createDirectory(path.win32.dirname(p.arena),path.win32.basename(p.arena));for(const name of ['source','out','tmp','cache','evidence'])io.createDirectory(p.arena,name);for(const name of ['roaming','local','profile'])io.createDirectory(p.cache,name);
  const source=all[plan.sources.findIndex(x=>x.path===SOURCE+'/books-qa-watchdog.cpp')].bytes;
  const sourceCopy=io.writeBytesNew(p.source,source);requireThat(sourceCopy.sha256===plan.source_sha256,'Sealed source copy mismatch');
  const binding={outer_owner_id:argv[7],invocation_id:plan.invocation_id,plan_sha256:expected,source_sha256:plan.source_sha256,recipe_sha256:plan.recipe_sha256,toolchain_manifest_sha256:plan.toolchain_manifest_sha256,worker:io.processIdentity()};
  const startup=io.writeRecord(p.evidence+'/startup.json',{schema:'books-native-engineering-startup-v2',authoritative:false,...binding,arena_birth:rootBirth,directories:io.directoryProof(),deadline_epoch_ms:deadline});
  const command=compilerInvocation(plan);io.check();
  // Controller is outside this separate inner Job, so it can retain leases while the compiler tree closes.
  const remaining=remainingCompilerBudget(deadline);
  const innerId=newOwnerId(),inner=createEngineeringOwner(KOFFI,{ownerId:innerId});compilerUncertain=true;
  const result=await runOwned(command.file,command.args,{cwd:command.cwd,env:command.env,timeoutMs:remaining,koffiRoot:KOFFI,maxBytes:1048576,jobFactory:()=>inner});
  // Even a compiler failure may not release leases until exact inner closure. No root-close substitution.
  const innerEvidence=inner.evidence();requireThat(result.closed===true&&result.native?.zero===true&&innerEvidence?.closed===true,'Inner compiler closure uncertain: outer owner must terminate controller');compilerUncertain=false;
  const innerIdentity=validateOwnedResult(result,innerEvidence,innerId);
  const allowedImages=new Set(manifest.files.filter(x=>/\.exe$/i.test(x.path)).map(x=>normalized(x.path)));allowedImages.add(normalized('C:/Program Files/nodejs/node.exe'));
  for(const member of innerIdentity.observed)requireThat(allowedImages.has(normalized(member.image_path_at_admission)),'Inner compiler image outside pinned toolchain');
  io.check();const built=[];for(const name of ['books-qa-watchdog.exe','books-qa-watchdog.obj']){const file=p.out+'/'+name;const s=fs.lstatSync(file);requireThat(s.isFile()&&!s.isSymbolicLink()&&s.nlink===1,'Compiler output floor');const h=io.retain(file);io.streams(file);built.push({path:file,size:s.size,sha256:hash(io.bytes(h,s.size)),facts:io.facts(h)});}
  const work=io.writeRecord(p.evidence+'/worker-result.json',{schema:'books-native-engineering-work-v2',authoritative:false,...binding,startup,inner_owner_id:innerId,inner_result:result,inner_evidence:innerEvidence,outputs:built,directories:io.directoryProof()});
  io.check();console.log(JSON.stringify({schema:'books-native-engineering-wire-v2',...binding,startup,work,directories:io.directoryProof()}));exitCode=0;
 }finally{if(compilerUncertain){/* Keep every lease and controller alive until ORIGINAL bounded outer owner terminates this uncertain tree. */setInterval(()=>{},1000);await new Promise(()=>{});}io.teardown();}return exitCode;
}
// Fixed module is imported by no other operation. It runs only as the assigned worker.
if(typeof process!=='undefined'&&process.argv[1]&&normalized(process.argv[1])===normalized(fileURLToPath(import.meta.url)))main(process.argv.slice(2)).then(code=>{process.exitCode=code;}).catch(error=>{console.error('Engineering worker REFUSED: '+error.message);process.exitCode=2;});

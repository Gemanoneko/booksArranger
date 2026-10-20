/** SOURCE ONLY until exact invocation review. stdout facts; no durable output/OS writes. */
import {types} from 'node:util';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {acquireConsoleCompanion,fixedAsciiPath,SYSTEM_DIRECTORY} from './console-companion.mjs';
const KOFFI='C:/Antigravity Projects/Studio Illuminati/WIP/QuickLaunch/node_modules/koffi';
const need=(v,m)=>{if(!v)throw Error(m);};

export function decodeSystemDirectory(buffer,count){
 need(Buffer.isBuffer(buffer)&&buffer.length===2050,'Exact system directory buffer required');
 need(Number.isSafeInteger(count)&&count>0&&count<1025,'System directory query failed/overflow');
 need(buffer.readUInt16LE(count*2)===0,'System directory missing terminator');
 for(let i=0;i<count;i++){const u=buffer.readUInt16LE(i*2);need(u!==0,'System directory embedded null');if(u>=0xd800&&u<=0xdbff){need(i+1<count,'System directory incomplete UTF16');const low=buffer.readUInt16LE((++i)*2);need(low>=0xdc00&&low<=0xdfff,'System directory invalid UTF16');}else need(u<0xdc00||u>0xdfff,'System directory invalid UTF16');}
 return {value:buffer.toString('utf16le',0,count*2),observation:{schema:'books-system-directory-observation-v1',authoritative:false,returned_units:count,utf16le_hex:buffer.toString('hex',0,count*2),expected_policy_path:SYSTEM_DIRECTORY}};
}
export function encodeSystemDirectoryObservation(observation){
 need(observation&&typeof observation==='object'&&!types.isProxy(observation)&&Object.getPrototypeOf(observation)===Object.prototype,'Own directory checkpoint required');
 const d=Object.getOwnPropertyDescriptors(observation),keys=Reflect.ownKeys(d),expected=['schema','authoritative','returned_units','utf16le_hex','expected_policy_path'];
 need(keys.length===expected.length&&expected.every(k=>Object.hasOwn(d,k)&&'value' in d[k]),'Exact directory checkpoint data');
 const get=k=>d[k].value;need(get('schema')==='books-system-directory-observation-v1'&&get('authoritative')===false&&get('expected_policy_path')===SYSTEM_DIRECTORY&&Number.isSafeInteger(get('returned_units'))&&get('returned_units')>0&&get('returned_units')<1025&&typeof get('utf16le_hex')==='string'&&get('utf16le_hex').length===get('returned_units')*4&&/^[0-9a-f]+$/.test(get('utf16le_hex')),'Bounded lossless directory checkpoint');
 const line=JSON.stringify(observation)+String.fromCharCode(10);need(Buffer.byteLength(line)<=8192,'Directory checkpoint byte quota');return line;
}
/** Production path: exactly one original API call. No retry, normalization or alternate root. */
export function systemDirectoryOnce(call,checkpoint){
 const buffer=Buffer.alloc(2050),count=call(buffer,1025),decoded=decodeSystemDirectory(buffer,count);
 try{need(checkpoint(encodeSystemDirectoryObservation(decoded.observation))===true,'Directory diagnostic write failed');}
 catch{throw Error((fixedAsciiPath(decoded.value,SYSTEM_DIRECTORY)?'System directory diagnostic':'Unreviewed native system directory; diagnostic')+' capture_failed');}
 return decoded.value;
}

/** Loading this module never loads FFI. No API provides write/delete/process authority. */
export function createReadonlyConsoleApi({checkpoint=line=>{process.stderr.write(line);return true;}}={}){
 need(process.platform==='win32'&&process.arch==='x64','Reviewed Windows x64 required');
 const koffi=createRequire(import.meta.url)(KOFFI),k=koffi.load('kernel32.dll');
 const system=k.func('uint32_t __stdcall GetSystemDirectoryW(void*,uint32_t)');
 const open=k.func('void* __stdcall CreateFileW(str16,uint32_t,uint32_t,void*,uint32_t,uint32_t,void*)');
 const close=k.func('bool __stdcall CloseHandle(void*)');
 const info=k.func('bool __stdcall GetFileInformationByHandle(void*,void*)');
 const id=k.func('bool __stdcall GetFileInformationByHandleEx(void*,int,void*,uint32_t)');
 const final=k.func('uint32_t __stdcall GetFinalPathNameByHandleW(void*,void*,uint32_t,uint32_t)');
 const seek=k.func('bool __stdcall SetFilePointerEx(void*,int64_t,void*,uint32_t)');
 const read=k.func('bool __stdcall ReadFile(void*,void*,uint32_t,void*,void*)');
 const first=k.func('void* __stdcall FindFirstStreamW(str16,int,void*,uint32_t)');
 const next=k.func('bool __stdcall FindNextStreamW(void*,void*)');
 const findClose=k.func('bool __stdcall FindClose(void*)');
 const lastError=k.func('uint32_t __stdcall GetLastError()');
 const invalid=h=>h===null||koffi.address(h)===0n||koffi.address(h)===0xffffffffffffffffn;
 const held=new Map();
 const requireHeld=h=>need(held.has(h),'Unknown/closed native companion handle');
 return Object.freeze({
  systemDirectory(){return systemDirectoryOnce(system,checkpoint);},
  open(p,directory){const h=open(p,directory?0x81:0x80000080,1,null,3,0x00200000|(directory?0x02000000:0),null);need(!invalid(h),'Readonly OPEN_EXISTING companion lease failed');held.set(h,{directory});return h;},
  facts(h){requireHeld(h);const b=Buffer.alloc(52),f=Buffer.alloc(24);need(info(h,b)&&id(h,18,f,24),'Native full128 companion facts failed');return {volume64:String(f.readBigUInt64LE(0)),file_id128:f.toString('hex',8,24),creation_ticks:String(b.readBigUInt64LE(4)),attrs:b.readUInt32LE(0),size:b.readUInt32LE(32)*4294967296+b.readUInt32LE(36),links:b.readUInt32LE(40)};},
  finalPath(h){requireHeld(h);const b=Buffer.alloc(2050),n=final(h,b,1025,0);need(n>4&&n<1025,'Native final path failed/overflow');const p=b.toString('utf16le',0,n*2);need(p.startsWith('\\\\?\\'),'Expected native DOS final path');return p.slice(4);},
  streams(p){const b=Buffer.alloc(600),h=first(p,0,b,0);need(!invalid(h),'Companion stream query failed');const names=[];let failure;
   try{for(;;){need(names.length<2,'Companion stream count cap');names.push(b.toString('utf16le',8).split('\0')[0]);if(!next(h,b)){const e=lastError();need(e===38,'Companion stream query incomplete');break;}}}catch(e){failure=e;}
   const ok=findClose(h);if(!ok)throw new AggregateError(failure?[failure,Error('Stream close failed')]:[Error('Stream close failed')],'Companion stream checked-close failed');if(failure)throw failure;return names;},
  rewind(h){requireHeld(h);need(seek(h,0,null,0),'Companion rewind failed');},
  read(h,size){requireHeld(h);need(size===65536&&!held.get(h).directory,'Fixed readonly file chunk');const b=Buffer.alloc(size),count=Buffer.alloc(4);need(read(h,b,size,count,null),'Companion held read failed');const n=count.readUInt32LE(0);need(n<=size,'Invalid native read size');return b.subarray(0,n);},
  close(h){requireHeld(h);const ok=close(h);if(ok)held.delete(h);return Boolean(ok);}
 });
}
export function collectConsoleFacts(api,deadline,{now=Date.now}={}){
 const lease=acquireConsoleCompanion(api,{deadline,now});let failure,result;
 try{lease.revalidate();result=lease.proof();}catch(e){failure=e;}
 try{lease.close();}catch(e){if(failure)throw new AggregateError([failure,e],'Collector operation/close failed');throw e;}
 if(failure)throw failure;
 const finished=now();need(Number.isSafeInteger(finished)&&finished<deadline-2000,'Collector closure reserve expired');
 return {schema:'books-console-companion-collection-v1',facts:result,checked_close:true,limitations:'Installed Windows trusted; descriptive closed receipt only. Later fixture must reacquire expected facts and retain leases through original checked Job/EOF closure. No signer, process ancestry, loaded-code integrity or execution permission.'};
}
export function collectorMain(argv){
 need(argv.length===2&&argv[0]==='--deadline-unix-ms'&&/^[0-9]{13}$/.test(argv[1]),'Fixed collector argv only');
 const deadline=Number(argv[1]);need(deadline>Date.now()+2000&&deadline<=Date.now()+60000,'Collector60s maximum incl closure');
 const result=collectConsoleFacts(createReadonlyConsoleApi(),deadline),out=JSON.stringify(result);need(Buffer.byteLength(out)<16384,'Collector stdout cap');need(Date.now()<deadline,'Collector deadline exceeded');process.stdout.write(out+'\n');
}
if(typeof process!=='undefined'&&process.argv[1]&&fileURLToPath(import.meta.url)===process.argv[1]){try{collectorMain(process.argv.slice(2));}catch(e){process.stderr.write('Console companion collection refused: '+String(e.message).slice(0,1024)+'\n');process.exitCode=1;}}

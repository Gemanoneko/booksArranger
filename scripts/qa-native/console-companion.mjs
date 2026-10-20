/** Dedicated READONLY installed-OS companion. Not a generic hardlink/runtime waiver. */
import crypto from 'node:crypto';
import {types} from 'node:util';
export const POLICY='books-fixed-console-companion-v2';
export const SYSTEM_DIRECTORY='C:\\Windows\\System32';
export const COMPANION_PATH=SYSTEM_DIRECTORY+'\\conhost.exe';
export const ANCESTRY=['C:\\','C:\\Windows',SYSTEM_DIRECTORY];
export function fixedAsciiPath(actual,expected){
 if(typeof actual!=='string'||typeof expected!=='string'||![...ANCESTRY,COMPANION_PATH].includes(expected)||actual.length!==expected.length)return false;
 for(let i=0;i<expected.length;i++){const e=expected.charCodeAt(i),a=actual.charCodeAt(i);if(a===e)continue;if(e>=65&&e<=90&&a===e+32)continue;if(e>=97&&e<=122&&a===e-32)continue;return false;}return true;
}
function rawPaths(directory){return [directory.slice(0,3),directory.slice(0,10),directory];}
export const MAX_FILE_BYTES=16*1024*1024;
const need=(v,m)=>{if(!v)throw Error(m);};
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const object=v=>{need(v&&typeof v==='object'&&!types.isProxy(v),'Nonproxy own-data required');const proto=Object.getPrototypeOf(v);need(proto===Object.prototype||proto===null,'Plain own-data required');};
const shape=(v,keys)=>{object(v);const descriptors=Object.getOwnPropertyDescriptors(v),own=Reflect.ownKeys(descriptors);need(own.every(k=>typeof k==='string')&&own.length===keys.length&&keys.every(k=>Object.hasOwn(descriptors,k))&&own.every(k=>'value' in descriptors[k]),'Exact own-data proof shape required');};
const array=(v,length)=>{need(v&&typeof v==='object'&&!types.isProxy(v)&&Array.isArray(v)&&Object.getPrototypeOf(v)===Array.prototype,'Plain nonproxy array required');const d=Object.getOwnPropertyDescriptors(v),keys=Reflect.ownKeys(d);need(d.length?.value===length&&keys.length===length+1&&keys.every(k=>typeof k==='string'&&'value' in d[k])&&Array.from({length},(_,i)=>String(i)).every(k=>Object.hasOwn(d,k)),'Exact dense own-data array required');};
const uint=(v,max)=>Number.isSafeInteger(v)&&v>=0&&v<=max;
const positive64=v=>typeof v==='string'&&/^[1-9][0-9]{0,19}$/.test(v)&&BigInt(v)<=18446744073709551615n;
function facts(f,directory){
 shape(f,['volume64','file_id128','creation_ticks','attrs','size','links']);
 need(f&&positive64(f.volume64)&&typeof f.file_id128==='string'&&/^[0-9a-f]{32}$/.test(f.file_id128)&&!/^0+$/.test(f.file_id128)&&positive64(f.creation_ticks),'Full native identity required');
 need(uint(f.attrs,4294967295)&&!(f.attrs&0x400)&&Boolean(f.attrs&0x10)===directory,'Ordinary nonreparse kind required');
 need(uint(f.links,4294967295)&&f.links>0&&uint(f.size,Number.MAX_SAFE_INTEGER),'Native size/link facts required');
 if(!directory)need(f.size>0&&f.size<=MAX_FILE_BYTES,'Companion size cap');
 return {volume64:f.volume64,file_id128:f.file_id128,creation_ticks:f.creation_ticks,attrs:f.attrs,size:f.size,links:f.links};
}
export function validateCompanionProof(p){
 shape(p,['schema','system_directory','path','native_path','access','os_trust','file','streams','sha256','ancestry']);
 need(p&&p.schema===POLICY&&fixedAsciiPath(p.system_directory,SYSTEM_DIRECTORY)&&p.path===p.system_directory+'\\conhost.exe'&&fixedAsciiPath(p.native_path,COMPANION_PATH)&&p.access==='readonly-openexisting-share-read-noninheritable'&&p.os_trust==='installed-windows-assumed','Exact OS policy required');
 facts(p.file,false);array(p.streams,1);need(/^[0-9a-f]{64}$/.test(p.sha256)&&equal(p.streams,['::$DATA']),'Default stream/hash required');
 array(p.ancestry,ANCESTRY.length);
 for(let i=0;i<ANCESTRY.length;i++){shape(p.ancestry[i],['path','native_path','facts']);need(p.ancestry[i].path===rawPaths(p.system_directory)[i]&&fixedAsciiPath(p.ancestry[i].native_path,ANCESTRY[i]),'Exact ancestry path required');facts(p.ancestry[i].facts,true);}
 need(p.file.volume64===p.ancestry[0].facts.volume64&&p.ancestry.every(x=>x.facts.volume64===p.file.volume64),'Same-volume ancestry required');
 return true;
}
/** api is a private read-only native backend; fake APIs provide developer evidence only. */
export function acquireConsoleCompanion(api,{deadline,expectedFacts,now=Date.now}={}){
 need(typeof now==='function','Trusted clock required');const start=now();need(Number.isSafeInteger(start)&&Number.isSafeInteger(deadline)&&deadline>start&&deadline<=start+600000,'Finite caller deadline required');
 const check=()=>{const at=now();need(Number.isSafeInteger(at)&&at>=start&&at<deadline-2000,'Companion deadline reserves closure');};
 const handles=[];let closed=false,proof,rawDirectory,paths,rawFile;
 const close=()=>{if(closed)throw Error('Companion lease already closed');closed=true;const errors=[];for(const h of handles.reverse()){try{need(api.close(h)===true,'Companion native close failed');}catch(e){errors.push(e.message);}}if(errors.length)throw Error(errors.join('; '));return true;};
 const inspect=(h,expected,d)=>{check();const native_path=api.finalPath(h);need(fixedAsciiPath(native_path,expected),'Native canonical path/alias mismatch');return {native_path,facts:facts(api.facts(h),d)};};
 const fileHash=h=>{const digest=crypto.createHash('sha256');let total=0;api.rewind(h);for(;;){check();const block=api.read(h,65536);need(Buffer.isBuffer(block)&&block.length<=65536,'Bounded native read');if(!block.length)break;total+=block.length;need(total<=proof.file.size&&total<=MAX_FILE_BYTES,'File grew or exceeded cap');digest.update(block);}need(total===proof.file.size,'Short native read');return digest.digest('hex');};
 const revalidate=()=>{need(!closed,'Companion lease expired');check();for(let i=0;i<ANCESTRY.length;i++){const observed=inspect(handles[i],ANCESTRY[i],true);need(equal(observed,{native_path:proof.ancestry[i].native_path,facts:proof.ancestry[i].facts}),'Companion ancestry drift');}const observed=inspect(handles[3],COMPANION_PATH,false);need(equal(observed,{native_path:proof.native_path,facts:proof.file}),'Companion native identity drift');need(equal(api.streams(rawFile),proof.streams),'Companion stream drift');need(fileHash(handles[3])===proof.sha256,'Companion content drift');check();return true;};
 try{
  check();rawDirectory=api.systemDirectory();need(fixedAsciiPath(rawDirectory,SYSTEM_DIRECTORY),'Unreviewed native system directory');paths=rawPaths(rawDirectory);rawFile=rawDirectory+'\\conhost.exe';
  const ancestry=[];for(let i=0;i<paths.length;i++){const p=paths[i];check();const h=api.open(p,true);need(h!==null&&h!==undefined,'Ancestor open failed');handles.push(h);ancestry.push({path:p,...inspect(h,ANCESTRY[i],true)});}
  const h=api.open(rawFile,false);need(h!==null&&h!==undefined,'Companion open failed');handles.push(h);
  const observed=inspect(h,COMPANION_PATH,false);proof={schema:POLICY,system_directory:rawDirectory,path:rawFile,native_path:observed.native_path,access:'readonly-openexisting-share-read-noninheritable',os_trust:'installed-windows-assumed',file:observed.facts,streams:api.streams(rawFile),sha256:'0'.repeat(64),ancestry};
  validateCompanionProof(proof);proof.sha256=fileHash(h);validateCompanionProof(proof);
  if(expectedFacts!==undefined){validateCompanionProof(expectedFacts);need(equal(proof,expectedFacts),'Reviewed companion facts changed');}
  revalidate();check();const immutable=JSON.parse(JSON.stringify(proof));
  return Object.freeze({proof:()=>{need(!closed,'Companion lease expired');return JSON.parse(JSON.stringify(immutable));},revalidate,
   acceptImage:(image,role)=>{need(expectedFacts!==undefined,'Discovery cannot authorize an admission image');need(!closed,'Companion lease expired');need(role==='member','Companion cannot be root/supervisor/controller/worker');need(image===proof.native_path,'Unproved admission image');revalidate();check();return true;},close});
 }catch(error){try{close();}catch(e){throw new AggregateError([error,e],'Companion operation and checked-close failed');}throw error;}
}

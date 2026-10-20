/** Protected fixed Books entry candidate. Not installed or executable until reviewed. */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
export const BASE='C:/Program Files/BooksArranger-QA-v2';
export const SOURCE='C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1';
export const RUN_PARENT='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/q';
export const STUDIO='C:/Antigravity Projects/Studio Illuminati';
export const NODE='C:/Program Files/nodejs/node.exe';
export const CORE=['run_entry_checks.mjs','entry-main.mjs','entry-identity.mjs','bounded-check.mjs','bounded-child.mjs'];
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const validHash=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x);
const same=(a,b)=>path.win32.resolve(a).toLowerCase()===path.win32.resolve(b).toLowerCase();
const abs=x=>typeof x==='string'&&/^C:[\\/]/i.test(x)&&x.length<=259&&!x.slice(2).includes(':')&&!x.split(/[\\/]/).some(p=>p==='.'||p==='..');
export function parseRegistry(raw){
 if(typeof raw!=='string'||Buffer.byteLength(raw)>16384||/[\r\0]/.test(raw))throw Error('Registry encoding/size');
 const lines=raw.split('\n');if(lines.pop()!=='')throw Error('Terminating registry newline required');if(lines.shift()!=='BOOKS_QA_REGISTRY_V1')throw Error('Registry version');
 const out={};for(const line of lines){const at=line.indexOf('=');if(at<1||at===line.length-1||Object.hasOwn(out,line.slice(0,at)))throw Error('Duplicate/empty registry value');out[line.slice(0,at)]=line.slice(at+1);}
 const keys=['state','node_sha256','bootstrap_sha256','operation','plan_path','plan_sha256','source_root','run_parent'];if(Object.keys(out).sort().join('|')!==keys.sort().join('|'))throw Error('Unknown registry keys');
 if(out.state!=='enabled'||out.operation!=='entry'||![out.node_sha256,out.bootstrap_sha256,out.plan_sha256].every(validHash)||!same(out.source_root,SOURCE)||!same(out.run_parent,RUN_PARENT)||!abs(out.plan_path)||!path.win32.resolve(out.plan_path).toLowerCase().startsWith(path.win32.resolve(RUN_PARENT,'../qa-entry-context').toLowerCase()+'\\'))throw Error('Disabled or wrong Books entry contract');
 return Object.freeze(out);
}
export function validateGuardian(plan){
 const fixedGuardian=SOURCE+'/scripts/qa-owned-guardian-v2.mjs';
 if(!plan||plan.schema!=='books-owned-guardian-v2'||plan.operation?.kind!=='entry'||!same(plan.guardian?.path??'',fixedGuardian)||!validHash(plan.guardian?.sha256)||!same(plan.node?.path??'',NODE)||!validHash(plan.node?.sha256)||!same(plan.koffiRoot??'',BASE+'/runtime/koffi')||Object.keys(plan.checker??{}).sort().join('|')!==[...CORE].sort().join('|')||!Object.values(plan.checker).every(validHash)||!Array.isArray(plan.trees)||!plan.trees.length||!Array.isArray(plan.files)||!plan.files.length)throw Error('Wrong fixed guardian contract');
 const context=plan.operation.context;if(!context||!validHash(context.sha256)||!abs(context.path)||!path.win32.resolve(context.path).toLowerCase().startsWith(path.win32.resolve(RUN_PARENT,'../qa-entry-context').toLowerCase()+'\\'))throw Error('Context outside owned assembly');
 return plan;
}
export async function main(args=process.argv.slice(2)){
 if(process.platform!=='win32'||process.arch!=='x64'||!same(process.execPath,NODE)||!same(fileURLToPath(import.meta.url),BASE+'/launch-books-qa.mjs')||!same(process.cwd(),BASE))throw Error('Not the protected fixed entry');
 if(args.length!==4||args[0]!=='--registry-sha'||!validHash(args[1])||args[2]!=='--deadline-unix-ms'||!/^\d{13}$/.test(args[3]))throw Error('Fixed outer native admission required');
 const deadline=Number(args[3]);if(deadline<=Date.now()||deadline>Date.now()+600000)throw Error('Expired or extended native deadline');
 const check=()=>{if(Date.now()>=deadline-2000)throw Error('Native work deadline reached');};
 // The native watcher holds the complete protected Koffi JS/native closure BEFORE this import.
 // Registry/data prechecks do not claim to establish that bootstrap trust themselves.
 const koffi=createRequire(import.meta.url)(BASE+'/runtime/koffi');const kernel=koffi.load('kernel32.dll');
 const native={open:kernel.func('void* __stdcall CreateFileW(str16,uint32_t,uint32_t,void*,uint32_t,uint32_t,void*)'),info:kernel.func('bool __stdcall GetFileInformationByHandle(void*,void*)'),close:kernel.func('bool __stdcall CloseHandle(void*)')};
 const handles=[],held=new Set();
 function one(file,directory){check();const key=path.win32.resolve(file).toLowerCase();if(held.has(key))return;const s=fs.lstatSync(file);if(s.isSymbolicLink()||(directory?!s.isDirectory():!s.isFile())||(!directory&&s.nlink!==1))throw Error('Nonordinary entry input');const h=native.open(file,directory?0x81:0x80000080,1,null,3,0x00200000|(directory?0x02000000:0),null);const b=Buffer.alloc(52);if(!h||!native.info(h,b)){if(h)native.close(h);throw Error('Native entry lease failed');}handles.push(h);if(b.readUInt32LE(0)&0x400||Boolean(b.readUInt32LE(0)&0x10)!==directory||(!directory&&b.readUInt32LE(40)!==1))throw Error('Native entry shape changed');held.add(key);}
 function retain(file){if(!abs(file))throw Error('Unsafe entry input');file=path.win32.resolve(file);const parents=[];for(let p=path.win32.dirname(file);;p=path.win32.dirname(p)){parents.unshift(p);if(path.win32.dirname(p)===p)break;}for(const p of parents)one(p,true);one(file,false);}
 function read(file,digest,bound){retain(file);const size=fs.statSync(file).size;if(size>bound)throw Error('Entry input too large');const raw=fs.readFileSync(file);check();if(raw.length!==size||sha(raw)!==digest)throw Error('Entry input pin changed');return raw;}
 let code=2,child=null;
 try{
  const registry=parseRegistry(read(BASE+'/operations.registry',args[1],16384).toString('utf8'));
  const raw=read(registry.plan_path,registry.plan_sha256,24000).toString('utf8');const plan=validateGuardian(JSON.parse(raw));
  if(plan.node.sha256!==registry.node_sha256)throw Error('Node registration disagreement');read(NODE,plan.node.sha256,128*1024*1024);
  read(plan.guardian.path,plan.guardian.sha256,128*1024);for(const name of CORE)read(STUDIO+'/.claude/skills/qa-handoff/scripts/'+name,plan.checker[name],128*1024);
  const env={SystemRoot:'C:\\Windows',WINDIR:'C:\\Windows',ComSpec:'C:\\Windows\\System32\\cmd.exe',PATH:'C:\\Program Files\\nodejs;C:\\Windows\\System32;C:\\Users\\AnGeLZzZ\\AppData\\Local\\Temp\\codex-books-2026-10-20\\shared\\git-ro-v1',PATHEXT:'.COM;.EXE;.BAT;.CMD'};
  check();code=await new Promise((resolve,reject)=>{child=spawn(NODE,[plan.guardian.path,'--plan-sha',registry.plan_sha256,'--plan-json',raw],{cwd:STUDIO,env,windowsHide:true,stdio:['ignore','pipe','pipe']});let bytes=0;for(const [stream,target] of [[child.stdout,process.stdout],[child.stderr,process.stderr]])stream.on('data',chunk=>{bytes+=chunk.length;if(bytes>16*1024*1024){reject(Error('Entry output exceeds bound'));return;}target.write(chunk);});child.on('error',reject);child.on('close',(status,signal)=>signal?reject(Error('Owned descendant signal')):resolve(status??2));});
  check();if(code!==0)throw Error('Fixed guardian refused');return 0;
 }finally{let fail=false;for(const h of handles.reverse())if(!native.close(h))fail=true;if(fail)throw Error('Entry lease closure failed');}
}
if(typeof process!=='undefined'&&process.argv[1]&&same(process.argv[1],fileURLToPath(import.meta.url)))main().then(code=>{process.exitCode=code;}).catch(error=>{console.error('Books protected entry REFUSED: '+error.message);process.exitCode=2;});

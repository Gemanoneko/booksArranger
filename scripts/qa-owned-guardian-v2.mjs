/**
 * CANDIDATE v2 Books-only outer owner. Not a deployed guard exception.
 * Requires independent review and approved exact invocation before use. It creates no files itself.
 * Invoke the pinned Node with --plan-sha SHA --plan-json EXACT_JSON under the
 * exact startup environment below. Plans and operations require separate review.
 *
 * Trust boundary: this file, the installed Node/OS loader, and Koffi's first load
 * execute before native leases exist. All are prehashed using ordinary read-only
 * APIs; immediately after Koffi loads, inputs are rehashed under retained native
 * handles. This is an explicit trusted launch bootstrap, not a race-free claim
 * about an attacker controlling the already-running interpreter or OS loader.
 * No child work is released before the canonical private Job has been assigned.
 */
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { performance } from 'node:perf_hooks';

const STUDIO='C:/Antigravity Projects/Studio Illuminati';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const CHECKER=path.join(STUDIO,'.claude/skills/qa-handoff/scripts');
const SELF=fileURLToPath(import.meta.url);
const CORE=['run_entry_checks.mjs','entry-main.mjs','entry-identity.mjs','bounded-check.mjs','bounded-child.mjs'];
const RUN_PARENT='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/q';
const CONTEXT_BASE='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-entry-context';
const NODE='C:/Program Files/nodejs/node.exe';
const PYTHON='C:/Python314/python.exe';
const GIT_RUNTIME='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/git-ro-v1';
const STARTUP={SystemRoot:'C:\\Windows',WINDIR:'C:\\Windows',ComSpec:'C:\\Windows\\System32\\cmd.exe',
  PATH:'C:\\Program Files\\nodejs;C:\\Windows\\System32;C:\\Users\\AnGeLZzZ\\AppData\\Local\\Temp\\codex-books-2026-10-20\\shared\\git-ro-v1',PATHEXT:'.COM;.EXE;.BAT;.CMD'};
const started=performance.now(),deadline=started+600000;
const timer=setTimeout(()=>{
  // Closing the guardian terminates its kill-on-close Job. There is no success
  // claim or fresh cleanup allowance when completion could not be observed.
  fs.writeSync(2,'Books guardian REFUSED: whole-invocation deadline; closure unproved\n');
  process.exit(2);
},600000);
const handles=[],held=new Map();
let native=null;
const fail=message=>{throw Error(message);};
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const same=(a,b)=>path.resolve(a).toLowerCase()===path.resolve(b).toLowerCase();
const within=(file,root)=>same(file,root)||path.resolve(file).toLowerCase().startsWith(path.resolve(root).toLowerCase()+path.sep);
const remaining=()=>{const value=Math.floor(deadline-performance.now());if(value<=0)fail('Whole-invocation deadline exceeded');return value;};
const validHash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const absolute=value=>{
  if(typeof value!=='string'||!path.isAbsolute(value)||!/^c:[\\/]/i.test(value)||value.length>259||value.slice(2).includes(':'))fail('Expected ordinary absolute C: input');
  return path.resolve(value);
};
const ref=value=>{
  if(!value||!validHash(value.sha256))fail('Missing exact file hash');
  return{path:absolute(value.path),sha256:value.sha256};
};
function canonical(value){
  if(Array.isArray(value))return'['+value.map(canonical).join(',')+']';
  if(value&&typeof value==='object')return'{'+Object.keys(value).sort().map(key=>canonical(key)+':'+canonical(value[key])).join(',')+'}';
  return JSON.stringify(value).replace(/[\u0080-\uffff]/g,char=>'\\u'+char.charCodeAt(0).toString(16).padStart(4,'0'));
}
function chain(file){
  const result=[];for(let current=absolute(file);;current=path.dirname(current)){
    result.unshift(current);if(path.dirname(current)===current)break;
  }return result;
}
function ordinary(file,directory){
  const info=fs.lstatSync(file);
  if(info.isSymbolicLink()||(directory?!info.isDirectory():!info.isFile())||(!directory&&info.nlink!==1))fail('Nonordinary input: '+file);
  return info;
}
function hold(file,directory){
  const key=absolute(file).toLowerCase();
  if(held.has(key)){const prior=held.get(key);if(prior.directory!==directory)fail('Input kind changed');return prior;}
  ordinary(file,directory);
  // LIST_DIRECTORY is a read-data access right; READ_ATTRIBUTES alone does not
  // establish the sharing conflict required to refuse parent rename/deletion.
  const handle=native.open(file,directory?0x81:0x80000000,1,null,3,0x00200000|(directory?0x02000000:0),null);
  const bytes=Buffer.alloc(52);
  if(!native.info(handle,bytes)){if(handle)native.close(handle);fail('Native input lease refused: '+file);}
  const attributes=bytes.readUInt32LE(0),links=bytes.readUInt32LE(40);
  if((attributes&0x400)||!!(attributes&0x10)!==directory||(!directory&&links!==1)){
    native.close(handle);fail('Native reparse/kind/link refusal: '+file);
  }
  const result={directory,handle,attributes,identity:[bytes.readUInt32LE(28),bytes.readUInt32LE(44),bytes.readUInt32LE(48)]};
  handles.push(handle);held.set(key,result);return result;
}
function protect(file,directory=false){
  const parts=chain(file);
  for(let i=0;i<parts.length;i++){
    remaining();const isDirectory=i<parts.length-1||directory;
    if(native)hold(parts[i],isDirectory);else ordinary(parts[i],isDirectory);
  }
  return native?held.get(absolute(file).toLowerCase()):null;
}
function hashFile(file){
  protect(file);const digest=createHash('sha256'),fd=fs.openSync(file,'r'),buffer=Buffer.alloc(1024*1024);let size=0;
  try{for(;;){remaining();const count=fs.readSync(fd,buffer,0,buffer.length,null);if(!count)break;digest.update(buffer.subarray(0,count));size+=count;}}
  finally{fs.closeSync(fd);}
  return{sha256:digest.digest('hex'),size};
}
function verifyFile(value){
  const item=ref(value);if(hashFile(item.path).sha256!==item.sha256)fail('Pinned file differs: '+item.path);return item.path;
}
function inventory(root){
  root=absolute(root);const records=[];
  function walk(directory){
    protect(directory,true);
    for(const name of fs.readdirSync(directory).sort()){
      remaining();const file=path.join(directory,name),info=fs.lstatSync(file);
      if(info.isSymbolicLink())fail('Runtime reparse entry refused: '+file);
      if(info.isDirectory())walk(file);
      else if(info.isFile())records.push({path:path.relative(root,file).split(path.sep).join('/'),...hashFile(file)});
      else fail('Runtime special entry refused: '+file);
    }
  }
  walk(root);return records.sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);
}
function verifyTree(tree){
  if(!tree||!validHash(tree.sha256)||!Number.isInteger(tree.count)||tree.count<1)fail('Incomplete runtime tree pin');
  const records=inventory(tree.root);
  if(records.length!==tree.count||sha(canonical(records))!==tree.sha256)fail('Complete runtime tree differs: '+tree.root);
}
function readJSON(value){const file=verifyFile(value);remaining();return JSON.parse(fs.readFileSync(file,'utf8'));}
function verifyManifest(root,value,{complete=true}={}){
  root=absolute(root);const manifest=readJSON(value),names=new Set();
  if(!Array.isArray(manifest.files)||!manifest.files.length)fail('Empty immutable manifest');
  for(const item of manifest.files){
    if(typeof item.path!=='string'||path.isAbsolute(item.path)||item.path.split(/[\\/]/).some(part=>!part||part==='.'||part==='..')||names.has(item.path.toLowerCase()))fail('Unsafe manifest member');
    names.add(item.path.toLowerCase());verifyFile({path:path.join(root,item.path),sha256:item.sha256});
  }
  if(complete){const actual=inventory(root);if(actual.length!==names.size||actual.some(item=>!names.has(item.path.toLowerCase())))fail('Immutable tree contains extra members');}
  return manifest;
}
function closeInputs(){
  let failure=false;for(const handle of handles.reverse())if(!native.close(handle))failure=true;
  handles.length=0;held.clear();if(failure)fail('Native input lease closure failed');
}
function startup(){
  if(process.platform!=='win32'||process.arch!=='x64'||!same(process.execPath,NODE)||!same(process.cwd(),STUDIO))fail('Wrong guardian bootstrap executable/platform/cwd');
  const wanted=new Map(Object.entries(STARTUP).map(([key,value])=>[key.toLowerCase(),value]));
  for(const [key,value]of Object.entries(process.env))if(wanted.get(key.toLowerCase())!==value)fail('Unreviewed startup environment variable: '+key);
  for(const [key,value]of wanted)if(!Object.entries(process.env).some(([name,actual])=>name.toLowerCase()===key&&actual===value))fail('Missing startup environment variable: '+key);
}
async function main(){
  startup();const args=process.argv.slice(2);
  if(args.length!==4||args[0]!=='--plan-sha'||args[2]!=='--plan-json'||!validHash(args[1])||args[3].length>24000||sha(args[3])!==args[1])fail('Exact reviewed guardian plan required');
  const plan=JSON.parse(args[3]);
  if(plan.schema!=='books-owned-guardian-v2'||!Array.isArray(plan.trees)||!plan.trees.length||!Array.isArray(plan.files)||!plan.files.length)fail('Incomplete guardian plan');
  if(!same(ref(plan.guardian).path,SELF)||!same(ref(plan.node).path,NODE)||Object.keys(plan.checker??{}).sort().join('|')!==[...CORE].sort().join('|'))fail('Wrong guardian/checker identity');
  const koffiRoot=absolute(plan.koffiRoot),nativeRoot=path.resolve(koffiRoot,'../@koromix/koffi-win32-x64');
  for(const root of [koffiRoot,nativeRoot,path.dirname(NODE)])if(!plan.trees.some(tree=>within(root,absolute(tree.root))))fail('Koffi/native/Node complete dependency tree is unpinned');
  const pins=[plan.guardian,plan.node,...CORE.map(name=>({path:path.join(CHECKER,name),sha256:plan.checker[name]})),...plan.files];
  const verifyInputs=()=>{for(const tree of plan.trees)verifyTree(tree);for(const item of pins)verifyFile(item);};
  verifyInputs();remaining();
  // The only non-builtin bootstrap import; both JS and native optional package
  // have complete preflight maps, then are checked again under native leases.
  const koffi=createRequire(import.meta.url)(koffiRoot),kernel=koffi.load('kernel32.dll');
  native={open:kernel.func('void* __stdcall CreateFileW(str16, uint32_t, uint32_t, void*, uint32_t, uint32_t, void*)'),
    info:kernel.func('bool __stdcall GetFileInformationByHandle(void*, void*)'),close:kernel.func('bool __stdcall CloseHandle(void*)')};
  verifyInputs();remaining();
  const pinned=file=>pins.some(item=>same(item.path,file))||plan.trees.some(tree=>within(file,tree.root));
  const operation=plan.operation??{};let file,argsForChild;
  if(operation.kind==='inert-controls'){
    file=NODE;const suite=path.join(CHECKER,'bounded-check-evidence.test.mjs');
    if(!pinned(suite))fail('Inert suite is unpinned');argsForChild=['--test',suite];
  }else if(operation.kind==='assemble'){
    file=PYTHON;const writer=path.join(ROOT,'scripts/qa-context-assembly-v2.py');
    if(!pinned(writer)||!plan.trees.some(tree=>within(PYTHON,tree.root)))fail('Assembly writer/Python runtime unpinned');
    if(typeof operation.planJSON!=='string'||operation.planJSON.length>20000||sha(operation.planJSON)!==operation.planSHA)fail('Assembly plan pin differs');
    const assembly=JSON.parse(operation.planJSON);
    if(assembly.schema!=='books-entry-assembly-plan-v2')fail('Wrong assembly plan');
    for(const item of Object.values(assembly.executables??{}))if(!pinned(ref(item).path))fail('Assembly executable lacks an outer lease');
    for(const relative of ['native_io.py','scripts/build_fs_guard.py'])if(!pinned(path.join(ROOT,relative)))fail('Assembly guard source lacks an outer lease');
    argsForChild=['-I','-B',writer,'--plan-sha',operation.planSHA,'--plan-json',operation.planJSON];
  }else if(operation.kind==='entry'){
    file=NODE;const contextRef=ref(operation.context);
    if(!within(contextRef.path,CONTEXT_BASE)||same(contextRef.path,CONTEXT_BASE))fail('Context is outside the owned Books assembly');
    const context=readJSON(contextRef),owner=readJSON(operation.owner);
    if(!context.runtime.manifests.some(tree=>tree.name==='git-installation'&&same(tree.root,GIT_RUNTIME)))fail('Reviewed private ordinary Git runtime missing');
    if(context.schema!==2||owner.schema!=='books-entry-assembly-owner-v2'||!same(context.execution?.runRootParent,RUN_PARENT))fail('Wrong owned Books context');
    const receipt=context.execution.runParentNativeReceipt;
    if(!receipt||!same(receipt.path,RUN_PARENT)||JSON.stringify(receipt)!==JSON.stringify(owner.run_parent))fail('Run parent receipt disagreement');
    const actual=protect(RUN_PARENT,true);
    if(JSON.stringify(actual.identity)!==JSON.stringify(receipt.identity)||actual.attributes!==receipt.attributes)fail('Run parent native identity changed');
    if(JSON.stringify(context.execution.ownedSiblingDirectories)!==JSON.stringify(['build-guard-probes']))fail('Unexpected sibling fixture ownership');
    verifyManifest(context.source.root,context.source.manifest);
    verifyManifest(context.source.repo,context.source.manifest,{complete:false});
    verifyManifest(context.harness.root,context.harness.manifest);
    for(const item of context.runtime.manifests)verifyManifest(item.root,item.manifest);
    for(const key of ['node','npmCli','shell','npmShim'])verifyFile(context.runtime[key]);
    if(!same(context.runtime.koffiRoot,koffiRoot))fail('Context ownership runtime differs');
    for(const item of context.tooling.files)if(plan.checker[item.path]!==item.sha256)fail('Context checker differs');
    argsForChild=[path.join(CHECKER,CORE[0]),'--context',contextRef.path,'--context-sha',contextRef.sha256,'--run-root',RUN_PARENT];
  }else fail('Only inert controls, assembly, or entry are supported');
  remaining();
  const {runOwned}=await import(pathToFileURL(path.join(CHECKER,'bounded-check.mjs')).href);
  const budget=remaining()-1000;if(budget<=0)fail('No owned execution budget remains');
  const result=await runOwned(file,argsForChild,{cwd:STUDIO,env:{...STARTUP},timeoutMs:budget,koffiRoot,maxBytes:16*1024*1024});
  // Exact input and run-parent handles outlive the owned Job and every retained
  // process handle. A close failure is refusal, even if inner checks passed.
  closeInputs();remaining();
  const ok=result.ok&&result.closed&&!result.forced&&!result.overflow&&!result.truncated&&result.native?.zero===true&&result.native?.unsignaled===0;
  process.stdout.write(result.out);process.stderr.write(result.err);process.stderr.write(result.supervisorErr);
  const {out,err,supervisorErr,...details}=result;
  console.log('Books guardian evidence v1: '+JSON.stringify({operation:operation.kind,planSHA:args[1],...details,ok,
    stdoutSHA:sha(out),stderrSHA:sha(err),supervisorStderrSHA:sha(supervisorErr),wholeElapsedMs:performance.now()-started}));
  return ok?0:1;
}
try{process.exitCode=await main();}
catch(error){process.exitCode=2;console.error('Books guardian REFUSED: '+error.message);}
finally{try{closeInputs();remaining();}catch(error){process.exitCode=2;console.error('Books guardian REFUSED: '+error.message);}clearTimeout(timer);}

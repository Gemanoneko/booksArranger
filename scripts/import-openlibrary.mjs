// Index-specific offline entry. The only child is the pinned sibling importer;
// callers provide a reviewed input plan, never an executable or arbitrary argv.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {performance} from 'node:perf_hooks';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const STUDIO='C:/Antigravity Projects/Studio Illuminati';
const OWNER=path.join(STUDIO,'.claude/skills/qa-handoff/scripts/bounded-check.mjs');
const CHILD=path.join(STUDIO,'.claude/skills/qa-handoff/scripts/bounded-child.mjs');
const KOFFI=path.join(STUDIO,'WIP/QuickLaunch/node_modules/koffi');
const ADDON=path.join(STUDIO,'WIP/QuickLaunch/node_modules/@koromix/koffi-win32-x64');
const PYTHON=path.join(ROOT,'build-cache/runtime/python/python.exe');
const started=performance.now();
function hash(raw){return createHash('sha256').update(raw).digest('hex');}
function key(file){return path.resolve(file).toLowerCase();}
const [planFile,expected,...extra]=process.argv.slice(2);
if(!planFile||extra.length||!/^([a-f0-9]{64})$/.test(expected||''))throw Error('Expected exact reviewed plan path and SHA256');
const raw=fs.readFileSync(planFile);if(hash(raw)!==expected)throw Error('Import plan differs from reviewed bytes');
const plan=JSON.parse(raw);
if(plan.schema!==1||!['fixture','actual'].includes(plan.mode)||!Array.isArray(plan.files)||typeof plan.includeEditions!=='boolean')throw Error('Invalid index input plan');
for(const field of ['manifest','targets','directory'])if(typeof plan[field]!=='string'||!path.isAbsolute(plan[field]))throw Error('Import paths must be absolute');
if(path.basename(plan.directory)!=='openlibrary-index')throw Error('Dedicated openlibrary-index directory required');
const pins=new Map(plan.files.map(p=>[key(p.path),p]));
if(pins.size!==plan.files.length||pins.size>512)throw Error('Ambiguous input pin list');
function verify(file){
  const pin=pins.get(key(file));if(!pin||!Number.isInteger(pin.size)||pin.size<0||pin.size>128*1024*1024||!/^([a-f0-9]{64})$/.test(pin.sha256))throw Error('Missing bounded input pin: '+file);
  const stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==1||stat.size!==pin.size||hash(fs.readFileSync(file))!==pin.sha256)throw Error('Input differs from reviewed pin: '+file);
}
const mandatory=[process.execPath,fileURLToPath(import.meta.url),OWNER,CHILD,plan.manifest,plan.targets,...fs.readdirSync(ROOT).filter(n=>n.endsWith('.py')).map(n=>path.join(ROOT,n)),...fs.readdirSync(path.dirname(PYTHON)).map(n=>path.join(path.dirname(PYTHON),n))];
for(const file of mandatory)verify(file);
for(const pin of pins.values()){
  const file=path.resolve(pin.path);
  if(!mandatory.some(p=>key(p)===key(file))&&!file.startsWith(path.resolve(KOFFI)+path.sep)&&!file.startsWith(path.resolve(ADDON)+path.sep))throw Error('Unrelated pin refused');
  verify(file);
}
// Verify the installed native runtime before loading, then retain and recheck all
// inputs through closure. The same installed runtime owns the existing runOwned.
for(const file of [path.join(KOFFI,'package.json'),path.join(KOFFI,'index.cjs'),path.join(KOFFI,'src/koffi/index.cjs'),path.join(KOFFI,'src/koffi/src/static.cjs'),path.join(ADDON,'package.json'),path.join(ADDON,'index.js'),path.join(ADDON,'win32_x64/koffi.node')])verify(file);
const require=createRequire(import.meta.url),koffi=require(KOFFI),kernel=koffi.load('kernel32.dll');
const open=kernel.func('void* __stdcall CreateFileW(str16,uint32_t,uint32_t,void*,uint32_t,uint32_t,void*)');
const info=kernel.func('bool __stdcall GetFileInformationByHandle(void*,void*)');
const close=kernel.func('bool __stdcall CloseHandle(void*)');
const holds=[],directories=new Set();
function hold(file,directory=false){
  const handle=open(file,0x81,1,null,3,0x00200000|(directory?0x02000000:0),null);
  if(!handle||koffi.address(handle)===0xffffffffffffffffn)throw Error('Cannot retain ordinary input: '+file);
  holds.push(handle);const raw=Buffer.alloc(52);
  if(!info(handle,raw)||raw.readUInt32LE(0)&0x400||Boolean(raw.readUInt32LE(0)&0x10)!==directory||(!directory&&raw.readUInt32LE(40)!==1))throw Error('Input native identity refused');
}
try{
  for(const file of [path.resolve(planFile),...pins.values()].map(value=>typeof value==='string'?value:path.resolve(value.path))){
    let parent=path.dirname(file),chain=[];
    while(!directories.has(key(parent))){chain.push(parent);const next=path.dirname(parent);if(next===parent)break;parent=next;}
    for(const dir of chain.reverse()){hold(dir,true);directories.add(key(dir));}
    hold(file);
  }
  if(hash(fs.readFileSync(planFile))!==expected)throw Error('Held plan changed');
  for(const pin of pins.values())verify(pin.path);
  const {runOwned}=await import(pathToFileURL(OWNER).href);
  const timeoutMs=Math.floor(600000-(performance.now()-started));if(timeoutMs<1000)throw Error('Input admission exceeded total deadline');
  // This pinned, native-held ordinary FILE cannot contain a cache subtree.
  // Python falls back to the pinned .py sources; -B also prevents cache writes.
  const args=['-I','-B','-X','pycache_prefix='+plan.manifest,path.join(ROOT,'openlibrary_index.py'),'--manifest',plan.manifest,'--targets',plan.targets,'--directory',plan.directory,'--seconds','540'];
  if(plan.includeEditions)args.push('--include-editions');
  const result=await runOwned(PYTHON,args,{cwd:ROOT,timeoutMs,koffiRoot:KOFFI,env:{...process.env,PYTHONPATH:'',PYTHONHOME:'',NODE_OPTIONS:'',NODE_PATH:''}});
  console.log(JSON.stringify({operation:'openlibrary-import',mode:plan.mode,plan_sha256:expected,...result}));
  if(!result.ok||!result.closed||result.forced||!result.native?.zero)process.exitCode=1;
}finally{for(const handle of holds.reverse())if(!close(handle))throw Error('Input native handle closure failed');}

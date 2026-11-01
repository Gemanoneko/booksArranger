// Purely verifies the exact private output and returns the manifest to native owner.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import * as asar from '@electron/asar';
import {getCurrentFuseWire,FuseVersion,FuseV1Options} from '@electron/fuses';
import yaml from 'js-yaml';
import {productTree} from './release-contract.mjs';
const request=JSON.parse(fs.readFileSync(0,'utf8'));
const root=request.root,output=request.output,unpacked=path.join(output,'win-unpacked');
function hash(bytes){return createHash('sha256').update(bytes).digest('hex');}
function facts(file){const b=fs.readFileSync(file);return {sha256:hash(b),size:b.length};}
function map(folder){const result={};function visit(p){for(const e of fs.readdirSync(p,{withFileTypes:true})){const full=path.join(p,e.name);const stat=fs.lstatSync(full);if(stat.isSymbolicLink()||stat.nlink!==1&&!stat.isDirectory())throw Error('Payload reparse/hardlink refused');if(e.isDirectory())visit(full);else result[path.relative(folder,full).split(path.sep).join('/')]=facts(full);}}visit(folder);return result;}
function same(a,b){return JSON.stringify(a)===JSON.stringify(b);}
function sorted(value){return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b,'en')));}
function run(exe,args){const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',windowsHide:true,timeout:Math.max(1,Math.min(120000,request.deadline-Date.now())),maxBuffer:16*1024*1024,env:process.env});if(r.error||r.status!==0)throw Error(r.error?.message||r.stderr||'Payload probe failed');return r.stdout;}
const git='C:/Program Files/Git/cmd/git.exe';
const sourceHead=run(git,['rev-parse','HEAD']).trim();
const records=run(git,['ls-tree','-r','--full-tree','HEAD']).trim().split('\n').map(line=>{const m=/^(\d+) \w+ ([a-f0-9]+)\t(.+)$/.exec(line);if(!m)throw Error('Invalid Git tree');return {mode:m[1],object:m[2],name:m[3]};});
if(run(git,['status','--porcelain','--untracked-files=normal']).trim())throw Error('Product source is dirty; commit before packaging');
const archive=path.join(unpacked,'resources','app.asar');
const shellPackage=JSON.parse(asar.extractFile(archive,'package.json').toString('utf8'));
if(shellPackage.version!==request.version)throw Error('ASAR shell version mismatch');
for(const name of ['desktop/main.js','desktop/icon.png','desktop/preload.js']){
 if(fs.existsSync(path.join(root,name))&&!asar.extractFile(archive,name).equals(fs.readFileSync(path.join(root,name))))throw Error('ASAR source mismatch '+name);
}

if(!request.shell||!request.shell_manifest||!request.pack_inputs_sha256)throw Error('Exact staged shell proof missing');
if(facts(path.join(root,'scripts/build-inputs.json')).sha256!==request.pack_inputs_sha256)throw Error('Pack input inventory changed');
const expectedShell=JSON.parse(fs.readFileSync(request.shell_manifest,'utf8'));
if(!same(sorted(map(request.shell)),sorted(expectedShell)))throw Error('Private shell stage changed');
const shellFiles={};
for(const member of asar.listPackage(archive)){
 const name=member.replace(/^[/\\]/,'').replace(/\\/g,'/');
 const info=asar.statFile(archive,name);
 if(info.link)throw Error('ASAR link member refused');
 if(!info.files)shellFiles[name]=asar.extractFile(archive,name);
}
if(!same(Object.keys(shellFiles).sort(),Object.keys(expectedShell).sort()))throw Error('ASAR complete shell/dependency membership mismatch');
const ignoredMetadata=new Set(['dist','gitHead','build','jspm','ava','xo','nyc','eslintConfig','contributors','bundleDependencies','tags','scripts','keywords']);
function canonicalJson(value){if(Array.isArray(value))return value.map(canonicalJson);if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonicalJson(value[k])]));return value;}
for(const [name,expected]of Object.entries(expectedShell)){
 const actual=shellFiles[name];
 if(name==='package.json'||name.endsWith('/package.json')){
  const source=JSON.parse(fs.readFileSync(path.join(request.shell,name),'utf8'));
  const isMain=name==='package.json';
  const removeBabel=source.dependencies&&typeof source.dependencies==='object'&&!Object.keys(source.dependencies).some(n=>n.startsWith('babel'));
  for(const key of Object.keys(source))if(key.startsWith('_')||ignoredMetadata.has(key)||(isMain&&key==='devDependencies')||(!isMain&&key==='bugs')||(removeBabel&&key==='babel'))delete source[key];
  if(!same(canonicalJson(source),canonicalJson(JSON.parse(actual.toString('utf8')))))throw Error('ASAR runtime package metadata differs '+name);
 }else if(actual.length!==expected.size||hash(actual)!==expected.sha256)throw Error('ASAR complete shell/dependency bytes differ '+name);
}
const fuseWire=await getCurrentFuseWire(path.join(unpacked,'Books Arranger.exe'));
if(fuseWire.version!==FuseVersion.V1||fuseWire[FuseV1Options.RunAsNode]!==48||fuseWire[FuseV1Options.EnableNodeOptionsEnvironmentVariable]!==48||fuseWire[FuseV1Options.OnlyLoadAppFromAsar]!==49)throw Error('Packaged Electron fuse configuration differs');
const updateConfig=yaml.load(fs.readFileSync(path.join(unpacked,'resources/app-update.yml'),'utf8'));
const expectedPublish=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8')).build.publish;
for(const key of ['provider','owner','repo'])if(updateConfig?.[key]!==expectedPublish[key])throw Error('Packaged update configuration differs '+key);

const backendVersion=fs.readFileSync(path.join(unpacked,'resources','backend','VERSION'),'utf8').trim();
if(backendVersion!==request.version)throw Error('Packaged backend version mismatch');
const protectedFiles={};
for(const name of ['replacement_eye_plan.json','public_source_leads.json']){
 const source=facts(path.join(root,name)),packed=facts(path.join(unpacked,'resources','backend',name));
 if(!same(source,packed))throw Error('Protected raw JSON differs');protectedFiles[name]=packed;
}
const runtimeFiles={};for(const kind of ['python','ffmpeg']){const actual=map(path.join(unpacked,'resources',kind)),expected=map(path.join(request.runtime,kind));if(!same(sorted(actual),sorted(expected)))throw Error('Runtime resource differs '+kind);for(const [name,f]of Object.entries(actual))runtimeFiles['resources/'+kind+'/'+name]=f;}
const backendPacked=map(path.join(unpacked,'resources','backend'));
if(!same(sorted(backendPacked),sorted(map(request.backend))))throw Error('Backend stage bytes differ from packaged resources');
const files=map(unpacked);
// Native phase passes a separately extracted NSIS app64 payload. No integrity
// assertion derives from mere installer existence or unpacked artifact alone.
if(!request.nsis_payload)throw Error('Actual extracted NSIS payload missing; verification blocked');
const nsis=map(request.nsis_payload);
if(!same(sorted(files),sorted(nsis)))throw Error('NSIS app64 payload differs from accepted unpacked bytes');
const artifacts=['Books-Arranger-Setup-'+request.version+'.exe','Books-Arranger-Setup-'+request.version+'.exe.blockmap','latest.yml'].map(name=>({path:'builds/'+request.build_id+'/'+name,...facts(path.join(output,name))}));
const fileMap=sorted(files);
const manifest={schema:'books-desktop-artifacts-v1',version:request.version,source_head:sourceHead,product_digest:productTree(records),build_id:request.build_id,unpacked:'builds/'+request.build_id+'/win-unpacked',runtime:{pins_sha256:facts(path.join(root,'desktop','runtime-pins.json')).sha256,files:sorted(runtimeFiles)},payload:{verified:true,shell_version:request.version,backend_version:backendVersion,installer_equivalent:true,files:fileMap,protected_data_files:protectedFiles,manifest_sha256:hash(Buffer.from(JSON.stringify(fileMap)))},artifacts};
process.stdout.write(JSON.stringify(manifest,null,2)+'\n');

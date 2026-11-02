#!/usr/bin/env node
// One finite owned pack operation. No CLI passthrough or general launcher.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire,syncBuiltinESMExports} from 'node:module';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {validateChildLease} from './guarded-io.mjs';
import {createChildPolicy,fileFacts} from './build-child-policy.mjs';
const require=createRequire(import.meta.url);
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const same=isDeepStrictEqual; // JSON object property order does not change membership or file facts.
function ordinaryMap(folder) {
  const values={};
  function walk(current) {
    for(const item of fs.readdirSync(current,{withFileTypes:true})) {
      const file=path.join(current,item.name);
      if(item.isSymbolicLink())throw Error('Private app reparse member');
      if(item.isDirectory())walk(file);
      else values[path.relative(folder,file).split(path.sep).join('/')]=fileFacts(file);
    }
  }
  walk(folder);return values;
}
function sorted(value){return Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b,'en')));}
export function verifyAppStage(app,manifest) {
  if(!same(sorted(ordinaryMap(app)),sorted(manifest)))throw Error('Private app membership or bytes changed');
}
export function packageArchivePath(packageJson,output,projectRoot) {
  if(packageJson?.name!=='books-arranger'||!/^\d+\.\d+\.\d+$/.test(packageJson?.version||''))throw Error('Invalid archive package identity/version');
  const builds=path.join(projectRoot,'dist','builds')+path.sep;
  if(typeof output!=='string'||!path.isAbsolute(output)||path.resolve(output)!==output||!output.startsWith(builds))throw Error('Archive output escape');
  return path.join(output,packageJson.name+'-'+packageJson.version+'-x64.nsis.7z');
}
function installNetworkBoundary(policy) {
  const restorers=[];
  for(const [name,methods] of [['http',['request','get']],['https',['request','get']],['net',['connect','createConnection']],['tls',['connect']],['dns',['lookup','resolve','resolve4','resolve6']]]) {
    const module=require('node:'+name);
    for(const method of methods){const original=module[method];module[method]=policy.rejectNetwork;restorers.push(()=>module[method]=original);}
    if(name==='net'){const original=module.Socket.prototype.connect;module.Socket.prototype.connect=policy.rejectNetwork;restorers.push(()=>module.Socket.prototype.connect=original);}
  }
  const originalFetch=globalThis.fetch;globalThis.fetch=policy.rejectNetwork;
  syncBuiltinESMExports();
  return ()=>{for(const restore of restorers.reverse())restore();globalThis.fetch=originalFetch;syncBuiltinESMExports();};
}
async function main() {
  if(process.argv.length!==2&&!(process.argv.length===3&&process.argv[2]==='--icons'))throw Error('Unsupported builder invocation');
  const iconOnly=process.argv[2]==='--icons';
  const lease=validateChildLease({mode:'build',root});delete lease.manifestPath;
  const owned=lease.ownedRoot;
  const inputPath=path.join(root,'scripts/build-inputs.json');
  if(digest(fs.readFileSync(inputPath))!==lease.pack_inputs?.config_sha256)throw Error('Pack input capability changed');
  const pins=JSON.parse(fs.readFileSync(inputPath,'utf8'));
  const seed=path.join(root,pins.seedDirectory);
  if(seed!==lease.pack_inputs.root)throw Error('Pack seed mismatch');
  const requestPath=path.join(owned,iconOnly?'icons-request.json':'builder-request.json');
  const request=JSON.parse(fs.readFileSync(requestPath,'utf8'));
  if(request.lease_nonce!==lease.nonce)throw Error('Private builder request not bound to lease');
  const tools=Object.fromEntries(Object.entries(pins.tools).map(([name,relative])=>[name,path.join(seed,relative)]));
  const baseEnv={...process.env, ELECTRON_BUILDER_NSIS_DIR:tools.nsisRoot,ELECTRON_BUILDER_NSIS_RESOURCES_DIR:tools.nsisResources,ELECTRON_BUILDER_7ZIP_PATH:tools.seven};
  Object.assign(process.env,baseEnv);
  const executablePins={};
  for(const file of [lease.node,'C:/Python314/python.exe',tools.npm,tools.nsis,tools.seven,path.join(root,'scripts/build-nsis-generator.py')])executablePins[file]=fileFacts(file);
  // Fixed native/tool bytes are already deny-write/delete-held by the supervisor.
  for(const name of ['npm','nsis','seven'])if(!same(executablePins[tools[name]],pins.files[pins.tools[name]]))throw Error('Pack executable fingerprint mismatch '+name);
  const context={root,ownedRoot:owned,output:request.output,appDir:request.app,deadline:lease.deadline,node:lease.node,bootstrap:'C:/Python314/python.exe',
    npmCli:tools.npm,nsis:tools.nsis,seven:tools.seven,nsisTemplates:path.join(root,'node_modules/app-builder-lib/templates/nsis'),
    generator:request.generator||{},executablePins,baseEnv,iconOnly,
    ...(!iconOnly?{archivePath:packageArchivePath(JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8')),request.output,root)}:{})};
  const policy=createChildPolicy(context);
  policy.install();
  installNetworkBoundary(policy);
  process.once('beforeExit',()=>policy.assertClean());
  if(iconOnly) {
    // CLI is pinned explicitly at1.2.3; no default1.1.0 builder tool substitution.
    if(request.input!==path.join(root,'desktop/icon.png')||request.output!==path.join(owned,'icons'))throw Error('Unlisted icon conversion');
    process.argv=[lease.node,tools.icons,'--input='+request.input,'--format=ico','--out='+request.output];
    process.once('beforeExit',()=>{
      policy.assertClean();
      const ico=fileFacts(path.join(request.output,'icon.ico'));
      if(ico.size<22)throw Error('Icon conversion produced no valid output');
    });
    require(tools.icons);
    return; // Keep process/network boundary active until converter event loop drains.
  }
  try {
    if(request.app!==path.join(owned,'shell')||!request.output.startsWith(path.join(root,'dist/builds')+path.sep))throw Error('Builder request path escape');
    const manifest=JSON.parse(fs.readFileSync(path.join(owned,'shell-manifest.json'),'utf8'));
    verifyAppStage(request.app,manifest);
    const config=JSON.parse(fs.readFileSync(path.join(owned,'builder-config.json'),'utf8'));
    if(config.electronDist!==tools.electron||config.electronVersion!==pins.electronVersion||config.nodeGypRebuild!==false||config.npmRebuild!==true)throw Error('Private builder configuration mismatch');
    if(config.directories.app!==request.app||config.directories.output!==request.output)throw Error('Builder directory mismatch');
    const util=require('builder-util'); // imports capture the already-installed child boundary
    policy.wrapBuilderUtilities(util); // before cross-spawn resolves bare npm
    const builder=require('electron-builder');
    let hookCount=0;
    config.beforeBuild=async context=>{
      if(path.resolve(context.appDir)!==request.app||context.arch!=='x64'||context.electronVersion!==pins.electronVersion)throw Error('Unexpected external dependency hook');
      verifyAppStage(request.app,manifest);hookCount++;return false;
    };
    await builder.build({projectDir:root,targets:builder.Platform.WINDOWS.createTarget(['nsis'],builder.Arch.x64),publish:'never',config});
    policy.assertClean();
    if(hookCount!==1)throw Error('External production dependency hook did not run exactly once');
    verifyAppStage(request.app,manifest);
    fs.writeFileSync(path.join(owned,'builder-policy-result.json'),JSON.stringify({schema:'books-builder-policy-v1',passed:true,beforeBuildCalls:hookCount,launches:policy.launches},null,2)+'\n',{flag:'wx'});
  } finally {
    // One-use controller: late dependency work stays guarded through process exit.
    policy.assertClean(); // A dependency cannot turn a caught refusal into success.
  }
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  main().catch(error=>{console.error('Guarded builder: '+error.message);process.exitCode=1;});
}

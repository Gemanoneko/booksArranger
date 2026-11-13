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

// Diagnostic evidence only: never substitutes for the final package proofs.
export function createBuildTrace(file) {
  const fd=fs.openSync(file,'wx');
  const state={schema:'books-builder-progress-v1',diagnostic_only:true,phases:[],children:[]};
  const phases=new Set(['lease-validated','policy-installed','dependencies-loaded','before-build',
    'builder-await','builder-returned','stage-verified','complete','icons-await','icons-verified',
    'out-open-enter','out-open-returned','out-close-enter','out-close-returned',
    'nsis-path-enter','nsis-path-returned','nsis-path-rejected',
    'compiler-util-enter','compiler-util-returned','compiler-util-rejected']);
  function flush(){const bytes=Buffer.from(JSON.stringify(state));if(bytes.length>65536)throw Error('Build diagnostic byte bound');fs.ftruncateSync(fd,0);fs.writeSync(fd,bytes,0,bytes.length,0);fs.fsyncSync(fd);}
  flush();
  return {
    phase(name){if(!phases.has(name)||state.phases.length>=64)throw Error('Build diagnostic phase bound');state.phases.push(name);flush();},
    child(event,data){
      if(event==='prepared'){
        if(data.index!==state.children.length||data.index>=128||!['npm-prefix','nsis-archive','makensis','nsis-generator'].includes(data.kind)||
           ![data.file,data.cwd].every(v=>typeof v==='string'&&v.length<=4096&&!/[\0\r\n]/.test(v)))throw Error('Build diagnostic child bound');
        state.children.push({kind:data.kind,file:data.file,cwd:data.cwd,state:'prepared'});
      }else{
        const item=state.children[data.index];if(!item)throw Error('Unknown diagnostic child');
        if(event==='spawned'){if(data.pid!==null&&(!Number.isInteger(data.pid)||data.pid<=0))throw Error('Invalid diagnostic PID');item.pid=data.pid;item.state='spawned';}
        else if(event==='error'){item.error_code=/^[A-Z_0-9]{1,64}$/.test(data.code)?data.code:'UNKNOWN';item.state='error';}
        else if(event==='closed'){if(data.code!==null&&!Number.isInteger(data.code))throw Error('Invalid diagnostic exit');item.exit_code=data.code;item.signal=typeof data.signal==='string'&&/^SIG[A-Z0-9]{1,16}$/.test(data.signal)?data.signal:null;item.state='closed';}
        else throw Error('Unknown diagnostic event');
      }
      flush();
    },
    close(){fs.closeSync(fd);}
  };
}

export function watchBuildCompletion(work,{isVerified,subscribeBeforeExit,subscribeExit=()=>{},fail,enqueue=queueMicrotask}) {
  let settled=false,failed=false;
  const result=Promise.resolve(work).then(()=>{settled=true;},error=>{settled=true;failed=true;fail(error);});
  // Icon proof runs synchronously in the same beforeExit emission. No timer
  // keeps an unfinished await alive or extends the native build deadline.
  const check=()=>{if(failed||!settled||!isVerified())fail(Error('Build exited before verified async completion'));};
  subscribeBeforeExit(()=>enqueue(check));
  // Explicit process.exit skips beforeExit. This check must be synchronous.
  subscribeExit(check);
  return result;
}

export function compilerErrorRecord(error,environment={}) {
  const secrets=Object.entries(environment).filter(([key,value])=>/TOKEN|SECRET|PASSWORD|CREDENTIAL|API_KEY|PRIVATE_KEY|AUTHORIZATION|COOKIE/i.test(key)&&typeof value==='string'&&value.length>=4).map(([,value])=>value);
  function text(value,limit){
    let s=Buffer.isBuffer(value)?value.toString('utf8'):typeof value==='string'?value:'';
    for(const secret of secrets)s=s.split(secret).join('[redacted]');
    s=s.replace(/(https?:\/\/)[^\s/@:]+:[^\s/@]+@/gi,'$1[redacted]@')
      .replace(/((?:password|token|secret|authorization|api_key)\s*[:=]\s*)[^\s;]+/gi,'$1[redacted]')
      .replace(/\bBearer\s+[^\s;]+/gi,'Bearer [redacted]');
    const b=Buffer.from(s);return b.length<=limit?s:b.subarray(0,limit/2).toString('utf8')+'\n[bounded middle omitted]\n'+b.subarray(-limit/2).toString('utf8');
  }
  return {schema:'books-compiler-error-v1',diagnostic_only:true,compiler:'makensis',
    exit_code:Number.isInteger(error?.exitCode)?error.exitCode:null,
    message:text(error?.message,24000),stdout:text(error?.stdout,12000),stderr:text(error?.stderr,12000)};
}

export function orderPrivateCompilerInput(script,{privateInclude,pluginDirectory}) {
  if(typeof script!=='string'||Buffer.byteLength(script)>4*1024*1024)throw Error('Bounded compiler input required');
  const newline=script.includes('\r\n')?'\r\n':'\n',lines=script.split(newline);
  const include='!include "'+privateInclude+'"',plugin='!addplugindir /x86-unicode "'+pluginDirectory+'"';
  const includes=lines.map((line,index)=>line===include?index:-1).filter(index=>index>=0);
  const plugins=lines.map((line,index)=>/^\s*!addplugindir\b/i.test(line)?index:-1).filter(index=>index>=0);
  if(includes.length!==1||plugins.length!==1||lines[plugins[0]]!==plugin)throw Error('Expected single exact private include and pinned plugin directive');
  const ordered=[...lines];if(plugins[0]>includes[0]){ordered.splice(plugins[0],1);ordered.splice(includes[0],0,plugin);}
  const result=ordered.join(newline);
  return {script:result,original_sha256:digest(Buffer.from(script)),final_sha256:digest(Buffer.from(result)),
    private_include:privateInclude,pinned_plugin_directory:pluginDirectory,method:'Only the single expected plugin directive is moved before the exact private include'};
}

export function observeNsisAwait({fsApi,windows,util,output,nsis,onPhase,onCompilerFailure=()=>{},onCompilerInput=null}) {
  const original={open:fsApi.open,close:fsApi.close,path:windows.getMakeNsisPath,compiler:util.spawnAndWriteWithOutput};
  const fds=new Set(),same=(a,b)=>typeof a==='string'&&path.resolve(a).toLowerCase()===path.resolve(b).toLowerCase();
  fsApi.open=function(...args){
    if(!same(args[0],output)||typeof args.at(-1)!=='function')return original.open.apply(this,args);
    onPhase('out-open-enter');const callback=args.at(-1);
    args[args.length-1]=function(error,fd){onPhase('out-open-returned');if(Number.isInteger(fd))fds.add(fd);return callback.apply(this,arguments);};
    return original.open.apply(this,args);
  };
  fsApi.close=function(fd,callback){
    if(!fds.has(fd)||typeof callback!=='function')return original.close.apply(this,arguments);
    onPhase('out-close-enter');return original.close.call(this,fd,function(){fds.delete(fd);onPhase('out-close-returned');return callback.apply(this,arguments);});
  };
  windows.getMakeNsisPath=async function(...args){onPhase('nsis-path-enter');try{const value=await original.path.apply(this,args);onPhase('nsis-path-returned');return value;}catch(error){onPhase('nsis-path-rejected');throw error;}};
  util.spawnAndWriteWithOutput=async function(...args){
    if(!same(args[0],nsis))return original.compiler.apply(this,args);
    onPhase('compiler-util-enter');try{if(onCompilerInput)args[2]=onCompilerInput(args[2]);const value=await original.compiler.apply(this,args);onPhase('compiler-util-returned');return value;}catch(error){onPhase('compiler-util-rejected');onCompilerFailure(error);throw error;}
  };
  return ()=>{fsApi.open=original.open;fsApi.close=original.close;windows.getMakeNsisPath=original.path;util.spawnAndWriteWithOutput=original.compiler;};
}
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
async function main(verified=()=>{}) {
  if(process.argv.length!==2&&!(process.argv.length===3&&process.argv[2]==='--icons'))throw Error('Unsupported builder invocation');
  const iconOnly=process.argv[2]==='--icons';
  const lease=validateChildLease({mode:'build',root});delete lease.manifestPath;
  const owned=lease.ownedRoot;
  const trace=createBuildTrace(path.join(owned,process.argv[2]==='--icons'?'icons-progress.json':'builder-progress.json'));
  trace.phase('lease-validated');
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
  const policy=createChildPolicy(context,{onChildEvent:(event,data)=>trace.child(event,data)});
  policy.install();
  installNetworkBoundary(policy);
  trace.phase('policy-installed');
  process.once('beforeExit',()=>policy.assertClean());
  if(iconOnly) {
    // CLI is pinned explicitly at1.2.3; no default1.1.0 builder tool substitution.
    if(request.input!==path.join(root,'desktop/icon.png')||request.output!==path.join(owned,'icons'))throw Error('Unlisted icon conversion');
    process.argv=[lease.node,tools.icons,'--input='+request.input,'--format=ico','--out='+request.output];
    process.once('beforeExit',()=>{
      policy.assertClean();
      const ico=fileFacts(path.join(request.output,'icon.ico'));
      if(ico.size<22)throw Error('Icon conversion produced no valid output');
      trace.phase('icons-verified');verified();
    });
    trace.phase('icons-await');
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
    let compilerInputCount=0;
    observeNsisAwait({fsApi:require('node:fs'),windows:require('app-builder-lib/out/toolsets/windows'),util,
      output:request.generator.image,nsis:tools.nsis,onPhase:name=>trace.phase(name),
      onCompilerInput:script=>{if(compilerInputCount>=2)throw Error('Expected at most two compiler inputs');
        const ordered=orderPrivateCompilerInput(script,{privateInclude:path.join(owned,'nsis-private.nsh'),pluginDirectory:path.join(tools.nsisResources,'plugins','x86-unicode')});
        const prefix=path.join(owned,'compiler-input-'+compilerInputCount++);
        for(const [suffix,bytes] of [['.nsi',ordered.script],['.json',JSON.stringify({...ordered,script:undefined})]]){
          const fd=fs.openSync(prefix+suffix,'wx');try{fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
        return ordered.script;},
      onCompilerFailure:error=>{const bytes=Buffer.from(JSON.stringify(compilerErrorRecord(error,context.baseEnv)));if(bytes.length>65536)throw Error('Compiler diagnostic byte bound');
        const fd=fs.openSync(path.join(owned,'compiler-error.json'),'wx');try{fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}});
    trace.phase('dependencies-loaded');
    let hookCount=0;
    config.beforeBuild=async context=>{
      if(path.resolve(context.appDir)!==request.app||context.arch!=='x64'||context.electronVersion!==pins.electronVersion)throw Error('Unexpected external dependency hook');
      verifyAppStage(request.app,manifest);hookCount++;trace.phase('before-build');return false;
    };
    trace.phase('builder-await');
    await builder.build({projectDir:root,targets:builder.Platform.WINDOWS.createTarget(['nsis'],builder.Arch.x64),publish:'never',config});
    trace.phase('builder-returned');
    policy.assertClean();
    if(hookCount!==1)throw Error('External production dependency hook did not run exactly once');
    verifyAppStage(request.app,manifest);
    trace.phase('stage-verified');
    fs.writeFileSync(path.join(owned,'builder-policy-result.json'),JSON.stringify({schema:'books-builder-policy-v1',passed:true,beforeBuildCalls:hookCount,launches:policy.launches},null,2)+'\n',{flag:'wx'});
    trace.phase('complete');verified();
  } finally {
    // One-use controller: late dependency work stays guarded through process exit.
    policy.assertClean(); // A dependency cannot turn a caught refusal into success.
  }
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  let verified=false;
  watchBuildCompletion(main(()=>{verified=true;}),{isVerified:()=>verified,
    subscribeBeforeExit:listener=>process.once('beforeExit',listener),
    subscribeExit:listener=>process.once('exit',listener),
    fail:error=>{process.exitCode=1;console.error('Guarded builder: '+compilerErrorRecord(error,process.env).message);}});
}

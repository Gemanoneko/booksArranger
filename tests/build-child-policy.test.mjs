import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import cp from 'node:child_process';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import tls from 'node:tls';
import dns from 'node:dns';
import dgram from 'node:dgram';
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import {EventEmitter} from 'node:events';
import {createRequire, syncBuiltinESMExports} from 'node:module';

// Guards precede production and third-party imports. No test is permission to
// launch a child, query native APIs or contact a network service.
const restores=[];let nativeAttempts=0;
function guard(object,name){
  if(typeof object[name]!=='function')return;
  const original=object[name];restores.push(()=>{object[name]=original;});
  object[name]=()=>{nativeAttempts++;throw Error('Native operation prohibited in pack policy tests: '+name);};
}
for(const name of ['spawn','spawnSync','exec','execSync','execFile','execFileSync','fork'])guard(cp,name);
guard(cp.ChildProcess.prototype,'spawn');
for(const module of [http,https])for(const name of ['request','get'])guard(module,name);
for(const name of ['connect','createConnection','createServer'])guard(net,name);
guard(net.Socket.prototype,'connect');guard(tls,'connect');guard(tls,'createServer');
for(const name of ['lookup','resolve','resolve4','resolve6','reverse'])guard(dns,name);
guard(dgram,'createSocket');guard(globalThis,'fetch');guard(process,'dlopen');
syncBuiltinESMExports();
after(()=>{for(const restore of restores.reverse())restore();syncBuiltinESMExports();assert.equal(nativeAttempts,0,'No real process/network/native call was attempted');});
const {createChildPolicy,fileFacts}=await import('../scripts/build-child-policy.mjs');
const {verifyAppStage}=await import('../scripts/build-builder.mjs');
const require=createRequire(import.meta.url);

function fixture(overrides={}){
  const root=path.resolve(process.env.TEMP||process.env.TMP||'.','books-pack-policy-inert');
  const ownedRoot=path.join(root,'build-cache','builds','owned');
  const output=path.join(ownedRoot,'output');
  const context={root,ownedRoot,output,appDir:path.join(ownedRoot,'app'),deadline:10000,
    node:process.execPath,bootstrap:path.join(root,'bootstrap','python.exe'),
    npmCli:path.join(ownedRoot,'inputs','npm','bin','npm-cli.js'),
    nsis:path.join(ownedRoot,'inputs','nsis','Bin','makensis.exe'),
    seven:path.join(ownedRoot,'inputs','seven','bin','7za.exe'),
    nsisTemplates:path.join(root,'node_modules','app-builder-lib','templates','nsis'),
    generator:{image:path.join(output,'uninstaller-generator.exe'),requestPath:path.join(ownedRoot,'generator-request.json'),
      requestSha256:'b'.repeat(64),script:path.join(root,'scripts','build-generator.py')},
    baseEnv:{SystemRoot:'C:/Windows',WINDIR:'C:/Windows',PATH:path.dirname(process.execPath),TEMP:ownedRoot,TMP:ownedRoot,
      USERPROFILE:path.join(ownedRoot,'profile'),APPDATA:path.join(ownedRoot,'profile','Roaming'),LOCALAPPDATA:path.join(ownedRoot,'profile','Local')}};
  Object.assign(context,overrides);
  const facts={size:17,sha256:'a'.repeat(64)};
  context.executablePins=Object.fromEntries([context.node,context.bootstrap,context.npmCli,context.nsis,context.seven,context.generator.script].map(p=>[p,{...facts}]));
  const inspected=[];let current=1000,drift=false;
  const policy=createChildPolicy(context,{now:()=>current,inspectFile:file=>{inspected.push(file);return {...facts,...(drift?{sha256:'c'.repeat(64)}:{})};}});
  const npm=[context.npmCli,'prefix','-w'];
  const archive=['a','-bd','-mx=9','-md=1m','-mtc=off','-ms=off','-mtm=off','-mta=off',path.join(output,'books-arranger-0.24.2-x64.nsis.7z'),'.'];
  return {context,policy,inspected,npm,archive,setNow:n=>{current=n;},setDrift:()=>{drift=true;}};
}
function denied(f,call,pattern=/Pack child refused/){
  assert.throws(call,pattern);
  assert.throws(()=>f.policy.assertClean(),/Pack child refused/,'a swallowed refusal must remain fatal');
}
function fakeProcess(output='fixture output\n'){
  const child=new EventEmitter();child.pid=424242;child.stdout=new EventEmitter();child.stderr=new EventEmitter();
  child.stdin={end(){}};child.kill=()=>{throw Error('No test should kill even a fake process');};
  queueMicrotask(()=>{child.stdout.emit('data',Buffer.from(output));child.emit('close',0);});
  return child;
}

test('fixed npm prefix becomes a hidden, private, lease-bounded Node launch',()=>{
  const f=fixture(),options={cwd:f.context.appDir,timeout:4000};
  const result=f.policy.prepare(f.context.node,f.npm,options);
  assert.equal(result.file,f.context.node);assert.deepEqual(result.args,f.npm);
  assert.equal(result.options.windowsHide,true);assert.equal(result.options.shell,false);assert.equal(result.options.detached,false);
  assert.equal(result.options.timeout,4000);assert.deepEqual(result.options.env,f.context.baseEnv);
  assert.deepEqual(options,{cwd:f.context.appDir,timeout:4000});
  assert.deepEqual(f.inspected,[f.context.npmCli,f.context.node]);f.policy.assertClean();
});

test('timeout cannot exceed the remaining original lease',()=>{
  const f=fixture();f.setNow(9500);
  assert.equal(f.policy.prepare(f.context.node,f.npm,{timeout:5000}).options.timeout,500);
  f.setNow(10000);denied(f,()=>f.policy.prepare(f.context.node,f.npm));
});

test('7zip permits only the exact private NSIS archive operation',()=>{
  const f=fixture(),result=f.policy.prepare(f.context.seven,f.archive,{cwd:path.join(f.context.output,'win-unpacked')});
  assert.equal(result.file,f.context.seven);assert.deepEqual(result.args,f.archive);assert.equal(result.options.windowsHide,true);
  assert.equal(f.policy.launches[0].kind,'nsis-archive');f.policy.assertClean();
});

test('makensis binds stdin compiler shape, templates cwd and generator output',()=>{
  const f=fixture(),args=['-WX','-INPUTCHARSET','UTF8','-DVERSION=0.24.2','-XOutFile "'+f.context.generator.image+'"','-'];
  const result=f.policy.prepare(f.context.nsis,args,{cwd:f.context.nsisTemplates,env:{NSISDIR:path.dirname(path.dirname(f.context.nsis))}});
  assert.deepEqual(result.args,args);assert.equal(result.options.env.TEMP,f.context.ownedRoot);
  assert.equal(result.options.windowsHide,true);assert.equal(f.policy.launches[0].kind,'makensis');
});

test('generated helper maps to fixed bootstrap bridge and exact retained request hash',()=>{
  const f=fixture(),result=f.policy.prepare(f.context.generator.image,[],{env:{__COMPAT_LAYER:'RunAsInvoker'}},'execFile');
  assert.equal(result.file,f.context.bootstrap);
  assert.deepEqual(result.args,['-I','-B',f.context.generator.script,f.context.generator.requestPath,f.context.generator.requestSha256]);
  assert.equal(result.options.env.USERPROFILE,f.context.baseEnv.USERPROFILE);
  assert.equal(result.options.env.TEMP,f.context.ownedRoot);assert.equal(result.options.env.__COMPAT_LAYER,'RunAsInvoker');
  assert.deepEqual(f.inspected,[f.context.bootstrap,f.context.generator.script]);
});

test('unknown, relative, shell and application executables refuse before a launch',()=>{
  for(const file of ['npm','cmd.exe','powershell.exe',path.resolve('unknown.exe')]){
    const f=fixture();denied(f,()=>f.policy.prepare(file,[]));assert.equal(f.policy.launches.length,0);
  }
});

test('shell, detached, visible and verbatim process options remain forbidden',()=>{
  for(const options of [{shell:true},{shell:'cmd.exe'},{detached:true},{windowsHide:false},{windowsVerbatimArguments:true}]){
    const f=fixture();denied(f,()=>f.policy.prepare(f.context.node,f.npm,options));assert.equal(f.policy.launches.length,0);
  }
});

test('EncodedCommand, changed argv and nonliteral arguments refuse',()=>{
  for(const args of [['-EncodedCommand','abc'],['prefix','-w'],['--eval','1'],[null],['line\nbreak']]){
    const f=fixture();denied(f,()=>f.policy.prepare(f.context.node,args));
  }
  for(const args of [null,'prefix -w']){const f=fixture();denied(f,()=>f.policy.prepare(f.context.node,args));}
});

test('private environment cannot be escaped or ambient loaders injected',()=>{
  for(const env of [{TEMP:'C:/outside'},{LOCALAPPDATA:'C:/outside'},{Path:'C:/outside'},{NODE_OPTIONS:'--require evil'},
    {NSISDIR:'C:/outside'},{__COMPAT_LAYER:'RunAsAdmin'},null,[]]){
    const f=fixture();denied(f,()=>f.policy.prepare(f.context.node,f.npm,{env}));
  }
});

test('cwd and 7zip output drift refuse even with an otherwise known executable',()=>{
  for(const mutate of [f=>[f.context.node,f.npm,{cwd:path.dirname(f.context.root)}],
    f=>[f.context.seven,f.archive,{cwd:f.context.root}],
    f=>[f.context.seven,f.archive.map((x,i)=>i===8?path.join(f.context.root,'escape.7z'):x),{cwd:path.join(f.context.output,'win-unpacked')} ]]){
    const f=fixture();denied(f,()=>f.policy.prepare(...mutate(f)));
  }
});

test('NSIS compiler rejects unbound output, unsupported commands and wrong templates cwd',()=>{
  for(const mutate of [f=>['-WX','-INPUTCHARSET','UTF8','-DTEST=1','-'],
    f=>['-WX','-INPUTCHARSET','UTF8','-XOutFile '+path.join(f.context.root,'escape.exe'),'-'],
    f=>['-WX','-INPUTCHARSET','UTF8','-XExec evil','-XOutFile '+f.context.generator.image,'-']]){
    const f=fixture();denied(f,()=>f.policy.prepare(f.context.nsis,mutate(f),{cwd:f.context.nsisTemplates}));
  }
  const f=fixture();denied(f,()=>f.policy.prepare(f.context.nsis,['-WX','-INPUTCHARSET','UTF8','-XOutFile '+f.context.generator.image,'-'],{cwd:f.context.root}));
});

test('generator requires exact no-argument compatibility and request binding',()=>{
  for(const mutate of [f=>[[],{}],f=>[['/S'],{env:{__COMPAT_LAYER:'RunAsInvoker'}}],f=>[[],{cwd:f.context.output,env:{__COMPAT_LAYER:'RunAsInvoker'}}]]){
    const f=fixture();denied(f,()=>f.policy.prepare(f.context.generator.image,...mutate(f),'execFile'));
  }
  const f=fixture();f.context.generator.requestSha256='short';denied(f,()=>f.policy.prepare(f.context.generator.image,[],{env:{__COMPAT_LAYER:'RunAsInvoker'}},'execFile'));
});

test('changed or missing executable fingerprints refuse before child creation',()=>{
  const changed=fixture();changed.setDrift();denied(changed,()=>changed.policy.prepare(changed.context.node,changed.npm));
  const missing=fixture();delete missing.context.executablePins[missing.context.npmCli];denied(missing,()=>missing.policy.prepare(missing.context.node,missing.npm));
  const f=fixture(),broken=createChildPolicy(f.context,{now:()=>1000,inspectFile:()=>{throw Error('identity unavailable');}});
  assert.throws(()=>broken.prepare(f.context.node,f.npm),/identity unavailable/);assert.throws(()=>broken.assertClean(),/identity unavailable/);
});

test('invalid timeouts and unsupported process methods are sticky refusals',()=>{
  for(const timeout of [0,-1,NaN,Infinity,'100']){const f=fixture();denied(f,()=>f.policy.prepare(f.context.node,f.npm,{timeout}));}
  for(const method of ['fork','exec','spawnSync','execFileSync','execSync']){const f=fixture();denied(f,()=>f.policy.prepare(f.context.node,f.npm,{},method));}
});

test('install wraps asynchronous originals and restores the original adapter exactly',()=>{
  const f=fixture(),calls=[],token={};
  const original=(...args)=>{calls.push(args);return token;};
  const adapter=Object.fromEntries(['spawn','execFile','fork','exec','spawnSync','execFileSync','execSync'].map(k=>[k,original]));
  const before={...adapter},restore=f.policy.install(adapter);
  assert.equal(adapter.spawn(f.context.node,f.npm),token);
  const callback=()=>{};assert.equal(adapter.execFile(f.context.node,f.npm,callback),token);
  assert.equal(calls.length,2);assert.equal(calls[0][2].windowsHide,true);assert.equal(calls[1][3],callback);
  restore();assert.deepEqual(adapter,before);f.policy.assertClean();
});

test('install denies every unsupported API before captured originals are called',()=>{
  for(const name of ['fork','exec','spawnSync','execFileSync','execSync']){
    const f=fixture();let calls=0;const adapter=Object.fromEntries(['spawn','execFile','fork','exec','spawnSync','execFileSync','execSync'].map(k=>[k,()=>{calls++;}]));
    const restore=f.policy.install(adapter);try{denied(f,()=>adapter[name](f.context.node,f.npm));assert.equal(calls,0);}finally{restore();}
  }
});

test('network refusal remains fatal after a library catches it',()=>{
  const f=fixture();try{f.policy.rejectNetwork();}catch{}
  assert.throws(()=>f.policy.assertClean(),/network access prohibited/);
  assert.throws(()=>f.policy.prepare(f.context.node,f.npm),/network access prohibited/);
  assert.equal(f.policy.launches.length,0);
});

test('actual installed builder-util spawn maps npm before cross-spawn and never launches cmd',async t=>{
  const f=fixture(),captured=[],beforeCross=[];
  const originalSpawn=cp.spawn,originalExecFile=cp.execFile;
  cp.spawn=(file,args,options)=>{captured.push({file,args,options});return fakeProcess(f.context.appDir+'\n');};
  cp.execFile=()=>{throw Error('npm-prefix must use spawn');};syncBuiltinESMExports();
  const restorePolicy=f.policy.install(cp);
  t.after(()=>{restorePolicy();cp.spawn=originalSpawn;cp.execFile=originalExecFile;syncBuiltinESMExports();});
  // These are the installed exports, not stand-ins for builder-util or cross-spawn.
  const util=require('builder-util'),cross=require('cross-spawn');
  assert.match(require('builder-util/package.json').version,/^26\.15\.3$/);
  const actualCross=cross.spawn;cross.spawn=(file,args,options)=>{beforeCross.push({file,args});assert.equal(file,f.context.node);assert.deepEqual(args,f.npm);return actualCross(file,args,options);};
  const restoreUtil=f.policy.wrapBuilderUtilities(util);
  t.after(()=>{restoreUtil();cross.spawn=actualCross;});
  const out=await util.spawn('npm',['prefix','-w'],{cwd:f.context.appDir,env:{...f.context.baseEnv}});
  assert.equal(out,f.context.appDir+'\n');assert.equal(beforeCross.length,1);assert.equal(captured.length,1);
  assert.equal(captured[0].file,f.context.node);assert.deepEqual(captured[0].args,f.npm);
  assert.equal(captured[0].options.shell,false);assert.equal(captured[0].options.windowsHide,true);
  assert.equal(captured[0].options.detached,false);assert.deepEqual(captured[0].options.env,f.context.baseEnv);
  assert.equal(f.policy.launches.length,1);assert.equal(f.policy.launches[0].kind,'npm-prefix');f.policy.assertClean();
});

test('actual builder-util wrapper rejects changed npm commands before cross-spawn resolution',async t=>{
  const f=fixture(),util=require('builder-util'),cross=require('cross-spawn');let resolutions=0;
  const previous=cross.spawn;cross.spawn=()=>{resolutions++;throw Error('cross-spawn must not be reached');};
  const restore=f.policy.wrapBuilderUtilities(util);t.after(()=>{restore();cross.spawn=previous;});
  assert.throws(()=>util.spawn('npm',['install'],{cwd:f.context.root}),/unlisted npm command/);
  assert.equal(resolutions,0);assert.equal(f.policy.launches.length,0);assert.throws(()=>f.policy.assertClean(),/unlisted npm command/);
});

// Real stage verifier, using the exact nested property order emitted by
// Python json.dumps(..., sort_keys=True). These fixtures never launch children.
function appStageFixture(t){
  const base=path.resolve(os.tmpdir()),app=fs.mkdtempSync(path.join(base,'books-pack-stage-'));
  const relative=path.relative(base,app);
  assert.ok(relative&&!relative.startsWith('..')&&!path.isAbsolute(relative));
  t.after(()=>fs.rmSync(app,{recursive:true,force:false}));
  fs.mkdirSync(path.join(app,'desktop'));
  fs.writeFileSync(path.join(app,'desktop','main.js'),'first');
  fs.writeFileSync(path.join(app,'package.json'),'{}');
  const manifest=Object.fromEntries(['package.json','desktop/main.js'].map(relative=>{
    const facts=fileFacts(path.join(app,relative));
    return [relative,{sha256:facts.sha256,size:facts.size}];
  }));
  return {app,manifest};
}

test('actual stage verifier accepts Python-sorted nested facts without weakening byte comparison',t=>{
  const {app,manifest}=appStageFixture(t);
  const pythonJson=JSON.stringify(Object.fromEntries(Object.entries(manifest).sort()));
  assert.deepEqual(Object.keys(JSON.parse(pythonJson)['desktop/main.js']),['sha256','size']);
  assert.doesNotThrow(()=>verifyAppStage(app,JSON.parse(pythonJson)));
});

test('actual stage verifier refuses changed bytes including equal-length changes',t=>{
  const {app,manifest}=appStageFixture(t),file=path.join(app,'desktop','main.js');
  for(const body of ['other','longer content']){
    fs.writeFileSync(file,body);
    assert.throws(()=>verifyAppStage(app,manifest),/Private app membership or bytes changed/);
  }
});

test('actual stage verifier refuses missing, extra and renamed members',t=>{
  const {app,manifest}=appStageFixture(t),file=path.join(app,'desktop','main.js');
  fs.unlinkSync(file);
  assert.throws(()=>verifyAppStage(app,manifest),/Private app membership or bytes changed/);
  fs.writeFileSync(file,'first');fs.writeFileSync(path.join(app,'extra.txt'),'extra');
  assert.throws(()=>verifyAppStage(app,manifest),/Private app membership or bytes changed/);
  fs.unlinkSync(path.join(app,'extra.txt'));fs.renameSync(file,path.join(app,'desktop','renamed.js'));
  assert.throws(()=>verifyAppStage(app,manifest),/Private app membership or bytes changed/);
});

test('actual stage verifier refuses malformed or extended fingerprint records',t=>{
  const {app,manifest}=appStageFixture(t),facts=manifest['desktop/main.js'];
  for(const record of [null,[],{}, {size:facts.size}, {sha256:facts.sha256},
    {...facts,size:String(facts.size)}, {...facts,sha256:facts.sha256.toUpperCase()},
    {...facts,extra:true}]){
    assert.throws(()=>verifyAppStage(app,{...manifest,'desktop/main.js':record}),/Private app membership or bytes changed/);
  }
});

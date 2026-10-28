// Proposed hidden-only packaged smoke. Senua must approve this file AND its plan hashes before Futaba runs it.
// Invocation: node hidden-package-smoke.mjs <plan.json> <plan-sha256> <this-file-sha256>
// Does not install, click, type, focus, edit payloads or kill processes by PID/name. Owned Job closes descendants.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import net from 'node:net';
import {spawn,spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {runOwned} from 'file:///C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/bounded-check.mjs';
const SELF=fileURLToPath(import.meta.url),Q='C:/Antigravity Projects/Worktrees/Books Arranger/q230';
const OWNER=Q+'/ownership/node_modules/koffi',REG='C:/Windows/System32/reg.exe';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const norm=p=>path.resolve(p).toLowerCase();
const inside=(p,root)=>norm(p).startsWith(norm(root)+path.sep);
function need(ok,why){if(!ok)throw Error(why);}
function ordinary(p){for(let at=path.resolve(p);;at=path.dirname(at)){need(!fs.lstatSync(at).isSymbolicLink(),'Reparse path refused: '+at);if(path.dirname(at)===at)return;}}
function readPin(p,digest){ordinary(p);const b=fs.readFileSync(p);need(hash(b)===digest,'Pin differs: '+p);return b;}
const worker=process.argv[2]==='--owned-worker';
const args=process.argv.slice(worker?4:2);
need(args.length===3,'Expected plan path, plan SHA256 and helper SHA256');
const [planPath,planSha,selfSha]=args;
need(/^[a-f0-9]{64}$/.test(planSha)&&/^[a-f0-9]{64}$/.test(selfSha),'Bad external pin');
readPin(SELF,selfSha);
need(inside(planPath,Q),'Plan must be owned under q23j');
const p=JSON.parse(readPin(planPath,planSha));
need(p.schema==='books-hidden-package-smoke-v1'&&/^[a-f0-9]{40}$/.test(p.sourceHead)&&/^\d+\.\d+\.\d+$/.test(p.version),'Bad plan identity');
need(p.authorization?.nativeLaunchApproved===true&&p.authorization?.approvedBy==='Sergei','Explicit user native-launch authorization absent; deny activity');
need(inside(p.workDir,Q)&&path.dirname(path.resolve(p.workDir))===path.resolve(Q)&&/^hidden-smoke-[a-f0-9-]{36}$/.test(path.basename(p.workDir)),'Bad unique work directory');
need(inside(p.manifestPath,p.candidateDist),'Manifest must be in accepted candidate dist');
readPin(process.execPath,p.nodeSha256);
if(!worker){
 const nonce=crypto.randomBytes(32).toString('hex');
 const result=await runOwned(process.execPath,[SELF,'--owned-worker',nonce,planPath,planSha,selfSha],{cwd:Q,env:{...process.env,BOOKS_HIDDEN_SMOKE_NONCE:nonce},timeoutMs:600000,koffiRoot:OWNER});
 fs.writeFileSync(Q+'/logs/hidden-package-smoke-result.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({ok:result.ok,code:result.code,closed:result.closed,native:result.native,reason:result.reason}));
 process.exitCode=result.ok&&result.native?.zero?0:1;
}else{
 need(process.env.BOOKS_HIDDEN_SMOKE_NONCE===process.argv[3]&&/^[a-f0-9]{64}$/.test(process.argv[3]),'Owned-worker nonce missing');
 const require=createRequire(import.meta.url),koffi=require(OWNER),u=koffi.load('user32.dll');
 const enumWindows=u.func('bool __stdcall EnumWindows(void *callback, intptr_t param)');
 const visible=u.func('bool __stdcall IsWindowVisible(void *window)');
 const winPid=u.func('uint32_t __stdcall GetWindowThreadProcessId(void *window, _Out_ uint32_t *pid)');
 const foreground=u.func('void * __stdcall GetForegroundWindow()');
 const proto=koffi.proto('bool __stdcall BooksSmokeEnum(void *window, intptr_t param)');
 const ownedPids=new Set();let intrusion='',timer=null,shell=null,socket=null,report={sourceHead:p.sourceHead,version:p.version,workDir:p.workDir,closedByQuit:false};
 const kernel=koffi.load('kernel32.dll');
 const openProcess=kernel.func('void * __stdcall OpenProcess(uint32_t access, bool inherit, uint32_t pid)');
 const closeHandle=kernel.func('bool __stdcall CloseHandle(void *handle)');
 const queryImage=kernel.func('bool __stdcall QueryFullProcessImageNameW(void *process, uint32_t flags, void *buffer, _Inout_ uint32_t *size)');
 let privateAppRoot='';
 function imageOf(pid){const h=openProcess(0x1000,false,pid);need(h,'Cannot read a visible-window process image');try{const buffer=Buffer.alloc(65536),size=[32768];need(queryImage(h,0,buffer,size),'Cannot identify visible-window process image');return buffer.subarray(0,size[0]*2).toString('utf16le');}finally{closeHandle(h);}}
 function matchesPrivate(pid){if(ownedPids.has(pid))return true;return !!privateAppRoot&&inside(imageOf(pid),privateAppRoot);}
 function windowCheck(control=false){let totalVisible=0,witness=0,probeError='';const matched=[];
  const callback=koffi.register((hwnd)=>{try{if(visible(hwnd)){totalVisible++;const pid=[0];winPid(hwnd,pid);if(pid[0]&&!witness)witness=pid[0];if(pid[0]&&matchesPrivate(pid[0]))matched.push(pid[0]);}return true;}catch(e){probeError=e.message;return false;}},koffi.pointer(proto));
  try{const ok=enumWindows(callback,0);need(!probeError,probeError);need(ok,'EnumWindows failed');}finally{koffi.unregister(callback);}
  let foregroundOwned=false;const fg=foreground();if(fg){const pid=[0];winPid(fg,pid);foregroundOwned=pid[0]>0&&matchesPrivate(pid[0]);}
  if(!control&&(matched.length||foregroundOwned))intrusion=matched.length?'Private package-tree process has a visible window':'Private package-tree process took foreground';
  return {totalVisible,witness,matched,foregroundOwned};
 }
 function guard(){need(!intrusion,intrusion);}
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 async function waitFor(fn,ms,label){const end=Date.now()+ms;while(Date.now()<end){guard();const v=await fn();if(v)return v;await sleep(100);}throw Error(label+' timeout');}
 function command(args){const r=spawnSync(REG,args,{windowsHide:true,encoding:null,timeout:5000,maxBuffer:16*1024*1024});need(!r.error&&(r.status===0||r.status===1),'Registry query failed');return {...r,stdout:(r.stdout||Buffer.alloc(0)).toString('latin1')};}
 const trayBase='HKCU\\Control Panel\\NotifyIconSettings',trayFull='HKEY_CURRENT_USER\\Control Panel\\NotifyIconSettings';
 let trayExportNumber=0;
 function traySnapshot(){
  const file=path.join(p.workDir,'tray-snapshot-'+(trayExportNumber++)+'.reg');
  need(!fs.existsSync(file),'Registry export target already exists');
  const r=command(['export',trayBase,file]);need(r.status===0,'Cannot export complete existing tray IDs/types/values');
  ordinary(file);const stat=fs.lstatSync(file);need(stat.isFile()&&stat.size>2&&stat.size<=16*1024*1024,'Registry export size/type refused');
  const bytes=fs.readFileSync(file);need(bytes[0]===255&&bytes[1]===254,'Registry export must be complete UTF-16LE');
  const text=bytes.subarray(2).toString('utf16le');need(text.startsWith('Windows Registry Editor Version 5.00\r\n')&&text.endsWith('\r\n'),'Registry export header/end refused');
  const rows={};let current=null,headers=0;
  for(const line of text.split(/\r?\n/)){
   if(line.startsWith('[')){const match=line.match(/^\[([^\]]+)\]$/);need(match,'Malformed registry export key header');const key=match[1];
    need(key===trayFull||key.startsWith(trayFull+'\\'),'Registry export escaped tray subtree');need(!Object.hasOwn(rows,key),'Duplicate registry export key');
    current=key;rows[current]='';headers++;
   }else if(current)rows[current]+=line+'\n';
   else need(line===''||line==='Windows Registry Editor Version 5.00','Unexpected data before registry export root');
  }
  need(headers===Object.keys(rows).length&&Object.hasOwn(rows,trayFull),'Complete tray export positive control failed');
  return rows;
 }
 function trayExecutable(values){
  // Compare every value/type as raw exported text. Decode only ExecutablePath for exact own-EXE ownership.
  const logical=String(values).replace(/\\\n[ \t]*/g,'');const match=logical.match(/^"ExecutablePath"=(.+)$/im);if(!match)return '';
  const encoded=match[1];if(encoded.startsWith('"')){const value=JSON.parse(encoded);need(typeof value==='string','ExecutablePath type refused');return value;}
  const hex=encoded.match(/^hex\((?:1|2)\):([0-9a-f,\s]*)$/i);if(!hex)return '';
  const compact=hex[1].replace(/\s/g,'');need(/^(?:[0-9a-f]{2},)*[0-9a-f]{2},?$/i.test(compact),'Malformed exported ExecutablePath bytes');
  const data=Buffer.from(compact.replace(/,/g,''),'hex');need(data.length%2===0,'Odd UTF-16 ExecutablePath');return data.toString('utf16le').replace(/\0+$/,'');
 }
 function trayKeys(exe,snapshot=traySnapshot()){return Object.keys(snapshot).filter(key=>/^HKEY_CURRENT_USER\\Control Panel\\NotifyIconSettings\\\d+$/.test(key)&&trayExecutable(snapshot[key])&&norm(trayExecutable(snapshot[key]))===norm(exe));}
 function existingTrayUnchanged(before,after){for(const [key,values] of Object.entries(before))need(Object.hasOwn(after,key)&&after[key]===values,'Preexisting tray key was changed or removed; preserve and STOP: '+key);}
 function pins(root,expected){ordinary(root);const seen=[];function walk(dir,rel=''){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const name=rel+e.name,full=path.join(dir,e.name);need(!e.isSymbolicLink(),'Payload link refused');if(e.isDirectory())walk(full,name+'/');else{need(e.isFile()&&Object.hasOwn(expected,name),'Unexpected payload file '+name);const pin=expected[name],b=fs.readFileSync(full);need(b.length===pin.size&&hash(b)===pin.sha256,'Payload pin differs '+name);seen.push(name);}}}walk(root);need(seen.length===Object.keys(expected).length,'Missing payload files');}
 function freePort(){return new Promise((resolve,reject)=>{const s=net.createServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const port=s.address().port;s.close(()=>port===5210||port===5212?freePort().then(resolve,reject):resolve(port));});});}
 const finish=child=>new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',(code,signal)=>resolve({code,signal}));});
 function launch(exe,argv,env){const child=spawn(exe,argv,{cwd:path.dirname(exe),env,windowsHide:true,stdio:['ignore','pipe','pipe']});child.stdout.on('data',()=>{});child.stderr.on('data',b=>{report.lastStderr=(report.lastStderr||'').slice(-3000)+b.toString().slice(-3000);});if(child.pid)ownedPids.add(child.pid);return child;}
 let privateArgs=[],env={},exe='',quitTried=false,preTray=[],beforeTray=null;
 async function control(flag){need(shell&&shell.exitCode===null,'Original package already exited');const child=launch(exe,[...privateArgs,flag],env),done=finish(child);const result=await Promise.race([done,sleep(10000).then(()=>{throw Error(flag+' controller timeout');})]);need(result.code===0&&result.signal===null,flag+' controller failed');}
 try{
  const manifest=JSON.parse(readPin(p.manifestPath,p.manifestSha256));
  need(manifest.source_head===p.sourceHead&&manifest.version===p.version&&manifest.payload?.verified===true&&manifest.payload.installer_equivalent===true,'Accepted artifact identity differs');
  for(const item of manifest.artifacts){const file=path.resolve(p.candidateDist,item.path);need(inside(file,p.candidateDist),'Artifact escapes dist');readPin(file,item.sha256);}
  const original=path.resolve(p.candidateDist,manifest.unpacked);need(inside(original,p.candidateDist),'Unpacked escapes dist');pins(original,manifest.payload.files);
  need(!fs.existsSync(p.workDir),'Unique work directory already exists');fs.mkdirSync(p.workDir);ordinary(p.workDir);
  const app=path.join(p.workDir,'app'),home=path.join(p.workDir,'home');fs.cpSync(original,app,{recursive:true,errorOnExist:true,force:false});pins(app,manifest.payload.files);privateAppRoot=app;
  const dirs=Object.fromEntries(['profile','data','local','roaming','temp','Audiobooks','Podcasts','Ebooks','Sorted'].map(name=>[name,path.join(home,name)]));for(const d of Object.values(dirs))fs.mkdirSync(d,{recursive:true});
  const roots=path.join(home,'roots.json');fs.writeFileSync(roots,JSON.stringify({Audiobooks:dirs.Audiobooks,Podcasts:dirs.Podcasts,Ebooks:dirs.Ebooks}),{flag:'wx'});
  exe=path.join(app,'Books Arranger.exe');beforeTray=traySnapshot();fs.writeFileSync(path.join(p.workDir,'tray-before.json'),JSON.stringify(beforeTray),{flag:'wx'});preTray=trayKeys(exe,beforeTray);need(preTray.length===0,'Preexisting unique-exe tray record; preserve and STOP');
  const enginePort=await freePort();let debugPort=await freePort();for(let tries=0;debugPort===enginePort&&tries<16;tries++)debugPort=await freePort();need(enginePort!==debugPort,'Engine and CDP ports must differ');
  env={...process.env,LOCALAPPDATA:dirs.local,APPDATA:dirs.roaming,TEMP:dirs.temp,TMP:dirs.temp,USERPROFILE:home};for(const key of Object.keys(env))if(/^ELECTRON_|^(NODE_OPTIONS|NODE_PATH|PYTHONHOME|PYTHONPATH)$/.test(key))delete env[key];
  privateArgs=['--start-hidden','--quiet-errors','--catalog-mode=new','--data-dir='+dirs.data,'--roots-json='+roots,'--shell-profile='+dirs.profile,'--port='+enginePort];
  const witness=windowCheck(true);need(witness.totalVisible>0&&witness.witness>0,'No existing visible-window positive control; STOP');ownedPids.add(witness.witness);let matched;try{matched=windowCheck(true);}finally{ownedPids.delete(witness.witness);}need(matched.matched.includes(witness.witness),'Visible PID-matching positive control failed');report.visiblePositiveControl={visibleCount:witness.totalVisible,matchedPid:witness.witness};
  shell=launch(exe,[...privateArgs,'--remote-debugging-address=127.0.0.1','--remote-debugging-port='+debugPort],env);const shellDone=finish(shell);
  timer=setInterval(()=>{try{windowCheck();}catch(e){intrusion=e.message;}},100);
  const targets=await waitFor(async()=>{try{need(shell.exitCode===null,'Package exited while loading');const r=await fetch('http://127.0.0.1:'+debugPort+'/json/list',{signal:AbortSignal.timeout(1500)});const t=await r.json();return t.find(x=>x.type==='page'&&x.url.startsWith('http://127.0.0.1:'+enginePort+'/'));}catch{return false;}},60000,'Hidden packaged page');
  socket=new WebSocket(targets.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});let id=0;const waiting=new Map();socket.onmessage=event=>{const m=JSON.parse(event.data);if(waiting.has(m.id)){waiting.get(m.id)(m);waiting.delete(m.id);}};
  async function evaluate(expression){const n=++id;const answer=await Promise.race([new Promise(resolve=>{waiting.set(n,resolve);socket.send(JSON.stringify({id:n,method:'Runtime.evaluate',params:{expression,awaitPromise:true,returnByValue:true}}));}),sleep(5000).then(()=>{throw Error('Hidden renderer evaluation timeout');})]);need(!answer.error&&!answer.result?.exceptionDetails,'Renderer evaluation failed');return answer.result.result.value;}
  const ready=await waitFor(async()=>{try{const r=await evaluate('(async()=>({status:await window.booksDesktop.status(),text:document.body.innerText,origin:location.origin}))()');return r.status.engineVersion===p.version&&r.text.includes(p.version)?r:false;}catch{return false;}},30000,'Displayed package version');
  guard();report.displayedVersion=p.version;report.engineVersion=ready.status.engineVersion;report.rendererOrigin=ready.origin;
  await control('--close-window');await sleep(300);guard();need(shell.exitCode===null,'Window close incorrectly quit tray tool');
  need((await evaluate('window.booksDesktop.status()')).engineVersion===p.version,'Engine did not survive hidden window close');report.windowClose='hidden; shell and engine remain running';
  quitTried=true;await control('--quit');const ended=await Promise.race([shellDone,sleep(30000).then(()=>{throw Error('Tray Quit did not exit package');})]);need(ended.code===0&&ended.signal===null,'Package did not exit normally through Quit');report.closedByQuit=true;
  pins(app,manifest.payload.files);report.payloadUnchanged=true;
 }catch(error){report.error=error.stack;throw error;}
 finally{
  if(shell&&shell.exitCode===null&&!quitTried){try{quitTried=true;await control('--quit');await waitFor(()=>shell.exitCode!==null,10000,'Failure cleanup Quit');}catch(e){report.cleanupError=e.message;}}
  if(timer)clearInterval(timer);try{socket?.close();}catch{}
  // Preserve new records for separate same-handle cleanup after normal Quit; never mutate registry here.
  if(exe&&shell&&shell.exitCode!==null&&preTray.length===0&&beforeTray){try{
    const after=traySnapshot(),keys=trayKeys(exe,after);
    report.ownTrayKeysPending=keys;report.trayCleanup='Pending separately reviewed same-handle cleanup; no registry mutation';
    existingTrayUnchanged(beforeTray,after);
    for(const key of keys){
     need(!Object.hasOwn(beforeTray,key),'Refuse to adopt any preexisting tray ID');
     need(/^HKEY_CURRENT_USER\\Control Panel\\NotifyIconSettings\\\d+$/.test(key),'Tray key scope differs');
    }
    report.removedOwnTrayKeys=0;const final=traySnapshot();existingTrayUnchanged(beforeTray,final);
    need(JSON.stringify(trayKeys(exe,final))===JSON.stringify(keys),'Pending own tray key set changed; preserve and STOP');
   }catch(e){report.cleanupError=e.message;}}

  report.intrusion=intrusion||null;console.log('HIDDEN_PACKAGE_SMOKE '+JSON.stringify(report));
  if(report.cleanupError||intrusion)throw Error(report.cleanupError||intrusion);
 }
}

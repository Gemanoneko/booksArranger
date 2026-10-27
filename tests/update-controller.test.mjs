import test from 'node:test';import assert from 'node:assert/strict';import {EventEmitter} from 'node:events';import {createRequire} from 'node:module';import fs from 'node:fs';import vm from 'node:vm';const {UpdateController}=createRequire(import.meta.url)('../desktop/update-controller.js');
// 0.22.1 (ruling 27; Judy's 0.22.1 UX spec, section 2). A fake provider and a fake clock: each sleep advances it; a
// 30 s attempt bound only fires when GitHub is black-holed (otherwise the provider answers first). No real requests.
const START=new Date(2026,9,25,21,4,0).getTime();
function fixture(){const provider=new EventEmitter();const f={provider,seen:[],states:[],log:[],clock:START,blackHole:false};
 provider.checkForUpdates=async()=>{provider.emit('update-available',{version:'0.22.2'});return {};};
 provider.downloadUpdate=async()=>{provider.emit('download-progress',{percent:42.4});provider.emit('update-downloaded',{version:'0.22.2'});};
 provider.downloadedUpdateHelper={file:'C:/owned/update.exe',downloadedFileInfo:{sha512:'checksum',isAdminRightsRequired:false}};
 f.lease={isAlive:()=>true,close:async()=>f.seen.push('close')};
 f.sleep=async ms=>{f.clock+=ms;if(ms===30000&&!f.blackHole)await new Promise(()=>{});};
 f.controller=new UpdateController({provider,packaged:true,version:'0.22.1',notify:v=>f.states.push(v),now:()=>f.clock,sleep:f.sleep,log:line=>f.log.push(line),
  acquireArtifact:async()=>{f.seen.push('lease');return f.lease;},parkEngine:async()=>{f.seen.push('park');},
  install:async()=>{f.seen.push('install while '+f.controller.value.install.phase);},restartEngine:async()=>{f.seen.push('old engine started');}});
 return f;}
async function ready(f){await f.controller.check();await f.controller.download();assert.equal(f.controller.value.ready,true,'positive control: downloaded and verified');}
const typed=(cause,extra={})=>Object.assign(new Error('fixture '+cause),{updateCause:cause},extra);
// The page's pure helpers, run in their own realm; answers come back as plain values.
function page(){const context={window:{},console};vm.createContext(context);vm.runInContext(fs.readFileSync(new URL('../web/desktop-ui.js',import.meta.url),'utf8'),context);
 return Object.fromEntries(Object.entries(context.booksUpdateText).map(([key,fn])=>[key,(...args)=>JSON.parse(JSON.stringify(fn(...args)))]));}

test('restart holds the installer from before the engine stops until the installer starts',async()=>{const f=fixture();await ready(f);await f.controller.restart();
 assert.deepEqual(f.seen,['lease','park','install while installing','close']);assert.equal(f.provider.autoInstallOnAppQuit,false);assert.equal(f.provider.autoDownload,false);});
test('GitHub black-holed: 3 tries of 30 s, 5 s and 15 s apart, then its own plain line',{timeout:3000},async()=>{const f=fixture();f.blackHole=true;let calls=0;
 f.provider.checkForUpdates=()=>{calls++;f.provider.checkForUpdatesPromise='stuck';return new Promise(()=>{});};
 await f.controller.check();const check=f.controller.value.check;
 assert.equal(calls,3);assert.equal(f.clock-START,3*30000+5000+15000);assert.equal(f.provider.checkForUpdatesPromise,null,'each try sends a new request, not the stuck one');
 assert.deepEqual([check.phase,check.cause,check.at],['failed','no_answer','21:05']);
 assert.deepEqual(f.states.filter(v=>v.check.phase==='retrying').map(v=>v.check.attempt),[2,3]);
 assert(f.log.length===3&&!JSON.stringify(f.controller.value).includes('No answer in'),'raw text stays in the log');});
test('no internet and a GitHub error fail at once, each with its cause',async()=>{for(const [error,cause,code] of [[new Error('net::ERR_INTERNET_DISCONNECTED'),'no_internet',0],[Object.assign(new Error('HttpError: 503 Service Unavailable'),{statusCode:503}),'github_error',503]]){
 const f=fixture();let calls=0;f.provider.checkForUpdates=async()=>{calls++;throw error;};await f.controller.check();
 assert.equal(calls,1);assert.deepEqual([f.controller.value.check.cause,f.controller.value.check.code],[cause,code]);assert(!JSON.stringify(f.controller.value).includes('ERR_INTERNET'),'raw text stays in the log');assert(f.log.length);}});
test('a check answers up to date or available, with the time',async()=>{const f=fixture();await f.controller.check();assert.deepEqual([f.controller.value.check.phase,f.controller.value.check.at,f.controller.value.available],['available','21:04','0.22.2']);
 const g=fixture();g.provider.checkForUpdates=async()=>{g.provider.emit('update-not-available',{});};await g.controller.check();assert.equal(g.controller.value.check.phase,'current');});
test('a failed install never shows up as a check result',async()=>{const f=fixture();await ready(f);const before=f.controller.value.check;f.controller.parkEngine=async()=>{throw typed('bound',{waiting:[{kind:'scan'}]});};
 await f.controller.restart();assert.deepEqual(f.controller.value.check,before);assert.deepEqual([f.controller.value.install.phase,f.controller.value.install.cause],['failed','bound']);
 await f.controller.check();assert.equal(f.controller.value.install.cause,'bound','a new check clears only the check line');assert.equal(f.controller.value.showInstaller,false,'Show installer file goes with a new check');});
test('download: progress, ready, and every typed failure',async()=>{const f=fixture();await f.controller.check();const progress=[];f.controller.notify=v=>progress.push(v.download.phase+':'+Math.round(v.download.progress));
 await f.controller.download();assert.deepEqual(progress,['downloading:0','downloading:42','ready:100']);
 for(const [message,cause] of [['sha512 checksum mismatch, expected x','checksum'],['ENOSPC: no space left on device','disk_full'],['net::ERR_CONNECTION_RESET','dropped'],['something else','other']]){
  const g=fixture();await g.controller.check();g.provider.downloadUpdate=async()=>{throw new Error(message);};await g.controller.download();assert.deepEqual([g.controller.value.download.phase,g.controller.value.download.cause,g.controller.value.ready],['failed',cause,false]);}});
test('missing checksum and admin installer cannot become ready',async()=>{for(const [bad,cause] of [[{sha512:null},'checksum'],[{sha512:'x',isAdminRightsRequired:true},'other']]){const f=fixture();f.provider.downloadedUpdateHelper.downloadedFileInfo=bad;await f.controller.check();await f.controller.download();
 assert.equal(f.controller.ready,null);assert.deepEqual([f.controller.value.download.phase,f.controller.value.download.cause],['failed',cause]);}});
test('the installer would not start: the old engine starts again, and the line and Show installer file name the file',async()=>{const f=fixture();await ready(f);f.controller.install=async()=>{throw typed('installer_blocked');};
 await f.controller.restart();assert.deepEqual(f.seen,['lease','park','old engine started','close']);const value=f.controller.value;
 assert.deepEqual([value.install.cause,value.showInstaller,value.installerPath,value.ready],['installer_blocked',true,'C:/owned/update.exe',true]);});
test('Cancel update while it waits: no installer, no engine restart, the lease is released',async()=>{const f=fixture();await ready(f);
 f.controller.parkEngine=async({progress,cancelRequested})=>{progress({phase:'pausing',waiting:[{kind:'conversion',title:'Fixture'}],elapsed:12,safe_seconds:90});assert.equal(f.controller.value.canCancel,true);assert.equal(f.controller.cancel(),true);assert.equal(cancelRequested(),true);throw typed('cancelled');};
 await f.controller.restart();assert.deepEqual(f.seen,['lease','close']);assert.deepEqual([f.controller.value.install.phase,f.controller.value.canCancel,f.controller.value.busy.install],['cancelled',false,false]);});
// Futaba's 0.22.2 QA, m-1: an idle engine ends for the update in under a second; a Cancel pressed meanwhile was answered
// (true) and the installer still ran.
test('Cancel pressed while an idle engine already ends for the update: no installer, the old engine starts again',async()=>{
 const run=async stopped=>{const f=fixture();await ready(f);
  f.controller.parkEngine=async({progress,cancelRequested})=>{progress({phase:'pausing',waiting:[],elapsed:0,safe_seconds:90,stopped});
   assert.equal(f.controller.cancel(),true,'answered at the press');assert.equal(cancelRequested(),true);};  // then the engine exits: park resolves
  await f.controller.restart();return f;};
 let f=await run([]);
 assert.deepEqual(f.seen,['lease','old engine started','close'],'never the installer');
 assert.deepEqual([f.controller.value.install.phase,f.controller.value.install.cause,f.controller.value.canCancel,f.controller.value.busy.install,f.controller.value.ready],['cancelled','cancelled',false,false,true]);
 assert.equal(page().installLine(f.controller.value).text,'Update cancelled. Books Arranger is running as before.');
 f=await run(['automatic']);
 assert.deepEqual(f.controller.value.install.problems,[{kind:'automatic',cause:'engine_ended'}],'what the ended engine had stopped is named');
 // Control: no Cancel, the same park: the installer runs.
 const g=fixture();await ready(g);g.controller.parkEngine=async({progress})=>{progress({phase:'pausing',waiting:[],elapsed:0,safe_seconds:90,stopped:[]});};
 await g.controller.restart();assert.deepEqual(g.seen,['lease','install while installing','close']);});
test('a tampered artifact never stops the engine and asks for a new download',async()=>{const f=fixture();await ready(f);f.controller.acquireArtifact=async()=>{throw new Error('checksum changed');};
 await f.controller.restart();assert(!f.seen.includes('park'));assert.deepEqual([f.controller.value.install.cause,f.controller.value.ready],['checksum',false]);});
test('verification that runs out of time keeps the download for another try',async()=>{const f=fixture();await ready(f);f.controller.acquireArtifact=async()=>{throw new Error('Installer integrity check timed out');};
 await f.controller.restart();assert.deepEqual([f.controller.value.install.cause,f.controller.value.ready],['verify_timeout',true]);});
test('lease loss after the engine stopped: no installer, and the old engine starts again',async()=>{let alive=true;const f=fixture();await ready(f);f.lease.isAlive=()=>alive;f.controller.parkEngine=async()=>{alive=false;};
 await f.controller.restart();assert(!f.seen.some(s=>s.startsWith('install')));assert(f.seen.includes('old engine started'));assert.equal(f.controller.value.install.cause,'checksum');});
test('an engine that exits unsafely is started again; one that cannot be started says so',async()=>{const f=fixture();await ready(f);f.controller.parkEngine=async()=>{throw typed('engine_exit');};
 f.controller.restartEngine=async()=>{throw new Error('port taken');};await f.controller.restart();assert.equal(f.controller.value.install.cause,'engine_restart');});
test('dev build says updates work only in the installed app and never asks GitHub',async()=>{const f=fixture();let calls=0;f.controller.packaged=false;f.provider.checkForUpdates=async()=>calls++;
 await f.controller.check();assert.equal(calls,0);assert.equal(f.controller.value.check.phase,'dev');});

test('page: the controller records read as their lines (black-holed GitHub, dev build)',{timeout:3000},async()=>{const f=fixture();f.blackHole=true;f.provider.checkForUpdates=()=>new Promise(()=>{});await f.controller.check();
 assert.equal(page().checkLine(f.controller.value),"Couldn't check for updates: GitHub didn't answer after 3 tries (tried 21:05). Check your internet connection, then try again. Nothing changed.");
 const g=fixture();g.controller.packaged=false;await g.controller.check();assert.equal(page().checkLine(g.controller.value),'Updates work only in the installed app.');});
test('page: every Check, Download and Install line reads as Judy wrote it',()=>{const t=page();const base={version:'0.22.1',available:'0.22.2',ready:false,check:{},download:{},install:{}};
 const check=c=>t.checkLine({...base,check:c}),download=d=>t.downloadLine({...base,download:d}),install=(i,extra={})=>t.installLine({...base,...extra,install:{at:'21:07',...i}}).text;
 assert.equal(check({phase:'idle'}),'Books Arranger 0.22.1. Not checked yet.');assert.equal(check({phase:'checking'}),'Checking for updates…');
 assert.equal(check({phase:'retrying',attempt:2}),'Checking for updates… no answer yet, trying again (try 2 of 3).');
 assert.equal(check({phase:'current',at:'21:04'}),'Books Arranger 0.22.1 is up to date (checked 21:04).');assert.equal(check({phase:'available',at:'21:04',version:'0.22.2'}),'Version 0.22.2 is available (checked 21:04).');
 assert.equal(check({phase:'failed',cause:'no_internet',at:'21:04'}),"Couldn't check for updates: no internet connection (tried 21:04). Connect, then try again. Nothing changed.");
 assert.equal(check({phase:'failed',cause:'github_error',code:503,at:'21:04'}),"Couldn't check for updates: GitHub returned an error, 503 (tried 21:04). Try again later. Nothing changed.");
 assert.equal(check({phase:'failed',cause:'other',at:'21:04'}),"Couldn't check for updates (tried 21:04). Try again later. Nothing changed.");
 assert.equal(download({phase:'downloading',progress:42.4}),'Downloading version 0.22.2… 42%');assert.equal(t.downloadLine({...base,ready:true}),'Version 0.22.2 is downloaded and verified. Ready to install.');
 assert.equal(download({phase:'failed',cause:'dropped',at:'21:05'}),"Couldn't download version 0.22.2: the connection dropped (tried 21:05). Press Download update to try again.");
 assert.equal(download({phase:'failed',cause:'checksum',at:'21:05'}),"Couldn't use the download: it failed its checksum check, so it was discarded (tried 21:05). Press Download update to try again.");
 assert.equal(download({phase:'failed',cause:'disk_full',at:'21:05'}),"Couldn't download version 0.22.2: not enough disk space (tried 21:05). Free some space, then press Download update.");
 assert.equal(download({phase:'failed',cause:'other',at:'21:05'}),"Couldn't download version 0.22.2 (tried 21:05). Press Download update to try again.");
 assert.equal(install({phase:'cancelled'}),'Update cancelled. Books Arranger is running as before.');
 assert.equal(install({phase:'failed',cause:'bound',waiting:[{kind:'conversion',title:'Лабиринты Ехо 3'}]}),'Update cancelled: the conversion of Лабиринты Ехо 3 did not stop in time (tried 21:07). Books Arranger is running as before. Press Restart to update to try again, or choose Quit Books Arranger in the tray, then run the installer.','M2: no number; the engine gives up at 150 s, the shell at 180 s');
 assert(!fs.readFileSync(new URL('../web/desktop-ui.js',import.meta.url),'utf8').includes('3 minutes'),'M2: the bound has no number anywhere in the page');
 assert.equal(install({phase:'failed',cause:'engine_exit'}),'The engine stopped during the update and was started again (tried 21:07). It is loading now. Press Restart to update to try again.','N3');
 assert.equal(install({phase:'failed',cause:'refused'}),'Update cancelled (tried 21:07). Books Arranger is running as before. Press Restart to update to try again.','the generic line stays for refused, blocked and other');
 const blocked=t.installLine({...base,installerPath:'C:/owned/update.exe',install:{phase:'failed',cause:'installer_blocked',at:'21:07'}});
 assert.deepEqual([blocked.text,blocked.path],["The installer couldn't start (tried 21:07). Windows or your antivirus may have blocked it. Books Arranger is running again on 0.22.1. Run the installer yourself:",'C:/owned/update.exe']);
 assert.equal(install({phase:'failed',cause:'checksum'}),"Update cancelled: the downloaded installer is missing or doesn't match its checksum (tried 21:07). Check for updates, then download it again.");
 assert.equal(install({phase:'failed',cause:'verify_timeout'}),"Update cancelled: the downloaded installer couldn't be verified in time (tried 21:07). Press Restart to update to try again.");
 assert.equal(install({phase:'failed',cause:'engine_restart'}),"Books Arranger couldn't restart its engine (tried 21:07). Choose Quit Books Arranger in the tray, then open it again.");
 for(const file of ['../web/desktop-ui.js','../desktop/update-controller.js','../desktop/engine-update.js'])assert(!fs.readFileSync(new URL(file,import.meta.url),'utf8').includes('Request timed out'),'"Request timed out" appears nowhere: '+file);});
test('page: phase lines, with the seconds counter apart from the live text',()=>{const t=page();const u=i=>t.phaseLine({available:'0.22.2',install:{safe:90,elapsed:0,waiting:[],critical:[],...i}});
 assert.deepEqual(u({phase:'starting'}),{text:'Starting the update…',counter:''});
 assert.deepEqual(u({phase:'pausing',elapsed:12.6,waiting:[{kind:'conversion',title:'Fixture'},{kind:'scan'},{kind:'research'},{kind:'approval'}]}),{text:'Stopping safely for the update. Waiting for the conversion of Fixture and the library scan and 2 more to reach a safe point…',counter:'(12 s of 90 s)'});
 assert.deepEqual(u({phase:'pausing',waiting:[{kind:'critical',title:'a tag edit'}],critical:['a tag edit']}),{text:'Finishing a tag edit first, so nothing is left half-done. This takes a few seconds.',counter:''});
 assert.equal(u({phase:'forcing',waiting:[{kind:'conversion',title:'Fixture'}]}).text,"The conversion of Fixture didn't reach a safe point in 90 s. Stopping it now; continue it with Resume audiobook jobs.");  // Judy 0.22.2 6.3 (m-11)
 assert.equal(u({phase:'forcing',waiting:[{kind:'approval'}]}).text,"An approval didn't reach a safe point in 90 s. Stopping it now; start it again after the update.");
 // N2: series backfill and optional-field lookups run by themselves, so they are "background lookups" and need no restart.
 assert.equal(u({phase:'pausing',waiting:[{kind:'lookups'}]}).text,'Stopping safely for the update. Waiting for background lookups to reach a safe point…');
 assert.equal(u({phase:'forcing',waiting:[{kind:'lookups'}]}).text,"Background lookups didn't reach a safe point in 90 s. Stopping them now; they continue by themselves after the update."); assert.equal(u({phase:'updating'}).text,'Stopping the engine now. Saved work is kept.');
 assert.equal(u({phase:'installing'}).text,'Installing 0.22.2… No installer window opens. Books Arranger reopens by itself and shows its loading progress.');});
test('page: the confirm names the running work; idle starts at once; unknown work confirms',()=>{const t=page();
 assert.deepEqual(t.workLines({busy:{converting:true,current_title:'Лабиринты Ехо 3',scanning:true,automatic:'Running'},queued_actions:2}).lines,['Converting Лабиринты Ехо 3. It stops. Continue it with Resume audiobook jobs.','Scanning the library. It stops. Continue it with Resume scanning.','Automatic processing stops. Press Start automatic processing to continue.','2 queued actions are dropped. Press them again afterwards.']);
 assert.deepEqual(t.workLines({busy:{converting:false,scanning:false,automatic:'Idle'},queued_actions:[{id:1}]}).lines,['1 queued action is dropped. Press it again afterwards.']);
 assert.deepEqual(t.workLines({busy:{converting:false,scanning:false,automatic:'Idle'}}),{known:true,lines:[]},'no queue count in status: no queue line');
 assert.equal(t.workLines({busy:null}).known,false);});
test('page: buttons have real tooltips, busy ones use aria-disabled, and show only when they apply',()=>{const t=page();const base={version:'0.22.1',available:'0.22.2',ready:false,packaged:true,busy:{},check:{},download:{},install:{},canCancel:false,showInstaller:false};
 const idle=t.buttons(base,{busy:{converting:false,scanning:false,automatic:'Idle'}});
 for(const [key,b] of Object.entries(idle))assert.notEqual(b.title,b.face,key+' tooltip is a sentence, not the face');
 assert.deepEqual([idle.download.hidden,idle.restart.hidden,idle.cancel.hidden,idle.installer.hidden],[false,true,true,true]);
 const readyIdle=t.buttons({...base,ready:true},{busy:{converting:false,scanning:false,automatic:'Idle'}}).restart;
 assert.equal(readyIdle.title,'Install version 0.22.2 now. Books Arranger closes, updates and reopens by itself. No installer window opens.');assert.equal(readyIdle.busy,false,'no idle gate');
 assert.equal(t.buttons({...base,ready:true},{busy:{converting:true}}).restart.title,'Install version 0.22.2 now. Running work stops safely and restarts afterwards. Your source files are not touched. You confirm first.');
 const updating=t.buttons({...base,ready:true,busy:{install:true},canCancel:true},{});
 assert.deepEqual([updating.restart.face,updating.restart.busy,updating.restart.title,updating.cancel.hidden,updating.cancel.title],['Updating…',true,'Updating Books Arranger…',false,'Stop the update. Books Arranger keeps running as before.']);
 const checking=t.buttons({...base,busy:{check:true}},{}).check;assert.deepEqual([checking.face,checking.busy,checking.title],['Checking…',true,'Checking for updates…']);
 const downloading=t.buttons({...base,busy:{download:true},download:{progress:7}},{}).download;assert.deepEqual([downloading.face,downloading.title],['Downloading… 7%','Downloading version 0.22.2…']);});
// Senua's 0.22.1 review, W3: Cancel, the engine's bound or a failed close that could not start the stopped work again
// says what stays stopped and what to press, never "running as before".
test('the Install line names what did not start again after Cancel, the bound or a failed close',async()=>{const t=page();const base={version:'0.22.1',available:'0.22.2',ready:false,check:{},download:{},install:{}};
 const line=i=>t.installLine({...base,install:{at:'21:07',...i}});
 assert.deepEqual(line({phase:'cancelled',problems:[{kind:'automatic',cause:'still_stopping'}]}),{text:"Update cancelled (tried 21:07). Automatic processing didn't start again. Press Start automatic processing to continue.",failed:true});
 assert.deepEqual(line({phase:'cancelled',problems:[]}),{text:'Update cancelled. Books Arranger is running as before.',failed:false},'everything started again: as before');
 assert.equal(line({phase:'cancelled',problems:[{kind:'conversion',cause:'refused'},{kind:'scan',cause:'still_stopping'},{kind:'lookups',cause:'still_stopping'},{kind:'lookups',cause:'refused'}]}).text,
  "Update cancelled (tried 21:07). The audiobook jobs, the library scan and background lookups didn't start again. Press Resume audiobook jobs to continue. Continue the scan with Resume scanning. Background lookups start again by themselves the next time Books Arranger opens.");
 assert.equal(line({phase:'failed',cause:'bound',waiting:[{kind:'conversion',title:'Fixture'}],problems:[{kind:'conversion',cause:'still_stopping'}]}).text,
  "Update cancelled: the conversion of Fixture did not stop in time (tried 21:07). The audiobook jobs didn't start again. Press Resume audiobook jobs to continue. Press Restart to update to try again, or choose Quit Books Arranger in the tray, then run the installer.");
 assert.equal(line({phase:'failed',cause:'blocked',problems:[{kind:'automatic',cause:'refused'}]}).text,
  "Update cancelled (tried 21:07). Automatic processing didn't start again. Press Start automatic processing to continue. Press Restart to update to try again.");
 assert.equal(line({phase:'failed',cause:'blocked',problems:[{kind:'unknown',cause:'refused'}]}).text,'Update cancelled (tried 21:07). Books Arranger is running as before. Press Restart to update to try again.','an unknown kind is never shown');
 // The controller keeps the typed list from the shell, drops the engine's wording, and a new restart clears it.
 const f=fixture();await ready(f);f.controller.parkEngine=async()=>{throw typed('cancelled',{resumeProblems:[{kind:'scan',cause:'refused'}]});};
 await f.controller.restart();assert.deepEqual(f.controller.value.install.problems,[{kind:'scan',cause:'refused'}]);
 assert.equal(page().installLine(f.controller.value).text,"Update cancelled (tried 21:04). The library scan didn't start again. Continue the scan with Resume scanning.");
 f.controller.parkEngine=async()=>{};await f.controller.restart();assert.deepEqual(f.controller.value.install.problems,[]);});
// Senua's 0.22.1 review, W5: the engine's exit after the shell gave up on its ending (engine_stuck) starts the old engine
// again and says so with N3's line; it never closes the app.
test('a late exit of an engine ending for the update starts the old engine again, with the engine_exit line',async()=>{const f=fixture();await ready(f);
 f.controller.parkEngine=async()=>{throw typed('engine_stuck');};await f.controller.restart();assert.equal(f.controller.value.install.cause,'engine_stuck');assert(!f.seen.includes('old engine started'));
 await f.controller.lateEngineExit();assert(f.seen.includes('old engine started'));
 assert.deepEqual([f.controller.value.install.phase,f.controller.value.install.cause],['failed','engine_exit']);
 assert.equal(page().installLine(f.controller.value).text,'The engine stopped during the update and was started again (tried 21:04). It is loading now. Press Restart to update to try again.');
 const g=fixture();g.controller.restartEngine=async()=>{throw new Error('port taken');};await g.controller.lateEngineExit();assert.equal(g.controller.value.install.cause,'engine_restart');});
// Senua's 0.22.1 review, W7: electron-updater 6.8.9's NsisUpdater.doInstall (node_modules/electron-updater/out/
// NsisUpdater.js:131-141) answers a failed spawn by itself, after the shell has started the old engine again. The
// provider below does exactly what that code does with its spawn's rejection.
function nsisLike(spawnError){const provider={calls:[],quitAndInstallCalled:false,installerPath:'C:/owned/update.exe'};
 provider.spawnLog=async function(cmd){this.calls.push('spawn '+cmd);if(spawnError&&!cmd.endsWith('elevate.exe'))throw Object.assign(new Error('spawn failed'),{code:spawnError});return true;};
 provider.quitAndInstall=function(){this.quitAndInstallCalled=true;
  const elevate=()=>{this.spawnLog('C:/resources/elevate.exe',[this.installerPath]).catch(()=>{});this.calls.push('elevate.exe');};
  this.spawnLog(this.installerPath,['--updated','/S','--force-run']).catch(e=>{if(e.code==='UNKNOWN'||e.code==='EACCES')elevate();else if(e.code==='ENOENT')this.calls.push('shell.openPath '+this.installerPath);else this.calls.push('dispatchError');});};
 return provider;}
test('a failed installer start never lets the updater start its own fallback; a good start goes through',async()=>{const {holdInstallerSpawn}=createRequire(import.meta.url)('../desktop/update-controller.js');
 const settle=()=>new Promise(resolve=>setTimeout(resolve,10));
 for(const code of ['ENOENT','EACCES','UNKNOWN']){
  // Positive control: without the hold the updater's own fallback runs.
  const bare=nsisLike(code);bare.quitAndInstall();await settle();assert(bare.calls.some(c=>c.startsWith('shell.openPath')||c==='elevate.exe'),'control '+code+': '+bare.calls);
  const provider=nsisLike(code),original=provider.spawnLog,log=[];const hold=holdInstallerSpawn(provider,line=>log.push(line));
  provider.quitAndInstall();const spawned=hold.spawned();assert(spawned,'the shell sees the attempt');
  await assert.rejects(spawned,error=>error.code===code,'the shell learns the start failed');await settle();
  assert.deepEqual(provider.calls,['spawn C:/owned/update.exe'],code+': no elevate.exe, no opening the file');assert.match(log[0],/Installer did not start/);
  hold.restore();assert.equal(provider.spawnLog,original);}
 const provider=nsisLike(null);const hold=holdInstallerSpawn(provider);provider.quitAndInstall();assert.equal(await hold.spawned(),true);hold.restore();});
// Judy 12.4 (2026-10-26). Offer 1: background lookups alone leave nothing to press, so the Cancel line keeps its plain tint.
// Offer 2: when the engine has ended and the update did not install, the new engine leaves automatic processing, the
// audiobook jobs and the scan stopped (desktop_backend.py _stopped_kinds); the line names what was running.
test('lookups alone: the Cancel line names them without the warning tint; anything to press keeps it',()=>{const t=page();const base={version:'0.22.1',available:'0.22.2',check:{},download:{}};
 const line=problems=>t.installLine({...base,install:{phase:'cancelled',at:'21:07',problems}});
 assert.deepEqual(line([{kind:'lookups',cause:'still_stopping'}]),{text:"Update cancelled (tried 21:07). Background lookups didn't start again. Background lookups start again by themselves the next time Books Arranger opens.",failed:false});
 assert.equal(line([{kind:'lookups',cause:'still_stopping'},{kind:'scan',cause:'refused'}]).failed,true);
 assert.equal(line([{kind:'automatic',cause:'refused'}]).failed,true);
 assert.equal(t.installLine({...base,install:{phase:'failed',cause:'bound',at:'21:07',waiting:[],problems:[{kind:'lookups',cause:'still_stopping'}]}}).failed,true,'a failed update stays a failure');});
test('an ended engine: the installer, engine exit and engine restart lines name the work that stays stopped',async()=>{
 const run=async(cause,stopped,extra={})=>{const f=fixture();await ready(f);
  f.controller.parkEngine=async({progress})=>{progress({phase:'pausing',waiting:[],elapsed:1,safe_seconds:90,stopped});if(cause==='engine_exit'||cause==='engine_stuck')throw typed(cause);};
  if(cause==='installer_blocked'||cause==='engine_restart')f.controller.install=async()=>{throw typed('installer_blocked');};
  if(cause==='engine_restart')f.controller.restartEngine=async()=>{throw new Error('port taken');};
  Object.assign(f.controller,extra);await f.controller.restart();return f;};
 let f=await run('installer_blocked',['automatic','scan','nonsense']);
 assert.deepEqual(f.controller.value.install.problems,[{kind:'automatic',cause:'engine_ended'},{kind:'scan',cause:'engine_ended'}]);
 const blocked=page().installLine(f.controller.value);
 assert.deepEqual([blocked.text,blocked.path],["The installer couldn't start (tried 21:04). Windows or your antivirus may have blocked it. Books Arranger is running again on 0.22.1. Automatic processing and the library scan didn't start again. Press Start automatic processing to continue. Continue the scan with Resume scanning. Run the installer yourself:",'C:/owned/update.exe']);
 f=await run('engine_exit',['conversion']);
 assert.equal(page().installLine(f.controller.value).text,"The engine stopped during the update and was started again (tried 21:04). It is loading now. The audiobook jobs didn't start again. Press Resume audiobook jobs to continue. Press Restart to update to try again.");
 f=await run('engine_restart',['conversion']);
 assert.equal(page().installLine(f.controller.value).text,"Books Arranger couldn't restart its engine (tried 21:04). Choose Quit Books Arranger in the tray, then open it again. The audiobook jobs didn't start again. Press Resume audiobook jobs to continue.");
 f=await run('engine_stuck',['automatic']);
 assert.equal(page().installLine(f.controller.value).text,"Books Arranger couldn't restart its engine (tried 21:04). Choose Quit Books Arranger in the tray, then open it again. Automatic processing didn't start again. Press Start automatic processing to continue.");
 await f.controller.lateEngineExit();  // W5: the late exit's line keeps naming it
 assert.equal(page().installLine(f.controller.value).text,"The engine stopped during the update and was started again (tried 21:04). It is loading now. Automatic processing didn't start again. Press Start automatic processing to continue. Press Restart to update to try again.");
 // Nothing was running: the lines stay as Judy wrote them in 2.6.
 f=await run('installer_blocked',[]);
 assert.equal(page().installLine(f.controller.value).text,"The installer couldn't start (tried 21:04). Windows or your antivirus may have blocked it. Books Arranger is running again on 0.22.1. Run the installer yourself:");
 // A failure before the engine ended (the bound) never takes the ended engine's list.
 f=await run('bound',['automatic'],{parkEngine:async({progress})=>{progress({phase:'pausing',stopped:['automatic']});throw typed('bound',{waiting:[{kind:'research'}],resumeProblems:[]});}});
 assert.deepEqual([f.controller.value.install.cause,f.controller.value.install.problems],['bound',[]]);
 // A new restart clears what the last one recorded.
 f.controller.parkEngine=async()=>{};await f.controller.restart();assert.deepEqual(f.controller.value.install.stopped,[]);});
// Senua's 0.22.1 review, W16: an engine exit that lands while restart() still closes the installer lease (busy.install
// still true) was dropped by lateEngineExit, so the old engine was never started again.
test('a late engine exit during the lease close is kept and starts the old engine once the install has ended',async()=>{const f=fixture();await ready(f);
 f.controller.parkEngine=async()=>{throw typed('engine_stuck');};
 let late=null;f.lease.close=async()=>{f.seen.push('close');late=f.controller.lateEngineExit();await new Promise(resolve=>setTimeout(resolve,10));};
 await f.controller.restart();await late;await new Promise(resolve=>setTimeout(resolve,0));
 assert(f.seen.includes('old engine started'),'the exit is followed by a restart once busy.install clears');
 assert.deepEqual([f.controller.value.install.phase,f.controller.value.install.cause,f.controller.value.busy.install],['failed','engine_exit',false]);
 assert.equal(f.seen.filter(s=>s==='old engine started').length,1,'once');});
// Futaba's 0.22.1 QA, m-4: a download cut by ERR_CONTENT_LENGTH_MISMATCH read the generic line.
test('a download the connection cut short reads as the connection dropped',async()=>{
 for(const message of ['net::ERR_CONTENT_LENGTH_MISMATCH','net::ERR_INCOMPLETE_CHUNKED_ENCODING','Error: aborted','Premature close']){
  const g=fixture();await g.controller.check();g.provider.downloadUpdate=async()=>{throw new Error(message);};await g.controller.download();
  assert.deepEqual([g.controller.value.download.phase,g.controller.value.download.cause],['failed','dropped'],message);}});
// Futaba's 0.22.1 QA, m-2 and m-11 (Judy 0.22.2 6.2 and 6.3): Cancel answers at the press and keeps its focus; the confirm
// names an approval in flight and tells the truth about what comes back after an update.
test('page: Cancel update answers at the press, names what is slow to resume from 3 s, and keeps its button',()=>{const t=page();
 const cancelling={available:'0.22.2',busy:{install:true},canCancel:false,install:{phase:'pausing',cancelling:true,cancelAt:1000,safe:90,elapsed:12,waiting:[{kind:'conversion',title:'Fixture'}],resuming:[],resumeSeconds:25}};
 assert.deepEqual(t.phaseLine(cancelling,1500),{text:'Cancelling the update…',counter:''},'at the press, no counter');
 assert.deepEqual(t.phaseLine({...cancelling,install:{...cancelling.install,resuming:[{kind:'conversion',title:'Fixture'}]}},4100),{text:'Cancelling the update… The conversion of Fixture is slow to resume. This can take up to 25 s.',counter:''});
 assert.deepEqual(t.phaseLine({...cancelling,install:{...cancelling.install,waiting:[]}},4100),{text:'Cancelling the update… The engine is resuming. This can take up to 25 s.',counter:''});
 const button=t.buttons({version:'0.22.1',ready:true,packaged:true,check:{},download:{},...cancelling},{}).cancel;
 assert.deepEqual([button.face,button.busy,button.hidden,button.title],['Cancelling…',true,false,'Cancelling can’t be stopped.'],'it stays on screen with its focus');
 assert.equal(t.quitBlock({quit:'updating',update:cancelling}),'The update is being cancelled. Quit works when it finishes.');
});
test('page: the confirm names approvals in flight; the conversion line says it comes back with Resume audiobook jobs',()=>{const t=page();
 assert.deepEqual(t.workLines({busy:{approvals:1}}).lines,['An approval in progress stops, and the book is not approved. Press Approve again afterwards.']);
 assert.deepEqual(t.workLines({busy:{approvals:2}}).lines,['2 approvals in progress stop, and those books are not approved. Press Approve again afterwards.']);
 assert.deepEqual(t.workLines({busy:{converting:true,current_title:'Fixture'}}).lines,['Converting Fixture. It stops. Continue it with Resume audiobook jobs.']);});
test('a Cancel press is answered at once: cancelling, its time, and the button stays',async()=>{const f=fixture();await ready(f);
 f.controller.parkEngine=async({progress})=>{progress({phase:'pausing',waiting:[{kind:'conversion',title:'Fixture'}],elapsed:3,safe_seconds:90,resume_seconds:25});
  assert.equal(f.controller.cancel(),true);const value=f.controller.value;
  assert.deepEqual([value.install.cancelling,value.install.cancelAt,value.canCancel],[true,f.clock,false]);
  progress({phase:'pausing',waiting:[],resuming:[{kind:'conversion',title:'Fixture'}],resume_seconds:25});
  assert.deepEqual([f.controller.value.install.resuming,f.controller.value.install.resumeSeconds],[[{kind:'conversion',title:'Fixture'}],25]);
  throw typed('cancelled');};
 await f.controller.restart();assert.equal(f.controller.value.install.cancelling,false,'answered');});

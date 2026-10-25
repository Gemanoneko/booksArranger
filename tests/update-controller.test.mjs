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

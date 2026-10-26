'use strict';
// Provider injected for deterministic tests; production uses electron-updater's
// GitHub provider, checksum download and explicit installer invocation.
// 0.22.1 (ruling 27; Judy's 0.22.1 UX spec, section 2): Check, Download and Install each keep their own record
// (phase, HH:MM, typed cause), so a failed install can never show up as a check result. A check is bounded (30 s an
// attempt, 3 attempts, 5 s and 15 s apart). Restart to update has no idle gate: the engine stops its work in bounded
// steps and can be cancelled. Once the engine has ended, any failure to start the installer starts the old engine
// again. Raw error text goes to the log, never to the page.
const CHECK_ATTEMPTS = 3;
const CHECK_ATTEMPT_MS = 30000;
const CHECK_BACKOFF_MS = [5000, 15000];
const NO_INTERNET = /ERR_INTERNET_DISCONNECTED|ERR_NAME_NOT_RESOLVED|ERR_NAME_RESOLUTION_FAILED|ERR_ADDRESS_UNREACHABLE|ERR_NETWORK_ACCESS_DENIED|ENOTFOUND|EAI_AGAIN|ENETUNREACH|ENETDOWN/;
const NO_ANSWER = /ERR_TIMED_OUT|ERR_CONNECTION_TIMED_OUT|ERR_CONNECTION_RESET|ERR_CONNECTION_CLOSED|ERR_NETWORK_CHANGED|ETIMEDOUT|ECONNRESET|socket hang up|timed out/i;

function hhmm(ms) { const d = new Date(ms); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); }
function text(error) { return String((error && (error.stack || error.message)) || error); }
function httpCode(error) {
 const code = Number(error && (error.statusCode || error.status)) || Number((/HttpError: (\d{3})|\b(?:status(?:Code)?|code)\D{0,3}(\d{3})\b/i.exec(text(error)) || []).slice(1).find(Boolean));
 return code >= 400 && code <= 599 ? code : 0;
}
function checkCause(error) {
 if (error && error.timedOut) return { cause: 'no_answer' };
 const message = text(error);
 if (NO_INTERNET.test(message)) return { cause: 'no_internet' };
 const code = httpCode(error);
 if (code) return { cause: 'github_error', code };
 if (NO_ANSWER.test(message)) return { cause: 'no_answer' };
 return { cause: 'other' };
}
function downloadCause(error) {
 const message = text(error);
 if ((error && error.code === 'ERR_CHECKSUM_MISMATCH') || /checksum/i.test(message)) return 'checksum';
 if (/ENOSPC|not enough space|disk (is )?full/i.test(message)) return 'disk_full';
 if (NO_INTERNET.test(message) || NO_ANSWER.test(message)) return 'dropped';
 return 'other';
}
const INSTALL_BUSY = ['starting', 'pausing', 'forcing', 'updating', 'installing'];

// Senua's 0.22.1 review, W7. electron-updater 6.8.9 answers a failed installer spawn by itself
// (NsisUpdater.doInstall: EACCES or UNKNOWN runs it again through elevate.exe, ENOENT opens it with shell.openPath),
// after the shell has already reported installer_blocked and started the old engine again: a UAC prompt or the
// installer then appears over a running app, and NSIS closes it mid-load. While the shell installs, the provider's
// spawn hands the shell the real attempt and the provider a settled one, so the shell alone decides what follows a
// failed start. restore() puts the provider's own spawn back.
function holdInstallerSpawn(provider, log = () => {}) {
  const original = provider.spawnLog;
  let attempt = null;
  provider.spawnLog = function (...args) {
    try { attempt = Promise.resolve(original.apply(this, args)); } catch (error) { attempt = Promise.reject(error); }
    return attempt.catch(error => { log('Installer did not start: ' + text(error)); return false; });
  };
  return { spawned: () => attempt, restore: () => { provider.spawnLog = original; } };
}

class UpdateController {
  constructor({provider, packaged, version = '', notify, acquireArtifact, parkEngine, install, restartEngine = async () => {}, exists = () => true,
    log = () => {}, now = Date.now, sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))}) {
    Object.assign(this,{provider,packaged,version,notify,acquireArtifact,parkEngine,install,restartEngine,exists,log,now,sleep});
    this.available='';this.ready=null;this.seen=null;this.downloadFailed='';this.cancelRequested=false;this.installerShown=false;
    this.busy={check:false,download:false,install:false};
    this.check_={phase:packaged?'idle':'dev',at:'',cause:'',code:0,attempt:0};
    this.download_={phase:'idle',at:'',cause:'',progress:0};
    this.install_={phase:'idle',at:'',cause:'',waiting:[],critical:[],elapsed:0,safe:0,problems:[]};
    provider.autoDownload=false;provider.autoInstallOnAppQuit=false;provider.autoRunAppAfterInstall=true;
    provider.on('update-available',info=>{this.seen={available:String(info.version||'')};});
    provider.on('update-not-available',()=>{this.seen={current:true};});
    provider.on('download-progress',progress=>{if(!this.busy.download)return;this.download_={...this.download_,phase:'downloading',progress:Math.max(0,Math.min(100,Number(progress.percent)||0))};this.emit();});
    provider.on('update-downloaded',info=>{const helper=provider.downloadedUpdateHelper;
      if(!helper||!helper.file||!helper.downloadedFileInfo||!helper.downloadedFileInfo.sha512||helper.downloadedFileInfo.isAdminRightsRequired){
        this.ready=null;this.downloadFailed=helper&&helper.downloadedFileInfo&&helper.downloadedFileInfo.isAdminRightsRequired?'other':'checksum';this.log('Downloaded update lacks checksum identity');return;}
      this.ready=Object.freeze({path:helper.file,sha512:helper.downloadedFileInfo.sha512,version:info.version});this.downloadFailed='';});
    // Check and download handle their own failures; a late error from an abandoned attempt only reaches the log.
    provider.on('error',error=>this.log('updater: '+text(error)));
  }
  get value(){
    const installing=this.busy.install;
    return {version:this.version,available:this.available||(this.ready&&this.ready.version)||'',ready:!!this.ready,packaged:!!this.packaged,
      busy:{...this.busy},check:{...this.check_},download:{...this.download_},
      install:{...this.install_,waiting:this.install_.waiting.map(item=>({...item})),critical:[...this.install_.critical],problems:this.install_.problems.map(item=>({...item}))},
      canCancel:installing&&!this.cancelRequested&&['starting','pausing','forcing'].includes(this.install_.phase),
      showInstaller:this.installerShown&&!!this.ready&&this.exists(this.ready.path),installerPath:this.ready?this.ready.path:''};
  }
  emit(){this.notify(this.value);}
  stamp(){return hhmm(this.now());}
  async check(){
    if(!this.packaged){this.check_={...this.check_,phase:'dev'};this.emit();return this.value;}
    if(this.busy.check)return this.value;
    this.busy.check=true;this.installerShown=false;
    try{
      for(let attempt=1;attempt<=CHECK_ATTEMPTS;attempt++){
        if(attempt===1){this.check_={phase:'checking',at:'',cause:'',code:0,attempt};this.emit();}
        this.seen=null;
        try{
          await this.bounded(this.provider.checkForUpdates(),CHECK_ATTEMPT_MS);
        }catch(error){
          this.log('Update check attempt '+attempt+' failed: '+text(error));
          const {cause,code=0}=checkCause(error);
          if(error&&error.timedOut)this.provider.checkForUpdatesPromise=null; // the next try sends a new request, not the stuck one
          if(cause!=='no_answer'||attempt===CHECK_ATTEMPTS){this.check_={phase:'failed',at:this.stamp(),cause,code,attempt};return this.value;}
          this.check_={phase:'retrying',at:'',cause:'',code:0,attempt:attempt+1};this.emit();
          await this.sleep(CHECK_BACKOFF_MS[attempt-1]);
          continue;
        }
        const found=this.seen&&this.seen.available;
        if(found)this.available=found;
        this.check_={phase:found?'available':'current',at:this.stamp(),cause:'',code:0,attempt,version:found||''};
        return this.value;
      }
    }finally{this.busy.check=false;this.emit();}
    return this.value;
  }
  bounded(promise,ms){
    return Promise.race([Promise.resolve(promise),this.sleep(ms).then(()=>{throw Object.assign(new Error('No answer in '+ms/1000+' s'),{timedOut:true});})]);
  }
  async download(){
    if(!this.packaged||!this.available||this.ready&&this.ready.version===this.available)throw new Error('Check for an available update first');
    if(this.busy.download||this.busy.install)return this.value;
    this.busy.download=true;this.downloadFailed='';this.download_={phase:'downloading',at:'',cause:'',progress:0};this.emit();
    try{
      await this.provider.downloadUpdate();
      if(!this.ready)throw Object.assign(new Error('Downloaded update lacks checksum identity'),{downloadCause:this.downloadFailed||'checksum'});
      this.download_={phase:'ready',at:this.stamp(),cause:'',progress:100};
    }catch(error){
      this.log('Update download failed: '+text(error));
      this.ready=null;this.download_={phase:'failed',at:this.stamp(),cause:error.downloadCause||downloadCause(error),progress:0};
    }finally{this.busy.download=false;this.emit();}
    return this.value;
  }
  progress(update){
    const phase=update.phase==='exiting'?'updating':update.phase;
    if(!INSTALL_BUSY.includes(phase)||this.install_.phase==='installing')return;
    this.install_={...this.install_,phase,waiting:Array.isArray(update.waiting)?update.waiting:[],critical:Array.isArray(update.critical)?update.critical:[],
      elapsed:Number(update.elapsed)||0,safe:Number(update.safe_seconds)||this.install_.safe};
    this.emit();
  }
  cancel(){
    if(!this.value.canCancel)return false;
    this.cancelRequested=true;this.emit();return true;
  }
  async restart(){
    if(!this.packaged||!this.ready)throw new Error('A verified downloaded update is required');
    if(this.busy.install||this.busy.download)return this.value;
    this.busy.install=true;this.cancelRequested=false;this.installerShown=false;
    this.install_={phase:'starting',at:'',cause:'',waiting:[],critical:[],elapsed:0,safe:0,problems:[]};this.emit();
    const ready=this.ready;let lease=null,engineEnded=false;
    try{
      // Keep the exact checksum-verified installer write/delete denied from before the engine stops until the
      // installer process exists.
      try{lease=await this.acquireArtifact(ready);}
      catch(error){throw Object.assign(error,{updateCause:/timed out/i.test(error.message)?'verify_timeout':'checksum'});}
      if(!lease.isAlive())throw Object.assign(new Error('Installer native lease ended; update cancelled'),{updateCause:'checksum'});
      try{await this.parkEngine({progress:update=>this.progress(update),cancelRequested:()=>this.cancelRequested});}
      catch(error){engineEnded=error.updateCause==='engine_exit';throw error;}
      engineEnded=true;
      if(!lease.isAlive())throw Object.assign(new Error('Installer native lease ended; update cancelled'),{updateCause:'checksum'});
      this.install_={...this.install_,phase:'installing'};this.emit();
      await this.install(ready); // resolves once the installer process exists; the app then exits
      return this.value;
    }catch(error){
      this.log('Update did not install: '+text(error));
      let cause=error.updateCause||(engineEnded?'installer_blocked':'other');
      if(engineEnded){try{await this.restartEngine();}catch(restartError){this.log('Engine restart failed: '+text(restartError));cause='engine_restart';}}
      if(cause==='checksum'){this.ready=null;this.download_={phase:'idle',at:'',cause:'',progress:0};}
      this.installerShown=['bound','installer_blocked'].includes(cause);
      // Senua's 0.22.1 review, W3: what the engine could not start again after Cancel, its bound or a failed close.
      this.install_={...this.install_,phase:cause==='cancelled'?'cancelled':'failed',at:this.stamp(),cause,
        waiting:Array.isArray(error.waiting)&&error.waiting.length?error.waiting:this.install_.waiting,
        problems:Array.isArray(error.resumeProblems)?error.resumeProblems.map(item=>({kind:String(item.kind),cause:String(item.cause)})):[]};
      return this.value;
    }finally{if(lease)await lease.close();this.busy.install=false;this.cancelRequested=false;this.emit();}
  }
  // Senua's 0.22.1 review, W5: the engine ended for the update after the shell had given up waiting for it (engine_stuck,
  // too late to cancel). That exit is no Stop of the app: the old engine starts again and the Install line says so (N3).
  async lateEngineExit(){
    if(this.busy.install)return this.value;
    this.log('The engine ended for the update after the shell stopped waiting; starting it again');
    let cause='engine_exit';
    try{await this.restartEngine();}catch(error){this.log('Engine restart failed: '+text(error));cause='engine_restart';}
    this.install_={...this.install_,phase:'failed',at:this.stamp(),cause,problems:[]};this.emit();
    return this.value;
  }
}
module.exports={UpdateController,holdInstallerSpawn,checkCause,downloadCause,CHECK_ATTEMPTS,CHECK_ATTEMPT_MS,CHECK_BACKOFF_MS};

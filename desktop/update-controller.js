'use strict';
// Provider injected for deterministic tests; production uses electron-updater's
// GitHub provider, checksum download and explicit installer invocation.
class UpdateController {
  constructor({provider, packaged, notify, acquireArtifact, parkEngine, install}) {
    Object.assign(this,{provider,packaged,notify,acquireArtifact,parkEngine,install});
    this.value={phase:'idle',version:'',error:'',progress:0};this.ready=null;this.operation=false;
    provider.autoDownload=false;provider.autoInstallOnAppQuit=false;provider.autoRunAppAfterInstall=true;
    provider.on('update-available',info=>{if(this.ready){this.emit();return;}this.value={phase:'available',version:info.version,error:'',progress:0};this.emit();});
    provider.on('update-not-available',()=>{if(!this.ready)this.value={phase:'current',version:'',error:'',progress:0};this.emit();});
    provider.on('download-progress',progress=>{this.value={...this.value,phase:'downloading',progress:Math.max(0,Math.min(100,Number(progress.percent)||0))};this.emit();});
    provider.on('update-downloaded',info=>{const helper=provider.downloadedUpdateHelper;
      if(!helper||!helper.file||!helper.downloadedFileInfo||!helper.downloadedFileInfo.sha512||helper.downloadedFileInfo.isAdminRightsRequired){this.fail(new Error('Downloaded update lacks checksum identity'));return;}
      this.ready=Object.freeze({path:helper.file,sha512:helper.downloadedFileInfo.sha512,version:info.version});
      this.value={phase:'ready',version:info.version,error:'',progress:100};this.emit();});
    provider.on('error',error=>this.fail(error));
  }
  emit(){this.notify({...this.value,ready:!!this.ready});}
  fail(error){this.value={...this.value,phase:this.ready?'ready':'error',error:String(error.message||error).slice(0,512)};this.emit();}
  async check(){if(!this.packaged)throw new Error('Update checks are available in the installed app');if(this.operation)return;
    this.operation=true;this.value={...this.value,phase:this.ready?'ready':'checking',error:''};this.emit();
    try{await this.provider.checkForUpdates();}catch(error){this.fail(error);throw error;}finally{this.operation=false;}}
  async download(){if(!this.packaged||this.operation||this.value.phase!=='available')throw new Error('Check for an available update first');
    this.operation=true;this.value={...this.value,phase:'downloading',error:''};this.emit();
    try{await this.provider.downloadUpdate();}catch(error){this.fail(error);throw error;}finally{this.operation=false;}}
  async restart(){if(!this.packaged||!this.ready||this.operation)throw new Error('A verified downloaded update is required');
    this.operation=true;let lease;
    try{
      // Keep the exact checksum-verified installer write/delete denied throughout
      // the engine idle fence, native exit and installer process creation.
      lease=await this.acquireArtifact(this.ready);
      if(!lease.isAlive())throw new Error('Installer native lease ended; update cancelled');
      await this.parkEngine();
      if(!lease.isAlive())throw new Error('Installer native lease ended; update cancelled');
      this.value={...this.value,phase:'installing',error:''};this.emit();
      await this.install(this.ready);
    }catch(error){this.fail(error);throw error;}finally{if(lease)await lease.close();this.operation=false;}}
}
module.exports={UpdateController};

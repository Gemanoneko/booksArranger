// Read-only exact-installation admission before any Electron writable paths.
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
function assertNoPendingCleanup(installationId,{run=spawnSync,platform=process.platform,windows=process.env.SystemRoot}={}){
 if(!UUID.test(installationId))throw Error('Invalid Books Arranger installation identity.');
 if(platform!=='win32')return;
 if(typeof windows!=='string'||!path.win32.isAbsolute(windows)||windows.startsWith('\\\\'))throw Error('Windows registry admission is unavailable. No alternate storage was opened.');
 const executable=path.win32.join(windows,'System32','WindowsPowerShell','v1.0','powershell.exe');
 // RegistryKey directly, without provider/module loading or Add-Type. Only the
 // UUID above is interpolated; every other byte is fixed program text.
 const script="$ErrorActionPreference='Stop';$key=$null;try{$key=[Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Software\\Books Arranger\\UninstallTransactions\\"+installationId+"',$false);if($null -ne $key){if($key.SubKeyCount -gt 0){exit 17};if($key.ValueCount -gt 0){exit 18}};exit 0}catch{exit 18}finally{if($null -ne $key){$key.Dispose()}}";
 const result=run(executable,['-NoLogo','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-Command',script],
  {windowsHide:true,encoding:'utf8',timeout:5000,maxBuffer:65536,stdio:['ignore','pipe','pipe']});
 if(!result.error&&!result.signal&&result.status===0)return;
 if(!result.error&&!result.signal&&result.status===17)throw Error('Cleanup is unfinished for this installation. Keep it closed and review the recovery record at “HKCU\\Software\\Books Arranger\\UninstallTransactions\\'+installationId+'” before retrying.');
 throw Error('Books Arranger could not verify whether data cleanup is unfinished. Retained data was not opened.');
}
module.exports={assertNoPendingCleanup};

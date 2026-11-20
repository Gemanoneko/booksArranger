import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {cDriveEnvRefusal} from './c-drive-guard.mjs';

export const LOCAL_UPDATE_TITLE='M-1: an installer that cannot start keeps the app open: the old engine starts again and the Install line says so';
const entry='tests/main-startup.test.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));

export function verifyLocalShell(readMember){
 for(const filename of fs.readdirSync(path.join(root,'desktop')).filter(name=>name.endsWith('.js'))){
  const relative='desktop/'+filename;
  if(!readMember(relative).equals(fs.readFileSync(path.join(root,relative))))throw Error('Local update check source differs from package: '+relative);
 }
}

export function verifyLocalUpdateRun(result){
 const lines=String(result.stdout||'').split(/\r?\n/);
 const required=['ok 1 - '+LOCAL_UPDATE_TITLE,'1..1','# tests 1','# pass 1','# fail 0','# cancelled 0','# skipped 0','# todo 0'];
 if(result.error||result.status!==0||result.signal||required.some(line=>lines.filter(item=>item===line).length!==1)){
  throw Error('Project-local update check did not pass its exact case.\n'+(result.error?.message||'')+'\n'+lines.slice(-36).join('\n')+'\n'+(result.stderr||''));
 }
}

export function checkLocalUpdate(deadline=Date.now()+60000){
 const refusal=cDriveEnvRefusal({},root);
 if(refusal)throw Error(refusal);
 const timeout=Math.min(60000,deadline-Date.now());
 if(timeout<=0)throw Error('Release deadline expired before project-local update check');
 const scratch=fs.mkdtempSync(path.join(root,'books-update-qa-'));
 try{
  // Run the actual shell behind the test's fake Electron/engine/installer. Only
  // the loopback HTTP fixture and this fresh private directory are real.
  const env={SystemRoot:process.env.SystemRoot,windir:process.env.windir,TEMP:scratch,TMP:scratch,TMPDIR:scratch,
   USERPROFILE:scratch,HOME:scratch,APPDATA:scratch,LOCALAPPDATA:scratch,ProgramData:scratch};
  const result=spawnSync(process.execPath,['--test','--test-isolation=none','--test-reporter=tap','--test-name-pattern=^'+LOCAL_UPDATE_TITLE+'$',entry],
   {cwd:root,env,encoding:'utf8',windowsHide:true,timeout,maxBuffer:1024*1024});
  verifyLocalUpdateRun(result);
 }finally{fs.rmSync(scratch,{recursive:true,force:true});}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{checkLocalUpdate();console.log('PASS '+LOCAL_UPDATE_TITLE);}catch(error){console.error(error.message);process.exitCode=1;}
}

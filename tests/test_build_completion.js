const assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const moduleUrl=pathToFileURL(path.resolve(__dirname,'../scripts/build-builder.mjs')).href;
for(const mode of ['pending','unverified','rejected','verified']){
  const code=`import {watchBuildCompletion} from ${JSON.stringify(moduleUrl)};
const mode=${JSON.stringify(mode)};
const work=mode==='pending'?new Promise(()=>{}):mode==='rejected'?Promise.reject(Error('fixture rejection')):Promise.resolve();
const result=watchBuildCompletion(work,{isVerified:()=>mode==='verified',subscribeBeforeExit:f=>process.once('beforeExit',f),subscribeExit:f=>process.once('exit',f),fail:()=>{process.exitCode=1;}});
if(mode!=='pending')await result;process.exit(0);`;
  const result=spawnSync(process.execPath,['--input-type=module','-e',code],{cwd:process.cwd(),env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''},windowsHide:true,timeout:5000,maxBuffer:8192});
  assert.ifError(result.error);assert.equal(result.signal,null);
  assert.equal(result.status,mode==='verified'?0:1,'actual OS exit status for '+mode);
}
console.log('Verified actual Node exit status for pending, unverified, rejected and verified builds');

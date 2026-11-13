const assert=require('node:assert/strict');
const {assertNoPendingCleanup}=require('../desktop/pending-cleanup');
const id='3b1c0b6f-4256-4379-9174-3c20646bfba0';let calls=0;
function options(status){return {platform:'win32',windows:'C:\\Windows',run:(exe,args,config)=>{
 calls++;assert.match(exe,/System32\\WindowsPowerShell\\v1\.0\\powershell\.exe$/);
 assert(args.includes('-NoProfile'));assert(args.includes('-NonInteractive'));
 assert(args.at(-1).includes('UninstallTransactions\\'+id));assert(!args.at(-1).includes('Add-Type'));
 assert.equal(config.windowsHide,true);assert.equal(config.timeout,5000);return {status,signal:null};}};}
assertNoPendingCleanup(id,options(0));
assert.throws(()=>assertNoPendingCleanup(id,options(17)),/Cleanup is unfinished.*recovery record.*UninstallTransactions/);
assert.throws(()=>assertNoPendingCleanup(id,options(18)),/could not verify/);
assert.throws(()=>assertNoPendingCleanup(id,{...options(0),run:()=>({status:null,error:Error('timeout')})}),/could not verify/);
assert.throws(()=>assertNoPendingCleanup(id+';not-code',options(0)),/identity/);
assert.equal(calls,3);console.log('pending cleanup: exact installation, pre-write refusal and bounded uncertainty controls passed');

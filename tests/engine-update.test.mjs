import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';const {parkOwnedEngine}=createRequire(import.meta.url)('../desktop/engine-update.js');
// 0.22.1 (ruling 27): a fake engine on a fake clock. Each sleep advances the clock; the engine "exits" by setting
// backendExited with its native exit code, as the host reports it.
function fixture(){const state={quit:'none',backendExited:false,owner:{pid:123},backend:{exitCode:null}};const f={state,clock:0,calls:[],progress:[],cancel:false};
 Object.assign(f,{sleep:async ms=>{f.clock+=ms;},now:()=>f.clock,broadcast:()=>{},progressFn:v=>f.progress.push(v.phase),exit:code=>{state.backendExited=true;state.backend.exitCode=code;}});
 f.request=async(method,path)=>{f.calls.push(method+' '+path);return path.endsWith('/status')?{phase:'pausing',update:{phase:'pausing',waiting:[]}}:{phase:'pausing',update:{phase:'pausing'}};};
 f.run=()=>parkOwnedEngine({state,request:(...a)=>f.request(...a),sleep:f.sleep,now:f.now,broadcast:f.broadcast,progress:f.progressFn,cancelRequested:()=>f.cancel});
 return f;}
const refusal=(status,message,code)=>Object.assign(new Error(message),{status,code});
test('update mode starts before the request is sent, so an exit 0 installs instead of closing the app',async()=>{const f=fixture();let modeAtPost=null;
 f.request=async(method,path)=>{if(method==='POST'){modeAtPost=f.state.quit;return {update:{phase:'pausing'}};}f.exit(0);throw Error('serving ended');};
 await f.run();assert.equal(modeAtPost,'updating');assert.equal(f.state.quit,'updating');});
test('a slow answer to the request is not a failure: it is sent again and the update goes on',async()=>{const f=fixture();let posts=0;
 f.request=async(method,path,options)=>{if(method==='POST'){posts++;assert.equal(options.timeout,15000);if(posts===1)throw new Error('Request timed out');return {update:{phase:'pausing'}};}f.exit(0);return {};};
 await f.run();assert.equal(posts,2);assert.equal(f.state.quit,'updating');});
test('HTTP absence only succeeds after the exact native zero exit',async()=>{const f=fixture();let polls=0;f.request=async method=>{if(method==='POST')return {};if(++polls===2)f.exit(0);throw Error('serving ended');};await f.run();assert.equal(f.state.quit,'updating');assert.equal(f.state.backendExited,true);});
test('status polls feed the progress line: what it waits for and each phase',async()=>{const f=fixture();let polls=0;
 const phases=['pausing','pausing','forcing','updating'];f.request=async(method,path)=>{if(method==='POST')return {update:{phase:'pausing',waiting:[]}};const phase=phases[polls++];if(!phase){f.exit(0);throw Error('gone');}return {phase,update:{phase,waiting:[{kind:'conversion',title:'Fixture'}],elapsed:polls}};};
 await f.run();assert.deepEqual(f.progress,['starting','pausing','pausing','pausing','forcing','updating']);});
test('the overall bound (3 minutes) cancels, names what did not stop, and the old app runs on',async()=>{const f=fixture();let cancelled=false;
 f.request=async(method,path)=>{f.calls.push(method+' '+path);if(path.endsWith('/update-cancel')){cancelled=true;return {phase:'running',update:{outcome:{result:'cancelled',waiting:[{kind:'conversion',title:'Fixture'}]}}};}return {phase:'pausing',update:{phase:'pausing',waiting:[{kind:'conversion',title:'Fixture'}]}};};
 await assert.rejects(f.run(),error=>error.updateCause==='bound'&&error.waiting[0].kind==='conversion');
 assert(cancelled);assert(f.clock>=180000&&f.clock<182000,'bound at 180 s, measured '+f.clock);assert.equal(f.state.quit,'none');assert.equal(f.state.backendExited,false);});
test('Cancel update while waiting: the engine undoes the update and the shell leaves update mode',async()=>{const f=fixture();let polls=0;
 f.request=async(method,path)=>{f.calls.push(method+' '+path);if(path.endsWith('/update-cancel'))return {phase:'running',update:{outcome:{result:'cancelled',waiting:[]}}};if(path.endsWith('/status')&&++polls===2)f.cancel=true;return {phase:'pausing',update:{phase:'pausing'}};};
 await assert.rejects(f.run(),error=>error.updateCause==='cancelled');assert(f.calls.includes('POST /api/desktop/update-cancel'));assert.equal(f.state.quit,'none');});
test('too late to cancel: the engine is already ending, so the update goes on to install',async()=>{const f=fixture();let refused=false;
 f.request=async(method,path)=>{if(path.endsWith('/update-cancel')){refused=true;throw refusal(409,'The update has started','started');}if(method==='POST'){f.cancel=true;return {update:{phase:'pausing'}};}f.exit(0);throw Error('gone');};
 await f.run();assert(refused);assert.equal(f.state.quit,'updating');});
test("the engine's own bound or a failed close is read from status and leaves update mode",async()=>{for(const result of ['bound','blocked']){const f=fixture();
 f.request=async(method,path)=>method==='POST'?{update:{phase:'pausing'}}:{phase:'running',update:{phase:'running',outcome:{result,waiting:[{kind:'scan'}],reason:'worker'}}};
 await assert.rejects(f.run(),error=>error.updateCause===result&&error.waiting[0].kind==='scan');assert.equal(f.state.quit,'none');}});
test('a refusal (a Quit is under way) restores the shell and is not retried',async()=>{const f=fixture();let posts=0;f.request=async()=>{posts++;throw refusal(409,'Books Arranger is closing');};
 await assert.rejects(f.run(),error=>error.updateCause==='refused');assert.equal(posts,1);assert.equal(f.state.quit,'none');assert.equal(f.state.backendExited,false);});
test('an engine exit other than 0 is typed; update mode stays for the controller to start the old engine again',async()=>{const f=fixture();f.request=async method=>{if(method==='POST')return {};f.exit(1);throw Error('gone');};
 await assert.rejects(f.run(),error=>error.updateCause==='engine_exit');assert.equal(f.state.quit,'updating');});
test('no update without an owned running engine',async()=>{const f=fixture();f.state.owner=null;await assert.rejects(f.run(),error=>error.updateCause==='refused');assert.equal(f.state.quit,'none');});

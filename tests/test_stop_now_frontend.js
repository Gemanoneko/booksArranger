'use strict';
// 0.29.0 item 7 (Sergei Q8, 2026-11-17: "Stop always acts at once") on the real frontend, with the Retry test's DOM and
// transport doubles. No server, no library.
// - Stop automatic processing bypasses the page queue (like Pause audiobook jobs) and never touches busy.
// - A press in flight when Stop is pressed may land at the engine after it: once it lands, the page pauses audiobook jobs
//   again, so its job stays paused. A queued Resume or Start is dropped by Stop.
// - Cancelling a queued press replaces its "queued … Press it again to cancel." line.
// - A queued line names its blocker; one the page cannot name is "the app is free", never "the current action".
// - A queued press the page turns away when its turn comes says why.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const answers={};const posts=[];const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(answers[route]){posts.push({route,data});return answers[route](data);}
  return baseFetch(route,options);
};
const ok=(value,status=200)=>({ok:status<400,status,json:async()=>value});
const sent=route=>posts.filter(p=>p.route===route).length;
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const running={...backend.automatic_processing,state:'Running',phase:'research',can_start:false,can_stop:true};
(async()=>{
  backend={...backend,automatic_processing:running,audiobook_jobs:{...backend.audiobook_jobs,state:'Running',queued:2}};
  run('state='+JSON.stringify(backend)+';controls()');
  // 1. A press in flight (Start scanning), then Stop: Stop reaches the engine at once and is never queued.
  let scanAnswer;answers['/api/scan/start']=()=>new Promise(resolve=>{scanAnswer=resolve;});
  answers['/api/automatic/stop']=()=>ok({automatic_processing:{...running,state:'Stopping',can_stop:false}});
  answers['/api/audiobook/pause']=()=>ok({state:'Paused'});
  const scanning=run("action('/api/scan/start',{library:'Audiobooks'})");
  assert.equal(run('busy'),true,'the scan press is in flight');
  assert.equal(get('stop-automatic').disabled,false);
  const stopping=get('stop-automatic').handlers.click();
  assert.equal(sent('/api/automatic/stop'),1,'Stop is sent at once, not queued behind the press in flight');
  assert.equal(run('laterPresses.length'),0,'nothing is queued');
  assert.equal(get('message').textContent,'Stopping automatic processing…');
  await stopping;await tick();
  assert.equal(run('busy'),true,'Stop never touches busy: the scan press still holds it');
  assert.equal(sent('/api/audiobook/pause'),0,'the press in flight has not landed yet');
  // 2. The press lands after Stop: its job is paused again, once.
  backend={...backend,automatic_processing:{...running,state:'Paused',can_start:true,can_stop:false}};
  scanAnswer(ok({state:'Running'}));await scanning;await tick();await tick();
  assert.equal(run('busy'),false);
  assert.equal(sent('/api/audiobook/pause'),1,'a press in flight landing just after Stop leaves its job paused');
  run('controls()');await tick();assert.equal(sent('/api/audiobook/pause'),1,'paused once, not again on every redraw');
  // Positive control: Stop with no press in flight sends no extra pause.
  backend={...backend,automatic_processing:running};run('state='+JSON.stringify(backend)+';controls()');
  await get('stop-automatic').handlers.click();await tick();await tick();
  assert.equal(sent('/api/automatic/stop'),2);assert.equal(sent('/api/audiobook/pause'),1,'nothing in flight: no second pause');
  // 3. A queued Resume is dropped by Stop: it would undo it.
  run('state='+JSON.stringify(backend)+';busy=true;controls()');
  run("pressLater('toolbar:resume-jobs','resume','',()=>{throw Error('a dropped press ran')})");assert.equal(run('laterPresses.length'),1);
  await get('stop-automatic').handlers.click();await tick();
  assert.equal(run('laterPresses.length'),0,'Stop drops the queued Resume');
  run('busy=false;controls()');await tick();await tick();
  // 4. A queued line names its blocker; an unnamed one says the app is free.
  run("busy=true;busyPress='Start scanning';controls()");
  let item=run("pressLater('toolbar:find-covers','find_covers','',()=>null)");
  assert.equal(run('laterLine(laterPresses[0])'),'Find local covers queued. It runs when Start scanning finishes.');
  run("busyPress=''");assert.equal(run('laterLine(laterPresses[0])'),'Find local covers queued. It runs when the app is free.');
  assert.doesNotMatch(run('laterLine(laterPresses[0])'),/the current action/);
  // 5. Cancelling a queued press replaces its line.
  run("message(laterLine(laterPresses[0])+' Press it again to cancel.')");
  assert.equal(run("cancelLater('toolbar:find-covers')"),true);
  assert.equal(get('message').textContent,'Find local covers cancelled. Nothing was sent.');
  // 6. A queued Start turned away when its turn comes says why.
  backend={...backend,automatic_processing:{...running,state:'Paused',can_start:true,can_stop:false}};run('state='+JSON.stringify(backend)+';busy=true;controls()');
  get('start-automatic').handlers.click();assert.equal(run('laterPresses.length'),1,'Start waits behind the busy page');
  run("state={...state,automatic_processing:{...state.automatic_processing,state:'Running',can_start:false,can_stop:true}};busy=false;controls()");await tick();await tick();
  assert.equal(sent('/api/automatic/start'),0);
  assert.match(get('message').textContent,/^Start automatic processing was not sent: /);
  console.log('PASS 0.29.0 Stop acts at once: bypasses the queue, keeps busy, re-pauses after a press in flight; queued lines name the blocker; cancel and turn-away lines');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_stop_now_frontend.js'),module);m.filename=path.join(__dirname,'test_stop_now_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

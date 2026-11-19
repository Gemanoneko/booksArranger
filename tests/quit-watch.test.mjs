import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const {createQuitWatch,outcomeOf}=createRequire(import.meta.url)('../desktop/quit-watch.js');

test('refusals for the bound mean the engine is gone',()=>{
 const clock={t:0};const watch=createQuitWatch({now:()=>clock.t,goneAfterMs:5000});
 assert.equal(watch.observe('refused'),false);clock.t=4000;assert.equal(watch.observe('refused'),false);
 clock.t=5000;assert.equal(watch.observe('refused'),true);
});

test('any reply or a timeout resets the count: the engine is still there',()=>{
 const clock={t:0};const watch=createQuitWatch({now:()=>clock.t,goneAfterMs:5000});
 watch.observe('refused');clock.t=4900;assert.equal(watch.observe('reply'),false);
 clock.t=6000;assert.equal(watch.observe('refused'),false,'counting starts again');clock.t=8000;assert.equal(watch.observe('other'),false);
 clock.t=9000;assert.equal(watch.observe('refused'),false);clock.t=14000;assert.equal(watch.observe('refused'),true);
});

test('only a refused connection counts as gone',()=>{
 assert.equal(outcomeOf(Object.assign(new Error('connect'),{code:'ECONNREFUSED'})),'refused');
 assert.equal(outcomeOf(new Error('Request timed out')),'other');assert.equal(outcomeOf(new Error('HTTP 503')),'other');assert.equal(outcomeOf(null),'reply');
});

// 0.22.3 (seen on 0.22.1 under load: "Quit could not be confirmed; ownership remains held. Request timed out").
const {sendQuit}=createRequire(import.meta.url)('../desktop/quit-watch.js');
const timedOut=()=>Object.assign(new Error('Request timed out'));
const fakeClock=()=>{const clock={t:0};return {clock,now:()=>clock.t,sleep:async ms=>{clock.t+=ms;}};};
test('a Quit request that runs out is sent again until the engine takes it',async()=>{
 const {now,sleep}=fakeClock();let calls=0;
 const sent=await sendQuit({now,sleep,post:async()=>{calls++;if(calls<3)throw timedOut();return {phase:'finishing'};}});
 assert.equal(sent.outcome,'accepted');assert.equal(calls,3);
});
test('no answer at all for the bound is "silent", never a bare timeout',async()=>{
 const {clock,now,sleep}=fakeClock();
 const sent=await sendQuit({now,sleep,boundMs:45000,post:async()=>{clock.t+=10000;throw timedOut();}});
 assert.equal(sent.outcome,'silent');assert.equal(sent.error.message,'Request timed out');assert.ok(clock.t>=45000&&clock.t<60000,String(clock.t));
});
test('refused connections mean the engine is gone; an HTTP refusal keeps its reason',async()=>{
 const {now,sleep}=fakeClock();
 assert.equal((await sendQuit({now,sleep,post:async()=>{throw Object.assign(new Error('connect'),{code:'ECONNREFUSED'});}})).outcome,'gone');
 const refused=await sendQuit({now,sleep,post:async()=>{throw Object.assign(new Error('Missing or invalid desktop control token'),{status:403});}});
 assert.equal(refused.outcome,'refused');assert.equal(refused.error.status,403);
 assert.equal((await sendQuit({now,sleep,gone:()=>true,post:async()=>{throw timedOut();}})).outcome,'gone','the engine exited meanwhile');
});

// Futaba's 0.22.3 QA, m-2: one busy-engine Quit left a python.exe 2.5 s after the shell exited (engineGoneExit waited 5 s).
const {endOwnEngine}=createRequire(import.meta.url)('../desktop/quit-watch.js');
const host=(exitsAt)=>{const {clock,now,sleep}=fakeClock();const calls=[];return {clock,calls,options:{now,sleep,exited:()=>clock.t>=exitsAt(calls),closePipe:()=>calls.push('pipe'),kill:()=>{calls.push('kill');}}};};
test('Quit waits until its own engine host has exited, however long its safe stop takes within the bound',async()=>{
 const h=host(()=>12000);
 assert.equal(await endOwnEngine({...h.options,boundMs:30000}),'exited');assert.deepEqual(h.calls,['pipe'],'never ended: it stopped by itself');assert.ok(h.clock.t>=12000);
});
test('past the bound the host is ended through its own handle, and Quit waits for that too',async()=>{
 const h=host(calls=>calls.includes('kill')?h.clock.t:Infinity);
 const outcome=await endOwnEngine({...h.options,boundMs:30000,killWaitMs:5000});
 assert.equal(outcome,'ended');assert.deepEqual(h.calls,['pipe','kill']);assert.ok(h.clock.t>=30000);
 const stuck=host(()=>Infinity);assert.equal(await endOwnEngine({...stuck.options,boundMs:1000,killWaitMs:1000}),'still-running');
 const gone=host(()=>0);assert.equal(await endOwnEngine(gone.options),'exited');assert.deepEqual(gone.calls,[],'an exited host is left alone');
});
test('the shell ends Quit through endOwnEngine on its own child only',async()=>{
 const fs=await import('node:fs');const main=fs.readFileSync(new URL('../desktop/main.js',import.meta.url),'utf8');
 const gone=main.slice(main.indexOf('async function engineGoneExit()'),main.indexOf('async function watchQuit()'));
 assert.match(gone,/await endLoadingEngine\(30000\);/,'the host gets 30 s, then is ended, before the shell exits');
 assert.ok(!/taskkill|process\.kill\(/.test(main),'never a kill by name or PID');
});

// 0.30.0 item F (Sergei 2026-11-18: closed at 21:20, the engine still "closing" an hour later): the engine says what an
// accepted Quit still waits for (waiting_for), and the shell keeps those facts for the Quit-anyway offer (Judy's spec).
const {quitWaiting,createQuitProgress,quitNow}=createRequire(import.meta.url)('../desktop/quit-watch.js');
test('what Quit waits for is read from waiting_for; any other shape is nothing',()=>{
 assert.deepEqual(quitWaiting({phase:'finishing',waiting_for:[{kind:'conversion',title:'Дюна'},{kind:'cleanup',title:''}]}),[{kind:'conversion',title:'Дюна'},{kind:'cleanup',title:''}]);
 assert.deepEqual(quitWaiting({phase:'parking',waiting_for:[{kind:'press'},null,{title:'x'},{kind:5}]}),[{kind:'press',title:''}]);
 for(const status of [null,{},{waiting_for:'conversion'},{waiting_for:{kind:'conversion'}}])assert.deepEqual(quitWaiting(status),[]);
});
test('the facts count how long real work has been waited for, say when the list changes, and mark a failed close',()=>{
 const clock={t:0};const progress=createQuitProgress({now:()=>clock.t});
 let facts=progress.observe({phase:'finishing',waiting_for:[]});
 assert.deepEqual([facts.waitedMs,facts.changed,facts.blocked],[0,false,false]);
 clock.t=1000;facts=progress.observe({phase:'finishing',waiting_for:[{kind:'conversion',title:'Дюна'}]});
 assert.deepEqual([facts.waitedMs,facts.changed],[0,true]);
 clock.t=61000;facts=progress.observe({phase:'finishing',waiting_for:[{kind:'conversion',title:'Дюна'}]});
 assert.deepEqual([facts.waitedMs,facts.changed],[60000,false]);
 clock.t=62000;facts=progress.observe({phase:'parking',waiting_for:[{kind:'cleanup',title:''}]});
 assert.deepEqual([facts.phase,facts.waitedMs,facts.changed],['parking',61000,true],'still waiting since the first work named');
 clock.t=63000;facts=progress.observe({phase:'blocked',error:'A press is still running; ownership retained',waiting_for:[{kind:'press',title:''}]});
 assert.deepEqual([facts.blocked,facts.error],[true,'A press is still running; ownership retained']);
 clock.t=64000;facts=progress.observe({phase:'parking',waiting_for:[]});
 assert.deepEqual([facts.waiting,facts.waitedMs,facts.changed],[[],0,true]);
});
test('Quit anyway is the engine\'s safe stop, then the shell waits for its own host (and ends it past the bound)',async()=>{
 const calls=[];
 const done=await quitNow({post:async()=>{calls.push('stop-now');return {phase:'stopping'};},endEngine:async()=>{calls.push('end');return 'exited';}});
 assert.deepEqual(calls,['stop-now','end']);assert.deepEqual(done,{answer:{phase:'stopping'},engine:'exited'});
 const silent=await quitNow({post:async()=>{throw new Error('Request timed out');},endEngine:async()=>'ended'});
 assert.deepEqual(silent,{answer:null,engine:'ended'},'an engine that does not answer is stopped through its pipe');
 const fs=await import('node:fs');const main=fs.readFileSync(new URL('../desktop/main.js',import.meta.url),'utf8');
 const anyway=main.slice(main.indexOf('async function quitAnyway()'),main.indexOf('// Quit while loading closes at once'));
 assert.match(anyway,/'\/api\/desktop\/stop-now'/);assert.match(anyway,/endLoadingEngine\(30000\)/);assert.match(anyway,/finishExit\(0\)/);
 const watch=main.slice(main.indexOf('async function watchQuit('),main.indexOf('async function quitAnyway()'));
 assert.match(watch,/progress\.observe\(status\)/,'every Quit status poll keeps what it waits for');
});

// 0.30.0 item F follow-up: a failed close ('blocked') no longer leaves a half-closed app behind an error box, and Quit no
// longer waits without end for work Sergei did not choose to finish. Both end in the same safe stop (Quit anyway).
const {createQuitBound,QUIT_WAIT_BOUND_MS}=createRequire(import.meta.url)('../desktop/quit-watch.js');
const facts=(waiting,phase='finishing')=>({phase,waiting,blocked:phase==='blocked',error:phase==='blocked'?'A press is still running; ownership retained':''});
test('a failed close stops safely at once, whatever it waits for',()=>{
 assert.equal(typeof createQuitBound,'function','the bound exists');
 const clock={t:0};const bound=createQuitBound({keepConversion:true,now:()=>clock.t});
 assert.equal(bound.observe(facts([{kind:'conversion',title:'Дюна'}])),null);
 assert.equal(bound.observe(facts([{kind:'press',title:''}],'blocked')),'blocked','even with the chosen book still named');
 assert.equal(createQuitBound({now:()=>0}).observe(facts([],'blocked')),'blocked');
});
test('the book he chose to finish is waited for as before; any other work stops safely after the bound',()=>{
 assert.equal(QUIT_WAIT_BOUND_MS,15000);
 const clock={t:0};const kept=createQuitBound({keepConversion:true,now:()=>clock.t});
 for(clock.t=0;clock.t<=3600000;clock.t+=60000)assert.equal(kept.observe(facts([{kind:'conversion',title:'Дюна'},{kind:'cleanup',title:''}])),null,'an hour on the chosen book: still waiting');
 // The chosen book is done; its cleanup still runs: the bound starts now, not at the Quit.
 const start=clock.t;assert.equal(kept.observe(facts([{kind:'cleanup',title:''}])),null);
 clock.t=start+14000;assert.equal(kept.observe(facts([{kind:'cleanup',title:''}])),null);
 clock.t=start+15000;assert.equal(kept.observe(facts([{kind:'cleanup',title:''}])),'bound');
 // No book chosen (Quit with nothing converting, or a status that did not answer): a conversion is bounded like the rest.
 clock.t=0;const plain=createQuitBound({now:()=>clock.t});
 assert.equal(plain.observe(facts([{kind:'conversion',title:'Дюна'}])),null);
 clock.t=15000;assert.equal(plain.observe(facts([{kind:'conversion',title:'Дюна'}])),'bound');
 // Nothing named resets the clock; a list that changes does not.
 clock.t=0;const quiet=createQuitBound({now:()=>clock.t});
 assert.equal(quiet.observe(facts([{kind:'scan',title:''}])),null);clock.t=10000;assert.equal(quiet.observe(facts([])),null);
 clock.t=20000;assert.equal(quiet.observe(facts([{kind:'press',title:''}])),null);
 clock.t=30000;assert.equal(quiet.observe(facts([{kind:'critical',title:'move'}])),null);
 clock.t=35000;assert.equal(quiet.observe(facts([{kind:'critical',title:'move'}])),'bound');
});
test('the shell stops safely through Quit anyway on a failed close and past the bound, and keeps the chosen book',()=>{
 return import('node:fs').then(fs=>{
  const main=fs.readFileSync(new URL('../desktop/main.js',import.meta.url),'utf8');
  const watch=main.slice(main.indexOf('async function watchQuit('),main.indexOf('async function quitAnyway()'));
  assert.match(watch,/bound\.observe\(facts\)/);assert.match(watch,/return quitAnyway\(\)/);
  assert.ok(!/reportError\(/.test(watch),'no error box and no half-closed app on a failed close');
  assert.match(main,/watchQuit\(\{ keepConversion: busy\.converting === true \}\)/,'the book is kept only when Quit was accepted while it converted');
 });
});

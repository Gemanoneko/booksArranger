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

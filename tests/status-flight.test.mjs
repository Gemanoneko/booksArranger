import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const {createStatusFlight}=createRequire(import.meta.url)('../desktop/status-flight.js');

function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}
function harness(){
 const clock={t:1000};const pending=[];
 const fetch=(timeout)=>{const d=deferred();pending.push({...d,timeout});return d.promise;};
 return {clock,pending,flight:createStatusFlight({fetch,now:()=>clock.t})};
}

test('concurrent readers share one request and one answer',async()=>{
 const {pending,flight}=harness();
 const readers=Array.from({length:6},()=>flight.get());
 assert.equal(pending.length,1);assert.equal(pending[0].timeout,5000);
 pending[0].resolve({phase:'running',idle:true});
 for(const value of await Promise.all(readers))assert.deepEqual(value,{phase:'running',idle:true});
 assert.equal(flight.inFlight,false);
});

test('a finished answer is reused for one second, then refreshed',async()=>{
 const {clock,pending,flight}=harness();
 const first=flight.get();pending[0].resolve({phase:'running',n:1});await first;
 clock.t+=900;assert.deepEqual(await flight.get(),{phase:'running',n:1});assert.equal(pending.length,1);
 clock.t+=200;const next=flight.get();assert.equal(pending.length,2);pending[1].resolve({phase:'running',n:2});
 assert.deepEqual(await next,{phase:'running',n:2});
});

test('maxAge 0 never answers from the old value but still joins the request in flight',async()=>{
 const {pending,flight}=harness();
 const first=flight.get();pending[0].resolve({phase:'running'});await first;
 const fresh=flight.get({maxAge:0});const joined=flight.get({maxAge:0});
 assert.equal(pending.length,2);pending[1].resolve({phase:'finishing'});
 assert.deepEqual(await fresh,{phase:'finishing'});assert.deepEqual(await joined,{phase:'finishing'});
});

test('a short caller timeout ends only that wait; later polls join the same slow request',async()=>{
 const {pending,flight}=harness();
 await assert.rejects(flight.get({timeout:20}),/Request timed out/);
 for(let i=0;i<30;i++){const late=flight.get({timeout:5});await assert.rejects(late,/Request timed out/);}
 assert.equal(pending.length,1,'a slow engine must not receive one new request per poll');
 const waiting=flight.get();pending[0].resolve({phase:'running'});
 assert.deepEqual(await waiting,{phase:'running'});
});

test('failures are shared, never cached, and the next poll retries once',async()=>{
 const {pending,flight}=harness();
 const a=flight.get(),b=flight.get();pending[0].reject(new Error('Request timed out'));
 await assert.rejects(a,/timed out/);await assert.rejects(b,/timed out/);
 const retry=flight.get();assert.equal(pending.length,2);pending[1].resolve({phase:'running'});
 assert.deepEqual(await retry,{phase:'running'});
});

test('invalidate drops the remembered answer after a phase-changing control',async()=>{
 const {pending,flight}=harness();
 const first=flight.get();pending[0].resolve({phase:'running'});await first;
 flight.invalidate();const after=flight.get();assert.equal(pending.length,2);
 pending[1].resolve({phase:'finishing'});assert.deepEqual(await after,{phase:'finishing'});
});

test('an answer ages from when its request was sent, not when it arrived (M1)',async()=>{
 const {clock,pending,flight}=harness();
 const first=flight.get();clock.t+=800;pending[0].resolve({n:1});await first;
 clock.t+=300;// 300 ms after arrival, 1100 ms after sending
 const next=flight.get();assert.equal(pending.length,2,'an answer sent over 1 s ago must not be reused');
 pending[1].resolve({n:2});assert.deepEqual(await next,{n:2});
});

test('invalidate detaches the request in flight: it is never joined and never refills the answer (m1)',async()=>{
 const {pending,flight}=harness();
 const before=flight.get();// e.g. a tray poll sent before a Quit retry
 flight.invalidate();
 const watch=flight.get({timeout:3000,maxAge:0});// watchQuit after the retry
 assert.equal(pending.length,2,'a reader after invalidate must not join the pre-control request');
 pending[1].resolve({phase:'finishing'});pending[0].resolve({phase:'blocked'});// the stale reply lands last
 assert.deepEqual(await before,{phase:'blocked'});
 assert.deepEqual(await watch,{phase:'finishing'});
 assert.deepEqual(await flight.get(),{phase:'finishing'},'the stale reply must not replace the newer answer');
 assert.equal(pending.length,2);assert.equal(flight.inFlight,false);
});

test('a stale reply arriving after invalidate leaves nothing remembered (m1)',async()=>{
 const {pending,flight}=harness();
 const before=flight.get();flight.invalidate();pending[0].resolve({phase:'blocked'});await before;
 const next=flight.get();assert.equal(pending.length,2,'the pre-control reply must not be served from memory');
 pending[1].resolve({phase:'finishing'});assert.deepEqual(await next,{phase:'finishing'});
});

test('a backwards clock step counts as expired, never as fresh (m2)',async()=>{
 const {clock,pending,flight}=harness();
 const first=flight.get();pending[0].resolve({n:1});await first;
 clock.t-=60000;
 const next=flight.get();assert.equal(pending.length,2,'a negative age must not pin the old answer');
 pending[1].resolve({n:2});assert.deepEqual(await next,{n:2});
});

test('the default clock is monotonic: a frozen wall clock cannot pin an answer (m2)',async()=>{
 const wall=Date.now;Date.now=()=>0;
 try{
  let calls=0;const flight=createStatusFlight({fetch:()=>Promise.resolve({n:++calls}),maxAgeMs:20});
  assert.deepEqual(await flight.get(),{n:1});
  await new Promise(resolve=>setTimeout(resolve,60));
  assert.deepEqual(await flight.get(),{n:2});
 }finally{Date.now=wall;}
});

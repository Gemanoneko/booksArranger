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

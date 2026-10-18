'use strict';
// v0.16.12 (Sergei, live on v0.16.11): in Output needs attention the selection queues retries ("Retry selected (N)",
// one confirmation, one request per book, no double press) instead of the disabled "Queue selected books", and the
// selection count no longer says "need review". A pressed Retry never comes back as an enabled Retry.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
function attentionRow(name,group,job={}){
  return blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name}},{job_id:'job-'+name,reason:'raw '+name,attention:{group,cause:null,originals_untouched:true},...job});
}
const posted=route=>calls.filter(call=>call.route===route);
let retryAnswer=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  if(route==='/api/audiobook/repair'){calls.push({route,options});return {ok:true,status:202,json:async()=>({requeued:false,accepted:true,queued_next:true,position:2,kind:'repair'})};}
  if(route==='/api/audiobook/retry' && retryAnswer){calls.push({route,options});return retryAnswer(JSON.parse(options.body));}
  return baseFetch(route,options);
};
const settle=(ms=20)=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";viewControls()');
  const a=attentionRow('a','retry'),b=attentionRow('b','retry'),r=attentionRow('r','repair',{retry:undefined,repair:{allowed:true,reason:''},attention:{group:'repair',cause:null,originals_untouched:true,damage:[]}});
  const u=attentionRow('u','unsupported',{retry:undefined}),n=attentionRow('n','retry',{retry:{allowed:false,reason:'Not yet.'}});
  context.fixture=[a,b,r,u,n];run('rows=fixture.map(row=>({...row}));for(const row of rows)selectedBooks.set(row.id,row.revision);renderRows(true);batchCounts();controls()');
  // The selection speaks of retries here, not of review; "Queue selected books" gives way to "Retry selected (N)".
  assert.equal(get('batch-count').textContent,'5 selected · 3 can be retried or repaired');
  assert.equal(get('queue-books').hidden,true);assert.equal(get('retry-selected').hidden,false);assert.equal(get('retry-selected').textContent,'Retry selected (3)');assert.equal(get('retry-selected').disabled,false);
  assert.equal(get('batch-help').textContent,'Only selected books that can be retried or repaired are queued.');
  // One confirmation, Cancel first, Esc cancels and nothing is sent.
  get('retry-selected').handlers.click();
  assert.equal(get('retry-selected-confirm').hidden,false);assert.equal(get('retry-selected').hidden,true);assert.equal(document.activeElement,get('retry-selected-cancel'));
  assert.equal(get('retry-selected-question').textContent,'Queue 3 selected books to be checked again? They run one at a time, right after the current book.');
  get('retry-selected-confirm').handlers.keydown({key:'Escape',preventDefault(){}});
  assert.equal(get('retry-selected-confirm').hidden,true);assert.equal(document.activeElement,get('retry-selected'));assert.equal(posted('/api/audiobook/retry').length,0);
  // Confirmed: one request per book, Retry or Repair by its class, a double press sends nothing more; one is refused.
  retryAnswer=async data=>data.job_id==='job-b'?{ok:false,status:409,json:async()=>({error:'This book cannot be retried now.'})}:{ok:true,status:202,json:async()=>({job_id:data.job_id,requeued:true,queued_next:true,position:1,kind:'retry'})};
  get('retry-selected').handlers.click();const going=get('retry-selected-go').handlers.click();get('retry-selected-go').handlers.click();await going;await settle();
  assert.deepEqual(posted('/api/audiobook/retry').map(call=>JSON.parse(call.options.body).job_id),['job-a','job-b']);
  assert.deepEqual(posted('/api/audiobook/repair').map(call=>JSON.parse(call.options.body).job_id),['job-r']);
  assert.equal(get('retry-selected-status').textContent,'Queued 2 of 3. They run one at a time, right after the current book. 1 could not be retried.');
  // A queued book shows a disabled "Queued", even when a list from before the presses repaints it; the refused one can be pressed again.
  context.fixture=[a,b,r];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');
  const button=index=>get('inventory').children[index].children[5].children[0].children[0];
  assert.equal(button(0).textContent,'Queued');assert.equal(button(0).disabled,true);assert.equal(button(2).textContent,'Queued');
  assert.equal(button(1).textContent,'Retry');assert.equal(button(1).disabled,false,'the server refused it explicitly');
  const presses=()=>calls.filter(call=>call.route==='/api/audiobook/retry' || call.route==='/api/audiobook/repair').length,before=presses();button(0).handlers.click({stopPropagation(){}});await settle();assert.equal(presses(),before,'a queued book sends no second request');
  assert.equal(get('retry-selected').textContent,'Retry selected (1)','only the refused book is left to retry');
  // Elsewhere the selection keeps its review wording and queue button.
  run('filters.candidates="all";viewControls();batchCounts();controls()');
  assert.match(get('batch-count').textContent,/ need review$/);assert.equal(get('queue-books').hidden,false);assert.equal(get('retry-selected').hidden,true);
  console.log('PASS Retry selected in Output needs attention, its confirmation and per-book requests, no double press, remembered Queued over stale lists, review wording elsewhere');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_retry_selected_frontend.js'),module);m.filename=path.join(__dirname,'test_retry_selected_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

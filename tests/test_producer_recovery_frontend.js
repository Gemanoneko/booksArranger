'use strict';
// Real app event paths with isolated DOM/transport doubles; no browser geometry claim.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const CAP_SCHEMA='books-producer-recovery-capability-v1';
function producer(state='prepare',extra={},jobExtra={}){
  const cap={schema:CAP_SCHEMA,state,cause:state==='unsupported'?'origin_unproved':state==='waiting_restart'?'restart_unverified':'checkpoint_required',can_prepare:state==='prepare',can_retry:false,reason:'Exact backend reason',retained_files:true,...extra};
  return blocked({}, {attention:{group:'other',producer_recovery:cap,working:{state:'cleanable',bytes:12}},...jobExtra});
}
let prepareReply=null;const ordinaryFetch=context.fetch;
context.fetch=async(route,options)=>{
  if(route==='/api/audiobook/prepare-recovery'){calls.push({route,options});return prepareReply(JSON.parse(options.body));}
  return ordinaryFetch(route,options);
};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const posts=()=>calls.filter(item=>item.route==='/api/audiobook/prepare-recovery');
function paint(row){context.fixture=row;run('rows=[fixture];renderRows(true);controls()');}
function buttons(){return get('inventory').children[0].children[5].children[0].children;}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention"');
  const unsupported=producer('unsupported');paint(unsupported);show(unsupported);
  assert.equal(get('automatic-result-status').textContent,'Recovery stays blocked');
  assert.match(get('automatic-result-hint').textContent,/cannot establish where this conversion ran/);
  assert.equal(run('rowAction(fixture)'),null);assert.equal(get('clear-working').hidden,true);
  assert.ok(!buttons().some(item=>/Prepare recovery|Retry|Clear working files/.test(item.textContent)));
  const unavailable=producer('unsupported',{cause:'startup_unavailable'});show(unavailable);assert.equal(get('automatic-result-status').textContent,'Recovery check unavailable');
  const mismatch=producer('unsupported',{cause:'binding_mismatch'});show(mismatch);assert.equal(get('automatic-result-status').textContent,'Recovery checkpoint does not match');

  const prepared=producer();paint(prepared);show(prepared);const rowButton=buttons()[0];
  assert.equal(rowButton.textContent,'Prepare recovery');assert.equal(rowButton.title,"Save this job's recovery checkpoint without changing its audio files.");
  assert.equal(rowButton.getAttribute('aria-label'),'Prepare recovery: Название книги');assert.ok(rowButton.getAttribute('aria-describedby'));
  assert.equal(button.textContent,'Prepare recovery');assert.equal(get('clear-working').hidden,true);
  const field=fieldNodes.get('title');field.value='Мой несохранённый текст';field.selectionStart=3;field.selectionEnd=7;run('dirty=true');
  let reply;prepareReply=()=>new Promise(resolve=>reply=resolve);rowButton.focus();const before=posts().length;
  rowButton.handlers.click({stopPropagation(){}});await tick();
  assert.equal(posts().length,before+1);assert.deepEqual(JSON.parse(posts().at(-1).options.body),{job_id:'job-a'});
  assert.equal(rowButton.textContent,'Preparing…');assert.equal(rowButton.getAttribute('aria-disabled'),'true');assert.equal(rowButton.disabled,false);assert.equal(document.activeElement,rowButton);
  rowButton.handlers.click({stopPropagation(){}});await run('retryJob()');assert.equal(posts().length,before+1);
  reply({ok:true,status:200,json:async()=>({job_id:'job-a',producer_recovery:{...prepared.creation.job.attention.producer_recovery,state:'waiting_restart',cause:'restart_unverified',can_prepare:false,checkpoint_id:'checkpoint-1'},queued:false,outputs_changed:false})});await tick();await tick();
  assert.equal(rowButton.hidden,true);assert.equal(run('selectedRow.creation.job.attention.producer_recovery.state'),'waiting_restart');
  assert.equal(get('automatic-result-status').textContent,'Restart verification needed');assert.match(get('automatic-result-hint').textContent,/Restarting only the app will not help/);
  assert.equal(field.value,'Мой несохранённый текст');assert.equal(field.selectionStart,3);assert.equal(field.selectionEnd,7);assert.equal(run('dirty'),true);
  assert.notEqual(document.activeElement,rowButton);assert.equal(calls.filter(item=>item.route==='/api/audiobook/retry').length,0);

  run('dirty=false;retryResult=null');paint(prepared);show(prepared);button.focus();
  prepareReply=async()=>({ok:false,status:400,json:async()=>({error:'The catalog is busy.'})});await run('retryJob()');
  assert.equal(get('automatic-result-status').textContent,'Recovery checkpoint not saved');assert.match(note.textContent,/catalog is busy/);assert.doesNotMatch(note.textContent,/Restart Windows/);assert.equal(button.disabled,false);
  assert.equal(run('selectedRow.creation.job.attention.producer_recovery.state'),'prepare');
  run('retryResult=null');prepareReply=async()=>({ok:true,status:200,json:async()=>({job_id:'job-a',producer_recovery:{...prepared.creation.job.attention.producer_recovery,state:'waiting_restart'},queued:false,outputs_changed:false})});await run('retryJob()');
  assert.equal(get('automatic-result-status').textContent,'Recovery checkpoint not saved');assert.doesNotMatch(note.textContent,/Restart Windows/);assert.equal(run('selectedRow.creation.job.attention.producer_recovery.state'),'prepare');
  run('retryResult=null');prepareReply=async()=>{throw new Error('Transport interrupted');};await run('retryJob()');
  assert.equal(run('recoveryDisconnected'),true);assert.equal(note.textContent,'Could not confirm the checkpoint. Reconnect to check its saved state.');
  const offlinePosts=posts().length;await run('retryJob()');assert.equal(posts().length,offlinePosts);
  run('recoveryDisconnected=false');const acknowledged=producer('waiting_restart',{checkpoint_id:'checkpoint-from-durable-read'});show(acknowledged);assert.equal(get('automatic-result-status').textContent,'Restart verification needed');

  const ready=producer('isolated_retained',{cause:'isolated_retained',can_retry:true});show(ready);assert.equal(button.textContent,'Retry');assert.equal(button.disabled,false);assert.equal(button.title,'Check the original sources and start a new attempt. Keep the old working files.');
  const sourceBlocked=producer('isolated_retained',{cause:'isolated_retained',can_retry:false,reason:'Original sources unavailable'});show(sourceBlocked);assert.equal(button.hidden,true);assert.match(note.textContent,/Original sources unavailable/);
  const later=blocked({producer_recovery_retained:{schema:'books-producer-retention-v1',count:1,attempts:[{path:'Private/old/attempt',attempt_id:'old-attempt',reason:'Isolated, retained'}]}},{state:'Creating',attention:undefined});show(later);
  assert.equal(get('producer-retained').hidden,false);assert.match(get('producer-retained-paths').textContent,/Private\/old\/attempt/);assert.match(get('producer-retained-paths').textContent,/old-attempt/);
  run('retryResult=null');paint(prepared);show(prepared);button.focus();context.background=unsupported;
  run('selectedRow=background;rows=[background];for(const entry of rowRetries.values())entry.row=background;controls()');
  assert.equal(document.activeElement,button,'background capability changes do not programmatically move focus');
  console.log('PASS producer recovery typed states, exact POST, duplicate guard, pending focus, acknowledged-only restart copy, failure/offline retention, dirty draft/caret, Clear suppression and retained history');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module'),m=new Module(path.join(__dirname,'test_producer_recovery_frontend.js'),module);
m.filename=path.join(__dirname,'test_producer_recovery_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

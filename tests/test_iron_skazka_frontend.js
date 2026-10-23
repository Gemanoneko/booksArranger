'use strict';
// 0.21.1 Iron Inferno and Сказка rows (Judy's UX spec 2026-10-23): real app code against owned DOM/transport doubles.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const CAP='books-producer-recovery-capability-v1',GB=2432812989;
const STATEMENTS=['The interrupted conversion ran on this PC.','Since then, Windows and these files were not moved, copied, cloned or restored from a backup.'];
function skazka(cap={},job={}){return blocked({},{attention:{group:'other',producer_recovery:{schema:CAP,state:'unsupported',cause:'origin_unproved',can_prepare:false,can_retry:false,can_confirm_origin:true,reason:'Backend English reason',retained_files:true,disposal:{bytes:GB,originals:1},...cap},working:{state:'blocked'}},retry:undefined,...job});}
function iron(attention={},job={}){return blocked({},{attention:{group:'retry',cause:null,originals_untouched:true,remedy:{kind:'tag_repair',cause:'legacy_decode_failed',path:'Z:/Audio/Железная.mp3'},...attention},retry:{allowed:true,reason:''},...job});}
let convertReply=null;const ordinaryFetch=context.fetch;
context.fetch=async(route,options)=>{if(route==='/api/audiobook/confirm-convert'){calls.push({route,options});return convertReply(JSON.parse(options.body));}return ordinaryFetch(route,options);};
const tick=()=>new Promise(resolve=>setImmediate(resolve)),posts=()=>calls.filter(item=>item.route==='/api/audiobook/confirm-convert');
function paint(row){context.fixture=row;run('rows=[fixture];renderRows(true);controls()');}
function cells(){return get('inventory').children[0].children;}
function rowButton(){return cells()[5].children[0].children[0];}
const dialog=get('convert-dialog');dialog.showModal=function(){this.open=true;};dialog.close=function(){this.open=false;};
const [here,unmoved,cancel,go]=['convert-here','convert-unmoved','convert-cancel','convert-confirm'].map(get);
const trusted={isTrusted:true},tab=shiftKey=>({key:'Tab',shiftKey,preventDefault(){}});
function text(row){context.fixture=row;return run('attentionText(fixture)');}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention"');

  // Iron: a normal Retry row in Can retry; the copy never mentions the tag.
  let shown=text(iron());assert.equal(shown.status,'Stopped — ready to retry');assert.equal(shown.hint,'An MP3 file failed its audio check in an earlier app version. Retry checks it again.');
  paint(iron());show(iron());assert.equal(rowButton().textContent,'Retry');assert.equal(rowButton().title,'Check this MP3 again with this app version and queue its audiobook job.');
  assert.equal(rowButton().getAttribute('aria-label'),'Retry: Название книги');assert.doesNotMatch(JSON.stringify(shown)+rowButton().title,/tag|byte|repair/i);
  const request={accepted:true,queued_next:true,state:'queued',parent_job_id:'job-a',child_job_id:null,kind:'retry'};
  for(const [origin,hint] of [['automatic','Queued by automatic processing. Nothing to do.'],[undefined,'The book is checked again before it runs.']]){
    const queuedRow=iron({group:'checking',readmission:{...request,origin},remedy:undefined},{readmission:{...request,origin},retry:undefined});
    shown=text(queuedRow);assert.equal(shown.status,'Waiting for retry checks');assert.equal(shown.hint,hint);
    context.fixture=queuedRow;assert.equal(run('rowAction(fixture).label'),'Waiting for retry checks');assert.equal(run('rowAction(fixture).data.allowed'),false);
  }
  shown=text(iron({group:'other',remedy:{kind:'replace_source',cause:'source_decode_failed',path:'Z:/a.mp3'}},{retry:undefined}));assert.equal(shown.status,'Source audio needs replacement');

  // Сказка K0: Convert… opens the confirmation; nothing is sent by opening it.
  const k0=skazka();shown=text(k0);assert.equal(shown.status,'Stopped — needs your confirmation');assert.equal(shown.hint,"The app can't tell where this conversion ran.");assert.ok(!shown.warn);
  paint(k0);show(k0);let button=rowButton();assert.equal(button.textContent,'Convert…');
  assert.equal(button.title,'Confirm where this conversion ran, then convert this book. Opens a confirmation first.');assert.equal(button.getAttribute('aria-label'),'Convert: Название книги');
  button.focus();button.handlers.click({stopPropagation(){}});await tick();
  assert.equal(posts().length,0);assert.equal(dialog.open,true);assert.equal(document.activeElement,cancel);assert.equal(here.checked,false);assert.equal(unmoved.checked,false);
  assert.equal(get('convert-dialog-delete').textContent,'When the new conversion is verified, the old working files (about 2.3 GB) and the original are deleted.');
  assert.equal(go.getAttribute('aria-disabled'),'true');assert.equal(go.title,'Tick both statements first.');
  for(const expected of [here,unmoved,go,cancel]){dialog.handlers.keydown(tab(false));assert.equal(document.activeElement,expected);}  // Cancel, box 1, box 2, Confirm
  dialog.handlers.keydown(tab(true));assert.equal(document.activeElement,go);
  let prevented=false;here.handlers.keydown({key:'Enter',preventDefault(){prevented=true;}});assert.ok(prevented,'Enter on a box does nothing');
  here.checked=true;here.handlers.change();go.handlers.click(trusted);await tick();
  assert.equal(posts().length,0);assert.equal(dialog.open,true);assert.equal(get('convert-dialog-status').textContent,'Tick both statements first.');
  unmoved.checked=true;unmoved.handlers.change();assert.equal(go.getAttribute('aria-disabled'),'false');assert.equal(go.title,'Save your confirmation and start converting this book.');
  go.handlers.click({isTrusted:false});await tick();assert.equal(posts().length,0,'a synthetic click never confirms');assert.equal(dialog.open,true);
  dialog.handlers.keydown({key:'Escape',preventDefault(){}});assert.equal(dialog.open,false);assert.equal(document.activeElement,button);
  button.handlers.click({stopPropagation(){}});await tick();assert.equal(here.checked,false,'never remembered');assert.equal(unmoved.checked,false);

  // Confirm and convert: one POST with the statements verbatim, K2 while pending, then the queued words (K4).
  let reply;convertReply=()=>new Promise(resolve=>reply=resolve);here.checked=unmoved.checked=true;here.handlers.change();go.handlers.click(trusted);await tick();
  assert.equal(dialog.open,false);assert.equal(posts().length,1);assert.deepEqual(JSON.parse(posts()[0].options.body),{library:'Audiobooks',id:'cand-a',revision:4,job_id:'job-a',statements:STATEMENTS});
  assert.equal(button.textContent,'Starting…');assert.equal(button.getAttribute('aria-disabled'),'true');assert.equal(document.activeElement,button);
  assert.equal(cells()[4].firstChild?.nodeValue ?? run('candidateStatus(rows[0])'),'Starting conversion…');assert.equal(run('rowState(rows[0]).hint'),'Saving your confirmation, then checking the book.');
  reply({ok:true,status:202,json:async()=>({job_id:'job-a',requeued:false,accepted:true,queued_next:true,position:1,kind:'retry',state:'queued',parent_job_id:'job-a',child_job_id:null,origin_recorded:true,producer_recovery:{...k0.creation.job.attention.producer_recovery,state:'ready'}})});
  for(let i=0;i<6;i++)await tick();
  assert.equal(run('candidateStatus(rows[0])'),'Waiting for retry checks');assert.equal(note.textContent,'Confirmed. Starting conversion.');assert.notEqual(run('rowState(rows[0]).hint'),'Confirmed. Starting conversion.');

  // R1a: no restart since the attempt; the confirmation is kept and no button is offered.
  const r1a=skazka({state:'waiting_restart',cause:'restart_unproven',can_confirm_origin:false});inventoryRows=[r1a];  // the server's next read
  run('retryResult=null;heldRow=null;pressed.clear()');paint(k0);show(k0);button=rowButton();
  convertReply=async()=>({ok:true,status:202,json:async()=>({job_id:'job-a',accepted:false,queued_next:false,origin_recorded:true,producer_recovery:{...k0.creation.job.attention.producer_recovery,state:'waiting_restart',cause:'restart_unproven',can_confirm_origin:false}})});
  button.handlers.click({stopPropagation(){}});await tick();here.checked=unmoved.checked=true;here.handlers.change();go.handlers.click(trusted);for(let i=0;i<6;i++)await tick();
  shown=run('rowState(rows[0])');assert.equal(shown.status,'Stopped — restart Windows first');assert.equal(shown.hint,"Windows hasn't restarted since this conversion ran. Restart it, then reopen the app.");assert.ok(shown.warn);
  assert.equal(run('rowAction(rows[0])'),null);assert.equal(run('cellTip(rows[0])'),'The app confirms the old conversion ended by checking that Windows restarted after it. Your confirmation is kept; Retry appears after the restart.');
  shown=text(skazka({cause:'startup_unavailable',can_confirm_origin:false}));assert.equal(shown.status,'Recovery check unavailable');assert.equal(shown.hint,"The app can't read when Windows started, so it can't confirm the old conversion ended. Files are kept.");assert.doesNotMatch(shown.hint,/Backend English/);

  // R3 refused, the book changed, and R3b connection lost: nothing changed, Convert… stays where it applies.
  for(const [answer,status,hint] of [[{ok:false,status:409,json:async()=>({error:'Scanning is running. Convert when it stops.'})},'Conversion not started','Nothing was changed. Scanning is running. Convert when it stops.'],
      [{ok:false,status:409,json:async()=>({error:'This book changed. Review its details and try again.',cause:'book_changed'})},'Conversion not started','This book changed. Review its details and try again.'],[null,'Conversion status unknown','Could not confirm the request. Reconnect to check its saved state.']]){
    inventoryRows=[k0];run('retryResult=null;heldRow=null;recoveryDisconnected=false;pressed.clear()');paint(k0);show(k0);button=rowButton();convertReply=async()=>{if(!answer)throw new Error('transport lost');return answer;};
    button.handlers.click({stopPropagation(){}});await tick();here.checked=unmoved.checked=true;here.handlers.change();go.handlers.click(trusted);for(let i=0;i<6;i++)await tick();
    shown=run('rowState(rows[0])');assert.equal(shown.status,status);assert.equal(shown.hint,hint);assert.ok(shown.warn);
    if(answer)assert.equal(run('rowAction(rows[0]).label'),'Convert…');else assert.equal(run('recoveryDisconnected'),true);
  }
  run('retryResult=null;recoveryDisconnected=false');paint(k0);show(k0);button=rowButton();const before=posts().length;
  button.handlers.click({stopPropagation(){}});await tick();context.changed=skazka({reason:'Another backend state'});run('rows=[changed];selectedRow=changed');
  here.checked=unmoved.checked=true;here.handlers.change();go.handlers.click(trusted);await tick();
  assert.equal(posts().length,before);assert.equal(run('rowState(rows[0]).hint'),'This book changed. Review its details and try again.');

  // K3 (after R1a and a restart): a plain Retry whose copy carries the deletion line; R2 when no confirmation is saved.
  run('retryResult=null');const k3=skazka({state:'ready',cause:'boot_after_attempt',basis:'boot_after_attempt',can_retry:true,can_confirm_origin:false},{retry:{allowed:true,reason:''}});
  shown=text(k3);assert.equal(shown.status,'Stopped — ready to retry');assert.equal(shown.hint,'When the new conversion is verified, the old working files (about 2.3 GB) and the original are deleted.');
  paint(k3);show(k3);button=rowButton();assert.equal(button.textContent,'Retry');assert.equal(button.title,'Start a new conversion. When it is verified, the old working files and the original are deleted.');
  retryOverride=async()=>({ok:false,status:409,json:async()=>({error:'No confirmation is saved for this book.',cause:'origin_unconfirmed'})});await run('retryJob()');retryOverride=null;
  context.fixture=k0;run('rows=[fixture];selectedRow=fixture');shown=run('rowState(rows[0])');assert.equal(shown.status,'Stopped — needs your confirmation');assert.equal(shown.hint,'No confirmation is saved for this book.');
  assert.match(run('deletionLine({disposal:{bytes:10,originals:2}})'),/ and the originals are deleted\.$/);
  // "Old working files kept": the removal sentence only for an attempt that is removed after verification.
  for(const [flag,hidden] of [[true,false],[undefined,true]]){context.fixture=blocked({producer_recovery_retained:{schema:'books-producer-retention-v1',count:1,attempts:[{path:'Old/attempt',attempt_id:'a',reason:'kept',removed_after_verification:flag}]}},{state:'Creating',attention:undefined});
    run('renderProducerRetained(fixture)');assert.equal(get('producer-retained').hidden,false);assert.equal(get('producer-retained-removal').hidden,hidden);}
  console.log('PASS Iron Retry row and automatic queue hint; Сказка Convert…, confirmation dialog (Tab cycle, default focus, Esc, inert until both ticked, trusted press only), K2/K4, R1a, R1b, R2, R3, R3b, changed book, K3 deletion line');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module'),m=new Module(path.join(__dirname,'test_iron_skazka_frontend.js'),module);
m.filename=path.join(__dirname,'test_iron_skazka_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

'use strict';
// v0.16.7 needs-attention actions (Docs/BooksArranger_AttentionActions_Spec.md, amended): classes and hints,
// row Retry and Repair, the repaired record, the group strip and the server-side Retry all with its inline
// confirmation, the book-list loading state and request discipline, and two progress-row fixes. Runs the
// real frontend on the Retry test's DOM/transport doubles.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
function attentionRow(name,group,extra={},job={}){
  return blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name},...extra},{job_id:'job-'+name,reason:'raw reason '+name,attention:{group,cause:group==='retry'?'busy':null,originals_untouched:true},...job});
}
const DANGLING={kind:'dangling_chapter_reference',removed:[3],description:'The chapter list pointed to missing track 3. That pointer was removed; audio and chapters are unchanged.'};
function damaged(name,damage=[DANGLING]){return attentionRow(name,'repair',{},{attention:{group:'repair',cause:null,originals_untouched:true,damage},retry:undefined,repair:{allowed:true,reason:''}});}
function statusCell(tr){return tr.children[4];}
// 0.22.1: a hidden Cancel retry / Cancel delete sits beside a queueable face (Judy 1.3); the slots below count the others.
function actionButtons(tr){return tr.children[5].children[0].children.filter(b=>!String(b.className || '').includes('row-cancel'));}
const posted=route=>calls.filter(call=>call.route===route);
let repairOverride=null,retryAllOverride=null,stateOverride503=false;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  if(stateOverride503 && route.startsWith('/api/state')){calls.push({route,options});return {ok:false,status:503,json:async()=>({error:'Status is still updating; retrying'})};}
  if(route==='/api/audiobook/repair'){calls.push({route,options});const data=JSON.parse(options.body);return repairOverride?repairOverride(data):{ok:true,status:202,json:async()=>({requeued:true,job_id:'child-'+data.job_id})};}
  if(route==='/api/audiobook/retry-all'){calls.push({route,options});return retryAllOverride?retryAllOverride(JSON.parse(options.body)):{ok:true,status:202,json:async()=>({retry_all:{id:'run-1',state:'running',total:121,done:0,queued:0,refused:0}})};}
  return baseFetch(route,options);
};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
// Futaba's 0.22.0 QA, m-6: the cell tooltip carries no raw text (the spec's check 3); the technical message is read from
// technicalText(), which Technical details shows.
function techOf(tr){const title=tr.children[4].title || '';assert.ok(!/Technical detail|WinError|Header missing|ffmpeg|audio-staging/.test(title),'m-6: no raw text in the cell tooltip: '+title);return run('technicalText(rows.find(row=>row.path==='+JSON.stringify(tr.dataset.path)+'))');}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";viewControls()');
  // Class copy comes from the API class, never from the reason text; missing class falls back.
  const retry=attentionRow('a','retry'),space=attentionRow('b','retry',{},{attention:{group:'retry',cause:'space',originals_untouched:true},retry:{allowed:false,reason:'Not enough free disk space yet. Free up space, then retry.'}});
  const unsupported=attentionRow('c','unsupported',{},{retry:undefined}),other=attentionRow('d','other',{},{retry:undefined}),repair=damaged('r');
  const status=row=>run('candidateStatus('+JSON.stringify(row)+')');
  assert.equal(status(retry),'Stopped — ready to retry');assert.equal(status(space),'Stopped — not enough disk space');
  assert.equal(status(unsupported),"Can't convert — M4B not supported");assert.equal(status(other),'Stopped — see details');assert.equal(status(repair),'Damaged — can repair');
  assert.equal(status(blocked({},{attention:undefined})),'Stopped — see details','older data without a class: raw text never prints (Judy 2026-10-24)');

  // Rows: short status, hint line, technical detail on hover; Retry or Repair first, only with API data.
  context.fixture=[retry,space,unsupported,other,repair];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');
  const trs=get('inventory').children;assert.equal(trs.length,5);
  assert.equal(statusCell(trs[0]).textContent,'Stopped — ready to retry');assert.equal(statusCell(trs[0]).children[0].textContent,'Safe to retry now.');
  assert.equal(techOf(trs[0]),'Technical detail: raw reason a');
  assert.equal(actionButtons(trs[0])[0].textContent,'Retry');assert.equal(actionButtons(trs[0])[0].disabled,false);assert.equal(actionButtons(trs[0])[0].getAttribute('aria-label'),'Retry: Title a');
  assert.equal(actionButtons(trs[0])[0].className.split(' ').includes('quiet'),true,'row actions are quiet; the accent fill is for Retry all');
  assert.equal(statusCell(trs[1]).children[0].textContent,'Not enough free disk space yet. Free up space, then retry.','an unavailable reason replaces the hint');assert.equal(actionButtons(trs[1])[0].disabled,true);
  assert.equal(statusCell(trs[2]).children[0].textContent,'Nothing to do for now. Originals are untouched.');assert.notEqual(actionButtons(trs[2])[0].textContent,'Retry','no button, not even a disabled one');
  assert.equal(statusCell(trs[3]).children[0].textContent,'The conversion stopped. Select the row to read the technical message.');assert.notEqual(actionButtons(trs[3])[0].textContent,'Retry');
  // Damaged: the damage line, Repair and never Retry; the technical note joins the hover detail.
  assert.equal(statusCell(trs[4]).children[0].textContent,'The chapter list points to a missing part. Repair removes that pointer.');
  assert.equal(techOf(trs[4]),'Technical detail: raw reason r — '+DANGLING.description);
  assert.equal(actionButtons(trs[4])[0].textContent,'Repair');assert.equal(actionButtons(trs[4])[0].getAttribute('aria-label'),'Repair: Title r');
  assert.equal(actionButtons(trs[4])[0].title,'Patch the damage found in this book, then queue its audiobook job.');
  assert.ok(![...actionButtons(trs[4])].some(button=>button.textContent==='Retry'),'a damaged book never shows both');
  assert.equal(run('damageHint('+JSON.stringify({damage:[{kind:'future_kind'}]})+')'),'The app found damage it can patch. Repair fixes it.','unknown kind');
  assert.equal(run('damageHint('+JSON.stringify({damage:[{kind:'mdat_tail_overrun',padding:8}]})+')'),'The file claims a few bytes past its end. Repair adds them; no audio is missing.');
  assert.equal(run('damageHint('+JSON.stringify({damage:[{kind:'truncated_final_frames',frames:1,replaced_ticks:1024,timescale:44100}]})+')'),'The last 0.02 s of audio is missing. Repair fills it with silence.');
  assert.equal(run('patchCopy('+JSON.stringify({kind:'truncated_final_frames'})+')'),'Filled the missing end of the audio with silence.','no amount from the API, no number');
  // 0.22.1 (Judy 1.1): Retry is no longer disabled while another press runs; it stays enabled and a press is queued.
  run('busy=true;controls()');assert.equal(actionButtons(trs[0])[0].disabled,false);assert.equal(actionButtons(trs[0])[0].title,'Queue this retry. Another operation is in progress; it starts when the current operation finishes.');assert.equal(statusCell(trs[0]).children[0].textContent,'Safe to retry now.','busy is tooltip only');run('busy=false;controls()');

  // Row Retry: one request, pending hint, then the book is queued; focus lands back in the list.
  let answer;retryOverride=()=>new Promise(resolve=>{answer=resolve;});inventoryRows=[space,unsupported,other,repair];const sent=calls.length;
  actionButtons(trs[0])[0].handlers.click({stopPropagation(){}});await tick();
  assert.equal(statusCell(trs[0]).children[0].textContent,'Checking this book…');assert.equal(actionButtons(trs[0])[0].textContent,'Checking…');
  actionButtons(trs[0])[0].handlers.click({stopPropagation(){}});
  answer({ok:true,status:202,json:async()=>({requeued:true})});await new Promise(resolve=>setTimeout(resolve,20));
  const posts=calls.slice(sent).filter(call=>call.route==='/api/audiobook/retry');assert.equal(posts.length,1);assert.equal(JSON.parse(posts[0].options.body).job_id,'job-a');
  // v0.16.12: the book stays where it was, disabled "Queued", and keeps focus; it never lands on a neighbour's Retry.
  assert.equal(get('inventory').children.length,5);assert.equal(get('inventory').children[0].dataset.path,'cand-a');assert.equal(document.activeElement,get('inventory').children[0]);
  assert.equal(actionButtons(get('inventory').children[0])[0].textContent,'Queued');assert.equal(actionButtons(get('inventory').children[0])[0].disabled,true);
  assert.equal(get('retry-all-status').textContent,'Title a queued — runs next','a note in place says which book was queued');
  retryOverride=null;

  // Queue next (M4B): accepted while a book converts; the row and panel say when it runs, with no button to press twice.
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,current_job_id:'job-running'}};run('state='+JSON.stringify(backend));
  const m4b=attentionRow('m','retry',{},{attention:{group:'retry',cause:null,originals_untouched:true}});
  const m4bQueued={...m4b,creation:{...m4b.creation,job:{...m4b.creation.job,readmission:{accepted:true,queued_next:true,position:1,kind:'retry',state:'queued'}}}};
  context.fixture=[m4b];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');
  retryOverride=async data=>({ok:true,status:202,json:async()=>({job_id:data.job_id,requeued:false,accepted:true,queued_next:true,position:1,kind:'retry',state:'queued'})});
  inventoryRows=[m4bQueued];const m4bSent=calls.length;
  actionButtons(get('inventory').children[0])[0].handlers.click({stopPropagation(){}});await new Promise(resolve=>setTimeout(resolve,20));
  assert.equal(calls.slice(m4bSent).filter(call=>call.route==='/api/audiobook/retry').length,1);
  let m4bRow=get('inventory').children[0];
  assert.equal(statusCell(m4bRow).textContent,'Waiting for retry checks');assert.equal(statusCell(m4bRow).children[0].textContent,'The book is checked again before it runs.');
  assert.ok(![...actionButtons(m4bRow)].some(button=>/^Retry/.test(button.textContent)),'no button to press twice');
  assert.equal(get('automatic-result-status').textContent,'Waiting for retry checks');
  assert.equal(get('retry-block').hidden,false);assert.equal(get('retry-job').textContent,'Waiting for retry checks');assert.equal(get('retry-job').disabled,true,'a saved request cannot be pressed again');
  assert.equal(actionButtons(m4bRow)[0].textContent,'Waiting for retry checks');assert.equal(actionButtons(m4bRow)[0].disabled,true);
  get('filter').value='all';await get('filter').handlers.change();
  assert.equal(statusCell(get('inventory').children[0]).textContent,'Waiting for retry checks','the saved request survives a filter change without claiming a conversion job');
  run('filters.candidates="output_attention";viewControls()');
  assert.equal(run('queuedNextText({position:3})'),'Queued — runs after 3 books');
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,current_job_id:null}}');assert.equal(run('queuedNextText({position:1})'),'Queued — runs next','nothing running');
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,current_job_id:"job-running"}}');
  // A refusal found by the worker is shown for that book in the UI's own words, keyed by its typed cause
  // (RefusedRetry spec 2026-10-19); a review change offers no Retry, and the raw text stays in Technical detail.
  const refusedM4b={...m4b,creation:{...m4b.creation,job:{...m4b.creation.job,retry:undefined,attention:{group:'other',cause:null,originals_untouched:true},readmission:{accepted:false,queued_next:false,reason:'Failed M4B retained: Reviewed candidate changed during source proof',kind:'retry',state:'refused',cause:'source_changed',fix:'review',stale:false}}}};
  context.fixture=[refusedM4b];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');m4bRow=get('inventory').children[0];
  assert.equal(statusCell(m4bRow).textContent,'Stopped — review changed');
  // Superseded by follow-up 2, section 1.2 (Sergei: Start over, with automatic re-processing): the hint names Start over.
  assert.equal(statusCell(m4bRow).children[0].textContent,"Retry was refused: the book's review or source files changed. Start over sends it back to automatic processing.");assert.ok(statusCell(m4bRow).children[0].classes.has('retry-refused'));
  assert.ok(![...actionButtons(m4bRow)].some(button=>button.textContent==='Retry'),'no Retry that cannot work');
  assert.equal(actionButtons(m4bRow)[0].textContent,'Start over','Start over in the Retry slot');
  assert.match(techOf(m4bRow),/^Technical detail: Failed M4B retained: Reviewed candidate changed during source proof; earlier failure: /);
  // A queued child outside the attention list says the same.
  assert.equal(status(blocked({status:'Queued',creation:{status:'Queued',reasons:[],job:{job_id:'child-m',state:'Queued',stage:'queued',reason:'',readmission:{accepted:true,queued_next:true,position:2,kind:'repair',state:'admitted'}}}})),'Queued — runs after 2 books');
  // v0.16.8: the press got no reply but it landed: the page asks the server and shows Queued, never an error.
  const timedOut=attentionRow('t','retry',{},{attention:{group:'retry',cause:null,originals_untouched:true}});
  const timedOutQueued={...timedOut,creation:{...timedOut.creation,job:{...timedOut.creation.job,readmission:{accepted:true,queued_next:true,position:2,kind:'retry',state:'admitted'}}}};
  context.fixture=[timedOut];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');
  retryOverride=async()=>{throw new TypeError('Failed to fetch');};inventoryRows=[timedOutQueued];
  context.setTimeout=setTimeout;actionButtons(get('inventory').children[0])[0].handlers.click({stopPropagation(){}});await new Promise(resolve=>setTimeout(resolve,40));
  const landedRow=get('inventory').children[0];
  assert.equal(statusCell(landedRow).textContent,'Queued — runs after 2 books');assert.equal(actionButtons(landedRow)[0].textContent,'Queued');assert.equal(actionButtons(landedRow)[0].disabled,true);
  assert.equal(run('recoveryDisconnected'),false,'no connection alarm for a press that landed');
  // A busy status read (503) is not a lost connection: Retry stays available.
  // poll() schedules the next poll: keep the harness's inert timer for it, so the script can exit.
  const liveTimeout=context.setTimeout;context.setTimeout=()=>0;stateOverride503=true;await run('poll()');stateOverride503=false;context.setTimeout=liveTimeout;assert.equal(run('recoveryDisconnected'),false);
  retryOverride=null;context.fixture=[space,unsupported,other,repair];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');inventoryRows=[space,unsupported,other,repair];

  // Row Repair: its own endpoint and pending copy; a refusal shows the server message in the hint.
  const repairRow=()=>[...get('inventory').children].find(tr=>tr.dataset.path==='cand-r');
  repairOverride=async()=>({ok:false,status:409,json:async()=>({error:'This book cannot be repaired.'})});
  actionButtons(repairRow())[0].handlers.click({stopPropagation(){}});await new Promise(resolve=>setTimeout(resolve,20));
  assert.equal(posted('/api/audiobook/repair').length,1);assert.deepEqual(JSON.parse(posted('/api/audiobook/repair')[0].options.body),{library:'Audiobooks',id:'cand-r',revision:4,job_id:'job-r',queue:true,title:'Title r'});
  assert.equal(statusCell(repairRow()).children[0].textContent,'This book cannot be repaired.');assert.ok(statusCell(repairRow()).children[0].classes.has('retry-refused'));
  let repairAnswer;repairOverride=()=>new Promise(resolve=>{repairAnswer=resolve;});
  actionButtons(repairRow())[0].handlers.click({stopPropagation(){}});await tick();
  assert.equal(actionButtons(repairRow())[0].textContent,'Repairing…');assert.equal(statusCell(repairRow()).children[0].textContent,'Repairing this book…');
  inventoryRows=[space,unsupported,other];repairAnswer({ok:true,status:202,json:async()=>({requeued:true})});await new Promise(resolve=>setTimeout(resolve,20));
  assert.equal(posted('/api/audiobook/repair').length,2);assert.equal(get('retry-all-status').textContent,'Repair queued: The chapter list points to a missing part. Repair removes that pointer.');
  assert.equal(get('retry-all-line').hidden,false);repairOverride=null;

  // After Repair the row and the details panel keep the record, in any status.
  const repairedJob=(applied)=>({job_id:'child-r',state:'Queued',stage:'queued',reason:'',repaired:{applied,patched:[{kind:'mdat_tail_overrun',padding:8},{kind:'dangling_chapter_reference',removed:[3]}],detail:'The audio container declared 8 bytes past the end of the file.'}});
  const queuedRepair=blocked({id:'cand-q',path:'cand-q',title_clue:'Title q',status:'Queued',creation:{status:'Queued',reasons:[],job:repairedJob(false)}});
  context.fixture=[queuedRepair];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');
  assert.equal(statusCell(get('inventory').children[0]).children[0].textContent,'Repair queued: Added 8 missing bytes at the end of the file. No audio was missing. +1 more');
  const doneRepair={...queuedRepair,status:'Audiobook created',audiobook_ready:true,creation:{status:'Audiobook created',reasons:[],job:{...repairedJob(true),state:'Audiobook created'}}};
  context.fixture=doneRepair;run('automaticResultKey=null;renderAutomaticResult(fixture)');
  assert.equal(get('automatic-repaired').hidden,false);assert.equal(get('automatic-repaired-title').textContent,'Repaired');
  assert.deepEqual(get('automatic-repaired-list').children.map(item=>item.textContent),['Added 8 missing bytes at the end of the file. No audio was missing.','Removed a chapter-list pointer to a missing part.']);
  assert.equal(get('automatic-technical').textContent,'Technical detail: The audio container declared 8 bytes past the end of the file.');
  context.fixture=[doneRepair];run('rows=fixture.map(row=>({...row}));renderRows(true)');assert.match(statusCell(get('inventory').children[0]).children[0].textContent,/^Repaired: Added 8 missing bytes/);

  // Group strip: live counts with Can repair, pressed state and a group request.
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,queued:5,attention_counts:{retry:121,repair:2,other:1,unsupported:0}}};run('state='+JSON.stringify(backend)+';controls()');
  assert.equal(get('attention-groups').hidden,false);assert.equal(get('group-all').textContent,'All · 124');assert.equal(get('group-repair').textContent,'Can repair · 2');assert.equal(get('group-unsupported').textContent,'M4B not supported · 0');
  assert.equal(get('group-all').getAttribute('aria-pressed'),'true');assert.equal(get('retry-all').hidden,true,'never in All');
  assert.equal(get('retry-all-status').textContent,'Repair queued: The chapter list points to a missing part. Repair removes that pointer.','the repair line stays while the filter does');
  const second=attentionRow('e','retry');inventoryRows=[retry,second];const before=calls.length;await get('group-retry').handlers.click();
  assert.match(calls.slice(before).find(call=>call.route.startsWith('/api/inventory')).route,/&status=output_attention&group=retry$/);
  assert.equal(get('retry-all-line').hidden,true,'a group change clears the strip line');
  // Retry all: the whole server group (121) while the page shows 2, behind an inline confirmation.
  assert.equal(get('group-retry').getAttribute('aria-pressed'),'true');assert.equal(get('retry-all').hidden,false);assert.equal(get('retry-all').textContent,'Retry all (121)');
  assert.equal(get('retry-all').title,'Request retries for these 121 books. Each book is checked before a conversion job can be queued.');
  get('retry-all').handlers.click();
  assert.equal(get('retry-all').hidden,true);assert.equal(get('retry-all-confirm').hidden,false);assert.equal(document.activeElement,get('retry-all-cancel'),'focus on the safe default');
  assert.equal(get('retry-all-question').textContent,'Request retries for 121 books? Each book is checked before a conversion job can be queued.');assert.equal(get('retry-all-go').textContent,'Request 121 retries');
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:{retry:118,repair:2,other:1,unsupported:0}}};run('state='+JSON.stringify(backend)+';controls()');
  assert.equal(get('retry-all-go').textContent,'Request 121 retries','polls never rebuild the confirmation');
  get('retry-all-confirm').handlers.keydown({key:'Escape',preventDefault(){}});
  assert.equal(get('retry-all-confirm').hidden,true);assert.equal(get('retry-all').hidden,false);assert.equal(document.activeElement,get('retry-all'));assert.equal(posted('/api/audiobook/retry-all').length,0);
  // A state poll begun before acceptance must not erase the new bulk run when
  // its delayed answer arrives (the old answer contains no retry_all field).
  const preBulkState=JSON.parse(JSON.stringify(backend)),preBulkFetch=context.fetch;let releasePreBulk;
  const preBulkGate=new Promise(resolve=>{releasePreBulk=resolve;});
  context.fetch=async(route,options)=>route.startsWith('/api/state')?(await preBulkGate,{ok:true,json:async()=>preBulkState}):preBulkFetch(route,options);
  const preBulkPoll=run('refresh()');await tick();
  get('retry-all').handlers.click();await get('retry-all-go').handlers.click();
  releasePreBulk();await preBulkPoll;context.fetch=preBulkFetch;
  assert.equal(run('bulkRunning()'),true,'a stale status poll must not erase the accepted Retry all run');
  assert.equal(get('retry-all').disabled,true,'Retry all stays disabled while its accepted run is active');
  assert.equal(posted('/api/audiobook/retry-all').length,1);assert.deepEqual(JSON.parse(posted('/api/audiobook/retry-all')[0].options.body),{library:'Audiobooks'});
  assert.equal(get('retry-all-status').textContent,'Requesting retries.');assert.match(fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),/<span id="retry-all-status" role="status" tabindex="-1"><\/span><span id="retry-all-count"><\/span>/,'the running count sits outside the live region');
  // While it runs: the count outside the live region, every action disabled.
  context.fixture=[retry,second];run('rows=fixture.map(row=>({...row}));renderRows(true)');
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,retry_all:{id:'run-1',state:'running',total:121,done:37,queued:36,refused:1}}};run('state='+JSON.stringify(backend)+';controls()');
  assert.equal(get('retry-all-count').textContent,'37 of 121 processed');assert.equal(get('retry-all-status').textContent,'Requesting retries.','current submission progress is distinct from queued jobs');
  assert.equal(get('retry-all').disabled,true);assert.equal(actionButtons(get('inventory').children[0])[0].disabled,true);
  // The end: one line, the list reloads, focus returns to the group.
  context.setTimeout=setTimeout;
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,retry_all:{id:'run-1',state:'done',total:121,done:121,accepted:119,queued:119,next:119,refused:2}}};run('state='+JSON.stringify(backend)+';controls()');
  assert.equal(get('retry-all-status').textContent,'Retry requested for 119 of 121 books. 2 refused. Current retry progress unavailable.');assert.equal(get('retry-all-count').textContent,'');
  await new Promise(resolve=>setTimeout(resolve,30));assert.notEqual(document.activeElement,null,'completion preserves a real focus target');
  run('controls()');assert.equal(get('retry-all-status').textContent,'Retry requested for 119 of 121 books. 2 refused. Current retry progress unavailable.','the end line stays until the group or filter changes');
  // A refused start shows the server message.
  retryAllOverride=async()=>({ok:false,status:409,json:async()=>({error:'Retry all is already running.'})});
  get('retry-all').handlers.click();await get('retry-all-go').handlers.click();assert.equal(get('retry-all-status').textContent,'Retry all is already running.');retryAllOverride=null;
  // Leaving the filter resets the group and the strip.
  get('filter').value='all';await get('filter').handlers.change();assert.equal(run('attentionGroup'),'all');assert.equal(get('attention-groups').hidden,true);assert.equal(run('stripNote'),'');
  run('filters.candidates="output_attention";viewControls()');

  // Details panel: the hint under the status and the technical detail as the last line (a fresh view: no remembered press).
  run("pressed.clear()");
  context.fixture=retry;run('automaticResultKey=null;renderAutomaticResult(fixture)');
  assert.equal(get('automatic-result-hint').textContent,'Safe to retry now.');assert.equal(get('automatic-result-hint').hidden,false);
  assert.equal(get('automatic-technical').textContent,'Technical detail: raw reason a');assert.equal(get('automatic-repaired').hidden,true);
  context.fixture=blocked({},{attention:undefined});run('automaticResultKey=null;renderAutomaticResult(fixture)');assert.equal(get('automatic-technical').hidden,false);assert.equal(get('automatic-technical').textContent,'Technical detail: '+JOB_REASON,'no typed cause: its text is in Technical details only (Judy 2026-10-24)');
  // The details-panel action reads Repair for a damaged book.
  show(damaged('p'));run('controls()');assert.equal(get('retry-job').textContent,'Repair');assert.equal(get('retry-job').title,'Patch the damage found in this book, then queue its audiobook job.');

  // 1a: while a list is on its way, polls do not restart it; a changed list shows a loading state, not the old rows.
  let slow;inventoryOverride=()=>new Promise(resolve=>{slow=resolve;});const listed=()=>calls.filter(call=>call.route.startsWith('/api/inventory')).length;
  run('selectedPath=null;selectedRow=null');
  const startCount=listed();const first=run('refresh()');await tick();
  assert.equal(listed(),startCount+1);assert.equal(await run('refresh()'),true);assert.equal(listed(),startCount+1,'a poll never restarts the pending list');
  slow({ok:true,json:async()=>({rows:[retry],total:1})});await first;
  context.fixture=[retry,other];run('rows=fixture.map(row=>({...row}));renderRows(true)');assert.equal(get('inventory').children.length,2);
  let pendingList;inventoryOverride=()=>new Promise(resolve=>{pendingList=resolve;});get('filter').value='all';const changing=get('filter').handlers.change();await tick();
  assert.equal(get('inventory').children.length,0,'the old list is not shown as the new result');assert.equal(get('page').textContent,'Loading All candidates…');assert.equal(get('empty').hidden,false);
  document.activeElement=null;pendingList({ok:true,json:async()=>({rows:[other],total:1})});await changing;
  assert.equal(get('inventory').children.length,1);assert.match(get('page').textContent,/All candidates/);inventoryOverride=null;
  // QA v0.16.7: a slow status read never delays the loading text, the list request or its rows.
  let stateGate;const stateWait=new Promise(resolve=>{stateGate=resolve;}),listFetch=context.fetch;
  context.fetch=async(route,options)=>{if(route.startsWith('/api/state'))await stateWait;return listFetch(route,options);};
  let listGate;inventoryOverride=()=>new Promise(resolve=>{listGate=resolve;});
  const beforeSlow=calls.length;get('filter').value='output_attention';const slowChange=get('filter').handlers.change();await tick();
  assert.match(get('page').textContent,/^Loading Output needs attention/,'loading shows at once');
  assert.ok(calls.slice(beforeSlow).some(call=>call.route.startsWith('/api/inventory')),'the list is asked for while the status read is pending');
  listGate({ok:true,json:async()=>({rows:[retry],total:1})});await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(get('inventory').children.length,1,'the rows paint before the status answers');
  stateGate();await slowChange;context.fetch=listFetch;inventoryOverride=null;

  // 3c: whole files in the detail, the bar by fraction. 3d: research keeps one ETA history across books.
  context.fixture={audiobook_jobs:{state:'Running',queued:0,failed:0},activities:[{id:'conversion',kind:'conversion',subject:'B',step:'preparing',step_index:1,step_count:4,done:2,total:4,fraction:0.63,unit:'files',indeterminate:false,state:'running',step_started_at:Date.now()-20000}]};
  run('state=fixture;renderJobs()');const preparing=get('jobs-rows').children[0];assert.equal(preparing.children[0].children[1].textContent,'2 of 4 files');assert.equal(preparing.children[1].value,63);
  const researchStart=Date.now()-60000,researching=(title,done)=>({audiobook_jobs:{state:'Running',queued:0,failed:0},activities:[{id:'scan',kind:'scan',subject:title,step:'researching',step_text:'x',done,total:100,unit:'books',indeterminate:false,state:'running',step_started_at:researchStart}]});
  context.fixture=researching('Book 1',10);run('state=fixture;renderJobs()');const view=run("activityRows.get('scan')");const samples=view.samples.length;
  context.fixture=researching('Book 2',12);run('state=fixture;renderJobs()');assert.equal(view.samples.length,samples+1,'a new book does not reset the history');
  context.fixture=attentionRow('bad-source','other',{}, {attention:{group:'other',originals_untouched:true,remedy:{kind:'replace_source',cause:'source_decode_failed',path:'Z:/Audio/Железная.mp3'}}});
  const sourceText=run('attentionText(fixture)');assert.equal(sourceText.status,'Source audio needs replacement');assert.equal(sourceText.hint,"The MP3 failed its full audio check and can't be repaired by the app. Delete the book, then get a new copy.",'Judy 2026-10-25, Delete book spec section 7');
  assert.match(run('technicalText(fixture)'),/Z:\/Audio\/Железная.mp3/);
  context.fixture=attentionRow('reacquire','reacquire',{}, {attention:{group:'reacquire',reacquire:{state:'required',certainty:'uncertain',reason:'Measured damaged audio',repair_limit:'Cannot preserve speech',originals:[{path:'Z:/shared/one.mp3'}],source_presence:'unavailable'}},retry:{allowed:true}});
  assert.equal(run('attentionText(fixture).status'),'Need to reacquire');
  assert.match(run('attentionText(fixture).hint'),/risking missing audio/);
  assert.equal(run('rowAction(fixture)'),null,'stale Retry data cannot bypass analyzed damage');
  assert.match(run('technicalText(fixture)'),/Affected source file.*one.mp3.*deletion not confirmed/);
  context.fixture={kind:'conversion',state:'attention'};assert.equal(run('activityLabel(fixture)'),'Audiobook on hold');
  context.fixture={kind:'conversion',state:'paused'};assert.equal(run('activityLabel(fixture)'),'Audiobook paused');
  context.fixture={kind:'conversion',state:'running'};assert.equal(run('activityLabel(fixture)'),'Converting');
  context.setTimeout=()=>0;  // nothing scheduled after the checks keeps the process alive
  console.log('PASS attention classes, row hints, Retry and Repair, queued next, repaired record, group strip, server Retry all with confirmation, details lines, list loading and request discipline, whole files and research history');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_attention_frontend.js'),module);m.filename=path.join(__dirname,'test_attention_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

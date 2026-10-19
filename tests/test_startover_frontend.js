'use strict';
// RefusedRetry follow-ups 2-4 (Judy, Sergei 2026-10-19) on seeded rows: Start over, the combined press, "Let the app
// handle it" and its dialog, the Started over states, filter and summary, leftover working files (Clear working files,
// Retry clears first, blocked), the bulk release, the pending start and Cancel, and the narrow table's structure.
// Real frontend on the Retry test's DOM/transport doubles; no server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
Object.defineProperty(Element.prototype,'firstChild',{get(){const element=this;return element.textContent?{nodeType:3,get nodeValue(){return element.textContent;},set nodeValue(value){element.textContent=value;}}:null;}});
const M4B_REASON='M4B preservation requires review: Unsupported structural box';
const FOLDER='C:\\Users\\fixture\\AppData\\Local\\Books Arranger\\data\\merge-cache\\audio-staging\\job-w';
const MB637=637*1024*1024;
function refusal(cause,extra={}){
  const fix={unsupported_file:'update',working_files:'wait',source_changed:'review',file_problem:'user',unknown:'update'}[cause];
  return {accepted:false,queued_next:false,kind:'retry',state:'refused',reason:'Failed M4B retained: fixture',cause,fix,app_version:'0.18.0',key:'k',at:'2026-10-19T08:00:00+00:00',stale:false,...extra};
}
function m4bRow(name,job={},row={}){
  return blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name},artists:['Author '+name],members:[{path:'a'},{path:'b'}],...row},
    {job_id:'job-'+name,reason:M4B_REASON,attention:{group:'retry',cause:null,originals_untouched:true,precheck:'passed'},retry:{allowed:true,reason:''},...job});
}
function stuck(name,startover='automatic',release_ok=false){
  return m4bRow(name,{retry:undefined,attention:{group:'other',cause:null,originals_untouched:true,startover,release_ok},readmission:refusal('source_changed')});
}
function noJob(name,row={}){
  return blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name},artists:['Author '+name],members:[{path:'a'}],status:'Pending',
    creation:{status:'Pending',can_create:false,chapters_available:false,reasons:[],job:null},...row});
}
function heldRow(name,extra={}){return noJob(name,{automatic:{state:'Held',reasons:['Manual draft retained'],hold:'manual_draft',lease:false,retry_at:null},release:{allowed:true},...extra});}
function marked(name,restart,extra={}){return noJob(name,{restart:{kind:'start_over',at:'2026-10-19T09:00:00+00:00',...restart},...extra});}
function statusCell(tr){return tr.children[4];}
function titleCell(tr){return tr.children[1];}
function actionButtons(tr){return tr.children[5].children[0].children;}
function rowOf(name){return [...get('inventory').children].find(tr=>tr.dataset.path==='cand-'+name);}
function paint(list){context.fixture=list;run('heldRow=null;rows=fixture.map(row=>({...row}));renderRows(true);controls()');}
function setAuto(value){context.auto=value;run('state={...state,automatic_processing:{...state.automatic_processing,...auto}};controls()');}
const text=row=>run('rowState('+JSON.stringify(row)+')');
const status=row=>run('candidateStatus('+JSON.stringify(row)+')');
// Transport: the new controls answer from these handlers; everything else is the harness's.
const baseFetch=context.fetch,posts=[],replies={};
context.fetch=async(route,options)=>{
  if(options.body && replies[route]){const body=JSON.parse(options.body);posts.push({route,body});return replies[route](body);}
  return baseFetch(route,options);
};
const accepted=body=>({ok:true,status:202,json:async()=>body}),refused=body=>({ok:false,status:409,json:async()=>body});
const RUNNING={state:'Running',can_start:false,can_stop:true,start_block_reason:'Automatic processing is already running.',start_pending:null};
const IDLE={state:'Idle',can_start:true,can_stop:false,start_block_reason:'',start_pending:null};
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";viewControls()');

  // ---- Start over: the button in the Retry slot, its hint and tooltip by prediction (follow-up 2, 1.2; follow-up 3, 1.2)
  paint([stuck('a'),stuck('m','manual_draft'),stuck('c','manual_draft',true)]);
  let tr=rowOf('a'),start=actionButtons(tr)[0];
  assert.equal(start.textContent,'Start over');assert.equal(start.disabled,false);assert.equal(start.getAttribute('aria-label'),'Start over: Title a');
  assert.equal(start.title,"Set this failed job aside and send the book back to automatic processing. Starts automatic processing if it isn't running. Nothing is deleted.");
  assert.equal(statusCell(tr).textContent,'Stopped — review changed');
  assert.equal(statusCell(tr).children[0].textContent,"Retry was refused: the book's review or source files changed. Start over sends it back to automatic processing.");
  assert.ok(statusCell(tr).children[0].classes.has('retry-refused'),'--warning: a stop that needs a press');
  tr=rowOf('m');
  assert.equal(actionButtons(tr)[0].title,"Set this failed job aside. Starts automatic processing if it isn't running. The book has a saved review, so automatic processing will hold it; \"Let the app handle it\" can then release it. Nothing is deleted.");
  assert.equal(statusCell(tr).children[0].textContent,"Retry was refused: the book's review or source files changed. Start over sets this job aside, but automatic processing will hold the book.");
  // O13: the combined button replaces plain Start over on a single M4B known to hold; never beside it.
  tr=rowOf('c');
  assert.equal(actionButtons(tr)[0].textContent,'Start over and let the app handle it');
  assert.ok(![...actionButtons(tr)].some(button=>button.textContent==='Start over'),'never beside plain Start over');
  assert.equal(actionButtons(tr)[0].getAttribute('aria-label'),'Start over and let the app handle it: Title c');
  assert.equal(statusCell(tr).children[0].textContent,"Retry was refused: the book's review or source files changed. One press sets this job aside, discards its saved review, and sends the book to automatic processing.");
  assert.equal(actionButtons(tr)[0].title,"Set this failed job aside, discard this book's saved review (including any edits you made by hand), and let automatic processing take the book. Starts automatic processing if it isn't running. This can't be undone. The failed job and your audio files are kept.");
  context.fixture=stuck('a');run('select(fixture,true);controls()');
  assert.equal(get('retry-block').hidden,false);assert.equal(get('retry-job').textContent,'Start over','the panel offers the same press');

  // ---- The press: pending face, the request, the held row in its Started over state, the panel note, focus.
  paint([stuck('a')]);tr=rowOf('a');start=actionButtons(tr)[0];
  let answer;replies['/api/audiobook/startover']=()=>new Promise(resolve=>{answer=resolve;});
  const fresh=marked('a',{state:'waiting'},{revision:4});
  backend={...backend,automatic_processing:{...backend.automatic_processing,...RUNNING}};  // what the next poll reports too
  inventoryRows=[fresh];start.focus();
  const pressing=run('retryFromRow(rows[0],'+'rowButtons("cand-a").children[0])');
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(start.textContent,'Starting over…');assert.equal(start.getAttribute('aria-disabled'),'true');assert.equal(statusCell(tr).children[0].textContent,'Setting this job aside…');
  assert.deepEqual(posts.at(-1),{route:'/api/audiobook/startover',body:{library:'Audiobooks',id:'cand-a',revision:4,job_id:'job-a'}});
  answer(accepted({set_aside:true,outcome:'automatic',pass:{action:'started',visit:'this_run'},automatic_processing:RUNNING,row:fresh}));await pressing;
  tr=rowOf('a');
  assert.equal(statusCell(tr).textContent,'Started over — waiting its turn');
  assert.equal(statusCell(tr).children[0].textContent,'Nothing to do. Automatic processing will research this book and queue it if the match is safe.');
  assert.equal(statusCell(tr).children[0].classes.has('retry-refused'),false,'--muted: nothing to do');
  assert.equal(get('retry-note').textContent,'Started over. Automatic processing has started. It scans the library first, so this may take a while. Find it under Status: Started over.');
  assert.equal(get('retry-job').hidden,true,'no Retry, no Start over on the held row');
  assert.equal(get('automatic-status').textContent,'Automatic processing: Running');
  backend={...backend,automatic_processing:{...backend.automatic_processing,...IDLE}};
  assert.equal(document.activeElement?.textContent,'View metadata','focus: the row\'s first remaining button');
  assert.ok([...actionButtons(tr)].includes(document.activeElement),'in the row as painted now, never a detached button');
  assert.ok(!/Pending|Needs attention/.test(get('automatic-result-status').textContent));

  // Every result note (follow-up 3, 1.3 and 4.5; follow-up 4, 1.2 and 3.4).
  const note=(kind,answer)=>JSON.parse(run('JSON.stringify(restartNote('+JSON.stringify(kind)+','+JSON.stringify(answer)+'))'));
  const FIND=' Find it under Status: Started over.';
  assert.deepEqual(note('startover',{pass:{action:'continued'}}),{text:'Started over. Automatic processing continued where it paused.'+FIND,warn:false});
  assert.deepEqual(note('startover',{pass:{action:'running',visit:'this_run'}}),{text:'Started over. Automatic processing is running and will reach this book.'+FIND,warn:false});
  assert.equal(note('startover',{pass:{action:'running',visit:'next_run'}}).warn,true);
  assert.match(note('startover',{pass:{action:'running',visit:'next_run'}}).text,/^Started over\. Automatic processing is running but has already passed this book\. Press Start automatic processing above after it finishes\./);
  assert.deepEqual(note('startover',{pass:{action:'pending',pending_kind:'conversion'}}),{text:'Started over. Audiobook conversion is running, so automatic processing will start by itself when it finishes or is paused.'+FIND,warn:false});
  assert.equal(note('release',{pass:{action:'pending',pending_kind:'scan'}}).text,'Review discarded. A library scan is running, so automatic processing will start by itself when the scan ends or is stopped.'+FIND);
  assert.equal(note('combined',{pass:{action:'pending',pending_kind:'stopping'}}).text,'Started over. Review discarded. Automatic processing is stopping, so it will start again by itself once it has stopped.'+FIND);
  assert.deepEqual(note('startover',{pass:{action:'blocked',reason:'The local server is stopping or stopped. Start is unavailable.'}}),{text:'Started over, but automatic processing did not start. The local server is stopping or stopped. Start is unavailable.',warn:true});
  assert.equal(note('release',{pass:{action:'blocked',reason:'x'}}).text,'Review discarded, but automatic processing did not start. x');
  assert.equal(note('startover',{}).text,'Started over. The book goes back to automatic processing.'+FIND);
  assert.deepEqual(note('startover',{outcome:'manual_draft',pass:{action:'started'}}),{text:'Started over. Automatic processing has started. It scans the library first, so this may take a while. Automatic processing will then hold this book because it has a saved review; Let the app handle it appears once it is held.'+FIND,warn:true});
  assert.equal(note('release',{pass:{action:'running',visit:'next_run'}}).text,'Review discarded. Automatic processing is running but has already passed this book. Press Start automatic processing above after it finishes.');
  assert.equal(note('release',{pass:{action:'running'}}).text,'Review discarded. Automatic processing is running and will reach this book.'+FIND);

  // Refused: an outdated view, and anything else (words from the typed cause, never the server's English).
  setAuto(IDLE);paint([stuck('r')]);
  replies['/api/audiobook/startover']=()=>refused({error:'server words',cause:'changed'});inventoryRows=[stuck('r')];run('heldRow=null');
  await run('retryFromRow(rows[0],rowButtons("cand-r").children[0])');
  assert.equal(get('retry-note').textContent,"This book's status changed. Check the updated status above.");
  replies['/api/audiobook/startover']=()=>refused({error:'server words',cause:'busy'});
  await run('retryFromRow(rows[0],rowButtons("cand-r").children[0])');
  assert.equal(get('retry-note').textContent,'Start over was not accepted. Check the status above.');

  // ---- The combined press: one confirmation, then one request with discard_review (follow-up 4, 3.3 and 3.4).
  paint([stuck('c','manual_draft',true)]);inventoryRows=[stuck('c','manual_draft',true)];tr=rowOf('c');const combined=actionButtons(tr)[0];combined.focus();
  const before=posts.length;
  await run('retryFromRow(rows[0],rowButtons("cand-c").children[0])');
  assert.equal(posts.length,before,'the dialog opens and nothing else happens');
  assert.equal(get('discard-dialog-title').textContent,"Start over and discard this book's saved review?");
  assert.equal(get('discard-dialog-book').textContent,'Title c');
  assert.equal(get('discard-dialog-body').textContent,"This sets the failed job aside, then deletes the metadata, cover and track choices saved on this book, including any you made by hand. The deleted review can't be restored.");
  assert.equal(get('discard-dialog-body2').textContent,"Automatic processing then researches the book again and queues it if the match is safe. It starts if it isn't running. The failed job and your audio files are kept.");
  assert.equal(get('discard-confirm').textContent,'Discard review and start over');assert.equal(get('discard-cancel').title,'Keep everything as it is.');
  assert.equal(document.activeElement,get('discard-cancel'),'Cancel first and focused');
  get('discard-dialog').handlers.keydown({key:'Escape',preventDefault(){}});
  assert.equal(run('discardConfirmation'),null);assert.equal(document.activeElement,combined,'Esc: no change, focus returns');assert.equal(posts.length,before);
  replies['/api/audiobook/startover']=()=>refused({error:'x',cause:'editing'});
  await run('retryFromRow(rows[0],rowButtons("cand-c").children[0])');get('discard-confirm').handlers.click();
  await new Promise(resolve=>setImmediate(resolve));await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(posts.at(-1).body,{library:'Audiobooks',id:'cand-c',revision:4,job_id:'job-c',discard_review:true});
  assert.equal(get('retry-note').textContent,'This book is being edited. Finish editing, then try again.');
  replies['/api/audiobook/startover']=()=>refused({error:'x',cause:'busy'});
  await run('retryFromRow(rows[0],rowButtons("cand-c").children[0])');get('discard-confirm').handlers.click();
  for(let i=0;i<4;i++)await new Promise(resolve=>setImmediate(resolve));
  assert.equal(get('retry-note').textContent,'Start over was not accepted. Nothing was changed.');

  // ---- "Let the app handle it" (follow-up 3, section 4): status, hint, button first, tooltip, dialog, request.
  run('filters.candidates="held";viewControls()');
  paint([heldRow('h'),heldRow('l',{automatic:{state:'Held',reasons:['Manual draft retained'],hold:'manual_draft',lease:true},release:{allowed:false}})]);
  tr=rowOf('h');
  assert.equal(statusCell(tr).textContent,'Held — saved review kept');
  assert.equal(statusCell(tr).children[0].textContent,'A saved review keeps this book held. Let the app handle it discards that review, including any hand edits, and lets automatic processing take the book.');
  assert.ok(statusCell(tr).children[0].classes.has('retry-refused'),'--warning: a decision is waiting');
  const release=actionButtons(tr)[0];
  assert.equal(release.textContent,'Let the app handle it');assert.equal(release.getAttribute('aria-label'),'Let the app handle it: Title h');
  assert.equal(release.title,"Discard this book's saved review, including any edits you made by hand, and let automatic processing take the book. Starts automatic processing if it isn't running. This can't be undone. Your audio files are not touched.");
  assert.equal(actionButtons(tr)[1].textContent,'View metadata','first slot, then View metadata');
  assert.equal(status(heldRow('l',{automatic:{state:'Held',reasons:['Manual draft retained'],hold:'manual_draft',lease:true},release:{allowed:false}})),'Held — Manual draft retained','negative control: an editor open, no button');
  assert.ok(![...actionButtons(rowOf('l'))].some(button=>button.textContent==='Let the app handle it'));
  replies['/api/audiobook/release']=()=>accepted({released:true,outcome:'automatic',pass:{action:'running',visit:'this_run'},automatic_processing:RUNNING,row:marked('h',{state:'waiting',kind:'release'})});
  release.focus();await run('retryFromRow(rows[0],rowButtons("cand-h").children[0])');
  assert.equal(get('discard-dialog-title').textContent,"Discard this book's saved review?");
  assert.equal(get('discard-dialog-body').textContent,"This deletes the metadata, cover and track choices saved on this book, including any you made by hand. It can't be undone.");
  assert.equal(get('discard-dialog-body2').textContent,"Automatic processing then researches the book again and queues it if the match is safe. It starts if it isn't running. Your audio files are not touched.");
  assert.equal(get('discard-confirm').textContent,'Discard review');assert.equal(get('discard-cancel').title,'Keep the saved review and leave this book held.');
  assert.equal(get('discard-confirm').title,"Delete this book's saved review, then let automatic processing take the book. This can't be undone.");
  inventoryRows=[];get('discard-confirm').handlers.click();for(let i=0;i<6;i++)await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(posts.at(-1),{route:'/api/audiobook/release',body:{library:'Audiobooks',id:'cand-h',revision:4}});
  assert.equal(get('retry-note').textContent,'Review discarded. Automatic processing is running and will reach this book. Find it under Status: Started over.');
  assert.equal(statusCell(rowOf('h')).textContent,'Started over — waiting for you','held in place in its Started over state, never "Held" (the poll says Idle)');
  for(const [cause,words] of [['changed',"This book's status changed. Check the updated status above."],['editing','This book is being edited. Finish editing, then try again.'],
                              ['busy',"The review wasn't discarded. The app is busy; try again in a moment."],['other',"The review wasn't discarded. Select the row to read why."]])
    assert.equal(run('refusedText("release",'+JSON.stringify({body:{cause}})+')'),words,cause);

  // ---- The Started over states (follow-up 3, 2.2; follow-up 4, 1.3 and 2), with the live pass state.
  run('filters.candidates="restarted";viewControls()');
  const waiting=marked('w',{state:'waiting'});
  setAuto(RUNNING);assert.deepEqual([text(waiting).status,text(waiting).hint],['Started over — waiting its turn','Nothing to do. Automatic processing will research this book and queue it if the match is safe.']);
  setAuto(IDLE);assert.deepEqual([text(waiting).status,text(waiting).hint,text(waiting).warn],['Started over — waiting for you','Press Start automatic processing above. It will then research this book and queue it if the match is safe.',true]);
  setAuto({state:'Idle',can_start:false,start_block_reason:'The local server is stopping or stopped. Start is unavailable.',start_pending:null});
  assert.equal(text(waiting).hint,"Automatic processing can't start yet. The local server is stopping or stopped. Start is unavailable.");
  for(const [kind,hint] of [['conversion','Nothing to do. Automatic processing starts by itself when audiobook conversion finishes or is paused, then takes this book.'],
                            ['scan','Nothing to do. Automatic processing starts by itself when the library scan ends or is stopped, then takes this book.'],
                            ['stopping','Nothing to do. Automatic processing starts again by itself once it has stopped, then takes this book.']]){
    setAuto({state:'Idle',can_start:false,start_block_reason:'x',start_pending:{kind}});
    assert.deepEqual([text(waiting).status,text(waiting).hint,!!text(waiting).warn],['Started over — waiting to start',hint,false],kind);
  }
  setAuto({state:'Idle',can_start:false,start_pending:{kind:'conversion'}});
  assert.equal(text(marked('e',{state:'waiting',expect:'hold',release_expected:true})).hint,'Nothing to do. Automatic processing starts by itself when audiobook conversion finishes or is paused, then holds this book because it has a saved review. Then Let the app handle it appears here.');
  setAuto(RUNNING);
  assert.equal(text(marked('e',{state:'waiting',expect:'hold',release_expected:true})).hint,'Nothing to do yet. Automatic processing will hold this book because it has a saved review. Then Let the app handle it appears here.');
  assert.equal(text(marked('e',{state:'waiting',expect:'hold',release_expected:false})).hint,'Nothing to do yet. Automatic processing will hold this book because it has a saved review.','follow-up 4, 2: only when the book is a single M4B');
  setAuto(IDLE);
  assert.equal(text(marked('e',{state:'waiting',expect:'hold',release_expected:true})).hint,'Press Start automatic processing above. It will then hold this book because it has a saved review, and Let the app handle it appears here.');
  assert.equal(text(marked('e',{state:'waiting',expect:'hold',release_expected:false})).hint,'Press Start automatic processing above. It will then hold this book because it has a saved review.');
  setAuto(RUNNING);
  assert.deepEqual([text(marked('x',{state:'working'})).status,text(marked('x',{state:'working'})).hint],['Started over — researching','Nothing to do. Automatic processing is looking this book up now. It queues the book if the match is safe.']);
  assert.deepEqual([text(marked('x',{state:'working',source_wait:true})).status,text(marked('x',{state:'working',source_wait:true})).hint],['Started over — waiting for a source','Nothing to do. A metadata source is busy. Automatic processing tries again by itself.']);
  assert.deepEqual([text(marked('n',{state:'waiting',visit:'next_run'})).status,text(marked('n',{state:'waiting',visit:'next_run'})).warn],['Started over — next run',true]);
  setAuto(IDLE);assert.equal(text(marked('x',{state:'working'})).status,'Started over — waiting for you','working, pass not running: shown as waiting');
  run('recoveryDisconnected=true');assert.deepEqual([text(waiting).status,text(waiting).hint],['Started over — waiting','Reconnecting to the app. This row updates when it is back.']);run('recoveryDisconnected=false');
  const other=marked('o',{state:'held'},{automatic:{state:'Held',reasons:['Cover source unavailable'],retry_at:null},status:'Pending'});
  assert.deepEqual([status(other),text(other).hint],['Held — Cover source unavailable','Nothing to do. Automatic processing couldn\'t approve this book safely. It tries again later, while it is running.']);
  assert.equal(text(marked('k',{state:'held',hold:'manual_draft'},{automatic:{state:'Held',reasons:['Manual draft retained'],hold:'manual_draft',lease:true}})).hint,'You are editing this book. Automatic processing waits until you stop.');
  assert.equal(text(marked('k',{state:'held',hold:'manual_draft'},{automatic:{state:'Held',reasons:['Manual draft retained'],hold:'manual_draft',lease:false}})).hint,'Automatic processing holds this book because it has a saved review.');
  const failed=marked('f',{state:'failed'},{automatic:{state:'Needs attention',reasons:['Metadata research failed']}});
  assert.deepEqual([status(failed),text(failed).hint,text(failed).warn],['Needs attention — Metadata research failed','Automatic processing hit an error on this book. Press Start automatic processing above to try again.',true]);
  const queuedRow=marked('q',{state:'queued'},{creation:{status:'Queued',can_create:false,reasons:[],job:{job_id:'job-q',state:'Queued',stage:'queued',reason:''}},status:'Queued'});
  assert.deepEqual([status(queuedRow),text(queuedRow).hint],['Queued','Queued by automatic processing after Start over. Nothing to do.']);
  assert.equal(status(marked('changed',{state:'waiting'},{status:'Candidate changed — review required'})),'Started over — waiting for you','the marker comes before "Candidate changed"');
  // Each row follows the pass in place: no rebuild, no focus move.
  paint([waiting]);tr=rowOf('w');const hintElement=statusCell(tr).children[0];
  assert.equal(statusCell(tr).textContent,'Started over — waiting for you');
  setAuto(RUNNING);assert.equal(statusCell(rowOf('w')).children[0],hintElement,'the same element');assert.equal(statusCell(tr).textContent,'Started over — waiting its turn');
  context.fixture=waiting;run('select(fixture,true);controls()');assert.match(get('automatic-facts').children.map(item=>item.textContent).join('|'),/Started over\|/,'the panel fact line');

  // ---- The filter, its empty text and the summary line (follow-up 3, 2.3; follow-up 4, 1.3).
  const option=JSON.parse(run('JSON.stringify(filterOptions.candidates.at(-1))'));assert.deepEqual(option,['restarted','Started over']);
  assert.equal(run('FILTER_TITLES.restarted'),'Show books you started over that automatic processing has not queued yet.');
  paint([]);assert.equal(get('empty').textContent,'No books are waiting after Start over. Books you start over appear here until automatic processing queues them.');
  const summary=(counts,auto)=>{context.counts=counts;setAuto(auto);run('restartCounts=counts;renderRestartSummary()');return get('restart-summary').textContent;};
  assert.equal(summary({waiting:9,working:2,held:1,failed:0,next_run:0,release:0},RUNNING),'12 books started over: 9 waiting, 2 being processed, 1 held. Nothing for you to do.');
  assert.equal(summary({waiting:12,working:0,held:0,failed:0,next_run:0,release:0},IDLE),'12 books started over: 12 waiting. Press Start automatic processing above.');
  assert.equal(summary({waiting:0,working:0,held:1,failed:0,next_run:0,release:1},IDLE),'1 book started over: 1 held. 1 held for a saved review: press Let the app handle it on a book to release it, or leave it held.');
  assert.equal(summary({waiting:3,working:0,held:0,failed:0,next_run:0,release:0},{state:'Idle',can_start:false,start_pending:{kind:'conversion'}}),'3 books started over: 3 waiting. Nothing for you to do. Automatic processing starts by itself when audiobook conversion finishes or is paused.');
  assert.equal(summary({waiting:1,working:0,held:0,failed:0,next_run:1,release:0},RUNNING),'1 book started over: 1 waiting. Press Start automatic processing above after this run finishes.');
  run('filters.candidates="held";viewControls();renderRestartSummary()');assert.equal(get('restart-summary').hidden,true,'only in this filter');

  // ---- O12: the notice, Cancel automatic start, and its press (follow-up 4, 1.4).
  setAuto({state:'Idle',can_start:false,start_block_reason:'Audiobook conversion is running. Pause audiobook jobs before starting automatic processing.',start_pending:{kind:'conversion'}});
  assert.equal(get('automatic-start-reason').textContent,'Automatic processing will start by itself when audiobook conversion finishes or is paused. Starting also resumes any queued audiobook jobs.');
  assert.equal(get('start-automatic').title,get('automatic-start-reason').textContent,'the Start tooltip carries the same sentence');
  assert.equal(get('cancel-automatic-start').hidden,false);assert.equal(get('cancel-automatic-start').disabled,false);
  backend={...backend,automatic_processing:{...backend.automatic_processing,...IDLE,can_start:false,start_block_reason:'Audiobook conversion is running. Pause audiobook jobs before starting automatic processing.'}};
  replies['/api/automatic/cancel-start']=()=>accepted({automatic_processing:backend.automatic_processing});
  await run('automaticAction("cancel-start")');
  assert.equal(posts.at(-1).route,'/api/automatic/cancel-start');assert.deepEqual(posts.at(-1).body,{});
  assert.equal(get('automatic-start-reason').textContent,'Audiobook conversion is running. Pause audiobook jobs before starting automatic processing.','back to the block reason');
  assert.equal(get('cancel-automatic-start').hidden,true);assert.equal(document.activeElement,get('automatic-start-reason'),'focus moves to the notice');
  assert.equal(get('automatic-start-reason').getAttribute('tabindex'),'-1');
  // Page contract for Senua M2 (v0.19.0): Stop, Quit or a safety stop (disk full, working-file hold) ends the pending
  // start on the server, with no Cancel press. The next poll carries no start_pending: the row and the notice stop
  // promising a start, in place, and read as after Cancel (follow-up 4, section 1.4).
  run('filters.candidates="restarted";viewControls()');paint([marked('w',{state:'waiting'})]);
  setAuto({state:'Idle',can_start:false,start_block_reason:'Audiobook conversion is running. Pause audiobook jobs before starting automatic processing.',start_pending:{kind:'conversion'}});
  assert.equal(statusCell(rowOf('w')).textContent,'Started over — waiting to start','positive control: the pending start is promised');
  assert.equal(get('cancel-automatic-start').hidden,false);
  setAuto(IDLE);  // the converter stopped on the hold and is Paused; the server ended the pending start
  assert.equal(statusCell(rowOf('w')).textContent,'Started over — waiting for you');
  assert.equal(statusCell(rowOf('w')).children[0].textContent,'Press Start automatic processing above. It will then research this book and queue it if the match is safe.');
  assert.equal(get('cancel-automatic-start').hidden,true);assert.equal(get('automatic-start-reason').hidden,true,'no "will start by itself" notice');
  run('filters.candidates="held";viewControls()');
  setAuto(IDLE);

  // ---- Leftover working files (follow-up 2, section 2; follow-up 3, section 3).
  run('filters.candidates="output_attention";viewControls()');
  const cleanable=m4bRow('cw',{attention:{group:'retry',cause:null,originals_untouched:true,precheck:'passed',working:{state:'cleanable',bytes:MB637,reason:'Leftover working files from an earlier attempt'},working_folder:FOLDER}});
  paint([cleanable]);tr=rowOf('cw');
  assert.equal(statusCell(tr).textContent,'Stopped — ready to retry','cleanable is not a stop: the natural state');
  assert.equal(statusCell(tr).children[0].textContent,'Safe to retry now.');
  assert.equal(statusCell(tr).children[0].children[0].textContent,' Retry clears leftover working files first.');assert.equal(statusCell(tr).children[0].children[0].className,'hint-clause');
  assert.equal(actionButtons(tr)[0].title,'Clear the leftover working files, then check this book again and queue its audiobook job.');
  const clear=actionButtons(tr)[1];
  assert.equal(clear.textContent,'Clear working files');assert.equal(clear.disabled,false);assert.equal(clear.getAttribute('aria-label'),'Clear working files: Title cw');
  assert.equal(clear.title,'Delete the working files an earlier attempt left behind. Originals are not touched. Frees about 637 MB.');
  assert.deepEqual([...actionButtons(tr)].map(button=>button.textContent),['Retry','Clear working files','View metadata','Source folders'],'Retry, Clear, then navigation');
  assert.equal(statusCell(tr).title,'Technical detail: Leftover working files from an earlier attempt; earlier failure: '+M4B_REASON+'; working folder: '+FOLDER);
  // Repair: the same rule with its own verb.
  const repairable=m4bRow('rw',{retry:undefined,repair:{allowed:true,reason:''},attention:{group:'repair',cause:null,originals_untouched:true,damage:[{kind:'dangling_chapter_reference'}],working:{state:'cleanable',bytes:10,reason:'r'}}});
  paint([repairable]);tr=rowOf('rw');
  assert.equal(statusCell(tr).children[0].children[0].textContent,' Repair clears leftover working files first.');
  assert.equal(actionButtons(tr)[0].title,'Clear the leftover working files, patch the damage found in this book, then queue its audiobook job.');
  // Retry's press says it clears first.
  paint([cleanable]);let retryAnswer;retryOverride=()=>new Promise(resolve=>{retryAnswer=resolve;});
  const retrying=run('retryFromRow(rows[0],rowButtons("cand-cw").children[0])');await new Promise(resolve=>setImmediate(resolve));
  assert.equal(statusCell(rowOf('cw')).children[0].textContent,'Clearing working files, then checking this book…');
  retryAnswer({ok:false,status:409,json:async()=>({error:"Retry was not accepted: the working files weren't cleared. Nothing was queued.",cause:'not_safe'})});await retrying;
  assert.equal(get('retry-note').textContent,"Retry was not accepted: the working files weren't cleared. Nothing was queued.");retryOverride=null;run('pressed.clear()');
  // Futaba Minor 2 (c2abd97): the refused clear-first answers with the book's refreshed row, as Clear does; the details
  // panel shows it at once and stops offering Retry and Clear. The next list no longer holds the book (it moved from
  // Can retry to Other), so before the fix nothing ever re-selected it and the panel kept the state before the press.
  const nowBlocked=m4bRow('cw',{retry:undefined,attention:{group:'other',cause:null,originals_untouched:true,working:{state:'blocked',stops:true,bytes:null,reason:'Working files were kept: x'},working_folder:FOLDER}});
  paint([cleanable]);inventoryRows=[];run('select(rows[0],true);controls()');
  assert.equal(get('retry-job').hidden,false);assert.equal(get('clear-working').hidden,false,'positive control: the panel offers Retry and Clear');
  retryOverride=async()=>({ok:false,status:409,json:async()=>({error:"Retry was not accepted: the working files weren't cleared. Nothing was queued.",cause:'not_safe',row:nowBlocked})});
  await run('retryJob()');
  assert.equal(get('retry-job').hidden,true,'no Retry from the state before the press');assert.equal(get('clear-working').hidden,true,'no Clear either');
  assert.equal(statusCell(rowOf('cw')).textContent,"Stopped — can't clear working files",'held in place in its new state, never vanishing under the pointer');
  retryOverride=null;run('pressed.clear();retryResult=null;heldRow=null;controls()');
  // Clear: the press, success with the size and the natural hint, focus to the same row's Retry.
  paint([cleanable]);tr=rowOf('cw');let clearAnswer;replies['/api/audiobook/clear-working']=()=>new Promise(resolve=>{clearAnswer=resolve;});
  const cleared=m4bRow('cw',{attention:{group:'retry',cause:null,originals_untouched:true,precheck:'passed'}});inventoryRows=[cleared];actionButtons(tr)[1].focus();
  const clearing=run('clearFromRow(rows[0],rowButtons("cand-cw").children[1])');await new Promise(resolve=>setImmediate(resolve));
  assert.equal(actionButtons(tr)[1].textContent,'Clearing…');assert.equal(actionButtons(tr)[1].getAttribute('aria-disabled'),'true');
  assert.equal(statusCell(tr).children[0].textContent,'Clearing working files…');
  assert.deepEqual(posts.at(-1),{route:'/api/audiobook/clear-working',body:{library:'Audiobooks',id:'cand-cw',revision:4,job_id:'job-cw'}});
  clearAnswer(accepted({cleared:true,bytes:MB637,row:cleared}));await clearing;
  tr=rowOf('cw');
  assert.equal(statusCell(tr).children[0].textContent,'Cleared 637 MB of working files. Safe to retry now.');assert.equal(statusCell(tr).children[0].classes.has('retry-refused'),false);
  assert.ok(![...actionButtons(tr)].some(button=>button.textContent==='Clear working files' && !button.hidden),'the button leaves');
  assert.equal(document.activeElement?.textContent,'Retry','focus: the same row\'s Retry');
  for(const [answer,words] of [[{cleared:true,bytes:0,already:true},'Working files were already cleared.'],[{cleared:true,bytes:null},'Working files cleared.']]){
    paint([cleanable]);replies['/api/audiobook/clear-working']=()=>accepted({...answer,row:cleared});await run('clearFromRow(rows[0],rowButtons("cand-cw").children[1])');
    assert.equal(statusCell(rowOf('cw')).children[0].textContent,words+' Safe to retry now.');
  }
  // Failures: the typed cause's words, warning colour; the button stays while the files are still cleanable.
  for(const [cause,words] of [['busy',"Working files weren't cleared. The app is busy; try again in a moment."],['changed',"This book's status changed. Check the updated status above."],
      ['not_safe',"Some working files weren't cleared. The app keeps any file it can't confirm is safe to delete."],['file_problem',"Some working files weren't cleared. A file couldn't be removed; try again in a moment."],
      ['what',"Working files weren't cleared. Select the row to read why."]]){
    paint([cleanable]);inventoryRows=[cleanable];replies['/api/audiobook/clear-working']=()=>refused({error:'server words',cause});
    await run('clearFromRow(rows[0],rowButtons("cand-cw").children[1])');
    assert.equal(statusCell(rowOf('cw')).children[0].textContent,words,cause);assert.ok(statusCell(rowOf('cw')).children[0].classes.has('retry-refused'));
    assert.equal(actionButtons(rowOf('cw'))[1].hidden,false,'still cleanable: the button stays');
  }
  // Another request in flight: the button is not disabled; the press is answered in the note.
  paint([cleanable]);run('retryPending={key:"other",kind:"retry"};controls()');assert.equal(actionButtons(rowOf('cw'))[1].disabled,false);
  assert.equal(actionButtons(rowOf('cw'))[0].disabled,true,'positive control: Retry is busy');
  const sent=posts.length;await run('clearFromRow(rows[0],rowButtons("cand-cw").children[1])');
  assert.equal(posts.length,sent);assert.equal(statusCell(rowOf('cw')).children[0].textContent,'Another operation is in progress. Try again in a moment.');run('retryPending=null;retryResult=null;controls()');
  // Blocked: its own status, no Retry, no Clear; the reason and the folder in Technical detail only.
  const blockedRow=m4bRow('bw',{retry:undefined,attention:{group:'other',cause:null,originals_untouched:true,working:{state:'blocked',stops:true,bytes:null,reason:'A file the app did not record is in the working folder: x.wav'},working_folder:FOLDER}});
  paint([blockedRow]);tr=rowOf('bw');
  assert.equal(statusCell(tr).textContent,"Stopped — can't clear working files");
  assert.equal(statusCell(tr).children[0].textContent,"Working files from an earlier attempt are still present, and the app can't clear them safely right now.");
  assert.deepEqual([...actionButtons(tr)].map(button=>button.textContent),['View metadata','Source folders']);
  assert.equal(statusCell(tr).title,'Technical detail: A file the app did not record is in the working folder: x.wav; earlier failure: '+M4B_REASON+'; working folder: '+FOLDER);
  const unreachable={...blockedRow,creation:{...blockedRow.creation,job:{...blockedRow.creation.job,attention:{...blockedRow.creation.job.attention,working:{state:'blocked',stops:true,cause:'originals_unreachable',reason:'r'}}}}};
  assert.equal(text(unreachable).hint,"Working files from an earlier attempt are still present, and the app can't clear them while the original files can't be reached. Check that the library drive is connected.");
  // An old working-files record with no files: the natural row, nothing about cleanup (Minor 3).
  const oldRecord=m4bRow('or',{readmission:refusal('working_files')});
  assert.deepEqual([text(oldRecord).status,text(oldRecord).hint],['Stopped — ready to retry','Safe to retry now.']);
  assert.doesNotMatch(JSON.stringify(text(oldRecord)),/waiting for cleanup|still present/);
  // The bulk dialogs carry k (decision A).
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,attention_counts:{retry:3},working_cleanable:2}};attentionGroup="retry";openRetryAll()');
  assert.equal(get('retry-all-question').textContent,'Queue 3 books to be checked again? They run one at a time, right after the current book. 2 of them have leftover working files, which are cleared first.');
  run('retryAllConfirm=null;attentionGroup="all"');
  paint([cleanable,m4bRow('plain')]);run('for(const row of rows)selectedBooks.set(row.id,row.revision);batchCounts()');get('retry-selected').handlers.click();
  assert.equal(get('retry-selected-question').textContent,'Queue 2 selected books to be checked again? They run one at a time, right after the current book. 1 of them has leftover working files, which are cleared first.');
  run('retrySelectedConfirm=null;selectedBooks.clear();controls()');

  // ---- Let the app handle selected (follow-up 4, section 4).
  run('filters.candidates="held";viewControls()');
  const mix=[heldRow('b1'),heldRow('b2'),heldRow('b3'),heldRow('multi',{release:{allowed:false}}),heldRow('lease',{release:{allowed:false},automatic:{state:'Held',reasons:['Manual draft retained'],hold:'manual_draft',lease:true}})];
  paint(mix);run('for(const row of rows)selectedBooks.set(row.id,row.revision);batchCounts();controls()');
  assert.equal(get('batch-count').textContent,'5 selected · 0 ready · 5 need review · 3 can be handled by the app');
  assert.equal(get('release-selected').hidden,false);assert.equal(get('release-selected').textContent,'Let the app handle selected (3)');
  assert.equal(get('release-selected').title,"Discard the saved reviews of these 3 selected books, including any edits you made by hand, and let automatic processing take them. Starts automatic processing if it isn't running. This can't be undone.");
  assert.equal(get('batch-help').textContent,'Only selected books held for a saved review can be handed to the app. The others stay as they are.');
  run('filters.candidates="restarted";viewControls();batchCounts()');assert.equal(get('batch-count').textContent,'5 selected · 3 can be handled by the app · 2 left out');
  get('release-selected').handlers.click();
  assert.equal(get('discard-dialog-title').textContent,'Discard 3 saved reviews?');
  assert.equal(get('discard-dialog-body').textContent,"This deletes the metadata, cover and track choices saved on these 3 books, including any you made by hand. It can't be undone.");
  assert.equal(get('discard-dialog-body3').textContent,'2 other selected books are not included. They stay selected and unchanged.');assert.equal(get('discard-dialog-body3').hidden,false);
  assert.equal(get('discard-confirm').textContent,'Discard 3 reviews');assert.equal(get('discard-cancel').title,'Keep the saved reviews and leave these books held.');
  assert.equal(document.activeElement,get('discard-cancel'));
  replies['/api/audiobook/release-selected']=body=>accepted({released:2,refused:[{id:body.items[2].id,cause:'changed'}],pass:{action:'running',visit:'this_run'},automatic_processing:RUNNING});
  inventoryRows=mix;get('discard-confirm').handlers.click();for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(posts.at(-1).body,{library:'Audiobooks',items:[{id:'cand-b1',revision:4},{id:'cand-b2',revision:4},{id:'cand-b3',revision:4}]});
  assert.equal(get('release-selected-status').textContent,'Discarded 2 of 3 saved reviews. Automatic processing is running and will reach these books. Find them under Status: Started over. 1 were not changed. Check their status.');
  assert.ok(get('release-selected-status').classes.has('retry-refused'),'--warning when some were not changed');
  assert.equal(document.activeElement,get('release-selected-status'),'focus moves to the result');
  run('selectedBooks.clear();batchCounts();controls()');
  assert.equal(get('release-selected').disabled,true);assert.equal(get('release-selected').title,'Select books held for a saved review.');
  run('filters.candidates="output_attention";viewControls();controls()');assert.equal(get('release-selected').hidden,true,'hidden in every other filter');
  // k of 1 uses the single dialog.
  run('filters.candidates="held";viewControls()');paint([heldRow('one')]);run('selectedBooks.set("cand-one",4);batchCounts();controls()');get('release-selected').handlers.click();
  assert.equal(get('discard-dialog-title').textContent,"Discard this book's saved review?");run('closeDiscardDialog(false);selectedBooks.clear()');

  // ---- The narrow table's structure (follow-up 3, section 5): roles, the second line, the bands in CSS.
  run('filters.candidates="all";viewControls()');paint([m4bRow('t')]);tr=rowOf('t');
  assert.equal(tr.attrs.role,'row');assert.ok([...tr.children].every(cell=>cell.attrs.role==='cell'),'every cell keeps the cell role');
  assert.ok(get('inventory-head').children[0].children.every(cell=>cell.attrs.role==='columnheader'));
  assert.equal(titleCell(tr).children[0].textContent,'Author t · 2 audio files');assert.match(titleCell(tr).children[0].className,/title-facts/);
  assert.equal(run('titleFacts({artists:[],members:[{}]})'),'Unknown · 1 audio file');
  assert.ok(get('inventory-table').classes.has('candidates'));
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
  assert.match(html,/<div class="table-scroll" id="inventory-scroll"><table id="inventory-table" role="table"><thead id="inventory-head" role="rowgroup">/);
  assert.match(css,/#inventory-scroll\{container-type:inline-size;container-name:booklist\}/);
  assert.match(css,/#inventory-table td:nth-child\(3\),#inventory-table td:nth-child\(4\),#inventory-table td:last-child\{min-width:0\}/,'the Files-era minimums are dropped for the book list');
  for(const band of ['@container booklist (max-width:799px)','@container booklist (max-width:599px)','@container booklist (max-width:999px)'])assert.ok(css.includes(band),band);
  // The wide band's design minimums add up below its lower edge (800): 64+140+120+72+180+170.
  const wide=css.slice(0,css.indexOf('@container booklist (max-width:799px)'));
  const minimum=[...wide.matchAll(/#inventory-table\.candidates (?:th:nth-child\(\d\),#inventory-table\.candidates )?td:nth-child\((\d)\)\{(?:min-)?width:(\d+)px\}/g)].reduce((sum,match)=>sum+Number(match[2]),0);
  assert.equal(minimum,746);
  context.setTimeout=()=>0;
  console.log('PASS Start over, combined press, release and its dialog, Started over states/filter/summary, working files, bulk release, pending start, narrow table structure');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_startover_frontend.js'),module);m.filename=path.join(__dirname,'test_startover_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

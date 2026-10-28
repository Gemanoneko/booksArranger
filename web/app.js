'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="books-token"]').content;
let offset = 0, search = '', selectedPath = null, selectedRow = null, reviewRow = null, rows = [], lastKey = null;
let dirty = false, busy = false, polling = false, ended = false, timer = null, state = null;
let view='candidates',totalRows=0,selectedLibrary=null;
let automaticRequest=null,automaticFlight=null,automaticResultKey=null,automaticInspectorKey=null;
let manualMetadataTouched=false,manualTrackTouched=false,manualDraftLease=null,draftLeaseFailure='',draftLeaseQueue=Promise.resolve();
const filters={files:'all',candidates:'converted'};
const filterOptions={files:[['all','All files'],['errors','Read errors'],['review','Needs metadata review'],['preview','Preview available'],['missing','No longer found']],candidates:[['converted','Audiobook Ready'],['all','All candidates'],['jobs','Queued / creating'],['held','Held'],['recording_review','Recording review'],['errors','Source read errors'],['changed','Candidate changed'],['output_attention','Output needs attention'],['restarted','Started over']]};
const form = $('review-form');
const fields = ['original_language','title','author','canonical_author','narrator','universe','series','number','genre','topic'];
// Futaba's 0.22.0 QA, m-4: the Accepted evidence never shows names or rule numbers ("(Sergei 2026-10-24, ruling 6b)",
// "Sergei's rule (ruling 12)"). The stored evidence stays as recorded; only its display is worded neutrally, as the
// grouping line is (groups.shown_grouping).
function plainEvidence(text){
  return String(text ?? '').replace(/\s*\((?:Sergei\b|rulings?\s+\d)[^()]*\)/g,'').replace(/\bSergei's\b/g,'your').replace(/\bSergei\s+rulings?\s+\d+[a-z]?/g,'your earlier answer')
    .replace(/\brulings?\s+\d+[a-z]?(?:\s+and\s+\d+[a-z]?)?(?:'s)?/gi,'your rules').replace(/\bSergei\b/g,'you');
}
let proposalId=null,coverId=null,trackDraft=null,trackDirty=false,noteOnlyDirty=false,coverSequence=0,mergeRenderKey=null,proposalRenderKey=null,memberRenderKey=null,coverRenderKey=null;
const selectedBooks=new Map(),coverObjects=[];
let inspectorIdentity=null,inspectSequence=0;
const inspectorObjects=[];
let recoveryPanel=null,recoveryConfirmation=null,recoverySubmitting=false,recoveryDisconnected=false;
let retryPending=null,retryResult=null,retryEpoch=0;
// v0.16.12: a Retry/Repair press the server accepted (or may have) is remembered per book, so a list read from
// before it never repaints the book as an enabled Retry; only the server's own state or refusal replaces it.
const pressed=new Map(),PRESS_MEMORY=10*60*1000;let heldRow=null,retrySelectedConfirm=null,retrySelectedRun=false;
let listTicket=0,listPending='',paintedContext='',attentionGroup='all',retryAllRun=null,retryAllConfirm=null,stripNote='',listGeneration=0;
const rowRetries=new Map();
const pendingFolders=new Set(),folderMessages=new Map();
// Start over, "Let the app handle it" and Clear working files (RefusedRetry follow-ups 2-4, Sergei 2026-10-19).
// restartResult: the panel note for a book whose press left it with no control (it now shows its Started over state).
let restartResult=null,discardConfirmation=null,releaseRun=false,restartCounts=null;
// The one to-do list (Judy, AttentionTodo UX 2026-10-24): rows that ask Sergei, by book id. Drafts survive polls, paging and
// chip changes and are dropped on Approve; done/results/checked are the per-row outcomes shown until the row leaves.
let askBulk=false,approveConfirm=null;
const askPendings=new Map();  // book id -> {id, kind, at}: a row's press on its way (one per row; rows never hold each other)
let editSeq=0,metaSave=null,metaAgain=false,metaQueued=false;  // Save preview metadata (2026-10-26)
const askRows=new Map(),askDrafts=new Map(),askDone=new Map(),askResults=new Map(),askChecked=new Map();
// Delete book (ruling 23): its row buttons, its row hints, the press reading the list, and the open dialog.
const deleteButtons=new Map(),deleteNotes=new Map();let deletePending=null,deleteDialog=null,focusPlan=null,deleteNext=null;
// The Delete book or Remove this copy pressed while another book's dialog was being prepared or open: it opens next (ruling 35).
function deleteNextPress(){const id=deleteNext;deleteNext=null;if(id && deleteButtons.has(id) && !deletePending && !deleteDialog)deletePress(id);}
// Queued Retry, Repair and Delete book (0.22.1, Judy's spec section 1): the engine's queue as last read, and the page's own
// notes. queuePresses: a Retry press on its way while the page is busy (book id). queueNotes: an outcome's row line until
// the next press, a filter change or a status change. queueLate: queued ids whose Cancel came too late (its line, Cancel
// hidden).
let queueState={queued:[],running:null},queueStripOutcome=null;
const queuePresses=new Map(),queueNotes=new Map(),queueSeen=new Set(),queueCancels=new Set(),queueLate=new Map();

let routingPreviewTimer=null,routingPreviewSequence=0;
function queueRoutingPreview(){
  if(routingPreviewTimer!==null)clearTimeout(routingPreviewTimer);const seq=++routingPreviewSequence;
  if(selectedRow?.kind!=='candidate')return;
  const original=selectedRow,library=selectedLibrary,review={};for(const field of fields)review[field]=form.elements.namedItem(field).value.trim();
  review.multi_author=form.elements.namedItem('multi_author').checked;review.anthology=form.elements.namedItem('anthology').checked;
  $('routing-preview-label').textContent='Unsaved destination preview';$('routing-preview-path').textContent='Checking destination…';
  routingPreviewTimer=setTimeout(async()=>{routingPreviewTimer=null;try{const response=await request('/api/candidate/routing-preview',{library,id:original.id,revision:original.revision,review});if(seq!==routingPreviewSequence||selectedRow?.id!==original.id)return;$('routing-preview-path').textContent=response.preview?.path || response.preview?.reason || 'Confirm the cycle or universe';}catch(error){if(seq===routingPreviewSequence&&selectedRow?.id===original.id)$('routing-preview-path').textContent=error.message;}},250);
}
function routingControls() {
  const audio=['audiobook','candidate'].includes(selectedRow?.kind);
  const anthology=audio && form.elements.namedItem('anthology').checked;
  for(const element of document.querySelectorAll('.audio-only'))element.hidden=!audio;
  form.elements.namedItem('author').disabled=false;
  form.elements.namedItem('multi_author').disabled=false;
  $('author-folder-help').hidden=!anthology;
  $('multi-author-help').hidden=false;
  renderNamesInputs();  // 0.22.3 (ruling 40): a book's name inputs stay off and hidden
}
function viewControls(){
  const audio=$('library').value==='Audiobooks';
  $('view').hidden=!audio;$('view-label').hidden=!audio;
  if(!audio)view='files';
  if(!filterOptions[view].some(([value])=>value===filters[view]))filters[view]=view==='candidates'?'converted':'all';
  $('view').value=view;
  $('filter').replaceChildren();
  // Before the library part arrives the Status filter has one option, "Loading…" ("Not loaded" when Stopped), 3.5.
  if(LS && loadingActive && !(state && partReady('library'))){const option=document.createElement('option');option.textContent=loadStopped()?'Not loaded':'Loading…';$('filter').append(option);}
  else for(const [value,label] of filterOptions[view]){const option=document.createElement('option');option.value=value;option.textContent=label;if(FILTER_TITLES[value])option.title=FILTER_TITLES[value];$('filter').append(option);}
  $('filter').value=filters[view];
  $('filter').title=FILTER_TITLES[filters[view]] || 'Filter the saved results in this library.';
  for(const id of ['automatic-controls','automatic-help','automatic-policy','automatic-status-block'])$(id).hidden=!audio;
  $('search-label').textContent=view==='files'?'Path contains':'Candidate contains';
  inventoryIntro.textContent=view==='files'?'Each row is a source file, including chapter tracks and companion files. Switch to Book candidates to review audiobook groups.':'Automatic processing researches book candidates and converts confident matches. Held books stay out of the queue; manual review is optional.';
  $('batch-controls').hidden=!audio || view!=='candidates' || !booksOnScreen();  // no "Select this page" before the books
  gateLoading();  // the titles above are the controls' own; while loading the gate's sentence stays (3.6)
}
const FILTER_TITLES={held:'Show books that automatic processing could not safely approve.',recording_review:'Show recordings marked for comparison, including verified distinct recordings.',
  restarted:'Show books you started over that automatic processing has not queued yet.'};
const connectionText='Connection interrupted; automatic processing may still be running. Retrying…';
const receivedStatus=new Map();
let refreshSequence=0;
let connectionNotice=$('connection-notice');
if(!connectionNotice){
  connectionNotice=document.createElement('p');connectionNotice.id='connection-notice';connectionNotice.hidden=true;
  connectionNotice.setAttribute('role','status');connectionNotice.setAttribute('aria-live','polite');
  $('message').insertAdjacentElement('afterend',connectionNotice);
}
let inventoryIntro=$('inventory-intro');
if(!inventoryIntro){inventoryIntro=document.createElement('p');inventoryIntro.id='inventory-intro';$('search-form').insertAdjacentElement('beforebegin',inventoryIntro);}
inventoryIntro.textContent='Each row is a source file, including chapter tracks and companion files. Book grouping, online metadata matching and merging are later steps.';

// ── Busy engine (Judy's 0.22.1 spec, section 4) ──
// In the desktop window a missing answer means "busy", never "interrupted": the shell closes the app itself, with its own
// message, when the engine process exits. So a slow answer sets no page-wide offline flag; a notice speaks after 3 s of
// silence, presses keep their pending face with the ladder below, and nothing reads "Connection interrupted" or "Local
// server unavailable". Browser mode (launch-web), where the server really can disappear, keeps the old words.
const BUSY_NOTICE='The app is busy with background work and answers slowly. This page refreshes by itself.';
const NOT_CONFIRMED={press:"This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check this row in a moment.",
  bulk:"The retry requests haven't been confirmed yet. They may still go through. Check the list in a moment.",
  discard:"The review may not have been discarded. The app hasn't confirmed it. Check the book before trying again.",
  delete:"The delete may not have finished. The app hasn't confirmed it. Check the list before trying again.",
  copy:"The removal may not have finished. The app hasn't confirmed it. Check the list before trying again."};
// A press that got no answer at all (4.3): the desktop's "not confirmed" line, else the browser's old one.
function lostLine(kind='press'){return desktopMode()?NOT_CONFIRMED[kind]:'Connection interrupted. Check the status above before trying again.';}
function desktopMode(){return !!shellApi;}
// Requests still waiting for an answer (any route), and when each status read was answered, per library.
const inflight=new Map(),receivedAt=new Map();let inflightSeq=0,busyShown=false;
function oldestWait(now=Date.now()){let oldest=null;for(const started of inflight.values())if(oldest===null || started<oldest)oldest=started;return oldest===null?0:Math.max(0,now-oldest);}
// The press ladder (4.3): the normal pending note, then one sentence more as time passes.
let ladderClock=null;  // the tick's own time while it renders (a fake clock in tests)
function ladderNote(note,since,now=ladderClock ?? Date.now()){
  if(!note || !Number.isFinite(since))return note;const age=now-since;
  if(age<3000)return note;
  if(age<60000)return `${note} The app is busy with background work, so this takes longer.`;
  return `${note} Still waiting (${Math.floor(age/60000)} min). The app is busy with background work.`;
}
function wallClock(ms){const d=new Date(ms);return [d.getHours(),d.getMinutes(),d.getSeconds()].map(v=>String(v).padStart(2,'0')).join(':');}
// The passes the last update named (4.2): at most three, in the order shown.
function busyPasses(){
  const parts=[],named=(row,words)=>{const n=Number(row?.total);return Number.isInteger(n) && n>0?words.replace('{n}',n.toLocaleString()):words.replace('{n} ','');};
  for(const row of Array.isArray(state?.activities)?state.activities:[]){
    if(row?.kind==='identity')parts.push(named(row,'re-checking {n} finished books'));
    else if(row?.kind==='series')parts.push(named(row,'updating series on {n} books'));
    else if(row?.kind==='scan' && row.step==='researching')parts.push(named(row,'researching {n} books'));
  }
  return parts.slice(0,3);
}
// The top of the page while an answer is missing (4.2), desktop only and only after loading (the load strip owns it then).
function renderBusy(now=Date.now()){
  const age=desktopMode() && !ended && !loadingActive?oldestWait(now):0;
  if(age<3000){if(busyShown)clearBusy();return;}
  const passes=busyPasses();
  const text=age<120000?BUSY_NOTICE+(passes.length?'\nBusy with: '+passes.join(', ')+'.':''):`No answer for ${Math.floor(age/60000)} min: the app is busy with background work. Your files are not touched. If it goes on, quit from the tray and open Books Arranger again.`;
  if(connectionNotice.textContent!==text)connectionNotice.textContent=text;connectionNotice.hidden=false;
  const library=$('library').value,at=receivedAt.get(library),status=`Last update ${at?wallClock(at):'not received yet'} · ${receivedStatus.get(library) || 'No status received yet.'}`;
  if($('status').textContent!==status)$('status').textContent=status;
  if(!busyShown){busyShown=true;renderJobs();}
}
function clearBusy(){
  busyShown=false;connectionNotice.hidden=true;if(connectionNotice.textContent)connectionNotice.textContent='';
  const text=receivedStatus.get($('library').value);if(text && $('status').textContent!==text)$('status').textContent=text;
  if(state?.audiobook_jobs)renderJobs();
}
// Once a second: the notice, and the ladder of any press waiting 3 s or more.
function pressTick(now=Date.now()){
  renderBusy(now);
  const since=[retryPending?.at,...[...askPendings.values()].map(item=>item.at),metaSave?.at,['deleting','queuing'].includes(deleteDialog?.state)?deleteDialog.at:null,...[...queuePresses.values()].map(item=>item.at)].filter(Number.isFinite);
  const clocks=clockSince(),reload=listWait && now-listWait.at>=1000 && !listWait.shown;if(reload)listWait.shown=true;
  if(since.some(at=>now-at>=3000) || clocks.some(at=>now-at>=2000) || since.some(at=>now-at>=2000) || reload){ladderClock=now;try{controls();if(rulesView.pending.size)renderAuthorRules();}finally{ladderClock=null;}if(['deleting','queuing'].includes(deleteDialog?.state))deleteStatusLine(now);}
}
function clearConnectionNotice(){
  recoveryDisconnected=false;
  // A status answer does not end the busy notice while another request (a slow press) still waits (4.2): no flicker.
  if(busyShown && oldestWait()>=3000)renderBusy();
  else{busyShown=false;connectionNotice.hidden=true;if(connectionNotice.textContent)connectionNotice.textContent='';}updateRecovery();renderAutomatic();renderJobs();controls();}
function refreshFailed(error){
  if(ended)return;
  if(loadingActive)return;  // the load strip owns silence while it is up: no notice, no "Last received" (Judy 7.7)
  // Desktop (4.1): no offline flag. An answer with an error is still shown; silence is the busy notice's (renderBusy).
  if(desktopMode()){if(error?.httpStatus){const prior=$('message').textContent;if(!prior.includes(error.message))message(prior ? prior+'\n'+error.message : error.message);}return;}
  if(error.httpStatus){
    const prior=$('message').textContent;
    if(!prior.includes(error.message))message(prior ? prior+'\n'+error.message : error.message);
  }
  recoveryDisconnected=true;closeRecoveryDialog();updateRecovery();
  if(connectionNotice.textContent!==connectionText)connectionNotice.textContent=connectionText;
  connectionNotice.hidden=false;
  $('status').textContent='Last received: '+(receivedStatus.get($('library').value) || 'No status received yet.');
  renderAutomatic();renderJobs();controls();
}

async function request(route, data, timeoutMs=0) {
  const options = {headers:{'X-Books-Token':token}, credentials:'same-origin', cache:'no-store'};
  if (data !== undefined && recoveryDisconnected)throw Error('Connection interrupted. Wait for the local server to reconnect.');
  if (data !== undefined) { options.method='POST'; options.headers['Content-Type']='application/json'; options.body=JSON.stringify(data); }
  // An optional bound: a request with no reply by then ends like a lost connection (no httpStatus).
  const controller=timeoutMs && typeof AbortController==='function'?new AbortController():null;
  if(controller)options.signal=controller.signal;
  const timer=controller?setTimeout(()=>controller.abort(),timeoutMs):null;
  const ticket=++inflightSeq;inflight.set(ticket,Date.now());
  let response;
  try{response = await fetch(route, options);}finally{if(timer)clearTimeout(timer);inflight.delete(ticket);if(busyShown)renderBusy();}
  const result = await response.json();
  if (!response.ok) {const error=new Error(result.error || `Local request failed (${response.status})`);error.httpStatus=response.status;error.automaticProcessing=result.automatic_processing;error.body=result;throw error;}
  return result;
}
function message(value='') { $('message').textContent=value; }
// The only writer of #version: the engine's own version, as reported by its state. Hidden while loading (Judy 3.5).
function renderVersion(){const value=typeof state?.version==='string' && state.version && !loadingActive?'v'+state.version:'';if($('version').textContent!==value)$('version').textContent=value;$('version').hidden=!value;}

// ── Startup (ruling 28; Judy's 0.22.1 UX spec, section 3) ──
// The window shows this page from the first frame: from disk until the engine answers (preEngine), then served by the
// engine. One strip says Working, Waiting, Stuck or Stopped from silence (load-state.js); each panel keeps its
// placeholder until its part arrives; looking works once the books are on screen, changing waits until loading ends.
const LS=globalThis.booksLoadState || null,shellApi=globalThis.window?.booksDesktop || null;
const preEngine=globalThis.location?.protocol==='file:';
const NOT_YET='Not yet: Books Arranger is still loading. This works when loading finishes.';
const NOT_YET_BOOKS='Not yet: your books are still loading. This works as soon as they appear.';
const NOT_YET_LIBRARY='Not yet: Books Arranger is still loading. You can switch library when loading finishes.';
const NOT_SAFE='Not safe right now: the engine is changing the catalog. Wait for it to finish.';
let loadingActive=!!LS,loadTracker=LS?LS.createTracker(Date.now()):null,loadAnswer=null,shellStartup=null,loadVerdict='working',loadStep='',loadReadyMs=null;
const notYetSentences=new Set([NOT_YET,NOT_YET_BOOKS,NOT_YET_LIBRARY,NOT_SAFE]);
// A part of the engine's answer that has arrived (an engine without a loading object has them all).
function partReady(name,answer=state){return !LS || (!!answer && LS.part(answer,name));}
function booksOnScreen(){return !loadingActive || partReady('books');}
function loadStopped(){return !!shellStartup && shellStartup.phase==='stopped';}
function announceLoad(text){const node=$('load-announce');if(!node)return;node.textContent='';node.textContent=text;}
// The shell's record (desktop): launch time, exit, port, last load. A new launch (Restart engine) restarts the clocks.
function applyStartup(value){
  if(!LS || !value || typeof value!=='object')return;
  const fresh=!shellStartup || value.startedAt!==shellStartup.startedAt;
  const wasStopped=loadStopped();shellStartup=value;
  if(fresh && value.phase==='launching')loadTracker.restart(value.startedAt);
  else if(fresh)loadTracker.launchedAt=value.startedAt;
  if(!wasStopped && loadStopped() && loadingActive)announceLoad('Books Arranger stopped loading. Try again is available.');
  renderLoad();loadPlaceholders();
}
// Every engine answer: the loading object, or none (loaded). A "still updating" 503 is an answer too (heard).
function observeLoad(answer){
  if(!LS || !loadingActive)return;
  loadTracker.observe(answer,Date.now());
  loadAnswer=answer?.loading && typeof answer.loading==='object'?answer.loading:null;
  renderLoad();  // refresh() settles, once the first list is on screen too
}
function loadHeard(){if(LS && loadingActive){loadTracker.heard(Date.now());renderLoad();}}
function loadTick(){if(LS && loadingActive){loadTracker.tick(Date.now());renderLoad();}}
function loadTechnical(verdict){
  const lines=[],step=LS.stepOf(loadTracker.answered?loadAnswer:null),now=Date.now();
  lines.push(`Step: ${step.id} (${step.n} of ${step.of})`);
  if(loadAnswer && Number.isFinite(loadAnswer.done))lines.push(`Counts: ${loadAnswer.done}${Number.isFinite(loadAnswer.total)?' of '+loadAnswer.total:''} ${loadAnswer.unit || 'items'}`);
  lines.push(`Engine answered: ${loadTracker.answered?Math.floor((now-loadTracker.answerAt)/1000)+' s ago':'never'}`);
  lines.push(`Progress: ${Math.floor((now-loadTracker.progressAt)/1000)} s ago`);
  lines.push(`Loading started: ${new Date(loadTracker.launchedAt).toISOString()}`);
  lines.push(`State: ${verdict.state}${loadAnswer?.restart_safe===false?' (the engine is changing the catalog)':''}`);
  if(loadAnswer?.error)lines.push('Engine: '+loadAnswer.error);
  if(shellStartup?.exited){lines.push(`Engine exit code: ${shellStartup.exited.code ?? 'unknown'}`);if(shellStartup.exited.lastLines)lines.push('Last engine output:\n'+shellStartup.exited.lastLines);}
  return lines.join('\n');
}
function renderLoad(){
  if(!LS || !loadingActive || !$('load-strip'))return;
  const now=Date.now(),stopped=loadStopped(),verdict=LS.evaluate(loadTracker,now,{stopped});
  const loading=loadTracker.answered?loadAnswer:null,step=LS.stepOf(loading),line=LS.stateLine(verdict,loading,{portPid:shellStartup?.portPid});
  setText('load-word',line.word);setText('load-text',line.text);
  $('load-strip').classList?.toggle('alert',['stuck','stopped'].includes(verdict.state));
  const fraction=LS.fraction(loading),segments=[...(document.querySelectorAll?.('#load-bar .load-segment') || [])];
  segments.forEach((segment,index)=>{
    const current=index===step.n-1;
    segment.classList?.toggle('done',index<step.n-1);
    // A moving stripe means real movement: only a step that cannot count, only in Working (Judy 3.9).
    segment.classList?.toggle('moving',current && fraction===null && verdict.state==='working' && loadTracker.answered);
    segment.classList?.toggle('alert',current && ['stuck','stopped'].includes(verdict.state));
    const fill=segment.firstElementChild || segment.firstChild;
    if(fill?.style)fill.style.width=current?(fraction===null?(['stuck','stopped'].includes(verdict.state)?'100%':''):Math.round(fraction*100)+'%'):'';
  });
  const bar=$('load-bar');bar.setAttribute('aria-valuemax',String(step.of));bar.setAttribute('aria-valuenow',String(Math.round((step.n-1+(fraction ?? 0))*100)/100));bar.setAttribute('aria-valuetext',LS.valueText(loading));
  const detail=stopped?[]:LS.detailParts(loadTracker,now,loading,shellStartup?.lastLoadMs),detailText=detail.join(' · ');
  if($('load-detail').dataset?.text!==detailText){$('load-detail').replaceChildren(...detail.flatMap((part,i)=>i?[' · ',node('span',part)]:[node('span',part)]));if($('load-detail').dataset)$('load-detail').dataset.text=detailText;}
  $('load-detail').hidden=stopped;
  const stuck=verdict.state==='stuck',actions=stuck || stopped;
  $('load-actions').hidden=!actions;$('load-details').hidden=!actions;
  // Restart engine and Try again are the shell's (desktop); browser mode keeps Copy details only (Judy 3.4).
  $('load-restart').hidden=!(stuck && !stopped && shellApi);$('load-retry').hidden=!(stopped && shellApi);
  const unsafe=loading?.restart_safe===false;
  $('load-restart').setAttribute('aria-disabled',unsafe?'true':'false');$('load-restart').title=unsafe?NOT_SAFE:'Stop the engine and start it again. Loading starts over. Your files are not touched.';
  if(actions)setText('load-technical',loadTechnical(verdict));
  // Announcements: events only (a step starts, Stuck, moving again, Stopped); Waiting is not announced.
  const stepKey=`${step.n}/${step.of}/${step.id}`;
  if(stepKey!==loadStep && !stopped){if(loadStep)announceLoad(`Step ${step.n} of ${step.of}: ${step.words}.`);loadStep=stepKey;}
  if(verdict.state!==loadVerdict){
    // N4 (Judy's implementation check): an inert Restart engine is never announced as available.
    if(stuck)announceLoad(`Loading is stuck. ${verdict.signal==='answer'?`The engine hasn't answered for ${LS.duration(verdict.quiet)}.`:`No progress for ${LS.duration(verdict.quiet)}.`}${!shellApi?'':unsafe?' The engine is changing the catalog, so Restart engine waits.':' Restart engine is available.'}`);
    else if(loadVerdict==='stuck' && verdict.state==='working')announceLoad('Loading is moving again.');
    loadVerdict=verdict.state;
  }
}
// Placeholders (Judy 3.5): "loading…" while loading, "not loaded" when Stopped. Never a number for a missing part.
function loadPlaceholders(){
  if(!LS || !loadingActive)return;
  const word=loadStopped()?'not loaded.':'loading…',library=state && partReady('library'),books=partReady('books');
  if(!library){setText('root',`Source folders: ${word}`);viewControls();}
  if(!(state && partReady('status')))setText('status',`Library status: ${word}`);
  if(!(state && partReady('jobs'))){
    setText('automatic-status',`Automatic processing: ${word}`);setText('research-status',`Research: ${word}`);
    setText('automatic-start-reason',loadStopped()?'':'Automatic processing can start when loading finishes.');$('automatic-start-reason').hidden=loadStopped();
    setText('jobs-status',loadStopped()?'Jobs: not loaded.':'Jobs: loading…');setText('book-candidate-counts',loadStopped()?'Book candidates: not loaded.':'Book candidates: loading…');
    $('jobs-idle').hidden=true;
    // Futaba's 0.22.1 QA, m-7: the panel itself was hidden until the jobs part came, so these lines never showed (3.5:
    // the Audiobook jobs panel is shown at its reserved height with them).
    $('audio-jobs').hidden=$('library').value!=='Audiobooks';
  }
  const attention=view==='candidates' && filters.candidates==='output_attention' && !(state && partReady('attention'));
  $('attention-loading').hidden=!attention;if(attention)setText('attention-loading',`Output needs attention: ${word}`);
  if(!books){
    const text=loadStopped()?'Your books are not loaded.':'Loading your books…';
    setText('empty',text);$('empty').hidden=false;setText('page',text);$('list-skeleton').hidden=loadStopped();
    // M3 (Judy's implementation check): the list's body is busy while its part is on its way, never <body>, which would
    // hold the live regions under it (#load-announce). The first list render clears it, as after a filter change.
    if(loadStopped())$('inventory').removeAttribute?.('aria-busy');else $('inventory').setAttribute?.('aria-busy','true');
  }else $('list-skeleton').hidden=true;
}
// Settling (3.7): one render pass, then the strip is one quiet line for the session.
function settleLoad(tookMs){
  if(!LS || !loadingActive)return;
  loadingActive=false;loadReadyMs=Number.isFinite(tookMs)?tookMs:null;
  const strip=$('load-strip'),focused=strip?.contains?.(globalThis.document?.activeElement);
  ungateAll();
  if(notYetSentences.has($('message').textContent))message();
  $('attention-loading').hidden=true;$('list-skeleton').hidden=true;
  if(strip){
    // Futaba's 0.22.1 QA, m-6: the strip shrank by 53 px at the settle (bar, detail line and margins), moving Quit and
    // everything under it past Judy's 48 px limit (3.7, point 4). Her fallback: the strip keeps its height for the session.
    const height=strip.getBoundingClientRect?.().height;
    if(loadReadyMs===null)strip.hidden=true;  // an engine that loads before it answers: no strip at all
    else{strip.classList?.remove('alert');strip.classList?.add('ready');setText('load-word','Ready');setText('load-text',LS.readyLine(loadReadyMs).replace(/^Ready · /,''));
      if(height>0&&strip.style)strip.style.minHeight=height+'px';}
    for(const id of ['load-bar','load-detail','load-actions','load-details'])$(id).hidden=true;
  }
  if(loadReadyMs!==null)announceLoad('Books Arranger is ready.');
  if(focused)$('filter').focus?.({preventScroll:true});  // the standing fallback (1.7)
  viewControls();renderVersion();controls();
}
// Inert while loading (3.6): aria-disabled (still focusable), the sentence as tooltip; never the disabled attribute.
const LOOKING_CONTROLS=['view','search','filter','clear-filters','previous','next'];
const CHANGING_CONTROLS=['start','stop','resume','start-automatic','stop-automatic','cancel-automatic-start','pause-jobs','resume-jobs','select-page','queue-books','retry-selected','approve-selected','release-selected','retry-all','retry-all-go','retry-job'];
function gate(element,sentence){
  if(!element?.setAttribute)return;
  if(sentence){
    if(!element.hasAttribute?.('data-not-yet') && element.dataset){element.dataset.titleBefore=element.title || '';element.dataset.ariaBefore=element.getAttribute('aria-disabled') ?? '';}
    element.setAttribute('data-not-yet','');element.setAttribute('aria-disabled','true');element.disabled=false;
    if(element.title!==sentence)element.title=sentence;
    if(element.tagName==='INPUT' && element.type!=='checkbox' || element.tagName==='TEXTAREA')element.readOnly=true;
  }else if(element.hasAttribute?.('data-not-yet')){
    element.removeAttribute('data-not-yet');element.title=element.dataset?.titleBefore || '';
    if(element.dataset?.ariaBefore)element.setAttribute('aria-disabled',element.dataset.ariaBefore);else element.removeAttribute('aria-disabled');
    if(element.tagName==='INPUT' || element.tagName==='TEXTAREA')element.readOnly=false;
  }
}
// The read-only row and details controls work once the books are on screen; everything else in them changes something.
function lookingOnly(element){return /^(View metadata|Open folder|Source folders)\b/.test(element.getAttribute?.('aria-label') || element.textContent || '');}
function gateLoading(){
  if(!LS || !loadingActive)return;
  const books=booksOnScreen();
  gate($('library'),NOT_YET_LIBRARY);
  for(const id of LOOKING_CONTROLS)gate($(id),books?'':NOT_YET_BOOKS);
  // Ruling 35 (Sergei 2026-10-26): changing presses are accepted while loading. The toolbar's wait in this page (later())
  // and run when loading finishes; a row's go to the engine, which queues them until it has loaded. Only what cannot work
  // before the books are on screen stays inert: switching library, and the list's own controls.
  for(const element of globalThis.document?.querySelectorAll?.('#inventory button,#inventory input,#details button,#details input,#details select,#details textarea') || [])
    if(lookingOnly(element))gate(element,books?'':NOT_YET_BOOKS);
}
function ungateAll(){for(const element of globalThis.document?.querySelectorAll?.('[data-not-yet]') || [])gate(element,'');}
// A press on an inert control is answered in the message line; focus does not move (3.6).
function refuseInert(event){
  const element=event.target?.closest?.('[data-not-yet]');
  if(!element || !loadingActive)return;
  if(event.type==='keydown' && ['Tab','Shift','Escape'].includes(event.key))return;
  event.preventDefault();event.stopImmediatePropagation();
  if(event.type!=='mousedown' || element.tagName==='SELECT')message(element.title);
}
async function restartFromStrip(button){
  if(button.getAttribute('aria-disabled')==='true'){message(button.title);return;}
  announceLoad('Restarting the engine.');
  try{await shellApi?.restartEngine?.();}catch(error){message(error.message);}
}
if(LS && $('load-strip')){
  $('load-restart').addEventListener('click',()=>restartFromStrip($('load-restart')));
  $('load-retry').addEventListener('click',()=>restartFromStrip($('load-retry')));
  $('load-copy').addEventListener('click',async()=>{
    try{const clipboard=globalThis.navigator?.clipboard;if(!clipboard?.writeText)throw Error('no clipboard');await clipboard.writeText($('load-technical').textContent || '');setText('load-copy-status','Copied.');}
    catch{setText('load-copy-status',"Couldn't copy. Select the text and press Ctrl+C.");}
  });
  for(const type of ['click','mousedown','keydown'])globalThis.document?.addEventListener?.(type,refuseInert,true);
}
function controls() {
  updateRecovery();updateRetry();updateRowRetries();renderAttentionGroups();updateAskRows();updateDeleteButtons();renderApproveSelected();renderAttentionShortcut();
  const active = state?.active_library;
  const automatic=state?.automatic_processing,automaticOwnsScanner=['Running','Stopping'].includes(automatic?.state);
  // Ruling 35: another press of this page never disables a button (later() holds the press until it is free).
  $('start-automatic').disabled=ended || recoveryDisconnected || automatic?.can_start!==true || !!draftLeaseFailure || !!(manualDraftLease?.active && !manualDraftLease.confirmed);
  renderAutomaticEligibility();
  $('stop-automatic').disabled=ended || recoveryDisconnected || automatic?.can_stop!==true;
  // Cancel automatic start (O12): shown only while a start is pending; the notice above says what it waits for.
  if($('cancel-automatic-start')){const cancel=$('cancel-automatic-start'),active=globalThis.document?.activeElement;cancel.hidden=!startPending(automatic) && active!==cancel;cancel.disabled=busy || ended || recoveryDisconnected || automaticRequest!==null || !startPending(automatic);}
  const stopped = ['stopped','offline','failed'].includes(state?.status?.state);
  // Start and Resume scanning queue behind conversion or automatic processing (ruling 35): only a running scan holds them.
  $('start').disabled = ended || recoveryDisconnected || !!active || stopped;
  $('resume').disabled = ended || recoveryDisconnected || !!active || !stopped;
  $('stop').disabled = ended || recoveryDisconnected || !active || state?.stopping || automaticOwnsScanner;
  $('shutdown').disabled = ended || recoveryDisconnected;
  $('approve-candidate').disabled=ended || recoveryDisconnected || dirty || selectedRow?.kind!=='candidate' || !selectedRow?.can_approve;
  if(selectedRow?.kind==='candidate')$('approval-reason').textContent=dirty ? 'Save the draft metadata before approving it.' : selectedRow.approval_reason || '';
  $('approval-reason').hidden=!$('approval-reason').textContent;
  if($('create-audiobook'))$('create-audiobook').disabled=ended || recoveryDisconnected || dirty || trackDirty || !selectedRow?.creation?.can_create || selectedRow?.creation?.status==='Single audiobook file';
  for(const id of ['source-coverage','playback-order'])if($(id))$(id).disabled=ended || recoveryDisconnected;
  if($('add-chapters'))$('add-chapters').disabled=ended || recoveryDisconnected || !selectedRow?.creation?.chapters_available;
  if($('check-metadata')){$('check-metadata').hidden=selectedRow?.kind!=='candidate';$('check-metadata').disabled=ended || recoveryDisconnected || dirty || selectedRow?.kind!=='candidate';$('check-metadata-save').hidden=!dirty;}
  for(const id of ['find-metadata','find-covers','save-tracks'])if($(id))$(id).disabled=ended || recoveryDisconnected || selectedRow?.kind!=='candidate';
  if($('queue-books'))$('queue-books').disabled=ended || recoveryDisconnected || !rows.some(readyForQueue);
  if($('retry-selected'))renderRetrySelected();
  if($('release-selected'))renderReleaseSelected();
  if($('pause-jobs'))$('pause-jobs').disabled=ended || recoveryDisconnected || !['Running','running'].includes(state?.audiobook_jobs?.state);
  if($('resume-jobs')){
    // The rest of ruling 35 (ruling 37): pressed while a Pause settles it is kept, so it is no longer disabled while Pausing;
    // while it is kept, the same button takes it back.
    const jobs=state?.audiobook_jobs,waiting=jobs?.start_waiting;
    $('resume-jobs').disabled=ended || recoveryDisconnected || !waiting && (!(jobs?.queued || jobs?.retry_checks?.waiting) || ['Running','running'].includes(jobs?.state));
    startWaitTip($('resume-jobs'),waiting);
  }
  renderMetaSave();updateNamesRows();renderLaterButtons();if(choiceSave)updateMetadataChoiceControls();if(trackSave)trackSaveLine();renderNamesFacts();
  gateLoading();  // last: while loading it overrides the states above (Judy 3.6)
  drainLater();
  if(metaQueued && !busy && !metaSave)saveMetadata();  // a Save pressed during another press runs now (ruling 35)
}
async function action(route, data) {
  if (ended) return;
  if (busy){pressLater('press:'+route,{'/api/scan/start':'scan_start','/api/scan/resume':'scan_resume','/api/scan/stop':'scan_stop','/api/audiobook/pause':'pause','/api/audiobook/resume':'resume'}[route],'',()=>action(route,data));return;}
  busy=true; controls(); message();
  // Ruling 35: Start and Resume scanning are accepted while conversion or automatic processing runs and start when they end.
  const queueable=route==='/api/scan/start' || route==='/api/scan/resume';
  try { const answer=await request(route,queueable?{...data,queue:true}:data); if(answer?.queued===true)message(`${laterWord(route.endsWith('/start')?'scan_start':'scan_resume')} queued. It starts when ${queueP(answer.blocker?.kind)} finishes.`);
    // The rest of ruling 35 (ruling 37): Resume while a Pause or an earlier start settles is kept; the same button cancels it.
    else if(route==='/api/audiobook/resume' && answer?.start_admission?.state==='waiting')message(startWaitLine(answer.start_admission.reason));
    else if(route==='/api/audiobook/resume-cancel' && answer?.cancelled===true)message('Resume audiobook jobs cancelled. Nothing was started.');
    lastKey=null; await refresh(true); }
  catch(error) {
    const kind={'/api/scan/start':'scan_start','/api/scan/resume':'scan_resume','/api/audiobook/resume':'resume'}[route];
    // A scan that began after the page looked: the press waits for it and is sent again (ruling 35), never refused.
    if(error.body?.code==='scanning' && kind){const item=pressLater('press:'+route,kind,'',()=>action(route,data),scanSeen());message(laterLine(item)+' Press it again to cancel.');}
    else if(route==='/api/audiobook/resume-cancel' && error.body?.code==='started')message('Too late to cancel: Resume audiobook jobs has already started.');
    else message(error.message);
  }
  finally { busy=false; controls(); }
}
// Provisional copy (ruling 35's rest, sent to Judy): what a kept Resume waits for.
const START_WAITS={pause:'the pause',start:'the earlier start'};
function startWaitLine(reason){return `Resume audiobook jobs queued. It starts when ${START_WAITS[reason] || 'the pause'} finishes. Press it again to cancel.`;}
function startWaitTip(button,waiting){
  if(!button?.setAttribute || !button.dataset || laterFor('toolbar:resume-jobs'))return;  // a press the page holds says its own line
  if(waiting){if(button.dataset.waitTitle===undefined)button.dataset.waitTitle=button.title || '';const tip=startWaitLine(waiting.reason);if(button.title!==tip)button.title=tip;}
  else if(button.dataset.waitTitle!==undefined){button.title=button.dataset.waitTitle;delete button.dataset.waitTitle;}
}
// One rule (Judy, MissingFiles UX 2026-10-24): a read error is an error on a file that is not gone. A gone file's old error
// stays in the catalog, never on screen; the server's counts and filters use the same predicate.
function readError(row){return row.error && !row.missing ? row.error : '';}
function select(row, reset) {
  $('manual-review').hidden=false;
  const changing=selectedPath!==row.path;
  if(reset && (changing || dirty || trackDirty)){discardManualDraft();if(changing)$('manual-review').open=row.kind!=='candidate';}
  // Technical details: closed again on every selection; "Copied." stays until the selection changes (Judy, section 4.6).
  if(changing && $('technical-details')){$('technical-details').open=false;setText('copy-technical-status','');}
  if(changing){metaSaveResult=null;panelDiscarded=null;trackSave=null;choiceSave=null;if($('track-save-status'))$('track-save-status').textContent='';automaticResultKey=null;automaticInspectorKey=null;closeRecoveryDialog(false);recoveryPanel=null;inspectorIdentity=null;++inspectSequence;$('metadata-inspector').hidden=true;for(const url of inspectorObjects)URL.revokeObjectURL(url);inspectorObjects.length=0;}
  selectedPath=row.path; selectedRow=row;
  updateRecovery();
  selectedLibrary=row.library || $('library').value;
  const candidate=row.kind==='candidate';
  $('details').hidden=false;
  $('details-heading').textContent=inspectorIdentity?.id===recordIdentity(row).id?(candidate?'Book metadata':'File metadata'):(candidate?'Book candidate':'Selected file');
  $('source').textContent=candidate?row.scope:row.path;
  $('reason').textContent=row.preview.reason;
  $('proposed').textContent=(candidate?'Reviewed destination preview: ':'')+(row.preview.path || 'No destination proposed until canonical metadata is reviewed.');
  $('method').textContent=row.metadata.method || 'Unavailable';
  $('language').textContent=row.metadata.edition_language || 'Unknown';
  $('series-clue').textContent=`${row.metadata.series || 'Unknown'} / ${row.metadata.number || 'Unknown'}`;
  $('genre-clue').textContent=row.metadata.genre || 'Unknown';
  $('notes').textContent=[...(row.metadata.notes || []),readError(row)].filter(Boolean).join(' · ');
  $('tags').textContent=JSON.stringify(row.metadata.tags || {},null,2);
  $('read-error').hidden=!readError(row);
  $('read-error-path').textContent=row.path;
  $('read-error-time').textContent=row.error_time ? `Last failed read: ${row.error_time}` : 'Last failed read time was not recorded.';
  $('read-error-message').textContent=readError(row);
  $('read-error-action').textContent=readError(row).startsWith('File changed during read') ? 'The file changed while its metadata was being read. Let copying finish, then start scanning to retry it.' : row.size===0 && row.kind==='audiobook' && row.metadata.notes?.includes('Metadata read failed; source file untouched') ? 'This audio file is empty. Replace it with a complete copy, then start scanning.' : 'Start scanning to retry unreadable files.';
  $('tags-heading').textContent=row.saved_snapshot?'Saved metadata snapshot':'Existing tag snapshot';
  $('candidate-details').hidden=!candidate;$('candidate-approval').hidden=!candidate;
  if(candidate){
    $('candidate-evidence').textContent=[row.grouping,`Title / album clues: ${row.title_evidence.join('; ') || 'Unknown'}`,'Edition / recording unverified',...row.conflicts].join(' · ');
    $('candidate-coverage').textContent=row.coverage;
    $('companion-count').textContent=`Related companion files — ${row.companions.length}`;
    $('candidate-companions').replaceChildren();for(const companion of row.companions){const p=document.createElement('p');p.textContent=companion.path;$('candidate-companions').append(p);}
  }
  $('audio-preview').hidden=!['audiobook','candidate'].includes(row.kind);
  if(['audiobook','candidate'].includes(row.kind)) {
    const sourceArtist=row.metadata.artist || Object.entries(row.metadata.tags || {}).find(([name])=>name.toLowerCase()==='artist')?.[1];
    $('source-artist').textContent=sourceArtist || 'Unknown';
    const tags=row.tag_preview || {};
    $('future-artist').textContent=tags.ARTIST || 'Needs author review';
    $('artist-fallback').hidden=!tags.artist_from_folder;
    $('future-narrator').textContent=tags.narrator || 'Not reviewed';
    const comments=tags.comment_fields || [];
    let text=comments.length>1 ? comments.map(item=>`${item.field}: ${item.value}`).join('\n') : tags.existing_comments || '';
    if(tags.narrator_appended)text+=(text ? '\n' : '')+`Narrator: ${tags.narrator}`;
    $('future-comments').textContent=text || 'No existing comments';
  }
  form.hidden=!['audiobook','ebook','candidate'].includes(row.kind) || !!row.error || !!row.missing;
  renderNamesInputs();if(candidate)loadNamesFacts(row);  // 0.22.3 (ruling 40): a book's names are facts here, edited on its row
  if (reset || (!dirty && !form.contains?.(document.activeElement))) {
    for (const field of fields) form.elements.namedItem(field).value=row.review?.[field] || (field==='original_language' ? 'Unknown' : '');
    form.elements.namedItem('multi_author').checked=!!row.review?.multi_author;
    form.elements.namedItem('anthology').checked=!!row.review?.anthology;
    dirty=false;
    reviewRow=row;
    $('review-note').textContent='Saved only in the local catalog.';
  }
  routingControls();
  renderMergeCandidate(row,reset);
  renderAutomaticResult(row);
  if(candidate)ensureCandidateInspector(row);
  controls();
  for (const element of $('inventory').children) element.setAttribute('aria-selected',String(element.dataset.path===row.path));
}
function renderRows(force=false) {
  const focused=document.activeElement;
  if(!force && focused && $('inventory').contains?.(focused)){
    // Focus stays put: the attention rows take the fresh data in place (updateRowRetries), so a refusal that lands
    // while Sergei is on a row shows there, and a removed Retry hands focus to the row's next button.
    for(const entry of rowRetries.values()){const fresh=rows.find(row=>row.path===entry.row.path);if(fresh)entry.row=fresh;}
    // The to-do rows take fresh data in place too; a row Sergei settled (approved, removed, found) leaves at this
    // refresh unless it holds focus.
    for(const entry of askRows.values()){const fresh=rows.find(row=>row.id===entry.row.id);if(fresh)entry.row=fresh;}
    updateNamesRows();  // Edit names takes fresh data in place too (its draft stays)
    for(const tr of [...($('inventory').children || [])]){const id=tr.dataset?.path;if(askDone.has(id) && !rows.some(row=>row.path===id) && (!tr.contains?.(focused) || deletedBooks.has(id))){$('inventory').removeChild?.(tr);askRows.delete(id);askDone.delete(id);}}
    updateAskRows();
    const selected=rows.find(row=>row.path===selectedPath);if(selected)select(selected,false);return;}
  const listFocus=!!document.activeElement && !!$('inventory').contains?.(document.activeElement);  // m-10: focus the rebuild drops
  const body=$('inventory'); body.replaceChildren();askRows.clear();deleteButtons.clear();namesRows.clear();
  for(const outcomes of [askDone,askResults,askChecked])for(const id of [...outcomes.keys()])if(!rows.some(row=>row.id===id))outcomes.delete(id);
  const attentionList=view==='candidates' && filters[view]==='output_attention';
  // In this filter the list window grows with the viewport: rows with fields are 150-230 px tall (section 9).
  // Edit names (Judy 1.2): while any editor is open, in every filter, so an open editor is never clipped.
  $('inventory-scroll')?.classList?.toggle('tall',attentionList || namesAny());
  $('inventory-head').replaceChildren();const heading=document.createElement('tr');heading.setAttribute('role','row');
  // The narrow table (follow-up 3, section 5): the bands come from CSS; explicit roles keep the table's meaning when a
  // narrow band shows each row as a block.
  $('inventory-table')?.classList?.toggle('candidates',view==='candidates');$('inventory-table')?.classList?.toggle('files',view!=='candidates');
  for(const label of view==='candidates'?['Select','Title clue','Author / reader clues','Audio files','Review status','Actions']:['Type','Arrival','Existing title / filename clue','Existing author / artist clue','Preview status','Proposed destination','Actions']){const th=document.createElement('th');th.textContent=label;th.setAttribute('role','columnheader');heading.append(th);}$('inventory-head').append(heading);
  for (const row of rows) {
    const tr=document.createElement('tr'); tr.dataset.path=row.path; tr.tabIndex=0;tr.setAttribute('role','row');
    tr.setAttribute('aria-selected',String(row.path===selectedPath));
    if(row.kind==='candidate'){const td=document.createElement('td'),label=document.createElement('label'),check=document.createElement('input');td.setAttribute('role','cell');label.className='check';check.type='checkbox';check.checked=selectedBooks.has(row.id);check.setAttribute('aria-label','Select '+row.title_clue);check.title='Select this candidate for the reviewed audiobook queue.';check.addEventListener('click',event=>event.stopPropagation());check.addEventListener('keydown',event=>event.stopPropagation());check.addEventListener('change',()=>{if(check.checked)selectedBooks.set(row.id,row.revision);else selectedBooks.delete(row.id);batchCounts();});label.append(check);td.append(label);tr.append(td);}
    const values=row.kind==='candidate'?[candidateTitle(row),row.artists.join('; ') || 'Unknown',row.members.length,candidateStatus(row)]:[row.kind,row.arrival ? 'Yes' : '',row.metadata.title || row.path.split(/[\\/]/).pop(),row.metadata.author || '',readError(row) ? `Read error · ${readError(row).split(/\r?\n/)[0].slice(0,200)}`:row.preview.confidence,row.preview.path || 'Needs review'];
    for (const [index,value] of values.entries()) { const td=document.createElement('td'); td.textContent=value;td.setAttribute('role','cell');
      // Medium and compact bands fold the two clue columns into a second line of the title cell (follow-up 3, section 5).
      if(row.kind==='candidate' && index===0)td.append(node('p',titleFacts(row),'field-help title-facts'));
      if(row.kind==='candidate' && index===3){
        // One honest state per row: attention, a queued-next press, the Started over marker, or a saved-review hold.
        // (A book waiting its turn after Retry keeps its disabled "Queued" button, v0.16.12.)
        if(askOf(row))buildAskCell(row,td);  // a book only Sergei can move on: its sentence, fields, Goes to (Judy 2026-10-24)
        else{
        const shown=rowState(row);
        if(shown){const hint=node('p','','field-help attention-hint');setHint(hint,shown.hint,shown.clause,shown.warn);td.append(hint);stoppedGoesTo(row,td);if(attentionOf(row))td.title=cellTip(row);rowRetries.set(row.path,{row,hint,button:null,clear:null,cell:td});}
        else if(repairedText(row.creation?.job?.repaired))td.append(node('p',repairedText(row.creation.job.repaired),'field-help attention-hint'));
        else if(row.creation?.job?.kept===true)td.append(node('p',KEPT_HINT,'field-help attention-hint'));
        if(recordingMarker(row))td.append(node('p',recordingMarker(row),'field-help'));
        }
        buildNamesBlock(row,td);  // Edit names (Judy 0.22.2 section 1): Place, Entered by you, the editor when open
      }
      tr.append(td); }
    const actions=node('td'),buttons=node('div','','row-actions'),name=row.title_clue || row.metadata?.title || row.path.split(/[\\/]/).pop();actions.setAttribute('role','cell');
    const rowRetry=rowRetries.get(row.path),action=rowAction(row);
    if(rowRetry && action){
      const retry=node('button',action.label,'quiet row-retry');retry.type='button';rowRetry.button=retry;
      rowRetry.hint.id='attention-hint-'+row.id;retry.setAttribute('aria-describedby',rowRetry.hint.id);
      retry.addEventListener('click',event=>{event.stopPropagation();if(retry.getAttribute?.('aria-disabled')==='true' || retryPending)return;retryFromRow(row,retry);});
      retry.addEventListener('keydown',event=>event.stopPropagation());buttons.append(retry);
      // Cancel retry beside the queued face (Judy 1.3): its own target, hidden until a press is queued.
      // Ruling 35: every row action can be queued (by the engine, or held by the page), so every one has its Cancel.
      rowRetry.cancel=queueCancelButton(row,action.kind);buttons.append(rowRetry.cancel);
    }
    // Clear working files (decision B): beside the action, only while the server says the files are cleanable; never disabled.
    if(rowRetry && workingOf(row)?.state==='cleanable'){
      const clear=node('button','Clear working files','quiet row-clear');clear.type='button';rowRetry.clear=clear;
      clear.addEventListener('click',event=>{event.stopPropagation();if(clear.getAttribute?.('aria-disabled')==='true')return;clearFromRow(row,clear);});
      clear.addEventListener('keydown',event=>event.stopPropagation());buttons.append(clear);
    }
    if(askOf(row))buildAskActions(row,buttons);
    if(row.kind==='candidate')buildNamesButton(row,buttons);  // after the row's own buttons, before View metadata (Judy 1.1)
    const inspect=node('button','View metadata','quiet');inspect.type='button';inspect.title='Show metadata, artwork and the file location.';inspect.setAttribute('aria-label','View metadata: '+name);inspect.setAttribute('aria-describedby','inspect-help');inspect.disabled=!recordIdentity(row).id;inspect.addEventListener('click',event=>{event.stopPropagation();viewMetadata(row);});inspect.addEventListener('keydown',event=>event.stopPropagation());buttons.append(inspect);
    if(row.kind==='candidate' && row.source_directory_count!==1){const folders=node('button','Source folders','quiet');folders.type='button';folders.title="Show the folders containing this candidate's source tracks.";folders.setAttribute('aria-label','Source folders: '+name);folders.setAttribute('aria-describedby','folder-help');folders.addEventListener('click',event=>{event.stopPropagation();viewMetadata(row,true);});folders.addEventListener('keydown',event=>event.stopPropagation());buttons.append(folders);}
    else{const folder=node('button','Open folder','quiet');folder.type='button';folder.title=row.kind==='candidate'?"Open this book's source folder in File Explorer.":"Open this source file's folder in File Explorer.";folder.setAttribute('aria-label','Open folder: '+name);folder.setAttribute('aria-describedby','folder-help');folder.disabled=!recordIdentity(row).id;const status=node('span','','folder-message');status.setAttribute('role','status');folderState(row,folder,status);folder.addEventListener('click',event=>{event.stopPropagation();select(row,selectedPath!==row.path);openFolder(row,folder,status);});folder.addEventListener('keydown',event=>event.stopPropagation());buttons.append(folder,status);}
    if(row.kind==='candidate' && deleteOffer(row))buildDeleteButton(row,buttons);  // ruling 23: last, on its own line
    else if(row.kind==='candidate' && copyOffer(row))buildDeleteButton(row,buttons,'copy');  // ruling 25: the same slot
    actions.append(buttons);
    if(askOf(row) && askRows.get(row.id)){const entry=askRows.get(row.id);entry.block=node('p','','field-help block-why');entry.block.id='block-why-'+row.id;entry.block.hidden=true;actions.append(entry.block);updateAskRow(entry);}
    tr.append(actions);
    tr.addEventListener('click',()=>select(row,selectedPath!==row.path));
    tr.addEventListener('keydown',event=>{if(event.key==='Enter' || event.key===' '){event.preventDefault();select(row,selectedPath!==row.path);}});
    body.append(tr);
  }
  const selected=rows.find(row=>row.path===selectedPath);
  if (selected) select(selected,false);
  else if(!selectedRow){$('details').hidden=true;}
  if(focusPlan && Date.now()>focusPlan.until)focusPlan=null;
  if(focusPlan && (listFocus || !document.activeElement || document.activeElement===document.body))leaveTo(focusPlan.next);
  $('empty').hidden=rows.length>0;
  const unit=view==='candidates'?'candidates':'files';
  const label=filterOptions[view].find(item=>item[0]===filters[view])[1];
  // Judy's copy check (must-fix): not running, the books are waiting, as the strip line above says.
  const waiting=stillChecking(),running=state?.automatic_processing?.state==='Running';
  const nothing=attentionList && !search?(!waiting?'Nothing needs your attention.':running?`Nothing needs your attention yet. Still checking ${plural(waiting,'book','books')}.`:
    `Nothing needs your attention yet. ${plural(waiting,'book is','books are')} waiting to be checked.`):'';
  const emptyText=view==='candidates' && filters[view]==='converted' && !search && totalRows===0?'No audiobooks are ready yet. Automatic processing progress appears above; choose All candidates or Held to inspect unfinished books.':
    view==='candidates' && filters[view]==='restarted' && !search?'No books are waiting after Start over. Books you start over appear here until automatic processing queues them.':nothing || `No ${unit} match these filters · ${label}.`;
  $('inventory').removeAttribute?.('aria-busy');
  $('empty').textContent=emptyText;
  $('page').textContent=rows.length ? `Showing ${offset+1}–${offset+rows.length} of ${totalRows} ${unit} · ${label}` : nothing || `No ${unit} match these filters · ${label}.`;
  $('previous').disabled=offset===0;
  $('next').disabled=offset+rows.length>=totalRows;
  batchCounts();renderRestartSummary();
}
let restartNoticeSeen=null;
function acknowledgeRestart(current){
  if(current.restart_context!==true || current.application!=='Books Arranger' || current.port!==5210 || !Number.isSafeInteger(current.pid) || current.pid<=0 || !/^[a-f0-9]{32}$/.test(current.instance || '') || current.instance===restartNoticeSeen)return;
  restartNoticeSeen=current.instance;
  const automatic=current.automatic_processing;
  if(automatic?.state==='Paused')message('Books Arranger restarted. Automatic processing is paused.');
  else if(automatic?.state==='Idle' && !automatic.run_id)message('Books Arranger restarted.');
}

// One book-list request; it paints itself if it is still the newest request for the list on screen.
function acknowledgeReacquireArchives(page){
  if(!selectedRow || !Array.isArray(page.reacquire_archives) || !page.reacquire_archives.includes(selectedRow.id))return;
  const focused=$('details').contains?.(document.activeElement),notice='Damaged originals confirmed removed. Scan the replacement for fresh research.';
  if(heldRow?.row?.id===selectedRow.id)heldRow=null;
  selectedRow=null;selectedPath=null;reviewRow=null;dirty=false;trackDirty=false;
  for(const id of ['manual-review','candidate-details','candidate-approval','automatic-result','metadata-inspector','audiobook-output'])$(id).hidden=true;
  $('details').hidden=false;$('details-heading').textContent='Source entry cleared';$('reason').textContent=notice;$('proposed').textContent='Historical jobs and evidence are kept.';
  controls();message(notice);if(focused)$('details-heading').focus?.({preventScroll:true});
}
function loadList(context,library,requestView,requestFilter,requestOffset,requestSearch,epoch,forceRender){
  const ticket=++listTicket;listPending=context;
  if(context!==paintedContext)showListLoading();
  const groupQuery=requestView==='candidates' && requestFilter==='output_attention' && attentionGroup!=='all'?`&group=${attentionGroup}`:'';
  const sentAt=Date.now();
  return request(`/api/inventory?library=${encodeURIComponent(library)}&offset=${requestOffset}&search=${encodeURIComponent(requestSearch)}&view=${requestView}&status=${requestFilter}${groupQuery}`).then(page=>{
    // A book list requested before Retry was answered predates it and would repaint the old state.
    if (ended || ticket!==listTicket || $('library').value!==library || context!==listContext() || epoch!==retryEpoch) return false;
    acknowledgeReacquireArchives(page);
    rows=page.rows.map(row=>requestView==='candidates'?({...row,path:row.id,kind:'candidate',library}):({...row,library}));totalRows=page.total ?? (requestOffset+rows.length);listGeneration++;pruneQueueNotes();
    if(requestView==='candidates')rows=withoutDeleted(rows,sentAt);  // Judy 0.22.2 section 5
    restartCounts=requestFilter==='restarted' && page.restart_counts && typeof page.restart_counts==='object'?page.restart_counts:null;
    if(heldRow && (heldRow.context!==context || Date.now()>heldRow.until))heldRow=null;
    else if(heldRow && !rows.some(item=>item.path===heldRow.path)){rows.splice(Math.min(heldRow.index,rows.length),0,heldRow.row);if(!heldRow.rechecked)recheckHeld(heldRow);}
    noteLeavers(sentAt);
    const changed=context!==paintedContext;paintedContext=context;renderRows(forceRender || changed);
    return true;
  }).finally(()=>{if(ticket===listTicket)listPending='';});
}
// The pressed book left this list (its child was admitted, or the worker refused it). Re-read it once, so the row held
// in place shows what is true now, never a stale "Queued" (RefusedRetry spec section 3, "While on screen").
async function recheckHeld(held){
  held.rechecked=true;
  try{
    const page=await request(`/api/inventory?library=Audiobooks&offset=0&search=${encodeURIComponent(held.row.title_clue || '')}&view=candidates&status=all`);
    const fresh=(page.rows || []).find(item=>item.id===held.row.id);
    if(!fresh || heldRow!==held || ended)return;
    const row={...fresh,path:fresh.id,kind:'candidate',library:held.row.library};held.row=row;
    if(rows.some(item=>item.path===row.path)){rows=rows.map(item=>item.path===row.path?row:item);renderRows(false);}
  }catch(error){}  // the held row keeps its last known state until the list changes
}
async function refresh(force=false) {
  if (ended) return false;
  const sequence=++refreshSequence;
  const library=$('library').value,context=listContext(),requestView=view,requestFilter=filters[view],requestOffset=offset,requestSearch=search,epoch=retryEpoch;
  // A list change (filter, group, page, search, view, library) shows its loading text and asks for its list at
  // once, beside the status read: neither waits for /api/state (v0.16.7 QA: up to 11 s behind a slow status).
  const early=force && booksOnScreen()?loadList(context,library,requestView,requestFilter,requestOffset,requestSearch,epoch,true):null;
  early?.catch(()=>{});
  const stateSent=Date.now();
  const current=await request(`/api/state?library=${encodeURIComponent(library)}`);
  deletedCounts(current,stateSent);  // Judy 0.22.2 section 5: a status from before a delete still counts that book
  observeLoad(current);  // any answer counts, whatever happens to it below (Judy 3.4)
  if (ended || sequence!==refreshSequence || $('library').value!==library || context!==listContext() || epoch!==retryEpoch) return false;
  const libraryWasMissing=!state || !partReady('library');
  state=current;
  syncQueue(current);  // queued Retry, Repair and Delete book, and their outcomes (0.22.1)
  // Each part paints only once it has arrived; until then its placeholder stays (Judy 3.5).
  if(partReady('jobs')){renderJobs();renderAutomatic();renewManualDraft();}
  renderVersion();
  if(libraryWasMissing && partReady('library'))viewControls();
  if(partReady('library')){const sourceRoots=Array.isArray(state.source_roots)&&state.source_roots.length?state.source_roots:[state.root];$('root').textContent=state.library==='Audiobooks'?sourceRoots.map((root,i)=>`Source ${i+1}: ${root}`).concat(state.audiobook_output_root?[`Output: ${state.audiobook_output_root}`]:[]).join('\n'):`Source: ${state.root}`;}
  if(!partReady('status') || !state.status){loadPlaceholders();controls();return true;}
  const status=state.status;
  const activity=state.stopping ? 'Stopping…' : state.active_library ? `Scanning ${state.active_library}` : status.state;
  const scanLabel=!state.active_library && status.state==='failed'?'Last scan':'Discovery';
  const statusText=`${scanLabel}: ${activity} · Files cataloged ${status.count} · Files checked this scan ${status.checked} · Metadata reused this scan ${status.reused} · Pending tasks ${status.pending} · Read failures this scan ${status.errors} · Files with read errors ${status.unresolved_errors ?? status.errors}`;
  receivedStatus.set(library,statusText);receivedAt.set(library,Date.now());$('status').textContent=statusText;if(busyShown)renderBusy();  // one format while the notice shows
  $('error-shortcut').hidden=!(status.unresolved_errors ?? status.errors);$('error-shortcut').textContent=`Read errors · ${status.unresolved_errors ?? status.errors}`;
  $('scan-issues').hidden=!status.scan_issues?.length;$('scan-issues-text').textContent=(status.scan_issues || []).map(issue=>`${issue.path}\n${issue.error}\n${issue.time}`).join('\n\n');
  $('current').textContent=status.current || 'Choose a file to inspect existing metadata and its sorting preview.';
  if (form.elements.namedItem('genre').options.length===1) {
    for (const genre of state.genres) { const option=document.createElement('option');option.value=genre;option.textContent=genre;form.elements.namedItem('genre').append(option); }
  }
  loadPlaceholders();controls();
  if(!booksOnScreen())return true;  // no list read before the books part: its placeholder stays (Judy 3.5)
  const key=JSON.stringify([library,view,filters[view],offset,search,status.count,status.checked,status.state,status.unresolved_errors]);
  if (early) {
    if(!await early)return false;
    lastKey=key;
  } else if (view==='candidates' || key!==lastKey) {
    // The book list is slow on a large catalog: a request already on its way for this exact list paints
    // itself, so polls never restart it; only a newer request for the list replaces it.
    if(listPending===context){acknowledgeRestart(current);return true;}
    if(!await loadList(context,library,requestView,requestFilter,requestOffset,requestSearch,epoch,false))return false;
    lastKey=key;
  }
  // Settling (3.7): every part has arrived and the first list is on screen; one render pass makes it all live.
  if(LS && loadingActive && LS.loaded(current) && paintedContext===context)settleLoad(current.loading?.took_ms);
  acknowledgeRestart(current);
  return true;
}
async function poll() {
  if (ended) return;
  if (!polling) {
    polling=true;
    const library=$('library').value,sequence=refreshSequence+1;
    try { if(await refresh())clearConnectionNotice(); }
    catch(error) {
      if(sequence===refreshSequence && library===$('library').value){
        // v0.16.8: a busy engine answered 503 "still updating" under load and the page declared the server
        // unavailable, disabling Retry. A reply means the server is there: retry on the next poll.
        if(error.httpStatus)loadHeard();  // any reply is the engine answering (Judy 3.4)
        if(error.httpStatus!==503)refreshFailed(error);
      }
    }
    finally { polling=false; }
  }
  if (!ended) timer=setTimeout(poll,800);
}
$('start').addEventListener('click',later('toolbar:start','scan_start',()=>action('/api/scan/start',{library:$('library').value})));
$('resume').addEventListener('click',later('toolbar:resume','scan_resume',()=>action('/api/scan/resume',{library:$('library').value})));
$('stop').addEventListener('click',later('toolbar:stop','scan_stop',()=>action('/api/scan/stop',{library:state.active_library})));
let searchTimer=null;
function listContext(){return JSON.stringify([$('library').value,view,filters[view],offset,search,$('search').value,filters[view]==='output_attention'?attentionGroup:'all']);}
// While a different list is on its way, the old rows are not shown as the new filter's result.
function showListLoading(){
  const label=filterOptions[view].find(item=>item[0]===filters[view])?.[1] || '';
  $('inventory').replaceChildren();rowRetries.clear();askRows.clear();deleteButtons.clear();$('inventory').setAttribute?.('aria-busy','true');
  const text=`Loading ${label}${filters[view]==='output_attention' && attentionGroup!=='all'?' · '+attentionLabels[attentionGroup]:''}…`;
  $('empty').textContent=text;$('empty').hidden=false;$('page').textContent=text;$('previous').disabled=true;$('next').disabled=true;
}
function cancelSearchRefresh(){if(searchTimer!==null)clearTimeout(searchTimer);searchTimer=null;}
function updateList(resetPage=true){
  cancelSearchRefresh();search=$('search').value;if(resetPage)offset=0;lastKey=null;
  const context=listContext(),generation=refreshSequence+1;
  return refresh(true).catch(error=>{if(generation===refreshSequence && context===listContext())message(error.message);});
}
$('library').addEventListener('change',()=>{cancelSearchRefresh();viewControls();return updateList();});
$('view').addEventListener('change',()=>{cancelSearchRefresh();view=$('view').value;viewControls();return updateList();});
function resetStrip(){retryAllRun=null;retryAllConfirm=null;stripNote='';stripShow=null;dropQueueStrip();for(const id of [...queueNotes.keys()])dropQueueNote(id);}
$('filter').addEventListener('change',()=>{filters[view]=$('filter').value;attentionGroup='all';resetStrip();restartCounts=null;$('release-selected-status').textContent='';return updateList();});
$('clear-filters').addEventListener('click',()=>{$('search').value='';filters[view]='all';attentionGroup='all';resetStrip();viewControls();return updateList();});
$('error-shortcut').addEventListener('click',()=>{$('search').value='';filters[view]='errors';viewControls();return updateList();});
$('search').addEventListener('input',()=>{cancelSearchRefresh();++refreshSequence;if(!$('search').value)return updateList();searchTimer=setTimeout(()=>{searchTimer=null;updateList();},250);});
$('search-form').addEventListener('submit',event=>{event.preventDefault();return updateList();});
$('previous').addEventListener('click',()=>{offset=Math.max(0,offset-100);return updateList(false);});
$('next').addEventListener('click',()=>{offset+=100;return updateList(false);});
form.addEventListener('input',event=>{metaSaveResult=null;panelDiscarded=null;noteOnlyDirty=false;editSeq++;if(!dirty)reviewRow=selectedRow;dirty=true;manualMetadataTouched=true;syncManualDraft();routingControls();queueRoutingPreview();updateMetadataChoiceControls();controls();$('review-note').textContent='Unsaved local review.';});
// "Save preview metadata" (2026-10-26, the diagnosis of "Save does nothing": the save succeeded and the page never said
// so). The press shows Saving… at once and keeps its focus (aria-disabled); "Saved." lands with the answer, the list reload
// follows outside the save's own error path; a press is never dropped: during a save the newest values are saved next,
// and while another press of this page runs the save waits for it (ruling 35). Edits typed meanwhile stay unsaved. A book
// a background update moved on (Candidate changed) keeps his values and is saved again on its new revision, once.
const SAVE_METADATA_FACE='Save preview metadata',SAVE_METADATA_FILE_TIP='Save these values as a draft and a metadata source for this book.',SAVE_METADATA_BOOK_TIP="Save these values as a draft and a metadata source for this book. Names are edited on the book's row.";
function saveMetadataTip(){return namesLocked()?SAVE_METADATA_BOOK_TIP:SAVE_METADATA_FILE_TIP;}
function metadataReview(){
  // Ruling 40 (Senua's 0.22.3 review, M3): a book's six name fields are hidden and may hold names from before a row Save;
  // they are sent as the saved draft's values, and the request says the names are the row's (names_row_only).
  const locked=namesLocked(),saved=(reviewRow || selectedRow)?.review || {};
  const review={};for(const field of fields)review[field]=locked && NAME_INPUTS.includes(field)?String(saved[field] ?? '').trim():form.elements.namedItem(field).value.trim();
  review.multi_author=form.elements.namedItem('multi_author').checked;
  review.anthology=['audiobook','candidate'].includes(selectedRow.kind) && (locked?saved.anthology===true:form.elements.namedItem('anthology').checked);
  if(!['audiobook','candidate'].includes(selectedRow.kind)){review.canonical_author='';review.narrator='';}
  return review;
}
function renderMetaSave(){
  const button=$('save-metadata');if(!button)return;const pending=!!metaSave || metaQueued;
  const face=pending?'Saving…':SAVE_METADATA_FACE,tip=pending?ladderNote('Saving these values…',metaSave?.at):saveMetadataTip();
  // 2.5: the line beside the button counts while it saves, then names what was saved, or why not.
  const note=metaSave?clockNote('Saving…',metaSave.at):metaQueued?'Saving after the current operation finishes…':metaSaveResult?.text;
  if(note && $('review-note') && $('review-note').textContent!==note)$('review-note').textContent=note;
  if(button.textContent!==face)button.textContent=face;if(button.title!==tip)button.title=tip;
  if(pending)button.setAttribute?.('aria-disabled','true');else button.removeAttribute?.('aria-disabled');
}
async function sendMetadata(row,review){
  if(row.kind!=='candidate'){await request('/api/review',{library:selectedLibrary || $('library').value,path:row.path,size:row.size,modified:row.modified,review});return {row:null};}
  for(let attempt=0;;attempt++){
    try{return {...await request('/api/candidate/review',{library:selectedLibrary,id:row.id,revision:row.revision,review,approve:false,...reviewContext(row),...(namesLocked()?{names_row_only:true}:{})}),sent:row};}
    catch(error){
      const fresh=error.body?.row;
      if(attempt===0 && error.body?.code==='changed' && fresh && fresh.id===row.id){row={...fresh,path:fresh.id,kind:'candidate',library:selectedLibrary};reviewRow=row;continue;}
      throw error;
    }
  }
}
async function saveMetadata(){
  if(!selectedRow)return;
  if(ended || recoveryDisconnected){message('Local server unavailable. Nothing was saved.');return;}
  if(metaSave){metaAgain=true;return;}  // never dropped: the newest values are saved when this save lands
  if(busy){metaQueued=true;renderMetaSave();setText('review-note','Saving after the current operation finishes…');return;}
  metaQueued=false;
  const row=reviewRow || selectedRow,review=metadataReview(),seq=editSeq,before=row.review || {};
  metaSaveResult=null;metaSave={at:Date.now(),seq,id:row.id};busy=true;renderMetaSave();controls();message();setText('review-note','Saving…');
  let saved=null,failure=null;
  try{saved=await sendMetadata(row,review);}
  catch(error){failure=error;}
  finally{metaSave=null;busy=false;}
  if(saved){
    const current=editSeq===seq;
    if(saved.row){
      const fresh={...saved.row,path:saved.row.id,kind:'candidate',library:selectedLibrary};
      if(trackDraft?.id===fresh.id && trackDraft.revision===saved.sent.revision)trackDraft.revision=fresh.revision;
      reviewRow=fresh;  // a later save goes to the book's new revision
      if(selectedRow?.id===fresh.id)select(fresh,false);
    }
    if(current){dirty=false;manualMetadataTouched=false;syncManualDraft();metaSaveResult={text:savedFieldsLine(before,review)};setText('review-note',metaSaveResult.text);}
    else setText('review-note','Unsaved local review.');  // typed while it saved: those edits are not saved yet
  }else{
    metaSaveResult={text:failure?.httpStatus?'Not saved. '+serverSentence(failure,'Nothing was changed.'):'Not saved. '+lostLine(),warn:true};setText('review-note',metaSaveResult.text);
    if(!failure?.httpStatus)refreshFailed(failure);
  }
  renderMetaSave();controls();
  if(metaAgain){metaAgain=false;if(dirty)return saveMetadata();}
  if(saved)refresh(true).catch(()=>{});  // the list follows; its failure is not the save's
}
form.addEventListener('submit',event=>{event.preventDefault();return saveMetadata();});
$('approve-candidate').addEventListener('click',later('toolbar:approve-candidate','approve_candidate',async()=>{const row=reviewRow || selectedRow;if(!row || row.kind!=='candidate' || dirty || busy || ended)return;busy=true;controls();try{const result=await request('/api/candidate/review',{library:selectedLibrary,id:row.id,revision:row.revision,review:row.review,approve:true,...reviewContext()});select({...result.row,path:result.row.id,kind:'candidate',library:selectedLibrary},true);await refresh(true);message('Candidate metadata approved. Tracks still require review; source files unchanged.');}catch(error){message(error.message);}finally{busy=false;controls();}}));
$('shutdown').addEventListener('click',later('toolbar:shutdown','shutdown',async()=>{
  if(busy || ended)return;busy=true;controls();message();
  try{await request('/api/shutdown',{});ended=true;clearConnectionNotice();clearTimeout(timer);$('status').textContent='Server stopping. Saved catalog and pending scans remain available on the next launch.';message('You can close this browser tab.');}
  catch(error){message(error.message);}
  finally{busy=false;controls();}
}));
function node(tag,text='',className=''){const element=document.createElement(tag);element.textContent=text;if(className)element.className=className;return element;}
function recordIdentity(row){return {library:row.library || $('library').value,view:row.kind==='candidate'?'candidates':'files',id:row.kind==='candidate'?row.id:row.record_id};}
function folderKey(row,kind='source',directory=null){return JSON.stringify([recordIdentity(row),kind,directory]);}
function folderState(row,button,status,kind='source',directory=null){const key=folderKey(row,kind,directory);button.disabled=ended || !recordIdentity(row).id || pendingFolders.has(key);status.textContent=pendingFolders.has(key)?'Opening folder…':folderMessages.get(key) || '';}
async function openFolder(row,button,status,folderKind='source',directoryId=null){const key=folderKey(row,folderKind,directoryId);if(ended || button.disabled || pendingFolders.has(key))return;pendingFolders.add(key);folderMessages.delete(key);folderState(row,button,status,folderKind,directoryId);try{const payload={...recordIdentity(row),folder_kind:folderKind};if(directoryId)payload.directory_id=directoryId;await request('/api/open-folder',payload);folderMessages.delete(key);}catch(error){folderMessages.set(key,error.message || 'Folder unavailable. Connect the library drive and try again.');}finally{pendingFolders.delete(key);folderState(row,button,status,folderKind,directoryId);}}
async function viewMetadata(row,showFolders=false){if(ended)return;const same=selectedPath===row.path;select(row,!same);const identity=recordIdentity(row),sequence=++inspectSequence;inspectorIdentity=identity;$('metadata-inspector').hidden=false;$('details-heading').textContent=row.kind==='candidate'?'Book metadata':'File metadata';$('details-heading').scrollIntoView?.({block:'start',behavior:'auto'});$('details-heading').focus?.({preventScroll:true});$('inspect-status').textContent='Reading metadata and artwork…';try{const result=await request('/api/inspect',identity);if(sequence!==inspectSequence || selectedPath!==row.path || ended)return;if(!result.inspector || !Array.isArray(result.inspector.sections))throw Error('Metadata inspection unavailable');renderInspector(result.inspector,row,sequence);if(showFolders)$('source-folders').open=true;$('inspect-status').textContent='';}catch(error){if(sequence===inspectSequence)$('inspect-status').textContent=error.message;}}
function inspectedCandidateStatus(section,inspector,row){
  if(section.kind==='created' || section.kind==='snapshot')return section.status || '';
  // The inspection is newer evidence than the selected inventory row.
  if(/error|failed|attention|changed/i.test(section.status || ''))return section.status;
  return candidateStatus({...row,...(typeof inspector.audiobook_ready==='boolean'?{audiobook_ready:inspector.audiobook_ready}:{}),...(Object.hasOwn(inspector,'duplicate_review')?{duplicate_review:inspector.duplicate_review}:{})});
}
function renderInspector(inspector,row,sequence){closeRecoveryDialog(false);recoveryPanel=null;for(const url of inspectorObjects)URL.revokeObjectURL(url);inspectorObjects.length=0;$('inspector-sections').replaceChildren();$('folder-list').replaceChildren();if(!inspector || !Array.isArray(inspector.sections)){ $('inspect-status').textContent='Metadata inspection unavailable';return;}
  const provenanceSection=inspector.sections.find(section=>section.kind==='created') || inspector.sections.find(section=>section.kind==='approved') || inspector.sections[0];
  for(const section of inspector.sections){const panel=node('section','','inspector-section');panel.append(node('h2',section.heading || 'Source metadata'));if(section.status)panel.append(node('p',row.kind==='candidate' && ['approved','created','snapshot'].includes(section.kind)?inspectedCandidateStatus(section,inspector,row):section.status));if(section.kind==='approved' && !inspector.sections.some(item=>item.kind==='created') && !(section.status || '').includes('Not written to a file'))panel.append(node('p','Not written to a file'));if(section.kind==='snapshot' && !(section.status || '').includes('Saved output snapshot'))panel.append(node('p','Saved output snapshot'));
    const location=node('div','','inspector-location');if(section.path)location.append(node('p',section.path,'path'));if(section.kind==='created' && inspector.output_folder_available){const button=node('button','Open output folder','quiet'),status=node('span','','folder-message');button.type='button';button.title='Open the folder containing this created audiobook.';button.setAttribute('aria-label','Open output folder: '+section.path);button.setAttribute('aria-describedby','folder-help');status.setAttribute('role','status');folderState(row,button,status,'output');button.addEventListener('click',()=>openFolder(row,button,status,'output'));location.append(button,status);}panel.append(location);
    const content=node('div','','inspector-content'),facts=node('dl');for(const fact of section.facts || []){if(fact.value===null || fact.value===undefined || fact.value==='')continue;facts.append(node('dt',fact.label),node('dd',typeof fact.value==='string'?fact.value:JSON.stringify(fact.value)));}if(row.kind==='candidate' && section===provenanceSection){const currentFacts={...row,...(inspector.metadata_facts?{metadata_facts:inspector.metadata_facts}:{}),...(Object.hasOwn(inspector,'duplicate_review')?{duplicate_review:inspector.duplicate_review}:{})};for(const [label,value] of Object.entries({...provenanceFacts(currentFacts),...recordingFacts(currentFacts)}))facts.append(node('dt',label),node('dd',String(value)));}content.append(facts);if(section.cover){const artwork=node('div','','inspector-artwork');content.append(artwork);inspectorCover(section.cover,artwork,sequence);}panel.append(content);
    if(section.kind==='created' && row.cleanup?.recovery)panel.append(makeRecoveryPanel());
    if(section.member_values?.length){const mixed=node('details');mixed.append(node('summary','Different values across source tracks'));for(const value of section.member_values)mixed.append(node('p',`${value.path}\n${value.field}: ${typeof value.value==='string'?value.value:JSON.stringify(value.value)}`,'path'));panel.append(mixed);}
    if(section.raw_tags){const raw=node('details');const summary=node('summary','All source tags');summary.title='Inspect all original source tags without changing them.';summary.setAttribute('aria-describedby','inspect-help');raw.append(summary,node('pre',JSON.stringify(section.raw_tags,null,2)));panel.append(raw);}
    if(section.alternatives?.length){const alternatives=node('details');const summary=node('summary','Other source artwork');summary.title='Inspect alternative artwork from source files.';summary.setAttribute('aria-describedby','inspect-help');alternatives.append(summary);for(const cover of section.alternatives){const holder=node('div','','inspector-artwork');alternatives.append(holder);inspectorCover(cover,holder,sequence);}panel.append(alternatives);}$('inspector-sections').append(panel);
  }
  const directories=inspector.source_directories || [];$('source-folders').hidden=!directories.length;for(const directory of directories){const line=node('div','','source-directory');line.append(node('p',directory.path,'path'));const button=node('button','Open folder','quiet'),status=node('span','','folder-message');button.type='button';button.title="Open this source file's folder in File Explorer.";button.setAttribute('aria-label','Open folder: '+directory.path);button.setAttribute('aria-describedby','folder-help');status.setAttribute('role','status');folderState(row,button,status,'source',directory.id);button.addEventListener('click',()=>openFolder(row,button,status,'source',directory.id));line.append(button,status);$('folder-list').append(line);}
}
async function inspectorCover(cover,holder,sequence){const caption=node('p',cover.label || 'Source artwork'),status=node('p',cover.error || cover.status || 'Loading artwork…');holder.append(caption,status);if(!cover.thumbnail_url){status.textContent=cover.error || cover.status || 'Cover not found';return;}try{const url=new URL(cover.thumbnail_url,location.origin);if(url.origin!==location.origin)throw Error('Cover preview unavailable');const response=await fetch(url.href,{headers:{'X-Books-Token':token},credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error('Cover could not be read');const blob=await response.blob();if(sequence!==inspectSequence)return;const object=URL.createObjectURL(blob);inspectorObjects.push(object);const image=node('img');image.alt=cover.label || 'Source artwork';image.src=object;image.addEventListener('error',()=>{image.hidden=true;status.textContent='Cover could not be read';});holder.append(image);status.textContent=cover.status || '';}catch(error){if(sequence===inspectSequence)status.textContent=cover.error || error.message || 'Cover preview unavailable';}}
function sourceLink(url,label){const link=node('a',label);try{const parsed=new URL(url,location.origin);if(!['http:','https:'].includes(parsed.protocol))throw Error();link.href=parsed.href;link.target='_blank';link.rel='noopener noreferrer';}catch{link.removeAttribute('href');link.textContent=label+' (source unavailable)';}return link;}
// Ruling 36 (Sergei 2026-10-26): no evidence field; a save keeps whatever note the catalog already holds (unused).
function keptNote(row){const note=row?.review_context?.manual_note;return typeof note==='string'?note:'';}
function reviewContext(row=reviewRow || selectedRow){return {manual_note:keptNote(row),proposal_id:proposalId,cover_id:coverId,actor:'user'};}
function readyForQueue(row){return !!row.creation?.can_create && row.creation?.status!=='Single audiobook file' && selectedBooks.get(row.id)===row.revision && !(selectedRow?.id===row.id && (dirty || trackDirty));}
function batchCounts(){const visible=rows.filter(row=>row.kind==='candidate'),selected=visible.filter(row=>selectedBooks.has(row.id)),ready=selected.filter(row=>readyForQueue(row));const retryItems=attentionSelection()?retrySelectable():[],retryable=retryItems.length,conditional=conditionalRetries(retryItems),waiting=selected.filter(row=>readmissionOf(row)?.state==='queued').length,queuedSel=selected.filter(row=>queuedFor(row) || queueRunning(row)).length,leftOut=selected.length-retryable-waiting-queuedSel,already=queuedSel?` · ${queuedSel} already queued`:'';const releasable=releaseSelection()?releaseSelectable().length:0;
  // Let the app handle selected (O14): in Started over the selection is counted against it; in Held it is added to the usual line.
  const approvable=bulkChip()?approveSelectable().items.length:0;
  $('batch-count').textContent=bulkChip()?`${selected.length} selected · ${approvable} can be approved as is`+already+(selected.length-approvable-queuedSel>0?` · ${selected.length-approvable-queuedSel} left out`:''):
    needsChip()?`${selected.length} selected`:attentionSelection()?`${selected.length} selected`+(waiting?` · ${waiting} already waiting for retry checks`:String())+(retryable>conditional || !conditional?` · ${retryable-conditional} new retries available`:'')+(conditional?` · ${conditional} can be checked again`:'')+already+(leftOut>0?` · ${leftOut} left out`:''):
    filters[view]==='restarted' && view==='candidates'?`${selected.length} selected · ${releasable} can be handled by the app`+(selected.length-releasable>0?` · ${selected.length-releasable} left out`:''):
    `${selected.length} selected · ${ready.length} ready · ${selected.length-ready.length} need review`+(releaseSelection() && releasable>0?` · ${releasable} can be handled by the app`:'');const takes=pageSelectable(),all=takes.length>0 && takes.every(row=>selectedBooks.has(row.id));$('select-page').checked=all;$('select-page').indeterminate=selected.length>0 && !all;controls();}
function renderJobs(){
  if(loadingActive && !(state && partReady('jobs')))return loadPlaceholders();  // m-7: its placeholders until the part comes (3.5)
  const jobs=state?.audiobook_jobs;$('audio-jobs').hidden=!jobs;if(!jobs)return;
  const text=(id,value)=>{if($(id).textContent!==value)$(id).textContent=value;};
  const counts=Number.isInteger(jobs.converted_total)&&Number.isInteger(jobs.approved_total)&&jobs.converted_total>=0&&jobs.approved_total>=jobs.converted_total;
  const wholeCounts=Number.isInteger(jobs.candidate_total)&&Number.isInteger(jobs.not_approved_total)&&jobs.candidate_total>=0&&jobs.not_approved_total>=0&&jobs.not_approved_total<=jobs.candidate_total;text('book-candidate-counts',wholeCounts?`${jobs.candidate_total} book candidates found · ${jobs.not_approved_total} not approved`:'Book candidate totals unavailable');
  text('jobs-status',(recoveryDisconnected || ended || busyShown?'Last confirmed — ':'')+[counts?`${jobs.converted_total} converted out of ${jobs.approved_total} approved books`:'Approved book progress unavailable',jobs.state,`${jobs.queued || 0} queued`,jobs.retry_checks?.waiting?`${jobs.retry_checks.waiting} waiting for retry checks`:'',`${attentionTotal(jobs)} need attention`].filter(Boolean).join(' · '));
  renderActivities(Array.isArray(state.activities)?state.activities:[],jobs);
  const cleanup=jobs.cleanup_active===true;
  $('pause-jobs').title=cleanup?'Pause audiobook work. Source cleanup finishes the current file before stopping.':'Stop the current audiobook operation and save pending books. Finished outputs stay in place.';
  $('resume-jobs').title=cleanup?'Continue pending audiobook work. Paused cleanup resumes without recreating the audiobook.':'Continue pending books. An interrupted book restarts; completed outputs are not recreated.';
  const help=cleanup?'Pausing source cleanup finishes the current file. Resume continues its saved progress. Scanning has separate stop and resume controls. An interrupted conversion restarts; completed outputs stay in place.':'An interrupted conversion restarts; completed outputs stay in place. Scanning has separate stop and resume controls.';
  text('jobs-help',help+(Array.isArray(jobs.folder_cleanup_notes)&&jobs.folder_cleanup_notes.length?' Empty source folders retained: safe automatic removal is unavailable on this drive.':''));
}
// Progress rows (ProgressRows spec): one row per running activity, fixed order, updated in place.
const activityOrder=['conversion','cleanup','identity','series','scan'],activityRows=new Map();let activityTimer=null;
const conversionSteps={'checking sources':'Checking source files',preparing:'Copying and checking source files','source copies':'Checking source copies','checking audio':'Checking source audio','matching format':'Choosing the audio format',normalizing:'Normalizing audio','joined audio':'Checking joined audio',creating:'Encoding audio',encoding:'Encoding audio',checking:'Verifying audiobook',copying:'Copying audiobook to the library',publishing:'Copying audiobook to the library'};
const cleanupSteps={originals:'Removing original files','recovery copies':'Checking recovery copies',temporary:'Removing temporary recovery and working files',folders:'Removing empty source folders','verifying replacement':'Verifying replacement audiobook','retiring former outputs':'Removing former audiobook versions','former outputs':'Removing former audiobook versions'};
function activityLabel(row){
  if(row.kind==='conversion')return ({attention:'Audiobook on hold',paused:'Audiobook paused',pausing:'Pausing audiobook'})[row.state] || 'Converting';
  if(row.kind==='cleanup')return ['originals','recovery copies'].includes(row.step)?'Removing originals':'Cleaning up';
  if(row.kind==='identity')return 'Checking finished books';
  if(row.kind==='series')return 'Updating series';
  return row.step==='researching'?'Researching books':'Scanning files';
}
function activityStep(row,finishing){
  let step;
  if(row.kind==='conversion'){const name=finishing && row.step==='encoding'?'Finalizing conversion':conversionSteps[row.step] || 'Working';step=Number.isInteger(row.step_index) && Number.isInteger(row.step_count)?`Step ${row.step_index} of ${row.step_count} - ${name}`:name;}
  else if(row.kind==='cleanup')step=cleanupSteps[row.step] || 'Working';
  else if(row.kind==='identity')step='Checking identity';
  else if(row.kind==='series')step=row.step==='series updating'?'Writing the series into the audiobook':'Looking up the series';
  else step=typeof row.step_text==='string' && row.step_text?row.step_text:'Working';
  // A held row is not progressing (v0.16.8): it says so, with no bar, count or clock.
  // A long or multi-line reason is technical text: it is never printed here (Judy 2026-10-24, section 4.6); the held book
  // is listed under Output needs attention, so the line points there (0.22.0 review A6).
  if(row.state==='attention')return 'On hold — '+(typeof row.reason==='string' && row.reason?(row.reason.length<=80 && !/[\r\n]/.test(row.reason)?row.reason:'see Needs attention'):step);
  if(row.state==='paused')return 'Paused - '+step;
  if(row.state==='pausing')return 'Pausing - '+step;
  return step;
}
function clockText(seconds,withHours){seconds=Math.max(0,Math.floor(seconds));const h=Math.floor(seconds/3600),m=Math.floor(seconds%3600/60),s=String(seconds%60).padStart(2,'0');return withHours || h?`${h}:${String(m).padStart(2,'0')}:${s}`:`${m}:${s}`;}
function byteText(done,total){const units=['B','KB','MB','GB','TB'];let index=0;while(index<units.length-1 && total>=1024**(index+1))index++;const scale=1024**index,format=value=>{const scaled=value/scale;return scaled.toLocaleString(undefined,{maximumFractionDigits:scaled<10 && index?1:0,minimumFractionDigits:0});};return `${format(done)} of ${format(total)} ${units[index]}`;}
function activityDetail(row,finishing){
  if(row.indeterminate || finishing || !(row.total>0))return '';
  const done=row.done,total=row.total,whole=value=>Math.floor(value).toLocaleString();
  if(row.unit==='files' || row.unit==='books'){const noun=row.unit==='files'?'file':'book';return `${whole(done)} of ${whole(total)} ${noun}${total===1?'':'s'}`;}
  if(row.unit==='bytes')return byteText(done,total);
  if(row.unit==='seconds'){const hours=total>=3600;return `${clockText(done,hours)} of ${clockText(total,hours)} audio`;}
  return Math.floor(done/total*100)+'%';
}
function activityRow(kind){
  const item=node('li','','activity-row'),first=node('div','','activity-line activity-first'),head=node('span','','activity-head'),label=node('span','','activity-label'),subject=node('span','','activity-subject'),detail=node('span','','activity-detail'),bar=node('progress'),last=node('div','','activity-line'),step=node('span','','activity-step'),time=node('span','','activity-time');
  item.dataset.kind=kind;bar.max=100;detail.setAttribute('aria-live','off');time.setAttribute('aria-live','off');step.setAttribute('aria-live','polite');
  head.append(label,subject);first.append(head,detail);last.append(step,time);item.append(first,bar,last);
  return {item,label,subject,detail,bar,step,time,samples:[],eta:'',etaAt:0,frozen:null,key:''};
}
function writeText(element,value){if(element.textContent!==value)element.textContent=value;}
function renderActivities(list,jobs){
  const rows=list.filter(row=>row && activityOrder.includes(row.kind)).sort((a,b)=>activityOrder.indexOf(a.kind)-activityOrder.indexOf(b.kind));
  const shown=[],seen=new Set();for(const row of rows){if(seen.has(row.kind))continue;seen.add(row.kind);shown.push(row);}
  const visible=shown.slice(0,4),extra=rows.length-visible.length,holder=$('jobs-rows');
  for(const [kind,view] of activityRows)if(!visible.some(row=>row.kind===kind)){view.item.parentElement?.removeChild(view.item);activityRows.delete(kind);}
  visible.forEach((row,index)=>{
    let view=activityRows.get(row.kind);if(!view){view=activityRow(row.kind);activityRows.set(row.kind,view);}
    if(holder.children[index]!==view.item)holder.insertBefore(view.item,holder.children[index] || null);
    const key=[row.step,row.step==='researching'?'':row.subject,row.step_started_at].join('\u001f');if(view.key!==key){view.key=key;view.samples=[];view.eta='';view.etaAt=0;}
    view.row=row;updateActivity(view,Date.now());
  });
  writeText($('jobs-more'),extra>0?`+${extra} more running`:'');$('jobs-more').hidden=!(extra>0);
  const idle=visible.length?'':['Paused','paused'].includes(jobs?.state)?'Paused. Resume continues pending books.':'Nothing running';
  writeText($('jobs-idle'),idle);$('jobs-idle').hidden=!idle;
  if(visible.length && activityTimer===null && typeof setInterval==='function')activityTimer=setInterval(()=>{const now=Date.now();for(const view of activityRows.values())updateActivity(view,now);},1000);
  if(!visible.length && activityTimer!==null && typeof clearInterval==='function'){clearInterval(activityTimer);activityTimer=null;}
}
function updateActivity(view,now){
  const row=view.row,running=row.state==='running' || row.state==='pausing',measured=!row.indeterminate && row.total>0 && row.done>=0 && row.done<=row.total;
  const finishing=measured && running && row.done>=row.total,determinate=measured && !finishing;
  const held=row.state==='attention',label=activityLabel(row),subject=typeof row.subject==='string'?row.subject:'',step=activityStep(row,finishing),detail=held?'':activityDetail(row,finishing);
  view.bar.hidden=held;
  writeText(view.label,label+(subject?': ':''));writeText(view.subject,subject);view.subject.title=subject;
  writeText(view.detail,detail);writeText(view.step,step);view.step.title=step;
  view.item.classList.toggle('paused',row.state==='paused');view.item.classList.toggle('attention',row.state==='attention');
  const fraction=typeof row.fraction==='number' && row.fraction>=0 && row.fraction<=1?row.fraction:row.done/row.total;
  if(determinate){const value=Math.min(99,Math.floor(fraction*100));if(view.bar.value!==value)view.bar.value=value;}
  else if(view.bar.hasAttribute?.('value')!==false)view.bar.removeAttribute('value');
  view.bar.setAttribute('aria-label',label+(subject?': '+subject:''));view.bar.setAttribute('aria-valuetext',[step,detail].filter(Boolean).join(', '));
  // Elapsed counts the current step from its start; it freezes while paused or needing attention.
  const started=Number.isFinite(row.step_started_at)?row.step_started_at:now;
  if(running)view.frozen=null;else if(view.frozen===null)view.frozen=now;
  const elapsed=Math.max(0,((view.frozen ?? now)-started)/1000);
  // ETA from the measured rate over the last 30 s (samples only when the data changed), once trustworthy.
  if(determinate && running && (!view.samples.length || view.samples[view.samples.length-1][1]!==fraction))view.samples.push([now,fraction]);
  while(view.samples.length>2 && now-view.samples[1][0]>30000)view.samples.shift();
  if(!(determinate && running) || elapsed<10 || fraction<0.05)view.eta='';
  else if(now-view.etaAt>=5000 && view.samples.length>1){
    const [t0,d0]=view.samples[0],[t1,d1]=view.samples[view.samples.length-1],rate=(d1-d0)/((t1-t0)/1000);
    view.etaAt=now;
    if(rate>0){const left=(1-fraction)/rate,minutes=Math.round(left/60);view.eta=left<60?'under 1 min left':minutes<60?`about ${minutes} min left`:`about ${Math.floor(minutes/60)} h ${minutes%60} min left`;}
  }
  // A held row is not running: no elapsed clock (Futaba, v0.16.8).
  writeText(view.time,held?'':clockText(elapsed,elapsed>=3600)+' elapsed'+(view.eta?' - '+view.eta:''));view.time.hidden=held;
}
let candidateFailure=null;
async function candidateRequest(route,extra={},options={}){candidateFailure=null;if(busy || ended || selectedRow?.kind!=='candidate')return;const original=selectedRow,library=selectedLibrary;busy=true;controls();try{const result=await request(route,{library,id:original.id,revision:original.revision,...extra});if(selectedRow?.id===original.id && selectedLibrary===library && result.row){const updated={...result.row,path:result.row.id,kind:'candidate',library};if(dirty)reviewRow=updated;select(updated,false);}lastKey=null;await refresh(true);return result;}catch(error){candidateFailure=error;if(!options.quiet)message(error.message);}finally{busy=false;controls();}}
let metadataChoiceState=null;
function metadataChoiceValues(){const values={};for(const name of fields)values[name]=form.elements.namedItem(name)?.value || '';for(const name of ['multi_author','anthology'])values[name]=!!form.elements.namedItem(name)?.checked;return values;}
function metadataChoiceFieldLabel(field){return ({title:'Title',canonical_author:'Author',original_language:'Original language',series:'Cycle',number:'Number in cycle',universe:'Universe',genre:'Genre',topic:'Topic',narrator:'Reader / narrator'})[field] || field.replaceAll('_',' ');}
function metadataChoiceDirtyReason(){
  const saved=metadataChoiceState;if(!saved)return '';
  if(!dirty)return '';
  if(saved.blockedDirty)return 'Save your edits before choosing a result.';
  const allowed=new Set();for(const question of saved.snapshot.questions || [])if(saved.answers[question.id]?.mode==='corrected')for(const field of question.type==='work_profile'?(question.profile_fields || ['title','canonical_author','original_language','series','number','universe']):[question.field])allowed.add(field);
  const values=metadataChoiceValues();if(!allowed.size || Object.keys(values).some(field=>values[field]!==saved.baseline[field] && !allowed.has(field)) || coverId!==saved.cover)return 'Save your edits before choosing a result.';
  return '';
}
function updateMetadataChoiceControls(){
  const saved=metadataChoiceState;if(!saved || $('metadata-questions').hidden)return;
  const reason=metadataChoiceDirtyReason();$('save-metadata-choices').disabled=!!(reason || saved.pending || ended || recoveryDisconnected);  // ruling 35: busy holds the press (later()), never disables it
  $('save-metadata-choices').textContent=saved.pending?'Saving choices…':'Save choices';
  const line=saved.pending && choiceSave?clockNote('Saving choices…',choiceSave.at):[saved.error,reason || saved.status || ''].filter(Boolean).join(' ');
  if($('metadata-question-status').textContent!==line)$('metadata-question-status').textContent=line;
}
function renderMetadataQuestions(row,reset=false){
  const section=$('metadata-questions'),snapshot=row.metadata_questions;
  if(row.kind!=='candidate' || !snapshot?.questions?.length){section.hidden=true;metadataChoiceState=null;return;}
  section.hidden=false;$('resolve-metadata-question').setAttribute('aria-label','Resolve metadata: '+(row.title_clue || row.id));
  const key=JSON.stringify([row.id,snapshot.signature,snapshot.questions.map(question=>[question.id,question.decision,question.renewed])]);
  if(metadataChoiceState?.key===key){metadataChoiceState.revision=row.revision;updateMetadataChoiceControls();return;}
  metadataChoiceState={id:row.id,revision:row.revision,key,snapshot,answers:{},baseline:metadataChoiceValues(),cover:row.review_context?.cover_id || row.selected_cover?.id || null,blockedDirty:dirty,
    pending:false,status:snapshot.questions.some(question=>question.renewed)?'Sources disagree — choose again.':snapshot.unresolved_count?`Metadata choice needed for ${row.title_clue || 'this book'}.`:'Chosen by you. Review the metadata to continue.'};
  const saved=metadataChoiceState,container=$('metadata-question-fields');container.replaceChildren();
  for(const question of snapshot.questions){
    const fieldset=node('fieldset'),legend=node('legend',question.label),help=node('p','Choose a result for this evidence snapshot. Other sources remain available.','field-help');help.id='metadata-question-help-'+question.id;fieldset.append(legend,help);fieldset.setAttribute('aria-describedby',help.id);
    const grid=node('div','','metadata-choice-grid');fieldset.append(grid);
    function radio(value,text,tooltip){
      const label=node('label','','metadata-choice-label'),input=node('input');input.type='radio';input.name='metadata-question-'+question.id;input.value=value;input.title=tooltip;input.setAttribute('aria-describedby',help.id);
      input.addEventListener('input',event=>event.stopPropagation());label.append(input,node('span',text));grid.append(label);return {input,label};
    }
    const prior=question.decision; saved.answers[question.id]=prior?{mode:prior.mode,option_id:prior.option_id}:{mode:'unresolved'};
    for(const option of question.options || []){
      const values=Object.entries(option.values || {}).map(([field,value])=>`${metadataChoiceFieldLabel(field)}: ${value || 'Not supplied'}`).join(' · '),names=(option.sources || []).map(source=>source.provider).join(', ');
      const item=radio(option.id,values+' — '+names,'Use this result for this conflict after saving your choices.');item.input.checked=prior?.mode==='provider' && prior.option_id===option.id;
      item.input.addEventListener('change',()=>{if(!item.input.checked)return;saved.answers[question.id]={mode:'provider',option_id:option.id};updateMetadataChoiceControls();});
      const card=node('section'),details=node('details'),summary=node('summary','View source evidence');card.append(item.label);details.append(summary);
      for(const source of option.sources || []){
        details.append(node('p',`${source.provider} · Record ${source.id || 'not supplied'} · Retrieved ${source.retrieved_utc || 'time not supplied'}`));
        if(source.public_url){const link=sourceLink(source.public_url,'Source record: '+source.provider+' — '+values);link.title='Open the source record for this result.';details.append(link);}
        for(const reference of source.source_links || []){const link=sourceLink(reference.url,'Source record: '+reference.provider+' — '+values);link.title='Open the source record for this result.';details.append(link);}
        details.append(node('pre',JSON.stringify(source.evidence || {},null,2)));
      }
      card.append(details);grid.append(card);
    }
    for(const source of question.not_supplied || [])fieldset.append(node('p',`Not supplied — ${source.provider} · ${source.id || 'Record ID not supplied'}`));
    const corrected=radio('corrected','Enter a corrected value','Enter your own value and save it with this conflict decision.');corrected.input.checked=prior?.mode==='corrected';
    corrected.input.addEventListener('change',()=>{if(!corrected.input.checked)return;saved.answers[question.id]={mode:'corrected'};$('manual-review').open=true;const control=form.elements.namedItem(question.type==='work_profile'?'title':question.field);if(control){control.title='Enter the value you want this book to use.';control.scrollIntoView?.({block:'center',behavior:'auto'});control.focus?.({preventScroll:true});}updateMetadataChoiceControls();});
    const unresolved=radio('unresolved','Keep unresolved','Leave this conflict open and keep this book out of automatic conversion.');unresolved.input.checked=!prior || prior.mode==='unresolved';
    unresolved.input.addEventListener('change',()=>{if(unresolved.input.checked){saved.answers[question.id]={mode:'unresolved'};updateMetadataChoiceControls();}});
    if(question.previous_decision){const decision=node('details'),summary=node('summary','View decision');summary.title='Show the sources compared and your saved choice.';decision.append(summary,node('p',question.resolved?'Chosen by you':'Earlier choice; current evidence needs review'),node('pre',JSON.stringify(question.previous_decision,null,2)));fieldset.append(decision);}
    container.append(fieldset);
  }
  // No focus/scroll action on a background render, including newly found conflicts.
  updateMetadataChoiceControls();
}
$('resolve-metadata-question').addEventListener('click',()=>{$('manual-review').open=true;$('metadata-questions-heading').scrollIntoView?.({block:'center',behavior:'auto'});$('metadata-questions-heading').focus?.({preventScroll:true});});
$('save-metadata-choices').addEventListener('click',later('toolbar:save-metadata-choices','save_choices',async()=>{
  const saved=metadataChoiceState;if(!saved || busy || ended || recoveryDisconnected || metadataChoiceDirtyReason())return;
  const choices=saved.snapshot.questions.map(question=>{const answer=saved.answers[question.id] || {mode:'unresolved'},choice={question_id:question.id,...answer};if(answer.mode==='corrected'){choice.values={};for(const field of question.type==='work_profile'?(question.profile_fields || ['title','canonical_author','original_language','series','number','universe']):[question.field])choice.values[field]=form.elements.namedItem(field)?.value.trim() || '';}return choice;});
  saved.pending=true;saved.error='';saved.status='';choiceSave={at:Date.now()};busy=true;controls();updateMetadataChoiceControls();
  try{
    const result=await request('/api/candidate/metadata-choice',{library:selectedLibrary,id:saved.id,revision:saved.revision,signature:saved.snapshot.signature,choices,manual_note:keptNote(selectedRow)});
    if(selectedRow?.id===saved.id && result.row){
      if(trackDraft?.id===saved.id && trackDraft.revision===saved.revision)trackDraft.revision=result.row.revision;
      dirty=false;manualMetadataTouched=false;syncManualDraft();
      for(const field of fields)if(form.elements.namedItem(field)!==document.activeElement)form.elements.namedItem(field).value=result.row.review?.[field] || (field==='original_language'?'Unknown':'');
      select({...result.row,path:result.row.id,kind:'candidate',library:selectedLibrary},false);
      if(metadataChoiceState?.id===saved.id)metadataChoiceState.status=choices.every(choice=>choice.mode==='unresolved')?'Left unresolved. This book stays held.':result.unresolved_count?`Choices saved. ${result.unresolved_count} conflicts remain.`:'Choices saved. Review the metadata to continue.';
    }
  }catch(error){
    if(selectedRow?.id===saved.id && error.httpStatus===409 && error.body?.row)renderMetadataQuestions({...error.body.row,kind:'candidate'},false);
    if(metadataChoiceState?.id===saved.id)metadataChoiceState.error='Choices not saved. '+(error.httpStatus?(error.message || 'Nothing was changed.'):lostLine());
  }finally{saved.pending=false;choiceSave=null;busy=false;controls();updateMetadataChoiceControls();}
}));
function renderMergeCandidate(row,reset){const candidate=row.kind==='candidate';renderMetadataQuestions(row,reset);for(const id of ['metadata-lookup','metadata-evidence','track-review','audiobook-output','create-audiobook'])$(id).hidden=!candidate;if(!candidate)return;
  const renderKey=JSON.stringify([row.id,row.revision,row.review_context,row.matching,row.cover_choices,row.creation,row.cleanup,row.audiobook_ready,row.metadata_facts,row.duplicate_review,row.manual_metadata_sources,row.metadata_holds,dirty,trackDirty,coverId]);
  if(!reset && renderKey===mergeRenderKey)return;mergeRenderKey=$('manual-review').contains?.(document.activeElement)?null:renderKey;
  // Keep metadata and track editing inside the optional manual disclosure.
  if($('candidate-details').parentElement!==$('manual-review') || $('candidate-details').nextElementSibling!==$('track-review'))$('manual-review').insertBefore($('candidate-details'),$('track-review'));
  const context=row.review_context || {},creation=row.creation || {},matching=row.matching || {};
  if(!dirty){++routingPreviewSequence;$('routing-preview-label').textContent='Output folder';$('routing-preview-path').textContent=creation.destination || row.preview?.reason || '';}
  const metadataHolds=row.metadata_holds || [],questionsPending=(row.metadata_questions?.unresolved_count || 0)>0;const metadataRemedy=questionsPending?'Resolve metadata question':namesHold(row)?'Edit names':'Edit metadata';$('edit-held-metadata').hidden=!metadataHolds.length && !questionsPending;$('edit-held-metadata').textContent=metadataRemedy;$('edit-held-metadata').setAttribute('aria-label',metadataRemedy+': '+(row.title_clue || row.id));$('metadata-hold-fields').hidden=!metadataHolds.length && !questionsPending;$('metadata-hold-fields').textContent=questionsPending?'Choose which recorded values this book should use. Your answer saves a draft for review.':metadataHolds.map(item=>item.reason).join(' · ');
  if(reset || (!dirty && !$('manual-review').contains?.(document.activeElement))){proposalId=context.proposal_id || null;coverId=context.cover_id || row.selected_cover?.id || null;}
  if(reset || (!trackDirty && !$('track-review').contains?.(document.activeElement) && !$('candidate-details').contains?.(document.activeElement))){trackDraft={id:row.id,revision:row.revision,order:row.track_order || row.members.map(member=>member.member_key || member.path),included:row.included || row.members.map(member=>member.member_key || member.path)};trackDirty=false;$('source-coverage').checked=!!context.source_coverage_confirmed;$('playback-order').checked=!!context.order_confirmed;const chapterDefault=context.chapters_choice_saved===false && creation.chapters_default===true && creation.chapters_available===true && !creation.job && !/queued|creating|checking|created|completed/i.test(creation.status || '');$('add-chapters').checked=chapterDefault || !!context.chapters;if(chapterDefault)trackDirty=true;}
  const actor=actorValue=>actorValue==='assistant'?'Assistant review':actorValue==='user'?'User review':'Needs review';
  $('candidate-facts').textContent=`Metadata: ${actor(context.metadata_actor)} · ${context.source_coverage_confirmed?'Source files reviewed: '+actor(context.track_actor):'Source files need review'} · Playback order: ${context.order_confirmed?actor(context.track_actor):'Needs review'} · Recording completeness unknown`;
  $('matching-status').textContent=matching.error || (matching.conflicts?.length?`${matching.conflicts.length} metadata disagreements need review.`:null) || (matching.state==='finding' || matching.state==='pending'?'Finding metadata…':matching.proposals?.length?'Original work matches; recording unverified':matching.state==='completed'?'No reliable match found. Review the title and author, then try again.':'Find possible identities or enter verified metadata manually.');
  const proposalKey=JSON.stringify([row.id,matching]);if(proposalKey!==proposalRenderKey && !$('metadata-proposals').contains?.(document.activeElement)){proposalRenderKey=proposalKey;$('metadata-proposals').replaceChildren();for(const proposal of matching.proposals || []){const panel=node('section','','proposal'),authors=Array.isArray(proposal.authors)?proposal.authors.join('; '):proposal.authors || '';panel.append(node('p',`${proposal.title || 'Unknown title'} · ${authors || 'Author unknown'}`),node('p',[proposal.original_language,proposal.series,proposal.number,'Original work match; recording unverified'].filter(Boolean).join(' · ')),proposal.manual_source?node('p','Entered by you · '+(proposal.per_field_evidence?.saved_utc || '')):sourceLink(proposal.public_url,`${proposal.provider || 'Source'}: ${proposal.title || 'book identity'}`));const evidence=node('details');evidence.append(node('summary','View evidence'),node('pre',JSON.stringify(proposal.per_field_evidence || {},null,2)));panel.append(evidence);const use=node('button','Use as proposal');use.type='button';use.title='Fill draft metadata from this match. Review the fields before approving.';use.disabled=ended;use.addEventListener('click',()=>{if(busy || ended)return;if(!dirty)reviewRow=selectedRow;proposalId=proposal.id;const named=!namesLocked();if(named && proposal.title)form.elements.namedItem('title').value=proposal.title;if(authors)form.elements.namedItem('canonical_author').value=authors;if(proposal.original_language && !['unknown','und'].includes(proposal.original_language.toLowerCase())){const lang=proposal.original_language.toLowerCase();form.elements.namedItem('original_language').value=['russian','ru','rus'].includes(lang)?'Russian':'Other';}if(named && proposal.universe)form.elements.namedItem('universe').value=proposal.universe;if(named && proposal.series)form.elements.namedItem('series').value=proposal.series;if(named && proposal.number!==null && proposal.number!==undefined)form.elements.namedItem('number').value=String(proposal.number);dirty=true;noteOnlyDirty=false;manualMetadataTouched=true;syncManualDraft();$('review-note').textContent='Proposal copied to draft. Review its sourced fields before saving.';controls();});panel.append(use);$('metadata-proposals').append(panel);}}
  renderMembers(row);renderCovers(row);
  $('chapters-control').hidden=!creation.chapters_available;$('add-chapters').disabled=!creation.chapters_available || busy;$('chapters-help').textContent=creation.chapters_available?"Preserves source track names when available. Unnamed tracks use Track 01, Track 02, and so on. These markers may differ from the book's written chapters.":creation.chapters_description || 'Chapter boundaries unavailable.';
  $('output-status').textContent=candidateStatus(row);$('output-path').textContent=creation.destination || 'No reviewed destination yet.';
  $('output-summary').textContent=[creation.format || 'M4B audiobook',`Included files: ${trackDraft.included.length}`,`Duration: ${typeof creation.duration_seconds==='number'?creation.duration_seconds.toFixed(2)+' s':'Total duration incomplete'}`,`Title: ${row.review?.title || 'Needs review'}`,`Artist: ${row.review?.canonical_author || 'Needs author review'}`,`Series: ${row.metadata_facts?.series_state==='omitted_unknown'?'Not established':row.review?.series || 'Series not established'}${row.metadata_facts?.series_state==='omitted_unknown'?'':row.review?.number?' / '+row.review.number:''}`,`Reader / comments: ${row.tag_preview?.narrator || row.review?.narrator || 'Unknown optional narrator'}`,`Comments: ${JSON.stringify(row.tag_preview?.comment_fields || [])}`,`Cover: ${provenanceFacts(row).Cover || row.selected_cover?.source_label || 'Artwork not established'}`,chapterSummary(row),...Object.entries({...provenanceFacts(row),...recordingFacts(row)}).filter(([label])=>!['Series','Cover'].includes(label)).map(([label,value])=>label+': '+value),...cleanupFacts(row)].join('\n');
  const cleanupPolicy=creation.cleanup_policy?.enabled===true,recordedRemoval=verifiedCount(row.cleanup?.removed)>0;$('output-policy-notice').textContent=recordedRemoval && !cleanupPolicy?(row.cleanup.status || 'Source cleanup needs attention: review the saved removal progress.'):cleanupPolicy?'Creates one audiobook, verifies it, then removes the included originals and their backup copies.':'Creates one new audiobook. Your source files stay in place.';$('create-audiobook').title=cleanupPolicy?'Create and verify this audiobook, then remove its included originals and their backup copies.':'Create and check one M4B from this reviewed book. Keep the source files.';
  $('output-reasons').textContent=[...(creation.reasons || []),dirty?'Save metadata edits before creating.':'',trackDirty?'Save track review before creating.':''].filter(Boolean).join(' · ');$('output-device').textContent=creation.device || 'Apple Books sync not checked';
}
function verifiedCount(value){return Number.isSafeInteger(value) && value>=0?value:null;}
function cleanupFacts(row){const creation=row.creation || {},policy=creation.cleanup_policy || {},receipt=row.cleanup || {},removed=verifiedCount(receipt.removed),total=verifiedCount(receipt.total),progress=removed!==null && total!==null?`${removed} of ${total} removed`:null;const state=typeof receipt.state==='string'?receipt.state.toLowerCase().replaceAll('_',' '):'';let status=typeof receipt.status==='string'?receipt.status:'';if(receipt.state==='completed' && receipt.recovery?.state==='retained')status='Originals removed; deleting recovery copies';if(!status){const states={'waiting':'Waiting for output checks','pending':'Waiting for output checks','checking':'Checking temporary recovery copies','checking recovery':'Checking temporary recovery copies','preparing':'Checking temporary recovery copies','removing':removed!==null && total!==null?`Removing originals: ${removed} of ${total}`:'Removing originals','pausing':'Pausing source cleanup','paused':progress?`Source cleanup paused: ${progress}`:'Source cleanup paused','completed':receipt.temporary_cleanup==='completed'?'Originals removed; verified temporary recovery and working copies removed':'Originals removed; temporary file cleanup pending','needs attention':'Source cleanup needs attention','failed':'Source cleanup needs attention'};status=states[state] || (removed>0?'Source cleanup needs attention':policy.enabled===true?'Waiting for output checks':'Originals retained');}const facts=[`Audiobook output: ${candidateStatus(row)}`,`Source cleanup: ${policy.enabled===true?'remove originals and their backup copies after audiobook verification':'originals retained'}`];if(removed>0 && policy.enabled!==true)facts[1]='Source cleanup: '+status;else if(receipt.state || receipt.status || policy.enabled===true)facts.push('Source cleanup status: '+status);if(progress && !status.includes(progress) && !status.includes(`${removed} of ${total}`))facts.push(progress);if(receipt.reason && !status.includes(receipt.reason))facts.push('Source cleanup needs attention: '+receipt.reason);if(receipt.recovery)facts.push('Recovery copies: '+recoveryStatus(receipt.recovery));const location=receipt.recovery?null:(receipt.recovery_location || policy.recovery_root);if(!receipt.recovery && receipt.temporary_cleanup==='completed')facts.push('Temporary recovery files: removed');else if(location && receipt.recovery_bytes!==0)facts.push('Temporary recovery storage: '+location);const bytes=verifiedCount(receipt.bytes_removed),recovery=verifiedCount(receipt.recovery_bytes);if(removed>0 && bytes!==null)facts.push(`Removed from Z: ${bytes.toLocaleString('en-US')} bytes`);if(!receipt.recovery && recovery!==null && recovery>0)facts.push(`Temporary recovery storage on C: ${recovery.toLocaleString('en-US')} bytes`);const evidence=verifiedCount(receipt.preserved_evidence_count);if(evidence>0)facts.push(`Unverified legacy evidence retained: ${evidence.toLocaleString('en-US')} files`);const remaining=verifiedCount(receipt.remaining);if(remaining!==null)facts.push('Originals remaining: '+remaining);return facts;}
function chapterSummary(row){if(row.creation?.job)return row.creation.chapters_description || 'Chapter markers: see saved job plan';return $('add-chapters').checked && row.creation?.chapters_available?`Chapter markers: ${trackDraft.included.length} — one per included source track`:'Chapter markers: none';}
function updateChapterSummary(){if(!trackDraft || selectedRow?.kind!=='candidate')return;$('output-summary').textContent=$('output-summary').textContent.replace(/^Chapter markers:.*$/m,chapterSummary(selectedRow));}
function plannedChapter(member,key){if(!$('add-chapters').checked)return 'Chapter markers disabled';if(!trackDraft.included.includes(key))return 'Excluded from output — no chapter marker';if(member.chapter_name_source==='source' && member.chapter_name)return 'Source chapter name: '+member.chapter_name;const position=trackDraft.order.filter(id=>trackDraft.included.includes(id)).indexOf(key)+1;const number=Number.isInteger(member.chapter_number) && member.chapter_number>=0?member.chapter_number:position;return 'Generated chapter label: Track '+String(number).padStart(Math.max(2,String(trackDraft.included.length).length),'0');}
function renderMembers(row,force=false){if(!force && $('candidate-members').contains?.(document.activeElement))return;const focused=document.activeElement?.dataset?.memberFocus;const memberKey=JSON.stringify([row.id,row.members,row.metadata_facts,trackDraft.order,trackDraft.included,$('add-chapters').checked]);if(memberKey===memberRenderKey)return;memberRenderKey=memberKey;$('candidate-members').replaceChildren();const map=new Map(row.members.map(member=>[member.member_key || member.path,member])),order=trackDraft.order;const header=$('candidate-members').parentElement.querySelector('thead tr');header.replaceChildren();for(const label of ['Include','Proposed order','Track title / filename','Source disc / track number','Duration','Order evidence'])header.append(node('th',label));for(let index=0;index<order.length;index++){const key=order[index],member=map.get(key);if(!member)continue;const tr=node('tr'),inc=node('input');inc.type='checkbox';inc.dataset.memberFocus=key+':include';inc.checked=trackDraft.included.includes(key);inc.title='Include this source file in the output audiobook. Excluded files stay untouched.';inc.setAttribute('aria-label','Include '+member.path);inc.setAttribute('aria-describedby','track-save-help');inc.disabled=ended;inc.addEventListener('change',()=>{if(busy || ended){inc.checked=trackDraft.included.includes(key);return;}trackDraft.included=inc.checked?[...trackDraft.included,key]:trackDraft.included.filter(item=>item!==key);tracksChanged();renderMembers(row,true);});const label=node('label','','check');label.append(inc,node('span',inc.checked?'Included':'Excluded from output'));const include=node('td');include.append(label);tr.append(include);const movement=node('td');movement.append(node('p',String(index+1)));const buttons=node('div','','member-actions');for(const [delta,text] of [[-1,'Move up'],[1,'Move down']]){const button=node('button',text,'quiet');button.type='button';button.dataset.memberFocus=key+':'+delta;button.title=`${text}: ${member.path}`;button.setAttribute('aria-label',`${text}: ${member.path}`);button.setAttribute('aria-describedby','order-help');button.disabled=ended || index+delta<0 || index+delta>=order.length;button.addEventListener('click',()=>{if(busy || ended)return;[order[index],order[index+delta]]=[order[index+delta],order[index]];tracksChanged();renderMembers(row,true);});buttons.append(button);}movement.append(buttons);tr.append(movement);for(const value of [`${member.track_title || ''}\n${member.path}${member.missing?'\nNot found':''}\n${plannedChapter(member,key)}${memberComponents(member,row).length?'\n'+memberComponents(member,row).join('\n'):''}`, `${member.source_disc || 'Unknown'} / ${member.source_track || 'Unknown'}`,typeof member.duration==='number'?`${member.duration.toFixed(2)} s`:'Unknown',member.order_evidence || 'Unknown'])tr.append(node('td',value));$('candidate-members').append(tr);}if(focused){const target=[...$('candidate-members').querySelectorAll('[data-member-focus]')].find(element=>element.dataset.memberFocus===focused && !element.disabled);target?.focus({preventScroll:true});}const included=row.members.filter(member=>trackDraft.included.includes(member.member_key || member.path)),known=included.every(member=>typeof member.duration==='number');$('member-count').textContent=`Included audio files — ${included.length} · ${known?included.reduce((sum,member)=>sum+member.duration,0).toFixed(2)+' s':'Total duration incomplete'}`;}
function tracksChanged(){panelDiscarded=null;trackDirty=true;manualTrackTouched=true;syncManualDraft();updateChapterSummary();$('source-coverage').checked=false;$('playback-order').checked=false;controls();$('output-reasons').textContent='Save the changed source selection and playback order. Review confirmations were reset.';}
async function renderCovers(row){const coverKey=JSON.stringify([row.id,row.cover_choices,coverId]);if(coverKey===coverRenderKey || $('selected-cover').contains?.(document.activeElement) || $('cover-choices').contains?.(document.activeElement))return;coverRenderKey=coverKey;const seq=++coverSequence;for(const url of coverObjects)URL.revokeObjectURL(url);coverObjects.length=0;$('selected-cover').replaceChildren();$('cover-choices').replaceChildren();for(const cover of row.cover_choices || []){const panel=node('section','','cover-choice');panel.append(node('p',`${cover.source_label || 'Artwork'} · ${cover.evidence_kind || 'Local artwork — edition unverified'}`));if(cover.source_url)panel.append(sourceLink(cover.source_url,`Cover source: ${cover.source_label || 'Artwork'}`));const image=node('img');image.alt=`Cover: ${row.review?.title || row.title_clue}`;image.hidden=true;panel.append(image);const imageState=node('p','Loading cover…');panel.append(imageState);const use=node('button','Use this cover','quiet');use.type='button';use.title='Select this image as the single cover in the output audiobook.';use.setAttribute('aria-describedby','cover-help');use.disabled=ended;use.addEventListener('click',()=>{if(busy || ended)return;if(!dirty)reviewRow=selectedRow;coverId=cover.id;dirty=true;noteOnlyDirty=false;manualMetadataTouched=true;syncManualDraft();$('review-note').textContent='Cover selection is an unsaved draft.';renderCovers(row);controls();});panel.append(use);(cover.id===coverId?$('selected-cover'):$('cover-choices')).append(panel);if(!cover.thumbnail_url){imageState.textContent='Cover image unavailable';continue;}try{const url=new URL(cover.thumbnail_url,location.origin);if(url.origin!==location.origin)throw Error('Invalid local thumbnail route');const response=await fetch(url.href,{headers:{'X-Books-Token':token},credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error('Cover image unavailable');const blob=await response.blob();if(seq!==coverSequence)return;const object=URL.createObjectURL(blob);coverObjects.push(object);image.src=object;image.hidden=false;imageState.textContent='';}catch(error){if(seq===coverSequence)imageState.textContent=error.message || 'Cover image unavailable';}}if(!coverId)$('selected-cover').append(node('p',row.metadata_facts?.cover?.kind==='absent'?'No artwork available; the saved policy permits processing without artwork.':'Artwork not selected. Artwork alone does not establish recording identity.'));}
$('select-page').addEventListener('change',()=>{const on=$('select-page').checked;for(const row of on?pageSelectable():rows.filter(item=>item.kind==='candidate')){if(on)selectedBooks.set(row.id,row.revision);else selectedBooks.delete(row.id);}renderRows();});
$('find-metadata').addEventListener('click',later('toolbar:find-metadata','find_metadata',()=>candidateRequest('/api/candidate/match')));
$('edit-held-metadata').addEventListener('click',()=>{if(!selectedRow || ended)return;if(!selectedRow.metadata_questions?.unresolved_count && namesHold(selectedRow))return panelEditNames();if(selectedRow.metadata_questions?.unresolved_count){$('manual-review').open=true;const heading=$('metadata-questions-heading');heading.scrollIntoView?.({block:'center',behavior:'auto'});heading.focus?.({preventScroll:true});return;}$('manual-review').open=true;const field=(selectedRow.metadata_holds || []).flatMap(item=>item.fields || [])[0] || 'title';const control=form.elements.namedItem(field) || form.elements.namedItem('title');control?.scrollIntoView?.({block:'center',behavior:'auto'});control?.focus?.({preventScroll:true});});
$('check-metadata').addEventListener('click',later('toolbar:check-metadata','check_metadata',()=>{if(dirty || busy || ended)return;$('matching-status').textContent='Checking metadata…';return candidateRequest('/api/candidate/match');}));
$('find-covers').addEventListener('click',later('toolbar:find-covers','find_covers',()=>candidateRequest('/api/candidate/covers')));
$('save-tracks').addEventListener('click',later('toolbar:save-tracks','save_tracks',async()=>{if(!trackDraft || trackSave)return;const draft=trackDraft;trackSave={at:Date.now()};trackSaveLine();const result=await candidateRequest('/api/candidate/tracks',{revision:draft.revision,order:draft.order,included:draft.included,source_coverage_confirmed:$('source-coverage').checked,order_confirmed:$('playback-order').checked,chapters:$('add-chapters').checked,actor:'user',evidence_note:''},{quiet:true});if(result?.row && selectedRow?.id===draft.id){trackDirty=false;manualTrackTouched=false;
  // The rows update now, not at the next poll, so Approve this order works as soon as the save lands (Futaba 0.22.0 M-3).
  syncManualDraft();renderMergeCandidate(selectedRow,false);controls();}
  trackSave=null;trackSaveLine(result?.row?'Track review saved.':'Track review not saved. '+(candidateFailure?serverSentence(candidateFailure,'Nothing was changed.'):'Nothing was changed.'));}));
function trackSaveLine(text){const line=$('track-save-status');if(!line)return;const value=trackSave?clockNote('Saving track review…',trackSave.at):text ?? line.textContent;if(line.textContent!==value)line.textContent=value;}
for(const id of ['source-coverage','playback-order','add-chapters'])$(id).addEventListener('change',()=>{trackDirty=true;manualTrackTouched=true;syncManualDraft();updateChapterSummary();if(id==='add-chapters' && selectedRow?.kind==='candidate')renderMembers(selectedRow);controls();});
$('create-audiobook').addEventListener('click',later('toolbar:create-audiobook','create',()=>{if(!dirty && !trackDirty && selectedRow?.creation?.can_create)candidateRequest('/api/audiobook/create');}));
$('queue-books').addEventListener('click',later('toolbar:queue-books','queue_books',async()=>{const chosen=rows.filter(row=>row.kind==='candidate' && selectedBooks.has(row.id));const ready=chosen.filter(row=>readyForQueue(row));const blocked=chosen.filter(row=>!ready.includes(row));if(!ready.length)return;if(busy || ended)return;busy=true;controls();try{const result=await request('/api/audiobook/queue',{library:'Audiobooks',candidates:ready.map(row=>({id:row.id,revision:row.revision}))});await refresh(true);message([`${ready.length} reviewed candidate(s) requested for queue.`,...blocked.map(row=>`${row.title_clue}: ${(row.creation?.reasons || ['Needs review or candidate changed']).join('; ')}`)].join('\n'));if(result.excluded?.length)message($('message').textContent+'\n'+result.excluded.map(item=>item.reason || 'Candidate needs review').join('\n'));}catch(error){message(error.message);}finally{busy=false;controls();}}));
$('pause-jobs').addEventListener('click',later('toolbar:pause-jobs','pause',()=>action('/api/audiobook/pause',{})));{const resume=later('toolbar:resume-jobs','resume',()=>action('/api/audiobook/resume',{}));$('resume-jobs').addEventListener('click',event=>state?.audiobook_jobs?.start_waiting && !laterFor('toolbar:resume-jobs')?action('/api/audiobook/resume-cancel',{}):resume(event));}
function recoveryDate(value){if(!value)return 'Unavailable';const date=new Date(value);if(!Number.isFinite(date.getTime()))return 'Unavailable';const zone=Intl.DateTimeFormat().resolvedOptions().timeZone;return new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:zone}).format(date)+` (${zone})`;}
function recoverySpace(value){return verifiedCount(value)===null?'Unavailable':`${(value/(value>0 && value<1000000?1000:1000000)).toLocaleString('en-US',{maximumFractionDigits:2})} ${value>0 && value<1000000?'KB':'MB'} (${value.toLocaleString('en-US')} bytes)`;}
function recoveryScope(row){const r=row?.cleanup?.recovery;return r?{job_id:row.creation?.job_id || row.creation?.job?.job_id || row.creation?.job?.id,token:r.token,count:r.count,bytes:r.bytes}:null;}
// The rest of ruling 35 (ruling 37): Delete recovery copies is accepted during a scan, a source cleanup or another book's
// deletion, and queued; while queued the same button takes it back. Provisional copy, sent to Judy.
const RECOVERY_WAITS={scan:'It runs when the scan finishes.',cleanup:'It runs when the source cleanup finishes.',deletion:'It runs after the deletion before it.',start:'It starts shortly.'};
const RECOVERY_WAITING={scan:'A scan is running, so the deletion is queued after you confirm.',cleanup:'A source cleanup is running, so the deletion is queued after you confirm.'};
const RECOVERY_BUTTON=['Delete recovery copies…','Permanently delete the verified recovery copies for this book. Keep the finished audiobook.'];
let recoveryCancelling=false;
function recoveryQueuedLine(waits){return 'Deletion queued. '+(RECOVERY_WAITS[waits] || RECOVERY_WAITS.start);}
function recoveryReason(){const r=selectedRow?.cleanup?.recovery;if(ended || recoveryDisconnected)return 'Local server unavailable';if(recoveryCancelling)return 'Cancelling the deletion…';if(recoverySubmitting)return 'Deleting the recovery copies…';if(!r)return 'Recovery details unavailable';if(r.queued===true)return '';if(r.state==='deleted')return 'No recovery copies remain';if(r.state==='deleting')return 'Recovery deletion is in progress';if(r.eligible!==true)return r.reason || 'Recovery copies are not eligible for deletion';if(!(verifiedCount(r.count)>0) || verifiedCount(r.bytes)===null || !r.token || !recoveryScope(selectedRow)?.job_id)return 'Verified recovery scope unavailable';return '';}
function recoveryStatus(r){if(r.queued===true && r.state!=='deleted' && r.state!=='deleting')return recoveryQueuedLine(r.waits);if(r.state==='deleted')return `Recovery copies deleted${r.actor==='automatic'?' automatically':r.actor==='manual'?' manually':''} on ${recoveryDate(r.deleted_at)}`;if(r.state==='deleting')return `Deleting recovery copies: ${verifiedCount(r.removed) ?? 'Unavailable'} of ${verifiedCount(r.total) ?? 'Unavailable'}`;if(r.state==='retained' && !r.eligible)return 'Recovery copies waiting to be deleted. '+(r.reason || 'Deletion is temporarily unavailable');if(r.state==='needs_attention' || !r.eligible)return 'Recovery cleanup needs attention: '+(r.reason || 'Verified recovery scope unavailable');return 'Deleting after the audiobook check';}
function makeRecoveryPanel(){const panel=node('section','','recovery-copies'),facts=node('dl'),values={};panel.append(node('h2','Recovery copies'));for(const key of ['Status','Original tracks backed up','Space on C:','Recovery location','Automatic deletion']){const label=node('dt',key),value=node('dd');facts.append(label,value);values[key]={label,value};}panel.append(facts);const help=node('p',"Deleting these copies permanently removes the app's backup of the original tracks. The finished audiobook stays in place.",'field-help');help.id='recovery-loss-help';const expiry=node('p','Automatic deletion happens while the app is running; overdue copies are checked when it starts.','field-help');const button=node('button','Delete recovery copies…','quiet');button.type='button';button.title='Permanently delete the verified recovery copies for this book. Keep the finished audiobook.';button.setAttribute('aria-describedby','recovery-loss-help recovery-reason');const reason=node('p','','field-help');reason.id='recovery-reason';const status=node('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');panel.append(help,expiry,button,reason,status);recoveryPanel={panel,values,expiry,button,reason,status,path:selectedPath};button.addEventListener('click',()=>selectedRow?.cleanup?.recovery?.queued===true?cancelRecoveryDeletion():openRecoveryDialog());updateRecovery();return panel;}
function updateRecovery(){if(!recoveryPanel || recoveryPanel.path!==selectedPath)return;const r=selectedRow?.cleanup?.recovery;if(!r){recoveryPanel.panel.hidden=true;closeRecoveryDialog();return;}recoveryPanel.panel.hidden=false;const v=recoveryPanel.values;v.Status.value.textContent=recoveryStatus(r);v['Original tracks backed up'].value.textContent=verifiedCount(r.count)===null?'Unavailable':r.count.toLocaleString('en-US');v['Space on C:'].value.textContent=recoverySpace(r.bytes);v['Recovery location'].label.textContent=r.state==='deleted'?'Former recovery location':'Recovery location';v['Recovery location'].value.textContent=r.location || 'Unavailable';v['Recovery location'].value.className='path';v['Automatic deletion'].value.textContent=r.state==='deleted'?(r.expires_at?'Completed':'Not applicable — copies already deleted'):recoveryDate(r.expires_at);recoveryPanel.expiry.hidden=r.state==='deleted';const reason=recoveryReason();recoveryPanel.button.disabled=!!reason;recoveryPanel.reason.textContent=reason;
  {const queued=r.queued===true && r.state!=='deleted' && r.state!=='deleting',label=queued?'Cancel deletion':RECOVERY_BUTTON[0],tip=queued?'Take this deletion out of the queue. Nothing was deleted.':RECOVERY_WAITING[r.waits]?RECOVERY_BUTTON[1]+' '+RECOVERY_WAITING[r.waits]:RECOVERY_BUTTON[1];
   if(recoveryPanel.button.textContent!==label)recoveryPanel.button.textContent=label;if(recoveryPanel.button.title!==tip)recoveryPanel.button.title=tip;}if(recoveryConfirmation && !recoverySubmitting && (reason || JSON.stringify(recoveryScope(selectedRow))!==JSON.stringify(recoveryConfirmation.scope))){closeRecoveryDialog();recoveryPanel.status.textContent='Recovery copies changed. Review the updated details and try again.';}}
function closeRecoveryDialog(restore=true){if(!recoveryConfirmation)return;const initiating=recoveryConfirmation.button;recoveryConfirmation=null;$('recovery-dialog').close?.();if(restore && initiating && initiating===recoveryPanel?.button){if(!initiating.disabled)initiating.focus?.({preventScroll:true});else{recoveryPanel.reason.setAttribute('tabindex','-1');recoveryPanel.reason.focus?.({preventScroll:true});}}}
function openRecoveryDialog(){if(recoveryReason() || recoveryConfirmation)return;const scope=recoveryScope(selectedRow),r=selectedRow.cleanup.recovery;recoveryConfirmation={scope:{...scope},path:selectedPath,button:recoveryPanel.button};$('recovery-dialog-book').textContent=`${selectedRow.review?.title || selectedRow.title_clue || 'Book'} — ${selectedRow.review?.canonical_author || 'Author unavailable'}`;$('recovery-dialog-size').textContent=`${scope.count} original tracks · ${recoverySpace(scope.bytes)} on C:`;$('recovery-dialog-location').textContent=r.location || 'Unavailable';$('recovery-dialog').showModal?.();$('recovery-cancel').focus?.();}
async function deleteRecoveryCopies(){if(!recoveryConfirmation || recoverySubmitting)return;const saved=recoveryConfirmation;if(recoveryReason() || selectedPath!==saved.path || JSON.stringify(recoveryScope(selectedRow))!==JSON.stringify(saved.scope)){closeRecoveryDialog();if(recoveryPanel)recoveryPanel.status.textContent='Recovery copies changed. Review the updated details and try again.';return;}closeRecoveryDialog();recoverySubmitting=true;updateRecovery();const panel=recoveryPanel;panel.status.textContent='Deleting recovery copies…';try{const answer=await request('/api/audiobook/recovery/delete',saved.scope);await refresh(true);if(panel===recoveryPanel)panel.status.textContent=answer?.queued===true?recoveryQueuedLine(answer.waits):'Recovery deletion request completed.';}catch(error){if(panel===recoveryPanel)panel.status.textContent=error.httpStatus===409?'Recovery copies changed. Review the updated details and try again.':error.message;if(!error.httpStatus)refreshFailed(error);}finally{recoverySubmitting=false;updateRecovery();}}
// A queued Delete recovery copies taken back (ruling 35's rest): nothing was deleted; once it started, too late.
async function cancelRecoveryDeletion(){
  const scope=recoveryScope(selectedRow),panel=recoveryPanel;if(!scope?.job_id || !panel || recoveryCancelling || recoverySubmitting)return;
  recoveryCancelling=true;updateRecovery();
  try{await request('/api/audiobook/recovery/cancel',{job_id:scope.job_id});if(panel===recoveryPanel)panel.status.textContent='Deletion cancelled. Nothing was deleted.';}
  catch(error){if(panel===recoveryPanel)panel.status.textContent=error.body?.code==='started'?'Too late to cancel: the deletion has already started.':error.message;if(!error.httpStatus)refreshFailed(error);}
  finally{recoveryCancelling=false;}
  if(!ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  updateRecovery();
}
// Retry for an audiobook job refused before it started. One static button, updated in place from
// controls() on every poll; pending and result text belong to one book (candidate id + job id).
const retryReady='Check this book again and queue its audiobook job.';
// A book's press key: its job, or (a held book with no job) its release.
function retryKey(row){const job=row?.kind==='candidate'?row.creation?.job:null;if(job && typeof job.job_id==='string')return JSON.stringify([row.id,job.job_id]);return row?.kind==='candidate' && releaseOf(row)?JSON.stringify([row.id,'release']):'';}
// Repair (Attention spec section 2) is the same control with another label, tooltip and endpoint.
const rowActions={queued:{kind:'queued',label:'Queued',pending:'Queued',note:'',ready:'',endpoint:null,refused:''},retry:{kind:'retry',label:'Retry',pending:'Checking…',note:'Checking this book…',ready:retryReady,endpoint:'/api/audiobook/retry',refused:'Retry was not accepted. Check the status above.'},
  repair:{kind:'repair',label:'Repair',pending:'Repairing…',note:'Repairing this book…',ready:'Patch the damage found in this book, then queue its audiobook job.',endpoint:'/api/audiobook/repair',refused:'Repair was not accepted. Check the status above.'},
  // Keep files (spec section 3): the kept recovery copies stop being flagged. Nothing is deleted, no job runs.
  keep:{kind:'keep',label:'Keep files',pending:'Keeping…',note:'Keeping these files…',ready:"Keep this book's files and stop flagging it. Nothing is deleted.",endpoint:'/api/audiobook/keep',refused:'Keep files was not accepted. Check the status above.'},
  // Start over (follow-ups 2-4): in the Retry slot of a "review changed" row. The combined press and the release discard
  // a saved review, so they confirm first. Nothing else on the row moves.
  startover:{kind:'startover',label:'Start over',pending:'Starting over…',note:'Setting this job aside…',ready:"Set this failed job aside and send the book back to automatic processing. Starts automatic processing if it isn't running. Nothing is deleted.",endpoint:'/api/audiobook/startover',refused:'Start over was not accepted. Check the status above.'},
  combined:{kind:'combined',label:'Start over and let the app handle it',pending:'Starting over…',note:'Setting this job aside and discarding the saved review…',ready:"Set this failed job aside, discard this book's saved review (including any edits you made by hand), and let automatic processing take the book. Starts automatic processing if it isn't running. This can't be undone. The failed job and your audio files are kept.",endpoint:'/api/audiobook/startover',refused:'Start over was not accepted. Nothing was changed.',confirm:true},
  release:{kind:'release',label:'Let the app handle it',pending:'Discarding review…',note:'Discarding the saved review…',ready:"Discard this book's saved review, including any edits you made by hand, and let automatic processing take the book. Starts automatic processing if it isn't running. This can't be undone. Your audio files are not touched.",endpoint:'/api/audiobook/release',refused:"The review wasn't discarded. Select the row to read why.",confirm:true}};
// Сказка (0.21.1 UX spec section 2): Convert… opens the confirmation; Confirm and convert saves it and queues the retry.
rowActions.convert={kind:'convert',label:'Convert…',pending:'Starting…',note:'Saving your confirmation, then checking the book.',ready:'Confirm where this conversion ran, then convert this book. Opens a confirmation first.',endpoint:'/api/audiobook/confirm-convert',refused:'Conversion not started.'};
const ORIGIN_STATEMENTS=['The interrupted conversion ran on this PC.','Since then, Windows and these files were not moved, copied, cloned or restored from a backup.'];
const TAG_REPAIR_HINT='An MP3 file failed its audio check in an earlier app version. Retry checks it again.',AUTO_QUEUED_HINT='Queued by automatic processing. Nothing to do.';
function deletionLine(capability){const d=capability?.disposal,bytes=d?.bytes;return `When the new conversion is verified, the old working files${Number.isSafeInteger(bytes) && bytes>0?` (about ${sizeText(bytes)})`:''} and the ${Number.isInteger(d?.originals) && d.originals>1?'originals':'original'} are deleted.`;}
rowActions.prepare={kind:'prepare',label:'Prepare recovery',pending:'Preparing…',note:"Saving this book's recovery checkpoint. Audio files stay in place.",ready:"Save this job's recovery checkpoint without changing its audio files.",endpoint:'/api/audiobook/prepare-recovery'};
function producerRecoveryOf(row){const value=row?.creation?.job?.attention?.producer_recovery;return value?.schema==='books-producer-recovery-capability-v1' && ['prepare','waiting_restart','ready','isolated_retained','unsupported'].includes(value.state)?value:null;}
function producerRecoveryText(row){
  const capability=producerRecoveryOf(row);if(!capability)return null;
  const key=retryKey(row);
  if(retryResult?.key===key && retryResult.producer && ((retryResult.snapshot && retryResult.snapshot!==JSON.stringify([capability.state,capability.checkpoint_id,capability.cause])) || (retryResult.transport && !recoveryDisconnected) || (retryResult.r2 && capability.can_confirm_origin!==true && capability.state!=='ready')))retryResult=null;
  if(retryPending?.key===key && retryPending.kind==='prepare')return {status:'Preparing recovery…',hint:rowActions.prepare.note};
  if(retryPending?.key===key && retryPending.kind==='convert')return {status:'Starting conversion…',hint:rowActions.convert.note};
  if(readmissionOf(row)?.queued_next===true)return null;  // K4: the existing queued and checking words
  if(retryResult?.key===key && retryResult.producer && (retryResult.warn || retryResult.status))return {status:retryResult.status,hint:retryResult.text,warn:!!retryResult.warn};
  if(capability.cause==='restart_unproven')return {status:'Stopped — restart Windows first',hint:"Windows hasn't restarted since this conversion ran. Restart it, then reopen the app.",warn:true,tip:'The app confirms the old conversion ended by checking that Windows restarted after it. Your confirmation is kept; Retry appears after the restart.'};
  if(['ready','isolated_retained'].includes(capability.state) && capability.can_retry===true && capability.basis==='boot_after_attempt')return {status:'Stopped — ready to retry',hint:deletionLine(capability)};
  if(capability.cause==='origin_unproved' && capability.can_confirm_origin===true)return {status:'Stopped — needs your confirmation',hint:"The app can't tell where this conversion ran."};
  if(capability.state==='prepare')return {status:'Stopped — recovery check needed',hint:"The app cannot confirm that this book's conversion process ended. Prepare recovery to save a checkpoint."};
  if(capability.state==='waiting_restart')return typeof capability.checkpoint_id==='string' && capability.checkpoint_id?{status:'Restart verification needed',hint:'Recovery checkpoint saved. Use Restart in Windows, then reopen Books Arranger and choose Retry so the app can verify the restart. Restarting only the app will not help. A Windows restart may still need another recovery check.'}:{status:'Recovery stays blocked',hint:'The saved recovery checkpoint is unavailable. Files are retained.',warn:true};
  if(capability.state==='ready' || capability.state==='isolated_retained')return {status:capability.can_retry?'Stopped — ready for a new attempt':'Recovery stays blocked',hint:capability.can_retry?'Old working files are kept. Retry starts a new attempt after checking the original sources.':capability.reason,warn:!capability.can_retry};
  if(capability.cause==='origin_unproved')return {status:'Recovery stays blocked',hint:'The saved information cannot establish where this conversion ran. All files are retained.'+(capability.reason?' '+capability.reason:''),warn:true};
  if(capability.cause==='startup_unavailable')return {status:'Recovery check unavailable',hint:"The app can't read when Windows started, so it can't confirm the old conversion ended. Files are kept.",warn:true};
  if(capability.cause==='binding_mismatch')return {status:'Recovery checkpoint does not match',hint:'This book changed or the checkpoint belongs to another computer. Files are retained; recovery stays blocked.'+(capability.reason?' '+capability.reason:''),warn:true};
  return {status:'Recovery stays blocked',hint:capability.reason || 'Files are retained; recovery stays blocked.',warn:true};
}
function updateProducerRecoverySurface(row){
  if(selectedRow?.path!==row.path)return;
  const shown=producerRecoveryText(row);if(!shown)return;
  setText('automatic-result-status',shown.status);setText('automatic-result-hint',shown.hint);$('automatic-result-hint').hidden=false;
}
function renderProducerRetained(row){
  const saved=row?.producer_recovery_retained,valid=saved?.schema==='books-producer-retention-v1' && Array.isArray(saved.attempts);
  const section=$('producer-retained');if(!section)return;
  section.hidden=!valid && producerRecoveryOf(row)?.state!=='isolated_retained';
  const removal=$('producer-retained-removal');if(removal)removal.hidden=!(valid && saved.attempts.some(item=>item?.removed_after_verification===true) || producerRecoveryOf(row)?.basis==='boot_after_attempt');
  setText('producer-retained-paths',valid?saved.attempts.map(item=>[item.path,item.attempt_id?'Attempt: '+item.attempt_id:'',item.reason].filter(value=>typeof value==='string' && value).join('\n')).join('\n\n'):'');
}
async function prepareProducerRecovery(row,origin=null){
  const capability=producerRecoveryOf(row),key=retryKey(row),job=row?.creation?.job;
  if(!key || !job || capability?.state!=='prepare' || capability.can_prepare!==true || retryPending || busy || ended || recoveryDisconnected || recoverySubmitting || automaticRequest!==null || bulkRunning() || releaseRun)return false;
  const focused=document.activeElement===(origin?.button || $('retry-job'));
  retryPending={key,kind:'prepare'};retryResult=null;busy=true;controls();updateProducerRecoverySurface(row);
  let fresh=row,acknowledged=false;
  try{
    const answer=await request('/api/audiobook/prepare-recovery',{job_id:job.job_id},PRESS_TIMEOUT),saved=answer?.producer_recovery;
    if(answer?.job_id!==job.job_id || answer.queued!==false || answer.outputs_changed!==false || saved?.schema!=='books-producer-recovery-capability-v1' || typeof saved.can_prepare!=='boolean' || typeof saved.can_retry!=='boolean' || !['prepare','waiting_restart','ready','isolated_retained','unsupported'].includes(saved.state) || (saved.state==='waiting_restart' && !(typeof saved.checkpoint_id==='string' && saved.checkpoint_id)))throw Object.assign(new Error('The recovery checkpoint response could not be verified.'),{httpStatus:502});
    fresh={...row,creation:{...row.creation,job:{...job,attention:{...job.attention,producer_recovery:saved}}}};
    rows=rows.map(item=>item.path===row.path?fresh:item);const entry=rowRetries.get(row.path);if(entry)entry.row=fresh;
    if(selectedRow?.path===row.path)selectedRow=fresh;
    acknowledged=saved.state==='waiting_restart' && typeof saved.checkpoint_id==='string' && !!saved.checkpoint_id;
    retryResult=acknowledged?{key,producer:true,snapshot:JSON.stringify([saved.state,saved.checkpoint_id,saved.cause]),warn:false,text:'Recovery checkpoint saved. Restart Windows, then choose Retry to verify.'}:null;
  }catch(error){
    retryResult={key,producer:true,snapshot:JSON.stringify([capability.state,capability.checkpoint_id,capability.cause]),transport:!error.httpStatus,warn:true,status:error.httpStatus?'Recovery checkpoint not saved':'Checkpoint status unknown',text:error.httpStatus?(error.message || 'The recovery checkpoint could not be saved.')+' Files are retained.':'Could not confirm the checkpoint. Reconnect to check its saved state.'};
    if(!error.httpStatus)refreshFailed(error);
  }finally{retryPending=null;busy=false;controls();updateProducerRecoverySurface(fresh);}
  if(acknowledged && focused){
    if(origin?.row)focusRowButton(row.path);
    else{$('automatic-result-status').setAttribute('tabindex','-1');$('automatic-result-status').focus?.({preventScroll:true});}
  }
  return acknowledged;
}
const STARTOVER_HELD_TIP="Set this failed job aside. Starts automatic processing if it isn't running. The book has a saved review, so automatic processing will hold it; \"Let the app handle it\" can then release it. Nothing is deleted.";
const CLEARS_FIRST={retry:['Clear the leftover working files, then check this book again and queue its audiobook job.','Clearing working files, then checking this book…',' Retry clears leftover working files first.'],
  repair:['Clear the leftover working files, patch the damage found in this book, then queue its audiobook job.','Clearing working files, then repairing this book…',' Repair clears leftover working files first.']};
const KEPT_HINT='Files kept at your choice.';
function keptGroup(attention){return attention?.group==='changed' || attention?.group==='audiobook';}
function rowAction(row){
  const job=row?.kind==='candidate'?row.creation?.job:null;
  // A held single-M4B book with a saved review and no job: "Let the app handle it" (O7), in every filter it shows in.
  if(!job)return row?.kind==='candidate' && releaseOf(row)?{...rowActions.release,data:{allowed:true,reason:''}}:null;
  if(attentionOf(row)?.group==='reacquire')return null;
  const savedRequest=readmissionOf(row);
  if(savedRequest?.state==='queued')return {...rowActions.queued,label:queuedNextText(savedRequest),data:{allowed:false,reason:queuedNextText(savedRequest)}};
  const destination=attentionOf(row)?.destination_review;
  if(destination && readmissionOf(row)?.queued_next===true)return {...rowActions.queued,data:{allowed:false,reason:queuedNextText(readmissionOf(row))}};
  if(destination){
    if(destination.state!=='needs_review' || destination.can_retry!==true || job.retry?.allowed!==true)return null;
    return {...rowActions.retry,ready:'Check the current sources, review and destination; queue a new job only if all checks pass.',note:'Checking the current sources, review and destination…',data:job.retry};
  }
  const recovery=producerRecoveryOf(row);
  if(recovery){
    if(recovery.state==='prepare' && recovery.can_prepare===true)return {...rowActions.prepare,data:{allowed:true,reason:recovery.reason}};
    if(recovery.state==='unsupported' && recovery.can_confirm_origin===true)return {...rowActions.convert,data:{allowed:true,reason:''}};
    if(['ready','isolated_retained'].includes(recovery.state) && recovery.can_retry===true && recovery.basis==='boot_after_attempt' && job.retry?.allowed===true)return {...rowActions.retry,ready:'Start a new conversion. When it is verified, the old working files and the original are deleted.',note:'Checking the original sources for a new attempt…',data:job.retry};
    if(['ready','isolated_retained'].includes(recovery.state) && recovery.can_retry===true && job.retry?.allowed===true)return {...rowActions.retry,ready:'Check the original sources and start a new attempt. Keep the old working files.',note:'Checking the original sources for a new attempt…',data:job.retry};
    return null;
  }
  // A damaged book shows Repair and never Retry (Retry would fail again on the same damage).
  // Once accepted, the request waits for its turn: the button reads "Queued" and cannot be pressed again.
  const queued=readmissionOf(row);
  if(queued?.queued_next===true)return {...rowActions.queued,data:{allowed:false,reason:queuedNextText(queued)}};
  if(!queued && pressedFor(row)?.state==='checking' && retryPending?.key!==retryKey(row))return {...rowActions.queued,label:'Checking…',pending:'Checking…',data:{allowed:false,reason:'Checking whether the press went through…'}};
  // A refusal that only an app update clears offers no control (no disabled ghost); the hint says why. A "review changed"
  // row offers Start over in the Retry slot, or the combined press when the book is known to hold for its saved review.
  const refusal=refusalCurrent(row),attention=attentionOf(row);
  if(refusal && refusalFix(refusal)==='review'){
    if(attention?.startover==='manual_draft' && attention.release_ok===true)return {...rowActions.combined,data:{allowed:true,reason:''}};
    return {...rowActions.startover,ready:attention?.startover==='manual_draft'?STARTOVER_HELD_TIP:rowActions.startover.ready,data:{allowed:true,reason:''}};
  }
  if(refusal && refusalFix(refusal)==='update')return null;
  const [kind,data]=keptGroup(attention)?['keep',job.keep]:attention?.group==='repair' || refusal?.kind==='repair'?['repair',job.repair]:['retry',job.retry];
  if(!data || typeof data!=='object' || typeof data.allowed!=='boolean')return null;
  if(kind==='retry' && attention?.remedy?.kind==='tag_repair')return {...rowActions.retry,ready:'Check this MP3 again with this app version and queue its audiobook job.',data};
  // Retry and Repair clear leftover working files first (decisions A and O10): their tooltip and press note say so.
  const clears=workingOf(row)?.state==='cleanable' && data.allowed===true && CLEARS_FIRST[kind];
  return clears?{...rowActions[kind],ready:clears[0],note:clears[1],data}:{...rowActions[kind],data};
}
function releaseOf(row){return row?.release?.allowed===true && !row?.creation?.job;}
function restartOf(row){const value=row?.restart;return value && typeof value==='object' && typeof value.state==='string'?value:null;}
function workingOf(row){if(producerRecoveryOf(row))return null;const value=attentionOf(row)?.working;return value && typeof value==='object' && (value.state==='cleanable' || value.state==='blocked')?value:null;}
function sizeText(bytes){const units=['B','KB','MB','GB','TB'];let index=0;while(index<units.length-1 && bytes>=1024**(index+1))index++;const scaled=bytes/1024**index;return scaled.toLocaleString(undefined,{maximumFractionDigits:scaled<10 && index?1:0})+' '+units[index];}
function clearTooltip(row){const bytes=workingOf(row)?.bytes;return 'Delete the working files an earlier attempt left behind. Originals are not touched.'+(Number.isSafeInteger(bytes) && bytes>0?` Frees about ${sizeText(bytes)}.`:'');}
// The hint text, plus a muted clause (the "clears first" sentence) in its own span; rebuilt only when it changes.
function setHint(element,text,clause='',warn=false,lines=null){
  const extra=Array.isArray(lines)?lines:[],key=JSON.stringify([text || '',clause || '',extra]);
  if(element.dataset?.hint!==key){
    element.replaceChildren?.();element.textContent=text || '';if(clause)element.append(node('span',clause,'hint-clause'));
    // A queued delete's partial outcome (Judy 1.6): each file on its own line, its cause muted below it.
    for(const line of extra)element.append(node('span',line.text,'hint-line'+(line.kind==='path'?' path':line.kind==='muted'?' hint-clause':'')));
    if(element.dataset)element.dataset.hint=key;
  }
  element.classList?.toggle?.('retry-refused',!!warn);
}
// Retry and Repair of an M4B book are accepted at once and run right after the current book (m4b_readmission).
function readmissionOf(row){
  const job=row?.creation?.job,value=job?.readmission || job?.attention?.readmission;
  const tracked=bulkRun()?.progress?.schema==='books-retry-progress-v1'?bulkRun().progress.targets?.find(item=>item.job_id===job?.job_id):null;
  if(tracked && ['waiting','checking'].includes(tracked.state))return {accepted:true,queued_next:true,state:'queued',parent_job_id:job.job_id,child_job_id:null};
  if(value && typeof value==='object')return value;
  const memory=pressedFor(row);
  return memory?.state==='queued'?{accepted:true,queued_next:true,position:memory.position,kind:memory.kind,remembered:true}:null;
}
const QUEUED_HINT='The book is checked again before it runs.';
function pressedFor(row){
  const key=retryKey(row),memory=key?pressed.get(key):null;if(!memory)return null;
  if(Date.now()-memory.at>PRESS_MEMORY){pressed.delete(key);return null;}
  return memory;
}
function remember(key,state,kind,position){if(kind==='retry' || kind==='repair')pressed.set(key,{state,kind,at:Date.now(),position:Number.isInteger(position) && position>0?position:1});}
function queuedNextText(value){
  if(value?.state==='queued' || value?.child_job_id===null)return state?.audiobook_jobs?.retry_checks?.worker?.state==='checking' && state.audiobook_jobs.retry_checks.worker.job_id===value?.parent_job_id?'Checking retry':'Waiting for retry checks';
  const running=!!state?.audiobook_jobs?.current_job_id,position=Number.isInteger(value?.position) && value.position>0?value.position:1,ahead=(running?1:0)+position-1;
  return ahead===0?'Queued — runs next':ahead===1 && running?'Queued — runs after the current book':`Queued — runs after ${ahead.toLocaleString()} books`;
}
function queuedNext(row,result){
  const job={...row.creation.job,readmission:{accepted:true,queued_next:true,position:result.position,kind:result.kind,state:result.state,child_job_id:result.child_job_id,parent_job_id:result.parent_job_id}};delete job.retry;delete job.repair;
  return {...row,creation:{...row.creation,job}};
}
function bulkRun(){const run=state?.audiobook_jobs?.retry_all;return run && typeof run==='object' && typeof run.id==='string'?run:null;}
function bulkRunning(){return bulkRun()?.state==='running';}
function updateRetry(){
  const block=$('retry-block'),button=$('retry-job'),note=$('retry-note');if(!block || !button || !note)return;
  const row=selectedRow,key=retryKey(row),action=key?rowAction(row):null,retry=action?.data;
  if(retryResult && retryResult.key!==key)retryResult=null;
  if(restartResult && restartResult.id!==row?.id)restartResult=null;
  const qmode=key?retryMode(row):null,queueMode=['sending','queued','running'].includes(qmode);
  const pending=!!key && retryPending?.key===key && retryPending.kind!=='clear',copy=queueMode?retryQueueCopy(row):pending?{...rowActions[retryPending.kind],note:retryPending.note || rowActions[retryPending.kind].note}:action;
  const clear=$('clear-working'),clearing=clearPending(row),cleanable=workingOf(row)?.state==='cleanable';
  if(clear){const gone=!clearing && !cleanable,lostClear=gone && !clear.hidden && document.activeElement===clear;clear.hidden=gone;if(!gone)updateClearButton(clear,row);if(lostClear)$('details-heading').focus?.({preventScroll:true});}
  const producer=producerRecoveryOf(row),shown=pending || queueMode || !!action,noted=!pending && !action && restartResult?restartResult:null;
  const lost=!shown && !button.hidden && document.activeElement===button;
  block.hidden=!shown && !noted && !clearing && !cleanable && !producer;button.hidden=!shown;
  updateQueueCancel($('retry-cancel'),row,['retry','repair']);
  if(!shown){
    // The press moved the book on (Started over): its result stays in the note; the button is gone.
    const text=producer?producerRecoveryText(row)?.hint:noted?noted.text:clearing?'Clearing working files…':retryResult?retryResult.text:'';
    if(note.textContent!==text)note.textContent=text;note.hidden=!text;note.classList?.toggle?.('retry-refused',!!(noted?noted.warn:retryResult && retryResult.warn!==false));
    if(lost && !producer)nextRowButton(rowButtons(selectedPath))?.focus?.({preventScroll:true});return;}
  const mode=qmode;
  const reason=typeof retry?.reason==='string' && retry.reason.trim()?retry.reason:copy.label+' is unavailable. Refresh and check again.';
  const held=key?laterFor(key):null;  // ruling 35: held by the page until it is free
  let label=mode==='pending'?copy.pending:mode==='later'?'Queued':copy.label,title={offline:'Local server unavailable.',pending:retryPending?.checking?'Checking…':copy.note,later:held?laterLine(held):'',sibling:QUEUE_SIBLING,blocked:retryBlockedTip(copy),unavailable:reason,ready:copy.ready}[mode];
  let aria=(label==='Convert…'?'Convert':label)+': '+((copy.kind==='prepare'?row.title_clue || row.review?.title:row.review?.title || row.title_clue) || 'Book');
  if(queueMode){const face=retryQueueFace(row,mode);label=face.label;title=face.title;aria=face.aria;}
  const result=mode!=='pending' && !queueMode && !clearing && retryResult,queued=queueMode?queueHint(row) || copy.note:null,later=!queueMode && !result?queueNoteFor(row):null;
  const text=clearing?ladderNote('Clearing working files…',retryPending?.at):queued || (result?retryResult.text:later?later.text:mode==='ready' || mode==='blocked'?'':mode==='pending'?ladderNote(title,retryPending?.at):title);
  if(button.textContent!==label)button.textContent=label;
  if(button.title!==title)button.title=title;
  button.setAttribute('aria-label',aria);
  // Pending, queued and running keep keyboard focus: aria-disabled with a disabled look, never the disabled attribute.
  const inert=mode==='pending' || queueMode || mode==='sibling' || mode==='later';
  if(inert)button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
  button.disabled=!inert && mode!=='ready' && mode!=='blocked';
  if(note.textContent!==text)note.textContent=text;
  note.hidden=!text;note.classList.toggle('retry-refused',!!result && retryResult.warn!==false || !!later?.warn);
}
// The Retry slot while a press is queued (Judy 1.4): its copy (Retry or Repair) and its faces.
function retryQueueCopy(row){const item=queuedFor(row) || (queueRunning(row)?queueState.running:null) || {action:queuePresses.get(row?.id)?.action};return rowActions[item?.action==='repair'?'repair':'retry'];}
function retryQueueFace(row,mode){
  const copy=retryQueueCopy(row),title=queueTitle(row);
  if(mode==='queued')return {label:`${copy.label} queued`,title:`${copy.label} is queued. It starts when ${queueP(queueBlocker(queuedFor(row)))} finishes.`,aria:`${copy.label} queued: ${title}`};
  return {label:copy.pending,title:copy.note,aria:`${copy.pending}: ${title}`};
}
function retryBlockedTip(copy){const kind=pageBlocker();return `Queue this ${String(copy?.label || 'Retry').toLowerCase()}. ${queueS(kind)}; it starts when ${queueP(kind)} finishes.`;}
function keptByChoice(row){const job={...row.creation.job,kept:true};delete job.attention;delete job.keep;return {...row,creation:{...row.creation,job}};}
function queuedByRetry(row){const job={...row.creation.job,state:'Queued',stage:'queued',reason:''};delete job.retry;delete job.repair;delete job.attention;return {...row,status:'Queued',creation:{...row.creation,status:'Queued',job}};}
async function retryFromRow(row,button=null){
  if(rowAction(row)?.kind==='prepare')return prepareProducerRecovery(row,{row:true,path:row.path,button});
  // Select without scrolling, then the same request as the details-panel Retry.
  if(selectedPath!==row.path)select(row,true);
  const index=rows.findIndex(item=>item.path===row.path);
  await retryJob({row:true,path:row.path,index,button});
}
async function clearFromRow(row,button){
  if(selectedPath!==row.path)select(row,true);
  await clearWorking({row:true,path:row.path,index:rows.findIndex(item=>item.path===row.path),button});
}
// Focus never falls to the page after a press moved the book on: the same row's first remaining button (or its Retry).
function focusRowButton(path,preferRetry=false){
  const buttons=rowButtons(path),list=[...(buttons?.children || [])].filter(item=>item.type==='button' && !item.hidden && !item.disabled);
  (preferRetry && list.find(item=>item.classList?.contains?.('row-retry')) || list[0])?.focus?.({preventScroll:true});
}
function retryMode(row){
  const key=retryKey(row),action=key?rowAction(row):null,retry=action?.data;
  if(ended || recoveryDisconnected && !desktopMode())return 'offline';
  if(key && retryPending?.key===key && retryPending.kind!=='clear')return 'pending';
  // Queued Retry and Repair (Judy 1.3, 1.4): on its way, waiting in the engine's queue, or running there.
  if(queuePresses.has(row?.id))return 'sending';
  if(queueRunning(row) && !queueRunning(row,'delete'))return 'running';
  if(queuedFor(row) && !queuedFor(row,'delete'))return 'queued';
  if(deleteQueued(row))return 'sibling';
  const queueable=action?.kind==='retry' || action?.kind==='repair';
  if(key && laterFor(key))return 'later';  // ruling 35: held by the page until it is free, with Cancel
  if(retry?.allowed!==true)return 'unavailable';
  // Blocked: enabled, and a press is queued (1.1). Only the server's "not allowed" disables Retry and Repair.
  return queueable && pageBlocker()?'blocked':'ready';
}
// Clear working files is never disabled: a press while another request runs is answered in the note.
function clearPending(row){const key=retryKey(row);return !!key && retryPending?.key===key && retryPending.kind==='clear';}
// The status cell's own text, beside its hint: changed in place, so the row is not rebuilt under focus.
function statusInPlace(cell,text){const first=cell?.firstChild;if(first && first.nodeType===3 && first.nodeValue!==text)first.nodeValue=text;}
// Focus never falls to the page: the first remaining button of the same row (RefusedRetry spec section 3).
function nextRowButton(buttons,except){return [...(buttons?.children || [])].find(item=>item!==except && item.type==='button' && !item.hidden && !item.disabled && !item.classList?.contains?.('row-retry')) || null;}
function rowButtons(path){const tr=[...($('inventory').children || [])].find(item=>item.dataset?.path===path),cell=tr?.children?.[tr.children.length-1];return cell?.children?.[0] || null;}
function updateRowRetries(){
  for(const entry of rowRetries.values()){
    const row=entry.row,shown=rowState(row),key=retryKey(row),mode=entry.button?retryMode(row):null,action=rowAction(row),retry=action?.data;
    const queueMode=['sending','queued','running'].includes(mode);
    const copy=queueMode?retryQueueCopy(row):retryPending?.key===key && retryPending.kind!=='clear'?{...rowActions[retryPending.kind],note:retryPending.note || rowActions[retryPending.kind].note}:action || rowActions.retry;
    let hint=shown?shown.hint:'',warn=!!shown?.warn,clause=shown?.clause || '',lines=null;
    if(mode==='unavailable' && action?.kind!=='queued' && typeof retry?.reason==='string' && retry.reason){hint=retry.reason;clause='';}
    if(mode==='pending'){hint=retryPending?.checking?'Checking…':ladderNote(copy.note,retryPending?.at);clause='';warn=false;}
    if(clearPending(row)){hint=ladderNote('Clearing working files…',retryPending?.at);clause='';warn=false;}
    if(!shown && row.creation?.job?.kept===true && mode!=='pending')hint=KEPT_HINT;
    if(retryResult && retryResult.key===key && !retryResult.panelOnly && mode!=='pending' && !queueMode && !clearPending(row)){hint=retryResult.text;warn=retryResult.warn!==false;clause='';}
    else if(!queueMode){const later=queueNoteFor(row);if(later){hint=later.text;warn=later.warn;clause='';}}  // a queued action's outcome (1.6)
    const deleted=deleteNotes.get(row.id);if(deleted){hint=deleted.text;warn=deleted.warn;clause='';lines=deleted.lines;}  // Delete book's outcome (ruling 23)
    const queued=queueHint(row);if(queued!==null || mode==='sending'){hint=queued ?? ladderNote(copy.note,queuePresses.get(row.id)?.at);warn=false;clause='';lines=null;}  // the queued line replaces the hint (1.3)
    const later=key?laterFor(key):null;if(later){hint=laterLine(later);warn=false;clause='';lines=null;}  // ruling 35: held by the page, with Cancel
    setHint(entry.hint,hint,clause,warn,lines);
    statusInPlace(entry.cell,candidateStatus(row));if(attentionOf(row) && entry.cell && entry.cell.title!==cellTip(row))entry.cell.title=cellTip(row);
    if(deleted?.done){if(entry.button)entry.button.hidden=true;if(entry.clear)entry.clear.hidden=true;continue;}  // deleted: its buttons go
    if(entry.clear)updateClearButton(entry.clear,row);
    updateQueueCancel(entry.cancel,row,['retry','repair']);
    if(entry.cancel && later){entry.cancel.hidden=false;const label='Cancel '+lowerFirst(laterWord(later.kind));if(entry.cancel.textContent!==label)entry.cancel.textContent=label;entry.cancel.title=`Take this ${lowerFirst(laterWord(later.kind))} out of the queue. Nothing was started.`;entry.cancel.setAttribute('aria-label',label+': '+queueTitle(row));entry.cancel.removeAttribute('aria-disabled');}
    if(!entry.button)continue;
    const gone=!action && mode!=='pending' && !queueMode,hadFocus=gone && document.activeElement===entry.button;
    entry.button.hidden=gone;if(hadFocus && !producerRecoveryOf(row))nextRowButton(entry.button.parentElement,entry.button)?.focus?.({preventScroll:true});
    if(entry.button.hidden)continue;
    let label=mode==='pending'?copy.pending:mode==='later'?'Queued':copy.label,title={offline:'Local server unavailable.',pending:copy.note,later:later?laterLine(later):'',sibling:QUEUE_SIBLING,blocked:retryBlockedTip(copy),unavailable:retry?.reason || copy.label+' is unavailable. Refresh and check again.',ready:copy.ready}[mode];
    let aria=(label==='Convert…'?'Convert':label)+': '+(row.title_clue || row.review?.title || 'Book');
    if(queueMode){const face=retryQueueFace(row,mode);label=face.label;title=face.title;aria=face.aria;}
    if(entry.button.textContent!==label)entry.button.textContent=label;
    if(entry.button.title!==title)entry.button.title=title;
    entry.button.setAttribute('aria-label',aria);
    const inert=mode==='pending' || queueMode || mode==='sibling' || mode==='later';
    if(inert)entry.button.setAttribute('aria-disabled','true');else entry.button.removeAttribute('aria-disabled');
    entry.button.disabled=!inert && mode!=='ready' && mode!=='blocked';
  }
}
function updateClearButton(button,row){
  const pending=clearPending(row),gone=!pending && workingOf(row)?.state!=='cleanable',hadFocus=gone && document.activeElement===button;
  button.hidden=gone;if(hadFocus)(nextRowButton(button.parentElement,button) || button.parentElement?.children?.[0])?.focus?.({preventScroll:true});
  if(gone)return;
  const label=pending?'Clearing…':'Clear working files';if(button.textContent!==label)button.textContent=label;
  const title=pending?'Clearing working files…':clearTooltip(row);if(button.title!==title)button.title=title;
  button.setAttribute('aria-label',label+': '+(row.title_clue || row.review?.title || 'Book'));
  if(pending)button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
  button.disabled=false;
}
// The 15 s abort is gone (Judy 0.22.1, 4.3): a slow answer is a busy app, not a lost one. A press waits for its answer, its
// pending face and the ladder say so, and only ten minutes without one end it with the "not confirmed" line.
const PRESS_TIMEOUT=600000;
// Futaba's 0.22.0 QA, M-4: Approve checks every file before it answers (probes, hashes, cover, track review): 24.5 s for
// a 77-file book, longer for real files. At PRESS_TIMEOUT the page said "Connection interrupted" while the server went on
// and queued the book, and the re-enabled button invited a second press (409). Approve waits for its answer; its pending
// face and aria-disabled button stay until then, so it cannot be pressed twice. A server gone away still ends the request
// at once (a closed connection), and a request still unanswered after ten minutes ends like a lost connection.
const APPROVE_TIMEOUT=600000;
// After a press with no reply: re-read the book from the server. Returns its queued state (it landed),
// false (the server answered and the book is not queued) or null (still no answer).
async function pressLanded(row,jobId){
  for(let attempt=0;attempt<3 && !ended;attempt++){
    try{
      const page=await request(`/api/inventory?library=Audiobooks&offset=0&search=${encodeURIComponent(row.title_clue || '')}&view=candidates&status=all`);
      const fresh=(page.rows || []).find(item=>item.id===row.id);if(!fresh)return false;
      const job=fresh.creation?.job || {},queued=job.readmission || job.attention?.readmission;
      if(job.kept===true)return {kept:true};
      if(queued?.queued_next===true)return {...queued,queued_next:true};
      if(job.job_id && (job.job_id!==jobId || job.state==='Queued' || job.state==='Creating'))return {queued_next:false,requeued:true};
      return false;
    }catch(error){if(error.httpStatus && error.httpStatus!==503)return false;}
    await new Promise(resolve=>setTimeout(resolve,1500));
  }
  return null;
}
async function retryJob(origin=null){
  const row=selectedRow,key=retryKey(row),job=key?row.creation.job:null,action=key?rowAction(row):null;
  if(!key || !action || ended || action.data.allowed!==true)return;
  // Retry and Repair while another operation runs are queued by the engine (Judy 1.1); the press never waits here.
  const queueable=action.kind==='retry' || action.kind==='repair',mode=retryMode(row);
  if(queueable && (mode==='blocked' || mode==='ready' && pressBusy()))return queuePress(row,action,origin);
  if(mode==='later')return;
  // Ruling 35: another press of this page never refuses this one; it waits for it (pressLater) and runs then.
  if(mode==='ready' && !recoveryDisconnected && pressBusy()){const path=row.path;pressLater(key,action.kind,queueTitle(row),()=>{const fresh=rows.find(item=>item.path===path);if(fresh)return retryFromRow(fresh,origin?.button || null);});return;}
  if(mode!=='ready' || retryPending || busy || recoveryDisconnected || recoverySubmitting || automaticRequest!==null || bulkRunning() || releaseRun || $('retry-job').disabled)return;
  dropQueueNote(row.id);
  if(action.kind==='prepare')return prepareProducerRecovery(row,origin);
  if(action.kind==='convert'){openConvertDialog(row,origin);return false;}
  if(['startover','combined','release'].includes(action.kind)){
    // Discarding a saved review deletes hand edits: one confirmation first (follow-up 3, section 4.4; follow-up 4, 3.3).
    if(action.confirm){openDiscardDialog(action.kind,[row],()=>restartPress(row,action,origin),origin?.button || $('retry-job'));return false;}
    return restartPress(row,action,origin);
  }
  retryPending={key,kind:action.kind,note:action.note,at:Date.now()};retryResult=null;busy=true;remember(key,'checking',action.kind);controls();
  let succeeded=false;
  let answer=null,refreshed=null;
  try{answer=await request(action.endpoint,{library:'Audiobooks',id:row.id,revision:row.revision,job_id:job.job_id,...(queueable?{queue:true,title:queueTitle(row)}:{})},PRESS_TIMEOUT);succeeded=true;}
  catch(error){
    if(error.httpStatus){pressed.delete(key);refreshed=freshRow(error.body?.row,row);retryResult=error.body?.cause==='origin_unconfirmed'?{key,producer:true,r2:true,status:'Stopped — needs your confirmation',text:'No confirmation is saved for this book.'}:{key:retryKey(refreshed || row),text:error.message || action.refused,warn:true};if(error.httpStatus===409)retryEpoch++;}
    else{
      // No reply in time: the press may still have landed. Check the book's queued state on the server
      // before saying anything; never show a scary error and re-enable a button for a request that worked.
      retryPending={key,kind:action.kind,checking:true};controls();
      const landed=await pressLanded(row,job.job_id);
      if(landed){succeeded=true;answer=landed;}
      else if(landed===false){pressed.delete(key);retryResult={key,text:action.label+' did not go through. Try again.',warn:true};}
      else retryResult={key,text:lostLine(),warn:true};  // stays "Checking…": the press may have landed
    }
  }
  if(succeeded && answer?.queued===true){
    // Something blocked it at the engine (a scan, a retry run): queued; the row says what it waits for (Judy 1.3).
    pressed.delete(key);retryPending=null;busy=false;queueAccepted(row,action.kind,answer);controls();
    const handed=document.activeElement;
    if(!ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
    controls();
    // The row was rebuilt by the list read: focus stays on its face ("Retry queued", aria-disabled keeps it).
    if(origin?.row && (document.activeElement===handed || document.activeElement===document.body || !document.activeElement))rowRetries.get(row.path)?.button?.focus?.({preventScroll:true});
    return true;
  }
  if(succeeded)remember(key,'queued',action.kind,answer?.position);
  // The book leaves this filter: the strip keeps a line saying what Repair will patch.
  if(succeeded && action.kind==='repair' && filters[view]==='output_attention')stripNote='Repair queued: '+damageHint(attentionOf(row));
  // v0.16.12: a note in place says which book was queued and when it runs.
  else if(succeeded && action.kind==='retry')stripNote=`${row.title_clue || row.review?.title || 'The book'} queued — ${queuedNextText({position:answer?.position}).replace(/^Queued — /,'')}`;
  const focused=document.activeElement===$('retry-job');
  retryPending=null;busy=false;
  // A clear-first that did not finish answers with the book's refreshed row, as Clear does: the panel and the row show
  // the state after the press now, never the Retry and Clear of the state before it.
  if(refreshed)placeRow(row,refreshed,origin);
  if(succeeded){
    // The server requeued the job: show it as queued now, and ignore book lists requested before this answer.
    retryEpoch++;const queued=action.kind==='keep'?keptByChoice(row):answer?.queued_next===true?queuedNext(row,answer):queuedByRetry(row);rows=rows.map(item=>item.path===row.path?queued:item);
    // The book stays where it was, showing Queued, until the list changes: it never vanishes under the pointer.
    if(action.kind!=='keep')heldRow={path:row.path,index:origin?.index ?? rows.findIndex(item=>item.path===row.path),context:listContext(),row:queued,until:Date.now()+PRESS_MEMORY};
    const entry=action.kind==='keep'?rowRetries.get(row.path):null;if(entry)entry.row=queued;
    // The block leaves the page: focus moves to the panel heading, never into the automatic result.
    if(focused && retryKey(selectedRow)===key)$('details-heading').focus?.({preventScroll:true});
    if(selectedRow?.path===row.path)select(queued,false);
  }
  controls();
  if(!recoveryDisconnected && !ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  controls();
  if(origin?.row && succeeded){
    // Focus stays on the book that was pressed; it never lands on a neighbour's Retry (v0.16.12).
    const rowsNow=$('inventory').children,same=[...rowsNow].find(tr=>tr.dataset?.path===origin.path);
    (same || (!$('attention-groups').hidden && stripNote?$('retry-all-status'):$('filter'))).focus?.({preventScroll:true});
  }
  return succeeded;
}
// A Retry or Repair pressed while the page is busy (Judy 1.1): no global busy, so other presses go on. The engine queues it,
// or runs it at once when nothing blocks it there; either way the row shows the answer.
async function queuePress(row,action,origin){
  const id=row.id,key=retryKey(row);if(queuePresses.has(id) || ended)return false;
  queuePresses.set(id,{action:action.kind,at:Date.now()});dropQueueNote(id);if(retryResult?.key===key)retryResult=null;controls();
  const button=origin?.button || null;
  let answer=null,failure=null;
  try{answer=await request(action.endpoint,{library:'Audiobooks',id,revision:row.revision,job_id:row.creation.job.job_id,queue:true,title:queueTitle(row)},APPROVE_TIMEOUT);}catch(error){failure=error;}
  queuePresses.delete(id);
  if(answer?.queued===true)queueAccepted(row,action.kind,answer);
  else if(answer)retryLanded(row,action,answer,origin);
  else if(failure?.httpStatus){if(failure.httpStatus===409)retryEpoch++;const fresh=freshRow(failure.body?.row,row);if(fresh)placeRow(row,fresh,origin);retryResult={key:retryKey(fresh || row),text:failure.message || action.refused,warn:true};}
  else retryResult={key,text:lostLine(),warn:true};
  controls();
  const handed=document.activeElement;
  if(!ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  controls();
  // A row press keeps focus on the row's face after the list read rebuilt it; nothing else moves (1.7).
  // In a browser the rebuilt row's old button is gone and focus falls to the page body: it comes back to the new face.
  const lost=document.activeElement===handed || document.activeElement===document.body || !document.activeElement;
  if(origin?.row && button && handed===button && lost)rowRetries.get(row.path)?.button?.focus?.({preventScroll:true});
  return !!answer;
}
// A queued press that ran at once: the row shows Queued now (v0.16.12) and the strip names the book, as after Retry.
function retryLanded(row,action,answer,origin){
  const key=retryKey(row);remember(key,'queued',action.kind,answer?.position);
  if(action.kind==='repair' && filters[view]==='output_attention')stripNote='Repair queued: '+damageHint(attentionOf(row));
  else stripNote=`${row.title_clue || row.review?.title || 'The book'} queued — ${queuedNextText({position:answer?.position}).replace(/^Queued — /,'')}`;
  retryEpoch++;const queued=answer?.queued_next===true?queuedNext(row,answer):queuedByRetry(row);rows=rows.map(item=>item.path===row.path?queued:item);
  heldRow={path:row.path,index:origin?.index ?? rows.findIndex(item=>item.path===row.path),context:listContext(),row:queued,until:Date.now()+PRESS_MEMORY};
  const entry=rowRetries.get(row.path);if(entry)entry.row=queued;
  if(selectedRow?.path===row.path)select(queued,false);
}
const PASS_PENDING={conversion:'Audiobook conversion is running, so automatic processing will start by itself when it finishes or is paused.',
  scan:'A library scan is running, so automatic processing will start by itself when the scan ends or is stopped.',
  stopping:'Automatic processing is stopping, so it will start again by itself once it has stopped.'};
// The panel note after Start over, the combined press or the release (follow-up 3, sections 1.3 and 4.5; follow-up 4,
// sections 1.2 and 3.4). The server's pass answer chooses the sentence.
function restartNote(kind,answer){
  const lead={startover:'Started over.',release:'Review discarded.',combined:'Started over. Review discarded.'}[kind],pass=answer?.pass,find=' Find it under Status: Started over.';
  // The button is promised only when the server expects it (follow-up 4, section 2: a single M4B, a saved review, no
  // editing lease); a multi-file or leased book never gets it, so the sentence ends at "…because it has a saved review."
  const release=answer?.row?.restart?.release_expected===true;
  const held=kind==='startover' && answer?.outcome==='manual_draft'?' Automatic processing will then hold this book because it has a saved review'+(release?'; Let the app handle it appears once it is held.':'.'):'';
  if(pass?.action==='blocked')return {text:`${kind==='release'?'Review discarded':kind==='combined'?'Started over. Review discarded':'Started over'}, but automatic processing did not start.${pass.reason?' '+pass.reason:''}`,warn:true};
  if(pass?.action==='running' && pass.visit==='next_run')return {text:`${lead} Automatic processing is running but has already passed this book. Press Start automatic processing above after it finishes.`+(kind==='release'?'':held+find),warn:true};
  const middle=pass?.action==='started'?'Automatic processing has started. It scans the library first, so this may take a while.':pass?.action==='continued'?'Automatic processing continued where it paused.':
    pass?.action==='running'?'Automatic processing is running and will reach this book.':pass?.action==='pending' && PASS_PENDING[pass.pending_kind]?PASS_PENDING[pass.pending_kind]:'The book goes back to automatic processing.';
  return {text:`${lead} ${middle}${held}${find}`,warn:!!held};
}
// The rest of ruling 35 (ruling 37): busy is held and sent again (never "try again in a moment"); a file held open is tried
// again a few times, then its sentence says what to do; a file the app can't prove it made says why and where (S10).
const CLEAR_FAILURE={busy:'Clear working files queued. It runs when the app is free.',changed:"This book's status changed. Check the updated status above.",
  not_safe:"Some working files weren't cleared. The app keeps any file it can't confirm is safe to delete.",file_problem:"Some working files weren't cleared: another program, often an antivirus scan, still has a file open. Wait a minute or close that program, then press Clear working files again.",
  unknown:"Working files weren't cleared. Select the row to read why."};
const CLEAR_TRIES=6;  // a file held open: tried again every 10 s for a minute before its sentence shows
// S5: each Start over and release cause in its own words; closing is the real refusal, busy is held and sent again.
// Judy 14.6: two sentences at most; the closing refusal names the press and when to press it again.
const RESTART_CLOSING={startover:'Books Arranger is closing. Start over after it restarts.',combined:'Books Arranger is closing. Start over after it restarts.',
  release:'Books Arranger is closing. Let the app handle it after it restarts.'};
// The words for a refused press come from its typed cause, never from the server's English.
function refusedText(kind,error){
  const cause=error?.body?.cause,changed="This book's status changed. Check the updated status above.",editing='This book is being edited. Finish editing, then try again.';
  const said=typeof error?.body?.error==='string' && error.body.error.trim()?error.body.error.trim():'';
  if(kind==='clear')return cause==='not_safe' && said?said:CLEAR_FAILURE[cause] || said || CLEAR_FAILURE.unknown;  // S10: the server names why and where
  if(cause==='changed')return changed;
  if(cause==='editing')return editing;
  if(cause==='closing')return RESTART_CLOSING[kind] || RESTART_CLOSING.startover;
  if(cause==='busy')return `${laterWord(kind)} queued. It runs when the app is free.`;  // held and sent again (restartPress); Judy 14.6
  return said || (kind==='release'?"The review wasn't discarded. Select the row to read why.":'Start over did not finish. Select the row to read why.');
}
function freshRow(value,row){return value && typeof value==='object' && typeof value.id==='string'?{...value,path:value.id,kind:'candidate',library:row.library || 'Audiobooks'}:null;}
function placeRow(row,fresh,origin){
  rows=rows.map(item=>item.path===row.path?fresh:item);
  // The book stays where it was until the list changes; it never vanishes under the pointer.
  heldRow={path:row.path,index:origin?.index ?? rows.findIndex(item=>item.path===row.path),context:listContext(),row:fresh,until:Date.now()+PRESS_MEMORY};
  const entry=rowRetries.get(row.path);if(entry)entry.row=fresh;
  if(selectedRow?.path===row.path)select(fresh,false);
}
async function restartPress(row,action,origin){
  const key=retryKey(row);if(ended || recoveryDisconnected)return false;
  if(retryPending || busy){const path=row.path;pressLater(key,action.kind,queueTitle(row),()=>{const fresh=rows.find(item=>item.path===path);if(fresh)return restartPress(fresh,action,origin);});return false;}
  const body=action.kind==='release'?{library:'Audiobooks',id:row.id,revision:row.revision}:{library:'Audiobooks',id:row.id,revision:row.revision,job_id:row.creation.job.job_id,...(action.kind==='combined'?{discard_review:true}:{})};
  retryPending={key,kind:action.kind,at:Date.now()};retryResult=null;restartResult=null;busy=true;controls();
  let answer=null,failure=null;
  try{answer=await request(action.endpoint,body,PRESS_TIMEOUT);}catch(error){failure=error;}
  const focused=document.activeElement===$('retry-job') || document.activeElement===origin?.button;
  retryPending=null;busy=false;
  if(failure?.httpStatus===409 && failure.body?.cause==='busy'){
    // The rest of ruling 35 (ruling 37): the catalog was still busy after the engine's own 30 s of tries. Never "try again in a
    // moment": the press is held and sent again in 5 s, every check again then; the row shows it queued, with Cancel.
    const path=row.path;holdAgain(key,action.kind,queueTitle(row),()=>{const fresh=rows.find(item=>item.path===path);if(fresh)return restartPress(fresh,action,origin);},'catalog',5);
    controls();return false;
  }
  if(answer){
    retryEpoch++;
    // The fresh pass state from the answer, as after Start: the top line and the hints do not wait for the next poll.
    if(answer.automatic_processing && state)state={...state,automatic_processing:answer.automatic_processing};
    const fresh=freshRow(answer.row,row) || {...row,release:undefined,restart:{state:'waiting',kind:action.kind==='release'?'release':'start_over'},creation:{...row.creation,job:null}};
    restartResult={id:row.id,...restartNote(action.kind,answer)};placeRow(row,fresh,origin);renderAutomatic();
  }else if(failure?.httpStatus){
    if(failure.httpStatus===409)retryEpoch++;
    const fresh=freshRow(failure.body?.row,row);if(fresh)placeRow(row,fresh,origin);
    retryResult={key:retryKey(fresh || row),text:refusedText(action.kind,failure),warn:true};
    if(!retryKey(fresh || row) || retryKey(fresh || row)!==key)restartResult={id:row.id,text:retryResult.text,warn:true};
  }else{retryResult={key,text:lostLine(action.kind==='release' || action.kind==='combined'?'discard':'press'),warn:true};refreshFailed(failure);}
  controls();
  if(!recoveryDisconnected && !ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  controls();
  if(answer && focused){if(origin?.row)focusRowButton(row.path);else $('details-heading').focus?.({preventScroll:true});}
  return !!answer;
}
// Clear working files (decision B). No confirmation: the files are the app's own copies and the server deletes only what
// its verified disposal proves. A press while another request runs is answered in the note; the button never disables.
async function clearWorking(origin=null,target=null){
  const row=target || selectedRow,key=retryKey(row),job=row?.creation?.job;
  if(!key || !job || workingOf(row)?.state!=='cleanable' || clearPending(row))return false;
  if(ended || recoveryDisconnected){retryResult={key,text:'Local server unavailable.',warn:true};controls();return false;}
  if(retryPending || busy || recoverySubmitting || automaticRequest!==null || bulkRunning() || releaseRun){
    // Ruling 35: never "Another operation is in progress"; it waits for the current press and runs then.
    const path=row.path;pressLater(key,'clear',queueTitle(row),()=>{const fresh=rows.find(item=>item.path===path);if(fresh)return clearFromRow(fresh,origin?.button || null);});return false;
  }
  retryPending={key,kind:'clear',at:Date.now()};retryResult=null;busy=true;controls();
  let answer=null,failure=null;
  try{answer=await request('/api/audiobook/clear-working',{library:'Audiobooks',id:row.id,revision:row.revision,job_id:job.job_id},PRESS_TIMEOUT);}catch(error){failure=error;}
  if(failure && !failure.httpStatus){
    // No reply in time: a large folder can take longer than the press bound. The row keeps "Clearing…" and is re-read.
    for(let attempt=0;attempt<3 && !answer && !ended;attempt++){
      try{const page=await request(`/api/inventory?library=Audiobooks&offset=0&search=${encodeURIComponent(row.title_clue || '')}&view=candidates&status=all`);const found=(page.rows || []).find(item=>item.id===row.id);if(found && !workingOf(freshRow(found,row)))answer={cleared:true,row:found};}catch(error){}
      if(!answer)await new Promise(resolve=>setTimeout(resolve,1500));
    }
  }
  retryPending=null;busy=false;
  const cause=failure?.httpStatus===409?failure.body?.cause:null,tries=Number(origin?.tries) || 0;
  if(cause==='busy' || cause==='file_problem' && tries<CLEAR_TRIES){
    // The rest of ruling 35 (ruling 37): busy (a scan, the catalog) waits and is sent again; a file another program holds
    // open is tried again every 10 s, CLEAR_TRIES times, then its sentence says what to do. Never "try again in a moment".
    const path=row.path,next={...(origin || {}),tries:tries+(cause==='file_problem'?1:0)},run=()=>{const fresh=rows.find(item=>item.path===path);if(fresh)return clearWorking(next,fresh);};
    if(cause==='busy' && scanRunning())pressLater(key,'clear',queueTitle(row),run,scanRunning);
    else holdAgain(key,'clear',queueTitle(row),run,cause==='busy'?'app':'file',cause==='busy'?5:10);
    controls();return false;
  }
  const focused=document.activeElement===$('clear-working') || document.activeElement===origin?.button;
  if(answer){
    retryEpoch++;
    const fresh=freshRow(answer.row,row) || (()=>{const attention={...row.creation.job.attention};delete attention.working;return {...row,creation:{...row.creation,job:{...row.creation.job,attention}}};})();
    placeRow(row,fresh,origin);
    const natural=rowState(fresh),head=answer.already===true?'Working files were already cleared.':Number.isSafeInteger(answer.bytes) && answer.bytes>0?`Cleared ${sizeText(answer.bytes)} of working files.`:'Working files cleared.';
    retryResult={key:retryKey(fresh),text:head+(natural?.hint?' '+natural.hint:''),warn:false};
  }else if(failure?.httpStatus){
    const fresh=freshRow(failure.body?.row,row);if(fresh)placeRow(row,fresh,origin);
    retryResult={key:retryKey(fresh || row),text:refusedText('clear',failure),warn:true};if(failure.httpStatus===409)retryEpoch++;
  }else retryResult={key,text:lostLine(),warn:true};
  controls();
  if(!recoveryDisconnected && !ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  controls();
  if(focused){if(origin?.row)focusRowButton(row.path,true);else{const retry=$('retry-job');(retry && !retry.hidden && !retry.disabled?retry:$('details-heading')).focus?.({preventScroll:true});}}
  return !!answer;
}
// Confirm where this conversion ran (Сказка): two statements, Cancel first and focused, its own four-stop Tab cycle.
let convertConfirmation=null;
function openConvertDialog(row,origin){
  if(convertConfirmation || discardConfirmation)return;const capability=producerRecoveryOf(row);
  convertConfirmation={path:row.path,key:retryKey(row),snapshot:JSON.stringify(capability),origin,button:origin?.button || $('retry-job')};
  setText('convert-dialog-book',`${row.review?.title || row.title_clue || 'Book'} — ${row.review?.canonical_author || 'Author unavailable'}`);
  $('convert-here').checked=false;$('convert-unmoved').checked=false;setText('convert-dialog-delete',deletionLine(capability));setText('convert-dialog-status','');convertReady();
  $('convert-dialog').showModal?.();$('convert-cancel').focus?.();
}
function convertReady(){const ready=$('convert-here').checked===true && $('convert-unmoved').checked===true,go=$('convert-confirm');go.setAttribute('aria-disabled',String(!ready));go.title=ready?'Save your confirmation and start converting this book.':'Tick both statements first.';if(ready)setText('convert-dialog-status','');return ready;}
function closeConvertDialog(restore=true){if(!convertConfirmation)return;const button=convertConfirmation.button;convertConfirmation=null;$('convert-dialog').close?.();if(restore)button?.focus?.({preventScroll:true});}
function confirmConvert(event){
  // The ruling needs Sergei's own press: a synthetic (untrusted) click does nothing.
  if(!convertConfirmation || event?.isTrusted!==true)return;
  if(!convertReady()){setText('convert-dialog-status','Tick both statements first.');return;}
  const {path,key,snapshot,origin,button}=convertConfirmation;closeConvertDialog(false);button?.focus?.({preventScroll:true});
  const row=rows.find(item=>item.path===path),capability=producerRecoveryOf(row);
  if(!row || retryKey(row)!==key || JSON.stringify(capability)!==snapshot){if(capability)retryResult={key,producer:true,snapshot:JSON.stringify([capability.state,capability.checkpoint_id,capability.cause]),warn:true,status:'Conversion not started',text:'This book changed. Review its details and try again.'};controls();return;}
  convertPress(row,origin);
}
async function convertPress(row,origin=null){
  const key=retryKey(row),job=row?.creation?.job,capability=producerRecoveryOf(row);
  if(!key || !job || capability?.can_confirm_origin!==true || ended || recoveryDisconnected)return false;
  // The rest of ruling 35 (ruling 37): a Convert confirmed while another press runs, or while a scan runs ("Scanning is
  // running. Convert when it stops."), waits and is sent then, every check again; the row shows it queued, with Cancel.
  const path=row.path,again=()=>{const fresh=rows.find(item=>item.path===path);if(fresh)return convertPress(fresh,origin);};
  if(retryPending || busy || recoverySubmitting || automaticRequest!==null || bulkRunning() || releaseRun || scanRunning()){
    pressLater(key,'convert',queueTitle(row),again,scanRunning()?scanRunning:null);controls();return false;
  }
  const snapshot=JSON.stringify([capability.state,capability.checkpoint_id,capability.cause]),focused=document.activeElement===(origin?.button || $('retry-job'));let answer=null;
  retryPending={key,kind:'convert',note:rowActions.convert.note};retryResult=null;busy=true;controls();updateProducerRecoverySurface(row);
  try{answer=await request('/api/audiobook/confirm-convert',{library:'Audiobooks',id:row.id,revision:row.revision,job_id:job.job_id,statements:[...ORIGIN_STATEMENTS]},PRESS_TIMEOUT);}
  catch(error){
    if(error.httpStatus===409 && error.body?.code==='scanning'){retryPending=null;busy=false;pressLater(key,'convert',queueTitle(row),again,scanSeen());controls();updateProducerRecoverySurface(row);return false;}  // a scan began meanwhile
    retryResult={key,producer:true,snapshot,transport:!error.httpStatus,warn:true,status:error.httpStatus?'Conversion not started':'Conversion status unknown',text:!error.httpStatus?(desktopMode()?NOT_CONFIRMED.press:'Could not confirm the request. Reconnect to check its saved state.'):error.body?.cause==='book_changed'?error.message:'Nothing was changed. '+(error.message || '')};
    if(!error.httpStatus)refreshFailed(error);
  }
  retryPending=null;busy=false;let fresh=row;const saved=answer?.producer_recovery;
  if(answer?.job_id===job.job_id && answer.queued_next===true){
    remember(key,'queued','retry',answer.position);retryEpoch++;fresh=queuedNext(row,answer);heldRow={path:row.path,index:rows.findIndex(item=>item.path===row.path),context:listContext(),row:fresh,until:Date.now()+PRESS_MEMORY};
    retryResult={key,text:'Confirmed. Starting conversion.',warn:false,panelOnly:true};
  }else if(answer?.job_id===job.job_id && saved?.schema==='books-producer-recovery-capability-v1')fresh={...row,creation:{...row.creation,job:{...job,attention:{...job.attention,producer_recovery:saved}}}};  // R1a/R1b: the confirmation is kept
  rows=rows.map(item=>item.path===row.path?fresh:item);const entry=rowRetries.get(row.path);if(entry)entry.row=fresh;if(selectedRow?.path===row.path){if(answer?.queued_next===true)select(fresh,false);else selectedRow=fresh;}
  controls();updateProducerRecoverySurface(fresh);
  if(!recoveryDisconnected && !ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  controls();
  if(focused && answer?.queued_next===true){if(origin?.row)focusRowButton(row.path);else $('details-heading').focus?.({preventScroll:true});}
  return answer?.queued_next===true;
}
$('convert-cancel').addEventListener('click',()=>closeConvertDialog());
$('convert-confirm').addEventListener('click',event=>confirmConvert(event));
for(const id of ['convert-here','convert-unmoved']){$(id).addEventListener('change',()=>convertReady());$(id).addEventListener('keydown',event=>{if(event.key==='Enter')event.preventDefault?.();});}
$('convert-dialog').addEventListener('cancel',event=>{event.preventDefault?.();closeConvertDialog();});
$('convert-dialog').addEventListener('keydown',event=>{if(!convertConfirmation)return;if(event.key==='Escape'){event.preventDefault?.();closeConvertDialog();}else if(event.key==='Tab'){event.preventDefault?.();const order=['convert-cancel','convert-here','convert-unmoved','convert-confirm'].map(id=>$(id)),at=order.indexOf(document.activeElement);order[(at+(event.shiftKey?order.length-1:1)+order.length)%order.length].focus?.();}});
// The confirmation before a saved review is discarded: the native modal dialog, Cancel first and focused.
const DISCARD_COPY={
  release:{title:"Discard this book's saved review?",body:["This deletes the metadata, cover and track choices saved on this book, including any you made by hand. It can't be undone.",'Automatic processing then researches the book again and queues it if the match is safe. It starts if it isn\'t running. Your audio files are not touched.'],go:'Discard review',cancelTip:'Keep the saved review and leave this book held.',goTip:"Delete this book's saved review, then let automatic processing take the book. This can't be undone."},
  combined:{title:"Start over and discard this book's saved review?",body:["This sets the failed job aside, then deletes the metadata, cover and track choices saved on this book, including any you made by hand. The deleted review can't be restored.",'Automatic processing then researches the book again and queues it if the match is safe. It starts if it isn\'t running. The failed job and your audio files are kept.'],go:'Discard review and start over',cancelTip:'Keep everything as it is.',goTip:"Set the failed job aside, delete this book's saved review and let automatic processing take the book. This can't be undone."}};
function openDiscardDialog(kind,books,onConfirm,button,leftOut=0){
  if(discardConfirmation)return;
  const bulk=kind==='bulk' && books.length>1,copy=bulk?{title:`Discard ${books.length.toLocaleString()} saved reviews?`,
    body:[`This deletes the metadata, cover and track choices saved on these ${books.length.toLocaleString()} books, including any you made by hand. It can't be undone.`,'Automatic processing then researches each book again and queues it if the match is safe. It starts if it isn\'t running. Your audio files are not touched.'],
    go:`Discard ${books.length.toLocaleString()} reviews`,cancelTip:'Keep the saved reviews and leave these books held.',goTip:`Delete the saved reviews of these ${books.length.toLocaleString()} books, then let automatic processing take them. This can't be undone.`}:DISCARD_COPY[kind==='bulk'?'release':kind];
  discardConfirmation={onConfirm,button};
  setText('discard-dialog-title',copy.title);
  const book=books[0];setText('discard-dialog-book',bulk?'':book?.review?.title || book?.title_clue || 'Book');$('discard-dialog-book').hidden=bulk;
  setText('discard-dialog-body',copy.body[0]);setText('discard-dialog-body2',copy.body[1]);
  setText('discard-dialog-body3',bulk && leftOut>0?`${leftOut.toLocaleString()} other selected books are not included. They stay selected and unchanged.`:'');$('discard-dialog-body3').hidden=!(bulk && leftOut>0);
  setText('discard-confirm',copy.go);$('discard-confirm').title=copy.goTip;$('discard-cancel').title=copy.cancelTip;
  $('discard-dialog').showModal?.();$('discard-cancel').focus?.();
}
function closeDiscardDialog(restore=true){
  if(!discardConfirmation)return;const button=discardConfirmation.button;discardConfirmation=null;$('discard-dialog').close?.();
  if(restore)button?.focus?.({preventScroll:true});
}
function confirmDiscard(){
  if(!discardConfirmation)return;const {onConfirm,button}=discardConfirmation;closeDiscardDialog(false);
  // The dialog closes at once; the button then shows its pending face and keeps focus.
  button?.focus?.({preventScroll:true});onConfirm();
}
$('discard-cancel').addEventListener('click',()=>closeDiscardDialog());
$('discard-confirm').addEventListener('click',()=>confirmDiscard());
$('discard-dialog').addEventListener('cancel',event=>{event.preventDefault?.();closeDiscardDialog();});
$('discard-dialog').addEventListener('keydown',event=>{if(!discardConfirmation)return;if(event.key==='Escape'){event.preventDefault?.();closeDiscardDialog();}else if(event.key==='Tab'){event.preventDefault?.();const first=$('discard-cancel'),last=$('discard-confirm');(document.activeElement===first?last:first).focus?.();}});
$('clear-working').addEventListener('click',()=>{if($('clear-working').getAttribute?.('aria-disabled')==='true')return;clearWorking();});
// Let the app handle selected (O14): the Held and Started over filters only. One confirmation with the count.
function releaseSelection(){return view==='candidates' && (filters[view]==='held' || filters[view]==='restarted');}
function releaseSelectable(){return rows.filter(row=>row.kind==='candidate' && selectedBooks.has(row.id) && releaseOf(row));}
function renderReleaseSelected(){
  const shown=releaseSelection(),button=$('release-selected'),count=shown?releaseSelectable().length:0;
  button.hidden=!shown;if(!shown)return;
  const label=releaseRun?'Discarding…':`Let the app handle selected (${count.toLocaleString()})`;if(button.textContent!==label)button.textContent=label;
  button.title=count?`Discard the saved reviews of these ${count.toLocaleString()} selected books, including any edits you made by hand, and let automatic processing take them. Starts automatic processing if it isn't running. This can't be undone.`:'Select books held for a saved review.';
  const unavailable=!count || releaseRun || ended || recoveryDisconnected || bulkRunning();
  if(releaseRun || unavailable)button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
  button.disabled=unavailable && !releaseRun;
  const help='Only selected books held for a saved review can be handed to the app. The others stay as they are.';
  if(!attentionSelection() && $('batch-help').textContent!==help)$('batch-help').textContent=help;
}
function bulkPassSentence(pass){
  if(!pass)return '';
  if(pass.action==='started')return ' Automatic processing has started. It scans the library first, so this may take a while.';
  if(pass.action==='continued')return ' Automatic processing continued where it paused.';
  if(pass.action==='running')return pass.visit==='next_run'?' Automatic processing is running but has already passed these books. Press Start automatic processing above after it finishes.':' Automatic processing is running and will reach these books.';
  if(pass.action==='pending')return {conversion:' Automatic processing will start by itself when audiobook conversion finishes or is paused.',scan:' Automatic processing will start by itself when the library scan ends or is stopped.',stopping:' Automatic processing will start by itself when it has stopped.'}[pass.pending_kind] || '';
  if(pass.action==='blocked')return ' Automatic processing did not start.'+(pass.reason?' '+pass.reason:'');
  return '';
}
async function startReleaseSelected(items){
  if(releaseRun || ended || recoveryDisconnected || !items.length)return;
  if(busy){pressLater('toolbar:release-selected','release_selected','',()=>startReleaseSelected(items));message(laterLine(laterFor('toolbar:release-selected')));return;}  // ruling 35
  releaseRun=true;busy=true;$('release-selected-status').textContent='';controls();
  let text='',warn=false;
  try{
    const answer=await request('/api/audiobook/release-selected',{library:'Audiobooks',items:items.map(row=>({id:row.id,revision:row.revision}))});
    if(answer.automatic_processing && state)state={...state,automatic_processing:answer.automatic_processing};
    const released=Number(answer.released) || 0,failed=Array.isArray(answer.refused)?answer.refused.length:0,pass=answer.pass;
    warn=failed>0 || pass?.action==='blocked' || pass?.visit==='next_run';
    text=`Discarded ${released.toLocaleString()} of ${items.length.toLocaleString()} saved reviews.${bulkPassSentence(pass)}${pass?.action==='blocked' || pass?.visit==='next_run'?'':' Find them under Status: Started over.'}`+(failed?` ${failed.toLocaleString()} were not changed. Check their status.`:'');
    retryEpoch++;
  }catch(error){text=error.httpStatus?"The reviews weren't discarded. Check the status above.":lostLine('discard');warn=true;if(!error.httpStatus)refreshFailed(error);}
  finally{releaseRun=false;busy=false;}
  const status=$('release-selected-status');status.textContent=text;status.classList?.toggle?.('retry-refused',warn);renderAutomatic();controls();
  if(!recoveryDisconnected && !ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  controls();status.focus?.({preventScroll:true});
}
$('release-selected').addEventListener('click',()=>{
  const button=$('release-selected');if(button.disabled || button.getAttribute?.('aria-disabled')==='true')return;
  const items=releaseSelectable(),selected=rows.filter(row=>row.kind==='candidate' && selectedBooks.has(row.id)).length;if(!items.length)return;
  if(items.length===1)openDiscardDialog('release',items,()=>startReleaseSelected(items),button);
  else openDiscardDialog('bulk',items,()=>startReleaseSelected(items),button,selected-items.length);
});
// Retry all (Attention spec section 6): the server's whole Can retry group, not the visible page,
// after an inline confirmation. The server runs one book at a time; its count arrives with each poll.
function openRetryAll(){
  const counts=state?.audiobook_jobs?.attention_counts || {},count=Number.isInteger(counts.retry)?counts.retry:0,queued=state?.audiobook_jobs?.queued;
  if(count<2 || bulkRunning() || busy || ended || recoveryDisconnected)return;
  const cleanable=state?.audiobook_jobs?.working_cleanable;
  retryAllConfirm={count,queued:Number.isInteger(queued) && queued>0?queued:0,cleanable:Number.isInteger(cleanable) && cleanable>0?cleanable:0};stripNote='';renderAttentionGroups();
  $('retry-all-cancel').focus?.({preventScroll:true});
}
function closeRetryAll(){if(!retryAllConfirm)return;retryAllConfirm=null;renderAttentionGroups();$('retry-all').focus?.({preventScroll:true});}
function retryReceiptText(run,includeProgress=true){
  if(!run)return '';
  const n=value=>Number.isInteger(value)&&value>=0?value.toLocaleString():'unavailable';
  if(run.state==='running')return includeProgress?'Requesting retries — '+n(run.done)+' of '+n(run.total)+' processed':'Requesting retries.';
  if(run.accepted===0 && Number.isInteger(run.refused) && run.refused>0)return 'No retry requests accepted. '+n(run.refused)+' refused. No conversion started from this request.';
  let line='Retry requested for '+n(run.accepted)+' of '+n(run.total)+' books.';
  if(run.refused>0)line+=' '+n(run.refused)+' refused.';
  const counts=run.progress?.schema==='books-retry-progress-v1'?run.progress.counts:null;
  if(counts && includeProgress)line+=' '+['waiting','checking','queued','running','completed','stopped'].map(key=>n(counts[key])+' '+key).join(' · ')+'.';
  else if(!counts)line+=' Current retry progress unavailable.';
  else line+=' '+(counts.running?'Conversion is running.':counts.checking?'Retry checks are running.':counts.queued?'Conversion jobs are queued.':counts.waiting?'Waiting for retry checks.':counts.stopped?'Some retry checks stopped.':counts.completed?'Retry checks finished.':'Retry request finished.');
  const stalled=!counts || (counts.waiting>0 && !counts.checking && !counts.queued && !counts.running);
  const blocked=run.receipt_error || (stalled?(run.worker?.reason || run.start_outcome?.reason || run.progress?.targets?.find(item=>item.reason)?.reason):'');
  if(blocked)line+=' '+blocked;
  else if(counts && (counts.waiting || counts.checking) && !counts.queued && !counts.running)line+=' Retry requests are saved; conversion has not started. Check the status above.';
  return line;
}
function acceptBulkResponse(result){
  const run=result?.retry_all;
  if(!run || typeof run.id!=='string')throw Error('Retry request receipt unavailable; check the current status before trying again.');
  retryEpoch++;retryAllRun={id:run.id,ended:false};
  state={...state,audiobook_jobs:{...(state?.audiobook_jobs || {}),retry_all:run}};
  $('retry-selected-status').textContent='';stripNote=retryReceiptText(run,false);
}
async function startRetryAll(){
  if(!retryAllConfirm || bulkRunning() || busy || ended || recoveryDisconnected)return;
  const confirm=retryAllConfirm;
  retryAllConfirm=null;busy=true;stripNote='';retryAllRun={id:bulkRun()?.id,ended:true,suppressReceipt:true};$('retry-selected-status').textContent='';controls();
  try{acceptBulkResponse(await request('/api/audiobook/retry-all',{library:'Audiobooks'}));}
  catch(error){
    // The rest of ruling 35 (ruling 37): a scan that began after the page looked: Retry all waits for it and is sent again.
    if(error.body?.code==='scanning'){retryAllConfirm=confirm;const item=pressLater('toolbar:retry-all-go','retry_all','',()=>startRetryAll(),scanSeen());stripNote=laterLine(item)+' Press it again to cancel.';}
    else stripNote=error.httpStatus?(error.message || 'Retry requests were not accepted. Check the status above.'):lostLine('bulk');if(!error.httpStatus)refreshFailed(error);}
  finally{busy=false;}
  controls();$('retry-all-status').focus?.({preventScroll:true});
}
function finishRetryAll(run){
  retryAllRun.ended=true;stripNote=retryReceiptText(run,false);
  setTimeout(async()=>{if(!recoveryDisconnected && !ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}controls();},0);
}
const attentionLabels={all:'All',files_missing:'Missing files',title_author:'Title or author',author_unclear:'Author unclear',same_author:'Same author?',name_taken:'Name taken',part_of_book:'Part of a bigger book',files_unclear:'Files unclear',order_unclear:'Order unclear',retry:'Can retry',repair:'Can repair',reacquire:'Need to reacquire',checking:'Retry checks',changed:'Original changed',audiobook:'Audiobook problem',other:'Other',unsupported:'M4B not supported'};
// All = the sum of these keys = the shortcut = the Jobs line (Judy 2026-10-24, section 2): the "Needs your answer" set first.
const NEEDS_KEYS=['files_missing','title_author','author_unclear','same_author','name_taken','part_of_book','files_unclear','order_unclear'];  // 0.22.0 review (Judy, B3): three hold chips
const attentionKeys=['all',...NEEDS_KEYS,'retry','repair','reacquire','checking','changed','audiobook','other','unsupported'];
function attentionTotal(jobs){
  const counts=jobs?.attention_counts;
  if(!counts || typeof counts!=='object')return jobs?.failed || 0;
  return attentionKeys.slice(1).reduce((sum,key)=>sum+(Number.isInteger(counts[key])?counts[key]:0),0);
}
function renderAttentionGroups(){
  const shown=view==='candidates' && filters[view]==='output_attention',strip=$('attention-groups');strip.hidden=!shown;if(!shown)return;
  const counts=state?.audiobook_jobs?.attention_counts || {},value=key=>Number.isInteger(counts[key])?counts[key]:0,total=attentionTotal({attention_counts:counts});
  const active=globalThis.document?.activeElement;
  if(attentionGroup!=='all' && attentionGroup!=='retry' && counts[attentionGroup]===0){
    // The selected group emptied: back to All, and focus moves there if it was in the strip or lost. Checking empties
    // into Can retry instead: the books Sergei waited for are there (RefusedRetry follow-up, section 2).
    const lost=!active || active===globalThis.document?.body || strip.contains?.(active),next=attentionGroup==='checking'?'retry':'all';
    // 0.22.1 (Futaba m-14): the chip emptied because its last row was settled; the strip line saying what happened (a
    // delete's outcome) stays across this one fall-back. A chip or filter Sergei changes still clears it.
    attentionGroup=next;retryAllConfirm=null;
    setTimeout(()=>{updateList();if(lost)$('group-'+next).focus?.({preventScroll:true});},0);
  }
  for(const key of attentionKeys){
    const button=$('group-'+key),count=key==='all'?total:value(key),text=`${attentionLabels[key]} · ${key==='reacquire' && !Number.isInteger(counts[key])?'unavailable':count.toLocaleString()}`;
    if(button.textContent!==text)button.textContent=text;
    button.setAttribute('aria-pressed',String(attentionGroup===key));
    if(key==='all')button.title=`Show all ${total.toLocaleString()} books that need attention.`;
    // A group at zero is hidden, except All and Can retry; it stays while selected or focused.
    button.hidden=key!=='all' && key!=='retry' && !(key==='reacquire' && !Number.isInteger(counts[key])) && value(key)===0 && attentionGroup!==key && active!==button;
  }
  // A set whose chips are all hidden hides its label too (the Stopped set always shows Can retry).
  if($('attention-set-needs'))$('attention-set-needs').hidden=NEEDS_KEYS.every(key=>$('group-'+key).hidden);
  // Books automatic processing has not settled yet are counted, never silently missing (0.22.0 review B5.2).
  const sweep=$('attention-sweep');
  if(sweep){const n=stillChecking(),running=state?.automatic_processing?.state==='Running';
    const text=!n?'':running?`Still checking ${plural(n,'book','books')}. More may appear here.`:`${plural(n,'book is','books are')} waiting to be checked. Start automatic processing to check ${n===1?'it':'them'}.`;
    if(sweep.textContent!==text)sweep.textContent=text;sweep.hidden=!text;}
  const queueLine=$('queue-line');
  if(queueLine){const n=queueState.queued.length,p=n?queueP(queueBlocker(queueState.queued[0])):'';
    const text=!n?'':n===1?`1 action queued. It runs when ${p} finishes.`:`${n.toLocaleString()} actions queued. They run one at a time when ${p} finishes.`;
    if(queueLine.textContent!==text)queueLine.textContent=text;queueLine.hidden=!text;}
  const run=bulkRun(),running=run?.state==='running';
  if(retryAllRun && !retryAllRun.ended && run?.id===retryAllRun.id && !running)finishRetryAll(run);
  const all=$('retry-all'),confirm=retryAllConfirm,allLabel=`Retry all (${value('retry').toLocaleString()})`;
  all.hidden=attentionGroup!=='retry' || value('retry')<2 || !!confirm;
  if(all.textContent!==allLabel)all.textContent=allLabel;
  all.title=`Request retries for these ${value('retry').toLocaleString()} books. Each book is checked before a conversion job can be queued.`;
  all.disabled=running || ended || recoveryDisconnected;  // ruling 35: another press of the page never disables it
  // The confirmation keeps the count it opened with; polls never rebuild it.
  $('retry-all-confirm').hidden=!confirm || attentionGroup!=='retry';
  if(confirm){
    const question=`Request retries for ${confirm.count.toLocaleString()} books? Each book is checked before a conversion job can be queued.`+clearsClause(confirm.cleanable),go=`Request ${confirm.count.toLocaleString()} retries`;
    if($('retry-all-question').textContent!==question)$('retry-all-question').textContent=question;
    if($('retry-all-go').textContent!==go)$('retry-all-go').textContent=go;
    $('retry-all-go').disabled=running || ended || recoveryDisconnected;
  }
  // The live region announces only the start and the end; the running count sits outside it.
  const countsForRun=run?.progress?.schema==='books-retry-progress-v1'?run.progress.counts:null;
  const count=running?`${Number(run.done).toLocaleString()} of ${Number(run.total).toLocaleString()} processed`:countsForRun?['waiting','checking','queued','running','completed','stopped'].map(key=>`${Number(countsForRun[key]).toLocaleString()} ${key}`).join(' · '):'';
  if(run && !retryAllRun?.suppressReceipt && (!retryAllRun || run.id===retryAllRun.id))stripNote=retryReceiptText(run,false);
  if($('retry-all-status').textContent!==stripNote)$('retry-all-status').textContent=stripNote;
  if(!stripNote)stripShow=null;renderStripShow();
  if($('retry-all-count').textContent!==count)$('retry-all-count').textContent=count;
  $('retry-all-line').hidden=!stripNote && !count;
}
for(const key of attentionKeys)$('group-'+key).addEventListener('click',()=>{if(attentionGroup===key)return;attentionGroup=key;resetStrip();renderAttentionGroups();return updateList();});
$('retry-all').addEventListener('click',()=>{if($('retry-all').disabled)return;openRetryAll();});
// Retry selected (v0.16.12): in Output needs attention, the selected books that can be retried or repaired, one
// press each through the same queued-next path as Retry, after one confirmation (as Retry all).
function attentionSelection(){return view==='candidates' && filters[view]==='output_attention';}
// The bulk dialogs say how many of the books have leftover working files, cleared first (decisions A and O10).
function clearsClause(count){return count>0?` ${count.toLocaleString()} of them ${count===1?'has':'have'} leftover working files, which are cleared first.`:'';}
function retrySelectable(){
  return rows.filter(row=>row.kind==='candidate' && selectedBooks.has(row.id)).map(row=>({row,action:rowAction(row)}))
    .filter(item=>item.action && (item.action.kind==='retry' || item.action.kind==='repair') && item.action.data?.allowed===true && !queuedFor(item.row) && !queueRunning(item.row));
}
function conditionalRetries(items){return items.filter(item=>!!refusalCurrent(item.row)).length;}
function renderRetrySelected(){
  const shown=attentionSelection(),button=$('retry-selected'),count=shown?retrySelectable().length:0,confirm=retrySelectedConfirm;
  // In the two chips where Approve as is works, Retry selected hides (Judy 2026-10-24, section 5).
  $('queue-books').hidden=shown;button.hidden=!shown || !!confirm || needsChip();
  const label=`Retry selected (${count.toLocaleString()})`;if(button.textContent!==label)button.textContent=label;
  button.title=count?`Request retries for these ${count.toLocaleString()} selected books. Each book is checked before a conversion job can be queued.`:'Select books that can be retried or repaired.';
  button.disabled=!count || ended || recoveryDisconnected || bulkRunning() || retrySelectedRun;
  // A "Needs your answer" chip without bulk Approve has no batch action, so no help line (0.22.0 review B3).
  const help=bulkChip()?'Approve as is uses the names shown on each row. Books that need a different action are left out.':needsChip()?'':shown?(conditionalRetries(retrySelectable())?'Previous attempts were refused. Check each book\'s reason before retrying.':'Only selected books that can be retried or repaired can request new checks.'):'Only ready selected revisions are queued. Candidates needing review remain selected.';
  if($('batch-help').textContent!==help)$('batch-help').textContent=help;$('batch-help').hidden=!help;
  $('retry-selected-confirm').hidden=!shown || !confirm || needsChip();
  if(confirm){
    const question=`Request retries for ${confirm.items.length.toLocaleString()} selected books? Each book is checked before a conversion job can be queued.`+clearsClause(confirm.items.filter(item=>workingOf(item.row)?.state==='cleanable').length),go=`Request ${confirm.items.length.toLocaleString()} retries`;
    if($('retry-selected-question').textContent!==question)$('retry-selected-question').textContent=question;
    if($('retry-selected-go').textContent!==go)$('retry-selected-go').textContent=go;
    $('retry-selected-go').disabled=ended || recoveryDisconnected || retrySelectedRun;
  }
}
function closeRetrySelected(){if(!retrySelectedConfirm)return;retrySelectedConfirm=null;controls();$('retry-selected').focus?.({preventScroll:true});}
async function startRetrySelected(){
  const confirm=retrySelectedConfirm;if(!confirm || retrySelectedRun || bulkRunning() || busy || ended || recoveryDisconnected)return;
  retrySelectedConfirm=null;retrySelectedRun=true;busy=true;stripNote='';retryAllRun={id:bulkRun()?.id,ended:true,suppressReceipt:true};$('retry-selected-status').textContent='';controls();
  try{
    const items=confirm.items.map(({row,action})=>({id:row.id,revision:row.revision,job_id:row.creation.job.job_id,kind:action.kind}));
    acceptBulkResponse(await request('/api/audiobook/retry-all',{library:'Audiobooks',items},PRESS_TIMEOUT));
  }catch(error){
    if(error.body?.code==='scanning'){retrySelectedConfirm=confirm;const item=pressLater('toolbar:retry-selected-go','retry_selected','',()=>startRetrySelected(),scanSeen());stripNote=laterLine(item)+' Press it again to cancel.';}  // ruling 35's rest
    else stripNote=error.httpStatus?(error.message || 'Retry requests were not accepted.'):lostLine('bulk');if(!error.httpStatus)refreshFailed(error);}
  finally{retrySelectedRun=false;busy=false;}
  controls();$('retry-all-status').focus?.({preventScroll:true});
}
$('retry-selected').addEventListener('click',()=>{
  if($('retry-selected').disabled)return;const items=retrySelectable();if(!items.length)return;
  retrySelectedConfirm={items};$('retry-selected-status').textContent='';controls();$('retry-selected-cancel').focus?.({preventScroll:true});
});
$('retry-selected-go').addEventListener('click',later('toolbar:retry-selected-go','retry_selected',()=>{if($('retry-selected-go').disabled)return;return startRetrySelected();}));
$('retry-selected-cancel').addEventListener('click',()=>closeRetrySelected());
$('retry-selected-confirm').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault?.();closeRetrySelected();}});
$('retry-all-go').addEventListener('click',later('toolbar:retry-all-go','retry_all',()=>{if($('retry-all-go').disabled)return;return startRetryAll();}));
$('retry-all-cancel').addEventListener('click',()=>closeRetryAll());
$('retry-all-confirm').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault?.();closeRetryAll();}});
$('retry-job').addEventListener('click',()=>{if($('retry-job').getAttribute?.('aria-disabled')==='true' || retryPending)return;retryJob();});
// The details panel's Cancel retry / Cancel repair beside a queued face (Judy 1.3), the same press as the row's.
$('retry-cancel').addEventListener('click',event=>{if(event?.repeat || $('retry-cancel').hidden || !selectedRow)return;const item=queuedFor(selectedRow);if(item && item.action!=='delete')cancelQueued(selectedRow,item.action);});
$('recovery-cancel').addEventListener('click',()=>closeRecoveryDialog());
$('recovery-confirm').addEventListener('click',deleteRecoveryCopies);
$('recovery-dialog').addEventListener('cancel',event=>{event.preventDefault();closeRecoveryDialog();});
$('recovery-dialog').addEventListener('keydown',event=>{if(!recoveryConfirmation)return;if(event.key==='Escape'){event.preventDefault();closeRecoveryDialog();}else if(event.key==='Tab'){event.preventDefault();const first=$('recovery-cancel'),last=$('recovery-confirm');(document.activeElement===first?last:first).focus();}});

const automaticStates=new Set(['Idle','Running','Stopping','Paused','Completed','Needs attention']);
function settleAutomaticRequest(flight){
  if(!flight || automaticFlight!==flight)return;
  automaticFlight=null;automaticRequest=null;busy=false;
}
function reconcileAutomaticRequest(automatic){
  const flight=automaticFlight;if(!flight)return;
  const changed=automatic?.run_id!==flight.run_id || automatic?.state!==flight.state || automatic?.failure?.id!==flight.failure_id;
  const confirmed=flight.kind==='start'?['Running','Needs attention','Completed','Paused'].includes(automatic?.state):
    flight.kind==='stop'?['Stopping','Paused','Completed','Needs attention','Idle'].includes(automatic?.state):!startPending(automatic);
  if(recoveryDisconnected || ended || !automaticStates.has(automatic?.state) || (changed && confirmed))settleAutomaticRequest(flight);
}
function setText(id,value){if($(id).textContent!==value)$(id).textContent=value;}
function automaticPhase(value){return {discovery:'discovery',research:'metadata research',conversion:'audiobook jobs',paused:'saving pending work',completed:'finishing the pass'}[value] || 'pending work';}
const PENDING_NOTICE={conversion:'Automatic processing will start by itself when audiobook conversion finishes or is paused. Starting also resumes any queued audiobook jobs.',
  scan:'Automatic processing will start by itself when the library scan ends or is stopped.',stopping:'Automatic processing will start again by itself once it has stopped.'};
function startPending(automatic){const kind=automatic?.start_pending?.kind;return Object.hasOwn(PENDING_NOTICE,kind)?kind:null;}
function renderAutomaticEligibility(){
  const automatic=state?.automatic_processing;
  let reason='';
  if(ended)reason='The local server is stopping or stopped. Start is unavailable.';
  else if(recoveryDisconnected || typeof automatic?.can_start!=='boolean')reason='Start availability is unknown. Waiting for the local server.';
  else if(automaticRequest==='start' || draftLeaseFailure || (manualDraftLease?.active && !manualDraftLease.confirmed))reason='';
  // A pending start (O12): the notice says what it waits for, in place of the block reason; Start stays disabled.
  else if(startPending(automatic))reason=PENDING_NOTICE[startPending(automatic)];
  else if(automatic.can_start!==true)reason=automatic.start_block_reason || 'Start availability is unknown. Waiting for the local server.';
  setText('automatic-start-reason',reason);
  $('automatic-start-reason').hidden=$('library').value!=='Audiobooks' || !reason;
  $('start-automatic').title=reason || (automatic?.state==='Paused'?'Continue the saved discovery, metadata research and queued audiobook jobs.':'Discover audiobooks, research public metadata, and convert confident matches. Uncertain books stay held.');
}
function renderAutomatic(){
  // Futaba's 0.22.1 QA, m-7: every answer re-rendered this, so between the library part and the jobs part the page said
  // "Automatic processing: status unavailable", words 3.5 removed: "unavailable" is for a failure, "loading…" for waiting.
  if(loadingActive && !(state && partReady('jobs')))return loadPlaceholders();
  const automatic=state?.automatic_processing,known=automaticStates.has(automatic?.state),stale=recoveryDisconnected || ended?'Last confirmed — ':'';
  reconcileAutomaticRequest(automatic);
  const shown=automatic?.state==='Needs attention'?'Stopped — needs attention':automatic?.state;
  setText('automatic-status',(!known || stale?'Current processing status unavailable. ':'')+stale+'Automatic processing: '+(known?(stale?automatic.state:shown):'status unavailable'));
  setText('automatic-request',automaticRequest==='start'?'Starting automatic processing…':automaticRequest==='stop'?'Requesting automatic stop…':'');
  renderAutomaticEligibility();
  let detail='';
  if(automatic?.state==='Stopping')detail='Stopping automatic processing — '+(automatic.reason || automaticPhase(automatic.phase));
  else if(automatic?.state==='Paused')detail=automatic.restart_paused?'Paused after server restart — start to continue saved work':(automatic.reason || 'Paused — pending work saved');
  else if(automatic?.state==='Completed'){
    const converted=verifiedCount(state?.audiobook_jobs?.converted_total),approved=verifiedCount(state?.audiobook_jobs?.approved_total),held=verifiedCount(automatic.research?.held);
    detail=converted!==null && approved!==null && approved>=converted && held!==null?'Automatic pass complete — '+converted+' converted · '+held+' held':'Automatic pass complete — result counts unavailable';
  }else if(automatic?.state==='Running' && automatic.phase==='waiting' && automatic.automatic_retry_enabled===true){
    detail='Waiting for metadata sources; saved research retries automatically.';
    const retry=retryDate(automatic.next_retry_at);detail+=retry?' Next automatic retry check: '+retry:' Automatic retry time unavailable';
  }else if(automatic?.state==='Needs attention')detail=(automatic.reason || 'Automatic processing stopped. The app did not report a specific reason.')+
    (automatic.can_start===true?' Start automatic processing to continue.':automatic.start_block_reason?'':' No action is available here yet.');
  else if(automatic?.reason)detail=automatic.reason;
  setText('automatic-detail',detail);$('automatic-detail').hidden=!detail;
  $('stop-automatic').title=!known || stale?'Current processing status unavailable.':automatic.state==='Stopping'?'Automatic processing is stopping.':automatic.can_stop!==true && automatic.state!=='Running'?'Automatic processing is stopped.':'Stop research and pause audiobook jobs. Save pending work; finished books stay in place.';
  const research=automatic?.research,counts=research && ['researching','waiting','held'].every(key=>verifiedCount(research[key])!==null);
  setText('research-status',stale+(counts?'Metadata research: '+research.researching+' researching · '+research.waiting+' waiting · '+research.held+' held':'Research status unavailable'));
  const current=automatic?.current;
  const currentText=current && current.title && research?.researching>0?'Current research: '+current.title+' — '+[current.source,current.stage].filter(Boolean).join(' / ')+(research.researching>1?' and '+(research.researching-1)+' more':''):'';
  setText('research-current',currentText);$('research-current').hidden=!currentText;
}
async function automaticAction(kind){
  controls();const button=$({start:'start-automatic',stop:'stop-automatic','cancel-start':'cancel-automatic-start'}[kind]);
  if(button.disabled || automaticRequest!==null || $('library').value!=='Audiobooks')return;
  const automatic=state?.automatic_processing,flight={kind,run_id:automatic?.run_id,state:automatic?.state,failure_id:automatic?.failure?.id};
  automaticFlight=flight;automaticRequest=kind;busy=true;renderAutomatic();controls();message();
  let refreshNeeded=false;
  try{
    const result=await request('/api/automatic/'+kind,{},60000);
    if(automaticFlight!==flight)return;
    const acknowledged=result.automatic_processing || result.state?.automatic_processing;
    if(!automaticStates.has(acknowledged?.state) || typeof acknowledged.can_start!=='boolean' || typeof acknowledged.can_stop!=='boolean')throw Error('Current processing status unavailable. Check the current status before trying again.');
    if(state)state={...state,automatic_processing:acknowledged};
    settleAutomaticRequest(flight);renderAutomatic();controls();
    refreshNeeded=true;
  }catch(error){
    if(automaticFlight!==flight)return;
    if(error.automaticProcessing && state)state={...state,automatic_processing:error.automaticProcessing};
    settleAutomaticRequest(flight);renderAutomatic();controls();
    message(error.message);
    if(error.httpStatus)refreshNeeded=true;else refreshFailed(error);
  }finally{settleAutomaticRequest(flight);renderAutomatic();controls();}
  if(refreshNeeded){
    try{lastKey=null;if(await refresh(true))clearConnectionNotice();}
    catch(error){if(error.httpStatus)message(error.message);else refreshFailed(error);}
  }
  // Cancel automatic start: every other toolbar button is disabled, so focus moves to the notice.
  if(kind==='cancel-start'){const notice=$('automatic-start-reason');notice.setAttribute('tabindex','-1');notice.focus?.({preventScroll:true});}
}
$('cancel-automatic-start').addEventListener('click',()=>automaticAction('cancel-start'));
$('start-automatic').addEventListener('click',later('toolbar:start-automatic','start_automatic',()=>automaticAction('start')));
$('stop-automatic').addEventListener('click',later('toolbar:stop-automatic','stop_automatic',()=>automaticAction('stop')));
function recordedApproval(row){
  if(row.metadata_approved!==true)return '';
  const approval=row.review_context?.automatic_approval;
  if(approval && typeof approval==='object' && !Array.isArray(approval) && typeof approval.matcher_version==='string' && typeof approval.work_id==='string')return 'Approved automatically';
  if(row.review_context?.metadata_actor==='user')return 'Approved manually';
  return '';
}
function candidateTitle(row){return recordedApproval(row) && row.review?.title?'Canonical title: '+row.review.title:'Title clue: '+(row.title_clue || 'Unknown');}
function memberComponents(member,row){
  const key=member.member_key || member.path;
  const components=Array.isArray(member.components)?member.components:(row.metadata_facts?.collection?.components || []).filter(item=>item.source_keys?.includes(key) || item.source_spans?.some(span=>span.source_key===key));
  return components.filter(item=>typeof item.title==='string' && item.title).map(item=>[item.title,Array.isArray(item.authors) && item.authors.length?'Author: '+item.authors.join('; '):'',Number.isSafeInteger(item.order)?'Recorded component order: '+item.order:''].filter(Boolean).join(' · '));
}
function recordingMarker(row){
  return {possible:'Recording review — possible duplicate recording',related_distinct:'Recording review — distinct recording verified',verified_identical:'Recording review — identical recording verified'}[row.duplicate_review?.state] || '';
}
function provenanceFacts(row){
  const recorded=row.metadata_facts;if(!recorded || typeof recorded!=='object')return {};
  const facts={},language=recorded.original_language;
  if(language && typeof language==='object')facts['Original work language']=language.status==='unknown'?'Unknown':language.value || 'Unknown';
  if(recorded.recording_language?.value)facts['Recording language']=recorded.recording_language.value;
  const title={published_english:'Published English title',verified_original:'Verified original title',source_russian:'Russian source title'}[recorded.title_basis];if(title)facts['Title source']=title;
  if(recorded.author_folder_basis==='verified_full_name')facts['Author folder']='Verified full name';
  if(recorded.series_state==='omitted_unknown')facts.Series='Not established';
  if(recorded.collection?.kind==='fan_assembly'){facts['Collection type']='Fan-made compilation';if(Number.isSafeInteger(recorded.collection.component_count) && recorded.collection.component_count>=0)facts['Verified component works']=recorded.collection.component_count;}
  const cover={embedded:'Embedded artwork',neutral:'Neutral artwork',absent:'No artwork available'}[recorded.cover?.kind];if(cover)facts.Cover=cover;
  return facts;
}
function recordingFacts(row){
  const marker=recordingMarker(row),review=row.duplicate_review;if(!marker)return {};
  const facts={'Recording review':marker.replace('Recording review — ',''),'Recording review result':review.blocking===true?'Blocking':review.blocking===false?'Nonblocking':'Unavailable'};
  if(review.state==='possible' && review.blocking===true)facts['Recording review reason']='Possible duplicate recording — compare the related recordings.';
  const related=Array.isArray(review.related)?review.related.filter(item=>typeof item.title==='string' && item.title):[];
  related.forEach((item,index)=>{facts['Related recording '+(index+1)]=[item.title,item.edition?'Edition: '+item.edition:'',item.narrator?'Narrator: '+item.narrator:'',item.language?'Recording language: '+item.language:''].filter(Boolean).join(' · ');});
  return facts;
}
const attentionCopy={retry:['Stopped — ready to retry','Safe to retry now.'],space:['Stopped — not enough disk space','Free up disk space, then retry.'],repair:['Damaged — can repair',''],
  unsupported:["Can't convert — M4B not supported",'Nothing to do for now.'],other:['Stopped — see details','The conversion stopped. Select the row to read the technical message.'],
  changed:['Original changed since checked','Recovery copies are kept until you decide.'],missing:['Audiobook missing','Recovery copies are kept until you decide.'],
  unverified:['Audiobook not verified','Recovery copies are kept until you decide.']};
// A refused Retry or Repair (RefusedRetry spec, 2026-10-19). The server sends a typed cause and fix; these are the
// words. Behaviour comes from the fix, copy from the cause, never from the server's English reason. A missing or
// unknown cause reads as 'unknown', whose fix is 'update'.
// {Verb} and {verb} follow the refusal's kind: Retry, or Repair for a refused Repair (follow-up, point 3b).
const refusalCopy={unsupported_file:["Can't convert — M4B not supported","the app doesn't support how this M4B is built. Nothing to do for now."],
  working_files:['Stopped — waiting for cleanup','working files from an earlier attempt are still present. {Verb} after they are cleared.'],
  source_changed:['Stopped — review changed',"the book's review or source files changed. Start over sends it back to automatic processing."],
  file_problem:['Stopped — check refused','the previous check stopped. Read the recorded reason before you {verb}.'],
  unknown:['Stopped — {verb} refused','']};
const refusalFixes={unsupported_file:'update',working_files:'wait',source_changed:'review',file_problem:'user',unknown:'update'};
function verbed(text,verb){return text.replaceAll('{Verb}',verb).replaceAll('{verb}',verb.toLowerCase());}
// The read-only dry run before "ready to retry" (RefusedRetry follow-up, section 2): not finished, or could not open
// the source. The checking text is also the disabled Retry's reason (the server sends the same words).
const precheckCopy={pending:['Stopped — checking the M4B','The app is checking this M4B before offering Retry. The row updates itself.'],
  unavailable:["Stopped — can't open the M4B","The app couldn't open this M4B to check it. Check that the library drive is connected, then retry."]};
// A working-files record no longer decides the row (follow-up 2, section 2.2): the live state of the files does. The
// record stays for the Technical detail line (refusalRecord).
function refusalRecord(row){const value=readmissionOf(row);return value?.accepted===false && value.queued_next!==true?value:null;}
function refusalOf(row){const value=refusalRecord(row);return value && value.cause!=='working_files'?value:null;}
// "Review changed": the second wording when the pass will hold the book, the combined wording when one press does both.
const STARTOVER_HINTS={automatic:"the book's review or source files changed. Start over sends it back to automatic processing.",
  manual_draft:"the book's review or source files changed. Start over sets this job aside, but automatic processing will hold the book.",
  combined:"the book's review or source files changed. One press sets this job aside, discards its saved review, and sends the book to automatic processing."};
const BLOCKED_COPY=['Stopped — can\'t clear working files',"Working files from an earlier attempt are still present, and the app can't clear them safely right now.",
  "Working files from an earlier attempt are still present, and the app can't clear them while the original files can't be reached. Check that the library drive is connected."];
function refusalCause(refusal){return Object.hasOwn(refusalCopy,refusal?.cause)?refusal.cause:'unknown';}
function refusalFix(refusal){return ['update','wait','review','user'].includes(refusal?.fix)?refusal.fix:refusalFixes[refusalCause(refusal)];}
// The refusal still decides the row: not stale (the deciding code has not changed since).
function refusalCurrent(row){const refusal=refusalOf(row);return refusal && refusal.stale!==true?refusal:null;}
// A stopped job, or a completed book whose recovery copies the 0.16.8 rule keeps (changed or audiobook).
function attentionOf(row){const job=row?.creation?.job,a=job?.attention;return a && typeof a.group==='string' && (job.state==='Output needs attention' || keptGroup(a))?a:null;}
function attentionText(row){
  const reacquire=attentionOf(row)?.reacquire;
  if(reacquire?.state==='required')return {status:'Need to reacquire',hint:(reacquire.certainty==='uncertain'?'The app cannot repair this damage without risking missing audio.':'The audio is damaged and cannot be repaired safely.')+' Delete the book, then get a new copy.',warn:true};
  const producer=producerRecoveryText(row);if(producer)return producer;
  const a=attentionOf(row);if(!a)return null;
  const destination=a.destination_review;
  if(destination){
    if(destination.state!=='needs_review')return {status:'Destination unavailable — review this book',hint:destination.reason || 'The destination or review changed. Check the current details before retrying.',warn:true};
    const queued=readmissionOf(row);
    if(queued?.queued_next===true)return {status:/paused|stopped|idle/i.test(state?.audiobook_jobs?.state || '')?'Queued — queue paused':queuedNextText(queued),hint:'The saved job is kept. The current sources, review and destination are checked before a new job is created.'};
    return {status:'Queued destination needs review',hint:'This saved job uses a different destination. Retry checks the current book before creating a new job.',warn:true};
  }
  if(a.remedy?.kind==='replace_source' && a.remedy.cause==='source_decode_failed')return {status:'Source audio needs replacement',hint:"The MP3 failed its full audio check and can't be repaired by the app. Delete the book, then get a new copy.",warn:true};
  const kind=a.group==='retry'?(a.cause==='space'?'space':'retry'):a.group==='repair'?'repair':a.group==='unsupported'?'unsupported':a.group==='changed'?'changed':a.group==='audiobook'?(a.cause==='unverified'?'unverified':'missing'):'other',[status,hint]=attentionCopy[kind];
  const readmission=readmissionOf(row);
  if(readmission?.queued_next===true)return {status:queuedNextText(readmission),hint:readmission.kind==='repair'?damageHint(a):readmission.origin==='automatic'?AUTO_QUEUED_HINT:'The book is checked again before it runs.'};
  const refusal=refusalOf(row),verb=refusal?.kind==='repair'?'Repair':'Retry',clause=clearsFirst(row);
  if(refusal && refusal.stale!==true){
    const cause=refusalCause(refusal),[refusedStatus,copy]=refusalCopy[cause],untouched=cause==='unsupported_file' && a.originals_untouched===true?' Originals are untouched.':'';
    const text=cause==='source_changed'?STARTOVER_HINTS[a.startover==='manual_draft'?(a.release_ok===true?'combined':'manual_draft'):'automatic']:copy;
    return {status:verbed(refusedStatus,verb),hint:text?`${verb} was refused: ${verbed(text,verb)}${untouched}`:`${verb} was refused. The app did not report a specific reason.`,warn:true,clause};
  }
  // Leftover working files the app cannot clear stop the row: no control, and nothing Sergei can press fixes it here.
  if(a.working?.state==='blocked' && a.working.stops===true)return {status:BLOCKED_COPY[0],hint:a.working.cause==='originals_unreachable'?BLOCKED_COPY[2]:BLOCKED_COPY[1],warn:true};
  // Precedence after a current refusal: the dry run could not open the source (warning: Sergei can fix it), then it has
  // not finished (muted: it clears by itself), then a stale refusal, then ready.
  if(a.precheck==='unavailable')return {status:precheckCopy.unavailable[0],hint:precheckCopy.unavailable[1],warn:true,clause};
  if(a.precheck==='pending')return {status:precheckCopy.pending[0],hint:precheckCopy.pending[1]};
  // Stale: the app was updated since the refusal; it is information, not an obstacle (muted). A book whose read-only
  // check refuses again under this build is in M4B not supported and reads as that group. A row the dry run covers and
  // passed is ready again and says why; "Stopped — try again" is left for rows the dry run does not cover.
  if(refusal && a.group!=='unsupported'){
    const version=typeof refusal.app_version==='string' && refusal.app_version?refusal.app_version:'';
    if(a.precheck==='passed')return {status:attentionCopy.retry[0],hint:`${verb} was refused${version?' in v'+version:''}. The app was updated, and this M4B now passes its check.`,clause};
    return {status:'Stopped — try again',hint:version?`${verb} was refused in v${version}; the app was updated since. It may work now.`:`${verb} was refused before the app was updated. It may work now.`,clause};
  }
  return {status,hint:kind==='repair'?damageHint(a):kind==='retry' && a.remedy?.kind==='tag_repair'?TAG_REPAIR_HINT:kind==='unsupported' && a.originals_untouched===true?'Nothing to do for now. Originals are untouched.':hint,clause};
}
// " Retry clears leftover working files first." on a cleanable row whose Retry (or Repair) is enabled.
function clearsFirst(row){const action=workingOf(row)?.state==='cleanable'?rowAction(row):null;return action?.data?.allowed===true && CLEARS_FIRST[action.kind]?CLEARS_FIRST[action.kind][2]:'';}
// The Started over marker (follow-up 3, section 2.2; follow-up 4, sections 1.3 and 2): status words and a hint that says
// whether Sergei must act, composed with the live pass state. A null status keeps the existing status chain.
function restartText(row){
  const r=restartOf(row);if(!r || row.creation?.job && r.state!=='queued')return null;
  if(r.state==='queued')return row.creation?.job?{status:null,hint:'Queued by automatic processing after Start over. Nothing to do.'}:null;
  const auto=state?.automatic_processing,known=automaticStates.has(auto?.state) && !recoveryDisconnected && !ended,running=known && auto.state==='Running';
  const held=r.expect==='hold',release=held && r.release_expected===true;
  if(r.state==='held')return heldText(row,r);
  if(r.state==='failed'){
    if(known && !running && auto.can_start!==true && !startPending(auto))return {status:null,hint:`Automatic processing hit an error on this book. It can't start again yet. ${auto.start_block_reason || ''}`.trim(),warn:true};
    return {status:null,hint:'Automatic processing hit an error on this book. Press Start automatic processing above to try again.',warn:true};
  }
  if(!known)return {status:'Started over — waiting',hint:'Reconnecting to the app. This row updates when it is back.'};
  if(running && r.state==='working')return r.source_wait===true?{status:'Started over — waiting for a source',hint:'Nothing to do. A metadata source is busy. Automatic processing tries again by itself.'}:
    {status:'Started over — researching',hint:'Nothing to do. Automatic processing is looking this book up now. It queues the book if the match is safe.'};
  if(running && r.visit==='next_run')return {status:'Started over — next run',hint:'Automatic processing has already passed this book. Press Start automatic processing above after it finishes.',warn:true};
  if(running)return {status:'Started over — waiting its turn',hint:held?'Nothing to do yet. Automatic processing will hold this book because it has a saved review.'+(release?' Then Let the app handle it appears here.':''):'Nothing to do. Automatic processing will research this book and queue it if the match is safe.'};
  const pending=startPending(auto);
  if(pending){
    const when={conversion:'Automatic processing starts by itself when audiobook conversion finishes or is paused, then',scan:'Automatic processing starts by itself when the library scan ends or is stopped, then',stopping:'Automatic processing starts again by itself once it has stopped, then'}[pending];
    return {status:'Started over — waiting to start',hint:`Nothing to do. ${when} ${held?'holds this book because it has a saved review.'+(release?' Then Let the app handle it appears here.':''):'takes this book.'}`};
  }
  if(auto.can_start===true)return {status:'Started over — waiting for you',hint:held?'Press Start automatic processing above. It will then hold this book because it has a saved review'+(release?', and Let the app handle it appears here.':'.'):'Press Start automatic processing above. It will then research this book and queue it if the match is safe.',warn:true};
  return {status:'Started over — waiting for you',hint:`Automatic processing can't start yet. ${auto.start_block_reason || ''}`.trim(),warn:true};
}
// Held for a saved review (follow-up 3, sections 2.2 and 4): "saved review kept" when the button can release it.
function heldText(row,marker=null){
  const auto=row.automatic;
  if(auto?.hold==='manual_draft'){
    if(releaseOf(row))return {status:'Held — saved review kept',hint:'A saved review keeps this book held. Let the app handle it clears the preview draft and lets automatic processing take the book. Saved Entered by you evidence is kept.',warn:true};
    if(auto.lease===true)return marker?{status:'Held — Manual draft retained',hint:'You are editing this book. Automatic processing waits until you stop.'}:null;
    return marker?{status:'Held — Manual draft retained',hint:'Automatic processing holds this book because it has a saved review.'}:null;
  }
  if(!marker)return null;
  const retry=retryDate(auto?.retry_at);
  return {status:null,hint:`Nothing to do. Automatic processing couldn't approve this book safely. ${retry?'It tries again after '+retry+', while it is running.':'It tries again later, while it is running.'}`};
}
function releaseText(row){return releaseOf(row)?heldText(row):null;}
function rowState(row){
  const ask=askText(row);if(ask)return ask;
  const attention=attentionText(row);if(attention)return attention;
  const readmission=readmissionOf(row);if(readmission?.queued_next===true)return {status:queuedNextText(readmission),hint:readmission.origin==='automatic'?AUTO_QUEUED_HINT:QUEUED_HINT};
  return restartText(row) || releaseText(row);
}
// The two folded columns, as the second line of the title cell (medium and compact bands).
function titleFacts(row){const count=Array.isArray(row.members)?row.members.length:0;return `${(row.artists || []).join('; ') || 'Unknown'} · ${count.toLocaleString()} audio ${count===1?'file':'files'}`;}
// The Started over summary line (follow-up 3, section 2.3; follow-up 4, section 1.3): global counts, live pass state.
function renderRestartSummary(){
  const line=$('restart-summary');if(!line)return;
  const shown=view==='candidates' && filters[view]==='restarted' && !!restartCounts;line.hidden=!shown;if(!shown){if(line.textContent)line.textContent='';return;}
  const c=restartCounts,n=key=>Number.isInteger(c[key]) && c[key]>0?c[key]:0,total=n('waiting')+n('working')+n('held')+n('failed');
  const parts=[[n('waiting'),'waiting'],[n('working'),'being processed'],[n('held'),'held'],[n('failed'),'stopped on an error']].filter(([count])=>count>0).map(([count,label])=>`${count.toLocaleString()} ${label}`);
  const auto=state?.automatic_processing,running=auto?.state==='Running',pending=startPending(auto),tails=[];
  if(!running && (n('waiting') || n('working') || n('failed'))){
    if(pending)tails.push('Nothing for you to do. Automatic processing starts by itself when '+{conversion:'audiobook conversion finishes or is paused.',scan:'the library scan ends or is stopped.',stopping:'it has stopped.'}[pending]);
    else if(auto?.can_start===true)tails.push('Press Start automatic processing above.');
    else if(auto && typeof auto.can_start==='boolean')tails.push(`Automatic processing can't start yet. ${auto.start_block_reason || ''}`.trim());
  }
  if(running && n('next_run'))tails.push('Press Start automatic processing above after this run finishes.');
  if(n('release'))tails.push(`${n('release').toLocaleString()} held for a saved review: press Let the app handle it on a book to release it, or leave it held.`);
  const text=total?`${total.toLocaleString()} ${total===1?'book':'books'} started over: ${parts.join(', ')}. ${tails.length?tails.join(' '):'Nothing for you to do.'}`:'';
  if(line.textContent!==text)line.textContent=text;line.hidden=!text;
}
// What is wrong, then what Repair does; and, once queued or done, what it patched. Keyed by the patch kind.
const damageCopy={
  dangling_chapter_reference:{hint:'The chapter list points to a missing part. Repair removes that pointer.',patch:()=>'Removed a chapter-list pointer to a missing part.'},
  mdat_tail_overrun:{hint:'The file claims a few bytes past its end. Repair adds them; no audio is missing.',patch:item=>Number.isInteger(item.padding) && item.padding>0?`Added ${item.padding.toLocaleString()} missing bytes at the end of the file. No audio was missing.`:'Added the missing bytes at the end of the file. No audio was missing.'},
  truncated_final_frames:{hint:item=>missingSeconds(item)?`The last ${missingSeconds(item)} s of audio is missing. Repair fills it with silence.`:'The end of the audio is missing. Repair fills it with silence.',
    patch:item=>missingSeconds(item)?`Filled the missing last ${missingSeconds(item)} s with silence.`:'Filled the missing end of the audio with silence.'}};
function missingSeconds(item){const ticks=item?.replaced_ticks,scale=item?.timescale;return Number.isInteger(ticks) && Number.isInteger(scale) && ticks>0 && scale>0?(ticks/scale).toLocaleString(undefined,{maximumFractionDigits:2}):'';}
const damageFallback={hint:'The app found damage it can patch. Repair fixes it.',patch:()=>'Patched damage the app found.'};
function damageHint(attention){const items=Array.isArray(attention?.damage)?attention.damage:[];return [...new Set(items.map(item=>{const hint=(damageCopy[item?.kind] || damageFallback).hint;return typeof hint==='function'?hint(item):hint;}))].join(' ') || damageFallback.hint;}
function patchCopy(item){return (damageCopy[item?.kind] || damageFallback).patch(item && typeof item==='object'?item:{});}
function repairedText(repaired){
  const patched=Array.isArray(repaired?.patched)?repaired.patched:[];if(!patched.length)return '';
  return (repaired.applied===true?'Repaired: ':'Repair queued: ')+patchCopy(patched[0])+(patched.length>1?` +${patched.length-1} more`:'');
}
// Futaba's 0.22.0 QA, m-6: the spec's check 3 wins over the last bullet of its section 4.6. The cell tooltip never carries
// the raw reason (a decode wall or a local path); it repeats the row's plain sentence, and raw text is only in the open
// Technical details.
function cellTip(row){const producer=producerRecoveryText(row)?.tip;if(producer)return producer;const plain=askText(row)?.hint || attentionText(row)?.hint || '';return typeof plain==='string'?plain:'';}
// Futaba's 0.22.0 QA, m-2: a raw operating-system message ("Cannot protect exact file: [WinError 2] The system cannot find
// the file specified.") becomes one plain sentence wherever a reason is printed; the raw text stays in Technical details.
const OS_TEXT=/\[(?:WinError|Errno)\s*-?\d+\]|cannot find the (?:file|path) specified|Access is denied|Cannot protect exact file/i;
const OS_PLAIN="A source file is missing or can't be opened.";
// 0.22.2: a media check past its deadline is transient; a record saved before 0.22.2 never shows the raw text.
const MEDIA_SLOW_PLAIN='The library drive answered slowly while the app checked this book. It tries again automatically.';  // Judy 14.6
function plainReason(reason){return typeof reason==='string' && /^Owned (media operation|decode verification) exceeded its deadline$/.test(reason)?MEDIA_SLOW_PLAIN:typeof reason==='string' && OS_TEXT.test(reason)?OS_PLAIN:reason;}
function rawReasons(row){return (row?.automatic?.reasons || []).filter(reason=>typeof reason==='string' && OS_TEXT.test(reason));}
function technicalText(row){
  const ask=askOf(row);if(ask)return 'Technical detail: '+([...(ask.reasons || []),...rawReasons(row)].filter(item=>typeof item==='string' && item).join('; ') || 'Unavailable');
  const job=row?.creation?.job || {},attention=attentionOf(row),details=(attention?.damage || []).map(item=>item?.description).filter(text=>typeof text==='string' && text);
  if(typeof job.retry_parent_job_id==='string')details.push('Saved job retained: '+job.retry_parent_job_id);
  const destination=attention?.destination_review;if(destination?.state==='needs_review')details.push('Saved job destination: '+destination.old_destination,'Current proposed destination: '+destination.proposed_destination,'Saved job retained.');
  const producer=producerRecoveryOf(row);if(producer)details.push(['Producer recovery: '+producer.state,producer.cause,producer.reason,producer.checkpoint_id?'Checkpoint: '+producer.checkpoint_id:'',producer.attempt_id?'Attempt: '+producer.attempt_id:'',producer.retained_path].filter(value=>typeof value==='string' && value).join('; '));
  const raw=keptGroup(attention) && typeof attention.reason==='string' && attention.reason?attention.reason:job.reason;
  // A refused Retry/Repair keeps both facts for support: the refusal, then the earlier failure (either alone if single).
  // A dry run that could not open the source puts its own raw text first, in the same format.
  const refusal=refusalRecord(row),refused=typeof refusal?.reason==='string'?refusal.reason:'';
  const unopened=attention?.precheck==='unavailable' && typeof attention.precheck_reason==='string'?attention.precheck_reason:'';
  // Leftover working files: their own reason first (follow-up 2, section 2.3), then the earlier failure and the folder.
  const working=workingOf(row),files=typeof working?.reason==='string'?working.reason:'';
  if(attention?.reacquire){const r=attention.reacquire;return 'Affected source file: '+r.originals.map(s=>s.path).join('; ')+' — Audio problem: '+r.reason+' — Why replacement is needed: '+r.repair_limit+' — The amount of affected audio is not established. Delete book removes these files and the book. If you remove the originals yourself, the book is cleared after a completed scan confirms they are gone.'+(r.source_presence==='unavailable'?' Source unavailable — deletion not confirmed. Connect the source drive and scan again.':r.source_presence==='partially_missing'?' Some original files remain. The book stays listed until all its original source files are confirmed gone.':'');}
  const sourceFile=attention?.remedy?.kind==='replace_source' && typeof attention.remedy.path==='string'?attention.remedy.path:'';
  const first=(sourceFile?'Source to replace: '+sourceFile:'') || files || unopened || refused,facts=first && raw?`${first}; earlier failure: ${raw}`:first || raw;
  // Working files from an earlier attempt: the absolute folder, here only, never in the hint (follow-up, point 3c).
  const folder=(working || refusal && refusal.cause==='working_files' && refusal.stale!==true) && typeof attention?.working_folder==='string' && attention.working_folder?'; working folder: '+attention.working_folder:'';
  return 'Technical detail: '+(facts || rawReasons(row).join('; ') || 'Unavailable')+folder+(details.length?' — '+details.join(' '):'');
}
function candidateStatus(row){
  const ask=askText(row);if(ask)return askDone.has(row.id) && ASK_DONE[askDone.get(row.id)]?.[0] || ask.status;
  const attention=attentionText(row);if(attention)return attention.status;
  const readmission=readmissionOf(row);if(readmission?.queued_next===true)return queuedNextText(readmission);
  // Precedence (follow-up 3, section 2.2): attention, a queued-next press, the Started over marker, then the existing chain.
  const shown=restartText(row) || releaseText(row);if(shown?.status)return shown.status;
  const creation=row.creation?.status || '',status=row.status || '',automatic=row.automatic,job=row.creation?.job;
  // A job that needs attention leads with its own reason, so the status names what was blocked.
  const jobReason=job?.state==='Output needs attention' && typeof job.reason==='string'?job.reason:'';
  const cleanup=row.cleanup || {},reason=plainReason(jobReason || (automatic?.reasons || [])[0] || (row.creation?.reasons || [])[0] || cleanup.reason || '');
  const facts=[creation,status,cleanup.state || '',cleanup.temporary_cleanup || ''].join(' ');
  // A stopped job's own text is technical (an ffmpeg wall once reached the screen): it lives in Technical details only.
  if(/failed|attention|error/i.test(facts) || automatic?.state==='Needs attention')return jobReason?'Stopped — see details':'Needs attention'+(reason?' — '+reason:'');
  if(/changed/i.test(status))return 'Candidate changed';
  if(automatic?.state==='Held' && automatic.reasons?.includes('Manual draft retained'))return 'Held — Manual draft retained';
  if(row.duplicate_review?.state==='possible' && row.duplicate_review.blocking===true)return 'Held — Possible duplicate recording';
  if(row.audiobook_ready===true)return 'Audiobook Ready';
  if(/paused|pausing/i.test(facts))return 'Paused';
  if(/queued/i.test(creation) || /queued/i.test(status))return 'Queued';
  if(/creating|converting|encoding|checking|publishing|verifying/i.test(facts) || ['checking','preparing','removing','deleting'].includes(cleanup.state) || automatic?.state==='Researching')return 'Processing';
  if(automatic?.state==='Waiting for source')return 'Waiting for source';
  if(automatic?.state==='Held')return 'Held'+(reason?' — '+reason:'');
  if(row.audiobook_ready===undefined && /created|completed|converted/i.test(creation+' '+status))return 'Ready status unavailable';
  return 'Pending';
}
// Judy 0.22.2 section 4: the details panel's "Original title" fact (ruling 38: no wait, so no "Waiting" line).
function originalTitleFact(row){
  const lookup=row.metadata_facts?.original_title_lookup;
  if((row.review_context?.metadata_actor==='user' || (Array.isArray(row.entered) && row.entered.includes('title'))) && lookup)return 'Entered by you.';
  if(lookup?.state==='found' && typeof lookup.title==='string' && lookup.title)return lookup.title;
  if(lookup && ['none','russian'].includes(lookup.state))return lookup.state==='none'?'Not found. Filed under the Russian title.':'';
  return '';
}
function retryDate(value){if(typeof value!=='number' || !Number.isFinite(value) || value<=0)return '';const date=new Date(value<1e12?value*1000:value);return Number.isFinite(date.getTime())?recoveryDate(date.toISOString()):'';}
function renderAutomaticResult(row){
  $('automatic-result').hidden=row.kind!=='candidate';if(row.kind!=='candidate')return;
  renderProducerRetained(row);
  const key=JSON.stringify([state?.automatic_processing?.state,state?.automatic_processing?.automatic_retry_enabled,state?.automatic_processing?.can_start,state?.automatic_processing?.start_pending,row.restart,row.release,row.producer_recovery_retained,row.id,row.revision,row.automatic,row.metadata_approved,row.review,row.review_context,row.selected_cover,row.track_order,row.included,row.members,row.creation?.destination,row.creation?.status,row.creation?.job?.state,row.creation?.job?.reason,row.creation?.job?.attention,row.creation?.job?.repaired,row.creation?.job?.readmission,row.creation?.job?.kept,row.creation?.job?.keep,state?.audiobook_jobs?.current_job_id,row.status,row.audiobook_ready,row.cleanup,row.metadata_facts,row.duplicate_review,row.current_audiobook,row.ask,askDone.get(row.id)]);
  if(key===automaticResultKey)return;
  // Retry is updated in place by updateRetry(), never rebuilt here, so its focus does not freeze the status line.
  if($('automatic-result').contains?.(document.activeElement) && !$('retry-block').contains?.(document.activeElement))return;
  automaticResultKey=key;const automatic=row.automatic;
  setText('automatic-result-status',candidateStatus(row));
  const attention=rowState(row),kept=!attention && row.creation?.job?.kept===true;
  setText('automatic-result-hint',attention?attention.hint+(attention.clause || ''):kept?'You chose to keep these files.':'');$('automatic-result-hint').hidden=!attention?.hint && !kept;
  $('automatic-result-hint').classList?.toggle?.('retry-refused',!!attention?.warn);
  // After Repair: a permanent line and one bullet per patch; the technical note is the last line.
  const repaired=row.creation?.job?.repaired,patched=Array.isArray(repaired?.patched)?repaired.patched:[];
  setText('automatic-repaired-title',patched.length?(repaired.applied===true?'Repaired':'Repair queued'):'');$('automatic-repaired-list').replaceChildren(...patched.map(item=>node('li',patchCopy(item))));$('automatic-repaired').hidden=!patched.length;
  // A stopped job with no typed cause reads "Stopped — see details": its own text is here, in Technical details.
  const untyped=row.creation?.job?.state==='Output needs attention' && typeof row.creation.job.reason==='string' && row.creation.job.reason;
  const technical=attention || untyped || rawReasons(row).length?technicalText(row):patched.length && typeof repaired.detail==='string' && repaired.detail?'Technical detail: '+repaired.detail:'';
  setText('automatic-technical',technical);$('automatic-technical').hidden=!technical;if($('technical-details'))$('technical-details').hidden=!technical;
  // Names found (section 7): where the title and author came from, for the three name reasons.
  const ask=askOf(row),names=ask && ['title_author','author_unclear','same_author'].includes(askKind(ask))?askNames(ask):[];
  $('names-found-list')?.replaceChildren(...names.map(text=>node('li',text)));if($('names-found'))$('names-found').hidden=!names.length;
  $('automatic-reasons').replaceChildren();for(const reason of new Set((automatic?.reasons || []).map(plainReason)))$('automatic-reasons').append(node('li',reason));$('automatic-reasons').hidden=!automatic?.reasons?.length;
  $('automatic-result-help').hidden=automatic?.state!=='Held';
  setText('automatic-attempt',automatic?.attempted_utc?'Last attempt: '+recoveryDate(automatic.attempted_utc):'No automatic research attempt recorded.');
  const run=state?.automatic_processing,automaticContinuation=run?.state==='Running' && typeof run.automatic_retry_enabled==='boolean';
  const retry=retryDate(automatic?.retry_at);setText('automatic-retry',retry?'Automatic retry after '+retry+(automaticContinuation?'':'; Start to continue'):'');$('automatic-retry').hidden=!retry;
  const wait=automatic?.wait,source=typeof wait?.source==='string'?wait.source:'';
  const waitText=wait?{app_limit:source?'App request limit reached for '+source:'App metadata request limit reached',source_pause:source?source+' requested a pause':'Metadata source requested a pause',source_unavailable:source?source+' unavailable':'Metadata source unavailable'}[wait.kind]:'';
  if(waitText){$('automatic-reasons').append(node('li',waitText));$('automatic-reasons').hidden=false;}
  const facts=$('automatic-facts');facts.replaceChildren();const approval=recordedApproval(row),review=row.review || {},context=row.review_context || {};
  const current=row.current_audiobook,actual=current?.state==='verified'?current.path:current?.state==='none' || !current?'No verified audiobook created yet':'Current audiobook unavailable'+(current.reason?' — '+current.reason:'');
  const values=approval?{'Canonical title':review.title,'Original work language':review.original_language,Author:review.canonical_author,'Reader / narrator':review.narrator,Series:review.series,'Series position':review.number,Cover:row.selected_cover?.source_label || 'Cover details unavailable','Reviewed destination':row.creation?.destination || 'Destination unavailable','Current audiobook':actual}:{'Title clue':row.title_clue || 'Unknown','Reviewed destination':row.creation?.destination || 'No verified destination yet','Current audiobook':actual};
  if(restartOf(row)?.at)values['Started over']=recoveryDate(restartOf(row).at);
  Object.assign(values,provenanceFacts(row),recordingFacts(row));if(row.metadata_facts?.series_state==='omitted_unknown')delete values['Series position'];
  const original=originalTitleFact(row);if(original)values['Original title']=original;  // Judy 0.22.2 section 4
  for(const [label,value] of Object.entries(values))if(value!==undefined && value!==null && value!=='')facts.append(node('dt',label),node('dd',value));
  const included=new Set(row.included || row.members?.map(member=>member.member_key || member.path) || []),members=new Map((row.members || []).map(member=>[member.member_key || member.path,member]));
  $('automatic-tracks').replaceChildren();for(const key of row.track_order || members.keys())if(included.has(key) && members.has(key))$('automatic-tracks').append(node('li',[members.get(key).path,...memberComponents(members.get(key),row),members.get(key).missing?'Not found':''].filter(Boolean).join('\n')));
  const sources=$('automatic-sources');sources.replaceChildren();if(automatic?.sources?.length){sources.append(node('h3','Research sources'));for(const source of automatic.sources){const line=node('p');let label=source.provider || source.kind || 'Public source';try{label+=' — '+new URL(source.url).hostname;}catch{}line.append(source.kind==='manual_metadata'?node('span','Entered by you'):sourceLink(source.url,label));const facts=[source.verified_identity===true?'Identity verified':source.verified_identity===false?'Identity unverified':'',typeof source.credit==='object' && source.credit!==null?[source.credit.author,source.credit.title].filter(Boolean).join(' — '):source.credit,source.retrieved_utc?'Retrieved '+recoveryDate(source.retrieved_utc):''].filter(Boolean);if(facts.length)line.append(node('span',' · '+facts.join(' · ')));sources.append(line);}}
  const accepted={metadata:context.metadata_evidence || [],recording:context.track_evidence || '',metadata_provenance:row.metadata_facts || null,recording_review:row.duplicate_review || null};
  $('automatic-accepted-evidence').textContent=plainEvidence(JSON.stringify(accepted,null,2));$('automatic-accepted').hidden=!accepted.metadata.length && !accepted.recording && !accepted.metadata_provenance && !accepted.recording_review;
}
async function ensureCandidateInspector(row){
  const identity=recordIdentity(row),key=JSON.stringify([identity,row.revision,row.creation?.status,row.audiobook_ready,row.cleanup,row.metadata_facts,row.duplicate_review,row.current_audiobook]);
  if(recoveryDisconnected || automaticInspectorKey===key || $('metadata-inspector').contains?.(document.activeElement))return;
  automaticInspectorKey=key;inspectorIdentity=identity;const sequence=++inspectSequence;$('metadata-inspector').hidden=false;
  setText('inspect-status','Reading metadata and artwork…');
  try{const result=await request('/api/inspect',identity);if(sequence!==inspectSequence || selectedPath!==row.path || ended)return;if($('metadata-inspector').contains?.(document.activeElement)){automaticInspectorKey=null;setText('inspect-status','');return;}renderInspector(result.inspector,row,sequence);setText('inspect-status',result.inspector?'':'Metadata inspection unavailable');}
  catch(error){if(sequence===inspectSequence){automaticInspectorKey=null;setText('inspect-status',error.message);}}
}
function draftStatus(){
  const value=draftLeaseFailure?'Manual draft protection unavailable: '+draftLeaseFailure:manualDraftLease?.active?(manualDraftLease.confirmed?'Manual draft retained; automatic processing holds this candidate.':'Saving manual draft protection…'):'';
  setText('draft-protection-status',value);$('draft-protection-status').hidden=!value;controls();
}
function sendDraftLease(scope){
  scope.lastSent=Date.now();scope.confirmed=false;draftStatus();
  draftLeaseQueue=draftLeaseQueue.catch(()=>{}).then(async()=>{
    try{await request('/api/automatic/draft',{id:scope.id,revision:scope.revision,active:scope.active});if(manualDraftLease===scope){scope.confirmed=true;draftLeaseFailure='';if(!scope.active)manualDraftLease=null;}}
    catch(error){if(manualDraftLease===scope){scope.confirmed=false;draftLeaseFailure=error.message || 'The local server could not retain this draft.';}}
    finally{draftStatus();}
  });
}
function syncManualDraft(){
  const active=selectedRow?.kind==='candidate' && ((manualMetadataTouched && dirty) || (manualTrackTouched && trackDirty));
  const row=dirty?(reviewRow || selectedRow):selectedRow;
  const revision=manualTrackTouched && trackDirty?trackDraft?.revision:row?.revision;
  if(manualDraftLease?.id===row?.id && manualDraftLease?.revision===revision && manualDraftLease?.active===active)return;
  const previous=manualDraftLease;draftLeaseFailure='';
  if(active){
    if(previous?.active && previous.id!==row.id)sendDraftLease({...previous,active:false});
    manualDraftLease={id:row.id,revision,active:true,confirmed:false};
  }else manualDraftLease=previous?{...previous,revision:selectedRow?.id===previous.id?selectedRow.revision:previous.revision,active:false,confirmed:false}:null;
  if(manualDraftLease)sendDraftLease(manualDraftLease);else draftStatus();
}
function discardManualDraft(){
  manualMetadataTouched=false;manualTrackTouched=false;
  if(manualDraftLease?.active){manualDraftLease={...manualDraftLease,revision:selectedRow?.id===manualDraftLease.id?selectedRow.revision:manualDraftLease.revision,active:false,confirmed:false};sendDraftLease(manualDraftLease);}
  draftStatus();
}
function renewManualDraft(){if(!recoveryDisconnected && manualDraftLease && Date.now()-manualDraftLease.lastSent>=45000){if(!manualDraftLease.active && selectedRow?.id===manualDraftLease.id)manualDraftLease.revision=selectedRow.revision;sendDraftLease(manualDraftLease);}}

// ---------------------------------------------------------------------------------------------------------------------
// The one to-do list (Judy, BooksArranger_AttentionTodo_UX_2026-10-24; Sergei's rulings 6a, 6b, 10, 11a, 12, 14). A book
// only Sergei can move on carries an "ask" from the server (merge_service.ask_payload): its reason, the names Approve
// would use, where it would be filed, its missing files. Rows update in place; typed text stays in memory per book
// until Approve; Approve sends only what Sergei changed, so nothing typed means "as is". The UI maps kinds to its own
// words and never shows the server's English for them.
const ASK_COPY={title_missing:['Title missing','No title in the tags, file name or folder name.'],author_missing:['Author missing','No author in the tags, file name or folder name.'],
  both_missing:['Title and author missing','No title or author in the tags, file name or folder name.'],garbled:['Tags unreadable',"The tags show garbled text, so they aren't used."],
  two_people:['Author unclear',"Two people are credited. The app can't tell who wrote it."],tag_and_name:['Author unclear','The tags and the folder name give different authors.'],
  names_differ:['Author unclear','The file name and the folder name give different authors.'],reader:['Author unclear',"The only name credited may be the reader. The app can't tell who wrote it."],
  name_taken:['Name taken','A book with this name is already in Audiobooks Sorted.'],other:['Needs you','This book needs your decision.'],
  // Odd names (0.22.1, Q3): the engine asks instead of filing a name that looks wrong; nothing is renamed by itself.
  // One sentence each, saying only what the engine tests (Judy's section 11).
  title_bitrate:['Title unclear','The title ends with a number that looks like a bitrate.'],
  title_series:['Title unclear','The title starts with what looks like a series name and number.'],
  title_latin:['Title unclear','The title looks like Russian written in Latin letters.'],
  author_folder:['Author unclear',"The author's name has underscores and may include more than a name."],
  // Ruling 33 (Sergei 2026-10-26): a Latin name with a Russian first name; one folder per person, by writing language.
  name_language:['Author unclear',"The author's name is in Latin letters. The app can't tell if they write in Russian."],
  // Ruling 39 (Sergei 2026-10-27): a foreign author credited only in Russian letters whose English spelling the lookup
  // didn't find (Judy's 0.22.2 doc, 15.1). The answer is kept for every book of this author.
  english_spelling:['Author unclear',"The app found no English spelling of this author's name online. Type one under Other, or keep this name if the author writes in Russian."]};
const ODD_TITLE=['title_bitrate','title_series','title_latin'];
// The three hold rows (Judy 2026-10-24, 0.22.0 review B4): status, then one sentence per typed cause; 'unknown' too.
const HOLD_STATUS={part_of_book:'Part of a bigger book',files_unclear:'Files unclear',order_unclear:'Order unclear'};
function holdSentence(kind,cause,f={}){
  const n=value=>Number.isInteger(value)?value:Number(value) || 0;
  if(kind==='order_unclear')return {no_tracks:'No file has a track number. The order comes from the file names.',
    some_missing:`${n(f.missing)} of ${n(f.total)} files ${n(f.missing)===1?'has':'have'} no track number.`,tied:'Some files share a track number.',
    gaps:"Track numbers skip or don't start at 1.",
    conflict:'The file names and the track tags number the files differently.',odd_tracks:"Some track tags aren't plain numbers."}[cause] || "The app can't be sure of the playback order.";
  if(kind==='files_unclear')return {track_total:`The tags say ${n(f.tags_say)} tracks, but ${n(f.here)} ${n(f.here)===1?'file is':'files are'} here.`,
    disc_total:`The tags say ${n(f.tags_say)} discs, but ${n(f.here)} ${n(f.here)===1?'is':'are'} here.`,
    one_of_many:`This file is tagged as track ${n(f.index)} of ${n(f.total)}. The other tracks aren't here.`,
    lack_title:n(f.missing)===1?`1 of ${n(f.total)} files doesn't mention this book's title.`:`${n(f.missing)} of ${n(f.total)} files don't mention this book's title.`,
    mixed:'The files carry different albums or artists. They may be more than one book.',works:'The title tags name more than one book.',
    parts:"The parts of this set don't number cleanly."}[cause] || "The app can't be sure which files belong to this book.";
  if(kind==='part_of_book')return {chapter:'This file is named as one chapter.',numbered_part:'The name marks this as one numbered part.',
    siblings:n(f.beside)===1?'Another file beside it carries the same title.':`${n(f.beside)} other files beside it carry the same title.`,
    part_set:`Part ${n(f.index)} of ${n(f.total)} of "${f.set || ''}".`,unreadable:"The other files in this folder couldn't be checked.",
    // Rulings 19 and 19a: a set of .m4b parts its chapters don't settle (Judy's part-sets copy check, 2026-10-25: the
    // evidence, then what it makes uncertain, in one sentence); the files show the proposed order.
    set_seasons:'Season or episode numbers in the names or chapters suggest separate books.',
    set_book_words:'The names or chapters number the files as books, so they may be separate books.',
    set_long:`Together these ${n(f.parts)} files run ${Math.round((Number(f.hours) || 0)*10)/10} hours, which is long for one book.`,
    set_authors:'The files credit different authors or readers, so they may be separate books.',
    set_unclear:"The chapters don't show whether these files make one book.",
    set_unreadable:"The chapters couldn't be read, so the app can't tell whether these files make one book."}[cause] || "The app can't tell if this is a whole book.";
  return '';
}
const HOLD_APPROVE={order_unclear:['Approve this order','Approve the order shown: convert if needed, rename, move to Audiobooks Sorted.'],
  files_unclear:['Approve these files','Approve the files shown as one book: convert if needed, rename, move to Audiobooks Sorted.'],
  part_of_book:['Approve as one book','File what is shown as one whole book: convert if needed, rename, move to Audiobooks Sorted.']};
const BASIS_LINES={number_rule:'Set name + part number.',file_name:'Title from the file name.',folder_name:'Title from the folder name.'};
const ASK_LABELS={approve:'Approve',separate:'Keep as separate books',scan:'Scan again',convert:"Convert what's there",remove:'Remove from list',order:'Change order',choose:'Choose files',delete:'Delete book',copy:'Remove this copy'};
const ASK_TIPS={approve:'Approve with the values shown: convert if needed, rename, move to Audiobooks Sorted. Ctrl+Enter in a field does the same.',
  // Keep as separate books (Judy 2026-10-25): the other answer to a set row; it records, approves nothing, touches no file.
  separate:'Make each file shown its own book. Nothing is joined. Each book is checked again.',
  scan:"Look for the missing files in this book's folders. Nothing is changed or deleted.",convert:'Convert the files that are present and leave out the missing ones.',
  remove:'Stop listing this book. No files are touched. A scan lists it again if its files return.',
  order:'Change the playback order in the details panel. Save it there, then approve.',choose:'Choose which files belong in the details panel. Save it there, then approve.',
  // Delete book (Judy 2026-10-25): two variants, by the offer's present count.
  delete:{files:"Delete this book's files from disk and remove the book from the app. You confirm first.",none:'Remove this book from the app for good. No files are left to delete. You confirm first.'},
  // Remove this copy (Judy's update spec 3.2, ruling 25); {sorted} is the Sorted folder's name (sortedText).
  copy:"Delete this copy's files from disk. The app shows the audiobook in {sorted} first, and you confirm."};
const HOLD_SCAN_TIP="Check this book's folders again, for example after you rename or add files. Nothing is changed or deleted.";
function holdKind(ask){return Object.hasOwn(HOLD_STATUS,ask?.kind || '')?ask.kind:'';}
// The face and tooltip follow the chip, so the press says what is confirmed (B4 Buttons).
function askLabel(entry,kind){const hold=holdKind(askOf(entry.row));return kind==='approve' && hold?HOLD_APPROVE[hold][0]:ASK_LABELS[kind];}
// A set of .m4b parts (cause set_*): the join always re-encodes once (ruling 19a, method A), so the tooltip says so (N3).
const SET_APPROVE_TIP='Join the files shown, in this order, into one book: re-encode the audio once, rename, move to Audiobooks Sorted.';
function setCause(ask){return holdKind(ask)==='part_of_book' && String(ask?.cause || '').startsWith('set_');}
function askTip(entry,kind){const ask=askOf(entry.row),hold=holdKind(ask);if(kind==='approve' && setCause(ask))return SET_APPROVE_TIP;return kind==='approve' && hold?HOLD_APPROVE[hold][1]:kind==='scan' && hold?HOLD_SCAN_TIP:kind==='approve' && inlineNames(entry.row)?'Approve this book with the author, title, series and number shown. Queued work waits for Start. Ctrl+Enter in a field does the same.':ASK_TIPS[kind];}
const ASK_PENDING={delete:['Checking...',"Checking this book's files..."],copy:['Checking...','Checking the audiobook in {sorted}...'],approve:['Approving...','Approving this book...'],separate:['Keeping...','Keeping these files separate...'],convert:['Queuing...','Queuing this book...'],scan:['Scanning...',"Scanning this book's folders..."],remove:['Removing...','Removing this book from the list...']};
const ASK_DONE={approve:['Queued','Approved. Converts if needed, then renames and moves it to Audiobooks Sorted.'],convert:['Queued','Approved without the missing files. Converts, renames and moves it to Audiobooks Sorted.'],
  found:[null,'Files found. The book is checked again.'],separate:[null,'Kept as separate books. Each is checked again.'],removed:[null,'Removed from the list. No files were touched.'],
  changed:[null,'Changes found. The book is checked again.'],deleted:[null,'Deleted. The book is gone from the app.'],copy_removed:[null,'Removed. The copy is gone from the app.'],later:[null,'Changes found. The next library scan will pick them up.']};
const ASK_REFUSED={delete:'Delete was not accepted. Nothing was deleted.',copy:'Remove was not accepted. Nothing was deleted.',approve:'Approve was not accepted. Nothing was changed.',separate:'Keep as separate books was not accepted. Nothing was changed.',convert:'Convert was not accepted. Nothing was changed.',scan:'Scan did not finish. Nothing was changed.',remove:'Remove from list was not accepted. Nothing was changed.'};
function askOf(row){const ask=row?.kind==='candidate'?row.ask:null;return ask && typeof ask==='object' && typeof ask.kind==='string'?ask:null;}
function askKind(ask){return ask.kind==='files_missing'?ask.also || '':ask.kind;}
function askName(row){return row.title_clue || row.review?.title || 'Book';}
function askDraft(id){if(!askDrafts.has(id))askDrafts.set(id,{seq:0,previewKey:'{}',timer:null});return askDrafts.get(id);}
function askProposal(ask,name){const value=ask?.fields?.[name]?.proposal;return typeof value==='string'?value:'';}
function plural(n,one,many){return `${n.toLocaleString()} ${n===1?one:many}`;}
// Which fields the row shows: Title when it is missing or a guess, Author when it is missing or unclear (section 3).
function inlineNames(row){const ask=askOf(row);return !!ask && (['author_unclear','same_author'].includes(askKind(ask)) || askKind(ask)==='title_author' && (!!askFieldPlanOf(ask).author || ask.why==='title_series'));}
function askFieldPlan(ask,row=null){
  const plan=askFieldPlanOf(ask);
  if(row && inlineNames(row))return {...plan,title:true,author:namesOpen(row.id)?plan.author || 'input':plan.author};
  // Edit names open (Judy 1.1, item 2): Title and Author are the editor's, the same inputs and draft as the ask fields.
  if(row && namesOpen(row.id) && !(ask.kind==='files_missing' && !(ask.missing?.present>0)))return {title:true,author:plan.author || 'input'};
  return plan;
}
function askFieldPlanOf(ask){
  if(ask.kind==='files_missing' && !(ask.missing?.present>0))return {title:false,author:null};
  const kind=askKind(ask),guess=Object.hasOwn(BASIS_LINES,ask.fields?.title?.basis),why=ask.why;let plan={title:false,author:null};
  if(kind==='title_author')plan={title:guess || ['title_missing','both_missing','garbled',...ODD_TITLE].includes(why),author:!askProposal(ask,'author') || ['author_missing','both_missing','garbled','author_folder'].includes(why)?'input':null};
  else if(kind==='author_unclear')plan={title:guess,author:'radio'};
  else if(kind==='same_author')plan={title:false,author:'same'};
  else if(kind==='name_taken')plan={title:true,author:'input'};
  // Part of a bigger book always shows Title (the question is "is it a whole book, and what is it called?", B4).
  else if(kind==='part_of_book')plan={title:true,author:!askProposal(ask,'author')?'input':null};
  plan.title=plan.title || !askProposal(ask,'title');
  return plan;
}
// What Approve sends: only what Sergei changed. forPreview turns a same-author choice into the name it files under.
function askValues(row,forPreview=false){
  const ask=askOf(row),d=askDrafts.get(row.id) || {},plan=askFieldPlan(ask,row),values={},title=askProposal(ask,'title'),author=askProposal(ask,'author');
  if(plan.title && typeof d.title==='string' && d.title.trim()!==title)values.title=d.title.trim();
  if(plan.author==='input' && typeof d.author==='string' && d.author.trim()!==author)values.author=d.author.trim();
  if(plan.author==='radio' && d.choice){const name=d.choice==='other'?(d.other || '').trim():ask.candidates?.[Number(d.choice.slice(1))]?.name;if(typeof name==='string' && name!==author)values.author=name;}
  if(plan.author==='same' && d.choice){if(d.choice==='other')values.author=(d.other || '').trim();else if(forPreview)values.author=(d.choice==='same'?ask.same_author?.existing:ask.same_author?.new) || '';else values.choice=d.choice;}
  return values;
}
function askTitleEmpty(row){const ask=askOf(row),d=askDrafts.get(row.id) || {};return askFieldPlan(ask,row).title && typeof d.title==='string'?!d.title.trim():!askProposal(ask,'title');}
function askDestination(row){const d=askDrafts.get(row.id);return d?.preview || askOf(row)?.destination || null;}
function outputName(){const root=state?.audiobook_output_root;return typeof root==='string' && root.trim()?root.replace(/[\\/]+$/,'').split(/[\\/]/).pop():'Audiobooks Sorted';}
// Why Approve does nothing yet ('' when it works): the press is prevented rather than refused.
function askInert(row){
  if(askTitleEmpty(row))return 'Type a title first.';
  const names=namesFor(row);  // Edit names open (Judy 1.3): Series and Number go together
  if(names?.series && !names.number)return 'Type the number in the series, or clear the series.';
  if(names?.number && !names.series)return 'Type the series name, or clear the number.';
  if(askDestination(row)?.taken===true)return 'That name is already in Audiobooks Sorted. Change the title or author.';
  return askPanelEdits(row);
}
// Unsaved metadata, order or file edits in the panel for this book (Judy 2026-10-24, 0.22.0 review A5: trackDirty too). The
// only test Keep as separate books takes: the Title field and a taken name belong to the join.
// 0.22.3 (Sergei 2026-10-27, «Крысы», «Крампус»): only edits Sergei made count (manual*Touched, the draft lease's own
// test). Selecting a multi-MP3 book applies the panel's chapter default as trackDirty, which is not his edit, and it locked
// every such row's Save and Approve with nothing to discard.
function askPanelEdits(row){
  if((dirty && manualMetadataTouched && (reviewRow || selectedRow)?.id===row.id) || (trackDirty && manualTrackTouched && (trackDraft?.id ?? selectedRow?.id)===row.id))return panelEditsLine();
  return '';
}
function askText(row){
  const ask=askOf(row);if(!ask)return null;
  if(ask.kind==='files_missing'){
    const total=Number(ask.missing?.total) || 0,present=Number(ask.missing?.present) || 0,gone=Math.max(0,total-present);
    // Parts the track tags say exist but were never here (a part set, N4): where the claim comes from.
    const parts=Array.isArray(ask.missing?.parts)?ask.missing.parts:null;
    if(parts && parts.length)return {status:'Missing files',hint:parts.length===1?`The track tags say there are ${total.toLocaleString()} parts, but part ${Number(parts[0]).toLocaleString()} isn't here.`:`The track tags say there are ${total.toLocaleString()} parts, but ${parts.length.toLocaleString()} aren't here.`};
    return present>0?{status:'Missing files',hint:`${gone.toLocaleString()} of ${total.toLocaleString()} files ${gone===1?'is':'are'} missing.`}:{status:'All files missing',hint:`All ${total.toLocaleString()} files are missing.`};
  }
  // A verified duplicate with the server's Remove this copy offer: the row says what it is (Judy's update spec 3.1).
  if(copyOffer(row))return {status:ASK_COPY.other[0],hint:sortedText(COPY_HINT)};
  if(ask.kind==='same_author')return {status:'Same author?',hint:`Is "${ask.same_author?.new || ''}" the same author as "${ask.same_author?.existing || ''}"?`};
  if(holdKind(ask))return {status:HOLD_STATUS[ask.kind],hint:holdSentence(ask.kind,ask.cause,ask.facts || {})};
  const copy=ASK_COPY[['title_author','author_unclear'].includes(ask.kind)?ask.why:ask.kind] || ASK_COPY[{title_author:'both_missing',author_unclear:'two_people'}[ask.kind] || 'other'];
  return {status:copy[0],hint:copy[1]};
}
// "Also:" takes the first sentence only (0.22.0 review A1a): "Also: the only name credited may be the reader."
function askAlso(ask){
  const text=!ask.also?'':Object.hasOwn(HOLD_STATUS,ask.also)?holdSentence(ask.also,ask.also_cause,ask.also_facts || {}):ASK_COPY[ask.why]?.[1] || '';
  const first=text.split(/(?<=\.)\s/)[0];return first?'Also: '+first[0].toLowerCase()+first.slice(1):'';
}
// Other's catch-all: the app's own short reason, when it is one line of 80 characters or fewer (B3).
function askReason(ask){const reason=typeof ask.reason==='string'?ask.reason.trim():'';return ask.kind==='other' && reason && reason.length<=80 && !/[\r\n]/.test(reason)?'Reason: '+reason:'';}
function sameWhy(ask){
  const why=ask.same_author?.why,books=Number(ask.same_author?.existing_books) || 0;
  if(why==='translation')return 'Same name in another language.';
  if(why==='near')return `Spelled almost like an author you have (${plural(books,'book','books')}).`;
  if(why==='pen_name')return 'May be a pen name of an author you have.';
  return typeof why==='string' && why.length<=70?why:'';
}
// The tag beside an Author unclear choice. Ruling 39's one choice is the credit's Cyrillic spelling (Judy 15.1: "Russian
// spelling", pairing with the hint's "English spelling"); ruling 33's pair keeps "spelling".
function candidateTag(ask,c){return ask?.why==='english_spelling' && c?.source==='spelling'?'Russian spelling':c?.source;}
function askNames(ask){
  const basis={tag:'tag',file_name:'file name',folder_name:'folder name',number_rule:'set name + part number',entered:'entered by you'},lines=[];
  if(askProposal(ask,'title'))lines.push(`Title: ${askProposal(ask,'title')} - ${basis[ask.fields.title.basis] || 'proposed'}`);
  const candidates=Array.isArray(ask.candidates)?ask.candidates:[];
  for(const c of candidates)if(typeof c?.name==='string')lines.push(`Author: ${c.name} - ${candidateTag(ask,c) || 'proposed'}`);
  if(!candidates.length && askProposal(ask,'author'))lines.push(`Author: ${askProposal(ask,'author')} - ${basis[ask.fields.author.basis] || 'proposed'}`);
  if(ask.same_author?.existing)lines.push(`Author you have: ${ask.same_author.existing} (${plural(Number(ask.same_author.existing_books) || 0,'book','books')})`);
  return lines;
}
// Fields, radios and their labels keep clicks and keys from the row (a space typed in a title must not select it).
// Enter refreshes the Goes to line; Ctrl+Enter presses the row's Approve (never Enter alone: approval moves files).
function guardAskControl(entry,element,keys=false){
  element.addEventListener('click',event=>event.stopPropagation());
  if(keys)element.addEventListener('keydown',event=>{event.stopPropagation();if(event.key!=='Enter')return;event.preventDefault?.();if(event.ctrlKey)askPrimary(entry);else askPreview(entry,0);});
}
function askInput(entry,name,label,value,placeholder,tip){
  const wrap=node('label','','ask-field'),input=node('input');input.type='text';input.maxLength=1000;input.setAttribute('maxlength','1000');input.setAttribute('autocomplete','off');input.setAttribute('spellcheck','false');
  input.dataset.name=name;input.value=value;input.title=tip;if(placeholder)input.placeholder=placeholder;input.setAttribute('aria-label',label+': '+askName(entry.row));
  wrap.append(node('span',label),input);guardAskControl(entry,wrap);guardAskControl(entry,input,true);
  input.addEventListener('input',()=>{askDraft(entry.row.id)[name]=input.value;askChanged(entry,500);});
  input.addEventListener('blur',()=>askPreview(entry,0));
  entry.controls.push(input);return wrap;
}
function askRadio(entry,group,value,label,tip,extra=''){
  const wrap=node('label','','ask-radio'),input=node('input'),d=askDraft(entry.row.id);input.type='radio';input.name=group;input.value=value;input.title=tip;input.checked=d.choice===value;
  wrap.append(input,node('span',label));if(extra)wrap.append(node('span',extra,'field-help'));
  guardAskControl(entry,wrap);guardAskControl(entry,input,true);
  input.addEventListener('change',()=>{if(!input.checked)return;d.choice=value;if(value==='other')entry.other?.focus?.({preventScroll:true});askChanged(entry,0);});
  entry.controls.push(input);return wrap;
}
function buildAskFields(entry){
  const row=entry.row,ask=askOf(row),plan=askFieldPlan(ask,row),d=askDraft(row.id),box=entry.fields,inline=inlineNames(row);
  if(plan.title && !inline || plan.author==='input'){
    const grid=node('div','','ask-grid');
    if(plan.title && !inline){const cell=node('div');cell.append(askInput(entry,'title','Title',typeof d.title==='string'?d.title:askProposal(ask,'title'),'','The title this book is filed under.'));const basis=BASIS_LINES[ask.fields?.title?.basis];if(basis)cell.append(node('p',basis,'field-help ask-basis'));grid.append(cell);}
    if(plan.author==='input'){const cell=node('div');cell.append(askInput(entry,'author','Author',typeof d.author==='string'?d.author:askProposal(ask,'author'),'Empty files it under Без автора.','The author this book is filed under. Leave empty to use Без автора.'));if(ask.fields?.author?.basis==='folder_name' && askProposal(ask,'author'))cell.append(node('p','Author from the folder name.','field-help ask-basis'));grid.append(cell);}
    box.append(grid);
  }
  if(plan.author!=='radio' && plan.author!=='same')return;
  // A native radio group: one Tab stop, arrow keys inside. Author unclear preselects the app's best guess (never a
  // reader of other books while another exists, ruling 14); Same author? preselects nothing (ruling 12).
  const set=node('fieldset','','ask-choice'),group='ask-author-'+row.id;set.append(node('legend','Author'));
  if(plan.author==='radio'){
    const author=askProposal(ask,'author'),candidates=(Array.isArray(ask.candidates)?ask.candidates:[]).filter(c=>typeof c?.name==='string');
    if(d.choice===undefined){const index=candidates.findIndex(c=>c.name===author);d.choice=index>=0?'c'+index:null;}
    candidates.forEach((c,i)=>{const readers=Number.isInteger(c.reader_count) && c.reader_count>0?`reader on ${plural(c.reader_count,'other book','other books')}`:'';set.append(askRadio(entry,group,'c'+i,c.name,`Use ${c.name} as the author.`,[candidateTag(ask,c),readers].filter(Boolean).join(' · ')));});
  }else{
    const s=ask.same_author || {};
    set.append(askRadio(entry,group,'same',`Same author: use "${s.existing || ''}"`,`Use ${s.existing || ''} as the author.`),askRadio(entry,group,'different',`Different author: keep "${s.new || ''}"`,`Use ${s.new || ''} as the author.`));
  }
  set.append(askRadio(entry,group,'other','Other','Type a different author.'));
  const other=node('input','','ask-other');other.type='text';other.maxLength=1000;other.setAttribute('maxlength','1000');other.setAttribute('autocomplete','off');other.setAttribute('spellcheck','false');
  other.placeholder='Another author';other.value=d.other || '';other.title='Type a different author.';other.setAttribute('aria-label','Other author: '+askName(row));
  guardAskControl(entry,other,true);
  other.addEventListener('input',()=>{d.other=other.value;d.choice='other';const radio=entry.controls.find(c=>c.type==='radio' && c.value==='other');if(radio)radio.checked=true;askChanged(entry,500);});
  other.addEventListener('blur',()=>askPreview(entry,0));
  entry.other=other;entry.controls.push(other);set.append(other);box.append(set);
  // While nothing is chosen, say what Approve alone does (0.22.0 review A2 and A3).
  entry.nochoice=node('p',plan.author==='same'?'No choice files it as written. Nothing is remembered.':'No choice files it under Без автора.','field-help ask-nochoice');box.append(entry.nochoice);
  if(plan.author==='same'){box.append(node('p','A choice is remembered for other books with these names.','field-help'));const count=Number(ask.same_author?.count) || 0;if(count>1)box.append(node('p',`Applies to ${count.toLocaleString()} books.`,'field-help'));}
}
// Missing files: the folder once on an "In" line, then each file name; up to 3 in the row (section 4.4).
function buildAskMissing(entry){
  const missing=askOf(entry.row).missing,files=Array.isArray(missing?.files)?missing.files.filter(f=>typeof f==='string'):[];if(!files.length)return;
  const parent=path=>path.slice(0,Math.max(path.lastIndexOf('\\'),path.lastIndexOf('/'))+1),folders=[...new Set(files.map(parent))];let shown=0;
  for(const folder of folders){if(shown>=3)break;entry.missing.append(node('p','In '+folder,'path'));for(const file of files.filter(f=>parent(f)===folder)){if(shown>=3)break;entry.missing.append(node('p',file.slice(folder.length),'path'));shown++;}}
  // A part set's missing parts are not in the details panel (never catalogued): no pointer there (N5).
  if(files.length>shown)entry.missing.append(node('p',Array.isArray(missing.parts)?`+ ${(files.length-shown).toLocaleString()} more.`:`+ ${(files.length-shown).toLocaleString()} more, listed in the details panel.`,'field-help'));
}
// The files Approve will use (0.22.0 review B4): Order unclear as a numbered "Playback order" list of 5, the others as an
// "In" folder line and 3 names (files without the title first), then "+ n more, listed in the details panel." Mixed
// recordings add the albums, or the artists when only they differ.
function buildHoldList(entry){
  const ask=askOf(entry.row),kind=holdKind(ask);if(!kind)return;
  const files=(Array.isArray(ask.files)?ask.files:[]).filter(f=>typeof f?.name==='string'),count=Number(ask.file_count) || files.length;if(!files.length)return;
  const box=entry.missing,more=shown=>{if(count>shown)box.append(node('p',`+ ${(count-shown).toLocaleString()} more, listed in the details panel.`,'field-help'));};
  if(kind==='order_unclear' || setCause(ask)){
    // A set of parts lists its proposed join order the same way (N2): a wrong order can't be repaired once the sources go.
    box.append(node('p','Playback order','field-help ask-list-label'));
    const list=node('ol','','path ask-order');list.setAttribute('aria-label','Playback order');
    for(const f of files.slice(0,5)){const item=node('li',f.name);item.title=f.folder || '';list.append(item);}
    box.append(list);more(Math.min(5,files.length));return;
  }
  const flagged=ask.cause==='lack_title' && Array.isArray(ask.flagged) && ask.flagged.length?ask.flagged:null,shown=(flagged || files).slice(0,3);
  for(const folder of [...new Set(shown.map(f=>f.folder || ''))]){
    box.append(node('p','In '+folder+(/[\\/]$/.test(folder)?'':'\\'),'path'));
    for(const f of shown.filter(item=>(item.folder || '')===folder))box.append(node('p',f.name,'path'));
  }
  more(shown.length);
  if(ask.cause==='mixed' || ask.cause==='works')for(const [label,items] of [['Albums',ask.facts?.albums],['Artists',ask.facts?.artists],['Books',ask.facts?.works]])if(Array.isArray(items) && items.length)
    box.append(node('p',`${label}: `+items.slice(0,3).map(item=>`${item.name==='(none)'?(label==='Albums'?'No album':'No artist'):item.name} (${plural(Number(item.files) || 0,'file','files')})`).join(' · ')+(items.length>3?` + ${(items.length-3).toLocaleString()} more`:''),'field-help'));
}
function buildInlineNames(entry){
  const row=entry.row;if(!inlineNames(row))return;
  const block=node('div','','ask-inline-names');
  block.append(askInput(entry,'title','Title',namesValue(row,'title'),'','The title this book is filed under.'));
  const basis=BASIS_LINES[askOf(row).fields?.title?.basis];if(basis)block.append(node('p',basis,'field-help ask-basis'));
  const pair=node('div','','ask-grid');
  for(const field of ['series','number']){const {wrap,input}=namesInput(row,field);entry.controls.push(input);pair.append(wrap);}
  block.append(pair);entry.fields.append(block);
}
function buildAskCell(row,td){
  const entry={row,cell:td,controls:[]};askRows.set(row.id,entry);
  entry.hint=node('p','','field-help attention-hint');entry.hint.id='attention-hint-'+row.id;
  entry.also=node('p','','field-help attention-also');entry.why=node('p','','field-help ask-why');entry.fields=node('div','','ask-fields');entry.missing=node('div','','ask-missing');entry.dest=node('p','','goes-to');
  td.append(entry.hint,entry.also,entry.why,entry.fields,entry.missing,entry.dest);
  buildAskFields(entry);buildInlineNames(entry);buildAskMissing(entry);buildHoldList(entry);
  if(recordingMarker(row))td.append(node('p',recordingMarker(row),'field-help'));
  updateAskRow(entry);
}
// The row's buttons, primary first: Missing files: Scan again + Convert what's there or Remove from list; a hold row:
// its Approve face + Change order (Order unclear) or Choose files (Files unclear) + Scan again; else Approve.
function buildAskActions(row,buttons){
  const entry=askRows.get(row.id),ask=askOf(row);if(!entry)return;
  const hold=holdKind(ask),wide=hold || ask.kind==='files_missing'?' ask-convert':'';
  // A duplicate-recording row has no Approve (Futaba's 0.22.0 QA, m-3: it was inert there, its tooltip saying the name is
  // taken); a verified one gets Remove this copy in the Delete book slot. ask.duplicate is the server's, never read from copy.
  const kinds=ask.duplicate?[]:ask.kind==='files_missing'?['scan',ask.missing?.present>0?'convert':'remove']:setCause(ask)?['approve','separate','scan']:hold?['approve',...({order_unclear:['order'],files_unclear:['choose']}[hold] || []),'scan']:['approve'];
  entry.buttons=kinds.map(kind=>{const button=node('button',askLabel(entry,kind),'quiet row-retry'+(kind==='convert'?' ask-convert':wide));button.type='button';button.setAttribute('aria-describedby',entry.hint.id);
    button.addEventListener('click',event=>{event.stopPropagation();askPress(entry,kind);});button.addEventListener('keydown',event=>event.stopPropagation());buttons.append(button);return {kind,button};});
  entry.primaryKind=kinds[0];entry.primary=entry.buttons[0]?.button;entry.secondKind=kinds[1];entry.second=entry.buttons[1]?.button;
  // Ruling 35: a queued press on this row has its own Cancel beside the buttons (Judy 0.22.1 1.1).
  if(kinds.some(kind=>ASK_QUEUE[kind])){entry.cancel=queueCancelButton(row,ASK_QUEUE[kinds.find(kind=>ASK_QUEUE[kind])]);buttons.append(entry.cancel);}
  updateAskRow(entry);
}
function askMode(row,kind){
  if(ended || recoveryDisconnected)return 'offline';
  if(askDone.has(row.id))return 'done';
  if(kind==='order' || kind==='choose')return 'ready';  // they only open the details panel
  if(deleteQueued(row))return 'queued';  // a delete is queued for this book (Judy 1.3)
  const own=ASK_QUEUE[kind];
  if(own && queueRunning(row,own))return 'pending';  // ruling 35: its queued press runs now
  if(own && queuedFor(row,own))return 'waiting';    // queued behind what is happening, with Cancel
  const mine=askPendings.get(row.id);
  if(mine)return mine.kind===kind?'pending':'sibling';
  if(queuedFor(row) || queueRunning(row))return 'sibling';  // one queued action per row (Judy 0.22.1 1.1)
  // Ruling 35 (Sergei 2026-10-26): nothing else holds a press back; the engine queues it if it must wait.
  if((kind==='approve' || kind==='convert') && askInert(row))return 'inert';
  if(kind==='separate' && askPanelEdits(row))return 'inert';
  return 'ready';
}
function updateAskButton(entry,button,kind){
  if(!button)return;const row=entry.row,mode=askMode(row,kind),done=askDone.get(row.id),queued=done==='approve' || done==='convert';
  const gone=mode==='done' && button!==entry.primary,hadFocus=gone && document.activeElement===button;button.hidden=gone;
  if(hadFocus)entry.primary?.focus?.({preventScroll:true});if(gone)return;
  const label=mode==='done' && queued?'Queued':mode==='waiting'?'Queued':mode==='pending'?ASK_PENDING[kind][0]:askLabel(entry,kind);
  const sibling=queuedFor(row) || (queueState.running?.book_id===row.id?queueState.running:null),siblingTip=sibling?`${queueWord(sibling.action)} is queued for this book. Cancel it to use this.`:(ASK_PENDING[askPendings.get(row.id)?.kind]?.[1] || '');
  const title={done:ASK_DONE[done]?.[1] || '',offline:'Local server unavailable.',sibling:siblingTip,queued:QUEUE_SIBLING,waiting:queueHint(row) || '',inert:kind==='separate'?askPanelEdits(row):askInert(row),pending:ASK_PENDING[kind]?.[1] || '',ready:askTip(entry,kind)}[mode];
  if(button.textContent!==label)button.textContent=label;if(button.title!==title)button.title=title;
  button.setAttribute('aria-label',label.replace(/\.\.\.$/,'')+': '+askName(row));
  // Pending and a not-yet-possible Approve keep keyboard focus: aria-disabled, never the disabled attribute.
  if(['pending','inert','queued','waiting','sibling'].includes(mode))button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
  button.disabled=!['ready','pending','inert','queued','waiting','sibling'].includes(mode);
}
// Every Stopped row shows where its book goes (Judy's to-do spec 1.6 and section 4; Futaba's m-3): its job's own destination.
function stoppedGoesTo(row,td){
  const job=row.creation?.job,dest=job?.destination;if(job?.state!=='Output needs attention' || typeof dest?.path!=='string' || !dest.path)return;
  const line=node('p','','goes-to');line.append(node('span','Goes to','goes-label'),node('span',outputName()+'\\'+dest.path,'path'));line.title=dest.absolute || dest.path;td.append(line);
}
function renderGoesTo(entry){
  const dest=askDestination(entry.row),line=entry.dest,path=typeof dest?.path==='string' && dest.path?outputName()+'\\'+dest.path:'';
  line.hidden=!path;if(!path)return;
  // On a set row the path is true only for Approve as one book (Keep is the other answer): "As one book" (Judy 2026-10-25).
  const taken=dest.taken===true && !askDone.has(entry.row.id),label=taken?'Already there':setCause(askOf(entry.row))?'As one book':'Goes to',key=JSON.stringify([label,path]);
  if(line.dataset.key!==key){line.replaceChildren();line.append(node('span',label,'goes-label'),node('span',path,'path'));line.dataset.key=key;}
  line.title=dest.absolute || path;line.classList?.toggle?.('taken',taken);
}
function updateAskRow(entry){
  const row=entry.row,ask=askOf(row);if(!ask)return;
  const text=askText(row),done=askDone.get(row.id),result=askResults.get(row.id),pending=askPendings.get(row.id)?.kind || null;
  let status=text.status,hint=text.hint,clause='',warn=false,lines=null;
  if(done){status=ASK_DONE[done]?.[0] || status;hint=ASK_DONE[done]?.[1] || hint;}
  else if(pending)hint=clockNote(ASK_PENDING[pending][1],askPendings.get(row.id)?.at);
  else if(result){hint=result.text;warn=result.warn!==false;}
  else if(askChecked.has(row.id))clause=' Checked '+askChecked.get(row.id)+(holdKind(ask)?'. No change.':'. Not found.');
  else if(!pending){const later=queueNoteFor(row);if(later){hint=later.text;warn=later.warn;clause='';}}  // a queued delete's outcome (1.6)
  const deleted=deleteNotes.get(row.id);if(deleted && !done){hint=deleted.text;warn=deleted.warn;clause='';lines=deleted.lines;}  // Delete book's outcome (ruling 23)
  const queued=done?null:queueHint(row);if(queued!==null){hint=queued;warn=false;clause='';lines=null;}  // the queued line replaces the hint (1.3)
  statusInPlace(entry.cell,status);setHint(entry.hint,hint,clause,warn,lines);
  const also=done?'':askAlso(ask),why=done?'':ask.kind==='same_author'?sameWhy(ask):askReason(ask);
  if(entry.also.textContent!==also)entry.also.textContent=also;entry.also.hidden=!also;
  if(entry.why.textContent!==why)entry.why.textContent=why;entry.why.hidden=!why;
  entry.fields.hidden=!!done;entry.missing.hidden=!!done;
  if(entry.nochoice)entry.nochoice.hidden=!!askDraft(row.id).choice;
  renderGoesTo(entry);
  for(const {kind,button} of entry.buttons || [])updateAskButton(entry,button,kind);
  if(entry.cancel)updateQueueCancel(entry.cancel,row,ASK_QUEUE_ACTIONS);
  if(entry.block){const mode=entry.primary?askMode(row,entry.primaryKind):'';const block=result?.code==='draft'?{text:'',fix:'panel'}:mode==='inert' && (entry.primaryKind==='approve' || entry.primaryKind==='convert')?approveBlock(row):{text:'',fix:null};
    renderBlock(entry.block,block,row,!namesOpen(row.id) || block.fix==='panel' || result?.code==='draft',entry.primary);if(entry.primary){const ids=[entry.hint.id,block.text || block.fix?entry.block.id:''].filter(Boolean).join(' ');if(entry.primary.getAttribute('aria-describedby')!==ids)entry.primary.setAttribute('aria-describedby',ids);}}
  const tip=cellTip(row);if(entry.cell.title!==tip)entry.cell.title=tip;
}
function updateAskRows(){for(const entry of askRows.values())updateAskRow(entry);}
function askChanged(entry,delay){askResults.delete(entry.row.id);askPreview(entry,delay);updateAskRow(entry);batchCounts();}
// The Goes to line follows what is shown: on blur, on Enter, and 500 ms after typing stops. Stale replies are ignored and
// the last good path stays meanwhile (no flicker, no "Loading").
function askPreview(entry,delay){
  const row=entry.row,id=row.id,d=askDraft(id),names=namesFor(row),values={...askValues(row,true),...(names?{names}:{})},key=JSON.stringify(values);
  if(d.timer!==null){clearTimeout(d.timer);d.timer=null;}
  if(key===d.previewKey)return;
  if(key==='{}'){d.previewKey=key;d.preview=null;++d.seq;updateAskRow(entry);return;}
  if(values.title!==undefined && !values.title)return;  // an empty title: Approve is inert; the last good path stays
  if(names && (names.series && !names.number || names.number && !names.series))return;  // Series and Number go together (Judy 1.3)
  const send=async()=>{
    d.timer=null;d.previewKey=key;const seq=++d.seq;
    try{const result=await request('/api/candidate/approve-preview',{library:'Audiobooks',id,revision:row.revision,...values});const p=result?.preview;if(seq===d.seq && typeof p?.path==='string')d.preview={path:p.path,absolute:p.absolute || '',taken:p.taken===true,reason:p.reason || ''};
      const state=namesState.get(id);if(seq===d.seq && names && state && p)state.preview={...(state.preview || {}),place:p.place,applies:p.applies,path:p.path,absolute:p.absolute};}
    catch(error){if(seq===d.seq)d.previewKey=null;}
    finally{const fresh=askRows.get(id);if(fresh && seq===d.seq)updateAskRow(fresh);batchCounts();}
  };
  if(delay>0)d.timer=setTimeout(send,delay);else return send();
}
function askPrimary(entry){const kind=entry.primaryKind==='scan'?(entry.secondKind==='convert'?'convert':null):entry.primaryKind;if(kind)return askPress(entry,kind);}
// Each Approve gate's code (web_server.approve_code): the real reason and the next step. Provisional copy, sent to Judy
// (0.22.2 spec, Ender's notes); a code with no line here shows the engine's own sentence, never the bare refusal.
const APPROVE_REFUSALS={name_taken:'An audiobook with this name is already in Audiobooks Sorted. Change the title or author, then approve.',
  title:'Type a title first.',job_exists:'This book already has an audiobook job. Find it under Queued / creating.',
  profiles:'The files are different recordings (their audio differs). Choose the files that belong in the details panel, then approve.',
  chapters:'The parts carry chapters of their own. Approve them as one book on the set row, or keep them as separate books.',
  cover:"The cover couldn't be checked. Choose a cover in the details panel, then approve.",
  sources:"A file of this book can't be read. Check that its drive is connected, then approve again.",
  draft:'Edits in the details panel hold this book. Save or discard them, then approve.',
  binding:'The collection files changed since they were checked. Scan again, then approve.',
  closing:'Books Arranger is closing. Approve again after it restarts.'};
function serverSentence(error,fallback){const text=typeof error?.body?.error==='string'?error.body.error.trim():'';return text?(/Nothing was (changed|deleted)\.$/.test(text)?text:text.replace(/\.?$/,'.')+' Nothing was changed.'):fallback;}
function askErrorText(error,kind){
  if(!error.httpStatus)return lostLine();
  if(error.body?.code==='changed')return 'This book changed. Review its details and try again.';
  if(error.body?.code==='moved')return 'The destination changed. Check the Goes to line and try again.';  // N7
  // A safety gate is named (0.22.0 review B5.4).
  if(error.body?.code==='format')return "The audio format needs a decision the app can't make yet. Select the row to read why.";
  if((kind==='approve' || kind==='convert') && Object.hasOwn(APPROVE_REFUSALS,error.body?.code))return APPROVE_REFUSALS[error.body.code];
  // «Спящие красавицы» (2026-10-26): the engine's own sentence, never the bare "… was not accepted. Nothing was changed."
  return serverSentence(error,ASK_REFUSED[kind]);
}
function askClock(date){return String(date.getHours()).padStart(2,'0')+':'+String(date.getMinutes()).padStart(2,'0');}
// The strip line (a polite live region): stays until the chip or filter changes; Retry receipts do not overwrite it.
function askNote(text){dropQueueStrip();stripNote=text;retryAllRun={id:bulkRun()?.id,ended:true,suppressReceipt:true};renderAttentionGroups();}
// After a press settled a book, focus goes to the next row's first working control, else the Status filter.
// After a forced re-read (Delete book): the first working control of row id if it is still listed, else the Status filter.
function leaveTo(id){
  const next=id?rows.find(row=>row.id===id):null,other=next?askRows.get(next.id):null;
  const target=!next?null:other?(other.controls.find(c=>!c.disabled && !c.hidden) || other.primary):[...(rowButtons(next.path)?.children || [])].find(b=>b.type==='button' && !b.hidden && !b.disabled);
  (target || $('filter')).focus?.({preventScroll:true});
}
function askLeave(entry){
  const index=rows.findIndex(item=>item.id===entry.row.id);
  for(const next of rows.slice(index+1)){
    if(askDone.has(next.id))continue;const other=askRows.get(next.id);
    const target=other?(other.controls.find(c=>!c.disabled && !c.hidden) || other.primary):[...(rowButtons(next.path)?.children || [])].find(b=>b.type==='button' && !b.hidden && !b.disabled);
    if(target){target.focus?.({preventScroll:true});return;}
  }
  $('filter').focus?.({preventScroll:true});
}
// ---------------------------------------------------------------- Edit names (Sergei 2026-10-26; Judy 0.22.2 section 1)
// "Edit names" on every book row opens an editor in the row: Title, Author (the ask fields when the row asks), Series,
// Number, Universe and Collection. Save records his values (lasting, "Entered by you") and touches no file; Approve records
// and approves. Values load when the editor opens (one read for one row). The draft lives in memory per book and survives
// polls, paging and chip changes. Ruling 35: Save is accepted whatever is happening and queued when it must wait (the book
// converting, loading); the row shows it with Cancel.
const NAMES_FIELDS=['title','author','series','number','universe','collection'];
const NAMES_LABELS={title:'Title',author:'Author',series:'Series',number:'Number',universe:'Universe',collection:'Collection of stories'};
const NAMES_TIPS={series:'The series this book belongs to. Leave empty for a standalone book.',number:'The book\'s number in its series. Needed when a series is set.',
  universe:'The shared universe this book belongs to, such as Warhammer 40,000. Leave empty if none.',collection:'File this book under Сборники. Use it for story collections by several authors.',
  title:'The title this book is filed under.',author:'The author this book is filed under. Leave empty to use Без автора.'};
const NAMES_EDIT_TIP='Correct this book\'s title, author, series or universe. Nothing is converted or moved.';
const NAMES_SAVE_TIP='Save these values and remember them for other scans of these files. Nothing is converted or moved.';
const NAMES_SCOPE='Saved values are remembered, so a new scan of these files uses them.';
const namesState=new Map(),namesNotes=new Map(),namesRows=new Map();
function namesOpen(id){return !!namesState.get(id)?.open;}
function namesAny(){for(const value of namesState.values())if(value.open)return true;return false;}
function namesDropped(id){namesState.delete(id);namesRows.delete(id);}
function namesData(id){return namesState.get(id)?.data || null;}
function namesProposal(id,field){const row=rows.find(row=>row.id===id),value=namesData(id)?.fields?.[field]?.proposal ?? (['series','number'].includes(field)?(row?.ask?.fields?.[field]?.proposal ?? row?.place?.[field]):undefined);return field==='collection'?value===true:typeof value==='string'?value:'';}
// The values shown: the draft over what the editor read; Title and Author of a question row are its ask draft (one draft).
function namesValue(row,field){
  const state=namesState.get(row.id),draft=state?.draft || {};
  if((field==='title' || field==='author') && askOf(row)){const d=askDrafts.get(row.id) || {};if(field==='author'){const chosen=askValues(row,true).author;if(typeof chosen==='string')return chosen;}if(typeof d[field]==='string')return d[field];const proposal=askProposal(askOf(row),field);return proposal || namesProposal(row.id,field);}
  if(inlineNames(row) && ['series','number'].includes(field)){const value=askDrafts.get(row.id)?.[field];if(typeof value==='string')return value;}
  if(Object.hasOwn(draft,field))return draft[field];
  return namesProposal(row.id,field);
}
function namesValues(row){const values={};for(const field of NAMES_FIELDS)values[field]=field==='collection'?namesValue(row,field)===true:String(namesValue(row,field) ?? '').trim();return values;}
// What Approve and its preview carry while the editor is open (the four fields beside Title and Author).
function namesFor(row){
  if(!row)return null;
  if(inlineNames(row) && (!namesOpen(row.id) || !namesData(row.id))){
    const d=askDrafts.get(row.id) || {},series=String(namesValue(row,'series') || '').trim(),number=String(namesValue(row,'number') || '').trim();
    return series || number || typeof d.series==='string' || typeof d.number==='string'?{series,number}:null;
  }
  if(!namesOpen(row.id) || !namesData(row.id))return null;
  const v=namesValues(row);return {series:v.series,number:v.number,universe:v.universe,collection:v.collection};
}
function namesChanged(row){if(!namesData(row.id))return false;const v=namesValues(row);return NAMES_FIELDS.some(field=>field==='collection'?v[field]!==namesProposal(row.id,field):v[field]!==String(namesProposal(row.id,field)).trim());}
// Why Save does nothing yet ('' when it works), Judy 1.6.
function namesInert(row){return saveBlock(row).text;}  // 0.22.3: the cause the line under Save shows (Judy 3)
// The Place line (Judy 2): a collection in a series, or a universe book; parts in order and only when set.
function placeText(place){
  if(!place || typeof place!=='object')return '';
  const series=place.series && place.number?[`Series: ${place.series}`,`No. ${place.number}`]:[];
  if(place.universe)return [`Universe: ${place.universe}`,...series].join(' · ');
  if(place.collection===true && series.length)return ['Collection',...series].join(' · ');
  return '';
}
function enteredText(fields){const list=(Array.isArray(fields)?fields:[]).filter(field=>Object.hasOwn(NAMES_LABELS,field));return list.length?`Entered by you: ${list.map(field=>field==='collection'?'collection':field).join(', ')}.`:'';}
// Edit names on the row (Judy 1.6): inert only while a retry, repair or delete is queued for it (one queued action per
// row) and when no file is left. Ruling 35: a converting book is no reason (its Save waits for the conversion).
function namesButtonInert(row){
  const queued=queuedFor(row) || (queueState.running?.book_id===row.id?queueState.running:null);
  if(queued && ['retry','repair','delete','copy'].includes(queued.action))return {retry:'A retry is queued for this book. Cancel it to use this.',repair:'A repair is queued for this book. Cancel it to use this.',delete:QUEUE_SIBLING,copy:QUEUE_SIBLING}[queued.action];
  if(Array.isArray(row.members) && row.members.length && row.members.every(member=>member.missing))return 'No files are left for this book.';
  return '';
}
function buildNamesButton(row,buttons){
  const button=node('button','Edit names','quiet row-retry names-edit');button.type='button';
  button.setAttribute('aria-controls','names-editor-'+row.id);
  button.addEventListener('click',event=>{event.stopPropagation();if(button.getAttribute('aria-disabled')==='true')return;namesToggle(row.id);});
  button.addEventListener('keydown',event=>event.stopPropagation());buttons.append(button);
  const entry=namesRows.get(row.id) || {};entry.button=button;entry.row=row;namesRows.set(row.id,entry);
  updateNamesButton(row);
}
function updateNamesButton(row){
  const entry=namesRows.get(row.id),button=entry?.button;if(!button)return;
  const inert=namesButtonInert(row),title=inert || NAMES_EDIT_TIP;
  if(button.title!==title)button.title=title;button.setAttribute('aria-label','Edit names: '+askName(row));
  button.setAttribute('aria-expanded',String(namesOpen(row.id)));
  if(inert)button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
}
async function namesToggle(id){
  const row=rows.find(item=>item.id===id);if(!row)return;
  if(namesOpen(id)){namesRows.get(id)?.inputs?.title?.focus?.({preventScroll:true});return;}  // open: focus moves to Title (1.7)
  const state=namesState.get(id) || {draft:{},seq:0,previewKey:''};state.open=true;namesState.set(id,state);
  renderRows(true);focusNames(id);
  if(!state.data){
    try{const answer=await request('/api/candidate/names',{library:'Audiobooks',id,revision:row.revision},PRESS_TIMEOUT);state.data=answer?.editor || null;}
    catch(error){namesNotes.set(id,{text:error.httpStatus?serverSentence(error,'The names could not be read.'):lostLine(),warn:true});state.open=false;}
    renderRows(true);focusNames(id);namesPreview(id,0);
  }
}
function focusNames(id){const entry=namesRows.get(id),title=entry?.inputs?.title;(title || entry?.button)?.focus?.({preventScroll:true});}
function namesClose(id,keep=false){
  const state=namesState.get(id);if(!state)return;state.open=false;if(!keep){state.draft={};askDrafts.delete(id);state.preview=null;state.previewKey='';}
  renderRows(true);namesRows.get(id)?.button?.focus?.({preventScroll:true});
}
// Fields stop clicks and keys reaching the row; Esc closes only an unchanged editor; Ctrl+Enter presses the row's Approve,
// else Save (Judy 1.3, 1.7); Enter alone refreshes the Goes to line.
function namesGuard(row,element){
  element.addEventListener('click',event=>event.stopPropagation());
  element.addEventListener('keydown',event=>{event.stopPropagation();
    if(event.key==='Escape'){if(!namesChanged(row))namesClose(row.id);return;}
    if(event.key!=='Enter')return;event.preventDefault?.();
    if(event.ctrlKey){const entry=askRows.get(row.id);if(entry && entry.primaryKind==='approve')askPrimary(entry);else namesSave(row.id);}
    else namesPreview(row.id,0);});
}
function namesChangedField(row,field,value){
  if(askOf(row) && (field==='title' || field==='author' || inlineNames(row) && ['series','number'].includes(field))){askDraft(row.id)[field]=value;const entry=askRows.get(row.id);if(entry){askChanged(entry,500);}}
  else{const state=namesState.get(row.id);state.draft[field]=value;namesPreview(row.id,500);}
  namesNotes.delete(row.id);updateNamesRows();
}
function namesInput(row,field,list){
  const wrap=node('label','','ask-field'),input=node('input');input.type='text';input.maxLength=1000;input.setAttribute('maxlength','1000');input.setAttribute('autocomplete','off');input.setAttribute('spellcheck','false');
  input.dataset.name=field;input.value=String(namesValue(row,field) ?? '');input.title=NAMES_TIPS[field];input.setAttribute('aria-label',NAMES_LABELS[field]+': '+askName(row));
  if(field==='series' || field==='universe')input.placeholder='None';
  if(list){input.setAttribute('list',list);}
  wrap.append(node('span',NAMES_LABELS[field]),input);namesGuard(row,wrap);namesGuard(row,input);
  input.addEventListener('input',()=>namesChangedField(row,field,input.value));input.addEventListener('blur',()=>namesPreview(row.id,0));
  return {wrap,input};
}
function namesList(id,name,values){const list=node('datalist');list.id=`names-${name}-${id}`;for(const value of values || []){const option=node('option');option.value=value;list.append(option);}return list;}
// The lines under Series and Universe (1.6): a new name, or the basis of a guess.
function namesFieldLine(row,field){
  const data=namesData(row.id),value=String(namesValue(row,field) || '').trim(),proposal=String(namesProposal(row.id,field) || '').trim();
  const known=field==='series'?data?.series:field==='universe'?data?.universes:null;
  if(known && value && value!==proposal && !known.includes(value))return field==='series'?'New series: nothing is filed there yet.':'New universe: nothing is filed there yet.';
  const basis=data?.fields?.[field]?.basis;
  if(value && value===proposal && basis==='folder_name')return field==='series'?'Series from the folder name.':'Universe from the folder name.';
  if(value && value===proposal && basis==='file_name' && field==='universe')return 'Universe from the file name.';
  return '';
}
// The editor's parts in the status cell. A question row keeps its own fields (Title, Author or the radio group) and its own
// Goes to line; the editor adds the rest around them. Any other row gets the whole editor.
function buildNamesBlock(row,td){
  const id=row.id,open=namesOpen(id),entry=namesRows.get(id) || {};entry.row=row;entry.inputs={};namesRows.set(id,entry);
  const ask=askRows.get(id),before=ask?.dest || [...(td.children || [])].find(child=>String(child.className || '').includes('goes-to')) || null;
  const place=node('p','','field-help book-place'),entered=node('p','','field-help names-entered');entry.place=place;entry.entered=entered;
  const insert=element=>{if(before && before.parentElement===td)td.insertBefore(element,before);else td.append(element);};
  if(!open){insert(place);insert(entered);updateNamesRow(row);return;}
  const box=node('div','','names-editor');box.id='names-editor-'+id;entry.box=box;
  if(!namesData(id)){box.append(node('p','Loading these names…','field-help'));insert(box);updateNamesRow(row);return;}
  const grid=node('div','','ask-grid'),data=namesData(id);
  if(inlineNames(row))for(const field of ['series','number'])entry.inputs[field]=ask.controls.find(control=>control.dataset.name===field);
  if(!ask){
    for(const field of ['title','author']){const {wrap,input}=namesInput(row,field);entry.inputs[field]=input;const cell=node('div');cell.append(wrap);grid.append(cell);}
  }else entry.inputs.title=ask.controls.find(control=>control.dataset.name==='title') || null;
  for(const field of (inlineNames(row)?['universe']:['series','number','universe'])){
    const list=field==='number'?null:`names-${field==='series'?'series':'universes'}-${id}`;
    const {wrap,input}=namesInput(row,field,list);entry.inputs[field]=input;const cell=node('div');cell.append(wrap);
    if(field!=='number'){const line=node('p','','field-help ask-basis');entry[field+'Line']=line;cell.append(line);}
    grid.append(cell);
  }
  const check=node('label','','check ask-radio'),box2=node('input');box2.type='checkbox';box2.checked=namesValue(row,'collection')===true;box2.title=NAMES_TIPS.collection;box2.setAttribute('aria-label',NAMES_LABELS.collection+': '+askName(row));
  check.append(box2,node('span',NAMES_LABELS.collection));namesGuard(row,check);namesGuard(row,box2);entry.inputs.collection=box2;
  box2.addEventListener('change',()=>namesChangedField(row,'collection',box2.checked));grid.append(check);
  box.append(grid,namesList(id,'series',data.series),namesList(id,'universes',data.universes));
  entry.scope=node('p','','field-help names-scope');box.append(entry.scope,place,entered);
  if(!ask){entry.dest=node('p','','goes-to');box.append(entry.dest);}
  insert(box);
  // After the Goes to line: Save and Discard, then what is remembered (Judy 1.2).
  const after=node('div','','names-after'),actions=node('div','','row-actions');
  const save=node('button','Save','quiet row-retry');save.type='button';save.addEventListener('click',event=>{event.stopPropagation();namesSave(id);});save.addEventListener('keydown',event=>event.stopPropagation());
  const discard=node('button','Discard','quiet row-retry');discard.type='button';discard.title='Throw away these changes. Nothing is saved.';discard.setAttribute('aria-label','Discard: '+askName(row));
  discard.addEventListener('click',event=>{event.stopPropagation();namesClose(id);});discard.addEventListener('keydown',event=>event.stopPropagation());
  actions.append(save,discard);after.append(actions);entry.save=save;entry.discard=discard;
  entry.status=node('p','','field-help names-status');entry.status.id='names-status-'+id;entry.status.hidden=true;entry.why=node('p','','field-help block-why');entry.why.id='names-why-'+id;entry.why.hidden=true;
  save.setAttribute('aria-describedby',entry.why.id+' '+entry.status.id);after.append(entry.status,entry.why);
  const remembered=Array.isArray(data.remembered)?data.remembered:[];
  if(remembered.length){
    after.append(node('p','Remembered for this book','field-help ask-list-label'));
    for(const item of remembered){
      const line=node('p','','field-help names-remembered'),label=NAMES_LABELS[item.field] || item.field,to=item.field==='collection'?(item.to==='true'?'Yes':'No'):item.to;
      line.append(node('span',item.from?`${label}: «${item.from}» → «${to}»`:`${label}: «${to}»`));
      const forget=node('button','Forget','quiet row-retry');forget.type='button';forget.title='Take this correction back. Nothing is renamed or moved.';forget.setAttribute('aria-label',`Forget: ${label}: ${askName(row)}`);
      forget.addEventListener('click',event=>{event.stopPropagation();namesForget(id,item.id);});forget.addEventListener('keydown',event=>event.stopPropagation());
      line.append(forget);after.append(line);(entry.forgets=entry.forgets || []).push(forget);
    }
  }
  if(ask?.dest?.nextSibling)td.insertBefore(after,ask.dest.nextSibling);else td.append(after);
  updateNamesRow(row);
}
function updateNamesRow(row){
  const entry=namesRows.get(row.id);if(!entry)return;const state=namesState.get(row.id),open=namesOpen(row.id);
  const place=open?(state?.preview?.place || namesData(row.id)?.place):row.place,placeLine=placeText(place);
  if(entry.place){if(entry.place.textContent!==placeLine)entry.place.textContent=placeLine;entry.place.hidden=!placeLine;}
  const entered=enteredText(open?namesData(row.id)?.entered:row.entered);
  if(entry.entered){if(entry.entered.textContent!==entered)entry.entered.textContent=entered;entry.entered.hidden=!entered;}
  if(open && entry.scope){const n=Number(state?.preview?.applies || namesData(row.id)?.applies) || 1,text=NAMES_SCOPE+(n>1?` Applies to ${n.toLocaleString()} books.`:'');if(entry.scope.textContent!==text)entry.scope.textContent=text;}
  for(const field of ['series','universe']){const line=entry[field+'Line'];if(line){const text=namesFieldLine(row,field);if(line.textContent!==text)line.textContent=text;line.hidden=!text;}}
  if(open && entry.dest){
    const dest=state?.preview || namesData(row.id)?.destination,path=typeof dest?.path==='string' && dest.path?outputName()+'\\'+dest.path:'';
    entry.dest.hidden=!path;if(path){const key=JSON.stringify(path);if(entry.dest.dataset.key!==key){entry.dest.replaceChildren(node('span','Goes to','goes-label'),node('span',path,'path'));entry.dest.dataset.key=key;}entry.dest.title=dest.absolute || path;}
  }
  if(entry.save){
    const pending=state?.pending,queued=queuedFor(row,'names') || queueRunning(row,'names'),inert=pending || queued?'':namesInert(row);
    const face=pending || queued?'Saving…':'Save',tip=pending?'Saving these names…':queued?(queueHint(row) || 'Saving these names…'):inert || NAMES_SAVE_TIP;
    if(entry.save.textContent!==face)entry.save.textContent=face;if(entry.save.title!==tip)entry.save.title=tip;entry.save.setAttribute('aria-label',face.replace(/…$/,'')+': '+askName(row));
    if(pending || queued || inert)entry.save.setAttribute('aria-disabled','true');else entry.save.removeAttribute('aria-disabled');
    // 0.22.3: the clock while it waits, a failure in its place (the editor stays open, the typing is kept), else the cause.
    const note=namesNotes.get(row.id),forgetting=state?.forgetting;
    const text=pending?clockNote('Saving these names…',pending.at,SAVE_TAIL):forgetting?clockNote('Taking this correction back…',forgetting.at,SAVE_TAIL):note?.warn && open?note.text:'';
    if(entry.status){if(entry.status.textContent!==text)entry.status.textContent=text;entry.status.hidden=!text;entry.status.classList?.toggle?.('warn',!pending && !forgetting && !!text);
      if(!pending && !forgetting && text)entry.status.setAttribute('role','alert');else entry.status.removeAttribute('role');}
    renderBlock(entry.why,pending || queued?{text:'',fix:null}:saveBlock(row),row,true,entry.save);
  }
  const note=namesNotes.get(row.id),inEditor=!!(note?.warn && open && entry.status),reloading=listWait?.id===row.id && listWait.shown;
  if(note && !inEditor){const text=note.text+(reloading?' Updating the list…':'');const ask=askRows.get(row.id);if(ask)setHint(ask.hint,text,'',note.warn);else{const retry=rowRetries.get(row.path);if(retry)setHint(retry.hint,text,'',note.warn);else{if(!entry.note){entry.note=node('p','','field-help attention-hint');(entry.place?.parentElement || null)?.insertBefore?.(entry.note,entry.place);}if(entry.note){entry.note.textContent=text;entry.note.classList?.toggle?.('retry-refused',!!note.warn);}}}}
  updateNamesButton(row);
}
function updateNamesRows(){for(const entry of namesRows.values()){const fresh=rows.find(row=>row.id===entry.row?.id);if(fresh){entry.row=fresh;updateNamesRow(fresh);}}}
// The Goes to line, the Place line and "Applies to" follow the draft: 500 ms after typing stops, on blur, on Enter.
function namesPreview(id,delay){
  const row=rows.find(item=>item.id===id),state=namesState.get(id);if(!row)return;
  if(askOf(row) && (inlineNames(row) || state?.open && state.data)){const entry=askRows.get(id);if(entry){askDraft(id).previewKey=null;return askPreview(entry,delay);}return;}
  if(!state?.open || !state.data)return;
  const v=namesValues(row),key=JSON.stringify(v);if(state.timer){clearTimeout(state.timer);state.timer=null;}
  if(key===state.previewKey || !v.title || (v.series && !v.number) || (v.number && !v.series))return;
  const send=async()=>{state.timer=null;state.previewKey=key;const seq=++state.seq;
    try{const answer=await request('/api/candidate/approve-preview',{library:'Audiobooks',id,revision:row.revision,title:v.title,author:v.author,names:{series:v.series,number:v.number,universe:v.universe,collection:v.collection}});
      if(seq===state.seq && answer?.preview)state.preview=answer.preview;}
    catch(error){if(seq===state.seq)state.previewKey='';}
    finally{if(seq===state.seq)updateNamesRows();}};
  if(delay>0)state.timer=setTimeout(send,delay);else return send();
}
// The row line after a press (Judy 1.6), by the row's family and the engine's outcome.
function namesSavedText(row,answer){
  if(answer?.outcome==='replanned')return 'Saved. The queued job uses these names.';
  if(answer?.outcome==='ready_only')return 'Saved. The finished audiobook in Audiobooks Sorted keeps its name.';
  if(answer?.outcome==='unchanged')return 'Nothing changed. Nothing was saved.';
  const ask=askOf(row);
  if(ask)return 'Saved. Approve uses these names.';
  const action=rowAction(row);
  if(action?.kind==='retry')return 'Saved. Retry uses these names.';
  if(action?.kind==='repair')return 'Saved. Repair uses these names.';
  if(row.creation?.job?.state==='Output needs attention')return 'Saved. The next attempt uses these names.';
  return 'Saved. These names are used when it converts.';
}
async function namesSave(id){
  const row=rows.find(item=>item.id===id),state=namesState.get(id),entry=namesRows.get(id);if(!row || !state || state.pending)return;
  if(entry?.save?.getAttribute('aria-disabled')==='true')return;
  const values=namesValues(row);state.pending={at:Date.now()};namesNotes.delete(id);updateNamesRows();
  let answer=null,failure=null;
  try{answer=await request('/api/candidate/names-save',{library:'Audiobooks',id,revision:row.revision,names:values,queue:true,title:askName(row)},PRESS_TIMEOUT);}catch(error){failure=error;}
  state.pending=null;
  if(answer?.queued===true){queueAccepted(row,'names',answer);updateNamesRows();return;}
  if(answer){namesDone(row,answer);return;}
  const code=failure?.body?.code;
  namesNotes.set(id,{text:!failure?.httpStatus?lostLine():code==='changed'?'This book changed. Review its details and try again.':serverSentence(failure,'Save was not accepted. Nothing was changed.'),warn:true});
  if(!failure?.httpStatus)refreshFailed(failure);
  if(code==='changed'){lastKey=null;refresh(true).catch(()=>{});}  // the next press carries the new revision
  updateNamesRows();
}
function namesDone(row,answer,forget=false){
  const id=row.id,n=Number(answer?.applies) || 1;
  namesNotes.set(id,{text:forget?'Forgotten. Nothing is renamed or moved.':namesSavedText(row,answer),warn:false});
  if(Array.isArray(answer?.entered))row.entered=answer.entered;
  if(!forget){const line=namesSavedStrip(row,answer);askNote(line);watchLeaving(row,line,answer);}else watchLeaving(row,`Took back a correction for ${askName(row)}.`,answer);
  const state=namesState.get(id);if(state){state.open=false;state.data=null;state.draft={};state.preview=null;state.previewKey='';}
  askDrafts.delete(id);renderRows(true);namesRows.get(id)?.button?.focus?.({preventScroll:true});
  namesFacts.key='';if(selectedRow?.id===id)loadNamesFacts(selectedRow);  // the panel's facts read the saved names
  const wait={id,at:Date.now()};listWait=wait;lastKey=null;
  refresh(true).then(()=>{if(listWait===wait){listWait=null;updateNamesRows();}}).catch(()=>{if(listWait===wait)listWait=null;if(!forget){namesNotes.set(id,{text:'Saved. The list could not be refreshed. It updates by itself.',warn:false});updateNamesRows();}});  // the list follows; its failure is not the save's
}
async function namesForget(id,entry){
  const row=rows.find(item=>item.id===id),state=namesState.get(id);if(!row || state?.forgetting)return;
  if(state){state.forgetting={at:Date.now()};namesNotes.delete(id);updateNamesRows();}
  let answer=null,failure=null;
  try{answer=await request('/api/candidate/names-forget',{library:'Audiobooks',id,revision:row.revision,entry_id:entry,queue:true,title:askName(row)},PRESS_TIMEOUT);}catch(error){failure=error;}
  if(state)state.forgetting=null;
  if(answer?.queued===true){queueAccepted(row,'names_forget',answer);updateNamesRows();return;}
  if(answer){namesDone(row,answer,true);return;}
  namesNotes.set(id,{text:!failure?.httpStatus?lostLine():serverSentence(failure,'Forget was not accepted. Nothing was changed.'),warn:true});updateNamesRows();
}
// A queued Save or Forget ended (ruling 35).
function namesQueued(outcome){
  const row=rows.find(item=>item.id===outcome.book_id);queueAck(outcome.id);
  if(!row){askNote(`${outcome.title || 'Book'}: ${queueWord(outcome.action)} ${outcome.result==='done'?'done':'cancelled'}.`);return;}
  if(outcome.result==='done'){namesDone(row,outcome.answer || {},outcome.action==='names_forget');return;}
  namesNotes.set(row.id,{text:`${queueWord(outcome.action)} cancelled: ${lowerFirst(serverSentence({body:{error:outcome.error}},'it was not accepted. Nothing was changed.'))}`,warn:true});updateNamesRows();
}
// ---------------------------------------------------------------- 0.22.3 (Judy's Docs/BooksArranger_0.22.3_UX_2026-10-27.md)
// 2.1: a pending press always shows text that counts: the note, then m:ss from 2 s, the ladder sentence from 3 s, and from
// 60 s "Still waiting (n min)" plus the press's own tail ("It may still go through. Don't press Save again.").
const SAVE_TAIL="It may still go through. Don't press Save again.";
function clockNote(note,since,tail='',now=ladderClock ?? Date.now()){
  if(!note || !Number.isFinite(since))return note;const age=Math.max(0,now-since);
  if(age<2000)return note;
  const clock=`${Math.floor(age/60000)}:${String(Math.floor(age/1000)%60).padStart(2,'0')}`;
  if(age>=60000)return `${note} ${clock} Still waiting (${Math.floor(age/60000)} min). The app is busy with background work.`+(tail?' '+tail:'');
  if(age>=3000)return `${note} ${clock} The app is busy with background work, so this takes longer.`;
  return `${note} ${clock}`;
}
// What still waits for an answer and shows a clock (pressTick re-renders while any of these is 2 s old or more).
function clockSince(){
  const since=[];for(const state of namesState.values()){if(state.pending)since.push(state.pending.at);if(state.forgetting)since.push(state.forgetting.at);}
  for(const pending of [trackSave,choiceSave])if(pending)since.push(pending.at);
  for(const rule of rulesView.pending.values())since.push(rule.at);
  return since;
}
// ---- Section 3: a blocked Save or Approve says why, under the control, with a one-click fix where one exists.
const PANEL_FIELD_LABELS={original_language:'Original work language',canonical_author:'Author for Artist tag',narrator:'Reader / narrator',genre:'Ebook main genre',topic:'Nonfiction topic',multi_author:'Cycle has multiple authors'};
// The panel fields Sergei changed for this book, by their labels, and the track order or files; '' if none can be named.
function panelEditsWhat(){
  const what=[],row=reviewRow || selectedRow;
  if(dirty && manualMetadataTouched && row){
    for(const [field,label] of Object.entries(PANEL_FIELD_LABELS)){
      const control=form.elements.namedItem(field);if(!control)continue;
      const now=field==='multi_author'?!!control.checked:String(control.value ?? '').trim(),was=field==='multi_author'?!!row.review?.multi_author:String(row.review?.[field] || (field==='original_language'?'Unknown':'')).trim();
      if(now!==was)what.push(label);
    }
    if(coverId!==(row.review_context?.cover_id || row.selected_cover?.id || null))what.push('the cover');
  }
  if(trackDirty && manualTrackTouched)what.push('the track order or included files');
  return what.join(', ');
}
function panelEditsLine(){const what=panelEditsWhat();return `The details panel has unsaved edits for this book: ${what || 'edits'}. Save them there, or discard them.`;}
let panelDiscarded=null;  // {id}: "Discarded the unsaved edits in the details panel." until the next change
// Discard panel edits (3): the metadata and track drafts for this book go, at once, no dialog; nothing is saved.
function discardPanelEdits(id,focusTarget){
  if(selectedRow?.id!==id)return;
  discardManualDraft();dirty=false;trackDirty=false;manualMetadataTouched=false;manualTrackTouched=false;
  select(selectedRow,true);panelDiscarded={id};controls();
  if(focusTarget && document.activeElement!==focusTarget)focusTarget.focus?.({preventScroll:true});
}
// The fix a cause has: [label, tooltip, action(row)] or null.
const BLOCK_FIXES={
  title:['Restore title',"Put the app's proposed title back.",row=>namesSetField(row,'title',namesProposal(row.id,'title') || askProposal(askOf(row),'title'))],
  series:['Clear series','Empty the Series field.',row=>namesSetField(row,'series','')],
  number:['Clear number','Empty the Number field.',row=>namesSetField(row,'number','')],
  panel:['Discard panel edits','Throw away the unsaved edits in the details panel for this book. Nothing is saved.',null]};
// One cause at a time, in the spec's order. {text, fix} ('' text: not blocked).
function saveBlock(row){
  if(!namesData(row.id))return {text:'Loading these names…',fix:null};
  const v=namesValues(row);
  if(!v.title)return {text:'Type a title first.',fix:(namesProposal(row.id,'title') || askProposal(askOf(row),'title'))?'title':null};
  if(v.series && !v.number)return {text:'Type the number in the series, or clear the series.',fix:'series'};
  if(v.number && !v.series)return {text:'Type the series name, or clear the number.',fix:'number'};
  // Unsaved panel edits never hold Save: since ruling 40 a book's panel saves no names (names_row_only, Senua's 0.22.3
  // review M3), so nothing it writes conflicts with the row's names (Judy 1, 3).
  if(!namesChanged(row))return {text:'Nothing to save: these are the names the app already has.',fix:null};
  return {text:'',fix:null};
}
function approveBlock(row){
  const ask=askOf(row);if(!ask)return {text:'',fix:null};
  if(askTitleEmpty(row))return {text:'Type a title first.',fix:askProposal(ask,'title')?'title':null};
  const names=namesFor(row);
  if(names?.series && !names.number)return {text:'Type the number in the series, or clear the series.',fix:'series'};
  if(names?.number && !names.series)return {text:'Type the series name, or clear the number.',fix:'number'};
  if(askDestination(row)?.taken===true)return {text:'That name is already in Audiobooks Sorted. Change the title or author.',fix:null};
  if(askPanelEdits(row))return {text:panelEditsLine(),fix:'panel'};
  return {text:'',fix:null};
}
// Sets one names field as if typed (Restore title, Clear series, Clear number), then the line re-renders.
function namesSetField(row,field,value){
  const entry=namesRows.get(row.id),ask=askRows.get(row.id),input=askOf(row)?ask?.controls?.find(control=>control.dataset.name===field) || entry?.inputs?.[field]:entry?.inputs?.[field];
  if(field!=='title' && !namesState.get(row.id) && !inlineNames(row))return;
  if(input)input.value=value;
  namesChangedField(row,field,value);namesPreview(row.id,0);controls();
  (input || entry?.save)?.focus?.({preventScroll:true});
}
// Renders one block line: the sentence, and the fix button when it belongs here. element: the p.block-why.
function renderBlock(element,block,row,withFix,button){
  if(!element)return;
  if(!block.text && !block.fix && panelDiscarded?.id===row.id)block={text:'Discarded the unsaved edits in the details panel.',fix:null};
  const fix=withFix && block.fix?BLOCK_FIXES[block.fix]:null,key=JSON.stringify([block.text,fix?.[0] || '']);
  element.hidden=!block.text && !fix;
  if(element.dataset.key!==key){
    element.dataset.key=key;element.replaceChildren(node('span',block.text));
    if(fix){
      const press=node('button',fix[0],'quiet block-fix');press.type='button';press.title=fix[1];press.setAttribute('aria-label',fix[0]+': '+askName(row));
      press.addEventListener('click',event=>{event.stopPropagation();if(block.fix==='panel')discardPanelEdits(row.id,button);else fix[2](row);});
      press.addEventListener('keydown',event=>event.stopPropagation());element.append(press);
    }
  }
}
// ---- Section 2.2 and 2.3: the strip says what a Save did and, when the list reload takes the book away, where it went.
const leavers=new Map();  // id -> {at, base, row, title}
let stripShow=null,listWait=null;  // stripShow: {id, title} for "Show it"; listWait: {id, at} while a Save's list reload runs
function savedPath(answer){const path=answer?.destination?.path;return typeof path==='string' && path?outputName()+'\\'+path:'';}
function namesSavedStrip(row,answer){
  const title=askName(row),n=Number(answer?.applies) || 1,applies=n>1?` Applies to ${n.toLocaleString()} books.`:'';
  if(answer?.outcome==='ready_only')return `Saved names for ${title}. The finished audiobook in Audiobooks Sorted keeps its name.`;
  const path=savedPath(answer);
  return `Saved names for ${title}.`+(path?` Goes to ${path}.`:'')+applies;
}
function watchLeaving(row,base,answer){if(row?.id)leavers.set(row.id,{at:Date.now(),base,row:answer?.list_row || null,title:askName(row)});}
function leftStatus(entry){
  if(!entry.row)return '';
  try{return candidateStatus({...entry.row,path:entry.row.id,kind:'candidate'}) || '';}catch(error){return '';}
}
// The first list answer requested after the press: a book it omits left this list (never a delete or a removal).
function noteLeavers(sentAt){
  for(const [id,entry] of [...leavers]){
    if(entry.at>sentAt)continue;
    leavers.delete(id);
    if(rows.some(row=>row.id===id) || deleteNotes.has(id) || ['deleted','removed','copy_removed'].includes(askDone.get(id)))continue;
    const status=leftStatus(entry);
    askNote(entry.base+(status?` It left this list: ${status}.`:' It left this list. Find it under All.'));
    stripShow={id,title:entry.title};renderStripShow();
  }
}
function renderStripShow(){
  const button=$('strip-show');if(!button)return;
  const shown=!!stripShow && !!stripNote;button.hidden=!shown;
  if(shown){button.setAttribute('aria-label','Show it: '+stripShow.title);button.title='List this book: sets Status to All and searches for its title.';}
}
async function showLeaver(){
  const target=stripShow;if(!target)return;
  $('search').value=target.title;filters[view]='all';attentionGroup='all';resetStrip();viewControls();
  await updateList();
  const row=rows.find(item=>item.id===target.id);
  if(row){select(row,true);const tr=[...$('inventory').children].find(item=>item.dataset?.path===row.path);tr?.scrollIntoView?.({block:'center',behavior:'auto'});tr?.focus?.({preventScroll:true});}
}
// ---- Section 2.5: the panel's own saves, each with its line beside the button.
let trackSave=null,choiceSave=null;  // {at} while Save track review / Save choices wait
let metaSaveResult=null;  // {text, warn} for #review-note after Save preview metadata
function savedFieldsLine(before,review){
  const labels={original_language:'Original work language',canonical_author:'Author for Artist tag',narrator:'Reader / narrator',genre:'Ebook main genre',topic:'Nonfiction topic',multi_author:'Cycle has multiple authors',
    title:'Canonical title',author:'Author folder name',universe:'Universe',series:'Series / cycle',number:'Number in series',anthology:'Short-story collection'};
  const changed=Object.keys(labels).filter(field=>field in review && (typeof review[field]==='boolean'?!!before?.[field]!==review[field]:String(before?.[field] || (field==='original_language'?'Unknown':'')).trim()!==String(review[field] ?? '').trim()));
  return changed.length?`Saved: ${changed.map(field=>labels[field]).join(', ')}.`:'Saved.';
}
// ---- Section 1: View metadata shows a book's names as facts; the row's Edit names box is the one editor (ruling 40).
const namesFacts={key:'',seq:0,data:null,failed:false};
function namesLocked(){return selectedRow?.kind==='candidate';}
const NAME_INPUTS=['title','author','universe','series','number','anthology'];
function renderNamesInputs(){
  const locked=namesLocked();
  for(const field of NAME_INPUTS){
    const input=form.elements.namedItem(field);if(!input)continue;input.disabled=locked;
    // Its label (the collection box: the block around its label) hides with it; the Files view keeps all six.
    let holder=input.parentElement;for(let up=0;holder && up<3 && !String(holder.className || '').split(' ').includes('names-input');up++)holder=holder.parentElement;
    if(holder && String(holder.className || '').split(' ').includes('names-input'))holder.hidden=locked;
  }
  const facts=$('names-facts');if(facts)facts.hidden=!locked;
}
function factText(field,data){
  const value=data?.fields?.[field]?.proposal;
  if(field==='collection')return value===true?'Yes':'No';
  if(field==='series'){const series=String(value || '').trim(),number=String(data?.fields?.number?.proposal || '').trim();return series?series+(number?` · No. ${number}`:''):'None';}
  if(field==='universe')return String(value || '').trim() || 'None';
  return String(value || '').trim();
}
async function loadNamesFacts(row){
  const key=JSON.stringify([row.id,row.revision]);if(namesFacts.key===key && (namesFacts.data || namesFacts.failed))return renderNamesFacts();
  namesFacts.key=key;namesFacts.data=null;namesFacts.failed=false;const seq=++namesFacts.seq;renderNamesFacts();
  try{const answer=await request('/api/candidate/names',{library:'Audiobooks',id:row.id,revision:row.revision},PRESS_TIMEOUT);if(seq===namesFacts.seq)namesFacts.data=answer?.editor || null;if(seq===namesFacts.seq && !namesFacts.data)namesFacts.failed=true;}
  catch(error){if(seq===namesFacts.seq)namesFacts.failed=true;}
  finally{if(seq===namesFacts.seq)renderNamesFacts();}
}
function namesFactsInert(row){
  if(!row)return '';
  if(!rows.some(item=>item.id===row.id))return "This book isn't on the current page. Clear the filters or find it in the list, then press Edit names.";
  return namesButtonInert(row);
}
function renderNamesFacts(){
  const row=selectedRow;if(!$('names-facts') || !namesLocked() || !row)return;
  const list=$('names-facts-list'),help=$('names-facts-help'),data=namesFacts.data;
  list.hidden=namesFacts.failed;
  for(const field of ['title','author','series','universe','collection'])setText('names-fact-'+field,data?factText(field,data):namesFacts.failed?'':'Loading names…');
  setText('names-facts-help',namesFacts.failed?'Names unavailable. Press Edit names to see them in the list.':"Names are edited on the book's row in the list.");help.hidden=false;
  const inert=namesFactsInert(row),button=$('names-facts-edit'),why=$('names-facts-why');
  button.title=inert || "Open this book's Edit names box in the list.";button.setAttribute('aria-label','Edit names: '+askName(row));
  if(inert)button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
  if(why){if(why.textContent!==inert)why.textContent=inert;why.hidden=!inert;}
}
// Edit names (panel, and the Automatic result's names hold): the list scrolls the book's row to the middle and its editor opens.
function panelEditNames(){
  const row=selectedRow;if(!row || ended || namesFactsInert(row))return;
  const live=rows.find(item=>item.id===row.id),tr=[...$('inventory').children].find(item=>item.dataset?.path===live.path);
  tr?.scrollIntoView?.({block:'center',behavior:'auto'});
  if(namesOpen(row.id))return focusNames(row.id);
  return namesToggle(row.id);
}
// A hold's fields name the book's identity: title and canonical_author (the author), series, number, universe (manual_metadata.holds).
const NAME_HOLD_FIELDS=new Set(['title','author','canonical_author','series','number','universe','collection','anthology']);
function namesHold(row){const fields=(row?.metadata_holds || []).flatMap(item=>item.fields || []);return fields.length>0 && fields.every(field=>NAME_HOLD_FIELDS.has(field));}
// ---- Section 4: author rules learned online, with Take back.
const rulesView={state:'loading',rules:[],total:0,confirm:null,pending:new Map(),errors:new Map(),retryTimer:null,find:''};
const RULES_SHOWN=200;
function ruleHost(source){try{const url=new URL(source);return /^https?:$/.test(url.protocol)?url.host:'';}catch(error){return '';}}
function ruleCredit(rule){return String(rule.credit || '').trim();}
function ruleLine(rule){return rule.kind==='keep'?`${ruleCredit(rule)} stays as written. The author writes in Russian.`:`${ruleCredit(rule)} → ${rule.target}`;}
function ruleConfirmText(rule){return rule.kind==='keep'?`Take back this rule? The app stops treating ${ruleCredit(rule)} as a Russian-writing author and asks about this name again. Books already filed keep their folders.`
  :`Take back this rule? The app stops filing ${ruleCredit(rule)} as ${rule.target} and asks about this name again. Books already filed keep their folders.`;}
async function loadAuthorRules(){
  if(ended)return;if(rulesView.retryTimer){clearTimeout(rulesView.retryTimer);rulesView.retryTimer=null;}
  try{const answer=await request('/api/author-rules',{});rulesView.rules=Array.isArray(answer?.rules)?answer.rules:[];rulesView.total=Number(answer?.total) || rulesView.rules.length;rulesView.state='ready';}
  catch(error){if(rulesView.state!=='ready')rulesView.state='failed';if(typeof setTimeout==='function')rulesView.retryTimer=setTimeout(loadAuthorRules,30000);}
  renderAuthorRules();
}
function renderAuthorRules(){
  const summary=$('author-rules-summary'),list=$('author-rules-list');if(!summary || !list)return;
  const text=rulesView.state==='loading'?'Author rules learned online · loading…':rulesView.state==='failed'?'Author rules learned online · unavailable':`Author rules learned online · ${rulesView.rules.length.toLocaleString()}`;
  if(summary.textContent!==text)summary.textContent=text;
  const note=$('author-rules-note'),find=rulesView.find.trim().toLocaleLowerCase();
  if(rulesView.state==='failed' && !rulesView.rules.length){note.textContent="The list couldn't be read. It tries again by itself.";note.hidden=false;list.replaceChildren();return;}
  const matching=find?rulesView.rules.filter(rule=>(ruleCredit(rule)+' '+(rule.target || '')).toLocaleLowerCase().includes(find)):rulesView.rules;
  const shown=find?matching:matching.slice(0,RULES_SHOWN);
  const noteText=rulesView.state!=='ready'?'':!rulesView.rules.length?"No author rules learned yet. When research finds a foreign author's English name online, it is listed here."
    :find && !matching.length?`No rule matches «${rulesView.find.trim()}».`:!find && rulesView.rules.length>RULES_SHOWN?`Showing the newest ${RULES_SHOWN} of ${rulesView.rules.length.toLocaleString()}. Find author searches all of them.`:'';
  if(note.textContent!==noteText)note.textContent=noteText;note.hidden=!noteText;
  const focused=document.activeElement,keep=focused?.dataset?.rule ? focused.dataset.rule+'|'+focused.dataset.role : '';
  list.replaceChildren(...shown.map(rule=>ruleEntry(rule)));
  if(keep){const again=walkFind(list,element=>element.dataset?.rule+'|'+element.dataset?.role===keep);again?.focus?.({preventScroll:true});}
}
function walkFind(element,test){for(const child of element.children || []){if(test(child))return child;const found=walkFind(child,test);if(found)return found;}return null;}
function ruleButton(label,tip,rule,role,action){
  const button=node('button',label,'quiet');button.type='button';button.title=tip;button.setAttribute('aria-label',`${label}: ${ruleCredit(rule)}`);button.dataset.rule=rule.rule_id;button.dataset.role=role;
  button.addEventListener('click',event=>{event?.stopPropagation?.();action();});return button;
}
function ruleEntry(rule){
  const box=node('div','','author-rule'),text=node('div','','author-rule-text'),pending=rulesView.pending.get(rule.rule_id),error=rulesView.errors.get(rule.rule_id);
  box.dataset.rule=rule.rule_id;text.append(node('p',ruleLine(rule)));
  const line=node('p','','field-help'),host=ruleHost(rule.source);
  if(host){const link=node('a',`Found on ${host}`);link.href=rule.source;link.target='_blank';link.rel='noopener noreferrer';link.title='Open this source in your browser.';line.append(link);}
  else line.append(node('span',`Source: ${rule.source || 'public research'}`));
  const learned=String(rule.saved_utc || '').slice(0,10),first=String(rule.question || '').trim();
  line.append(node('span',(learned?` · Learned ${learned}`:'')+(first?` · First seen on «${first}»`:'')));text.append(line);box.append(text);
  const confirming=rulesView.confirm===rule.rule_id && !pending;
  if(!confirming){
    const take=ruleButton(pending?'Taking back…':'Take back',pending?'Taking this rule back…':'Stop using this rule. Nothing is renamed or moved.',rule,'take',()=>{if(rulesView.pending.has(rule.rule_id))return;openRuleConfirm(rule);});
    if(pending)take.setAttribute('aria-disabled','true');box.append(take);
  }
  if(pending)box.append(node('p',clockNote('Taking this rule back…',pending.at),'field-help'));
  if(confirming){
    const confirm=node('div','','author-rule-confirm');confirm.append(node('p',ruleConfirmText(rule)));
    const go=ruleButton('Take back rule','Take this rule back now. Nothing is renamed or moved.',rule,'go',()=>takeBackRule(rule));
    const keep=ruleButton('Keep rule','Keep this rule and close this question.',rule,'keep',()=>closeRuleConfirm(rule));
    confirm.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault?.();closeRuleConfirm(rule);}});
    confirm.append(go,keep);box.append(confirm);
  }
  if(error){const alert=node('p',error,'rule-error');alert.setAttribute('role','alert');box.append(alert);}
  return box;
}
function ruleFocus(rule,role){const element=walkFind($('author-rules-list'),child=>child.dataset?.rule===rule.rule_id && child.dataset?.role===role);element?.focus?.({preventScroll:true});}
function openRuleConfirm(rule){rulesView.confirm=rule.rule_id;rulesView.errors.delete(rule.rule_id);renderAuthorRules();ruleFocus(rule,'keep');}
function closeRuleConfirm(rule){rulesView.confirm=null;renderAuthorRules();ruleFocus(rule,'take');}
async function takeBackRule(rule){
  if(rulesView.pending.has(rule.rule_id))return;
  const index=rulesView.rules.findIndex(item=>item.rule_id===rule.rule_id);
  rulesView.confirm=null;rulesView.pending.set(rule.rule_id,{at:Date.now()});rulesView.errors.delete(rule.rule_id);renderAuthorRules();ruleFocus(rule,'take');
  let answer=null,failure=null;
  try{answer=await request('/api/author-rule/retract',{rule_id:rule.rule_id},PRESS_TIMEOUT);}catch(error){failure=error;}
  rulesView.pending.delete(rule.rule_id);
  if(answer){
    rulesView.rules=rulesView.rules.filter(item=>item.rule_id!==rule.rule_id);
    const n=Number(answer.requeued) || 0;
    const done=n?`Took back the rule for ${ruleCredit(rule)}. ${n===1?'1 waiting book is':`${n.toLocaleString()} waiting books are`} checked again.`:`Took back the rule for ${ruleCredit(rule)}. The app asks about this name the next time it meets it.`;
    // The strip (in the to-do list) and the list's own line, which is on screen in every view.
    askNote(done);setText('author-rules-status',done);
    renderAuthorRules();
    // Focus: the next rule's Take back, else the previous one's, else Find author, else the summary (4.4).
    const list=rulesView.find.trim()?rulesView.rules.filter(item=>(ruleCredit(item)+' '+(item.target || '')).toLocaleLowerCase().includes(rulesView.find.trim().toLocaleLowerCase())):rulesView.rules;
    const next=list[Math.min(Math.max(index,0),list.length-1)];
    if(next)ruleFocus(next,'take');else ($('author-rules-find') || $('author-rules-summary'))?.focus?.({preventScroll:true});
    lastKey=null;refresh(true).catch(()=>{});
    return;
  }
  const replaced=failure?.httpStatus && /already replaced or taken back/.test(String(failure?.body?.error || ''));
  rulesView.errors.set(rule.rule_id,!failure?.httpStatus?"This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check the list in a moment.":serverSentence(failure,'Take back was not accepted. Nothing was changed.'));
  renderAuthorRules();ruleFocus(rule,'take');
  if(replaced)loadAuthorRules();
}

// ---------------------------------------------------------------- Queued Retry, Repair and Delete book (0.22.1)
// Judy's 0.22.1 spec, section 1 (backlog 2 and 3): a press while another operation runs is accepted and queued by the
// engine (action_queue.py), never refused as busy. One queue, first in first out, one action at a time, held in the
// engine's memory, so a reload, a filter change or a second look read the same state from /api/state. The row says what
// it waits for and has its own Cancel; a queued action never opens a dialog, moves focus or makes a sound when it runs;
// its outcome lands in the row, the strip line and a polite announcement. Every check runs again when it runs.
const QUEUE_WORDS={operation:['The app is working on another action','the current action'],scan:['A scan is running','the scan'],
  retry_run:['A retry run is in progress','the retry run'],approve_run:['A bulk approval is in progress','the bulk approval'],book:['This book is being processed',"this book's processing"],
  // Ruling 35 (provisional copy, sent to Judy): what a queued press also waits for.
  loading:['Books Arranger is still loading','loading'],jobs:['Audiobook conversion is running','the conversion'],automatic:['Automatic processing is running','automatic processing']};
// The word of each queued action (ruling 35), for its queued line, Cancel and outcome.
const QUEUE_ACTION_WORDS={retry:'Retry',repair:'Repair',delete:'Delete',approve:'Approve',convert:"Convert what's there",separate:'Keep as separate books',
  scan_again:'Scan again',dismiss:'Remove from list',copy:'Remove this copy',names:'Save',names_forget:'Forget',scan_start:'Start scanning',scan_resume:'Resume scanning'};
function queueWord(action){return QUEUE_ACTION_WORDS[action] || 'An action';}
// The kind's words (1.2). An unknown kind reads as operation; the bulk approval runs in this page, so the page names it.
function queueKind(kind){const known=Object.hasOwn(QUEUE_WORDS,kind || '')?kind:'operation';return known==='operation' && askBulk?'approve_run':known;}
function queueS(kind){return QUEUE_WORDS[queueKind(kind)][0];}
function queueP(kind){return QUEUE_WORDS[queueKind(kind)][1];}
function queueTitle(row){return row?.title_clue || row?.review?.title || 'Book';}
function queuedFor(row,action){const item=row?queueState.queued.find(entry=>entry.book_id===row.id):null;return item && (!action || item.action===action)?item:null;}
function queueRunning(row,action){const r=queueState.running;return !!row && r?.book_id===row.id && (!action || r.action===action);}
function queueAhead(item){const position=Number(item?.position);return Number.isInteger(position) && position>1?position-1:0;}
function queueBlocker(item){return item?.blocker?.kind;}
function deleteQueued(row){return !!(queuedFor(row,'delete') || queueRunning(row,'delete'));}
const QUEUE_SIBLING='A delete is queued for this book. Cancel it to use this.';
// Its mirror on Delete book (Judy's implementation check, N1): a queued Retry or Repair on the row.
const QUEUE_SIBLING_RETRY='A retry is queued for this book. Cancel it to use this.',QUEUE_SIBLING_REPAIR='A repair is queued for this book. Cancel it to use this.';
// The page's own "busy" before 0.22.1: one press at a time, plus the bulk runs. Other presses keep it (offer 1).
function pressBusy(){return busy || recoverySubmitting || automaticRequest!==null || !!retryPending || bulkRunning() || releaseRun || askPendings.size>0 || askBulk;}
// Ruling 35 (Sergei 2026-10-26): a press the page itself would have held back ("Another operation is in progress.") is
// accepted and waits here, first in first out, then runs when the page is free, every check made again then (the press
// runs as if pressed then). The row or button shows it queued, with Cancel. Kept in this page's memory, like a draft.
const laterPresses=[];let laterSeq=0,laterRunning=false;
const LATER_WORDS={startover:'Start over',combined:'Start over',release:'Let the app handle it',clear:'Clear working files',convert:'Convert',keep:'Keep files',prepare:'Prepare recovery',
  retry:'Retry',repair:'Repair',scan_start:'Start scanning',scan_resume:'Resume scanning',scan_stop:'Stop scanning',pause:'Pause audiobook jobs',resume:'Resume audiobook jobs',
  start_automatic:'Start automatic processing',stop_automatic:'Stop automatic processing',create:'Create audiobook',queue_books:'Queue selected',find_metadata:'Find metadata',
  find_covers:'Find local covers',save_tracks:'Save track review',check_metadata:'Check metadata',approve_candidate:'Approve candidate metadata',retry_all:'Retry all',retry_selected:'Retry selected',save_choices:'Save choices',release_selected:'Let the app handle selected'};
function laterWord(kind){return LATER_WORDS[kind] || 'This press';}
function laterFor(key){return laterPresses.find(item=>item.key===key) || null;}
// Provisional copy (ruling 35, sent to Judy).
// The rest of ruling 35 (ruling 37): a press the engine answered "busy" waits here too and is sent again, with why.
// Judy 14.6: every queued line says "the app is free" ("the catalog" is where the data lives, not a busy state).
const LATER_WHY={catalog:'It runs when the app is free.',app:'It runs when the app is free.',file:'It tries again every 10 s.'};
function laterLine(item){
  if(!loadingActive && item.why==='file')return `${laterWord(item.kind)} queued: a file is open in another program. ${LATER_WHY.file}`;
  if(!loadingActive && item.why && LATER_WHY[item.why])return `${laterWord(item.kind)} queued. ${LATER_WHY[item.why]}`;
  return `${laterWord(item.kind)} queued. It runs when ${loadingActive?'loading':item.waitFor?.()?'the scan':'the current action'} finishes.`;
}
function pressLater(key,kind,title,run,waitFor=null,why=''){
  if(laterFor(key))return laterFor(key);
  const item={id:'later-'+(++laterSeq),key,kind,title:title || '',run,at:Date.now(),waitFor,why};laterPresses.push(item);
  queueAnnounce(`${laterWord(kind)} queued${item.title?': '+item.title:''}.`);controls();return item;
}
// A press the engine answered "busy" (a catalog still busy after its own 30 s of tries, a file another program holds open):
// held and sent again after a pause, every check again then (ruling 35); the row shows it queued, with Cancel.
function holdAgain(key,kind,title,run,why,seconds){const until=Date.now()+seconds*1000;return pressLater(key,kind,title,run,()=>Date.now()<until,why);}
function cancelLater(key){
  const index=laterPresses.findIndex(item=>item.key===key);if(index<0)return false;
  const [item]=laterPresses.splice(index,1);queueAnnounce(`${laterWord(item.kind)} cancelled${item.title?': '+item.title:''}.`);controls();return true;
}
// The toolbar and panel buttons (ruling 35): a press made while another press of this page runs, or while loading, waits
// (pressLater) and runs then, as if pressed then; the same button pressed again takes it back. Provisional copy, for Judy.
// The presses the engine still refuses while a library scan runs (Create audiobook, Queue selected, Resume audiobook jobs):
// the page holds them until the scan ends.
// The rest of ruling 35 (ruling 37): Retry all and Retry selected too ("Scanning is running. Retry when it stops.").
const SCAN_HELD=['create','queue_books','resume','retry_all','retry_selected'];
function scanRunning(){return !!state?.active_library;}
// After the engine said a scan runs (409 code scanning): wait for it, and at least 3 s, until the page has read the scan too.
function scanSeen(){const until=Date.now()+3000;return ()=>scanRunning() || Date.now()<until;}
function later(key,kind,handler){
  return (...args)=>{
    if(laterFor(key)){cancelLater(key);return;}
    const waitFor=SCAN_HELD.includes(kind)?scanRunning:null;
    if(!ended && (busy || automaticRequest!==null || !!LS && loadingActive || waitFor?.())){const item=pressLater(key,kind,'',()=>handler(...args),waitFor);message(laterLine(item)+' Press it again to cancel.');return;}
    return handler(...args);
  };
}
const laterDecorated=new Set();
function renderLaterButtons(){
  const now=new Set();
  for(const item of laterPresses){
    if(!item.key.startsWith('toolbar:'))continue;const id=item.key.slice(8),button=$(id);if(!button?.setAttribute)continue;now.add(id);
    if(!laterDecorated.has(id)){button.dataset.laterTitle=button.title || '';laterDecorated.add(id);}
    const tip=laterLine(item)+' Press it again to cancel.';if(button.title!==tip)button.title=tip;button.setAttribute('aria-disabled','true');button.disabled=false;
  }
  for(const id of [...laterDecorated])if(!now.has(id)){const button=$(id);laterDecorated.delete(id);if(button?.setAttribute){button.title=button.dataset?.laterTitle || '';button.removeAttribute('aria-disabled');}}
}
function drainLater(){
  if(laterRunning || !laterPresses.length || pressBusy() || loadingActive || laterPresses[0].waitFor?.())return;
  const item=laterPresses.shift();laterRunning=true;
  Promise.resolve().then(()=>item.run()).catch(()=>{}).finally(()=>{laterRunning=false;controls();});
}
// What a Retry or Delete pressed now would wait for, as far as the page knows. The engine's answer decides.
function pageBlocker(){
  if(state?.active_library)return 'scan';
  if(bulkRunning() || retrySelectedRun)return 'retry_run';
  if(askBulk)return 'approve_run';
  if(queueState.queued.length)return queueBlocker(queueState.queued[0]) || 'operation';
  if(queueState.running || pressBusy() || deletePending)return 'operation';
  return null;
}
function queueAnnounce(text){const p=$('queue-announce');if(!p)return;if(p.textContent===text)p.textContent='';p.textContent=text;}
function queueAck(id){if(typeof id==='string')request('/api/queue/ack',{ids:[id]}).catch(()=>{});}
function dropQueueNote(bookId){const note=queueNotes.get(bookId);if(!note)return;queueNotes.delete(bookId);queueAck(note.outcome);}
function dropQueueStrip(){if(queueStripOutcome){queueAck(queueStripOutcome);queueStripOutcome=null;}}
// /api/state's queue (absent while loading). Each outcome is applied once; it is acknowledged when its line is dismissed.
function syncQueue(answer){
  if(!Array.isArray(answer?.queued_actions))return;
  const running=answer.queue_running && typeof answer.queue_running==='object' && typeof answer.queue_running.book_id==='string'?answer.queue_running:null;
  queueState={queued:answer.queued_actions.filter(item=>item && typeof item.id==='string' && typeof item.book_id==='string'),running};
  for(const id of [...queueLate.keys()])if(!queueState.queued.some(item=>item.id===id) && running?.id!==id)queueLate.delete(id);
  const fresh=(Array.isArray(answer.queue_outcomes)?answer.queue_outcomes:[]).filter(item=>item && typeof item.id==='string' && typeof item.book_id==='string' && !queueSeen.has(item.id));
  for(const outcome of fresh){queueSeen.add(outcome.id);applyQueueOutcome(outcome);}
  if(fresh.length)lastKey=null;
}
// The press was queued (202 queued): the row shows it at once, before the next poll.
function queueAccepted(row,action,answer){
  const item={id:answer.id,action,book_id:row.id,title:queueTitle(row),position:Number(answer.position) || queueState.queued.length+1,blocker:answer.blocker,...(action==='delete'?{n:answer.n}:{})};
  queueState={...queueState,queued:[...queueState.queued.filter(entry=>entry.id!==item.id && entry.book_id!==row.id),item].sort((a,b)=>(Number(a.position) || 0)-(Number(b.position) || 0))};
  queueAnnounce(`${queueWord(action)} queued: ${item.title}.`);
}
function lowerFirst(text){return text?text[0].toLowerCase()+text.slice(1):text;}
// A refused queued Retry or Repair (1.6), from its typed code; the server's own sentence for the others.
function queueRetryText(outcome){
  const word=outcome.action==='repair'?'Repair':'Retry';
  if(outcome.code==='changed')return `${word} cancelled: this book needs another look. Check its status above.`;
  const said=typeof outcome.error==='string' && outcome.error.trim()?outcome.error.trim().replace(/^(Retry|Repair) was not accepted: /,''):'';
  return said?`${word} cancelled: ${lowerFirst(said)}`:`${word} cancelled: it was not accepted. Check the status above.`;
}
function queueDeleteText(outcome){
  const files=Array.isArray(outcome.files)?outcome.files:[];
  const line={changed:"this book doesn't match what you confirmed. Nothing was deleted. Open its details and try again.",
    files_changed:"the files don't match the list you confirmed. Nothing was deleted. Press Delete book to see the current list.",
    shared:files.length>1?`${files.length.toLocaleString()} files also belong to other books. Nothing was deleted.`:'a file also belongs to another book. Nothing was deleted.',
    sorted:`a finished audiobook of this book is in ${outputName()}. Nothing was deleted.`,
    offline:`can't reach ${typeof outcome.root==='string' && outcome.root?outcome.root:'the source drive'}. Nothing was deleted.`}[outcome.code];
  const said=typeof outcome.message==='string' && outcome.message.trim()?lowerFirst(outcome.message.trim()):'';  // S6: its own cause
  return 'Delete cancelled: '+(line || said || 'it was not accepted. Nothing was deleted.');
}
// A partial queued delete (1.6): the counts, up to three files with their causes, then what to do.
function queuePartial(outcome){
  const failed=Array.isArray(outcome.failed)?outcome.failed:[],k=Number(outcome.deleted) || 0,n=Number(outcome.n) || k+failed.length,f=failed.length;
  const lines=failed.slice(0,3).flatMap(item=>[{text:String(item.path || ''),kind:'path'},{text:DELETE_CAUSE[item.cause] || DELETE_CAUSE.other,kind:'muted'}]);
  if(f>3)lines.push({text:`+ ${(f-3).toLocaleString()} more.`});
  lines.push({text:'The book stays listed. Press Delete book to try again.'});
  return {text:`Deleted ${k.toLocaleString()} of ${n.toLocaleString()} files. ${f===1?'1 is':f.toLocaleString()} still on disk.`,lines,
    strip:`Deleted ${k.toLocaleString()} of ${n.toLocaleString()} files. The book stays listed with the ${f.toLocaleString()} that could not be deleted.`};
}
const QUEUE_DELETE_UNKNOWN="The delete may not have finished. The app hasn't confirmed it. Check the list before trying again.";
function applyQueueOutcome(outcome){
  // A row line's status is taken from the first list read after the outcome (the rows on screen predate the run).
  const id=outcome.book_id,row=rows.find(item=>item.id===id),title=outcome.title || queueTitle(row),status=null,gen=listGeneration;
  queueLate.delete(outcome.id);
  if(outcome.action==='copy' && outcome.result==='done'){
    deleteNotes.set(id,{text:ASK_DONE.copy_removed[1],warn:false,done:true});if(askRows.has(id))askDone.set(id,'copy_removed');
    askNote(`Queued removal finished: ${title}. ${ASK_DONE.copy_removed[1]}`);queueStripOutcome=outcome.id;if(row)forgetDeleted(row);queueAnnounce(`${title}: ${ASK_DONE.copy_removed[1]}`);return;
  }
  if(outcome.action==='copy'){const text=`Remove this copy cancelled: ${lowerFirst(serverSentence({body:{error:outcome.error}},'it was not accepted. Nothing was deleted.'))}`;queueNotes.set(id,{text,warn:true,outcome:outcome.id,status,gen});queueAnnounce(`${title}: ${text}`);return;}
  if(outcome.action==='delete'){
    if(outcome.result==='done'){
      deleteNotes.set(id,{text:ASK_DONE.deleted[1],warn:false,done:true});if(askRows.has(id))askDone.set(id,'deleted');
      askNote(`Queued delete finished: ${title}. ${deleteStrip('delete',Number(outcome.deleted) || 0,Number(outcome.bytes) || 0,outcome.folders)}`);queueStripOutcome=outcome.id;
      if(row)forgetDeleted(row);  // Judy 0.22.2 section 5: a queued delete's row leaves at its outcome too
      queueAnnounce(`${title}: ${ASK_DONE.deleted[1]}`);return;
    }
    if(outcome.result==='refused' && outcome.code==='not_listed'){
      askNote(`Delete cancelled for ${title}: the book isn't listed. Nothing was deleted.`);queueStripOutcome=outcome.id;queueAnnounce(`Delete cancelled for ${title}: the book isn't listed. Nothing was deleted.`);return;
    }
    if(outcome.result==='partial'){
      const shown=queuePartial(outcome);deleteNotes.set(id,{text:shown.text,warn:true,lines:shown.lines,outcome:outcome.id});askNote(shown.strip);queueStripOutcome=outcome.id;
      queueAnnounce(`${title}: ${shown.text}`);return;
    }
    const text=outcome.result==='refused'?queueDeleteText(outcome):QUEUE_DELETE_UNKNOWN;
    queueNotes.set(id,{text,warn:true,outcome:outcome.id,status,gen});queueAnnounce(`${title}: ${text}`);return;
  }
  const asked=Object.keys(ASK_QUEUE).find(kind=>ASK_QUEUE[kind]===outcome.action);
  if(asked){
    // Ruling 35: a queued Approve, Keep, Scan again or Remove from list ended; the row shows it as its press would have.
    const entry=askRows.get(id) || {id,row,title};
    if(outcome.result==='saved' && outcome.code==='series_needed' && outcome.answer?.saved===true && outcome.answer?.code==='series_needed'){askSettled(entry,asked,outcome.answer,null);queueAck(outcome.id);return;}
    if(outcome.result==='done'){askSettled(entry,asked,outcome.answer || {},null);queueStripOutcome=outcome.id;queueAnnounce(`${title}: ${queueWord(outcome.action)} done.`);return;}
    const text=queueAskText(outcome,asked);askResults.set(id,{text});queueAnnounce(`${title}: ${text}`);queueAck(outcome.id);return;
  }
  if(outcome.action==='names' || outcome.action==='names_forget'){namesQueued(outcome);return;}
  if(outcome.result==='done'){
    // The press ran as today (1.6): the row shows the server's queued state; the existing strip line names the book.
    const key=row?retryKey(row):null;if(key)remember(key,'queued',outcome.action,outcome.answer?.position);
    const next=queuedNextText({position:outcome.answer?.position}),line=`${title} queued — ${next.replace(/^Queued — /,'')}`;
    askNote(line);queueStripOutcome=outcome.id;queueAnnounce(`${title}: ${next}`);return;
  }
  const text=queueRetryText(outcome);queueNotes.set(id,{text,warn:true,outcome:outcome.id,status,gen});queueAnnounce(`${title}: ${text}`);
}
// A refused queued press (ruling 35): its gate's own words, else the engine's sentence; never the bare refusal.
function queueAskText(outcome,kind){
  const error={httpStatus:409,body:{code:outcome.code,error:outcome.error}};
  return `${queueWord(outcome.action)} cancelled: ${lowerFirst(askErrorText(error,kind))}`;
}
// The row line of a queued or running action (1.4), or null.
function queueHint(row){
  const late=[...queueLate.values()].find(item=>item.book_id===row.id);if(late && (queuedFor(row) || queueRunning(row)))return late.text;
  const item=queuedFor(row);
  if(item){
    const p=queueP(queueBlocker(item)),n=queueAhead(item),ahead=n?`, ${n.toLocaleString()} ahead`:'';
    if(item.action==='delete')return `Delete queued${ahead}. Nothing is deleted yet. It runs when ${p} finishes.`;
    if(item.action==='copy')return `Remove this copy queued${ahead}. Nothing is deleted yet. It runs when ${p} finishes.`;
    if(['retry','repair'].includes(item.action))return `${item.action==='repair'?'Repair':'Retry'} queued${ahead}. Starts when ${p} finishes.`;
    // Ruling 35 (provisional copy, sent to Judy): his values are kept with the queued press.
    return `${queueWord(item.action)} queued${ahead}. Your choices are saved. It runs when ${p} finishes.`;
  }
  const running=queueState.running;if(!queueRunning(row))return null;
  if(running.action==='delete' || running.action==='copy'){const n=Number(running.n) || 0;return n===0?'Removing this book…':n===1?'Deleting 1 file…':`Deleting ${n.toLocaleString()} files…`;}
  const asked=Object.keys(ASK_QUEUE).find(kind=>ASK_QUEUE[kind]===running.action);
  if(asked)return ASK_PENDING[asked][1];
  if(running.action==='names' || running.action==='names_forget')return 'Saving these names…';
  return rowActions[running.action==='repair'?'repair':'retry'].note;
}
// A queued line ends when its status changes (the existing retryResult lifetime, 1.6).
function queueNoteFor(row){
  const note=queueNotes.get(row.id);if(!note)return null;
  const status=candidateStatus(row);if(note.status===null || note.status===undefined){if(listGeneration>(note.gen ?? -1))note.status=status;return note;}
  if(note.status!==status){dropQueueNote(row.id);return null;}
  return note;
}
// Every list read checks each queued line against its book's status, shown or not (a Queued row has no line slot).
function pruneQueueNotes(){for(const id of [...queueNotes.keys()]){const row=rows.find(item=>item.id===id);if(row)queueNoteFor(row);}}
async function cancelQueued(row,action){
  const item=queuedFor(row,action);if(!item || queueCancels.has(item.id) || queueLate.has(item.id))return false;
  const buttons=rowButtons(row.path),word=action==='delete'?'delete':action;
  const inRow=!!buttons?.contains?.(document.activeElement) || document.activeElement===$('retry-cancel') || document.activeElement===$('retry-job');
  queueCancels.add(item.id);controls();
  let answer=null,failure=null;
  try{answer=await request('/api/queue/cancel',{id:item.id},APPROVE_TIMEOUT);}catch(error){failure=error;}
  queueCancels.delete(item.id);
  if(answer?.cancelled===true){
    queueState={...queueState,queued:queueState.queued.filter(entry=>entry.id!==item.id).map(entry=>({...entry,position:Number(entry.position)>Number(item.position)?Number(entry.position)-1:entry.position}))};
    queueAnnounce(`${queueWord(item.action)} cancelled: ${item.title || queueTitle(row)}.`);
  }else if(failure?.httpStatus===409 && failure.body?.code==='started')queueLate.set(item.id,{book_id:row.id,text:`Too late to cancel: the ${word} has already started.`});
  // Focus goes to the row's restored Retry or Delete book button, else the Status filter (1.7); again after the list is
  // read, which rebuilds the row.
  const restore=()=>{if(answer?.cancelled!==true || !inRow)return;const target=action==='delete'?deleteButtons.get(row.id)?.button:(rowRetries.get(row.path)?.button || (selectedRow?.id===row.id?$('retry-job'):null));
    (target && !target.hidden && !target.disabled?target:$('filter')).focus?.({preventScroll:true});};
  controls();restore();
  if(!ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  controls();restore();
  return answer?.cancelled===true;
}
// The Cancel button of a queued action: a native button beside the face, never the same target (1.1).
function queueCancelButton(row,action){
  const button=node('button','Cancel '+lowerFirst(queueWord(action)),'quiet row-cancel');button.type='button';button.hidden=true;
  button.addEventListener('click',event=>{event?.stopPropagation?.();if(event?.repeat || button.hidden)return;const item=queuedFor(row);if(item){cancelQueued(row,item.action);return;}const key=retryKey(row);if(key && laterFor(key))cancelLater(key);});
  button.addEventListener('keydown',event=>event?.stopPropagation?.());
  return button;
}
function updateQueueCancel(button,row,kinds){
  if(!button)return;const item=queuedFor(row),shown=!!item && kinds.includes(item.action) && !queueLate.has(item.id);
  const lost=!shown && !button.hidden && document.activeElement===button;
  button.hidden=!shown;
  if(shown){
    const word=lowerFirst(queueWord(item.action)),label='Cancel '+word;
    if(button.textContent!==label)button.textContent=label;
    const tip=['delete','copy'].includes(item.action)?`Take this ${word} out of the queue. Nothing was deleted.`:`Take this ${word} out of the queue. Nothing was started.`;if(button.title!==tip)button.title=tip;
    button.setAttribute('aria-label',`${label}: ${item.title || queueTitle(row)}`);
    if(queueCancels.has(item.id))button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
  }
  // The action started or ended under focus: the row's next working control, else the Status filter (1.7).
  if(lost)(nextRowButton(button.parentElement,button) || $('filter')).focus?.({preventScroll:true});
}
// ---------------------------------------------------------------- Delete book and Remove this copy
// Ruling 23 (Sergei 2026-10-25): a book with missing parts or broken audio the app cannot repair is deleted from disk and
// from the app, so a reacquired copy is a new book; rulings 24 and 26: its other files, the app's working files for it and
// the folders left empty go too. Ruling 25: Remove this copy, for an exact copy of an audiobook already in Sorted. Judy's
// "Delete book - spec" and "Delete book update and Remove this copy - spec" (Docs/BooksArranger_AttentionTodo_UX_
// 2026-10-24.md). The server alone offers either (ask.delete on Missing files rows, attention.delete on Need to reacquire
// and Source audio needs replacement, ask.copy on a verified duplicate); the page never guesses. One dialog serves both: it
// always asks first; Cancel is the default and Enter in the dialog confirms nothing; "Nothing was deleted" is said only for
// a typed refusal issued before the first file.
const DELETE_CAUSE={in_use:'In use by another program.',denied:'Access denied.',unreachable:"Can't reach the drive.",other:"Couldn't delete it."};
const DELETE_REFUSAL={busy:'This book is being processed. Nothing was deleted.',changed:'This book changed, so nothing was deleted. Review its details and try again.',
  files_changed:"The folder doesn't match the list, so nothing was deleted. Press Delete book to see the current list.",refused:'Delete was not accepted. Nothing was deleted.'};
const DELETE_LOST='Connection interrupted, so the delete may have gone through. Check the list before trying again.';
const DELETE_UNKNOWN='Delete did not finish. Check the list before trying again.';
// {sorted} is the Sorted folder's own name (outputName()).
function sortedText(text){return String(text).replaceAll('{sorted}',outputName());}
const COPY_HINT='This recording is already in {sorted}. The audio files here are exact copies of the files it was arranged from.';
// The two modes' own strings (Judy's update spec 3.3 and 3.4); everything else in the dialog is shared.
function deleteText(mode){
  if(mode!=='copy')return {titles:{confirm:'Delete this book?',deleting:'Delete this book?',refused:"Can't delete this book",partial:'Not everything was deleted',unknown:'Delete may not have finished'},
    forget:sortedText("The app forgets this book. If you get it again, it's found as a new book. Nothing in {sorted} is touched."),
    confirm:n=>n===0?'Delete book':`Delete book and ${deleteCount(n)}`,  // Judy 0.22.1, 5.2
    tip:n=>n===0?'Remove this book from the app. No files are touched.':n===1?"Delete this book and its file. The app can't undo this.":`Delete this book and its ${n.toLocaleString()} files. The app can't undo this.`,
    partial:'The book stays listed. Press Delete book to try these again.',
    partialStrip:(k,n,f)=>`Deleted ${k.toLocaleString()} of ${n.toLocaleString()} files. The book stays listed with the ${f.toLocaleString()} that could not be deleted.`,
    lost:desktopMode()?NOT_CONFIRMED.delete:DELETE_LOST,unknown:DELETE_UNKNOWN,refusal:DELETE_REFUSAL,done:'deleted'};
  return {titles:{confirm:'Remove this copy?',deleting:'Remove this copy?',refused:"Can't remove this copy",partial:'Not everything was deleted',unknown:'Removal may not have finished'},
    forget:sortedText("The app forgets this copy. If the same files turn up again, they're found as a new book. Nothing in {sorted} is touched."),
    confirm:n=>n===1?'Remove this copy and 1 file':`Remove this copy and ${n.toLocaleString()} files`,
    tip:n=>sortedText(n===1?"Delete this copy's file. The audiobook in {sorted} stays. The app can't undo this.":`Delete this copy's ${n.toLocaleString()} files. The audiobook in {sorted} stays. The app can't undo this.`),
    partial:'The copy stays listed. The row offers to delete what is left.',
    partialStrip:(k,n,f)=>`Deleted ${k.toLocaleString()} of ${n.toLocaleString()} files. The copy stays listed with the ${f.toLocaleString()} that could not be deleted.`,
    lost:desktopMode()?NOT_CONFIRMED.copy:'Connection interrupted, so the removal may have gone through. Check the list before trying again.',unknown:'Removal did not finish. Check the list before trying again.',
    refusal:{...DELETE_REFUSAL,files_changed:"The folder doesn't match the list, so nothing was deleted. Press Remove this copy to see the current list.",refused:ASK_REFUSED.copy,
      sorted_missing:sortedText('The audiobook is not where the app put it in {sorted}. Nothing was deleted.'),sorted_changed:sortedText('The audiobook in {sorted} has changed since the app arranged it. Nothing was deleted.'),
      not_identical:'These files no longer match the ones the audiobook was arranged from. Nothing was deleted.'},done:'copy_removed'};
}
function deleteOffer(row){
  const ask=askOf(row);if(ask)return ask.delete && typeof ask.delete==='object'?ask.delete:null;
  const a=attentionOf(row);return a?.delete && typeof a.delete==='object' && row.creation?.job?.state==='Output needs attention'?a.delete:null;
}
// Remove this copy (ruling 25): only the server's typed proof offer; never with Delete book (a copy has no missing file).
function copyOffer(row){const ask=askOf(row);return ask?.copy && typeof ask.copy==='object' && ask.copy.kind==='verified_duplicate'?ask.copy:null;}
function deleteTip(offer,mode){return mode==='copy'?sortedText(ASK_TIPS.copy):Number(offer?.present)>0?ASK_TIPS.delete.files:ASK_TIPS.delete.none;}
function deleteRefusalText(refusal,mode='delete'){
  const code=refusal?.code,files=Array.isArray(refusal?.files)?refusal.files:[];
  if(code==='shared')return files.length===1?`"${files[0].path}" also belongs to "${files[0].other}". Nothing was deleted.`:`${files.length.toLocaleString()} of this book's files also belong to other books. Nothing was deleted.`;
  if(code==='sorted')return `A finished audiobook of this book is in ${outputName()}. Nothing was deleted.`;
  if(code==='offline')return `Can't reach ${typeof refusal.root==='string' && refusal.root?refusal.root:'the source drive'}. Nothing was deleted.`;
  // S6 (ruling 35's refusal texts): a cause with no line here is said in the engine's own words, never the bare refusal.
  return deleteText(mode).refusal[code] || (typeof refusal?.message==='string' && refusal.message.trim()) || ASK_REFUSED[mode==='copy'?'copy':'delete'];
}
// The row's own sentence, verbatim (Judy, section 4): a Missing files hint, or the first sentence of a Stopped hint; the
// copy's row hint (update spec 3.1).
function deleteReason(row,mode){
  if(mode==='copy')return sortedText(COPY_HINT);
  const text=askText(row)?.hint || attentionText(row)?.hint || '';return String(text).replace(/ Delete the book, then get a new copy\.$/,'');
}
function buildDeleteButton(row,buttons,mode='delete'){
  // Last in the row, after View metadata and the folder buttons, on a line of its own (Judy, section 3; update spec 3.2).
  const gap=node('span','','row-break');gap.setAttribute('aria-hidden','true');
  const button=node('button',ASK_LABELS[mode],'quiet row-retry danger');button.type='button';
  button.setAttribute('aria-label',ASK_LABELS[mode]+': '+(row.title_clue || row.review?.title || 'Book'));
  button.addEventListener('click',event=>{event?.stopPropagation?.();if(event?.repeat || button.getAttribute?.('aria-disabled')==='true' || button.disabled)return;deletePress(row.id);});
  button.addEventListener('keydown',event=>{event?.stopPropagation?.();if(event?.repeat)event.preventDefault?.();});  // a held Enter opens it once
  const cancel=mode==='delete'?queueCancelButton(row,'delete'):null;  // Cancel delete beside a queued face (Judy 1.3)
  buttons.append(gap,button,...(cancel?[cancel]:[]));deleteButtons.set(row.id,{row,button,gap,mode,cancel});updateDeleteButton(row.id);
}
function deleteMode(row,kind='delete'){
  if(ended || recoveryDisconnected && !desktopMode())return 'offline';
  if(deleteNotes.get(row.id)?.done || ['approve','convert','deleted','copy_removed'].includes(askDone.get(row.id)))return 'done';
  if(deletePending?.id===row.id)return 'pending';
  if(queueRunning(row,kind))return 'running';
  if(queuedFor(row,kind))return 'queued';
  // One dialog at a time: a press while another book's files are being checked opens its dialog right after (ruling 35).
  if(deleteNext===row.id)return 'next';
  if(deletePending || deleteDialog)return 'ready';
  if(queuedFor(row))return 'sibling';  // a Retry or Repair queued on this row: one queued action per row (N1)
  // Ruling 35: nothing else holds it; the confirm queues the delete behind what is happening (Judy 1.5).
  return pageBlocker() || queueRunning(row) || queuePresses.has(row.id)?'blocked':'ready';
}
function updateDeleteButton(id){
  const entry=deleteButtons.get(id);if(!entry)return;const {row,button,gap,mode}=entry,offer=mode==='copy'?copyOffer(row):deleteOffer(row),state=deleteMode(row,mode);
  const hidden=state==='done' || !offer && !['queued','running'].includes(state);
  const lost=hidden && !button.hidden && document.activeElement===button;button.hidden=hidden;gap.hidden=hidden;
  updateQueueCancel(entry.cancel,row,['delete','copy']);
  if(lost)(nextRowButton(button.parentElement,button) || $('filter')).focus?.({preventScroll:true});
  if(hidden)return;
  const item=queuedFor(row,mode),blocker=state==='blocked'?pageBlocker() || 'operation':null,word=mode==='copy'?'Remove this copy':'Delete';
  const label=state==='pending'?ASK_PENDING[mode][0]:state==='queued'?`${word} queued`:state==='running'?'Deleting…':state==='next'?ASK_PENDING[mode][0]:ASK_LABELS[mode];
  const title={offline:'Local server unavailable.',next:"Checking another book's files. This book's opens right after.",pending:sortedText(ASK_PENDING[mode][1]),ready:deleteTip(offer,mode),
    queued:`${word} is queued. Nothing is deleted until it runs, when ${queueP(queueBlocker(item))} finishes.`,running:"Deleting can't be stopped.",
    blocked:mode==='copy'?`Remove this copy. ${queueS(blocker)}, so the removal is queued after you confirm.`:`Delete this book. ${queueS(blocker)}, so the delete is queued after you confirm.`,
    sibling:queuedFor(row)?.action==='repair'?QUEUE_SIBLING_REPAIR:QUEUE_SIBLING_RETRY}[state];
  if(button.textContent!==label)button.textContent=label;if(button.title!==title)button.title=title;
  button.setAttribute('aria-label',(state==='queued'?'Delete queued':state==='running'?'Deleting':ASK_LABELS[mode])+': '+queueTitle(row));
  if(state==='ready' || state==='blocked')button.removeAttribute('aria-disabled');else button.setAttribute('aria-disabled','true');
}
function updateDeleteButtons(){for(const id of deleteButtons.keys())updateDeleteButton(id);}
async function deletePress(id){
  const entry=deleteButtons.get(id);if(!entry || !['ready','blocked'].includes(deleteMode(entry.row,entry.mode)))return;
  if(deletePending || deleteDialog){deleteNext=id;controls();return;}  // ruling 35: never dropped; it opens after the current one
  const row=entry.row,mode=entry.mode;deletePending={id};deleteNotes.delete(id);askResults.delete(id);dropQueueNote(id);controls();
  let preview=null;
  // Delete book asks with queue: true, so a blocker comes back as 'blocked' with the list, not as a busy refusal (Judy 1.5).
  // Remove this copy proves the copy and the audiobook now (both hashed in full): it waits as long as Approve (N19).
  try{preview=await request('/api/candidate/delete-preview',{library:'Audiobooks',id,revision:row.revision,...(mode==='copy'?{mode:'copy'}:{queue:true})},mode==='copy'?APPROVE_TIMEOUT:PRESS_TIMEOUT);}
  catch(error){deleteNotes.set(id,{text:error.httpStatus?serverSentence(error,ASK_REFUSED[mode]).replace(/Nothing was changed\.$/,'Nothing was deleted.'):lostLine(),warn:true});if(!error.httpStatus)refreshFailed(error);}
  finally{deletePending=null;}
  if(preview)openDeleteDialog(row,preview,mode);
  controls();
  if(!deleteDialog)deleteNextPress();
}
function deleteCount(n){return n===1?'1 file':n.toLocaleString()+' files';}
function deleteLines(list,lines){$('delete-dialog-list').replaceChildren(...lines);$('delete-dialog-list').hidden=!lines.length;}
// The list (update spec 2.2): audio, other files, working files, then folders, each under its subhead and sorted by path;
// with audio files only it is exactly as before (no subheads).
function deleteListing(d){
  const kindOf=file=>['audio','other','working'].includes(file.kind)?file.kind:'audio';
  const plain=d.files.every(file=>kindOf(file)==='audio') && !d.folders.length,lines=[];
  if(plain)lines.push(...d.paths.map(path=>node('p',path)));
  else{
    for(const [kind,label] of [['audio','Audio files'],['other',"Other files in this book's folder"],['working',"The app's working files"]]){
      const paths=d.files.filter(file=>kindOf(file)===kind).map(file=>file.path).sort();
      if(paths.length)lines.push(node('p',`${label} (${paths.length.toLocaleString()})`,'delete-group'),...paths.map(path=>node('p',path)));
    }
    if(d.folders.length)lines.push(node('p',`Folders left empty are removed (${d.folders.length.toLocaleString()})`,'delete-group'),...[...d.folders].sort().map(path=>node('p',path)));
  }
  $('delete-dialog-list').setAttribute('aria-label',d.folders.length?'Files and folders to delete':'Files to delete');
  deleteLines(null,lines);
}
function showDeleteState(kind,data={}){
  const d=deleteDialog;if(!d)return;d.state=kind;const n=d.n,row=d.row,t=deleteText(d.mode);
  const ask=askOf(row),book=row.review?.title || (ask?askProposal(ask,'title'):'') || row.title_clue || '',author=row.review?.canonical_author || (ask?askProposal(ask,'author'):'') || (row.artists || [])[0] || '';
  setText('delete-dialog-title',t.titles[kind]);
  const confirm=$('delete-confirm'),cancel=$('delete-cancel'),close=$('delete-close');
  const asking=kind==='confirm' || kind==='deleting' || kind==='queuing';
  for(const id of ['delete-dialog-book','delete-dialog-reason','delete-dialog-forget'])$(id).hidden=!asking;
  // The Sorted block only beside a proof made in this preview; the last-copy line only for Delete book; the stay line when k > 0.
  $('delete-dialog-sorted').hidden=!asking || !d.sorted;$('delete-dialog-last').hidden=!asking || !d.last;$('delete-dialog-folder').hidden=!asking || !d.stay;
  confirm.hidden=!asking;cancel.hidden=!asking;close.hidden=asking;
  // The blocked variant (Judy 1.5): what it waits for, "when it runs", and the re-check line; no new control.
  const blocked=asking && d.blocked?d.blocked:null;$('delete-dialog-blocked').hidden=!blocked;$('delete-dialog-recheck').hidden=!blocked;
  if(asking){
    setText('delete-dialog-book',author?`${book} — ${author}`:book);setText('delete-dialog-reason',deleteReason(row,d.mode));
    if(d.sorted){
      const at=new Date(d.sorted.verified_at),clock=askClock(Number.isNaN(at.getTime())?new Date():at);
      setText('delete-dialog-sorted-title',`Stays in ${outputName()}`);setText('delete-dialog-sorted-path',d.sorted.path);
      setText('delete-dialog-sorted-facts',`${sizeText(Number(d.sorted.size) || 0)}. Verified ${clock}: the file is there and unchanged since the app arranged it.`);
    }
    setText('delete-dialog-last',d.last==='all'?"The originals are already gone. The app's working files are the last copy of this book's audio.":"Some originals are already gone. The app's working files hold the last copy of that audio.");
    const when=blocked?' when it runs':'';
    setText('delete-dialog-files',n===0?'No files will be deleted from your disk.':n===1?`This file (${sizeText(d.bytes)}) will be deleted from your disk${when}. The app can't undo this.`:`These ${n.toLocaleString()} files (${sizeText(d.bytes)}) will be deleted from your disk${when}. The app can't undo this.`);
    if(blocked){setText('delete-dialog-blocked',`${queueS(blocked)}, so this delete waits its turn.`);setText('delete-dialog-recheck',n===0?'The app checks this book again first. If it differs, nothing is deleted.':'The app checks this book and these files again first. If anything differs, nothing is deleted.');}
    setText('delete-dialog-folder',d.stay===1?"1 other item stays where it is. It belongs to another book, or the app can't tell whose it is.":`${d.stay.toLocaleString()} other items stay where they are. They belong to other books, or the app can't tell whose they are.`);
    setText('delete-dialog-forget',t.forget);
    deleteListing(d);
    setText('delete-confirm',kind==='deleting'?'Deleting...':kind==='queuing'?'Queuing…':blocked?(n===0?'Queue delete':`Queue delete of ${deleteCount(n)}`):t.confirm(n));
    confirm.title=blocked?(n===0?'Queue removing this book from the app. No files are touched.':`Queue this delete. It runs when ${queueP(blocked)} finishes, after the app checks the book and files again. The app can't undo it.`):t.tip(n);
    if((kind==='deleting' || kind==='queuing') && !Number.isFinite(d.at))d.at=Date.now();
    deleteStatusLine();
    if(kind==='deleting'){confirm.setAttribute('aria-disabled','true');cancel.setAttribute('aria-disabled','true');cancel.title="Deleting can't be stopped.";}
    else if(kind==='queuing'){confirm.setAttribute('aria-disabled','true');cancel.setAttribute('aria-disabled','true');cancel.title="Queuing can't be stopped.";}
    else{confirm.removeAttribute('aria-disabled');cancel.removeAttribute('aria-disabled');cancel.title='Close without deleting anything.';}
    return;
  }
  setText('delete-dialog-status','');$('delete-dialog-list').setAttribute('aria-label','Files to delete');$('delete-dialog-blocked').hidden=true;$('delete-dialog-recheck').hidden=true;
  if(kind==='refused'){
    setText('delete-dialog-files',data.line || ASK_REFUSED[d.mode]);
    const shared=Array.isArray(data.files) && data.files.length>1?data.files:[];
    deleteLines(shared,shared.flatMap(file=>[node('p',file.path),node('p',`Also in "${file.other}"`,'delete-cause')]));
  }else if(kind==='partial'){
    const failed=data.failed || [],k=Number(data.deleted) || 0;
    setText('delete-dialog-files',`Deleted ${k.toLocaleString()} of ${n.toLocaleString()} files. ${failed.length.toLocaleString()} could not be deleted:`);
    deleteLines(failed,failed.flatMap(item=>[node('p',String(item.path || '')),node('p',DELETE_CAUSE[item.cause] || DELETE_CAUSE.other,'delete-cause')]));
    setText('delete-dialog-status',t.partial);
  }else{setText('delete-dialog-files',data.line || t.unknown);deleteLines([],[]);}
}
// The Deleting and Queuing status lines, with the ladder of 4.3 (4.4).
function deleteStatusLine(now=Date.now()){
  const d=deleteDialog;if(!d)return;const n=d.n;
  const base=d.state==='deleting'?(n===0?'Removing this book...':n===1?'Deleting 1 file...':`Deleting ${n.toLocaleString()} files...`):d.state==='queuing'?'Queuing this delete…':'';
  setText('delete-dialog-status',base?ladderNote(base,d.at,now):'');
}
function openDeleteDialog(row,preview,mode='delete'){
  const files=Array.isArray(preview?.files)?preview.files.filter(file=>typeof file?.path==='string'):[];
  const folders=Array.isArray(preview?.folders)?preview.folders.filter(folder=>typeof folder==='string'):[];
  const sorted=preview?.sorted && typeof preview.sorted==='object' && typeof preview.sorted.path==='string'?preview.sorted:null;
  deleteDialog={id:row.id,row,mode,files,paths:files.map(file=>file.path),folders,n:files.length,bytes:Number(preview?.bytes) || 0,
    last:mode==='delete' && ['all','some'].includes(preview?.last_copy)?preview.last_copy:null,stay:Math.max(0,Math.floor(Number(preview?.stay?.items) || 0)),sorted,state:'confirm',
    blocked:mode==='delete' && typeof preview?.blocked?.kind==='string'?preview.blocked.kind:null};  // what a queued delete waits for (Judy 1.5)
  // Remove this copy is offered only beside a proof made now: without one the dialog opens refused, never confirmable.
  const refusal=preview?.refusal || (mode==='copy' && !sorted?{code:'refused'}:null);
  if(refusal){const line=deleteRefusalText(refusal,mode);showDeleteState('refused',{line,files:refusal.files});deleteNotes.set(row.id,{text:line,warn:true});}
  else showDeleteState('confirm');
  $('delete-dialog').showModal?.();
  (refusal?$('delete-close'):$('delete-cancel')).focus?.();  // Cancel has focus: the Enter that opened it confirms nothing
}
function closeDeleteDialog(returnFocus=true){
  if(!deleteDialog)return;const id=deleteDialog.id;deleteDialog=null;$('delete-dialog').close?.();controls();
  if(deleteNext){deleteNextPress();return;}
  if(!returnFocus)return;
  const button=deleteButtons.get(id)?.button;
  if(button && !button.hidden)button.focus?.({preventScroll:true});else $('filter').focus?.({preventScroll:true});
}
// The success strip (update spec 2.3 and 3.4): files, then folders removed, then folders that stayed.
function deleteStrip(mode,k,bytes,folders){
  const size=sizeText(bytes),m=Math.max(0,Number(folders?.removed) || 0),s=Math.max(0,Number(folders?.stayed) || 0);
  const what=mode==='copy'?'Removed 1 copy':'Deleted 1 book',files=k===1?`1 file (${size})`:`${k.toLocaleString()} files (${size})`;
  let line=m?`${what}, ${files} and ${m===1?'1 folder':m.toLocaleString()+' folders'}.`:mode!=='copy' && k===0?'Deleted 1 book. No files were left on disk.':`${what} and ${files}.`;
  if(s)line+=s===1?' 1 folder stayed.':` ${s.toLocaleString()} folders stayed.`;
  return line;
}
async function deleteConfirm(event){
  const d=deleteDialog;
  if(event?.repeat || !d || d.state!=='confirm' || $('delete-confirm').getAttribute?.('aria-disabled')==='true')return;
  const t=deleteText(d.mode);
  showDeleteState(d.blocked?'queuing':'deleting');controls();
  let result=null;
  // Delete book confirms with queue: true: the answer decides (Judy 1.5), the result if it ran, or "queued".
  // Ruling 35: Remove this copy confirms with queue: true too.
  try{result=await request('/api/candidate/delete',{library:'Audiobooks',id:d.id,revision:d.row.revision,paths:d.paths,folders:d.folders,...(d.mode==='copy'?{mode:'copy'}:{}),queue:true,title:queueTitle(d.row)},APPROVE_TIMEOUT);}
  catch(error){
    if(error.httpStatus===409 && typeof error.body?.code==='string'){const line=deleteRefusalText(error.body,d.mode);showDeleteState('refused',{line,files:error.body.files});deleteNotes.set(d.id,{text:line,warn:true});}
    else{const line=error.httpStatus?t.unknown:t.lost;showDeleteState('unknown',{line});deleteNotes.set(d.id,{text:line,warn:true});if(!error.httpStatus)refreshFailed(error);}
    $('delete-close').focus?.();controls();return;
  }
  if(result?.queued===true){
    // Queued: the dialog closes, focus goes to the row's "Delete queued" face, the announcer says so (Judy 1.5).
    const row=d.row;closeDeleteDialog(false);queueAccepted(row,d.mode==='copy'?'copy':'delete',{...result,n:d.n});controls();
    const face=()=>{const button=deleteButtons.get(row.id)?.button;(button && !button.hidden?button:$('filter')).focus?.({preventScroll:true});};
    face();const handed=document.activeElement;
    // The list is read again, which rebuilds the row: focus follows the queued face unless it has moved meanwhile.
    if(!ended){lastKey=null;await refresh(true).catch(()=>{});if(document.activeElement===handed || !document.activeElement || document.activeElement===document.body)face();}
    return;
  }
  const failed=Array.isArray(result?.failed)?result.failed:[],k=Number(result?.deleted) || 0;
  if(result?.forgotten===true && !failed.length){
    deleteNotes.set(d.id,{text:ASK_DONE[t.done][1],warn:false,done:true});if(askRows.has(d.id))askDone.set(d.id,t.done);
    closeDeleteDialog(false);
    askNote(deleteStrip(d.mode,k,Number(result.bytes) || 0,result.folders));
    // Futaba's 0.22.0 QA, m-10: the forced re-read (the row leaves at the answer) replaces every row, the control askLeave
    // had just focused too, so focus fell to the page. After it, the next row is found again (else the Status filter),
    // unless focus has moved meanwhile.
    const index=rows.findIndex(item=>item.id===d.id),next=rows.slice(index+1).find(item=>item.id!==d.id && !askDone.has(item.id))?.id;
    askLeave({row:d.row});controls();const handed=document.activeElement;
    // 0.22.1 (m-10 on Stopped rows, about one press in three): a later re-render, after this hand-off, replaced the focused
    // button again. For a few seconds every rebuild of the list that drops focus hands it on once more (renderRows).
    focusPlan={next,until:Date.now()+5000};
    // Judy 0.22.2 section 5 (Sigma Force 9): the row leaves in this render, with its counts, and no list read before the
    // answer can bring it back.
    forgetDeleted(d.row);
    refresh(true).catch(()=>{}).then(()=>{if(document.activeElement===handed || !document.activeElement || document.activeElement===document.body)leaveTo(next);});return;
  }
  if(failed.length){
    const f=failed.length;showDeleteState('partial',{deleted:k,failed});
    deleteNotes.set(d.id,{text:`Deleted ${k.toLocaleString()} of ${d.n.toLocaleString()} files. ${f===1?'1 is':f.toLocaleString()} still on disk.`,warn:true});
    askNote(t.partialStrip(k,d.n,f));
  }else{showDeleteState('unknown',{line:t.unknown});deleteNotes.set(d.id,{text:t.unknown,warn:true});}
  $('delete-close').focus?.();controls();
}
// Judy 0.22.2 section 5 (Sergei 2026-10-26, Sigma Force 9 "All files missing"): after "Deleted. The book is gone from the
// app." the row was still listed. A list or status answer computed before the delete (a poll already on its way, the
// engine's shared answer) repainted it with its settled line, and the rebuild kept the row while it held focus. The
// deleted book leaves the rows and its chip's count at once, and every list or status answer sent before the delete is
// kept from bringing it back; a list answer sent after it, and without it, ends the guard.
const deletedBooks=new Map();  // id -> {at, chip}
function chipOf(row){const ask=askOf(row);if(ask)return NEEDS_KEYS.includes(ask.kind)?ask.kind:'other';return attentionOf(row)?.group || null;}
function forgetDeleted(row){
  if(!row?.id)return;
  const chip=chipOf(row);deletedBooks.set(row.id,{at:Date.now(),chip});
  const before=rows.length;rows=rows.filter(item=>item.id!==row.id);if(rows.length<before)totalRows=Math.max(0,totalRows-1);
  const counts=state?.audiobook_jobs?.attention_counts;if(counts && chip && Number.isInteger(counts[chip]) && counts[chip]>0)counts[chip]--;
  askRows.delete(row.id);askDone.delete(row.id);deleteButtons.delete(row.id);
  if(selectedPath===row.path){selectedPath=null;selectedRow=null;}
  renderRows(true);renderAttentionGroups();if(partReady('jobs'))renderJobs();
}
// A list answer: rows of deleted books leave it; sentAt is when its request was sent.
function withoutDeleted(list,sentAt){
  let kept=list;
  for(const [id,entry] of deletedBooks){
    if(kept.some(item=>item.id===id)){kept=kept.filter(item=>item.id!==id);totalRows=Math.max(0,totalRows-1);}
    else if(sentAt>=entry.at)deletedBooks.delete(id);
  }
  return kept;
}
// A status answer sent before a delete still counts the deleted book in its chip.
function deletedCounts(value,sentAt){
  const counts=value?.audiobook_jobs?.attention_counts;if(!counts)return;
  for(const entry of deletedBooks.values())if(sentAt<entry.at && entry.chip && Number.isInteger(counts[entry.chip]) && counts[entry.chip]>0)counts[entry.chip]--;
}
$('delete-confirm').addEventListener('click',deleteConfirm);
$('delete-cancel').addEventListener('click',event=>{if(event?.repeat || deleteDialog?.state==='deleting')return;closeDeleteDialog();});
$('delete-close').addEventListener('click',event=>{if(event?.repeat)return;closeDeleteDialog();});
$('delete-dialog').addEventListener('cancel',event=>{event?.preventDefault?.();if(deleteDialog?.state==='deleting')return;closeDeleteDialog();});
// No form and no default button: Enter in the body or the file list does nothing; only a focused button acts on it.
$('delete-dialog').addEventListener('keydown',event=>{if(event?.key==='Enter' && !['delete-cancel','delete-close','delete-confirm'].includes(event.target?.id))event.preventDefault?.();});
// Change order / Choose files (0.22.0 review B4): select the row, open Manual review and move focus to its included-files
// heading, where Include, Move up / Move down and Save track review already are. Approve then uses what he saved.
function openTrackReview(entry){
  const row=entry.row;select(row,selectedPath!==row.path);
  if($('manual-review'))$('manual-review').open=true;
  const heading=$('member-count');heading?.scrollIntoView?.({block:'start',behavior:'auto'});heading?.focus?.({preventScroll:true});
}
// The queue action each row button sends (ruling 35: every press is accepted, queued when something else is happening).
const ASK_QUEUE={approve:'approve',convert:'convert',separate:'separate',scan:'scan_again',remove:'dismiss'};
const ASK_QUEUE_ACTIONS=Object.values(ASK_QUEUE);
// A press's outcome on its row, whether it ran in its own request or later from the queue (outcome.answer).
function askSettled(entry,kind,result,values){
  const row=entry?.row,id=row?.id ?? entry?.id,ask=row?askOf(row):null;
  if(kind==='approve' || kind==='convert'){
    if(result?.saved===true && result?.code==='series_needed'){askResults.set(id,{text:result.message,warn:false,code:result.code});queueAnnounce(`${row?askName(row):entry?.title || 'Book'}: ${result.message}`);return;}
    askDone.set(id,kind);askDrafts.delete(id);selectedBooks.delete(id);namesDropped(id);
    const settled=Math.max(1,Number(ask?.same_author?.count) || 1);
    askNote(values?.choice?`Remembered. ${plural(settled,'book continues','books continue')}.`:kind==='convert'?'Approved 1 book without its missing files. Track it under Queued / creating.':'Approved 1 book. Track it under Queued / creating.');
    if(row)watchLeaving(row,`Approved ${askName(row)}.`,result);
    return;
  }
  if(kind==='separate'){
    const kept=Number(result?.kept) || (row?.members || []).length;
    askDone.set(id,'separate');askDrafts.delete(id);selectedBooks.delete(id);
    askNote(`Kept as ${kept.toLocaleString()} separate books. Each is checked again.`);return;
  }
  if(kind==='scan' && ask && holdKind(ask)){
    // A hold row: "Checked 14:32. No change." on the row, or the book leaves and is checked again (B4).
    if(result?.changed===true){const later=result.scan_later===true;askDone.set(id,later?'later':'changed');askNote(ASK_DONE[later?'later':'changed'][1]);}
    else if(result?.found===true)askChecked.set(id,askClock(new Date()));
    else askResults.set(id,{text:ASK_REFUSED.scan});
    return;
  }
  // A missing part (QA M-2): a new file beside the book is "changed" (its folder's source is scanned), never "found".
  if(kind==='scan' && result?.found!==true && result?.changed===true){const later=result.scan_later===true;askDone.set(id,later?'later':'changed');askNote(ASK_DONE[later?'later':'changed'][1]);return;}
  if(kind==='scan' && result?.found!==true){askChecked.set(id,askClock(new Date()));return;}
  askDone.set(id,kind==='scan'?'found':'removed');askNote(kind==='scan'?'Files found. The book is checked again.':'Removed 1 book from the list. No files were touched.');
}
async function askPress(entry,kind){
  const row=entry.row,id=row.id,button=(entry.buttons || []).find(item=>item.kind===kind)?.button;
  if(!button || button.disabled || button.getAttribute?.('aria-disabled')==='true' || askDone.has(id))return;
  if(kind==='order' || kind==='choose')return openTrackReview(entry);
  if(askPendings.has(id))return;  // this row's press is on its way; another row's never holds this one (ruling 35)
  const values=kind==='approve' || kind==='convert'?askValues(row):null;
  // Futaba's 0.22.0 QA, m-11: a Delete book note (a partial delete) took the hint over, so a later Scan again showed no
  // result line. A new press on the row replaces it, as it does an earlier refusal.
  askPendings.set(id,{id,kind,at:Date.now()});askResults.delete(id);deleteNotes.delete(id);dropQueueNote(id);controls();
  try{
    let result;
    if(values){
      // The "Goes to" line shown travels with the press: a different destination now is refused (Senua's 0.22.0 review, m1).
      // Ruling 35: always accepted and queued with his values; the row shows it running and its outcome.
      const shown=askDestination(row)?.path,names=namesFor(row);
      result=await request('/api/candidate/approve',{library:'Audiobooks',id,revision:row.revision,...values,...(kind==='convert'?{without_missing:true}:{}),...(shown?{path:shown}:{}),
        ...(names?{names}:{}),queue:true,label:askName(row)},APPROVE_TIMEOUT);
    }else{
      const route=kind==='separate'?'/api/candidate/keep-separate':kind==='scan'?'/api/candidate/scan-again':'/api/candidate/dismiss';
      result=await request(route,{library:'Audiobooks',id,revision:row.revision,queue:true,title:askName(row)},kind==='scan'?120000:PRESS_TIMEOUT);
    }
    if(result?.queued===true)queueAccepted(row,ASK_QUEUE[kind],result);
    else askSettled(entry,kind,result,values);
  }catch(error){
    askResults.set(id,{text:askErrorText(error,kind),code:error.body?.code || ''});
    // A gate refused it (for example Name taken, or the destination moved): the row shows the current Goes to line, with
    // his typed values kept.
    if(['name_taken','changed','moved'].includes(error.body?.code)){askDraft(id).previewKey=null;askPreview(entry,0);}
    if(!error.httpStatus)refreshFailed(error);
  }finally{askPendings.delete(id);}
  // Read before the buttons update: a focused button that becomes disabled drops focus to the page.
  const inRow=!!entry.cell.parentElement?.contains?.(document.activeElement);
  batchCounts();
  if(askDone.has(id) && inRow)askLeave(entry);
}
// Bulk "Approve as is (N)" (section 5): only in Title or author and Author unclear, selected rows only, never a row with
// typed text, an inert Approve, a reader as the author (ruling 14) or an odd-name question (0.22.1: each is approved on
// its own row, so a bad name is never filed unseen), always confirmed in a dialog.
function bulkChip(){return attentionSelection() && (attentionGroup==='title_author' || attentionGroup==='author_unclear');}
function stillChecking(){const n=state?.audiobook_jobs?.todo_still_checking;return Number.isInteger(n) && n>0?n:0;}
// Every "Needs your answer" chip: Retry selected hides there (0.22.0 review B3); bulk Approve stays only in bulkChip().
function needsChip(){return attentionSelection() && NEEDS_KEYS.includes(attentionGroup);}
// An odd-name question (the engine's odd_name flag: a bitrate, series or Latin letters in the title, underscores or two
// people in the author). Never in Select all or bulk Approve as is (Judy 11.4, item 2; Jane for Sergei 2026-10-26).
function oddName(row){return askOf(row)?.odd_name===true;}
// What Select all takes: every candidate row but an odd-name question.
function pageSelectable(){return rows.filter(row=>row.kind==='candidate' && !oddName(row));}
function readerRisk(row){const ask=askOf(row),author=askProposal(ask,'author');return ask.kind==='author_unclear' && (!author || ask.why==='reader' || (ask.candidates || []).some(c=>c?.name===author && c.reader_count>0));}
function approveSelectable(){
  if(!bulkChip())return {items:[],selected:0};
  const selected=rows.filter(row=>row.kind==='candidate' && selectedBooks.has(row.id));
  const items=selected.filter(row=>{const ask=askOf(row);return ask && ask.kind===attentionGroup && !oddName(row) && !askDone.has(row.id) && !askPendings.has(row.id) && !namesOpen(row.id) && !deleteQueued(row) && !askInert(row) && !Object.keys(askValues(row)).length && !(inlineNames(row) && ['series','number'].some(field=>typeof askDrafts.get(row.id)?.[field]==='string')) && !readerRisk(row) && !!askDestination(row)?.path;});
  return {items,selected:selected.length};
}
function renderApproveSelected(){
  const button=$('approve-selected');if(!button)return;const shown=bulkChip();button.hidden=!shown;if(!shown)return;
  const count=approveSelectable().items.length,label=`Approve as is (${count.toLocaleString()})`;if(button.textContent!==label)button.textContent=label;
  button.title=count?'Approve the selected books with the names shown. Each is converted if needed, renamed and moved to Audiobooks Sorted.':'Select books that can be approved as is.';
  button.disabled=!count || ended || recoveryDisconnected || askBulk || !!approveConfirm;  // ruling 35: other presses never hold it
}
function openApproveDialog(){
  const {items,selected}=approveSelectable();if(!items.length || approveConfirm)return;
  approveConfirm={items,paths:new Map(items.map(row=>[row.id,askDestination(row)?.path]))};const n=items.length,left=selected-n;
  setText('approve-dialog-title',`Approve ${plural(n,'book','books')} as is?`);
  $('approve-dialog-list').replaceChildren(...items.map(row=>{const dest=askDestination(row),line=node('p',outputName()+'\\'+dest.path);line.title=dest.absolute || '';return line;}));
  setText('approve-dialog-left',left>0?`${plural(left,'selected book is','selected books are')} left out. ${left===1?'It needs':'They need'} a different action.`:'');$('approve-dialog-left').hidden=!(left>0);
  setText('approve-confirm',`Approve ${plural(n,'book','books')}`);$('approve-confirm').title=`Approve these ${plural(n,'book','books')}.`;$('approve-confirm').removeAttribute('aria-disabled');
  $('approve-dialog').showModal?.();$('approve-cancel').focus?.();controls();
}
function closeApproveDialog(){if(!approveConfirm)return;approveConfirm=null;$('approve-dialog').close?.();controls();$('approve-selected').focus?.({preventScroll:true});}
async function runApproveSelected(){
  const confirm=approveConfirm,button=$('approve-confirm');if(!confirm || button.getAttribute?.('aria-disabled')==='true' || askBulk)return;
  button.setAttribute('aria-disabled','true');approveConfirm=null;$('approve-dialog').close?.();
  const items=confirm.items,n=items.length;let approved=0,queued=0;askBulk=true;askNote(`Approving ${plural(n,'book','books')}.`);controls();
  for(const row of items){
    if(ended || recoveryDisconnected)break;
    askPendings.set(row.id,{id:row.id,kind:'approve',at:Date.now()});updateAskRows();
    const shown=confirm.paths?.get(row.id);  // the path the dialog listed (m1)
    // Ruling 35: each Approve is accepted and queued at once; its checks run in the engine's queue, one book at a time.
    try{const answer=await request('/api/candidate/approve',{library:'Audiobooks',id:row.id,revision:row.revision,...(shown?{path:shown}:{}),queue:true,label:askName(row)},APPROVE_TIMEOUT);
      if(answer?.queued===true){queueAccepted(row,'approve',answer);selectedBooks.delete(row.id);queued++;}else{askDone.set(row.id,'approve');askDrafts.delete(row.id);selectedBooks.delete(row.id);approved++;}}
    catch(error){askResults.set(row.id,{text:askErrorText(error,'approve')});const entry=askRows.get(row.id);if(['name_taken','changed','moved'].includes(error.body?.code) && entry){askDraft(row.id).previewKey=null;askPreview(entry,0);}if(!error.httpStatus)refreshFailed(error);}
    finally{askPendings.delete(row.id);}
  }
  askBulk=false;
  // Provisional copy for the queued count (ruling 35, sent to Judy).
  askNote(queued===n?`Queued ${plural(n,'book','books')} for approval. Each is checked, then converted. Each row shows its outcome.`:
    approved+queued===n?`Approved ${plural(n,'book','books')}. Track ${n===1?'it':'them'} under Queued / creating.`:`Approved ${(approved+queued).toLocaleString()} of ${n.toLocaleString()}. ${(n-approved-queued).toLocaleString()} ${n-approved-queued===1?'stays listed with its reason':'stay listed with their reasons'}.`);
  batchCounts();$('group-'+attentionGroup).focus?.({preventScroll:true});
}
$('approve-selected').addEventListener('click',()=>{if($('approve-selected').disabled)return;openApproveDialog();});
$('approve-cancel').addEventListener('click',()=>closeApproveDialog());
$('approve-confirm').addEventListener('click',()=>runApproveSelected());
$('approve-dialog').addEventListener('cancel',event=>{event.preventDefault?.();closeApproveDialog();});
// "Needs attention · N" beside "Read errors · N" (section 8): N is the All total; one click opens the list on All.
function renderAttentionShortcut(){
  const button=$('attention-shortcut');if(!button)return;const total=attentionTotal(state?.audiobook_jobs);
  button.hidden=$('library').value!=='Audiobooks' || !state?.audiobook_jobs || total<=0;
  const text=`Needs attention · ${total.toLocaleString()}`;if(button.textContent!==text)button.textContent=text;
}
$('attention-shortcut').addEventListener('click',()=>{
  $('search').value='';view='candidates';filters.candidates='output_attention';attentionGroup='all';resetStrip();restartCounts=null;viewControls();
  const done=updateList();$('group-all').focus?.({preventScroll:true});return done;
});
$('copy-technical').addEventListener('click',async()=>{
  const text=$('automatic-technical').textContent || '';
  try{const clipboard=globalThis.navigator?.clipboard;if(!clipboard?.writeText)throw Error('no clipboard');await clipboard.writeText(text);setText('copy-technical-status','Copied.');}
  catch(error){setText('copy-technical-status',"Couldn't copy. Select the text and press Ctrl+C.");}  // 0.22.0 review A1d
});

controls();
viewControls();
if(LS){
  // The strip from the first frame: Step 1 and its clocks from the shell's launch time, ticking once a second.
  shellApi?.startup?.().then(applyStartup).catch(()=>{});shellApi?.onStartup?.(applyStartup);
  if(typeof setInterval==='function')setInterval(loadTick,1000);
  renderLoad();loadPlaceholders();
}
if(typeof setInterval==='function')setInterval(pressTick,1000);  // the busy notice and the press ladder (Judy 0.22.1, section 4)
// 0.22.3 (Judy): Edit names in the book panel, Show it on the strip, the learned author rules.
$('names-facts-edit')?.addEventListener('click',event=>{event?.stopPropagation?.();if($('names-facts-edit').getAttribute('aria-disabled')==='true')return;panelEditNames();});
$('strip-show')?.addEventListener('click',()=>showLeaver());
$('author-rules-find')?.addEventListener('input',()=>{rulesView.find=$('author-rules-find').value || '';renderAuthorRules();});
$('author-rules')?.addEventListener('toggle',()=>{if($('author-rules').open)loadAuthorRules();});
if(typeof setTimeout==='function' && !preEngine)setTimeout(loadAuthorRules,0);  // after the screen (ruling 28); the first frame from disk has no engine
if(!preEngine)poll();  // the first frame from disk has no engine to ask; the shell swaps in the engine's page

'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="books-token"]').content;
let offset = 0, search = '', selectedPath = null, selectedRow = null, reviewRow = null, rows = [], lastKey = null;
let dirty = false, busy = false, polling = false, ended = false, timer = null, state = null;
let view='candidates',totalRows=0,selectedLibrary=null;
let automaticRequest=null,automaticResultKey=null,automaticInspectorKey=null;
let manualMetadataTouched=false,manualTrackTouched=false,manualDraftLease=null,draftLeaseFailure='',draftLeaseQueue=Promise.resolve();
const filters={files:'all',candidates:'converted'};
const filterOptions={files:[['all','All files'],['errors','Read errors'],['review','Needs metadata review'],['preview','Preview available'],['missing','No longer found']],candidates:[['converted','Audiobook Ready'],['all','All candidates'],['jobs','Queued / creating'],['held','Held'],['recording_review','Recording review'],['errors','Source read errors'],['changed','Candidate changed'],['output_attention','Output needs attention']]};
const form = $('review-form');
const fields = ['original_language','title','author','canonical_author','narrator','series','number','genre','topic'];
let proposalId=null,coverId=null,trackDraft=null,trackDirty=false,coverSequence=0,mergeRenderKey=null,proposalRenderKey=null,memberRenderKey=null,coverRenderKey=null;
const selectedBooks=new Map(),coverObjects=[];
let inspectorIdentity=null,inspectSequence=0;
const inspectorObjects=[];
let recoveryPanel=null,recoveryConfirmation=null,recoverySubmitting=false,recoveryDisconnected=false;
let retryPending=null,retryResult=null,retryEpoch=0;
let listTicket=0,listPending='',paintedContext='',attentionGroup='all',retryAllRun=null,retryAllConfirm=null,stripNote='';
const rowRetries=new Map();
const pendingFolders=new Set(),folderMessages=new Map();

function routingControls() {
  const audio=['audiobook','candidate'].includes(selectedRow?.kind);
  const anthology=audio && form.elements.namedItem('anthology').checked;
  for(const element of document.querySelectorAll('.audio-only'))element.hidden=!audio;
  form.elements.namedItem('author').disabled=anthology;
  form.elements.namedItem('multi_author').disabled=anthology;
  $('author-folder-help').hidden=!anthology;
  $('multi-author-help').hidden=!anthology;
}
function viewControls(){
  const audio=$('library').value==='Audiobooks';
  $('view').hidden=!audio;$('view-label').hidden=!audio;
  if(!audio)view='files';
  if(!filterOptions[view].some(([value])=>value===filters[view]))filters[view]=view==='candidates'?'converted':'all';
  $('view').value=view;
  $('filter').replaceChildren();
  for(const [value,label] of filterOptions[view]){const option=document.createElement('option');option.value=value;option.textContent=label;if(value==='held')option.title='Show books that automatic processing could not safely approve.';if(value==='recording_review')option.title='Show recordings marked for comparison, including verified distinct recordings.';$('filter').append(option);}
  $('filter').value=filters[view];
  $('filter').title=filters[view]==='held'?'Show books that automatic processing could not safely approve.':filters[view]==='recording_review'?'Show recordings marked for comparison, including verified distinct recordings.':'Filter the saved results in this library.';
  for(const id of ['automatic-controls','automatic-help','automatic-policy','automatic-status-block'])$(id).hidden=!audio;
  $('search-label').textContent=view==='files'?'Path contains':'Candidate contains';
  inventoryIntro.textContent=view==='files'?'Each row is a source file, including chapter tracks and companion files. Switch to Book candidates to review audiobook groups.':'Automatic processing researches book candidates and converts confident matches. Held books stay out of the queue; manual review is optional.';
  $('batch-controls').hidden=!audio || view!=='candidates';
}
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

function clearConnectionNotice(){recoveryDisconnected=false;connectionNotice.hidden=true;if(connectionNotice.textContent)connectionNotice.textContent='';updateRecovery();renderAutomatic();renderJobs();controls();}
function refreshFailed(error){
  if(ended)return;
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

async function request(route, data) {
  const options = {headers:{'X-Books-Token':token}, credentials:'same-origin', cache:'no-store'};
  if (data !== undefined && recoveryDisconnected)throw Error('Connection interrupted. Wait for the local server to reconnect.');
  if (data !== undefined) { options.method='POST'; options.headers['Content-Type']='application/json'; options.body=JSON.stringify(data); }
  const response = await fetch(route, options);
  const result = await response.json();
  if (!response.ok) {const error=new Error(result.error || `Local request failed (${response.status})`);error.httpStatus=response.status;error.automaticProcessing=result.automatic_processing;throw error;}
  return result;
}
function message(value='') { $('message').textContent=value; }
// The only writer of #version: the engine's own version, as reported by its state.
function renderVersion(){const value=typeof state?.version==='string' && state.version?'v'+state.version:'';if($('version').textContent!==value)$('version').textContent=value;$('version').hidden=!value;}
function controls() {
  updateRecovery();updateRetry();updateRowRetries();renderAttentionGroups();
  const active = state?.active_library;
  const automatic=state?.automatic_processing,automaticOwnsScanner=['Running','Stopping'].includes(automatic?.state);
  $('start-automatic').disabled=busy || ended || recoveryDisconnected || automaticRequest!==null || automatic?.can_start!==true || !!draftLeaseFailure || !!(manualDraftLease?.active && !manualDraftLease.confirmed);
  renderAutomaticEligibility();
  $('stop-automatic').disabled=busy || ended || recoveryDisconnected || automaticRequest!==null || automatic?.can_stop!==true;
  const stopped = ['stopped','offline','failed'].includes(state?.status?.state);
  $('start').disabled = busy || ended || recoveryDisconnected || !!active || stopped || !state || automaticOwnsScanner;
  $('resume').disabled = busy || ended || recoveryDisconnected || !!active || !stopped || automaticOwnsScanner;
  $('stop').disabled = busy || ended || recoveryDisconnected || !active || state?.stopping || automaticOwnsScanner;
  $('shutdown').disabled = busy || ended || recoveryDisconnected;
  $('approve-candidate').disabled=busy || ended || recoveryDisconnected || dirty || selectedRow?.kind!=='candidate' || !selectedRow?.can_approve;
  if(selectedRow?.kind==='candidate')$('approval-reason').textContent=dirty ? 'Save the draft metadata before approving it.' : selectedRow.approval_reason || '';
  $('approval-reason').hidden=!$('approval-reason').textContent;
  if($('create-audiobook'))$('create-audiobook').disabled=busy || ended || recoveryDisconnected || dirty || trackDirty || !selectedRow?.creation?.can_create || selectedRow?.creation?.status==='Single audiobook file';
  for(const id of ['source-coverage','playback-order'])if($(id))$(id).disabled=busy || ended || recoveryDisconnected;
  if($('add-chapters'))$('add-chapters').disabled=busy || ended || recoveryDisconnected || !selectedRow?.creation?.chapters_available;
  for(const id of ['find-metadata','find-covers','save-tracks'])if($(id))$(id).disabled=busy || ended || recoveryDisconnected || selectedRow?.kind!=='candidate';
  if($('queue-books'))$('queue-books').disabled=busy || ended || recoveryDisconnected || !rows.some(readyForQueue);
  if($('pause-jobs'))$('pause-jobs').disabled=busy || ended || recoveryDisconnected || !['Running','running'].includes(state?.audiobook_jobs?.state);
  if($('resume-jobs'))$('resume-jobs').disabled=busy || ended || recoveryDisconnected || !state?.audiobook_jobs?.queued || ['Running','running','Pausing','pausing'].includes(state?.audiobook_jobs?.state);
}
async function action(route, data) {
  if (busy || ended) return;
  busy=true; controls(); message();
  try { await request(route,data); lastKey=null; await refresh(true); }
  catch(error) { message(error.message); }
  finally { busy=false; controls(); }
}
function select(row, reset) {
  const changing=selectedPath!==row.path;
  if(reset && (changing || dirty || trackDirty)){discardManualDraft();if(changing)$('manual-review').open=row.kind!=='candidate';}
  if(changing){automaticResultKey=null;automaticInspectorKey=null;closeRecoveryDialog(false);recoveryPanel=null;inspectorIdentity=null;++inspectSequence;$('metadata-inspector').hidden=true;for(const url of inspectorObjects)URL.revokeObjectURL(url);inspectorObjects.length=0;}
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
  $('notes').textContent=[...(row.metadata.notes || []),row.error].filter(Boolean).join(' · ');
  $('tags').textContent=JSON.stringify(row.metadata.tags || {},null,2);
  $('read-error').hidden=!row.error;
  $('read-error-path').textContent=row.path;
  $('read-error-time').textContent=row.error_time ? `Last failed read: ${row.error_time}` : 'Last failed read time was not recorded.';
  $('read-error-message').textContent=row.error || '';
  $('read-error-action').textContent=row.error?.startsWith('File changed during read') ? 'The file changed while its metadata was being read. Let copying finish, then start scanning to retry it.' : row.size===0 && row.kind==='audiobook' && row.metadata.notes?.includes('Metadata read failed; source file untouched') ? 'This audio file is empty. Replace it with a complete copy, then start scanning.' : 'Start scanning to retry unreadable files.';
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
  if(!force && focused && $('inventory').contains?.(focused)){const selected=rows.find(row=>row.path===selectedPath);if(selected)select(selected,false);return;}
  const body=$('inventory'); body.replaceChildren();
  $('inventory-head').replaceChildren();const heading=document.createElement('tr');
  for(const label of view==='candidates'?['Select','Title clue','Author / reader clues','Audio files','Review status','Actions']:['Type','Arrival','Existing title / filename clue','Existing author / artist clue','Preview status','Proposed destination','Actions']){const th=document.createElement('th');th.textContent=label;heading.append(th);}$('inventory-head').append(heading);
  for (const row of rows) {
    const tr=document.createElement('tr'); tr.dataset.path=row.path; tr.tabIndex=0;
    tr.setAttribute('aria-selected',String(row.path===selectedPath));
    if(row.kind==='candidate'){const td=document.createElement('td'),label=document.createElement('label'),check=document.createElement('input');label.className='check';check.type='checkbox';check.checked=selectedBooks.has(row.id);check.setAttribute('aria-label','Select '+row.title_clue);check.title='Select this candidate for the reviewed audiobook queue.';check.addEventListener('click',event=>event.stopPropagation());check.addEventListener('keydown',event=>event.stopPropagation());check.addEventListener('change',()=>{if(check.checked)selectedBooks.set(row.id,row.revision);else selectedBooks.delete(row.id);batchCounts();});label.append(check);td.append(label);tr.append(td);}
    const values=row.kind==='candidate'?[candidateTitle(row),row.artists.join('; ') || 'Unknown',row.members.length,candidateStatus(row)]:[row.kind,row.arrival ? 'Yes' : '',row.metadata.title || row.path.split(/[\\/]/).pop(),row.metadata.author || '',row.error ? `Read error · ${row.error.split(/\r?\n/)[0].slice(0,200)}`:row.preview.confidence,row.preview.path || 'Needs review'];
    for (const [index,value] of values.entries()) { const td=document.createElement('td'); td.textContent=value;
      if(row.kind==='candidate' && index===3){
        const attention=attentionText(row);
        if(attention){const hint=node('p',attention.hint,'field-help attention-hint');hint.classList.toggle('retry-refused',!!attention.warn);td.append(hint);td.title=technicalText(row);rowRetries.set(row.path,{row,hint,button:null});}
        else if(repairedText(row.creation?.job?.repaired))td.append(node('p',repairedText(row.creation.job.repaired),'field-help attention-hint'));
        if(recordingMarker(row))td.append(node('p',recordingMarker(row),'field-help'));
      }
      tr.append(td); }
    const actions=node('td'),buttons=node('div','','row-actions'),name=row.title_clue || row.metadata?.title || row.path.split(/[\\/]/).pop();
    const rowRetry=rowRetries.get(row.path),action=rowAction(row);
    if(rowRetry && action){
      const retry=node('button',action.label,'quiet row-retry');retry.type='button';rowRetry.button=retry;
      retry.addEventListener('click',event=>{event.stopPropagation();if(retry.getAttribute?.('aria-disabled')==='true' || retryPending)return;retryFromRow(row);});
      retry.addEventListener('keydown',event=>event.stopPropagation());buttons.append(retry);
    }
    const inspect=node('button','View metadata','quiet');inspect.type='button';inspect.title='Show metadata, artwork and the file location.';inspect.setAttribute('aria-label','View metadata: '+name);inspect.setAttribute('aria-describedby','inspect-help');inspect.disabled=!recordIdentity(row).id;inspect.addEventListener('click',event=>{event.stopPropagation();viewMetadata(row);});inspect.addEventListener('keydown',event=>event.stopPropagation());buttons.append(inspect);
    if(row.kind==='candidate' && row.source_directory_count!==1){const folders=node('button','Source folders','quiet');folders.type='button';folders.title="Show the folders containing this candidate's source tracks.";folders.setAttribute('aria-label','Source folders: '+name);folders.setAttribute('aria-describedby','folder-help');folders.addEventListener('click',event=>{event.stopPropagation();viewMetadata(row,true);});folders.addEventListener('keydown',event=>event.stopPropagation());buttons.append(folders);}
    else{const folder=node('button','Open folder','quiet');folder.type='button';folder.title=row.kind==='candidate'?"Open this book's source folder in File Explorer.":"Open this source file's folder in File Explorer.";folder.setAttribute('aria-label','Open folder: '+name);folder.setAttribute('aria-describedby','folder-help');folder.disabled=!recordIdentity(row).id;const status=node('span','','folder-message');status.setAttribute('role','status');folderState(row,folder,status);folder.addEventListener('click',event=>{event.stopPropagation();select(row,selectedPath!==row.path);openFolder(row,folder,status);});folder.addEventListener('keydown',event=>event.stopPropagation());buttons.append(folder,status);}
    actions.append(buttons);tr.append(actions);
    tr.addEventListener('click',()=>select(row,selectedPath!==row.path));
    tr.addEventListener('keydown',event=>{if(event.key==='Enter' || event.key===' '){event.preventDefault();select(row,selectedPath!==row.path);}});
    body.append(tr);
  }
  const selected=rows.find(row=>row.path===selectedPath);
  if (selected) select(selected,false);
  else if(!selectedRow){$('details').hidden=true;}
  $('empty').hidden=rows.length>0;
  const unit=view==='candidates'?'candidates':'files';
  const label=filterOptions[view].find(item=>item[0]===filters[view])[1];
  const emptyText=view==='candidates' && filters[view]==='converted' && !search && totalRows===0?'No audiobooks are ready yet. Automatic processing progress appears above; choose All candidates or Held to inspect unfinished books.':`No ${unit} match these filters · ${label}.`;
  $('inventory').removeAttribute?.('aria-busy');
  $('empty').textContent=emptyText;
  $('page').textContent=rows.length ? `Showing ${offset+1}–${offset+rows.length} of ${totalRows} ${unit} · ${label}` : `No ${unit} match these filters · ${label}.`;
  $('previous').disabled=offset===0;
  $('next').disabled=offset+rows.length>=totalRows;
  batchCounts();
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
function loadList(context,library,requestView,requestFilter,requestOffset,requestSearch,epoch,forceRender){
  const ticket=++listTicket;listPending=context;
  if(context!==paintedContext)showListLoading();
  const groupQuery=requestView==='candidates' && requestFilter==='output_attention' && attentionGroup!=='all'?`&group=${attentionGroup}`:'';
  return request(`/api/inventory?library=${encodeURIComponent(library)}&offset=${requestOffset}&search=${encodeURIComponent(requestSearch)}&view=${requestView}&status=${requestFilter}${groupQuery}`).then(page=>{
    // A book list requested before Retry was answered predates it and would repaint the old state.
    if (ended || ticket!==listTicket || $('library').value!==library || context!==listContext() || epoch!==retryEpoch) return false;
    rows=page.rows.map(row=>requestView==='candidates'?({...row,path:row.id,kind:'candidate',library}):({...row,library}));totalRows=page.total ?? (requestOffset+rows.length);
    const changed=context!==paintedContext;paintedContext=context;renderRows(forceRender || changed);
    return true;
  }).finally(()=>{if(ticket===listTicket)listPending='';});
}
async function refresh(force=false) {
  if (ended) return false;
  const sequence=++refreshSequence;
  const library=$('library').value,context=listContext(),requestView=view,requestFilter=filters[view],requestOffset=offset,requestSearch=search,epoch=retryEpoch;
  // A list change (filter, group, page, search, view, library) shows its loading text and asks for its list at
  // once, beside the status read: neither waits for /api/state (v0.16.7 QA: up to 11 s behind a slow status).
  const early=force?loadList(context,library,requestView,requestFilter,requestOffset,requestSearch,epoch,true):null;
  early?.catch(()=>{});
  const current=await request(`/api/state?library=${encodeURIComponent(library)}`);
  if (ended || sequence!==refreshSequence || $('library').value!==library || context!==listContext()) return false;
  state=current;
  renderJobs();renderAutomatic();renewManualDraft();
  renderVersion();
  $('root').textContent=`Source: ${state.root}`;
  const status=state.status;
  const activity=state.stopping ? 'Stopping…' : state.active_library ? `Scanning ${state.active_library}` : status.state;
  const statusText=`Discovery: ${activity} · Files cataloged ${status.count} · Files checked this scan ${status.checked} · Metadata reused this scan ${status.reused} · Pending tasks ${status.pending} · Read failures this scan ${status.errors} · Files with read errors ${status.unresolved_errors ?? status.errors}`;
  receivedStatus.set(library,statusText);$('status').textContent=statusText;
  $('error-shortcut').hidden=!(status.unresolved_errors ?? status.errors);$('error-shortcut').textContent=`Read errors · ${status.unresolved_errors ?? status.errors}`;
  $('scan-issues').hidden=!status.scan_issues?.length;$('scan-issues-text').textContent=(status.scan_issues || []).map(issue=>`${issue.path}\n${issue.error}\n${issue.time}`).join('\n\n');
  $('current').textContent=status.current || 'Choose a file to inspect existing metadata and its sorting preview.';
  if (form.elements.namedItem('genre').options.length===1) {
    for (const genre of state.genres) { const option=document.createElement('option');option.value=genre;option.textContent=genre;form.elements.namedItem('genre').append(option); }
  }
  controls();
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
  acknowledgeRestart(current);
  return true;
}
async function poll() {
  if (ended) return;
  if (!polling) {
    polling=true;
    const library=$('library').value,sequence=refreshSequence+1;
    try { if(await refresh())clearConnectionNotice(); }
    catch(error) { if(sequence===refreshSequence && library===$('library').value)refreshFailed(error); }
    finally { polling=false; }
  }
  if (!ended) timer=setTimeout(poll,800);
}
$('start').addEventListener('click',()=>action('/api/scan/start',{library:$('library').value}));
$('resume').addEventListener('click',()=>action('/api/scan/resume',{library:$('library').value}));
$('stop').addEventListener('click',()=>action('/api/scan/stop',{library:state.active_library}));
let searchTimer=null;
function listContext(){return JSON.stringify([$('library').value,view,filters[view],offset,search,$('search').value,filters[view]==='output_attention'?attentionGroup:'all']);}
// While a different list is on its way, the old rows are not shown as the new filter's result.
function showListLoading(){
  const label=filterOptions[view].find(item=>item[0]===filters[view])?.[1] || '';
  $('inventory').replaceChildren();rowRetries.clear();$('inventory').setAttribute?.('aria-busy','true');
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
function resetStrip(){retryAllRun=null;retryAllConfirm=null;stripNote='';}
$('filter').addEventListener('change',()=>{filters[view]=$('filter').value;attentionGroup='all';resetStrip();return updateList();});
$('clear-filters').addEventListener('click',()=>{$('search').value='';filters[view]='all';attentionGroup='all';resetStrip();viewControls();return updateList();});
$('error-shortcut').addEventListener('click',()=>{$('search').value='';filters[view]='errors';viewControls();return updateList();});
$('search').addEventListener('input',()=>{cancelSearchRefresh();++refreshSequence;if(!$('search').value)return updateList();searchTimer=setTimeout(()=>{searchTimer=null;updateList();},250);});
$('search-form').addEventListener('submit',event=>{event.preventDefault();return updateList();});
$('previous').addEventListener('click',()=>{offset=Math.max(0,offset-100);return updateList(false);});
$('next').addEventListener('click',()=>{offset+=100;return updateList(false);});
form.addEventListener('input',()=>{if(!dirty)reviewRow=selectedRow;dirty=true;manualMetadataTouched=true;syncManualDraft();routingControls();controls();$('review-note').textContent='Unsaved local review.';});
form.addEventListener('submit',async event=>{
  event.preventDefault();if(!selectedRow || busy || ended || recoveryDisconnected)return;
  const row=reviewRow || selectedRow;const review={};for(const field of fields)review[field]=form.elements.namedItem(field).value.trim();
  review.multi_author=form.elements.namedItem('multi_author').checked;
  review.anthology=['audiobook','candidate'].includes(selectedRow.kind) && form.elements.namedItem('anthology').checked;
  if(!['audiobook','candidate'].includes(selectedRow.kind)){review.canonical_author='';review.narrator='';}
  busy=true;controls();message();
  try {if(row.kind==='candidate'){const result=await request('/api/candidate/review',{library:selectedLibrary,id:row.id,revision:row.revision,review,approve:false,...reviewContext()});dirty=false;if(trackDraft?.id===row.id && trackDraft.revision===row.revision)trackDraft.revision=result.row.revision;select({...result.row,path:result.row.id,kind:'candidate',library:selectedLibrary},false);}else await request('/api/review',{library:selectedLibrary || $('library').value,path:row.path,size:row.size,modified:row.modified,review});dirty=false;manualMetadataTouched=false;syncManualDraft();await refresh(true);message('Preview metadata saved. Source files unchanged.');}
  catch(error){message(error.message);}
  finally{busy=false;controls();}
});
$('approve-candidate').addEventListener('click',async()=>{const row=reviewRow || selectedRow;if(!row || row.kind!=='candidate' || dirty || busy || ended)return;busy=true;controls();try{const result=await request('/api/candidate/review',{library:selectedLibrary,id:row.id,revision:row.revision,review:row.review,approve:true,...reviewContext()});select({...result.row,path:result.row.id,kind:'candidate',library:selectedLibrary},true);await refresh(true);message('Candidate metadata approved. Tracks still require review; source files unchanged.');}catch(error){message(error.message);}finally{busy=false;controls();}});
$('shutdown').addEventListener('click',async()=>{
  if(busy || ended)return;busy=true;controls();message();
  try{await request('/api/shutdown',{});ended=true;clearConnectionNotice();clearTimeout(timer);$('status').textContent='Server stopping. Saved catalog and pending scans remain available on the next launch.';message('You can close this browser tab.');}
  catch(error){message(error.message);}
  finally{busy=false;controls();}
});
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
function reviewContext(){return {manual_note:$('manual-evidence').value,proposal_id:proposalId,cover_id:coverId,actor:'user'};}
function readyForQueue(row){return !!row.creation?.can_create && row.creation?.status!=='Single audiobook file' && selectedBooks.get(row.id)===row.revision && !(selectedRow?.id===row.id && (dirty || trackDirty));}
function batchCounts(){const visible=rows.filter(row=>row.kind==='candidate'),selected=visible.filter(row=>selectedBooks.has(row.id)),ready=selected.filter(row=>readyForQueue(row));$('batch-count').textContent=`${selected.length} selected · ${ready.length} ready · ${selected.length-ready.length} need review`;$('select-page').checked=visible.length>0 && selected.length===visible.length;$('select-page').indeterminate=selected.length>0 && selected.length<visible.length;controls();}
function renderJobs(){
  const jobs=state?.audiobook_jobs;$('audio-jobs').hidden=!jobs;if(!jobs)return;
  const text=(id,value)=>{if($(id).textContent!==value)$(id).textContent=value;};
  const counts=Number.isInteger(jobs.converted_total)&&Number.isInteger(jobs.approved_total)&&jobs.converted_total>=0&&jobs.approved_total>=jobs.converted_total;
  text('jobs-status',(recoveryDisconnected || ended?'Last confirmed — ':'')+[counts?`${jobs.converted_total} converted out of ${jobs.approved_total} approved books`:'Approved book progress unavailable',jobs.state,`${jobs.queued || 0} queued`,`${jobs.failed || 0} need attention`].filter(Boolean).join(' · '));
  renderActivities(Array.isArray(state.activities)?state.activities:[],jobs);
  const cleanup=jobs.cleanup_active===true;
  $('pause-jobs').title=cleanup?'Pause audiobook work. Source cleanup finishes the current file before stopping.':'Stop the current audiobook operation and save pending books. Finished outputs stay in place.';
  $('resume-jobs').title=cleanup?'Continue pending audiobook work. Paused cleanup resumes without recreating the audiobook.':'Continue pending books. An interrupted book restarts; completed outputs are not recreated.';
  const help=cleanup?'Pausing source cleanup finishes the current file. Resume continues its saved progress. Scanning has separate stop and resume controls. An interrupted conversion restarts; completed outputs stay in place.':'An interrupted conversion restarts; completed outputs stay in place. Scanning has separate stop and resume controls.';
  text('jobs-help',help+(Array.isArray(jobs.folder_cleanup_notes)&&jobs.folder_cleanup_notes.length?' Empty source folders retained: safe automatic removal is unavailable on this drive.':''));
}
// Progress rows (ProgressRows spec): one row per running activity, fixed order, updated in place.
const activityOrder=['conversion','cleanup','identity','scan'],activityRows=new Map();let activityTimer=null;
const conversionSteps={'checking sources':'Checking source files',preparing:'Copying and checking source files','source copies':'Checking source copies','checking audio':'Checking source audio','matching format':'Choosing the audio format',normalizing:'Normalizing audio','joined audio':'Checking joined audio',creating:'Encoding audio',encoding:'Encoding audio',checking:'Verifying audiobook',copying:'Copying audiobook to the library',publishing:'Copying audiobook to the library'};
const cleanupSteps={originals:'Removing original files','recovery copies':'Checking recovery copies',temporary:'Removing temporary recovery and working files',folders:'Removing empty source folders','verifying replacement':'Verifying replacement audiobook','retiring former outputs':'Removing former audiobook versions','former outputs':'Removing former audiobook versions'};
function activityLabel(row){
  if(row.kind==='conversion')return 'Converting';
  if(row.kind==='cleanup')return ['originals','recovery copies'].includes(row.step)?'Removing originals':'Cleaning up';
  if(row.kind==='identity')return 'Checking finished books';
  return row.step==='researching'?'Researching books':'Scanning files';
}
function activityStep(row,finishing){
  let step;
  if(row.kind==='conversion'){const name=finishing && row.step==='encoding'?'Finalizing conversion':conversionSteps[row.step] || 'Working';step=Number.isInteger(row.step_index) && Number.isInteger(row.step_count)?`Step ${row.step_index} of ${row.step_count} - ${name}`:name;}
  else if(row.kind==='cleanup')step=cleanupSteps[row.step] || 'Working';
  else if(row.kind==='identity')step='Checking identity';
  else step=typeof row.step_text==='string' && row.step_text?row.step_text:'Working';
  if(row.state==='attention')return 'Needs attention - '+(row.reason || step);
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
  const label=activityLabel(row),subject=typeof row.subject==='string'?row.subject:'',step=activityStep(row,finishing),detail=activityDetail(row,finishing);
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
  writeText(view.time,clockText(elapsed,elapsed>=3600)+' elapsed'+(view.eta?' - '+view.eta:''));
}
async function candidateRequest(route,extra={}){if(busy || ended || selectedRow?.kind!=='candidate')return;const original=selectedRow,library=selectedLibrary;busy=true;controls();try{const result=await request(route,{library,id:original.id,revision:original.revision,...extra});if(selectedRow?.id===original.id && selectedLibrary===library && result.row){const updated={...result.row,path:result.row.id,kind:'candidate',library};if(dirty)reviewRow=updated;select(updated,false);}lastKey=null;await refresh(true);return result;}catch(error){message(error.message);}finally{busy=false;controls();}}
function renderMergeCandidate(row,reset){const candidate=row.kind==='candidate';for(const id of ['metadata-lookup','metadata-evidence','track-review','audiobook-output','create-audiobook'])$(id).hidden=!candidate;if(!candidate)return;
  const renderKey=JSON.stringify([row.id,row.revision,row.review_context,row.matching,row.cover_choices,row.creation,row.cleanup,row.audiobook_ready,row.metadata_facts,row.duplicate_review,dirty,trackDirty,coverId]);
  if(!reset && renderKey===mergeRenderKey)return;mergeRenderKey=$('manual-review').contains?.(document.activeElement)?null:renderKey;
  // Keep metadata and track editing inside the optional manual disclosure.
  if($('candidate-details').parentElement!==$('manual-review') || $('candidate-details').nextElementSibling!==$('track-review'))$('manual-review').insertBefore($('candidate-details'),$('track-review'));
  const context=row.review_context || {},creation=row.creation || {},matching=row.matching || {};
  if(reset || (!dirty && !$('manual-review').contains?.(document.activeElement))){$('manual-evidence').value=context.manual_note || '';proposalId=context.proposal_id || null;coverId=context.cover_id || row.selected_cover?.id || null;}
  if(reset || (!trackDirty && !$('track-review').contains?.(document.activeElement) && !$('candidate-details').contains?.(document.activeElement))){trackDraft={id:row.id,revision:row.revision,order:row.track_order || row.members.map(member=>member.member_key || member.path),included:row.included || row.members.map(member=>member.member_key || member.path)};trackDirty=false;$('source-coverage').checked=!!context.source_coverage_confirmed;$('playback-order').checked=!!context.order_confirmed;const chapterDefault=context.chapters_choice_saved===false && creation.chapters_default===true && creation.chapters_available===true && !creation.job && !/queued|creating|checking|created|completed/i.test(creation.status || '');$('add-chapters').checked=chapterDefault || !!context.chapters;if(chapterDefault)trackDirty=true;}
  const actor=actorValue=>actorValue==='assistant'?'Assistant review':actorValue==='user'?'User review':'Needs review';
  $('candidate-facts').textContent=`Metadata: ${actor(context.metadata_actor)} · ${context.source_coverage_confirmed?'Source files reviewed: '+actor(context.track_actor):'Source files need review'} · Playback order: ${context.order_confirmed?actor(context.track_actor):'Needs review'} · Recording completeness unknown`;
  $('accepted-evidence').textContent=JSON.stringify({proposal_id:context.proposal_id,metadata_reviewer:context.metadata_actor,metadata_date:context.metadata_utc,track_reviewer:context.track_actor,track_date:context.track_utc,metadata_evidence:context.metadata_evidence || [],track_evidence:context.track_evidence || '',manual_note:context.manual_note || ''},null,2);
  $('matching-status').textContent=matching.error || (matching.state==='finding' || matching.state==='pending'?'Finding metadata…':matching.proposals?.length?'Original work matches; recording unverified':matching.state==='completed'?'No reliable match found. Review the title and author, then try again.':'Find possible identities or enter verified metadata manually.');
  const proposalKey=JSON.stringify([row.id,matching]);if(proposalKey!==proposalRenderKey && !$('metadata-proposals').contains?.(document.activeElement)){proposalRenderKey=proposalKey;$('metadata-proposals').replaceChildren();for(const proposal of matching.proposals || []){const panel=node('section','','proposal'),authors=Array.isArray(proposal.authors)?proposal.authors.join('; '):proposal.authors || '';panel.append(node('p',`${proposal.title || 'Unknown title'} · ${authors || 'Author unknown'}`),node('p',[proposal.original_language,proposal.series,proposal.number,'Original work match; recording unverified'].filter(Boolean).join(' · ')),sourceLink(proposal.public_url,`${proposal.provider || 'Source'}: ${proposal.title || 'book identity'}`));const evidence=node('details');evidence.append(node('summary','View evidence'),node('pre',JSON.stringify(proposal.per_field_evidence || {},null,2)));panel.append(evidence);const use=node('button','Use as proposal');use.type='button';use.title='Fill draft metadata from this match. Review the fields before approving.';use.setAttribute('aria-describedby','lookup-help');use.disabled=ended;use.addEventListener('click',()=>{if(busy || ended)return;if(!dirty)reviewRow=selectedRow;proposalId=proposal.id;if(proposal.title)form.elements.namedItem('title').value=proposal.title;if(authors)form.elements.namedItem('canonical_author').value=authors;if(proposal.original_language && !['unknown','und'].includes(proposal.original_language.toLowerCase())){const lang=proposal.original_language.toLowerCase();form.elements.namedItem('original_language').value=['russian','ru','rus'].includes(lang)?'Russian':'Other';}if(proposal.series)form.elements.namedItem('series').value=proposal.series;if(proposal.number!==null && proposal.number!==undefined)form.elements.namedItem('number').value=String(proposal.number);dirty=true;manualMetadataTouched=true;syncManualDraft();$('review-note').textContent='Proposal copied to draft. Review its sourced fields before saving.';controls();});panel.append(use);$('metadata-proposals').append(panel);}}
  renderMembers(row);renderCovers(row);
  $('chapters-control').hidden=!creation.chapters_available;$('add-chapters').disabled=!creation.chapters_available || busy;$('chapters-help').textContent=creation.chapters_available?"Preserves source track names when available. Unnamed tracks use Track 01, Track 02, and so on. These markers may differ from the book's written chapters.":creation.chapters_description || 'Chapter boundaries unavailable.';
  $('output-status').textContent=candidateStatus(row);$('output-path').textContent=creation.destination || 'No reviewed destination yet.';
  $('output-summary').textContent=[creation.format || 'M4B audiobook',`Included files: ${trackDraft.included.length}`,`Duration: ${typeof creation.duration_seconds==='number'?creation.duration_seconds.toFixed(2)+' s':'Total duration incomplete'}`,`Title: ${row.review?.title || 'Needs review'}`,`Artist: ${row.review?.canonical_author || 'Needs author review'}`,`Series: ${row.metadata_facts?.series_state==='omitted_unknown'?'Not established':row.review?.series || 'Series not established'}${row.metadata_facts?.series_state==='omitted_unknown'?'':row.review?.number?' / '+row.review.number:''}`,`Reader / comments: ${row.tag_preview?.narrator || row.review?.narrator || 'Unknown optional narrator'}`,`Comments: ${JSON.stringify(row.tag_preview?.comment_fields || [])}`,`Cover: ${provenanceFacts(row).Cover || row.selected_cover?.source_label || 'Artwork not established'}`,chapterSummary(row),...Object.entries({...provenanceFacts(row),...recordingFacts(row)}).filter(([label])=>!['Series','Cover'].includes(label)).map(([label,value])=>label+': '+value),...cleanupFacts(row)].join('\n');
  const cleanupPolicy=creation.cleanup_policy?.enabled===true,recordedRemoval=verifiedCount(row.cleanup?.removed)>0;$('output-policy-notice').textContent=recordedRemoval && !cleanupPolicy?(row.cleanup.status || 'Source cleanup needs attention: review the saved removal progress.'):cleanupPolicy?'Creates one audiobook, verifies it, then removes the included originals. Recovery copies are kept for 24 hours after source cleanup completes, then deleted automatically while the app is running.':'Creates one new audiobook. Your source files stay in place.';$('create-audiobook').title=cleanupPolicy?'Create and verify this audiobook, then remove its included originals. Recovery copies expire 24 hours after successful source cleanup.':'Create and check one M4B from this reviewed book. Keep the source files.';
  $('output-reasons').textContent=[...(creation.reasons || []),dirty?'Save metadata edits before creating.':'',trackDirty?'Save track review before creating.':''].filter(Boolean).join(' · ');$('output-device').textContent=creation.device || 'Apple Books sync not checked';
}
function verifiedCount(value){return Number.isSafeInteger(value) && value>=0?value:null;}
function cleanupFacts(row){const creation=row.creation || {},policy=creation.cleanup_policy || {},receipt=row.cleanup || {},removed=verifiedCount(receipt.removed),total=verifiedCount(receipt.total),progress=removed!==null && total!==null?`${removed} of ${total} removed`:null;const state=typeof receipt.state==='string'?receipt.state.toLowerCase().replaceAll('_',' '):'';let status=typeof receipt.status==='string'?receipt.status:'';if(receipt.state==='completed' && receipt.recovery?.state==='retained')status='Originals removed; recovery copies kept until '+recoveryDate(receipt.recovery.expires_at);if(!status){const states={'waiting':'Waiting for output checks','pending':'Waiting for output checks','checking':'Checking temporary recovery copies','checking recovery':'Checking temporary recovery copies','preparing':'Checking temporary recovery copies','removing':removed!==null && total!==null?`Removing originals: ${removed} of ${total}`:'Removing originals','pausing':'Pausing source cleanup','paused':progress?`Source cleanup paused: ${progress}`:'Source cleanup paused','completed':receipt.temporary_cleanup==='completed'?'Originals removed; verified temporary recovery and working copies removed':'Originals removed; temporary file cleanup pending','needs attention':'Source cleanup needs attention','failed':'Source cleanup needs attention'};status=states[state] || (removed>0?'Source cleanup needs attention':policy.enabled===true?'Waiting for output checks':'Originals retained');}const facts=[`Audiobook output: ${candidateStatus(row)}`,`Source cleanup: ${policy.enabled===true?'remove originals after audiobook verification; recovery copies expire after 24 hours':'originals retained'}`];if(removed>0 && policy.enabled!==true)facts[1]='Source cleanup: '+status;else if(receipt.state || receipt.status || policy.enabled===true)facts.push('Source cleanup status: '+status);if(progress && !status.includes(progress) && !status.includes(`${removed} of ${total}`))facts.push(progress);if(receipt.reason && !status.includes(receipt.reason))facts.push('Source cleanup needs attention: '+receipt.reason);if(receipt.recovery)facts.push('Recovery copies: '+recoveryStatus(receipt.recovery));const location=receipt.recovery?null:(receipt.recovery_location || policy.recovery_root);if(!receipt.recovery && receipt.temporary_cleanup==='completed')facts.push('Temporary recovery files: removed');else if(location && receipt.recovery_bytes!==0)facts.push('Temporary recovery storage: '+location);const bytes=verifiedCount(receipt.bytes_removed),recovery=verifiedCount(receipt.recovery_bytes);if(removed>0 && bytes!==null)facts.push(`Removed from Z: ${bytes.toLocaleString('en-US')} bytes`);if(!receipt.recovery && recovery!==null && recovery>0)facts.push(`Temporary recovery storage on C: ${recovery.toLocaleString('en-US')} bytes`);const evidence=verifiedCount(receipt.preserved_evidence_count);if(evidence>0)facts.push(`Unverified legacy evidence retained: ${evidence.toLocaleString('en-US')} files`);const remaining=verifiedCount(receipt.remaining);if(remaining!==null)facts.push('Originals remaining: '+remaining);return facts;}
function chapterSummary(row){if(row.creation?.job)return row.creation.chapters_description || 'Chapter markers: see saved job plan';return $('add-chapters').checked && row.creation?.chapters_available?`Chapter markers: ${trackDraft.included.length} — one per included source track`:'Chapter markers: none';}
function updateChapterSummary(){if(!trackDraft || selectedRow?.kind!=='candidate')return;$('output-summary').textContent=$('output-summary').textContent.replace(/^Chapter markers:.*$/m,chapterSummary(selectedRow));}
function plannedChapter(member,key){if(!$('add-chapters').checked)return 'Chapter markers disabled';if(!trackDraft.included.includes(key))return 'Excluded from output — no chapter marker';if(member.chapter_name_source==='source' && member.chapter_name)return 'Source chapter name: '+member.chapter_name;const position=trackDraft.order.filter(id=>trackDraft.included.includes(id)).indexOf(key)+1;const number=Number.isInteger(member.chapter_number) && member.chapter_number>=0?member.chapter_number:position;return 'Generated chapter label: Track '+String(number).padStart(Math.max(2,String(trackDraft.included.length).length),'0');}
function renderMembers(row,force=false){if(!force && $('candidate-members').contains?.(document.activeElement))return;const focused=document.activeElement?.dataset?.memberFocus;const memberKey=JSON.stringify([row.id,row.members,row.metadata_facts,trackDraft.order,trackDraft.included,$('add-chapters').checked]);if(memberKey===memberRenderKey)return;memberRenderKey=memberKey;$('candidate-members').replaceChildren();const map=new Map(row.members.map(member=>[member.member_key || member.path,member])),order=trackDraft.order;const header=$('candidate-members').parentElement.querySelector('thead tr');header.replaceChildren();for(const label of ['Include','Proposed order','Track title / filename','Source disc / track number','Duration','Order evidence'])header.append(node('th',label));for(let index=0;index<order.length;index++){const key=order[index],member=map.get(key);if(!member)continue;const tr=node('tr'),inc=node('input');inc.type='checkbox';inc.dataset.memberFocus=key+':include';inc.checked=trackDraft.included.includes(key);inc.title='Include this source file in the output audiobook. Excluded files stay untouched.';inc.setAttribute('aria-label','Include '+member.path);inc.setAttribute('aria-describedby','track-save-help');inc.disabled=ended;inc.addEventListener('change',()=>{if(busy || ended){inc.checked=trackDraft.included.includes(key);return;}trackDraft.included=inc.checked?[...trackDraft.included,key]:trackDraft.included.filter(item=>item!==key);tracksChanged();renderMembers(row,true);});const label=node('label','','check');label.append(inc,node('span',inc.checked?'Included':'Excluded from output'));const include=node('td');include.append(label);tr.append(include);const movement=node('td');movement.append(node('p',String(index+1)));const buttons=node('div','','member-actions');for(const [delta,text] of [[-1,'Move up'],[1,'Move down']]){const button=node('button',text,'quiet');button.type='button';button.dataset.memberFocus=key+':'+delta;button.title=`${text}: ${member.path}`;button.setAttribute('aria-label',`${text}: ${member.path}`);button.setAttribute('aria-describedby','order-help');button.disabled=ended || index+delta<0 || index+delta>=order.length;button.addEventListener('click',()=>{if(busy || ended)return;[order[index],order[index+delta]]=[order[index+delta],order[index]];tracksChanged();renderMembers(row,true);});buttons.append(button);}movement.append(buttons);tr.append(movement);for(const value of [`${member.track_title || ''}\n${member.path}\n${plannedChapter(member,key)}${memberComponents(member,row).length?'\n'+memberComponents(member,row).join('\n'):''}`, `${member.source_disc || 'Unknown'} / ${member.source_track || 'Unknown'}`,typeof member.duration==='number'?`${member.duration.toFixed(2)} s`:'Unknown',member.order_evidence || 'Unknown'])tr.append(node('td',value));$('candidate-members').append(tr);}if(focused){const target=[...$('candidate-members').querySelectorAll('[data-member-focus]')].find(element=>element.dataset.memberFocus===focused && !element.disabled);target?.focus({preventScroll:true});}const included=row.members.filter(member=>trackDraft.included.includes(member.member_key || member.path)),known=included.every(member=>typeof member.duration==='number');$('member-count').textContent=`Included audio files — ${included.length} · ${known?included.reduce((sum,member)=>sum+member.duration,0).toFixed(2)+' s':'Total duration incomplete'}`;}
function tracksChanged(){trackDirty=true;manualTrackTouched=true;syncManualDraft();updateChapterSummary();$('source-coverage').checked=false;$('playback-order').checked=false;controls();$('output-reasons').textContent='Save the changed source selection and playback order. Review confirmations were reset.';}
async function renderCovers(row){const coverKey=JSON.stringify([row.id,row.cover_choices,coverId]);if(coverKey===coverRenderKey || $('selected-cover').contains?.(document.activeElement) || $('cover-choices').contains?.(document.activeElement))return;coverRenderKey=coverKey;const seq=++coverSequence;for(const url of coverObjects)URL.revokeObjectURL(url);coverObjects.length=0;$('selected-cover').replaceChildren();$('cover-choices').replaceChildren();for(const cover of row.cover_choices || []){const panel=node('section','','cover-choice');panel.append(node('p',`${cover.source_label || 'Artwork'} · ${cover.evidence_kind || 'Local artwork — edition unverified'}`));if(cover.source_url)panel.append(sourceLink(cover.source_url,`Cover source: ${cover.source_label || 'Artwork'}`));const image=node('img');image.alt=`Cover: ${row.review?.title || row.title_clue}`;image.hidden=true;panel.append(image);const imageState=node('p','Loading cover…');panel.append(imageState);const use=node('button','Use this cover','quiet');use.type='button';use.title='Select this image as the single cover in the output audiobook.';use.setAttribute('aria-describedby','cover-help');use.disabled=ended;use.addEventListener('click',()=>{if(busy || ended)return;if(!dirty)reviewRow=selectedRow;coverId=cover.id;dirty=true;manualMetadataTouched=true;syncManualDraft();$('review-note').textContent='Cover selection is an unsaved draft.';renderCovers(row);controls();});panel.append(use);(cover.id===coverId?$('selected-cover'):$('cover-choices')).append(panel);if(!cover.thumbnail_url){imageState.textContent='Cover image unavailable';continue;}try{const url=new URL(cover.thumbnail_url,location.origin);if(url.origin!==location.origin)throw Error('Invalid local thumbnail route');const response=await fetch(url.href,{headers:{'X-Books-Token':token},credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error('Cover image unavailable');const blob=await response.blob();if(seq!==coverSequence)return;const object=URL.createObjectURL(blob);coverObjects.push(object);image.src=object;image.hidden=false;imageState.textContent='';}catch(error){if(seq===coverSequence)imageState.textContent=error.message || 'Cover image unavailable';}}if(!coverId)$('selected-cover').append(node('p',row.metadata_facts?.cover?.kind==='absent'?'No artwork available; the saved policy permits processing without artwork.':'Artwork not selected. Artwork alone does not establish recording identity.'));}
$('select-page').addEventListener('change',()=>{for(const row of rows.filter(item=>item.kind==='candidate')){if($('select-page').checked)selectedBooks.set(row.id,row.revision);else selectedBooks.delete(row.id);}renderRows();});
$('find-metadata').addEventListener('click',()=>candidateRequest('/api/candidate/match'));
$('find-covers').addEventListener('click',()=>candidateRequest('/api/candidate/covers'));
$('save-tracks').addEventListener('click',async()=>{if(!trackDraft)return;const draft=trackDraft;const result=await candidateRequest('/api/candidate/tracks',{revision:draft.revision,order:draft.order,included:draft.included,source_coverage_confirmed:$('source-coverage').checked,order_confirmed:$('playback-order').checked,chapters:$('add-chapters').checked,actor:'user',evidence_note:$('manual-evidence').value});if(result?.row && selectedRow?.id===draft.id){trackDirty=false;manualTrackTouched=false;syncManualDraft();renderMergeCandidate(selectedRow,false);message('Track review saved. Source files unchanged.');}});
for(const id of ['source-coverage','playback-order','add-chapters'])$(id).addEventListener('change',()=>{trackDirty=true;manualTrackTouched=true;syncManualDraft();updateChapterSummary();if(id==='add-chapters' && selectedRow?.kind==='candidate')renderMembers(selectedRow);controls();});
$('create-audiobook').addEventListener('click',()=>{if(!dirty && !trackDirty && selectedRow?.creation?.can_create)candidateRequest('/api/audiobook/create');});
$('queue-books').addEventListener('click',async()=>{const chosen=rows.filter(row=>row.kind==='candidate' && selectedBooks.has(row.id));const ready=chosen.filter(row=>readyForQueue(row));const blocked=chosen.filter(row=>!ready.includes(row));if(!ready.length)return;if(busy || ended)return;busy=true;controls();try{const result=await request('/api/audiobook/queue',{library:'Audiobooks',candidates:ready.map(row=>({id:row.id,revision:row.revision}))});await refresh(true);message([`${ready.length} reviewed candidate(s) requested for queue.`,...blocked.map(row=>`${row.title_clue}: ${(row.creation?.reasons || ['Needs review or candidate changed']).join('; ')}`)].join('\n'));if(result.excluded?.length)message($('message').textContent+'\n'+result.excluded.map(item=>item.reason || 'Candidate needs review').join('\n'));}catch(error){message(error.message);}finally{busy=false;controls();}});
$('pause-jobs').addEventListener('click',()=>action('/api/audiobook/pause',{}));$('resume-jobs').addEventListener('click',()=>action('/api/audiobook/resume',{}));
function recoveryDate(value){if(!value)return 'Unavailable';const date=new Date(value);if(!Number.isFinite(date.getTime()))return 'Unavailable';const zone=Intl.DateTimeFormat().resolvedOptions().timeZone;return new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:zone}).format(date)+` (${zone})`;}
function recoverySpace(value){return verifiedCount(value)===null?'Unavailable':`${(value/(value>0 && value<1000000?1000:1000000)).toLocaleString('en-US',{maximumFractionDigits:2})} ${value>0 && value<1000000?'KB':'MB'} (${value.toLocaleString('en-US')} bytes)`;}
function recoveryScope(row){const r=row?.cleanup?.recovery;return r?{job_id:row.creation?.job_id || row.creation?.job?.job_id || row.creation?.job?.id,token:r.token,count:r.count,bytes:r.bytes}:null;}
function recoveryReason(){const r=selectedRow?.cleanup?.recovery;if(ended || recoveryDisconnected)return 'Local server unavailable';if(recoverySubmitting || busy)return 'Another operation is in progress';if(!r)return 'Recovery details unavailable';if(r.state==='deleted')return 'No recovery copies remain';if(r.state==='deleting')return 'Recovery deletion is in progress';if(r.eligible!==true)return r.reason || 'Recovery copies are not eligible for deletion';if(!(verifiedCount(r.count)>0) || verifiedCount(r.bytes)===null || !r.token || !recoveryScope(selectedRow)?.job_id)return 'Verified recovery scope unavailable';return '';}
function recoveryStatus(r){if(r.state==='deleted')return `Recovery copies deleted${r.actor==='automatic'?' automatically':r.actor==='manual'?' manually':''} on ${recoveryDate(r.deleted_at)}`;if(r.state==='deleting')return `Deleting recovery copies: ${verifiedCount(r.removed) ?? 'Unavailable'} of ${verifiedCount(r.total) ?? 'Unavailable'}`;if(r.state==='retained' && !r.eligible)return 'Recovery copies retained; waiting for the app to become idle. '+(r.reason || 'Deletion is temporarily unavailable');if(r.state==='needs_attention' || !r.eligible)return 'Recovery cleanup needs attention: '+(r.reason || 'Verified recovery scope unavailable');const deadline=new Date(r.expires_at).getTime();return Number.isFinite(deadline) && deadline<=Date.now()?'Expired; waiting for automatic cleanup':'Available until '+recoveryDate(r.expires_at);}
function makeRecoveryPanel(){const panel=node('section','','recovery-copies'),facts=node('dl'),values={};panel.append(node('h2','Recovery copies'));for(const key of ['Status','Original tracks backed up','Space on C:','Recovery location','Automatic deletion']){const label=node('dt',key),value=node('dd');facts.append(label,value);values[key]={label,value};}panel.append(facts);const help=node('p',"Deleting these copies permanently removes the app's backup of the original tracks. The finished audiobook stays in place.",'field-help');help.id='recovery-loss-help';const expiry=node('p','Automatic deletion happens while the app is running; overdue copies are checked when it starts.','field-help');const button=node('button','Delete recovery copies…','quiet');button.type='button';button.title='Permanently delete the verified recovery copies for this book. Keep the finished audiobook.';button.setAttribute('aria-describedby','recovery-loss-help recovery-reason');const reason=node('p','','field-help');reason.id='recovery-reason';const status=node('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');panel.append(help,expiry,button,reason,status);recoveryPanel={panel,values,expiry,button,reason,status,path:selectedPath};button.addEventListener('click',openRecoveryDialog);updateRecovery();return panel;}
function updateRecovery(){if(!recoveryPanel || recoveryPanel.path!==selectedPath)return;const r=selectedRow?.cleanup?.recovery;if(!r){recoveryPanel.panel.hidden=true;closeRecoveryDialog();return;}recoveryPanel.panel.hidden=false;const v=recoveryPanel.values;v.Status.value.textContent=recoveryStatus(r);v['Original tracks backed up'].value.textContent=verifiedCount(r.count)===null?'Unavailable':r.count.toLocaleString('en-US');v['Space on C:'].value.textContent=recoverySpace(r.bytes);v['Recovery location'].label.textContent=r.state==='deleted'?'Former recovery location':'Recovery location';v['Recovery location'].value.textContent=r.location || 'Unavailable';v['Recovery location'].value.className='path';v['Automatic deletion'].value.textContent=r.state==='deleted'?(r.expires_at?'Completed':'Not applicable — copies already deleted'):recoveryDate(r.expires_at);recoveryPanel.expiry.hidden=r.state==='deleted';const reason=recoveryReason();recoveryPanel.button.disabled=!!reason;recoveryPanel.reason.textContent=reason;if(recoveryConfirmation && !recoverySubmitting && (reason || JSON.stringify(recoveryScope(selectedRow))!==JSON.stringify(recoveryConfirmation.scope))){closeRecoveryDialog();recoveryPanel.status.textContent='Recovery copies changed. Review the updated details and try again.';}}
function closeRecoveryDialog(restore=true){if(!recoveryConfirmation)return;const initiating=recoveryConfirmation.button;recoveryConfirmation=null;$('recovery-dialog').close?.();if(restore && initiating && initiating===recoveryPanel?.button){if(!initiating.disabled)initiating.focus?.({preventScroll:true});else{recoveryPanel.reason.setAttribute('tabindex','-1');recoveryPanel.reason.focus?.({preventScroll:true});}}}
function openRecoveryDialog(){if(recoveryReason() || recoveryConfirmation)return;const scope=recoveryScope(selectedRow),r=selectedRow.cleanup.recovery;recoveryConfirmation={scope:{...scope},path:selectedPath,button:recoveryPanel.button};$('recovery-dialog-book').textContent=`${selectedRow.review?.title || selectedRow.title_clue || 'Book'} — ${selectedRow.review?.canonical_author || 'Author unavailable'}`;$('recovery-dialog-size').textContent=`${scope.count} original tracks · ${recoverySpace(scope.bytes)} on C:`;$('recovery-dialog-location').textContent=r.location || 'Unavailable';$('recovery-dialog').showModal?.();$('recovery-cancel').focus?.();}
async function deleteRecoveryCopies(){if(!recoveryConfirmation || recoverySubmitting)return;const saved=recoveryConfirmation;if(recoveryReason() || selectedPath!==saved.path || JSON.stringify(recoveryScope(selectedRow))!==JSON.stringify(saved.scope)){closeRecoveryDialog();if(recoveryPanel)recoveryPanel.status.textContent='Recovery copies changed. Review the updated details and try again.';return;}closeRecoveryDialog();recoverySubmitting=true;updateRecovery();const panel=recoveryPanel;panel.status.textContent='Deleting recovery copies…';try{await request('/api/audiobook/recovery/delete',saved.scope);await refresh(true);if(panel===recoveryPanel)panel.status.textContent='Recovery deletion request completed.';}catch(error){if(panel===recoveryPanel)panel.status.textContent=error.httpStatus===409?'Recovery copies changed. Review the updated details and try again.':error.message;if(!error.httpStatus)refreshFailed(error);}finally{recoverySubmitting=false;updateRecovery();}}
// Retry for an audiobook job refused before it started. One static button, updated in place from
// controls() on every poll; pending and result text belong to one book (candidate id + job id).
const retryReady='Check this book again and queue its audiobook job.';
function retryKey(row){const job=row?.kind==='candidate'?row.creation?.job:null;return job && typeof job.job_id==='string'?JSON.stringify([row.id,job.job_id]):'';}
// Repair (Attention spec section 2) is the same control with another label, tooltip and endpoint.
const rowActions={retry:{kind:'retry',label:'Retry',pending:'Retrying…',note:'Checking this book…',ready:retryReady,endpoint:'/api/audiobook/retry',refused:'Retry was not accepted. Check the status above.'},
  repair:{kind:'repair',label:'Repair',pending:'Repairing…',note:'Repairing this book…',ready:'Patch the damage found in this book, then queue its audiobook job.',endpoint:'/api/audiobook/repair',refused:'Repair was not accepted. Check the status above.'}};
function rowAction(row){
  const job=row?.kind==='candidate'?row.creation?.job:null;if(!job)return null;
  // A damaged book shows Repair and never Retry (Retry would fail again on the same damage).
  // Once accepted, the request waits for its turn: the button gives way to the queued text (no second press).
  if(readmissionOf(row)?.queued_next===true)return null;
  const [kind,data]=attentionOf(row)?.group==='repair'?['repair',job.repair]:['retry',job.retry];
  return data && typeof data==='object' && typeof data.allowed==='boolean'?{...rowActions[kind],data}:null;
}
// Retry and Repair of an M4B book are accepted at once and run right after the current book (m4b_readmission).
function readmissionOf(row){const job=row?.creation?.job,value=job?.readmission || job?.attention?.readmission;return value && typeof value==='object'?value:null;}
function queuedNextText(value){
  const running=!!state?.audiobook_jobs?.current_job_id,position=Number.isInteger(value?.position) && value.position>0?value.position:1,ahead=(running?1:0)+position-1;
  return ahead===0?'Queued — runs next':ahead===1 && running?'Queued — runs after the current book':`Queued — runs after ${ahead.toLocaleString()} books`;
}
function queuedNext(row,result){
  const job={...row.creation.job,readmission:{accepted:true,queued_next:true,position:result.position,kind:result.kind}};delete job.retry;delete job.repair;
  return {...row,creation:{...row.creation,job}};
}
function bulkRun(){const run=state?.audiobook_jobs?.retry_all;return run && typeof run==='object' && typeof run.id==='string'?run:null;}
function bulkRunning(){return bulkRun()?.state==='running';}
function updateRetry(){
  const block=$('retry-block'),button=$('retry-job'),note=$('retry-note');if(!block || !button || !note)return;
  const row=selectedRow,key=retryKey(row),action=key?rowAction(row):null,retry=action?.data;
  if(retryResult && retryResult.key!==key)retryResult=null;
  const pending=!!key && retryPending?.key===key,copy=pending?rowActions[retryPending.kind]:action;
  const shown=pending || !!action;
  block.hidden=!shown;
  if(!shown){if(note.textContent)note.textContent='';note.hidden=true;return;}
  const mode=ended || recoveryDisconnected?'offline':pending?'pending':busy || recoverySubmitting || automaticRequest!==null || retryPending || bulkRunning()?'busy':retry.allowed===true?'ready':'unavailable';
  const reason=typeof retry?.reason==='string' && retry.reason.trim()?retry.reason:copy.label+' is unavailable. Refresh and check again.';
  const title={offline:'Local server unavailable.',pending:copy.note,busy:'Another operation is in progress.',unavailable:reason,ready:copy.ready}[mode];
  const label=mode==='pending'?copy.pending:copy.label,result=mode!=='pending' && retryResult;
  const text=result?retryResult.text:mode==='ready'?'':title;
  if(button.textContent!==label)button.textContent=label;
  if(button.title!==title)button.title=title;
  button.setAttribute('aria-label',label+': '+(row.review?.title || row.title_clue || 'Book'));
  // Pending keeps keyboard focus: aria-disabled with a disabled look, never the disabled attribute.
  if(mode==='pending')button.setAttribute('aria-disabled','true');else button.removeAttribute('aria-disabled');
  button.disabled=mode!=='ready' && mode!=='pending';
  if(note.textContent!==text)note.textContent=text;
  note.hidden=!text;note.classList.toggle('retry-refused',!!result);
}
function queuedByRetry(row){const job={...row.creation.job,state:'Queued',stage:'queued',reason:''};delete job.retry;delete job.repair;delete job.attention;return {...row,status:'Queued',creation:{...row.creation,status:'Queued',job}};}
async function retryFromRow(row){
  // Select without scrolling, then the same request as the details-panel Retry.
  if(selectedPath!==row.path)select(row,true);
  const index=rows.findIndex(item=>item.path===row.path);
  await retryJob({row:true,path:row.path,index});
}
function retryMode(row){
  const key=retryKey(row),retry=key?rowAction(row)?.data:null;
  if(ended || recoveryDisconnected)return 'offline';
  if(key && retryPending?.key===key)return 'pending';
  if(busy || recoverySubmitting || automaticRequest!==null || retryPending || bulkRunning())return 'busy';
  return retry?.allowed===true?'ready':'unavailable';
}
function updateRowRetries(){
  for(const entry of rowRetries.values()){
    const row=entry.row,attention=attentionText(row),key=retryKey(row),mode=entry.button?retryMode(row):null,action=rowAction(row),retry=action?.data;
    const copy=retryPending?.key===key?rowActions[retryPending.kind]:action || rowActions.retry;
    let hint=attention?attention.hint:'',warn=!!attention?.warn;
    if(mode==='unavailable' && typeof retry?.reason==='string' && retry.reason)hint=retry.reason;
    if(mode==='pending')hint=copy.note;
    if(retryResult && retryResult.key===key && mode!=='pending'){hint=retryResult.text;warn=true;}
    if(entry.hint.textContent!==hint)entry.hint.textContent=hint;
    entry.hint.classList.toggle('retry-refused',warn);
    if(!entry.button)continue;
    const label=mode==='pending'?copy.pending:copy.label,title={offline:'Local server unavailable.',pending:copy.note,busy:'Another operation is in progress.',unavailable:retry?.reason || copy.label+' is unavailable. Refresh and check again.',ready:copy.ready}[mode];
    if(entry.button.textContent!==label)entry.button.textContent=label;
    if(entry.button.title!==title)entry.button.title=title;
    entry.button.setAttribute('aria-label',label+': '+(row.title_clue || row.review?.title || 'Book'));
    if(mode==='pending')entry.button.setAttribute('aria-disabled','true');else entry.button.removeAttribute('aria-disabled');
    entry.button.disabled=mode!=='ready' && mode!=='pending';
  }
}
async function retryJob(origin=null){
  const row=selectedRow,key=retryKey(row),job=key?row.creation.job:null,action=key?rowAction(row):null;
  if(!key || !action || retryPending || busy || ended || recoveryDisconnected || recoverySubmitting || automaticRequest!==null || bulkRunning() || action.data.allowed!==true || $('retry-job').disabled)return;
  retryPending={key,kind:action.kind};retryResult=null;busy=true;controls();
  let succeeded=false;
  let answer=null;
  try{answer=await request(action.endpoint,{library:'Audiobooks',id:row.id,revision:row.revision,job_id:job.job_id});succeeded=true;}
  catch(error){retryResult={key,text:error.httpStatus?(error.message || action.refused):'Connection interrupted. Check the status above before trying again.'};if(!error.httpStatus)refreshFailed(error);else if(error.httpStatus===409)retryEpoch++;}
  // The book leaves this filter: the strip keeps a line saying what Repair will patch.
  if(succeeded && action.kind==='repair' && filters[view]==='output_attention')stripNote='Repair queued: '+damageHint(attentionOf(row));
  const focused=document.activeElement===$('retry-job');
  retryPending=null;busy=false;
  if(succeeded){
    // The server requeued the job: show it as queued now, and ignore book lists requested before this answer.
    retryEpoch++;const queued=answer?.queued_next===true?queuedNext(row,answer):queuedByRetry(row);rows=rows.map(item=>item.path===row.path?queued:item);
    // The block leaves the page: focus moves to the panel heading, never into the automatic result.
    if(focused && retryKey(selectedRow)===key)$('details-heading').focus?.({preventScroll:true});
    if(selectedRow?.path===row.path)select(queued,false);
  }
  controls();
  if(!recoveryDisconnected && !ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}
  controls();
  if(origin?.row && succeeded){
    // The rebuilt list may no longer hold the book: its row, else the row now at that index, else the filter.
    const rowsNow=$('inventory').children,same=[...rowsNow].find(tr=>tr.dataset?.path===origin.path);
    (same || rowsNow[Math.min(origin.index,rowsNow.length-1)] || $('filter')).focus?.({preventScroll:true});
  }
  return succeeded;
}
// Retry all (Attention spec section 6): the server's whole Can retry group, not the visible page,
// after an inline confirmation. The server runs one book at a time; its count arrives with each poll.
function openRetryAll(){
  const counts=state?.audiobook_jobs?.attention_counts || {},count=Number.isInteger(counts.retry)?counts.retry:0,queued=state?.audiobook_jobs?.queued;
  if(count<2 || bulkRunning() || busy || ended || recoveryDisconnected)return;
  retryAllConfirm={count,queued:Number.isInteger(queued) && queued>0?queued:0};stripNote='';renderAttentionGroups();
  $('retry-all-cancel').focus?.({preventScroll:true});
}
function closeRetryAll(){if(!retryAllConfirm)return;retryAllConfirm=null;renderAttentionGroups();$('retry-all').focus?.({preventScroll:true});}
async function startRetryAll(){
  if(!retryAllConfirm || bulkRunning() || busy || ended || recoveryDisconnected)return;
  retryAllConfirm=null;busy=true;stripNote='';controls();
  try{
    const result=await request('/api/audiobook/retry-all',{library:'Audiobooks'}),run=result?.retry_all;
    if(run && typeof run.id==='string'){
      retryAllRun={id:run.id,ended:false};state={...state,audiobook_jobs:{...(state?.audiobook_jobs || {}),retry_all:run}};
      stripNote=`Retrying ${Number(run.total).toLocaleString()} books.`;
    }
  }catch(error){stripNote=error.httpStatus?(error.message || 'Retry all was not accepted. Check the status above.'):'Connection interrupted. Check the status above before trying again.';if(!error.httpStatus)refreshFailed(error);}
  finally{busy=false;}
  controls();$('retry-all-status').focus?.({preventScroll:true});
}
function finishRetryAll(run){
  // Once per run: the end line stays until the group or filter changes; the list reloads and focus returns to the group.
  retryAllRun.ended=true;const queued=Number(run.queued)||0,total=Number(run.total)||0;
  const next=Number(run.next)||0,after=next?` ${next===queued?'They run':`${next.toLocaleString()} of them run`} right after the current book, one at a time.`:'';
  stripNote=run.state==='done'?`Queued ${queued.toLocaleString()} of ${total.toLocaleString()}.${after}${total>queued?` ${(total-queued).toLocaleString()} could not be retried.`:''}`:`Stopped. Queued ${queued.toLocaleString()} of ${total.toLocaleString()}.${after}`;
  setTimeout(async()=>{if(!recoveryDisconnected && !ended){lastKey=null;try{await refresh(true);}catch(error){if(!error.httpStatus)refreshFailed(error);}}controls();if(!$('attention-groups').hidden)$('group-retry').focus?.({preventScroll:true});},0);
}
const attentionLabels={all:'All',retry:'Can retry',repair:'Can repair',other:'Other',unsupported:'M4B not supported'};
const attentionKeys=['all','retry','repair','other','unsupported'];
function renderAttentionGroups(){
  const shown=view==='candidates' && filters[view]==='output_attention',strip=$('attention-groups');strip.hidden=!shown;if(!shown)return;
  const counts=state?.audiobook_jobs?.attention_counts || {},value=key=>Number.isInteger(counts[key])?counts[key]:0,total=value('retry')+value('repair')+value('other')+value('unsupported');
  for(const key of attentionKeys){
    const button=$('group-'+key),count=key==='all'?total:value(key),text=`${attentionLabels[key]} · ${count.toLocaleString()}`;
    if(button.textContent!==text)button.textContent=text;
    button.setAttribute('aria-pressed',String(attentionGroup===key));
    if(key==='all')button.title=`Show all ${total.toLocaleString()} books that need attention.`;
  }
  const run=bulkRun(),running=run?.state==='running';
  if(retryAllRun && !retryAllRun.ended && run?.id===retryAllRun.id && !running)finishRetryAll(run);
  const all=$('retry-all'),confirm=retryAllConfirm,allLabel=`Retry all (${value('retry').toLocaleString()})`;
  all.hidden=attentionGroup!=='retry' || value('retry')<2 || !!confirm;
  if(all.textContent!==allLabel)all.textContent=allLabel;
  all.title=`Check these ${value('retry').toLocaleString()} books again and queue each audiobook job.`;
  all.disabled=running || busy || ended || recoveryDisconnected;
  // The confirmation keeps the count it opened with; polls never rebuild it.
  $('retry-all-confirm').hidden=!confirm || attentionGroup!=='retry';
  if(confirm){
    const question=`Queue ${confirm.count.toLocaleString()} books to be checked again? They run one at a time, right after the current book.`,go=`Queue ${confirm.count.toLocaleString()} books`;
    if($('retry-all-question').textContent!==question)$('retry-all-question').textContent=question;
    if($('retry-all-go').textContent!==go)$('retry-all-go').textContent=go;
    $('retry-all-go').disabled=running || busy || ended || recoveryDisconnected;
  }
  // The live region announces only the start and the end; the running count sits outside it.
  const count=running?`${Number(run.done).toLocaleString()} of ${Number(run.total).toLocaleString()}`:'';
  if($('retry-all-status').textContent!==stripNote)$('retry-all-status').textContent=stripNote;
  if($('retry-all-count').textContent!==count)$('retry-all-count').textContent=count;
  $('retry-all-line').hidden=!stripNote && !count;
}
for(const key of attentionKeys)$('group-'+key).addEventListener('click',()=>{if(attentionGroup===key)return;attentionGroup=key;resetStrip();renderAttentionGroups();return updateList();});
$('retry-all').addEventListener('click',()=>{if($('retry-all').disabled)return;openRetryAll();});
$('retry-all-go').addEventListener('click',()=>{if($('retry-all-go').disabled)return;return startRetryAll();});
$('retry-all-cancel').addEventListener('click',()=>closeRetryAll());
$('retry-all-confirm').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault?.();closeRetryAll();}});
$('retry-job').addEventListener('click',()=>{if($('retry-job').getAttribute?.('aria-disabled')==='true' || retryPending)return;retryJob();});
$('recovery-cancel').addEventListener('click',()=>closeRecoveryDialog());
$('recovery-confirm').addEventListener('click',deleteRecoveryCopies);
$('recovery-dialog').addEventListener('cancel',event=>{event.preventDefault();closeRecoveryDialog();});
$('recovery-dialog').addEventListener('keydown',event=>{if(!recoveryConfirmation)return;if(event.key==='Escape'){event.preventDefault();closeRecoveryDialog();}else if(event.key==='Tab'){event.preventDefault();const first=$('recovery-cancel'),last=$('recovery-confirm');(document.activeElement===first?last:first).focus();}});

const automaticStates=new Set(['Idle','Running','Stopping','Paused','Completed','Needs attention']);
function setText(id,value){if($(id).textContent!==value)$(id).textContent=value;}
function automaticPhase(value){return {discovery:'discovery',research:'metadata research',conversion:'audiobook jobs',paused:'saving pending work',completed:'finishing the pass'}[value] || 'pending work';}
function renderAutomaticEligibility(){
  const automatic=state?.automatic_processing;
  let reason='';
  if(ended)reason='The local server is stopping or stopped. Start is unavailable.';
  else if(recoveryDisconnected || typeof automatic?.can_start!=='boolean')reason='Start availability is unknown. Waiting for the local server.';
  else if(automaticRequest==='start' || draftLeaseFailure || (manualDraftLease?.active && !manualDraftLease.confirmed))reason='';
  else if(automatic.can_start!==true)reason=automatic.start_block_reason || 'Start availability is unknown. Waiting for the local server.';
  setText('automatic-start-reason',reason);
  $('automatic-start-reason').hidden=$('library').value!=='Audiobooks' || !reason;
  $('start-automatic').title=reason || (automatic?.state==='Paused'?'Continue the saved discovery, metadata research and queued audiobook jobs.':'Discover audiobooks, research public metadata, and convert confident matches. Uncertain books stay held.');
}
function renderAutomatic(){
  const automatic=state?.automatic_processing,known=automaticStates.has(automatic?.state),stale=recoveryDisconnected || ended?'Last confirmed — ':'';
  setText('automatic-status',stale+'Automatic processing: '+(known?automatic.state:'status unavailable'));
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
  }else if(automatic?.reason)detail=automatic.reason;
  setText('automatic-detail',detail);$('automatic-detail').hidden=!detail;
  const research=automatic?.research,counts=research && ['researching','waiting','held'].every(key=>verifiedCount(research[key])!==null);
  setText('research-status',stale+(counts?'Metadata research: '+research.researching+' researching · '+research.waiting+' waiting · '+research.held+' held':'Research status unavailable'));
  const current=automatic?.current;
  const currentText=current && current.title && research?.researching>0?'Current research: '+current.title+' — '+[current.source,current.stage].filter(Boolean).join(' / ')+(research.researching>1?' and '+(research.researching-1)+' more':''):'';
  setText('research-current',currentText);$('research-current').hidden=!currentText;
}
async function automaticAction(kind){
  controls();const button=$(kind==='start'?'start-automatic':'stop-automatic');
  if(button.disabled || automaticRequest!==null || $('library').value!=='Audiobooks')return;
  automaticRequest=kind;busy=true;renderAutomatic();controls();message();
  try{
    const result=await request('/api/automatic/'+kind,{});
    const acknowledged=result.automatic_processing || result.state?.automatic_processing;
    if(acknowledged && state){state={...state,automatic_processing:acknowledged};renderAutomatic();}
    lastKey=null;if(await refresh(true))clearConnectionNotice();
  }catch(error){
    if(error.automaticProcessing && state)state={...state,automatic_processing:error.automaticProcessing};
    message(error.message);
    if(error.httpStatus){lastKey=null;await refresh(true);}else refreshFailed(error);
  }finally{automaticRequest=null;busy=false;renderAutomatic();controls();}
}
$('start-automatic').addEventListener('click',()=>automaticAction('start'));
$('stop-automatic').addEventListener('click',()=>automaticAction('stop'));
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
  unsupported:["Can't convert — M4B not supported",'Nothing to do for now.'],other:['Stopped — see details','Select the row to read why.']};
function attentionOf(row){const job=row?.creation?.job;return job?.state==='Output needs attention' && job.attention && typeof job.attention.group==='string'?job.attention:null;}
function attentionText(row){
  const a=attentionOf(row);if(!a)return null;
  const kind=a.group==='retry'?(a.cause==='space'?'space':'retry'):a.group==='repair'?'repair':a.group==='unsupported'?'unsupported':'other',[status,hint]=attentionCopy[kind];
  const readmission=readmissionOf(row);
  if(readmission?.queued_next===true)return {status:queuedNextText(readmission),hint:readmission.kind==='repair'?damageHint(a):'The book is checked again before it runs.'};
  if(readmission?.accepted===false && typeof readmission.reason==='string' && readmission.reason)return {status,hint:(readmission.kind==='repair'?'Repair':'Retry')+' was refused: '+readmission.reason,warn:true};
  return {status,hint:kind==='repair'?damageHint(a):kind==='unsupported' && a.originals_untouched===true?'Nothing to do for now. Originals are untouched.':hint};
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
function technicalText(row){
  const job=row?.creation?.job || {},details=(attentionOf(row)?.damage || []).map(item=>item?.description).filter(text=>typeof text==='string' && text);
  return 'Technical detail: '+(job.reason || 'Unavailable')+(details.length?' — '+details.join(' '):'');
}
function candidateStatus(row){
  const attention=attentionText(row);if(attention)return attention.status;
  const readmission=readmissionOf(row);if(readmission?.queued_next===true)return queuedNextText(readmission);
  const creation=row.creation?.status || '',status=row.status || '',automatic=row.automatic,job=row.creation?.job;
  // A job that needs attention leads with its own reason, so the status names what was blocked.
  const jobReason=job?.state==='Output needs attention' && typeof job.reason==='string'?job.reason:'';
  const cleanup=row.cleanup || {},reason=jobReason || (automatic?.reasons || [])[0] || (row.creation?.reasons || [])[0] || cleanup.reason || '';
  const facts=[creation,status,cleanup.state || '',cleanup.temporary_cleanup || ''].join(' ');
  if(/failed|attention|error/i.test(facts) || automatic?.state==='Needs attention')return 'Needs attention'+(reason?' — '+reason:'');
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
function retryDate(value){if(typeof value!=='number' || !Number.isFinite(value) || value<=0)return '';const date=new Date(value<1e12?value*1000:value);return Number.isFinite(date.getTime())?recoveryDate(date.toISOString()):'';}
function renderAutomaticResult(row){
  $('automatic-result').hidden=row.kind!=='candidate';if(row.kind!=='candidate')return;
  const key=JSON.stringify([state?.automatic_processing?.state,state?.automatic_processing?.automatic_retry_enabled,row.id,row.revision,row.automatic,row.metadata_approved,row.review,row.review_context,row.selected_cover,row.track_order,row.included,row.members,row.creation?.destination,row.creation?.status,row.creation?.job?.state,row.creation?.job?.reason,row.creation?.job?.attention,row.creation?.job?.repaired,row.creation?.job?.readmission,state?.audiobook_jobs?.current_job_id,row.status,row.audiobook_ready,row.cleanup,row.metadata_facts,row.duplicate_review,row.current_audiobook]);
  if(key===automaticResultKey)return;
  // Retry is updated in place by updateRetry(), never rebuilt here, so its focus does not freeze the status line.
  if($('automatic-result').contains?.(document.activeElement) && !$('retry-block').contains?.(document.activeElement))return;
  automaticResultKey=key;const automatic=row.automatic;
  setText('automatic-result-status',candidateStatus(row));
  const attention=attentionText(row);setText('automatic-result-hint',attention?attention.hint:'');$('automatic-result-hint').hidden=!attention;
  // After Repair: a permanent line and one bullet per patch; the technical note is the last line.
  const repaired=row.creation?.job?.repaired,patched=Array.isArray(repaired?.patched)?repaired.patched:[];
  setText('automatic-repaired-title',patched.length?(repaired.applied===true?'Repaired':'Repair queued'):'');$('automatic-repaired-list').replaceChildren(...patched.map(item=>node('li',patchCopy(item))));$('automatic-repaired').hidden=!patched.length;
  const technical=attention?technicalText(row):patched.length && typeof repaired.detail==='string' && repaired.detail?'Technical detail: '+repaired.detail:'';
  setText('automatic-technical',technical);$('automatic-technical').hidden=!technical;
  $('automatic-reasons').replaceChildren();for(const reason of automatic?.reasons || [])$('automatic-reasons').append(node('li',reason));$('automatic-reasons').hidden=!automatic?.reasons?.length;
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
  Object.assign(values,provenanceFacts(row),recordingFacts(row));if(row.metadata_facts?.series_state==='omitted_unknown')delete values['Series position'];
  for(const [label,value] of Object.entries(values))if(value!==undefined && value!==null && value!=='')facts.append(node('dt',label),node('dd',value));
  const included=new Set(row.included || row.members?.map(member=>member.member_key || member.path) || []),members=new Map((row.members || []).map(member=>[member.member_key || member.path,member]));
  $('automatic-tracks').replaceChildren();for(const key of row.track_order || members.keys())if(included.has(key) && members.has(key))$('automatic-tracks').append(node('li',[members.get(key).path,...memberComponents(members.get(key),row)].join('\n')));
  const sources=$('automatic-sources');sources.replaceChildren();if(automatic?.sources?.length){sources.append(node('h3','Research sources'));for(const source of automatic.sources){const line=node('p');let label=source.kind || 'Public source';try{label+=' — '+new URL(source.url).hostname;}catch{}line.append(sourceLink(source.url,label));const facts=[source.verified_identity===true?'Identity verified':source.verified_identity===false?'Identity unverified':'',typeof source.credit==='object' && source.credit!==null?[source.credit.author,source.credit.title].filter(Boolean).join(' — '):source.credit,source.retrieved_utc?'Retrieved '+recoveryDate(source.retrieved_utc):''].filter(Boolean);if(facts.length)line.append(node('span',' · '+facts.join(' · ')));sources.append(line);}}
  const accepted={metadata:context.metadata_evidence || [],recording:context.track_evidence || '',manual_note:context.manual_note || '',metadata_provenance:row.metadata_facts || null,recording_review:row.duplicate_review || null};
  $('automatic-accepted-evidence').textContent=JSON.stringify(accepted,null,2);$('automatic-accepted').hidden=!accepted.metadata.length && !accepted.recording && !accepted.manual_note && !accepted.metadata_provenance && !accepted.recording_review;
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

controls();
viewControls();poll();

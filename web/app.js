'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="books-token"]').content;
let offset = 0, search = '', selectedPath = null, selectedRow = null, reviewRow = null, rows = [], lastKey = null;
let dirty = false, busy = false, polling = false, ended = false, timer = null, state = null;
let view='files',totalRows=0,selectedLibrary=null;
const filters={files:'all',candidates:'all'};
const filterOptions={files:[['all','All files'],['errors','Read errors'],['review','Needs metadata review'],['preview','Preview available'],['missing','No longer found']],candidates:[['all','All candidates'],['review','Needs review'],['approved','Metadata approved'],['errors','Source read errors'],['changed','Candidate changed']]};
const form = $('review-form');
const fields = ['original_language','title','author','canonical_author','narrator','series','number','genre','topic'];
let proposalId=null,coverId=null,trackDraft=null,trackDirty=false,coverSequence=0,mergeRenderKey=null,proposalRenderKey=null,memberRenderKey=null,coverRenderKey=null;
const selectedBooks=new Map(),coverObjects=[];
let inspectorIdentity=null,inspectSequence=0;
const inspectorObjects=[];
const pendingFolders=new Set(),folderMessages=new Map();
filterOptions.candidates.push(['ready','Ready to create'],['jobs','Queued / creating'],['created','Audiobook created'],['output_attention','Output needs attention']);

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
  $('view').value=view;
  $('filter').replaceChildren();
  for(const [value,label] of filterOptions[view]){const option=document.createElement('option');option.value=value;option.textContent=label;$('filter').append(option);}
  $('filter').value=filters[view];
  $('search-label').textContent=view==='files'?'Path contains':'Candidate contains';
  inventoryIntro.textContent=view==='files'?'Each row is a source file, including chapter tracks and companion files. Switch to Book candidates to review audiobook groups.':'Candidates are possible books assembled from source clues. Review metadata, intended source files and playback order before creating an audiobook.';
  $('batch-controls').hidden=!audio || view!=='candidates';
}
const connectionText='Browser connection interrupted. The scan may still be running; retrying…';
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

function clearConnectionNotice(){connectionNotice.hidden=true;if(connectionNotice.textContent)connectionNotice.textContent='';}
function refreshFailed(error){
  if(ended)return;
  if(error.httpStatus){
    const prior=$('message').textContent;
    if(!prior.includes(error.message))message(prior ? prior+'\n'+error.message : error.message);
    return;
  }
  if(connectionNotice.textContent!==connectionText)connectionNotice.textContent=connectionText;
  connectionNotice.hidden=false;
  $('status').textContent='Last received: '+(receivedStatus.get($('library').value) || 'No status received yet.');
}

async function request(route, data) {
  const options = {headers:{'X-Books-Token':token}, credentials:'same-origin', cache:'no-store'};
  if (data !== undefined) { options.method='POST'; options.headers['Content-Type']='application/json'; options.body=JSON.stringify(data); }
  const response = await fetch(route, options);
  const result = await response.json();
  if (!response.ok) {const error=new Error(result.error || `Local request failed (${response.status})`);error.httpStatus=response.status;throw error;}
  return result;
}
function message(value='') { $('message').textContent=value; }
function controls() {
  const active = state?.active_library;
  const stopped = ['stopped','offline','failed'].includes(state?.status.state);
  $('start').disabled = busy || ended || !!active || stopped || !state;
  $('resume').disabled = busy || ended || !!active || !stopped;
  $('stop').disabled = busy || ended || !active || state?.stopping;
  $('shutdown').disabled = busy || ended;
  $('approve-candidate').disabled=busy || ended || dirty || selectedRow?.kind!=='candidate' || !selectedRow?.can_approve;
  if(selectedRow?.kind==='candidate')$('approval-reason').textContent=dirty ? 'Save the draft metadata before approving it.' : selectedRow.approval_reason || '';
  $('approval-reason').hidden=!$('approval-reason').textContent;
  if($('create-audiobook'))$('create-audiobook').disabled=busy || ended || dirty || trackDirty || !selectedRow?.creation?.can_create || selectedRow?.creation?.status==='Single audiobook file';
  for(const id of ['source-coverage','playback-order'])if($(id))$(id).disabled=busy || ended;
  if($('add-chapters'))$('add-chapters').disabled=busy || ended || !selectedRow?.creation?.chapters_available;
  for(const id of ['find-metadata','find-covers','save-tracks'])if($(id))$(id).disabled=busy || ended || selectedRow?.kind!=='candidate';
  if($('queue-books'))$('queue-books').disabled=busy || ended || !rows.some(readyForQueue);
  if($('pause-jobs'))$('pause-jobs').disabled=busy || ended || !['Running','running'].includes(state?.audiobook_jobs?.state);
  if($('resume-jobs'))$('resume-jobs').disabled=busy || ended || !state?.audiobook_jobs?.queued || ['Running','running','Pausing','pausing'].includes(state?.audiobook_jobs?.state);
}
async function action(route, data) {
  if (busy || ended) return;
  busy=true; controls(); message();
  try { await request(route,data); lastKey=null; await refresh(true); }
  catch(error) { message(error.message); }
  finally { busy=false; controls(); }
}
function select(row, reset) {
  if(selectedPath!==row.path){inspectorIdentity=null;++inspectSequence;$('metadata-inspector').hidden=true;for(const url of inspectorObjects)URL.revokeObjectURL(url);inspectorObjects.length=0;}
  selectedPath=row.path; selectedRow=row;
  selectedLibrary=row.library || $('library').value;
  const candidate=row.kind==='candidate';
  $('details').hidden=false;
  $('details-heading').textContent=inspectorIdentity?.id===recordIdentity(row).id?(candidate?'Book metadata':'File metadata'):(candidate?'Book candidate':'Selected file');
  $('source').textContent=candidate?row.scope:row.path;
  $('reason').textContent=row.preview.reason;
  $('proposed').textContent=row.preview.path || 'No destination proposed until canonical metadata is reviewed.';
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
  if (reset || !dirty) {
    for (const field of fields) form.elements.namedItem(field).value=row.review?.[field] || (field==='original_language' ? 'Unknown' : '');
    form.elements.namedItem('multi_author').checked=!!row.review?.multi_author;
    form.elements.namedItem('anthology').checked=!!row.review?.anthology;
    dirty=false;
    reviewRow=row;
    $('review-note').textContent='Saved only in the local catalog.';
  }
  routingControls();
  renderMergeCandidate(row,reset);
  controls();
  for (const element of $('inventory').children) element.setAttribute('aria-selected',String(element.dataset.path===row.path));
}
function renderRows() {
  const body=$('inventory'); body.replaceChildren();
  $('inventory-head').replaceChildren();const heading=document.createElement('tr');
  for(const label of view==='candidates'?['Select','Title clue','Author / reader clues','Audio files','Review status','Actions']:['Type','Arrival','Existing title / filename clue','Existing author / artist clue','Preview status','Proposed destination','Actions']){const th=document.createElement('th');th.textContent=label;heading.append(th);}$('inventory-head').append(heading);
  for (const row of rows) {
    const tr=document.createElement('tr'); tr.dataset.path=row.path; tr.tabIndex=0;
    tr.setAttribute('aria-selected',String(row.path===selectedPath));
    if(row.kind==='candidate'){const td=document.createElement('td'),label=document.createElement('label'),check=document.createElement('input');label.className='check';check.type='checkbox';check.checked=selectedBooks.has(row.id);check.setAttribute('aria-label','Select '+row.title_clue);check.title='Select this candidate for the reviewed audiobook queue.';check.addEventListener('click',event=>event.stopPropagation());check.addEventListener('keydown',event=>event.stopPropagation());check.addEventListener('change',()=>{if(check.checked)selectedBooks.set(row.id,row.revision);else selectedBooks.delete(row.id);batchCounts();});label.append(check);td.append(label);tr.append(td);}
    const values=row.kind==='candidate'?[row.title_clue,row.artists.join('; ') || 'Unknown',row.members.length,row.status]:[row.kind,row.arrival ? 'Yes' : '',row.metadata.title || row.path.split(/[\\/]/).pop(),row.metadata.author || '',row.error ? `Read error · ${row.error.split(/\r?\n/)[0].slice(0,200)}`:row.preview.confidence,row.preview.path || 'Needs review'];
    for (const value of values) { const td=document.createElement('td'); td.textContent=value; tr.append(td); }
    const actions=node('td'),buttons=node('div','','row-actions'),name=row.title_clue || row.metadata?.title || row.path.split(/[\\/]/).pop();
    const inspect=node('button','View metadata','quiet');inspect.type='button';inspect.title='Show metadata, artwork and the file location.';inspect.setAttribute('aria-label','View metadata: '+name);inspect.setAttribute('aria-describedby','inspect-help');inspect.disabled=!recordIdentity(row).id;inspect.addEventListener('click',event=>{event.stopPropagation();viewMetadata(row);});inspect.addEventListener('keydown',event=>event.stopPropagation());buttons.append(inspect);
    if(row.kind==='candidate' && row.source_directory_count!==1){const folders=node('button','Source folders','quiet');folders.type='button';folders.title="Show the folders containing this candidate's source tracks.";folders.setAttribute('aria-label','Source folders: '+name);folders.setAttribute('aria-describedby','folder-help');folders.addEventListener('click',event=>{event.stopPropagation();viewMetadata(row,true);});folders.addEventListener('keydown',event=>event.stopPropagation());buttons.append(folders);}
    else{const folder=node('button','Open folder','quiet');folder.type='button';folder.title=row.kind==='candidate'?"Open this book's source folder in File Explorer.":"Open this source file's folder in File Explorer.";folder.setAttribute('aria-label','Open folder: '+name);folder.setAttribute('aria-describedby','folder-help');folder.disabled=!recordIdentity(row).id;const status=node('span','','folder-message');status.setAttribute('role','status');folderState(row,folder,status);folder.addEventListener('click',event=>{event.stopPropagation();select(row,selectedPath!==row.path);openFolder(row,folder,status);});folder.addEventListener('keydown',event=>event.stopPropagation());buttons.append(folder,status);}
    actions.append(buttons);tr.append(actions);
    tr.addEventListener('click',()=>select(row,true));
    tr.addEventListener('keydown',event=>{if(event.key==='Enter' || event.key===' '){event.preventDefault();select(row,true);}});
    body.append(tr);
  }
  const selected=rows.find(row=>row.path===selectedPath);
  if (selected) select(selected,false);
  else if(!selectedRow){$('details').hidden=true;}
  $('empty').hidden=rows.length>0;
  const unit=view==='candidates'?'candidates':'files';
  const label=filterOptions[view].find(item=>item[0]===filters[view])[1];
  $('empty').textContent=`No ${unit} match these filters.`;
  $('page').textContent=rows.length ? `Showing ${offset+1}–${offset+rows.length} of ${totalRows} ${unit} · ${label}` : `No ${unit} match these filters.`;
  $('previous').disabled=offset===0;
  $('next').disabled=offset+rows.length>=totalRows;
  batchCounts();
}
async function refresh(force=false) {
  if (ended) return false;
  const sequence=++refreshSequence;
  const library=$('library').value;
  const current=await request(`/api/state?library=${encodeURIComponent(library)}`);
  if (ended || sequence!==refreshSequence || $('library').value!==library) return false;
  state=current;
  renderJobs();
  $('version').textContent=`v${state.version} · local prototype`;
  $('root').textContent=`Source: ${state.root}`;
  const status=state.status;
  const activity=state.stopping ? 'Stopping…' : state.active_library ? `Scanning ${state.active_library}` : status.state;
  const statusText=`${activity} · Files cataloged ${status.count} · Files checked this scan ${status.checked} · Metadata reused this scan ${status.reused} · Pending tasks ${status.pending} · Read failures this scan ${status.errors} · Files with read errors ${status.unresolved_errors ?? status.errors}`;
  receivedStatus.set(library,statusText);$('status').textContent=statusText;
  $('error-shortcut').hidden=!(status.unresolved_errors ?? status.errors);$('error-shortcut').textContent=`Read errors · ${status.unresolved_errors ?? status.errors}`;
  $('scan-issues').hidden=!status.scan_issues?.length;$('scan-issues-text').textContent=(status.scan_issues || []).map(issue=>`${issue.path}\n${issue.error}\n${issue.time}`).join('\n\n');
  $('current').textContent=status.current || 'Choose a file to inspect existing metadata and its sorting preview.';
  if (form.elements.namedItem('genre').options.length===1) {
    for (const genre of state.genres) { const option=document.createElement('option');option.value=genre;option.textContent=genre;form.elements.namedItem('genre').append(option); }
  }
  controls();
  const key=JSON.stringify([library,view,filters[view],offset,search,status.count,status.checked,status.state,status.unresolved_errors]);
  if (force || view==='candidates' || key!==lastKey) {
    const page=await request(`/api/inventory?library=${encodeURIComponent(library)}&offset=${offset}&search=${encodeURIComponent(search)}&view=${view}&status=${filters[view]}`);
    if (ended || sequence!==refreshSequence || $('library').value!==library) return false;
    rows=page.rows.map(row=>view==='candidates'?({...row,path:row.id,kind:'candidate',library}):({...row,library}));totalRows=page.total ?? (offset+rows.length);lastKey=key;renderRows();
  }
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
$('library').addEventListener('change',()=>{offset=0;lastKey=null;viewControls();refresh(true).catch(error=>message(error.message));});
$('view').addEventListener('change',()=>{view=$('view').value;offset=0;lastKey=null;viewControls();refresh(true).catch(error=>message(error.message));});
$('filter').addEventListener('change',()=>{filters[view]=$('filter').value;search=$('search').value;offset=0;refresh(true).catch(error=>message(error.message));});
$('clear-filters').addEventListener('click',()=>{search='';$('search').value='';filters[view]='all';offset=0;viewControls();refresh(true).catch(error=>message(error.message));});
$('error-shortcut').addEventListener('click',()=>{search='';$('search').value='';filters[view]='errors';offset=0;viewControls();refresh(true).catch(error=>message(error.message));});
$('search-form').addEventListener('submit',event=>{event.preventDefault();search=$('search').value;offset=0;refresh(true).catch(error=>message(error.message));});
$('previous').addEventListener('click',()=>{offset=Math.max(0,offset-100);refresh(true).catch(error=>message(error.message));});
$('next').addEventListener('click',()=>{offset+=100;refresh(true).catch(error=>message(error.message));});
form.addEventListener('input',()=>{if(!dirty)reviewRow=selectedRow;dirty=true;routingControls();controls();$('review-note').textContent='Unsaved local review.';});
form.addEventListener('submit',async event=>{
  event.preventDefault();if(!selectedRow || busy || ended)return;
  const row=reviewRow || selectedRow;const review={};for(const field of fields)review[field]=form.elements.namedItem(field).value.trim();
  review.multi_author=form.elements.namedItem('multi_author').checked;
  review.anthology=['audiobook','candidate'].includes(selectedRow.kind) && form.elements.namedItem('anthology').checked;
  if(!['audiobook','candidate'].includes(selectedRow.kind)){review.canonical_author='';review.narrator='';}
  busy=true;controls();message();
  try {if(row.kind==='candidate'){const result=await request('/api/candidate/review',{library:selectedLibrary,id:row.id,revision:row.revision,review,approve:false,...reviewContext()});dirty=false;if(trackDraft?.id===row.id && trackDraft.revision===row.revision)trackDraft.revision=result.row.revision;select({...result.row,path:result.row.id,kind:'candidate',library:selectedLibrary},false);}else await request('/api/review',{library:selectedLibrary || $('library').value,path:row.path,size:row.size,modified:row.modified,review});dirty=false;await refresh(true);message('Preview metadata saved. Source files unchanged.');}
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
function renderInspector(inspector,row,sequence){for(const url of inspectorObjects)URL.revokeObjectURL(url);inspectorObjects.length=0;$('inspector-sections').replaceChildren();$('folder-list').replaceChildren();if(!inspector || !Array.isArray(inspector.sections)){ $('inspect-status').textContent='Metadata inspection unavailable';return;}
  for(const section of inspector.sections){const panel=node('section','','inspector-section');panel.append(node('h2',section.heading || 'Source metadata'));if(section.status)panel.append(node('p',section.status));if(section.kind==='approved' && !inspector.sections.some(item=>item.kind==='created') && !(section.status || '').includes('Not written to a file'))panel.append(node('p','Not written to a file'));if(section.kind==='snapshot' && !(section.status || '').includes('Saved output snapshot'))panel.append(node('p','Saved output snapshot'));
    const location=node('div','','inspector-location');if(section.path)location.append(node('p',section.path,'path'));if(section.kind==='created' && inspector.output_folder_available){const button=node('button','Open output folder','quiet'),status=node('span','','folder-message');button.type='button';button.title='Open the folder containing this created audiobook.';button.setAttribute('aria-label','Open output folder: '+section.path);button.setAttribute('aria-describedby','folder-help');status.setAttribute('role','status');folderState(row,button,status,'output');button.addEventListener('click',()=>openFolder(row,button,status,'output'));location.append(button,status);}panel.append(location);
    const content=node('div','','inspector-content'),facts=node('dl');for(const fact of section.facts || []){if(fact.value===null || fact.value===undefined || fact.value==='')continue;facts.append(node('dt',fact.label),node('dd',typeof fact.value==='string'?fact.value:JSON.stringify(fact.value)));}content.append(facts);if(section.cover){const artwork=node('div','','inspector-artwork');content.append(artwork);inspectorCover(section.cover,artwork,sequence);}panel.append(content);
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
function renderJobs(){const jobs=state?.audiobook_jobs;$('audio-jobs').hidden=!jobs;if(!jobs)return;$('jobs-status').textContent=[jobs.state,jobs.current_title,jobs.stage,`${jobs.completed || 0} completed`,`${jobs.queued || 0} queued`,`${jobs.failed || 0} need attention`].filter(Boolean).join(' · ');const cleanup=jobs.cleanup_active===true;$('pause-jobs').title=cleanup?'Pause audiobook work. Source cleanup finishes the current file before stopping.':'Stop the current audiobook operation and save pending books. Finished outputs stay in place.';$('resume-jobs').title=cleanup?'Continue pending audiobook work. Paused cleanup resumes without recreating the audiobook.':'Continue pending books. An interrupted book restarts; completed outputs are not recreated.';$('jobs-help').textContent=cleanup?'Pausing source cleanup finishes the current file. Resume continues its saved progress. Scanning has separate stop and resume controls. An interrupted conversion restarts; completed outputs stay in place.':'An interrupted conversion restarts; completed outputs stay in place. Scanning has separate stop and resume controls.';}
async function candidateRequest(route,extra={}){if(busy || ended || selectedRow?.kind!=='candidate')return;const original=selectedRow,library=selectedLibrary;busy=true;controls();try{const result=await request(route,{library,id:original.id,revision:original.revision,...extra});if(selectedRow?.id===original.id && selectedLibrary===library && result.row){const updated={...result.row,path:result.row.id,kind:'candidate',library};if(dirty)reviewRow=updated;select(updated,false);}lastKey=null;await refresh(true);return result;}catch(error){message(error.message);}finally{busy=false;controls();}}
function renderMergeCandidate(row,reset){const candidate=row.kind==='candidate';for(const id of ['metadata-lookup','metadata-evidence','track-review','audiobook-output'])$(id).hidden=!candidate;if(!candidate)return;
  const renderKey=JSON.stringify([row.id,row.revision,row.review_context,row.matching,row.cover_choices,row.creation,row.cleanup,dirty,trackDirty,coverId]);
  if(!reset && renderKey===mergeRenderKey)return;mergeRenderKey=renderKey;
  // Keep the three review sections in normal Metadata -> Sources -> Output flow.
  $('details').insertBefore($('candidate-details'),$('track-review'));
  const context=row.review_context || {},creation=row.creation || {},matching=row.matching || {};
  if(reset || !dirty){$('manual-evidence').value=context.manual_note || '';proposalId=context.proposal_id || null;coverId=context.cover_id || row.selected_cover?.id || null;}
  if(reset || !trackDirty){trackDraft={id:row.id,revision:row.revision,order:row.track_order || row.members.map(member=>member.member_key || member.path),included:row.included || row.members.map(member=>member.member_key || member.path)};trackDirty=false;$('source-coverage').checked=!!context.source_coverage_confirmed;$('playback-order').checked=!!context.order_confirmed;const chapterDefault=context.chapters_choice_saved===false && creation.chapters_default===true && creation.chapters_available===true && !creation.job && !/queued|creating|checking|created|completed/i.test(creation.status || '');$('add-chapters').checked=chapterDefault || !!context.chapters;if(chapterDefault)trackDirty=true;}
  const actor=actorValue=>actorValue==='assistant'?'Assistant review':actorValue==='user'?'User review':'Needs review';
  $('candidate-facts').textContent=`Metadata: ${actor(context.metadata_actor)} · ${context.source_coverage_confirmed?'Source files reviewed: '+actor(context.track_actor):'Source files need review'} · Playback order: ${context.order_confirmed?actor(context.track_actor):'Needs review'} · Recording completeness unknown`;
  $('accepted-evidence').textContent=JSON.stringify({proposal_id:context.proposal_id,metadata_reviewer:context.metadata_actor,metadata_date:context.metadata_utc,track_reviewer:context.track_actor,track_date:context.track_utc,metadata_evidence:context.metadata_evidence || [],track_evidence:context.track_evidence || '',manual_note:context.manual_note || ''},null,2);
  $('matching-status').textContent=matching.error || (matching.state==='finding' || matching.state==='pending'?'Finding metadata…':matching.proposals?.length?'Original work matches; recording unverified':matching.state==='completed'?'No reliable match found. Review the title and author, then try again.':'Find possible identities or enter verified metadata manually.');
  const proposalKey=JSON.stringify([row.id,matching]);if(proposalKey!==proposalRenderKey){proposalRenderKey=proposalKey;$('metadata-proposals').replaceChildren();for(const proposal of matching.proposals || []){const panel=node('section','','proposal'),authors=Array.isArray(proposal.authors)?proposal.authors.join('; '):proposal.authors || '';panel.append(node('p',`${proposal.title || 'Unknown title'} · ${authors || 'Author unknown'}`),node('p',[proposal.original_language,proposal.series,proposal.number,'Original work match; recording unverified'].filter(Boolean).join(' · ')),sourceLink(proposal.public_url,`${proposal.provider || 'Source'}: ${proposal.title || 'book identity'}`));const evidence=node('details');evidence.append(node('summary','View evidence'),node('pre',JSON.stringify(proposal.per_field_evidence || {},null,2)));panel.append(evidence);const use=node('button','Use as proposal');use.type='button';use.title='Fill draft metadata from this match. Review the fields before approving.';use.setAttribute('aria-describedby','lookup-help');use.disabled=ended;use.addEventListener('click',()=>{if(busy || ended)return;if(!dirty)reviewRow=selectedRow;proposalId=proposal.id;if(proposal.title)form.elements.namedItem('title').value=proposal.title;if(authors)form.elements.namedItem('canonical_author').value=authors;if(proposal.original_language && !['unknown','und'].includes(proposal.original_language.toLowerCase())){const lang=proposal.original_language.toLowerCase();form.elements.namedItem('original_language').value=['russian','ru','rus'].includes(lang)?'Russian':'Other';}if(proposal.series)form.elements.namedItem('series').value=proposal.series;if(proposal.number!==null && proposal.number!==undefined)form.elements.namedItem('number').value=String(proposal.number);dirty=true;$('review-note').textContent='Proposal copied to draft. Review its sourced fields before saving.';controls();});panel.append(use);$('metadata-proposals').append(panel);}}
  renderMembers(row);renderCovers(row);
  $('chapters-control').hidden=!creation.chapters_available;$('add-chapters').disabled=!creation.chapters_available || busy;$('chapters-help').textContent=creation.chapters_available?"Preserves source track names when available. Unnamed tracks use Track 01, Track 02, and so on. These markers may differ from the book's written chapters.":creation.chapters_description || 'Chapter boundaries unavailable.';
  $('output-status').textContent=creation.status || 'Needs metadata review';$('output-path').textContent=creation.destination || 'No reviewed destination yet.';
  $('output-summary').textContent=[creation.format || 'M4B audiobook',`Included files: ${trackDraft.included.length}`,`Duration: ${typeof creation.duration_seconds==='number'?creation.duration_seconds.toFixed(2)+' s':'Total duration incomplete'}`,`Title: ${row.review?.title || 'Needs review'}`,`Artist: ${row.review?.canonical_author || 'Needs author review'}`,`Series: ${row.review?.series || 'Standalone decision requires review'} / ${row.review?.number || ''}`,`Reader / comments: ${row.tag_preview?.narrator || row.review?.narrator || 'Unknown optional narrator'}`,`Comments: ${JSON.stringify(row.tag_preview?.comment_fields || [])}`,`Cover: ${row.selected_cover?.source_label || 'Choose a cover'}`,chapterSummary(row),...cleanupFacts(row)].join('\n');
  const cleanupPolicy=creation.cleanup_policy?.enabled===true,recordedRemoval=verifiedCount(row.cleanup?.removed)>0;$('output-policy-notice').textContent=recordedRemoval && !cleanupPolicy?(row.cleanup.status || 'Source cleanup needs attention: review the saved removal progress.'):cleanupPolicy?'Creates one audiobook, checks it, then removes the included originals. Recovery copies are kept.':'Creates one new audiobook. Your source files stay in place.';$('create-audiobook').title=cleanupPolicy?'Create and check this audiobook, keep recovery copies, then remove its included originals.':'Create and check one M4B from this reviewed book. Keep the source files.';
  $('output-reasons').textContent=[...(creation.reasons || []),dirty?'Save metadata edits before creating.':'',trackDirty?'Save track review before creating.':''].filter(Boolean).join(' · ');$('output-device').textContent=creation.device || 'Apple Books sync not checked';
}
function verifiedCount(value){return Number.isSafeInteger(value) && value>=0?value:null;}
function cleanupFacts(row){const creation=row.creation || {},policy=creation.cleanup_policy || {},receipt=row.cleanup || {},removed=verifiedCount(receipt.removed),total=verifiedCount(receipt.total),progress=removed!==null && total!==null?`${removed} of ${total} removed`:null;const state=typeof receipt.state==='string'?receipt.state.toLowerCase().replaceAll('_',' '):'';let status=typeof receipt.status==='string'?receipt.status:'';if(!status){const states={'waiting':'Waiting for output checks','pending':'Waiting for output checks','checking':'Checking recovery copies','checking recovery':'Checking recovery copies','preparing':'Checking recovery copies','removing':removed!==null && total!==null?`Removing originals: ${removed} of ${total}`:'Removing originals','pausing':'Pausing source cleanup','paused':progress?`Source cleanup paused: ${progress}`:'Source cleanup paused','completed':'Originals removed; recovery copies retained','needs attention':'Source cleanup needs attention','failed':'Source cleanup needs attention'};status=states[state] || (removed>0?'Source cleanup needs attention':policy.enabled===true?'Waiting for output checks':'Originals retained');}const facts=[`Audiobook output: ${creation.status || 'Needs metadata review'}`,`Source cleanup: ${policy.enabled===true?'remove after output checks':'originals retained'}`];if(removed>0 && policy.enabled!==true)facts[1]='Source cleanup: '+status;else if(receipt.state || receipt.status || policy.enabled===true)facts.push('Source cleanup status: '+status);if(progress && !status.includes(progress) && !status.includes(`${removed} of ${total}`))facts.push(progress);if(receipt.reason && !status.includes(receipt.reason))facts.push('Source cleanup needs attention: '+receipt.reason);const location=receipt.recovery_location || policy.recovery_root;if(location)facts.push('Recovery storage: '+location);const bytes=verifiedCount(receipt.bytes_removed),recovery=verifiedCount(receipt.recovery_bytes);if(removed>0 && bytes!==null)facts.push(`Removed from Z: ${bytes.toLocaleString('en-US')} bytes`);if(recovery!==null)facts.push(`Recovery storage on C: ${recovery.toLocaleString('en-US')} bytes`);const remaining=verifiedCount(receipt.remaining);if(remaining!==null)facts.push('Originals remaining: '+remaining);return facts;}
function chapterSummary(row){if(row.creation?.job)return row.creation.chapters_description || 'Chapter markers: see saved job plan';return $('add-chapters').checked && row.creation?.chapters_available?`Chapter markers: ${trackDraft.included.length} — one per included source track`:'Chapter markers: none';}
function updateChapterSummary(){if(!trackDraft || selectedRow?.kind!=='candidate')return;$('output-summary').textContent=$('output-summary').textContent.replace(/^Chapter markers:.*$/m,chapterSummary(selectedRow));}
function plannedChapter(member,key){if(!$('add-chapters').checked)return 'Chapter markers disabled';if(!trackDraft.included.includes(key))return 'Excluded from output — no chapter marker';if(member.chapter_name_source==='source' && member.chapter_name)return 'Source chapter name: '+member.chapter_name;const position=trackDraft.order.filter(id=>trackDraft.included.includes(id)).indexOf(key)+1;const number=Number.isInteger(member.chapter_number) && member.chapter_number>=0?member.chapter_number:position;return 'Generated chapter label: Track '+String(number).padStart(Math.max(2,String(trackDraft.included.length).length),'0');}
function renderMembers(row){const focused=document.activeElement?.dataset?.memberFocus;const memberKey=JSON.stringify([row.id,row.members,trackDraft.order,trackDraft.included,$('add-chapters').checked]);if(memberKey===memberRenderKey)return;memberRenderKey=memberKey;$('candidate-members').replaceChildren();const map=new Map(row.members.map(member=>[member.member_key || member.path,member])),order=trackDraft.order;const header=$('candidate-members').parentElement.querySelector('thead tr');header.replaceChildren();for(const label of ['Include','Proposed order','Track title / filename','Source disc / track number','Duration','Order evidence'])header.append(node('th',label));for(let index=0;index<order.length;index++){const key=order[index],member=map.get(key);if(!member)continue;const tr=node('tr'),inc=node('input');inc.type='checkbox';inc.dataset.memberFocus=key+':include';inc.checked=trackDraft.included.includes(key);inc.title='Include this source file in the output audiobook. Excluded files stay untouched.';inc.setAttribute('aria-label','Include '+member.path);inc.setAttribute('aria-describedby','track-save-help');inc.disabled=ended;inc.addEventListener('change',()=>{if(busy || ended){inc.checked=trackDraft.included.includes(key);return;}trackDraft.included=inc.checked?[...trackDraft.included,key]:trackDraft.included.filter(item=>item!==key);tracksChanged();renderMembers(row);});const label=node('label','','check');label.append(inc,node('span',inc.checked?'Included':'Excluded from output'));const include=node('td');include.append(label);tr.append(include);const movement=node('td');movement.append(node('p',String(index+1)));const buttons=node('div','','member-actions');for(const [delta,text] of [[-1,'Move up'],[1,'Move down']]){const button=node('button',text,'quiet');button.type='button';button.dataset.memberFocus=key+':'+delta;button.title=`${text}: ${member.path}`;button.setAttribute('aria-label',`${text}: ${member.path}`);button.setAttribute('aria-describedby','order-help');button.disabled=ended || index+delta<0 || index+delta>=order.length;button.addEventListener('click',()=>{if(busy || ended)return;[order[index],order[index+delta]]=[order[index+delta],order[index]];tracksChanged();renderMembers(row);});buttons.append(button);}movement.append(buttons);tr.append(movement);for(const value of [`${member.track_title || ''}\n${member.path}\n${plannedChapter(member,key)}`,`${member.source_disc || 'Unknown'} / ${member.source_track || 'Unknown'}`,typeof member.duration==='number'?`${member.duration.toFixed(2)} s`:'Unknown',member.order_evidence || 'Unknown'])tr.append(node('td',value));$('candidate-members').append(tr);}if(focused){const target=[...$('candidate-members').querySelectorAll('[data-member-focus]')].find(element=>element.dataset.memberFocus===focused && !element.disabled);target?.focus({preventScroll:true});}const included=row.members.filter(member=>trackDraft.included.includes(member.member_key || member.path)),known=included.every(member=>typeof member.duration==='number');$('member-count').textContent=`Included audio files — ${included.length} · ${known?included.reduce((sum,member)=>sum+member.duration,0).toFixed(2)+' s':'Total duration incomplete'}`;}
function tracksChanged(){trackDirty=true;updateChapterSummary();$('source-coverage').checked=false;$('playback-order').checked=false;controls();$('output-reasons').textContent='Save the changed source selection and playback order. Review confirmations were reset.';}
async function renderCovers(row){const coverKey=JSON.stringify([row.id,row.cover_choices,coverId]);if(coverKey===coverRenderKey)return;coverRenderKey=coverKey;const seq=++coverSequence;for(const url of coverObjects)URL.revokeObjectURL(url);coverObjects.length=0;$('selected-cover').replaceChildren();$('cover-choices').replaceChildren();for(const cover of row.cover_choices || []){const panel=node('section','','cover-choice');panel.append(node('p',`${cover.source_label || 'Artwork'} · ${cover.evidence_kind || 'Local artwork — edition unverified'}`));if(cover.source_url)panel.append(sourceLink(cover.source_url,`Cover source: ${cover.source_label || 'Artwork'}`));const image=node('img');image.alt=`Cover: ${row.review?.title || row.title_clue}`;image.hidden=true;panel.append(image);const imageState=node('p','Loading cover…');panel.append(imageState);const use=node('button','Use this cover','quiet');use.type='button';use.title='Select this image as the single cover in the output audiobook.';use.setAttribute('aria-describedby','cover-help');use.disabled=ended;use.addEventListener('click',()=>{if(busy || ended)return;if(!dirty)reviewRow=selectedRow;coverId=cover.id;dirty=true;$('review-note').textContent='Cover selection is an unsaved draft.';renderCovers(row);controls();});panel.append(use);(cover.id===coverId?$('selected-cover'):$('cover-choices')).append(panel);if(!cover.thumbnail_url){imageState.textContent='Cover image unavailable';continue;}try{const url=new URL(cover.thumbnail_url,location.origin);if(url.origin!==location.origin)throw Error('Invalid local thumbnail route');const response=await fetch(url.href,{headers:{'X-Books-Token':token},credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error('Cover image unavailable');const blob=await response.blob();if(seq!==coverSequence)return;const object=URL.createObjectURL(blob);coverObjects.push(object);image.src=object;image.hidden=false;imageState.textContent='';}catch(error){if(seq===coverSequence)imageState.textContent=error.message || 'Cover image unavailable';}}if(!coverId)$('selected-cover').append(node('p','Choose one usable cover before approving output metadata.'));}
$('select-page').addEventListener('change',()=>{for(const row of rows.filter(item=>item.kind==='candidate')){if($('select-page').checked)selectedBooks.set(row.id,row.revision);else selectedBooks.delete(row.id);}renderRows();});
$('find-metadata').addEventListener('click',()=>candidateRequest('/api/candidate/match'));
$('find-covers').addEventListener('click',()=>candidateRequest('/api/candidate/covers'));
$('save-tracks').addEventListener('click',async()=>{if(!trackDraft)return;const draft=trackDraft;const result=await candidateRequest('/api/candidate/tracks',{revision:draft.revision,order:draft.order,included:draft.included,source_coverage_confirmed:$('source-coverage').checked,order_confirmed:$('playback-order').checked,chapters:$('add-chapters').checked,actor:'user',evidence_note:$('manual-evidence').value});if(result?.row && selectedRow?.id===draft.id){trackDirty=false;renderMergeCandidate(selectedRow,false);message('Track review saved. Source files unchanged.');}});
for(const id of ['source-coverage','playback-order','add-chapters'])$(id).addEventListener('change',()=>{trackDirty=true;updateChapterSummary();if(id==='add-chapters' && selectedRow?.kind==='candidate')renderMembers(selectedRow);controls();});
$('create-audiobook').addEventListener('click',()=>{if(!dirty && !trackDirty && selectedRow?.creation?.can_create)candidateRequest('/api/audiobook/create');});
$('queue-books').addEventListener('click',async()=>{const chosen=rows.filter(row=>row.kind==='candidate' && selectedBooks.has(row.id));const ready=chosen.filter(row=>readyForQueue(row));const blocked=chosen.filter(row=>!ready.includes(row));if(!ready.length)return;if(busy || ended)return;busy=true;controls();try{const result=await request('/api/audiobook/queue',{library:'Audiobooks',candidates:ready.map(row=>({id:row.id,revision:row.revision}))});await refresh(true);message([`${ready.length} reviewed candidate(s) requested for queue.`,...blocked.map(row=>`${row.title_clue}: ${(row.creation?.reasons || ['Needs review or candidate changed']).join('; ')}`)].join('\n'));if(result.excluded?.length)message($('message').textContent+'\n'+result.excluded.map(item=>item.reason || 'Candidate needs review').join('\n'));}catch(error){message(error.message);}finally{busy=false;controls();}});
$('pause-jobs').addEventListener('click',()=>action('/api/audiobook/pause',{}));$('resume-jobs').addEventListener('click',()=>action('/api/audiobook/resume',{}));
viewControls();poll();

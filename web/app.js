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
  inventoryIntro.textContent=view==='files'?'Each row is a source file, including chapter tracks and companion files. Book grouping, online metadata matching and merging are later steps.':'Candidates are possible books assembled from source clues. Review their metadata, included tracks and order before a future merge.';
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
  if(selectedRow?.kind==='candidate')$('approval-reason').textContent=dirty ? 'Save the draft metadata before approving it.' : selectedRow.approval_reason || 'Metadata approval leaves track membership, completeness and order unverified.';
}
async function action(route, data) {
  if (busy || ended) return;
  busy=true; controls(); message();
  try { await request(route,data); lastKey=null; await refresh(true); }
  catch(error) { message(error.message); }
  finally { busy=false; controls(); }
}
function select(row, reset) {
  selectedPath=row.path; selectedRow=row;
  selectedLibrary=row.library || $('library').value;
  const candidate=row.kind==='candidate';
  $('details').hidden=false;
  $('details-heading').textContent=candidate?'Book candidate':'Selected file';
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
    $('candidate-facts').textContent='Track membership: Needs review · Recording completeness: Needs review · Track order: Needs review';
    $('member-count').textContent=`Included audio files — ${row.members.length}`;
    $('candidate-members').replaceChildren();
    for(const member of row.members){const tr=document.createElement('tr');for(const value of [member.order,`${member.track_title}\n${member.path}`,`${member.source_disc || 'Unknown'} / ${member.source_track || 'Unknown'}`,member.duration===null?'Unknown':`${member.duration.toFixed(2)} s`,member.order_evidence]){const td=document.createElement('td');td.textContent=String(value);tr.append(td);}$('candidate-members').append(tr);}
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
  controls();
  for (const element of $('inventory').children) element.setAttribute('aria-selected',String(element.dataset.path===row.path));
}
function renderRows() {
  const body=$('inventory'); body.replaceChildren();
  $('inventory-head').replaceChildren();const heading=document.createElement('tr');
  for(const label of view==='candidates'?['Title clue','Author / reader clues','Audio files','Review status']:['Type','Arrival','Existing title / filename clue','Existing author / artist clue','Preview status','Proposed destination']){const th=document.createElement('th');th.textContent=label;heading.append(th);}$('inventory-head').append(heading);
  for (const row of rows) {
    const tr=document.createElement('tr'); tr.dataset.path=row.path; tr.tabIndex=0;
    tr.setAttribute('aria-selected',String(row.path===selectedPath));
    const values=row.kind==='candidate'?[row.title_clue,row.artists.join('; ') || 'Unknown',row.members.length,row.status]:[row.kind,row.arrival ? 'Yes' : '',row.metadata.title || row.path.split(/[\\/]/).pop(),row.metadata.author || '',row.error ? `Read error · ${row.error.split(/\r?\n/)[0].slice(0,200)}`:row.preview.confidence,row.preview.path || 'Needs review'];
    for (const value of values) { const td=document.createElement('td'); td.textContent=value; tr.append(td); }
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
}
async function refresh(force=false) {
  if (ended) return false;
  const sequence=++refreshSequence;
  const library=$('library').value;
  const current=await request(`/api/state?library=${encodeURIComponent(library)}`);
  if (ended || sequence!==refreshSequence || $('library').value!==library) return false;
  state=current;
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
  if (force || key!==lastKey) {
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
  try {if(row.kind==='candidate'){const result=await request('/api/candidate/review',{library:selectedLibrary,id:row.id,revision:row.revision,review,approve:false});dirty=false;select({...result.row,path:result.row.id,kind:'candidate',library:selectedLibrary},true);}else await request('/api/review',{library:selectedLibrary || $('library').value,path:row.path,size:row.size,modified:row.modified,review});dirty=false;await refresh(true);message('Preview metadata saved. Source files unchanged.');}
  catch(error){message(error.message);}
  finally{busy=false;controls();}
});
$('approve-candidate').addEventListener('click',async()=>{const row=reviewRow || selectedRow;if(!row || row.kind!=='candidate' || dirty || busy || ended)return;busy=true;controls();try{const result=await request('/api/candidate/review',{library:selectedLibrary,id:row.id,revision:row.revision,review:row.review,approve:true});select({...result.row,path:result.row.id,kind:'candidate',library:selectedLibrary},true);await refresh(true);message('Candidate metadata approved. Tracks still require review; source files unchanged.');}catch(error){message(error.message);}finally{busy=false;controls();}});
$('shutdown').addEventListener('click',async()=>{
  if(busy || ended)return;busy=true;controls();message();
  try{await request('/api/shutdown',{});ended=true;clearConnectionNotice();clearTimeout(timer);$('status').textContent='Server stopping. Saved catalog and pending scans remain available on the next launch.';message('You can close this browser tab.');}
  catch(error){message(error.message);}
  finally{busy=false;controls();}
});
viewControls();poll();

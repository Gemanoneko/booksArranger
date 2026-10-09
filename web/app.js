'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="books-token"]').content;
let offset = 0, search = '', selectedPath = null, selectedRow = null, reviewRow = null, rows = [], lastKey = null;
let dirty = false, busy = false, polling = false, ended = false, timer = null, state = null;
const form = $('review-form');
const fields = ['original_language','title','author','series','number','genre','topic'];

async function request(route, data) {
  const options = {headers:{'X-Books-Token':token}, credentials:'same-origin', cache:'no-store'};
  if (data !== undefined) { options.method='POST'; options.headers['Content-Type']='application/json'; options.body=JSON.stringify(data); }
  const response = await fetch(route, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Local request failed (${response.status})`);
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
  $('details').hidden=false;
  $('source').textContent=row.path;
  $('reason').textContent=row.preview.reason;
  $('proposed').textContent=row.preview.path || 'No destination proposed until canonical metadata is reviewed.';
  $('method').textContent=row.metadata.method || 'Unavailable';
  $('language').textContent=row.metadata.edition_language || 'Unknown';
  $('series-clue').textContent=`${row.metadata.series || 'Unknown'} / ${row.metadata.number || 'Unknown'}`;
  $('genre-clue').textContent=row.metadata.genre || 'Unknown';
  $('notes').textContent=[...(row.metadata.notes || []),row.error].filter(Boolean).join(' · ');
  $('tags').textContent=JSON.stringify(row.metadata.tags || {},null,2);
  form.hidden=!['audiobook','ebook'].includes(row.kind) || !!row.error || !!row.missing;
  if (reset || !dirty) {
    for (const field of fields) form.elements.namedItem(field).value=row.review?.[field] || (field==='original_language' ? 'Unknown' : '');
    form.elements.namedItem('multi_author').checked=!!row.review?.multi_author;
    dirty=false;
    reviewRow=row;
    $('review-note').textContent='Saved only in the local catalog.';
  }
  for (const element of $('inventory').children) element.setAttribute('aria-selected',String(element.dataset.path===row.path));
}
function renderRows() {
  const body=$('inventory'); body.replaceChildren();
  for (const row of rows) {
    const tr=document.createElement('tr'); tr.dataset.path=row.path; tr.tabIndex=0;
    tr.setAttribute('aria-selected',String(row.path===selectedPath));
    const values=[row.kind,row.arrival ? 'Yes' : '',row.metadata.title || row.path.split(/[\\/]/).pop(),row.metadata.author || '',row.preview.confidence,row.preview.path || 'Needs review'];
    for (const value of values) { const td=document.createElement('td'); td.textContent=value; tr.append(td); }
    tr.addEventListener('click',()=>select(row,true));
    tr.addEventListener('keydown',event=>{if(event.key==='Enter' || event.key===' '){event.preventDefault();select(row,true);}});
    body.append(tr);
  }
  const selected=rows.find(row=>row.path===selectedPath);
  if (selected) select(selected,false);
  else { selectedRow=null; reviewRow=null; selectedPath=null; $('details').hidden=true; dirty=false; }
  $('empty').hidden=rows.length>0;
  $('empty').textContent=search ? 'No saved paths match this search.' : 'No files on this page yet. Start or resume scanning to build the inventory.';
  $('page').textContent=rows.length ? `Rows ${offset+1}–${offset+rows.length} · 100 per page` : '0 rows';
  $('previous').disabled=offset===0;
  $('next').disabled=rows.length<100;
}
async function refresh(force=false) {
  if (ended) return;
  const library=$('library').value;
  const current=await request(`/api/state?library=${encodeURIComponent(library)}`);
  if (ended || $('library').value!==library) return;
  state=current;
  $('version').textContent=`v${state.version} · local prototype`;
  $('root').textContent=`Source: ${state.root}`;
  const status=state.status;
  const activity=state.stopping ? 'Stopping…' : state.active_library ? `Scanning ${state.active_library}` : status.state;
  $('status').textContent=`${activity} · Catalog ${status.count} · Checked ${status.checked} · Reused ${status.reused} · Pending ${status.pending} · Errors ${status.errors}`;
  $('current').textContent=status.current || 'Choose a file to inspect existing metadata and its sorting preview.';
  if (form.elements.namedItem('genre').options.length===1) {
    for (const genre of state.genres) { const option=document.createElement('option');option.value=genre;option.textContent=genre;form.elements.namedItem('genre').append(option); }
  }
  controls();
  const key=JSON.stringify([library,offset,search,status.count,status.checked,status.state]);
  if (force || key!==lastKey) {
    const page=await request(`/api/inventory?library=${encodeURIComponent(library)}&offset=${offset}&search=${encodeURIComponent(search)}`);
    if (ended || $('library').value!==library) return;
    rows=page.rows;lastKey=key;renderRows();
  }
}
async function poll() {
  if (ended) return;
  if (!polling) {
    polling=true;
    try { await refresh(); }
    catch(error) { if(!ended)message('Local server unavailable. Saved scan progress remains in the catalog. '+error.message); }
    finally { polling=false; }
  }
  if (!ended) timer=setTimeout(poll,800);
}
$('start').addEventListener('click',()=>action('/api/scan/start',{library:$('library').value}));
$('resume').addEventListener('click',()=>action('/api/scan/resume',{library:$('library').value}));
$('stop').addEventListener('click',()=>action('/api/scan/stop',{library:state.active_library}));
$('library').addEventListener('change',()=>{offset=0;selectedPath=null;dirty=false;lastKey=null;refresh(true).catch(error=>message(error.message));});
$('search-form').addEventListener('submit',event=>{event.preventDefault();search=$('search').value;offset=0;refresh(true).catch(error=>message(error.message));});
$('previous').addEventListener('click',()=>{offset=Math.max(0,offset-100);refresh(true).catch(error=>message(error.message));});
$('next').addEventListener('click',()=>{offset+=100;refresh(true).catch(error=>message(error.message));});
form.addEventListener('input',()=>{if(!dirty)reviewRow=selectedRow;dirty=true;$('review-note').textContent='Unsaved local review.';});
form.addEventListener('submit',async event=>{
  event.preventDefault();if(!selectedRow || busy || ended)return;
  const row=reviewRow || selectedRow;const review={};for(const field of fields)review[field]=form.elements.namedItem(field).value.trim();
  review.multi_author=form.elements.namedItem('multi_author').checked;
  busy=true;controls();message();
  try {await request('/api/review',{library:$('library').value,path:row.path,size:row.size,modified:row.modified,review});dirty=false;await refresh(true);message('Preview metadata saved. Source files unchanged.');}
  catch(error){message(error.message);}
  finally{busy=false;controls();}
});
$('shutdown').addEventListener('click',async()=>{
  if(busy || ended)return;busy=true;controls();message();
  try{await request('/api/shutdown',{});ended=true;clearTimeout(timer);$('status').textContent='Server stopping. Saved catalog and pending scans remain available on the next launch.';message('You can close this browser tab.');}
  catch(error){message(error.message);}
  finally{busy=false;controls();}
});
poll();

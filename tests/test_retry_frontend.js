'use strict';
// v0.16.5 Retry for an audiobook job refused before it started: the real frontend against owned DOM and
// transport doubles. No server, no library, no deletion.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
class Element{
  constructor(id=''){this.id=id;this.value=id==='library'?'Audiobooks':'';this.children=[];this.handlers={};this.dataset={};this.attrs={};this.options=[{}];this.textContent='';this.hidden=false;this.disabled=false;this.open=false;this.title='';this.classes=new Set();
    this.classList={toggle:(key,on)=>{const add=on===undefined?!this.classes.has(key):!!on;if(add)this.classes.add(key);else this.classes.delete(key);return add;},contains:key=>this.classes.has(key),add:key=>this.classes.add(key),remove:key=>this.classes.delete(key)};}
  addEventListener(key,handler){this.handlers[key]=handler;}
  setAttribute(key,value){this.attrs[key]=String(value);}
  getAttribute(key){return Object.hasOwn(this.attrs,key)?this.attrs[key]:null;}
  removeAttribute(key){delete this.attrs[key];if(key==='value')this.value=null;}
  append(...items){for(const item of items){item.parentElement?.removeChild(item);item.parentElement=this;this.children.push(item);}}
  after(){}
  removeChild(item){this.children=this.children.filter(child=>child!==item);item.parentElement=null;}
  replaceChildren(...items){for(const child of this.children)child.parentElement=null;this.children=[];this.append(...items);}
  insertBefore(item,before){item.parentElement?.removeChild(item);item.parentElement=this;const index=this.children.indexOf(before);this.children.splice(index<0?this.children.length:index,0,item);}
  contains(item){return this===item || this.children.some(child=>child.contains?.(item));}
  querySelector(){return new Element();}
  querySelectorAll(){return [];}
  focus(){document.activeElement=this;}
  scrollIntoView(){}
  get nextElementSibling(){return this.parentElement?.children[this.parentElement.children.indexOf(this)+1];}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
const fieldNodes=new Map();get('review-form').elements={namedItem:key=>{if(!fieldNodes.has(key))fieldNodes.set(key,new Element(key));return fieldNodes.get(key);}};
get('candidate-members').parentElement=new Element();get('manual-review').append(get('review-form'),get('candidate-details'),get('track-review'));get('metadata-inspector').append(get('inspector-sections'),get('folder-list'));
// The static index.html structure: the Retry block sits inside the automatic result section.
get('automatic-result').append(get('automatic-result-status'),get('automatic-reasons'),get('retry-block'),get('automatic-sources'));get('retry-block').append(get('retry-job'),get('retry-note'));
const document={activeElement:null,getElementById:get,querySelector:()=>({content:'fixture-token'}),querySelectorAll:()=>[],createElement:tag=>new Element(tag)};
const calls=[];let backend={version:'fixture',root:'fixture-root',genres:[],status:{state:'idle',count:0,checked:0,reused:0,pending:0,errors:0},active_library:null,automatic_processing:{state:'Idle',phase:'discovery',can_start:true,can_stop:false,research:{researching:0,waiting:0,held:0},current:null,reason:'',run_id:null},audiobook_jobs:{state:'Needs attention',queued:0,failed:1,approved_total:0,converted_total:0}};
let inventoryRows=[],retryOverride=null,inventoryOverride=null;
async function fixtureFetch(route,options){calls.push({route,options});const data=options.body?JSON.parse(options.body):undefined;
  if(route==='/api/audiobook/retry'){if(retryOverride)return retryOverride(data);return {ok:true,status:202,json:async()=>({job_id:data.job_id,requeued:true})};}
  if(route.startsWith('/api/inventory') && inventoryOverride)return inventoryOverride();let result={};if(route.startsWith('/api/state'))result=backend;else if(route.startsWith('/api/inventory'))result={rows:inventoryRows,total:inventoryRows.length};else if(route==='/api/inspect')result={inspector:{sections:[],source_directories:[]}};
  return {ok:true,json:async()=>result};}
const context=vm.createContext({document,console,URL,Intl,Date,JSON,location:{origin:'http://127.0.0.1:5210'},setTimeout:()=>0,clearTimeout(){},fetch:fixtureFetch});
const app=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8').replace(/controls\(\);\s*viewControls\(\);poll\(\);\s*$/,'');vm.runInContext(app,context);
function run(code){return vm.runInContext(code,context);}
const JOB_REASON='Working cleanup requires attention: Legacy attempt still contains working inputs';
const NOT_YET='Working files from an earlier attempt are still present. Retry after they are cleared.';
const READY='Check this book again and queue its audiobook job.';
function blocked(overrides={},job={}){
  const row={id:'cand-a',path:'cand-a',kind:'candidate',library:'Audiobooks',revision:4,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],title_clue:'Название книги',conflicts:[],coverage:'',companions:[],artists:[],members:[],track_order:[],included:[],
    review:{title:'Вечный зов'},review_context:{},status:'Output needs attention',automatic:null,
    creation:{status:'Output needs attention',can_create:false,chapters_available:false,reasons:['Audiobook job already exists; inspect its current status'],job:{job_id:'job-a',state:'Output needs attention',stage:'queued',reason:JOB_REASON,retry:{allowed:true,reason:''},...job}},...overrides};
  return row;
}
function queued(row){return {...row,status:'Queued',creation:{...row.creation,status:'Queued',job:{job_id:row.creation.job.job_id,state:'Queued',stage:'queued',reason:'Queued again by Retry.'}}};}
function show(row){context.fixture=row;run('state=state||'+JSON.stringify(backend)+';rows=[fixture];select(fixture,selectedPath!==fixture.path)');}
const button=get('retry-job'),note=get('retry-note'),block=get('retry-block');
(async()=>{
  run('state='+JSON.stringify(backend));
  // C1: the status line leads with the job's own reason, not "Audiobook job already exists".
  const row=blocked();assert.equal(run('candidateStatus('+JSON.stringify(row)+')'),'Needs attention — '+JOB_REASON);
  assert.equal(run('candidateStatus('+JSON.stringify(blocked({},{reason:''}))+')'),'Needs attention — Audiobook job already exists; inspect its current status','positive control: no job reason falls back as before');
  assert.equal(run('candidateStatus('+JSON.stringify(blocked({creation:{status:'Audiobook created',reasons:[],job:{job_id:'job-a',state:'Audiobook created',reason:'old note'}},status:'Audiobook created',audiobook_ready:true}))+')'),'Audiobook Ready','a finished job never leads with its reason');
  show(row);assert.equal(get('automatic-result-status').textContent,'Needs attention — '+JOB_REASON);assert.equal(get('output-status').textContent,'Needs attention — '+JOB_REASON);

  // State 2, ready: one primary button, accessible name starts with the visible label, no note.
  assert.equal(block.hidden,false);assert.equal(button.disabled,false);assert.equal(button.textContent,'Retry');assert.equal(button.title,READY);
  assert.equal(button.getAttribute('aria-label'),'Retry: Вечный зов');assert.equal(button.getAttribute('aria-disabled'),null);assert.equal(note.hidden,true);assert.equal(note.textContent,'');
  assert.doesNotMatch(button.title,/Source files stay untouched/);
  // State 1, hidden: no retry data, or a job that no longer needs attention.
  show(blocked({},{retry:undefined}));assert.equal(block.hidden,true);assert.equal(note.hidden,true);
  show(queued(row));assert.equal(block.hidden,true);
  show(blocked({creation:undefined}));assert.equal(block.hidden,true);
  // State 3, unavailable: disabled, tooltip and visible note carry the same reason; it enables within a poll.
  show(blocked({},{retry:{allowed:false,reason:NOT_YET}}));assert.equal(block.hidden,false);assert.equal(button.disabled,true);assert.equal(button.title,NOT_YET);assert.equal(note.textContent,NOT_YET);assert.equal(note.hidden,false);assert.equal(note.classList.contains('retry-refused'),false);
  const before=note.textContent;show(blocked({},{retry:{allowed:false,reason:NOT_YET}}));assert.equal(note.textContent,before);
  show(row);assert.equal(button.disabled,false);assert.equal(note.hidden,true);
  // States 4 and 5, busy and offline, in the specified resolution order.
  run('busy=true;controls()');assert.equal(button.disabled,true);assert.equal(button.title,'Another operation is in progress.');assert.equal(note.textContent,'Another operation is in progress.');
  run('recoveryDisconnected=true;controls()');assert.equal(button.title,'Local server unavailable.','offline wins over busy');assert.equal(note.textContent,'Local server unavailable.');
  run('busy=false;recoveryDisconnected=false;ended=true;controls()');assert.equal(button.disabled,true);assert.equal(button.title,'Local server unavailable.');
  run('ended=false;controls()');assert.equal(button.disabled,false);assert.equal(note.hidden,true);

  // States 7 and 2 -> 1: Retrying keeps focus, one request only, success hides the block and focuses the heading.
  let answer;retryOverride=()=>new Promise(resolve=>{answer=resolve;});get('message').textContent='';
  show(row);document.activeElement=button;const sent=calls.length;const retrying=run('retryJob()');
  assert.equal(button.textContent,'Checking…');assert.equal(button.getAttribute('aria-disabled'),'true');assert.equal(button.disabled,false,'pending keeps keyboard focus');
  assert.equal(button.title,'Checking this book…');assert.equal(note.textContent,'Checking this book…');assert.equal(button.getAttribute('aria-label'),'Checking…: Вечный зов');
  button.handlers.click();await run('retryJob()');
  const posts=calls.slice(sent).filter(call=>call.route==='/api/audiobook/retry');assert.equal(posts.length,1,'double activation sends one request');
  assert.deepEqual(JSON.parse(posts[0].options.body),{library:'Audiobooks',id:'cand-a',revision:4,job_id:'job-a'});assert.equal(posts[0].options.headers['X-Books-Token'],'fixture-token');
  assert.equal(document.activeElement,button);
  inventoryRows=[queued(row)];answer({ok:true,status:202,json:async()=>({job_id:'job-a',requeued:true})});await retrying;
  // v0.16.12: accepted means a disabled "Queued", never an enabled Retry again, whatever an older list says.
  assert.equal(block.hidden,false);assert.equal(button.textContent,'Queued');assert.equal(button.disabled,true);
  assert.equal(document.activeElement,get('details-heading'),'focus moves to the panel heading');
  assert.equal(get('automatic-result-status').textContent,'Queued — runs next');assert.equal(get('message').textContent,'','feedback never uses the top-of-page message');
  assert.equal(run('busy'),false);

  // State 8, refused: the server's message verbatim, warning style; the button follows fresh data.
  run("pressed.clear()");  // v0.16.12: the accepted press above is remembered; this scenario starts fresh
  const refused="This book's status changed. Check the updated status above.";retryOverride=async()=>({ok:false,status:409,json:async()=>({error:refused})});
  show(row);document.activeElement=button;inventoryRows=[blocked({},{retry:{allowed:false,reason:NOT_YET}})];await run('retryJob()');
  assert.equal(note.textContent,refused);assert.equal(note.hidden,false);assert.equal(note.classList.contains('retry-refused'),true);
  assert.equal(button.disabled,true);assert.equal(button.title,NOT_YET);assert.notEqual(document.activeElement,get('details-heading'));assert.equal(get('message').textContent,'');
  // Selecting another book clears this book's note.
  show(blocked({id:'cand-b',path:'cand-b'},{job_id:'job-b'}));assert.equal(note.textContent,'');assert.equal(note.hidden,true);

  // State 9 (v0.16.8), no reply: the server is asked whether the press landed; here it did not, so the button
  // comes back with a plain message and no connection alarm.
  retryOverride=async()=>{throw new TypeError('Failed to fetch');};show(row);inventoryRows=[row];await run('retryJob()');
  assert.equal(note.textContent,'Retry did not go through. Try again.');assert.equal(run('recoveryDisconnected'),false);
  assert.equal(button.disabled,false);

  // Click, then switch book: the other book shows Busy, never Retrying, and no stale note arrives later.
  let late;retryOverride=()=>new Promise(resolve=>{late=resolve;});show(row);inventoryRows=[row];document.activeElement=button;const switching=run('retryJob()');
  const other=blocked({id:'cand-b',path:'cand-b',title_clue:'Другая книга',review:{title:'Другая книга'}},{job_id:'job-b'});show(other);
  assert.equal(button.textContent,'Retry');assert.equal(button.disabled,true);assert.equal(button.title,'Another operation is in progress.');assert.equal(button.getAttribute('aria-label'),'Retry: Другая книга');
  inventoryRows=[other];late({ok:false,status:409,json:async()=>({error:refused})});await switching;
  assert.notEqual(note.textContent,refused,'no stale note from the other book');assert.equal(button.disabled,false);assert.notEqual(document.activeElement,get('details-heading'));
  retryOverride=null;

  // Focus on Retry does not freeze the status line; focus elsewhere in the section still does (positive control).
  show(row);document.activeElement=button;const changed=blocked({},{reason:'A newer saved reason'});context.fixture=changed;run('rows=[fixture];select(fixture,false)');
  assert.equal(get('automatic-result-status').textContent,'Needs attention — A newer saved reason');
  const link=new Element('fixture-link');get('automatic-sources').append(link);document.activeElement=link;context.fixture=blocked({},{reason:'Hidden while reading sources'});run('rows=[fixture];select(fixture,false)');
  assert.equal(get('automatic-result-status').textContent,'Needs attention — A newer saved reason');document.activeElement=null;

  // v0.16.6: after 202 the panel shows the requeued job at once, and no book list requested before the answer repaints it.
  run("pressed.clear()");retryOverride=null;show(row);inventoryRows=[row];let fresh;inventoryOverride=()=>new Promise(resolve=>{fresh=resolve;});document.activeElement=button;
  const accepted=run('retryJob()');await new Promise(resolve=>setImmediate(resolve));
  assert.equal(get('automatic-result-status').textContent,'Queued — runs next','queued before any book list arrives');
  assert.equal(block.hidden,false);assert.equal(button.textContent,'Queued');assert.equal(button.disabled,true,'never an enabled Retry again');
  assert.equal(run('rows.find(item=>item.path==="cand-a").creation.job.state'),'Queued','the list no longer holds the needs-attention copy');
  fresh({ok:true,json:async()=>({rows:[queued(row)],total:1})});inventoryOverride=null;await accepted;assert.equal(get('automatic-result-status').textContent,'Queued — runs next');
  // v0.16.12: a list from before the press landed (the needs-attention copy) never repaints it as an enabled Retry.
  show(row);assert.equal(get('automatic-result-status').textContent,'Queued — runs next');assert.equal(button.textContent,'Queued');assert.equal(button.disabled,true);
  context.fixture=row;run('rows=[fixture];renderRows(true);controls()');const stale=get('inventory').children[0].children[5].children[0].children[0];
  assert.equal(stale.textContent,'Queued');assert.equal(stale.disabled,true);
  // Only the server's explicit answer replaces it: here, its own queue-next record says the book already ran.
  const ran=blocked({},{readmission:{accepted:true,queued_next:false,kind:'retry',state:'admitted'}});show(ran);assert.equal(button.textContent,'Retry');assert.equal(button.disabled,false);
  // The guard itself: a book list requested before Retry was answered is dropped even if it is the latest request.
  show(row);inventoryRows=[row];let old;inventoryOverride=()=>new Promise(resolve=>{old=resolve;});const pending=run('refresh(true)');await new Promise(resolve=>setImmediate(resolve));
  context.fixture=queued(row);run('retryEpoch++;rows=[fixture];select(fixture,false)');old({ok:true,json:async()=>({rows:[row],total:1})});inventoryOverride=null;
  assert.equal(await pending,false);assert.match(get('automatic-result-status').textContent,/^Queued/);
  run("pressed.clear()");show(queued(row));inventoryRows=[row];assert.equal(await run('refresh(true)'),true,'positive control: a list requested after the answer is painted');assert.match(get('automatic-result-status').textContent,/^Needs attention/);
  // A 409 also asks for a fresh book list, and its message names no missing action.
  retryOverride=async()=>({ok:false,status:409,json:async()=>({error:refused})});show(row);inventoryRows=[row];const sentBefore=calls.length;const epoch=run('retryEpoch');await run('retryJob()');
  assert.equal(run('retryEpoch'),epoch+1);assert.ok(calls.slice(sentBefore).some(call=>call.route.startsWith('/api/inventory')));assert.doesNotMatch(note.textContent,/Refresh/);retryOverride=null;

  // C2: the automatic wait no longer says "Retry".
  context.fixture={...blocked({creation:{status:'Needs metadata review',can_create:false,reasons:[]},status:''}),automatic:{state:'Waiting for source',reasons:[],sources:[],retry_at:1896901200}};run('automaticResultKey=null;renderAutomaticResult(fixture)');
  assert.match(get('automatic-retry').textContent,/^Automatic retry after .*; Start to continue$/);assert.doesNotMatch(get('automatic-retry').textContent,/Retry available/);

  // Static page contract: placement, primary style, the note, and the pending style.
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
  assert.match(html,/<ul id="automatic-reasons"><\/ul><div id="retry-block" hidden><div class="toolbar"><button id="retry-job" type="button" aria-describedby="retry-note" disabled>Retry<\/button><\/div><p id="retry-note" class="field-help" role="status" aria-live="polite" hidden><\/p><\/div><p id="automatic-result-help"/);
  assert.doesNotMatch(html,/id="retry-job"[^>]*class=/,'Retry is a primary button');
  assert.match(css,/#retry-job\{min-height:32px;min-width:96px\}/);assert.match(css,/#retry-job\[aria-disabled=true\],#retry-job\[aria-disabled=true\]:hover,#retry-job\[aria-disabled=true\]:active\{background:var\(--disabled\);color:var\(--disabled-text\);border-color:var\(--border\);cursor:default\}/);
  assert.match(css,/#retry-note\.retry-refused\{color:var\(--warning\)\}/);

  // The desktop layer disables Retry during Quit (state 6); a running window leaves it alone (positive control).
  async function desktop(status,id='retry-job'){
    const dnodes=new Map(),dget=id=>{if(!dnodes.has(id))dnodes.set(id,new Element(id));return dnodes.get(id);};
    const ddoc={getElementById:dget,querySelector:selector=>({'header':dget('header'),'#shutdown':dget('shutdown'),'#version':dget('version')})[selector] || null,createElement:tag=>new Element(tag)};
    const api={status:async()=>status,quit:async()=>({}),checkUpdates:async()=>({}),downloadUpdate:async()=>({}),installUpdate:async()=>({}),onStatus(){}};
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/desktop-ui.js'),'utf8'),vm.createContext({window:{booksDesktop:api},document:ddoc,setInterval:()=>0,console}));
    await new Promise(resolve=>setImmediate(resolve));return dget(id);
  }
  assert.equal((await desktop({quit:'requested',desktop:{phase:'finishing'},update:{phase:'idle'}})).disabled,true);
  assert.equal((await desktop({quit:'none',desktop:{phase:'running'},update:{phase:'idle'}})).disabled,false);
  assert.equal((await desktop({quit:'none',desktop:{phase:'unavailable',idle:false},update:{phase:'idle'}})).disabled,false,'a slow desktop status read must not disable Retry between book-list polls');
  assert.equal((await desktop({quit:'none',desktop:{phase:'unavailable',idle:false},update:{phase:'idle'}},'retry-all')).disabled,false,'a slow desktop status read must not disable Retry all');
  assert.equal((await desktop({quit:'none',desktop:{phase:'finishing'},update:{phase:'idle'}},'retry-all')).disabled,true,'actual finish-then-quit still disables Retry all');
  console.log('PASS retry block states, C1 job reason, C2 wording, request/feedback/focus, book scoping, desktop Quit');
})().catch(error=>{console.error(error);process.exitCode=1;});

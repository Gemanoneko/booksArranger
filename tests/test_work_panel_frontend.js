'use strict';
// 0.30.0 (Judy's Docs/BooksArranger_0.30.0_UX.md, section 6): the jobs panel drawn from the engine's work (books-work-v1).
// The acceptance checks the page can hold by itself: one sentence in three places, every row, split counts, freshness, the
// unread line, the backlog group, short jobs and the automatic wait. The real renderJobs against owned DOM doubles.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
class Element{
  constructor(id=''){this.id=id;this.value=id==='library'?'Audiobooks':'';this.children=[];this.handlers={};this.dataset={};this.attrs={};this.options=[{}];this.textContent='';this.hidden=false;this.disabled=false;this.title='';this.classes=new Set();
    this.classList={toggle:(key,on)=>{const add=on===undefined?!this.classes.has(key):!!on;if(add)this.classes.add(key);else this.classes.delete(key);return add;},contains:key=>this.classes.has(key)};}
  set className(value){this.classes=new Set(String(value).split(/\s+/).filter(Boolean));}
  get className(){return [...this.classes].join(' ');}
  addEventListener(key,handler){this.handlers[key]=handler;}
  setAttribute(key,value){this.attrs[key]=String(value);if(key==='value')this.value=Number(value);}
  getAttribute(key){return Object.hasOwn(this.attrs,key)?this.attrs[key]:null;}
  hasAttribute(key){return key==='value'?this.value!==null&&this.value!==undefined&&this.value!=='':Object.hasOwn(this.attrs,key);}
  removeAttribute(key){delete this.attrs[key];if(key==='value')this.value=null;}
  append(...items){for(const item of items){item.parentElement?.removeChild(item);item.parentElement=this;this.children.push(item);}}
  removeChild(item){this.children=this.children.filter(child=>child!==item);item.parentElement=null;}
  replaceChildren(...items){for(const child of this.children)child.parentElement=null;this.children=[];this.append(...items);}
  insertBefore(item,before){item.parentElement?.removeChild(item);item.parentElement=this;const index=before?this.children.indexOf(before):-1;this.children.splice(index<0?this.children.length:index,0,item);}
  contains(item){return this===item || this.children.some(child=>child.contains?.(item));}
  querySelector(){return new Element();}
  querySelectorAll(){return [];}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
get('review-form').elements={namedItem:()=>new Element()};get('candidate-members').parentElement=new Element();
const document={activeElement:null,getElementById:get,querySelector:()=>({content:'fixture'}),querySelectorAll:()=>[],createElement:tag=>{const element=new Element();element.tag=tag;if(tag==='progress')element.value=null;return element;}};
const context=vm.createContext({document,console,URL,location:{origin:'http://127.0.0.1:5210'},setTimeout:()=>0,clearTimeout(){},fetch:async()=>({ok:true,json:async()=>({})})});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8').replace(/viewControls\(\);poll\(\);\s*$/,''),context);
function run(code){return vm.runInContext(code,context);}
const NOW=Date.now(),ago=ms=>NOW-ms;
const jobsBase={state:'Running',approved_total:40,converted_total:12,queued:0,failed:0,attention_counts:{other:329},candidate_total:50,not_approved_total:3};
function show(work,jobs={},extra={}){
  context.fixture={audiobook_jobs:{...jobsBase,...jobs},work:{rows:[],waiting:[],counts:{},unread:[],snapshot_age_ms:0,refreshing:false,...work},...extra};
  run('state=fixture;renderJobs()');return get('jobs-rows').children;
}
const ids=list=>list.map(item=>item.dataset.id);
const plain=value=>JSON.parse(JSON.stringify(value));
const conversion={id:'conversion:j1',kind:'conversion',subject:'Dune',job_id:'j1',book_id:'b1',step:'encoding',done:100,total:1000,unit:'seconds',state:'running',started:ago(60000)};

// 1 and 2. The Brom replay: a Retry cleanup behind a conversion with 4 more queued. The row hint, the Waiting line and the
// queue strip end with the same sentence, which names the whole queue.
const blocker={kind:'jobs',cause:'conversion_queue',title:null,book_id:null,count:5};
run('queueState='+JSON.stringify({queued:[{id:'q1',book_id:'b9',action:'cleanup',title:'Foo',position:1,blocker}],running:null,outcomes:[]}));
show({rows:[conversion],waiting:[{id:'action:q1',kind:'action',label_key:'cleanup',subject:'Foo',book_id:'b9',blocker,ahead:0}],counts:{queued_conversions:4,actions_waiting:1}});
const sentence='It runs when the whole conversion queue (5 books) finishes.';
const hint=run("queueHint({id:'b9',kind:'candidate',title_clue:'Foo'})");assert.equal(hint,'Retry cleanup queued. '+sentence);
const wait=get('jobs-wait').children[0];assert.equal(wait.children[0].children[0].children.map(item=>item.textContent).join(''),'Retry cleanup: Foo');
assert.equal(wait.children[0].children[1].textContent,sentence);assert.equal(wait.children[0].children[1].title,'Cleanup never runs beside a conversion, so it waits for every queued book.');
run("view='candidates';filters[view]='output_attention';renderAttentionGroups()");assert.equal(get('queue-line').textContent,'1 action waiting. '+sentence);
// Every cause in 2.2: the row tail and the Waiting tail are one string.
for(const cause of ['own_conversion','own_cleanup','conversion','conversion_queue','queue_paused','cleanup_running','cleanup_waiting','cleanup_paused','checking','unknown','action','operation','source_check','retry_run','approve_run','book','scan','automatic','loading']){
  const b={kind:'jobs',cause,title:'Foo',book_id:'b2',count:3};
  run('queueState='+JSON.stringify({queued:[{id:'q1',book_id:'b9',action:'retry',title:'Bar',position:1,blocker:b}],running:null,outcomes:[]}));
  context.item={id:'action:q1',kind:'action',label_key:'retry',subject:'Bar',book_id:'b9',blocker:b,ahead:0};
  const row=run("queueHint({id:'b9',kind:'candidate'})").replace(/^Retry queued\. /,''),line=run('waitingLines(item,workOf())[2]');
  assert.equal(row,line,cause+': the same sentence');
  if(!['unknown','operation'].includes(cause))assert.notEqual(line,'It runs when the app is free.',cause+': a known cause is never the fallback');
}
run('queueState={queued:[],running:null,outcomes:[]}');

// 4 and 5. Every row, none folded; the status line counts them.
const five=[conversion,{id:'series',kind:'series',subject:'Мухи',state:'running',started:ago(5000)},{id:'finished_check',kind:'finished_check',state:'running',started:ago(5000)},
  {id:'scan',kind:'scan',subject:'Audiobooks',step:'scanning',state:'running',started:ago(5000)},{id:'research',kind:'research',subject:'Foo',step:'researching',state:'running',started:ago(5000)}];
let rows=show({rows:five});assert.equal(rows.length,5,'5 rows, none folded');assert.match(get('jobs-status').textContent,/^5 tasks running · /);
assert.deepEqual(ids(rows),five.map(row=>row.id),'scan and research both show, in the engine order');
// 6. A running queued action beside a conversion.
rows=show({rows:[conversion,{id:'action:q7',kind:'action',label_key:'delete',subject:'Bar',book_id:'b7',state:'running',started:ago(3000)}]});
assert.deepEqual(ids(rows),['conversion:j1','action:q7']);assert.match(get('jobs-status').textContent,/^2 tasks running · /);

// 7. Counts: three paused cleanups and one queued conversion are never "4 books waiting to convert".
const paused=n=>({id:'cleanup:p'+n,kind:'cleanup',subject:'Paused '+n,job_id:'p'+n,step:'originals',done:1,total:9,unit:'files',state:'paused',started:ago(90000)});
rows=show({rows:[paused(1),paused(2),paused(3)],waiting:[{id:'conversions',kind:'conversions',subject:'Next book',count:1}],counts:{queued_conversions:1,cleanups_paused:3}},{state:'Paused',queued:4});
assert.match(get('jobs-status').textContent,/^Paused · 1 book waiting to convert · Cleanup paused for 3 books · 329 need attention · /);
assert.doesNotMatch(get('jobs-status').textContent,/4 books/);assert.equal(rows.length,3);assert.equal(get('jobs-wait').children.length,1);
show({counts:{cleanups_paused:3,cleanups_waiting:2}},{state:'Paused'});assert.match(get('jobs-status').textContent,/· Cleanup paused for 3 books, waiting for 2 · /);
show({counts:{cleanups_waiting:2}},{state:'Running'});assert.match(get('jobs-status').textContent,/^Nothing running · Cleanup waiting for 2 books · /);
show({counts:{actions_waiting:3,retry_checks_waiting:2}});assert.match(get('jobs-status').textContent,/ · 3 actions waiting · 329 need attention · 12 converted out of 40 approved books · 2 waiting for retry checks$/);

// 8. Counts behind: the cue (muted from 10 s, warning from 30 s), the (as of …) suffixes, Refreshing… only while refreshing.
run('receivedAt.set("Audiobooks",'+NOW+')');
rows=show({rows:[conversion],snapshot_age_ms:45000,refreshing:false},{},{needs_you_only:false});run('renderFreshness('+NOW+')');
const cue=get('jobs-fresh');assert.equal(cue.textContent,'Counts updated 45 s ago');assert.equal(cue.hidden,false);assert.equal(cue.classes.has('behind'),true,'warning color from 30 s');
const asOf=run('wallClock('+(NOW-45000)+')');assert.match(get('jobs-status').textContent,new RegExp('12 converted out of 40 approved books \\(as of '+asOf+'\\)'));
assert.equal(cue.title,`Need attention, converted and candidate counts were last computed at ${asOf}. The running jobs below are live.`);
assert.equal(get('book-candidate-counts').textContent,`50 book candidates found · 3 not approved (as of ${asOf})`);
assert.equal(rows[0].children[2].children[1].hidden,false,'positive control: a live row keeps its clock while the counts are behind');
show({snapshot_age_ms:45000,refreshing:true});run('renderFreshness('+NOW+')');assert.equal(cue.textContent,'Counts updated 45 s ago. Refreshing…');
show({snapshot_age_ms:20000});run('renderFreshness('+NOW+')');assert.equal(cue.textContent,'Counts updated 20 s ago');assert.equal(cue.classes.has('behind'),false,'muted under 30 s');
assert.doesNotMatch(get('jobs-status').textContent,/as of/,'no suffix under 30 s');
show({snapshot_age_ms:9000});run('renderFreshness('+NOW+')');assert.equal(cue.hidden,true,'under 10 s: no cue');
show({snapshot_age_ms:150000});run('renderFreshness('+NOW+')');assert.equal(cue.textContent,'Counts updated 2 min ago');
show({snapshot_age_ms:4000000});run('renderFreshness('+NOW+')');assert.equal(cue.textContent,'Counts updated over 1 h ago');
show({snapshot_age_ms:null});run('renderFreshness('+NOW+')');assert.equal(cue.hidden,true,'the engine cannot tell: hidden');
// Waiting for you, behind.
show({snapshot_age_ms:45000},{},{needs_you_only:true});assert.equal(get('jobs-you-line').children.map(item=>item.textContent).join(''),`Waiting for you: 329 books need attention (as of ${asOf}). The app can't do more until you review them.`);

// 9. Unread: one failed poll never flashes; 3 s or more names the source, and an empty panel does not claim idle.
run('unreadSince.clear()');show({unread:['workers']},{},{needs_you_only:true});
assert.equal(get('jobs-unread').hidden,true,'first poll: nothing');assert.equal(get('jobs-idle').textContent,'Nothing running.');
run('unreadSince.set("workers",'+(NOW-4000)+')');show({unread:['workers','jobs']},{},{needs_you_only:true});run('unreadSince.set("jobs",'+(NOW-4000)+')');show({unread:['workers','jobs']},{},{needs_you_only:true});
assert.equal(get('jobs-unread').hidden,false);assert.equal(get('jobs-unread').textContent,'Could not read just now: background lookups and repairs, conversion and cleanup. Some work may be missing below.');
assert.equal(get('jobs-idle').textContent,'Nothing running that could be read.');assert.equal(get('jobs-you').hidden,true,'no absence claimed while a source is unread');
show({unread:[]});assert.equal(get('jobs-unread').hidden,true,'read again: the line goes');

// 10. Backlog: 100 waiting cleanups are one grouped item; 4 are four items.
const waiting=n=>Array.from({length:n},(_,i)=>({id:'cleanup:w'+i,kind:'cleanup',subject:'Waiting '+i,book_id:'w'+i,job_id:'w'+i}));
show({waiting:waiting(100).slice(0,50),counts:{cleanups_waiting:100}});
assert.equal(get('jobs-wait').children.length,1);assert.equal(get('jobs-wait').children[0].children[0].children[0].children.map(item=>item.textContent).join(''),'Cleanup waiting: 100 books');
show({waiting:waiting(4),counts:{cleanups_waiting:4}});assert.equal(get('jobs-wait').children.length,4);

// 12. A job under 1 s never creates a row; a blocker row is drawn at once (1.4, check 3).
rows=show({rows:[{...conversion,started:Date.now()}]});assert.equal(rows.length,0,'under 1 s: no row');
run('queueState='+JSON.stringify({queued:[{id:'q1',book_id:'b9',action:'retry',title:'Bar',position:1,blocker:{kind:'jobs',cause:'conversion',title:'Dune',book_id:'b1'}}],running:null,outcomes:[]}));
rows=show({rows:[{...conversion,started:Date.now()}]});assert.deepEqual(ids(rows),['conversion:j1'],'the row a sentence quotes is drawn even in its first second');
run('queueState={queued:[],running:null,outcomes:[]}');

// 13. O-r2-2: automatic processing between tries is a wait, named, and the panel does not read as idle.
show({waiting:[{id:'automatic',kind:'automatic',label_key:'automatic_waiting'}]},{},{automatic_processing:{state:'Running',phase:'waiting'}});
assert.equal(get('jobs-wait').children[0].children[0].children[1].textContent,'Waiting between tries. It continues by itself.');
assert.equal(run("blockerSentence({kind:'automatic',cause:'automatic'}).text"),"It can't run while automatic processing waits between tries. Press Stop automatic processing to run it now.");
// Section 7 (Sergei's answer 6 = leave): an Author unclear book saved with a blank author leaves Needs attention, and the Save
// line says so; with an author, or still asking, it adds nothing.
context.before={id:'a1',kind:'candidate',title_clue:'Клуб',ask:{kind:'author_unclear',why:'two_people'}};
context.after={id:'a1',kind:'candidate',review:{title:'Клуб',author:'',canonical_author:''}};
assert.equal(run('savedFieldsLine({},{})+leftAttentionLine(before,after)'),'Saved. «Клуб» left Needs attention. Its author is still blank.');
context.after.review.author='Паланик Чак';assert.equal(run('leftAttentionLine(before,after)'),'','an author entered: nothing to add');
context.after={...context.before};assert.equal(run('leftAttentionLine(before,after)'),'','still asking: it stays');
context.before={id:'a2',kind:'candidate',ask:{kind:'title_author',why:'title_missing'}};context.after={id:'a2',kind:'candidate',review:{}};assert.equal(run('leftAttentionLine(before,after)'),'','positive control: only an Author unclear book');
// Futaba's 0.30.0 QA A delta, 2: an Approve counts each pass over its files, named in the conversion steps' "Step N of 4"
// form so a count that starts again reads as the next step; with no pass reported the row reads as before.
assert.equal(run('workStep({kind:"action",label_key:"approve",step:"reading",state:"running"},false)'),'Step 1 of 4 - Reading each file');
assert.equal(run('workStep({kind:"action",label_key:"approve",step:"covers",state:"running"},false)'),"Step 2 of 4 - Reading each file's cover");
assert.equal(run('workStep({kind:"action",label_key:"approve",step:"checking",state:"running"},false)'),'Step 3 of 4 - Checking each file');
assert.equal(run('workStep({kind:"action",label_key:"approve",step:"confirming",state:"running"},false)'),'Step 4 of 4 - Checking each file again');
assert.equal(run('workStep({kind:"action",label_key:"approve",state:"running"},false)'),'Saving the approval','no pass reported: as before');
const approving={id:'action:q6',kind:'action',label_key:'approve',subject:'The Orchard Ledger',step:'confirming',total:6,unit:'files',state:'running',started:ago(5000)};
for(const [done,percent] of [[5,83],[6,100]]){
  const [row]=show({rows:[{...approving,done}]});
  assert.equal(row.children[0].children[1].textContent,done+' of 6 files');
  assert.equal(row.children[1].value,percent);
  assert.equal(row.children[1].getAttribute('aria-valuetext'),'Step 4 of 4 - Checking each file again, '+done+' of 6 files');
}
const [finalizing]=show({rows:[{...conversion,done:conversion.total}]});
assert.equal(finalizing.children[1].hasAttribute('value'),false);
assert.match(finalizing.children[1].getAttribute('aria-valuetext'),/Finalizing conversion/);
console.log('PASS 0.30.0 work panel: one sentence in three places, every row, split counts, freshness, unread, backlog, short jobs, automatic wait');

'use strict';
// v0.16.6 progress rows (Docs/BooksArranger_ProgressRows_Spec.md): the real renderJobs against owned DOM doubles.
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
const NOW=Date.now();
// 0.30.0 (Judy's spec 1): the engine's work rows (books-work-v1) are the only source of Running rows, drawn in the order sent.
function render(jobs={},rows=[],counts={}){context.fixture={audiobook_jobs:{state:'Running',approved_total:2,converted_total:1,queued:0,failed:0,...jobs},work:{rows,waiting:[],counts,unread:[]}};run('state=fixture;renderJobs()');return get('jobs-rows').children;}
function parts(row){const [first,bar,last]=row.children;return {label:first.children[0].children[0].textContent,subject:first.children[0].children[1].textContent,detail:first.children[1].textContent,bar,step:last.children[0].textContent,time:last.children[1].textContent};}
const conversion=(extra={})=>({id:'conversion:j1',kind:'conversion',subject:'Long book title',job_id:'j1',step:'encoding',done:4325,total:39820,unit:'seconds',state:'running',started:NOW-134000,...extra});
const ids=rows=>rows.map(item=>item.dataset.id);

// Status line is unchanged.
render();assert.match(get('jobs-status-text').textContent,/^0 need attention · 1 converted out of 2 approved books/);  // 0.29.0: the worker's "Running" is not work; 0.31.0: no bare "Nothing running" either
render({approved_total:undefined});assert.match(get('jobs-status-text').textContent,/Approved book progress unavailable/);

// One measured conversion row: label, subject, audio-time detail, bar, Step N of 4, elapsed.
let rows=render({},[conversion()]);assert.equal(rows.length,1);let row=parts(rows[0]);
assert.equal(row.label,'Converting: ');assert.equal(row.subject,'Long book title');assert.equal(row.detail,'1:12:05 of 11:03:40 audio');
assert.equal(row.bar.value,10);assert.equal(row.step,'Step 3 of 4 - Encoding audio');assert.equal(row.time,'2:14 elapsed');
assert.equal(row.bar.getAttribute('aria-label'),'Converting: Long book title');assert.equal(row.bar.getAttribute('aria-valuetext'),'Step 3 of 4 - Encoding audio, 1:12:05 of 11:03:40 audio');
assert.equal(get('jobs-idle').hidden,true);const first=rows[0];
// Updated in place: the same element, never rebuilt by a poll.
rows=render({},[conversion({done:8000})]);assert.equal(rows[0],first);assert.equal(parts(rows[0]).bar.value,20);
// Finishing: done = total while running is indeterminate, no detail, the encoding text says finalizing.
row=parts(render({},[conversion({done:39820})])[0]);assert.equal(row.bar.value,null);assert.equal(row.detail,'');assert.equal(row.step,'Step 3 of 4 - Finalizing conversion');
// Never 100 % before done.
assert.equal(parts(render({},[conversion({done:39819})])[0]).bar.value,99);
// Unmeasured step: indeterminate, no detail; the elapsed time is the proof of life.
row=parts(render({},[conversion({step:'checking',done:undefined,total:undefined,unit:undefined})])[0]);
assert.equal(row.bar.value,null);assert.equal(row.detail,'');assert.equal(row.step,'Step 4 of 4 - Verifying audiobook');assert.match(row.time,/elapsed$/);
// Sub-steps name what happens now; an unknown step has no invented step number.
for(const [step,text] of [['preparing','Step 1 of 4 - Copying and checking source files'],['source copies','Step 1 of 4 - Checking source copies'],['checking audio','Step 2 of 4 - Checking source audio'],['matching format','Step 2 of 4 - Choosing the audio format'],['normalizing','Step 2 of 4 - Normalizing audio'],['joined audio','Step 2 of 4 - Checking joined audio'],['publishing','Step 4 of 4 - Copying audiobook to the library'],['unknown-step','Working']])
  assert.equal(parts(render({},[conversion({step,done:undefined,total:undefined})])[0]).step,text);

// Detail formats: files (whole tracks, singular), bytes (1024-based, one decimal under 10), short audio, books.
assert.equal(parts(render({},[conversion({step:'preparing',unit:'files',done:2.6,total:17})])[0]).detail,'2 of 17 files');
assert.equal(parts(render({},[conversion({step:'preparing',unit:'files',done:0.4,total:1})])[0]).detail,'0 of 1 file');
assert.equal(parts(render({},[conversion({step:'publishing',unit:'bytes',done:1.2*1024**3,total:6.1*1024**3})])[0]).detail,'1.2 of 6.1 GB');
assert.equal(parts(render({},[conversion({step:'publishing',unit:'bytes',done:812*1024**2,total:940*1024**2})])[0]).detail,'812 of 940 MB');
assert.equal(parts(render({},[conversion({unit:'seconds',done:95,total:1800})])[0]).detail,'1:35 of 30:00 audio');
assert.equal(parts(render({},[conversion({unit:undefined,done:35,total:100})])[0]).detail,'35%');

// Several rows: the engine's order, as sent (the page never re-sorts), keyed by id.
const finished={id:'finished_check',kind:'finished_check',done:3,total:60,unit:'books',state:'running',started:NOW-9000};
const research={id:'research',kind:'research',subject:'Дюна',step:'researching',step_text:'Publisher - Fetching credits',done:12,total:40,unit:'books',state:'running',started:NOW-5000};
const series={id:'series',kind:'series',subject:'Мухи',step:'looking_up',done:0,total:292,unit:'books',state:'running',started:NOW-2000};
const oldHeld={title:'Похититель детей',book_id:'b0',cause:'other',held_total:1};
let mixed=render({state:'Paused',queued:418,attention_counts:{other:65},approved_total:1200,converted_total:778,pause:{origin:'interrupted'},attention_row:oldHeld},[series],{queued_conversions:418});
assert.match(get('jobs-status-text').textContent,/^Paused · 418 books waiting to convert · 65 need attention · 778 converted out of 1200 approved books/,'0.31.0 (2.1): a look-up row alone never leads the status line; it shows as its row below');
assert.match(get('jobs-help').textContent,/has not identified which book stopped them/);assert.doesNotMatch(get('jobs-help').textContent,/Похититель|Возрожденный/);
assert.equal(parts(mixed.find(item=>item.dataset.id==='series')).label,'Metadata: Updating series: ');
assert.equal(parts(mixed.find(item=>item.dataset.id==='series')).detail,'0 of 292 books');
// 0.29.0 (Judy section 7): a held cleanup is not a Running row; it is On hold, with its plain cause.
assert.equal(mixed.length,1);assert.equal(get('jobs-hold-block').hidden,false);
assert.match(get('jobs-hold').children[0].children[0].children[0].textContent,/^On hold: /);
// The start check is a row like any other; the help text keeps its line (spec 5: unchanged).
render({state:'Running',queue_work:{schema:'books-audio-queue-work-v1',state:'checking_pending'}},[{id:'start_check',kind:'start_check',step:'checking_pending',state:'running',started:NOW-3000},series]);
assert.match(get('jobs-status-text').textContent,/^2 tasks running · /);assert.match(get('jobs-help').textContent,/^Checking pending audiobook work/);
assert.deepEqual(ids(get('jobs-rows').children),['start_check','series']);
rows=render({},[conversion(),finished,research]);assert.deepEqual(ids(rows),['conversion:j1','finished_check','research']);
row=parts(rows[1]);assert.equal(row.label,'Re-checking finished audiobooks');assert.equal(row.subject,'');assert.equal(row.detail,'3 of 60 books');assert.equal(row.step,'Checking each finished file is still the right one');assert.equal(row.time,'0:09 elapsed');
row=parts(rows[2]);assert.equal(row.label,'Researching books: ');assert.equal(row.subject,'Дюна');assert.equal(row.step,'Publisher - Fetching credits');assert.equal(row.subject.length>0&&rows[2].children[0].children[0].children[1].title,'Дюна');
rows=render({},[research,finished]);assert.deepEqual(ids(rows),['research','finished_check'],'the engine order, never re-sorted');
row=parts(render({},[{id:'scan',kind:'scan',subject:'Audiobooks',step:'scanning',step_text:'Z:/Audiobooks/A/01.mp3',done:10,total:200,unit:'files',state:'running',started:NOW-2000}])[0]);
assert.equal(row.label,'Scanning files: ');assert.equal(row.detail,'10 of 200 files');assert.equal(row.step,'Z:/Audiobooks/A/01.mp3');
// A row that is no longer sent is removed at once.
rows=render({},[finished]);assert.equal(rows.length,1);assert.equal(rows[0].dataset.id,'finished_check');
// 1.4: a row younger than 1 s is not drawn yet (a blip); 1.3: every row shows, no "+N more running" line.
rows=render({},[finished,{...research,started:Date.now()}]);assert.deepEqual(ids(rows),['finished_check'],'under 1 s: not drawn');
const cleanupRow={id:'cleanup:j2',kind:'cleanup',subject:'Dune',job_id:'j2',step:'originals',done:12,total:40,unit:'files',state:'running',started:NOW-2000};
rows=render({},[conversion(),conversion({id:'conversion:j9',job_id:'j9'}),cleanupRow,finished,series,research]);
assert.equal(rows.length,6,'all of them');assert.equal(nodes.has('jobs-more') && !get('jobs-more').hidden,false);

// Cleanup labels: originals vs temporary files.
row=parts(render({},[cleanupRow])[0]);
assert.equal(row.label,'Removing originals: ');assert.equal(row.detail,'12 of 40 files');assert.equal(row.step,'Removing original files');
row=parts(render({},[{...cleanupRow,step:'temporary',done:undefined,total:undefined,unit:undefined}])[0]);
assert.equal(row.label,'Cleaning up: ');assert.equal(row.step,'Removing temporary recovery and working files');
// 74e (Judy 0.24.1 section 5): a folder holding a cover is removed too, so the step no longer says "empty".
row=parts(render({},[{...cleanupRow,step:'folders',done:undefined,total:undefined,unit:undefined}])[0]);
assert.equal(row.step,'Removing source folders');

// Paused: muted, labelled, elapsed frozen. Held (0.29.0): On hold, never a Running row.
rows=render({state:'Paused'},[conversion({state:'paused'})]);row=parts(rows[0]);
assert.equal(row.step,'Paused - Step 3 of 4 - Encoding audio');assert.equal(rows[0].classList.contains('paused'),true);assert.equal(row.bar.value,10);
const frozen=row.time;run(`updateActivity(activityRows.get('conversion:j1'),${NOW+60000})`);assert.equal(parts(rows[0]).time,frozen);
// 0.29.0 (Judy section 7): a held item is in On hold: no bar, no clock, never the verb, and its line 2 is the plain cause
// (an unmapped one points to Needs attention, never the engine's text).
rows=render({state:'Needs attention',current_title:'Long book title',current_book_id:'b9',progress:{phase:'encoding',reason:'Exact source changed'}},[]);
assert.equal(rows.length,0,'a held row is not a running row');assert.equal(get('jobs-hold-block').hidden,false);
let hold=get('jobs-hold').children[0];assert.equal(hold.children[0].children[0].textContent,'On hold: Long book title');
assert.equal(hold.children[0].children[1].textContent,'Stopped. See Needs attention.');assert.equal(hold.children[1].textContent,'Show in list');
assert.match(get('jobs-status-text').textContent,/^1 on hold · /);
rows=render({state:'Needs attention',attention_row:{title:'Похититель детей',phase:'originals',reason:'Cannot refresh protected file identity',cause:'identity_read',book_id:'b1',held_total:1}},[]);
hold=get('jobs-hold').children[0];assert.equal(hold.children[0].children[0].textContent,'On hold: Похититель детей');
assert.equal(hold.children[0].children[1].textContent,"Cleanup stopped. The app couldn't read one file's information.");
assert.doesNotMatch(get('jobs-status-text').textContent,/Running|Removing originals/);
rows=render({state:'Running'},[conversion()]);assert.match(parts(rows[0]).time,/elapsed/,'positive control: a running row keeps its clock');assert.equal(rows[0].children[2].children[1].hidden,false);
assert.equal(parts(render({state:'Pausing'},[conversion({state:'pausing'})])[0]).step,'Pausing - Step 3 of 4 - Encoding audio');

// Idle (0.31.0, 1.3): nothing runs right now (this engine sends no finished state); paused with no rows: how to continue.
assert.equal(render({},[]).length,0);assert.equal(get('jobs-idle').textContent,'Nothing is running right now.');assert.equal(get('jobs-idle').hidden,false);
render({state:'Paused'},[]);assert.equal(get('jobs-idle').textContent,'Paused. Resume continues pending books.');
render({},undefined);assert.equal(get('jobs-idle').textContent,'Nothing is running right now.');assert.equal(get('jobs-hold-block').hidden,true,'On hold empties with its rows');
// Item 8, 0.31.0 (1.4): only Sergei can move things on. The engine's finished state decides (needs_you_only is no longer
// read); the count is Needs attention's own.
const renderYou=(jobs,engine,you=true)=>{context.fixture={audiobook_jobs:{state:'Running',approved_total:2,converted_total:1,queued:0,failed:0,...jobs},work:{rows:[],waiting:[],counts:{},unread:[],state:engine,pending:{}},needs_you_only:you};run('state=fixture;renderJobs()');};
renderYou({attention_counts:{other:329}},'waiting_for_you');assert.equal(get('jobs-idle').textContent,'Nothing is running, queued or waiting.');
assert.equal(get('jobs-you').hidden,false);assert.equal(get('jobs-you-line').textContent,'329 books need attention.');
assert.equal(get('jobs-review').textContent,'Review them');assert.equal(get('jobs-review').title,'Show every book that needs you.');assert.equal(get('jobs-review').hidden,false);
renderYou({attention_counts:{other:329}},'continues');assert.equal(get('jobs-you').hidden,true,'a retry or check the app will make itself: not shown');assert.equal(get('jobs-idle').textContent,'Nothing is running right now.');
renderYou({attention_counts:{other:329}},'waiting_for_you',false);assert.equal(get('jobs-you').hidden,false,'needs_you_only is not read: the state decides');
renderYou({attention_counts:{other:329}},'',true);assert.equal(get('jobs-you').hidden,true,'needs_you_only alone shows nothing');
renderYou({attention_counts:{}},'waiting_for_you');assert.equal(get('jobs-you').hidden,true,'only a hold or a drive waits: they keep their own homes, no line here');

// ETA: only when determinate, running, at least 10 s into the step and 5 % done; from the recent rate.
rows=render({},[conversion({started:NOW-20000,done:10,total:100,unit:'files'})]);
run(`(()=>{const view=activityRows.get('conversion:j1');view.samples=[];view.etaAt=0;updateActivity(view,${NOW});view.row={...view.row,done:15};updateActivity(view,${NOW+5000});})()`);
assert.equal(parts(rows[0]).time,'0:25 elapsed - about 1 min left');
rows=render({},[conversion({step:'normalizing',started:NOW-3000,done:50,total:100})]);run(`updateActivity(activityRows.get('conversion:j1'),${NOW+6000})`);assert.doesNotMatch(parts(rows[0]).time,/left/);
rows=render({},[conversion({step:'joined audio',started:NOW-60000,done:1,total:100})]);assert.doesNotMatch(parts(rows[0]).time,/left/);

// Folder note in the help text is unchanged.
render({folder_cleanup_notes:['Native protected stream namespace unsupported']});assert.match(get('jobs-help').textContent,/Source folders retained: safe automatic removal is unavailable on this drive/);

// Page contract: the toolbar sits above the rows; the bar styles exist for every state.
const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
assert.ok(html.indexOf('id="pause-jobs"')<html.indexOf('id="jobs-rows"'),'Pause/Resume are above the rows');assert.doesNotMatch(html,/id="jobs-progress"|id="book-progress"/);
// Hidden until the engine reports its jobs: the idle line has no placeholder (Judy 0.22.1, 3.5; 0.31.0 retires "Nothing running").
assert.match(html,/<ul id="jobs-rows" role="region" aria-label="Running activities" tabindex="0"><\/ul><p id="jobs-idle" class="field-help" hidden><\/p>/);assert.doesNotMatch(html,/id="jobs-more"/,'1.3: no overflow line');
for(const rule of [/#jobs-activity\{min-height:136px\}/,/\.activity-row progress:indeterminate\{[^}]*animation:activity-slide 1\.4s linear infinite\}/,/\.activity-row\.paused progress:indeterminate\{animation:none/,/\.activity-row\.attention progress::-webkit-progress-value\{background:var\(--warning\)\}/,/@media\(prefers-reduced-motion:reduce\)\{\.activity-row progress:indeterminate\{animation:none;background:repeating-linear-gradient/,/@keyframes activity-slide/])assert.match(css,rule);

// One writer for #version: the engine version, never 'local prototype' (the desktop layer no longer writes it).
run("state={version:'0.16.6'};renderVersion()");assert.equal(get('version').textContent,'v0.16.6');assert.equal(get('version').hidden,false);
run('state={};renderVersion()');assert.equal(get('version').hidden,true);
const desktopUi=fs.readFileSync(path.join(__dirname,'../web/desktop-ui.js'),'utf8'),appSource=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
assert.doesNotMatch(desktopUi,/#version/);assert.match(appSource,/\$\('version'\)\.textContent=value/);assert.doesNotMatch(appSource+html,/local prototype/i);assert.match(html,/<span id="version" class="badge" hidden><\/span>/);
const options=run('filterOptions.candidates');const index=options.findIndex(x=>x[0]==='converted');assert.equal(options[index][1],'Audiobook Ready');assert.equal(index,0);
console.log('PASS progress rows: measured and indeterminate steps, detail formats, engine order, every row, paused/attention/idle, elapsed and ETA, page contract');

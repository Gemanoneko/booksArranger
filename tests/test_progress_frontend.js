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
function render(jobs={},activities=[]){context.fixture={audiobook_jobs:{state:'Running',approved_total:2,converted_total:1,queued:0,failed:0,...jobs},activities};run('state=fixture;renderJobs()');return get('jobs-rows').children;}
function parts(row){const [first,bar,last]=row.children;return {label:first.children[0].children[0].textContent,subject:first.children[0].children[1].textContent,detail:first.children[1].textContent,bar,step:last.children[0].textContent,time:last.children[1].textContent};}
const conversion=(extra={})=>({id:'conversion',kind:'conversion',subject:'Long book title',step:'encoding',step_index:3,step_count:4,done:4325,total:39820,unit:'seconds',indeterminate:false,state:'running',step_started_at:NOW-134000,...extra});

// Status line is unchanged.
render();assert.match(get('jobs-status').textContent,/1 converted out of 2 approved books/);
render({approved_total:undefined});assert.match(get('jobs-status').textContent,/Approved book progress unavailable/);

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
row=parts(render({},[conversion({step:'checking',step_index:4,indeterminate:true,done:undefined,total:undefined,unit:undefined})])[0]);
assert.equal(row.bar.value,null);assert.equal(row.detail,'');assert.equal(row.step,'Step 4 of 4 - Verifying audiobook');assert.match(row.time,/elapsed$/);
// Sub-steps name what happens now.
for(const [step,index,text] of [['preparing',1,'Copying and checking source files'],['source copies',1,'Checking source copies'],['checking audio',2,'Checking source audio'],['matching format',2,'Choosing the audio format'],['normalizing',2,'Normalizing audio'],['joined audio',2,'Checking joined audio'],['publishing',4,'Copying audiobook to the library'],['unknown-step',1,'Working']])
  assert.equal(parts(render({},[conversion({step,step_index:index,indeterminate:true})])[0]).step,`Step ${index} of 4 - ${text}`);

// Detail formats: files (whole tracks, singular), bytes (1024-based, one decimal under 10), short audio, books.
assert.equal(parts(render({},[conversion({step:'preparing',step_index:1,unit:'files',done:2.6,total:17})])[0]).detail,'2 of 17 files');
assert.equal(parts(render({},[conversion({step:'preparing',step_index:1,unit:'files',done:0.4,total:1})])[0]).detail,'0 of 1 file');
assert.equal(parts(render({},[conversion({step:'publishing',step_index:4,unit:'bytes',done:1.2*1024**3,total:6.1*1024**3})])[0]).detail,'1.2 of 6.1 GB');
assert.equal(parts(render({},[conversion({step:'publishing',step_index:4,unit:'bytes',done:812*1024**2,total:940*1024**2})])[0]).detail,'812 of 940 MB');
assert.equal(parts(render({},[conversion({unit:'seconds',done:95,total:1800})])[0]).detail,'1:35 of 30:00 audio');
assert.equal(parts(render({},[conversion({unit:undefined,done:35,total:100})])[0]).detail,'35%');

// Several activities: fixed order (conversion, cleanup, identity, scan), whatever order they arrive in.
const identity={id:'identity',kind:'identity',subject:'',step:'identity',done:3,total:60,unit:'books',indeterminate:false,state:'running',step_started_at:NOW-9000};
const research={id:'scan',kind:'scan',subject:'Дюна',step:'researching',step_text:'Publisher - Fetching credits',done:12,total:40,unit:'books',indeterminate:false,state:'running',step_started_at:NOW-5000};
rows=render({},[research,identity,conversion()]);assert.deepEqual(rows.map(item=>item.dataset.kind),['conversion','identity','scan']);
row=parts(rows[1]);assert.equal(row.label,'Checking finished books');assert.equal(row.subject,'');assert.equal(row.detail,'3 of 60 books');assert.equal(row.step,'Checking identity');assert.equal(row.time,'0:09 elapsed');
row=parts(rows[2]);assert.equal(row.label,'Researching books: ');assert.equal(row.subject,'Дюна');assert.equal(row.step,'Publisher - Fetching credits');assert.equal(row.subject.length>0&&rows[2].children[0].children[0].children[1].title,'Дюна');
row=parts(render({},[{id:'scan',kind:'scan',subject:'Audiobooks',step:'scanning',step_text:'Z:/Audiobooks/A/01.mp3',done:10,total:200,unit:'files',indeterminate:false,state:'running',step_started_at:NOW}])[0]);
assert.equal(row.label,'Scanning files: ');assert.equal(row.detail,'10 of 200 files');assert.equal(row.step,'Z:/Audiobooks/A/01.mp3');
// A row that is no longer sent is removed at once; the next one is placed in order.
rows=render({},[identity]);assert.equal(rows.length,1);assert.equal(rows[0].dataset.kind,'identity');
// More than four: the first four in order plus one "+N more running" line.
rows=render({},[conversion(),conversion({id:'second'}),identity,research,{id:'cleanup',kind:'cleanup',subject:'Dune',step:'originals',done:12,total:40,unit:'files',indeterminate:false,state:'running',step_started_at:NOW}]);
assert.equal(rows.length,4);assert.equal(get('jobs-more').textContent,'+1 more running');assert.equal(get('jobs-more').hidden,false);

// Cleanup labels: originals vs temporary files.
row=parts(render({},[{id:'cleanup',kind:'cleanup',subject:'Dune',step:'originals',done:12,total:40,unit:'files',indeterminate:false,state:'running',step_started_at:NOW}])[0]);
assert.equal(row.label,'Removing originals: ');assert.equal(row.detail,'12 of 40 files');assert.equal(row.step,'Removing original files');assert.equal(get('jobs-more').hidden,true);
row=parts(render({},[{id:'cleanup',kind:'cleanup',subject:'Dune',step:'temporary',indeterminate:true,state:'running',step_started_at:NOW}])[0]);
assert.equal(row.label,'Cleaning up: ');assert.equal(row.step,'Removing temporary recovery and working files');

// Paused: muted, labelled, elapsed frozen; attention: reason, warning style, bar keeps its value.
rows=render({state:'Paused'},[conversion({state:'paused'})]);row=parts(rows[0]);
assert.equal(row.step,'Paused - Step 3 of 4 - Encoding audio');assert.equal(rows[0].classList.contains('paused'),true);assert.equal(row.bar.value,10);
const frozen=row.time;run(`updateActivity(activityRows.get('conversion'),${NOW+60000})`);assert.equal(parts(rows[0]).time,frozen);
rows=render({state:'Needs attention'},[conversion({state:'attention',reason:'Exact source changed'})]);row=parts(rows[0]);
assert.equal(row.step,'Needs attention - Exact source changed');assert.equal(rows[0].classList.contains('attention'),true);assert.equal(rows[0].classList.contains('paused'),false);assert.equal(row.bar.value,10);
assert.equal(parts(render({state:'Pausing'},[conversion({state:'pausing'})])[0]).step,'Pausing - Step 3 of 4 - Encoding audio');

// Idle: "Nothing running"; paused with no rows: how to continue.
assert.equal(render({},[]).length,0);assert.equal(get('jobs-idle').textContent,'Nothing running');assert.equal(get('jobs-idle').hidden,false);
render({state:'Paused'},[]);assert.equal(get('jobs-idle').textContent,'Paused. Resume continues pending books.');
render({},undefined);assert.equal(get('jobs-idle').textContent,'Nothing running');

// ETA: only when determinate, running, at least 10 s into the step and 5 % done; from the recent rate.
rows=render({},[conversion({step_started_at:NOW-20000,done:10,total:100,unit:'files'})]);
run(`(()=>{const view=activityRows.get('conversion');view.samples=[];view.etaAt=0;updateActivity(view,${NOW});view.row={...view.row,done:15};updateActivity(view,${NOW+5000});})()`);
assert.equal(parts(rows[0]).time,'0:25 elapsed - about 1 min left');
rows=render({},[conversion({step:'normalizing',step_index:2,step_started_at:NOW-3000,done:50,total:100})]);run(`updateActivity(activityRows.get('conversion'),${NOW+6000})`);assert.doesNotMatch(parts(rows[0]).time,/left/);
rows=render({},[conversion({step:'joined audio',step_index:2,step_started_at:NOW-60000,done:1,total:100})]);assert.doesNotMatch(parts(rows[0]).time,/left/);

// Folder note in the help text is unchanged.
render({folder_cleanup_notes:['Native protected stream namespace unsupported']});assert.match(get('jobs-help').textContent,/Empty source folders retained: safe automatic removal is unavailable on this drive/);

// Page contract: the toolbar sits above the rows; the bar styles exist for every state.
const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
assert.ok(html.indexOf('id="pause-jobs"')<html.indexOf('id="jobs-rows"'),'Pause/Resume are above the rows');assert.doesNotMatch(html,/id="jobs-progress"|id="book-progress"/);
assert.match(html,/<ul id="jobs-rows" aria-label="Running activities"><\/ul><p id="jobs-idle" class="field-help">Nothing running<\/p>/);
for(const rule of [/#jobs-activity\{min-height:136px\}/,/\.activity-row progress:indeterminate\{[^}]*animation:activity-slide 1\.4s linear infinite\}/,/\.activity-row\.paused progress:indeterminate\{animation:none/,/\.activity-row\.attention progress::-webkit-progress-value\{background:var\(--warning\)\}/,/@media\(prefers-reduced-motion:reduce\)\{\.activity-row progress:indeterminate\{animation:none;background:repeating-linear-gradient/,/@keyframes activity-slide/])assert.match(css,rule);

const options=run('filterOptions.candidates');const index=options.findIndex(x=>x[0]==='converted');assert.equal(options[index][1],'Audiobook Ready');assert.equal(index,0);
console.log('PASS progress rows: measured and indeterminate steps, detail formats, fixed order, overflow, paused/attention/idle, elapsed and ETA, page contract');

'use strict';
// 0.31.0 (Judy's Docs/BooksArranger_0.31.0_UX.md, section 2): the two background look-ups get plain names, steps that say
// whether a file changes, a bar that counts the whole look-up, and a grouped Waiting item between tries with the next try.
// A look-up row never reads "No progress for 5 min" and carries no time estimate. The real renderJobs against DOM doubles.
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
const run=code=>vm.runInContext(code,context);
const NOW=Date.now();
const jobsBase={state:'Completed',approved_total:1510,converted_total:1510,queued:0,failed:0,attention_counts:{},candidate_total:1510,not_approved_total:0};
const tries={per_source:3,spacing_seconds:21600,failures:3};
function show(work,jobs={}){
  context.fixture={audiobook_jobs:{...jobsBase,...jobs},work:{rows:[],waiting:[],counts:{},unread:[],snapshot_age_ms:0,refreshing:false,state:'background_only',pending:{lookups:{series:212,details:31,all:243}},
    background:{series:{tries},gap_fill:{tries:null}},lookups_waiting:[],...work}};
  run('state=fixture;renderJobs()');return get('jobs-rows').children;
}
function parts(row){const [first,bar,last]=row.children;return {label:first.children[0].children[0].textContent,subject:first.children[0].children[1].textContent,detail:first.children[1].textContent,bar,step:last.children[0].textContent,tip:last.children[0].title,time:last.children[1].textContent};}
const waits=()=>get('jobs-wait').children.map(item=>({line1:item.children[0].children[0].children.map(part=>part.textContent).join(''),line2:item.children[0].children[1].textContent,tip:item.children[0].children[1].title,button:item.children[1]}));
const series=(extra={})=>({id:'series',kind:'series',subject:'Тёмный лес',step:'looking_up',done:691,total:903,unit:'books',state:'running',started:NOW-60000,...extra});
const details=(extra={})=>({id:'gap_fill',kind:'gap_fill',subject:'Дюна',done:40,total:71,unit:'books',state:'running',started:NOW-60000,...extra});
const conversion=(extra={})=>({id:'conversion:j1',kind:'conversion',subject:'Dune',job_id:'j1',book_id:'b1',step:'encoding',done:100,total:1000,unit:'seconds',state:'running',started:NOW-600000,...extra});

// 1. The running rows (2.1): the label says whose books, the step whether a file changes, the detail the whole look-up.
let rows=show({rows:[series(),details()]});
let row=parts(rows[0]);
assert.equal(row.label+row.subject,'Finding series for finished audiobooks: Тёмный лес');assert.equal(row.step,'Asking online sources. No file is changed.');
assert.equal(row.detail,'691 of 903 books','done and total are the whole look-up, as the engine sends them');
// Third round (2.1, check 28): the tooltip follows one engine fact, whether the app applies a found series by itself.
// The guard is at hold (the fact is false, or not sent): a found series is recorded and nothing is renamed or moved.
const HOLD_TIP='Finished audiobooks without a series are looked up online, one by one. A series that is found is recorded. No audiobook is renamed or moved.';
const APPLIES_TIP='Finished audiobooks without a series are looked up online, one by one. When author and series are found for certain, the book is filed under them. Otherwise it stays as it is.';
assert.equal(row.tip,HOLD_TIP);
assert.equal(parts(show({rows:[series()],background:{series:{tries,applies_by_itself:false},gap_fill:{tries:null}}})[0]).tip,HOLD_TIP);
assert.equal(parts(show({rows:[series()],background:{series:{tries,applies_by_itself:true},gap_fill:{tries:null}}})[0]).tip,APPLIES_TIP,'the automatic move is on');
assert.equal(parts(show({rows:[series({step:'updating'})],background:{series:{tries,applies_by_itself:true},gap_fill:{tries:null}}})[0]).tip,APPLIES_TIP,'the writing step too');
assert.equal(parts(show({rows:[series()],background:{series:{tries,applies_by_itself:'yes'},gap_fill:{tries:null}}})[0]).tip,HOLD_TIP,'only the engine\'s own true');
for(const tip of [HOLD_TIP,APPLIES_TIP])assert.doesNotMatch(tip,/approv/,'neither is about approval: he approves nothing (R18)');
rows=show({rows:[series(),details()]});row=parts(rows[0]);
assert.equal(row.bar.value,Math.floor(691/903*100),'determinate');
row=parts(rows[1]);
assert.equal(row.label+row.subject,'Finding original titles and author names: Дюна');assert.equal(row.step,'For books you already approved. Recorded only, no file is changed.');
assert.equal(row.detail,'40 of 71 books');
assert.equal(row.tip,'Books approved without an original title or a full author name are looked up online, one by one. The answers are recorded. No audiobook is renamed.');
// Writing: the same label, the writing step.
row=parts(show({rows:[series({step:'updating'})]})[0]);
assert.equal(row.label,'Finding series for finished audiobooks: ');assert.equal(row.step,'Writing the series into the file and renaming it. Audio unchanged.');
// The old names are gone from the page.
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
for(const old of ['Metadata: Updating series','Looking up book details','Looking up the series'])assert.ok(!source.includes(old),old);
// The other look-alike rows keep their names (2.1), so the three no longer read as one job.
assert.equal(run("workLabel({kind:'research'})"),'Researching books');assert.equal(run("workLabel({kind:'lookup'})"),'Looking up metadata');assert.equal(run("workLabel({kind:'finished_check'})"),'Re-checking finished audiobooks');

// 2. No time estimate and never "No progress for 5 min" on a look-up: its pace is the sources'.
rows=show({rows:[series(),conversion()]});
for(const view of run('[...activityRows.values()]')){view.progressAt=NOW-400000;view.samples=[[NOW-20000,0.1],[NOW-10000,0.2]];view.etaAt=0;}
run('for(const view of activityRows.values())updateActivity(view,Date.now())');
const stale=Object.fromEntries(get('jobs-rows').children.map(item=>[item.dataset.id,parts(item)]));
assert.equal(stale['conversion:j1'].step,'No progress for 5 min','positive control: a main job with no progress says so');
assert.equal(stale.series.step,'Asking online sources. No file is changed.','a look-up that is only being polite to a source never does');
assert.doesNotMatch(stale.series.time,/left/,'no estimate');assert.match(stale.series.time,/elapsed/,'the elapsed time stays');
assert.equal(get('jobs-rows').children.find(item=>item.dataset.id==='series').classes.has('stalled'),false);

// 3. Between tries (2.2): one grouped Waiting item per look-up, with the count, the next try and the tries limit.
const at=NOW+3600000,clock=run('waitingClock('+at+')');
show({lookups_waiting:[{id:'series_lookup',kind:'series_lookup',count:212,at},{id:'detail_lookup',kind:'detail_lookup',count:31,at}]});
let listed=waits();
assert.equal(get('jobs-wait-block').hidden,false);assert.equal(listed.length,2);
assert.equal(listed[0].line1,'Finding series for finished audiobooks: 212 books');assert.equal(listed[0].line2,`Waiting for online sources. Next try ${clock}. No file is changed.`);
assert.equal(listed[0].tip,'Each source is asked up to 3 times for a book, 6 hours apart. With no answer after that, the book is left as it is and the app stops asking.',"the engine's numbers (G8)");
assert.equal(listed[0].button.hidden,true,'no button');
assert.equal(listed[1].line1,'Finding original titles and author names: 31 books');assert.equal(listed[1].line2,`Waiting for online sources. Next try ${clock}. No file is changed.`);
assert.equal(listed[1].tip,'A book waits here until its sources answer. The app asks again by itself.','no limit sent for it: the no-limit sentence (G6)');
// G8 and 6.1: the tooltip follows the engine's numbers; no hours sent leaves that part out; one try and one hour read as one.
const tip=limit=>{show({background:{series:{tries:limit},gap_fill:{tries:limit}},lookups_waiting:[{id:'series_lookup',kind:'series_lookup',count:2,at},{id:'detail_lookup',kind:'detail_lookup',count:2,at}]});return waits().map(item=>item.tip);};
assert.deepEqual(tip({per_source:5,spacing_seconds:7200}),Array(2).fill('Each source is asked up to 5 times for a book, 2 hours apart. With no answer after that, the book is left as it is and the app stops asking.'),'a limit for the detail look-up gives it the same sentence');
assert.equal(tip({per_source:4,spacing_seconds:3600})[0],'Each source is asked up to 4 times for a book, 1 hour apart. With no answer after that, the book is left as it is and the app stops asking.');
assert.equal(tip({per_source:3})[0],'Each source is asked up to 3 times for a book. With no answer after that, the book is left as it is and the app stops asking.');
assert.equal(tip({per_source:1,spacing_seconds:21600})[0],'Each source is asked once for a book. With no answer, the book is left as it is and the app stops asking.');
assert.equal(get('jobs-rows').children.length,0,'between tries there is no running row');
// The next try time is left out when the engine has none; one book reads as one.
show({lookups_waiting:[{id:'series_lookup',kind:'series_lookup',count:1,at:null}]});
assert.deepEqual([waits()[0].line1,waits()[0].line2],['Finding series for finished audiobooks: 1 book','Waiting for online sources. No file is changed.']);
// A series found whose write is held by a job: the book, the 0.30.0 blocker sentence, Show in list.
const blocker={kind:'jobs',cause:'conversion',title:'Dune',book_id:'b1',count:null};
show({state:'working',rows:[conversion()],lookups_waiting:[{id:'series_write:j9',kind:'series_write',subject:'Граф Ноль',book_id:'b9',job_id:'j9',blocker}]},{state:'Running'});
listed=waits();
assert.equal(listed[0].line1,'Write series into audiobook: Граф Ноль');assert.equal(listed[0].line2,run('blockerSentence('+JSON.stringify(blocker)+',workOf()).text'));
assert.match(listed[0].line2,/^It runs when Converting: Dune finishes\.$/);assert.equal(listed[0].button.hidden,false);assert.equal(listed[0].button.textContent,'Show in list');

// 4. Their place in the Waiting list is the engine's: after metadata_sources, before drive.
show({waiting:[{id:'conversions',kind:'conversions',count:2,subject:'Next'},{id:'metadata_sources',kind:'metadata_sources',count:4,at},{id:'drive:Z',kind:'drive',subject:'Z:\\Audiobooks'},{id:'automatic',kind:'automatic',label_key:'automatic_waiting'}],
  lookups_waiting:[{id:'series_lookup',kind:'series_lookup',count:212,at},{id:'detail_lookup',kind:'detail_lookup',count:31,at}]});
assert.deepEqual(waits().map(item=>item.line1.split(':')[0]),['Waiting to convert','Metadata sources','Finding series for finished audiobooks','Finding original titles and author names','Drive not answering','Automatic processing']);
// An engine that sends none (0.30.0) draws its list as before.
show({waiting:[{id:'conversions',kind:'conversions',count:2,subject:'Next'}],lookups_waiting:undefined});assert.equal(waits().length,1);

// 5. With only look-ups left the badge is Background look-ups only, and the idle line never claims nothing is waiting.
run('badgeSeen={state:null,since:0};badgeShown=null');
show({lookups_waiting:[{id:'series_lookup',kind:'series_lookup',count:212,at}]});run('badgeSeen.since-=3000;renderJobs()');
assert.equal(get('jobs-state').textContent,'Background look-ups only');assert.equal(get('jobs-idle').textContent,'Nothing is running right now.');
assert.match(get('jobs-status-text').textContent,/ · 243 background look-ups left$/);
// 6. G7 (check 18): a paused queue names the look-up that still runs; two or more read as tasks.
run('badgeSeen={state:null,since:0};badgeShown=null');
show({state:'paused',rows:[series()]},{state:'Paused'});assert.match(get('jobs-status-text').textContent,/^Paused · Finding series for finished audiobooks: Тёмный лес · /);
show({state:'paused',rows:[series(),details()]},{state:'Paused'});assert.match(get('jobs-status-text').textContent,/^Paused · 2 tasks running · /);
show({state:'paused',rows:[]},{state:'Paused'});assert.match(get('jobs-status-text').textContent,/^Paused · /);assert.doesNotMatch(get('jobs-status-text').textContent,/Finding series/);
console.log('PASS 0.31.0 look-ups: plain names and steps, whole-look-up bar, no stall line or estimate, grouped Waiting items with next try and tries, held write, order');

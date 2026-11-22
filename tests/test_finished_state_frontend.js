'use strict';
// 0.31.0 (Judy's Docs/BooksArranger_0.31.0_UX.md, sections 1 and 6): the finished-state badge, the status line without bare
// "Nothing running", the idle line, the Waiting-for-you block and the automatic line's suffix, drawn from the engine's
// work.state, pending and waits_for_you (never worked out from rows). The real renderJobs against owned DOM doubles.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
class Element{
  constructor(id=''){this.id=id;this.value=id==='library'?'Audiobooks':'';this.children=[];this.handlers={};this.dataset={};this.attrs={};this.options=[{}];this.textContent='';this.hidden=false;this.disabled=false;this.title='';this.className='';
    this.classList={toggle(){},contains:()=>false};}
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
const lookups=(series,details=0)=>({series,details,all:series+details});
const pending=(more={})=>({any:true,running:0,paused:0,waiting:0,still_checking:0,attention:0,hold:0,moves:0,drives:0,lookups:lookups(0),same_name:0,...more});
// One poll. settle: the same state has been reported for 3 s (the badge's no-flicker rule), so two polls draw it.
function show(work,jobs={},settle=true){
  context.fixture={audiobook_jobs:{...jobsBase,...jobs},work:{rows:[],waiting:[],counts:{},unread:[],snapshot_age_ms:0,refreshing:false,pending:pending(),waits_for_you:[],background:{},lookups_waiting:[],...work}};
  run('state=fixture;renderJobs()');
  if(settle){run('badgeSeen.since-=3000;renderJobs()');}
  return {badge:get('jobs-state'),line:get('jobs-status-text').textContent,idle:get('jobs-idle')};
}
const reset=()=>run('badgeSeen={state:null,since:0};badgeShown=null');
const conversion={id:'conversion:j1',kind:'conversion',subject:'Dune',job_id:'j1',book_id:'b1',step:'encoding',done:100,total:1000,unit:'seconds',state:'running',started:NOW-60000};
const series={id:'series',kind:'series',subject:'Тёмный лес',step:'looking_up',done:691,total:903,unit:'books',state:'running',started:NOW-60000};

// 1. The three badges, each with its look, its tooltip and its status line (spec 1.2 and the examples of 1.3).
reset();
let view=show({state:'all_done',pending:pending({any:false})});
assert.equal(view.badge.hidden,false);assert.equal(view.badge.textContent,'All done');assert.equal(view.badge.className,'state-done');
assert.equal(view.badge.title,'Nothing is running, queued or waiting, background look-ups included. Nothing waits for you.');
assert.equal(view.line,' · 0 need attention · 1510 converted out of 1510 approved books');
assert.equal(view.idle.textContent,'Nothing is running, queued or waiting.');assert.equal(get('jobs-you').hidden,true);

reset();
view=show({state:'waiting_for_you',waits_for_you:['attention'],pending:pending({attention:329,moves:55,lookups:lookups(200,12)})},{attention_counts:{other:329},converted_total:1181});
assert.equal(view.badge.textContent,'Waiting for you');assert.equal(view.badge.className,'state-you');
assert.equal(view.badge.title,'No conversion, cleanup or other job is running or queued. The items under Waiting for you need your answer.');
// Third round (R18, R19): no status part about renames or moves to approve; 55 books with a series found add none.
assert.equal(view.line,' · 329 need attention · 1181 converted out of 1510 approved books · 212 background look-ups left');
assert.equal(view.idle.textContent,'Nothing is running right now.','look-ups are left: never "queued or waiting" nothing');
// The Waiting-for-you block (1.4, third round): one line again, the books that need attention; the old "can't do more"
// sentence is gone, and nothing about a finished book's name or place is ever in it.
assert.equal(get('jobs-you').hidden,false);assert.equal(get('jobs-you-line').textContent,'329 books need attention.');assert.equal(get('jobs-review').hidden,false);
assert.doesNotMatch(get('jobs-you-line').textContent,/can't do more/);assert.equal(nodes.has('jobs-you-moves'),false,'the page never asks for a second line');
// The books with a series found are said once, in the quiet line, whatever the state.
assert.equal(get('jobs-series-found').hidden,false);assert.equal(get('jobs-series-found').textContent,'Series found for 55 finished audiobooks. They are recorded and stay where they are.');

reset();
view=show({state:'background_only',pending:pending({lookups:lookups(200,12)})});
assert.equal(view.badge.textContent,'Background look-ups only');assert.equal(view.badge.className,'state-background');
assert.equal(view.badge.title,'No conversion, cleanup or other job is running or queued, and nothing waits for you. Only online look-ups are left.');
assert.equal(view.line,' · 0 need attention · 1510 converted out of 1510 approved books · 212 background look-ups left');
assert.equal(view.idle.textContent,'Nothing is running right now.');assert.equal(get('jobs-you').hidden,true);

// 2. Every other state: no badge, and never bare "Nothing running" (check 3).
for(const [state,work,jobs,first] of [
  ['working',{rows:[conversion]},{state:'Running'},'Converting: Dune'],
  ['paused',{},{state:'Paused'},'Paused'],
  ['continues',{counts:{queued_conversions:3}},{},'Continues by itself'],
  ['unknown',{},{},'Checking what is left'],  // G1: still counting is no failed read
  ['',{},{},'Checking what is left']]){  // G2: an engine that sends no state: no badge, and never the bare counts
  reset();
  view=show({state,...work},jobs);
  assert.equal(view.badge.hidden,true,state+': no badge');assert.equal(view.badge.textContent,'');
  assert.ok(view.line.startsWith(first+' · '),state+': '+view.line);assert.doesNotMatch(view.line,/^\d/,'never the counts first');
  assert.doesNotMatch(view.line,/Nothing running( ·|$)/,state);
}
reset();view=show({state:'continues',counts:{queued_conversions:3}});assert.equal(view.line,'Continues by itself · 3 books waiting to convert · 0 need attention · 1510 converted out of 1510 approved books');
assert.equal(view.idle.textContent,'Nothing is running right now.');
reset();view=show({state:'unknown'});assert.equal(view.idle.textContent,'Nothing is running right now.');assert.equal(get('jobs-you').hidden,true);
// G1 and check 17: only a source really unread for 3 s reads "could be read"; one failed poll never does.
reset();run('unreadSince.clear()');view=show({state:'unknown',unread:['workers']});assert.match(view.line,/^Checking what is left · /);
run('unreadSince.set("workers",'+(NOW-4000)+')');view=show({state:'unknown',unread:['workers']});
assert.match(view.line,/^Nothing running that could be read · /);assert.equal(view.idle.textContent,'Nothing running that could be read.');assert.equal(get('jobs-you').hidden,true);
view=show({state:'unknown',unread:[]});run('unreadSince.clear()');

// 3. "N on hold" is its own part after the badge (it was glued to "Nothing running").
reset();view=show({state:'waiting_for_you',waits_for_you:['hold'],pending:pending({hold:1})},{state:'Needs attention',current_title:'Long book',current_book_id:'b9',progress:{phase:'encoding',reason:'x'}});
assert.match(view.line,/^ · 1 on hold · 0 need attention · /);assert.equal(view.badge.textContent,'Waiting for you');
assert.equal(get('jobs-you').hidden,true,'a book on hold keeps its own home: the block has no line, so it is hidden');

// 4. Singular forms, and a drive as the only reason.
reset();view=show({state:'background_only',pending:pending({moves:1,lookups:lookups(1)})});
assert.match(view.line,/^ · 0 need attention · .* · 1 background look-up left$/);assert.doesNotMatch(view.line,/series|to approve|move/);
assert.equal(get('jobs-series-found').textContent,'Series found for 1 finished audiobook. It is recorded and stays where it is.');
reset();view=show({state:'waiting_for_you',waits_for_you:['attention'],pending:pending({attention:1})},{attention_counts:{other:1}});
assert.equal(get('jobs-you').hidden,false);assert.equal(get('jobs-you-line').textContent,'1 book needs attention.');assert.equal(get('jobs-review').hidden,false);
// 4a. A series found and not applied (3.2, check 26; the guard is at hold). 61 such books and nothing else pending: All
// done, the block hidden, no status part about them, and the one quiet line at the bottom of the panel.
reset();view=show({state:'all_done',pending:pending({any:false,moves:61})});
assert.equal(view.badge.hidden,false);assert.equal(view.badge.textContent,'All done');assert.equal(get('jobs-you').hidden,true);
assert.equal(view.line,' · 0 need attention · 1510 converted out of 1510 approved books','no part about them');
const quiet=get('jobs-series-found');
assert.equal(quiet.hidden,false);assert.equal(quiet.textContent,'Series found for 61 finished audiobooks. They are recorded and stay where they are.');
assert.equal(quiet.title,'','no tooltip');assert.equal(quiet.getAttribute('aria-live'),null);assert.equal(quiet.getAttribute('role'),null);assert.equal(quiet.children.length,0,'no control');
assert.equal(view.idle.textContent,'Nothing is running, queued or waiting.');
// Positive control that the line is not a state: one book needing attention turns the badge, the line unchanged.
reset();view=show({state:'waiting_for_you',waits_for_you:['attention'],pending:pending({attention:1,moves:61})},{attention_counts:{other:1}});
assert.equal(view.badge.textContent,'Waiting for you');assert.equal(quiet.textContent,'Series found for 61 finished audiobooks. They are recorded and stay where they are.');
// A large number prints as the page prints its counts; none, or no number from the engine: no line.
reset();show({state:'all_done',pending:pending({any:false,moves:1240})});assert.equal(quiet.textContent,'Series found for 1,240 finished audiobooks. They are recorded and stay where they are.');
for(const moves of [0,null,undefined,'61',-1,1.5]){reset();show({state:'all_done',pending:pending({any:false,moves})});assert.equal(quiet.hidden,true,String(moves));assert.equal(quiet.textContent,'');}
reset();show({state:'all_done',pending:undefined});assert.equal(quiet.hidden,true,'an engine that sends no pending');
reset();view=show({state:'waiting_for_you',waits_for_you:['drive'],pending:pending({drives:1}),waiting:[{id:'drive:Z',kind:'drive',subject:'Z:\\Audiobooks'}]});
assert.equal(view.badge.textContent,'Waiting for you');assert.equal(get('jobs-you').hidden,true);
// The same with books that have a series found: they add no line to the block, so it stays hidden (1.4: nothing about a
// finished book's name or place ever appears in it), and the quiet line says them.
reset();view=show({state:'waiting_for_you',waits_for_you:['drive'],pending:pending({drives:1,moves:61}),waiting:[{id:'drive:Z',kind:'drive',subject:'Z:\\Audiobooks'}]});
assert.equal(get('jobs-you').hidden,true);assert.equal(get('jobs-series-found').hidden,false);

// 5. No flicker (1.2, check 4): 3 s of the same state before the badge shows; another state for 1 s before it goes.
reset();
view=show({state:'all_done',pending:pending({any:false})},{},false);
assert.equal(view.badge.hidden,true,'first poll: not yet');assert.match(view.line,/^Checking what is left · 0 need attention · /,'G2: the 3 s before a badge comes up');
run('badgeSeen.since-=2900;renderJobs()');assert.equal(get('jobs-state').hidden,true,'2.9 s: not yet');
run('badgeSeen.since-=200;renderJobs()');assert.equal(get('jobs-state').hidden,false,'3 s: shown');
view=show({state:'working',rows:[]},{state:'Running'},false);
assert.equal(view.badge.hidden,false,'a job under 1 s does not remove the badge');assert.equal(view.badge.textContent,'All done');
run('badgeSeen.since-=1000;renderJobs()');assert.equal(get('jobs-state').hidden,true,'another state for 1 s: it goes');
// Straight back within the second: the badge never left.
reset();show({state:'all_done',pending:pending({any:false})});show({state:'working'},{state:'Running'},false);
view=show({state:'all_done',pending:pending({any:false})},{},false);assert.equal(view.badge.hidden,false);

// 6. The engine decides, but a main row on the page (a page-owned loop the engine does not know) is never under a badge.
reset();view=show({state:'all_done',pending:pending({any:false}),rows:[conversion]},{state:'Running'});
assert.equal(view.badge.hidden,true);assert.match(view.line,/^Converting: Dune · /);
// A look-up row alone is not main work: the badge leads and the row shows below it (2.1).
reset();view=show({state:'background_only',pending:pending({lookups:lookups(212)}),rows:[series]});
assert.equal(view.badge.textContent,'Background look-ups only');assert.match(view.line,/^ · 0 need attention · /);
assert.equal(get('jobs-rows').children.length,1);assert.equal(view.idle.hidden,true,'the Running list is not empty');
// Beside main work it counts as a task.
reset();view=show({state:'working',rows:[conversion,series]},{state:'Running'});assert.match(view.line,/^2 tasks running · /);
// 6a. Third round (1.1, 2.1): writing a series into a finished file is main work, not a look-up. The status line names
// the row and no finished-state badge shows over a file change, whatever state is reported beside it.
const writing={...series,step:'updating',background:false};
for(const reported of ['working','background_only','all_done']){
  reset();view=show({state:reported,pending:pending({writes:1}),rows:[writing]});
  assert.equal(view.badge.hidden,true,reported+': no badge over a write');assert.match(view.line,/^Finding series for finished audiobooks: Тёмный лес · /,reported);
}
// The engine's fact decides; an engine that sends none is read by the same rule (asking: a look-up; writing: main work).
reset();view=show({state:'background_only',pending:pending({lookups:lookups(1)}),rows:[{...series,background:true}]});assert.equal(view.badge.textContent,'Background look-ups only');
reset();view=show({state:'background_only',pending:pending({writes:1}),rows:[{...series,step:'updating'}]});assert.equal(view.badge.hidden,true);assert.match(view.line,/^Finding series for finished audiobooks: /);
assert.equal(run('isBackground({kind:"series",step:"updating",background:true})'),true,'the fact, when sent, is the engine\'s');
assert.equal(run('isBackground({kind:"gap_fill"})'),true);assert.equal(run('isBackground({kind:"conversion"})'),false);
// A write that waits is main work too: the engine reports "continues by itself", and the line says so, with no badge.
reset();view=show({state:'continues',pending:pending({writes:1}),lookups_waiting:[{id:'series_write:j9',kind:'series_write',subject:'Оно',book_id:'b9',job_id:'j9',blocker:null,background:false}]});
assert.equal(view.badge.hidden,true);assert.match(view.line,/^Continues by itself · /);

// 7. Counts behind (1.2, check 5): from 30 s the as-of time follows the badge as plain text, once.
run('receivedAt.set("Audiobooks",'+NOW+')');
reset();view=show({state:'all_done',pending:pending({any:false}),snapshot_age_ms:45000});
assert.match(view.line,/^ \(as of \d\d:\d\d:\d\d\) · 0 need attention · 1510 converted out of 1510 approved books$/);

// 8. Not shown while the engine is not answering, or before the jobs part has loaded.
reset();show({state:'all_done',pending:pending({any:false})});
run('busyShown=true;renderJobs()');assert.equal(get('jobs-state').hidden,true);assert.match(get('jobs-status-text').textContent,/^Last confirmed — /);
run('busyShown=false');

// 9. The automatic line (section 6) says what is left after its pass.
const automatic={state:'Completed',research:{researching:0,waiting:0,held:3}};
for(const [state,suffix] of [['working',' Other jobs are still running or waiting.'],['continues',' Other jobs are still running or waiting.'],['paused',' Other jobs are still running or waiting.'],
  ['background_only',' Background look-ups continue.'],['all_done',''],['waiting_for_you',''],['unknown',''],['','']]){
  context.fixture={audiobook_jobs:{...jobsBase,approved_total:15,converted_total:12},automatic_processing:automatic,work:{rows:[],waiting:[],counts:{},unread:[],state,pending:pending()}};
  run('state=fixture;renderAutomatic()');
  assert.equal(get('automatic-detail').textContent,'Automatic pass complete — 12 converted · 3 held'+suffix,state || 'no state');
}

// 10. The page's markup: the badge is the first thing in the status line; the block has its heading and its one line; the
// quiet line is the last thing above the two help lines.
const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
assert.match(html,/<p id="jobs-status" aria-live="polite"><strong id="jobs-state" hidden><\/strong><span id="jobs-status-text">Jobs: loading…<\/span><\/p>/);
assert.match(html,/<div id="jobs-you" hidden><p class="jobs-hold-heading">Waiting for you<\/p><div class="jobs-you"><p id="jobs-you-line"><\/p><button id="jobs-review" type="button" class="quiet" title="Show every book that needs you\.">Review them<\/button><\/div><\/div><\/div><p id="jobs-series-found" class="field-help" hidden><\/p><p id="approved-help" class="field-help">/);
assert.doesNotMatch(html,/Nothing running/);
// Check 27, nothing asks: no status part, second line, shortcut, dialog or button about a rename or move to approve.
const pageSource=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
for(const gone of [/jobs-you-moves/,/to approve`/,/waits? for your approval/,/Review (changes|moves)/,/Renames and moves/,/Leave as it is/,/Offer again/,/Series changes ·/,/moves-shortcut|moves-dialog/,/only after you approve it/])
  {assert.doesNotMatch(html,gone,String(gone));assert.doesNotMatch(pageSource,gone,String(gone));}
assert.match(css,/:root \.field-help\{font-size:13px;color:var\(--muted\)/,'the quiet line has the help lines\' look: 13 px, muted');
// Layout by construction (section 8): everything new is in normal flow, one line, with the look and the reserved height.
const rule=selector=>{const found=css.match(new RegExp(selector.replace(/[.#]/g,'\\$&')+'\\{([^}]*)\\}'));assert.ok(found,selector);return found[1];};
assert.doesNotMatch(css,/#jobs-series-found[^{]*\{[^}]*(position|float|z-index)/,'the quiet line is in normal flow');
assert.match(rule('#jobs-state'),/white-space:nowrap/);assert.match(rule('#jobs-state'),/font-size:15px;font-weight:600/);assert.match(rule('#jobs-state'),/padding:0 8px;border:1px solid/);
for(const selector of ['#jobs-state','#jobs-state.state-done','#jobs-state.state-you','#jobs-state.state-background','#jobs-status','#jobs-you .jobs-you'])
  assert.doesNotMatch(rule(selector),/position\s*:|float\s*:|z-index|margin[^;]*-\d/,selector+': normal flow only');
assert.match(rule('#jobs-state.state-done'),/background:var\(--notice\);color:var\(--notice-text\);border-color:var\(--notice-border\)/);
assert.match(rule('#jobs-state.state-you'),/background:var\(--surface\);color:var\(--warning\);border-color:var\(--warning\)/);
assert.match(rule('#jobs-state.state-background'),/background:var\(--raised\);color:var\(--text\);border-color:var\(--border\)/);
assert.match(rule('#jobs-status'),/min-height:23px/,'the line keeps the badge height (21 px line + 2 px border) with and without it');
assert.match(css,/\[hidden\]\{display:none!important\}/,'a hidden badge takes no room');
// needs_you_only is no longer read by the page (section 6).
assert.doesNotMatch(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8').replace(/\/\/[^\n]*/g,''),/needs_you_only/);
console.log('PASS 0.31.0 finished state: three badges, no bare Nothing running, on hold part, singulars, no flicker, look-up rows, as-of, automatic suffix, markup and flow');

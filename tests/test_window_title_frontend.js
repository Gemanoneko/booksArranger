'use strict';
// 0.31.0 (Judy's Docs/BooksArranger_0.31.0_UX.md, section 1.5, check 23; Sergei's R13 of 2026-11-22): the main window's
// title ends with the state, in the status line's own words, so the taskbar and Alt+Tab answer without opening the window.
// One title per engine state; it follows what the status line shows (never ahead of the badge) and is written only when it
// changes. The shell needs nothing for it: an Electron window takes its page's title unless the shell prevents that, and
// desktop/main.js does not. The real renderJobs against owned DOM doubles; nothing is launched.
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
// The document's title is the page's <title> at first; every write is recorded (the title changes only with the state).
const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
assert.match(html,/<title>Books Arranger<\/title>/,'the name alone until the page knows the state');
const written=[];let shownTitle='Books Arranger';
const document={activeElement:null,getElementById:get,querySelector:()=>({content:'fixture'}),querySelectorAll:()=>[],createElement:tag=>{const element=new Element();element.tag=tag;if(tag==='progress')element.value=null;return element;},
  get title(){return shownTitle;},set title(value){written.push(value);shownTitle=value;}};
const context=vm.createContext({document,console,URL,location:{origin:'http://127.0.0.1:5210'},setTimeout:()=>0,clearTimeout(){},fetch:async()=>({ok:true,json:async()=>({})})});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8').replace(/viewControls\(\);poll\(\);\s*$/,''),context);
const run=code=>vm.runInContext(code,context);
const NOW=Date.now();
const jobsBase={state:'Completed',approved_total:1510,converted_total:1510,queued:0,failed:0,attention_counts:{},candidate_total:1510,not_approved_total:0};
const pending=(more={})=>({any:true,running:0,paused:0,waiting:0,still_checking:0,attention:0,hold:0,moves:0,writes:0,drives:0,lookups:{series:0,details:0,all:0},same_name:0,...more});
// One poll; settle: the same state has been reported for 3 s, so the badge is up.
function show(work,jobs={},settle=true){
  context.fixture={audiobook_jobs:{...jobsBase,...jobs},work:{rows:[],waiting:[],counts:{},unread:[],snapshot_age_ms:0,refreshing:false,pending:pending(),waits_for_you:[],background:{},lookups_waiting:[],...work}};
  run('state=fixture;renderJobs()');if(settle)run('badgeSeen.since-=3000;renderJobs()');
  return document.title;
}
const reset=()=>run('badgeSeen={state:null,since:0};badgeShown=null;unreadSince.clear()');
const conversion=(subject='Dune')=>({id:'conversion:'+subject,kind:'conversion',subject,job_id:'j-'+subject,book_id:'b1',step:'encoding',done:100,total:1000,unit:'seconds',state:'running',started:NOW-60000,background:false});
const series=(step='looking_up')=>({id:'series',kind:'series',subject:'Тёмный лес',step,done:691,total:903,unit:'books',state:'running',started:NOW-60000,background:step!=='updating'});

// 1. One title for every value the engine sends (table 1.5).
for(const [state,work,jobs,title] of [
  ['all_done',{pending:pending({any:false})},{},'Books Arranger: all done'],
  ['waiting_for_you',{waits_for_you:['attention'],pending:pending({attention:3})},{attention_counts:{other:3}},'Books Arranger: waiting for you'],
  ['background_only',{pending:pending({lookups:{series:212,details:0,all:212}})},{},'Books Arranger: background look-ups only'],
  ['working',{rows:[conversion()]},{state:'Running'},'Books Arranger: working'],
  ['paused',{},{state:'Paused'},'Books Arranger: paused'],
  ['continues',{counts:{queued_conversions:3}},{},'Books Arranger: continues by itself'],
  ['unknown',{},{},'Books Arranger: checking what is left']]){
  reset();assert.equal(show({state,...work},jobs),title,state);
  // The words are the status line's own, in lower case, so the two never disagree.
  const said=(get('jobs-state').hidden?'':get('jobs-state').textContent) || get('jobs-status-text').textContent.split(' · ')[0];
  if(state!=='working')assert.equal(title,'Books Arranger: '+said.toLowerCase(),state+': '+said);
}
// Every state starts with a different word, so a taskbar label cut short still tells them apart.
const starts=['all done','waiting for you','background look-ups only','working','paused','continues by itself','checking what is left'].map(words=>words.split(' ')[0]);
assert.equal(new Set(starts).size,starts.length);

// 2. Not known with a source unread, the engine not answering, and before the jobs part has loaded: the name alone.
reset();run('unreadSince.set("workers",'+(NOW-4000)+')');
context.fixture={audiobook_jobs:jobsBase,work:{rows:[],waiting:[],counts:{},unread:['workers'],state:'unknown',pending:pending()}};run('state=fixture;renderJobs()');
assert.match(get('jobs-status-text').textContent,/^Nothing running that could be read · /);assert.equal(document.title,'Books Arranger','a source really unread');
reset();show({state:'all_done',pending:pending({any:false})});assert.equal(document.title,'Books Arranger: all done');
run('busyShown=true;renderJobs()');assert.match(get('jobs-status-text').textContent,/^Last confirmed — /);assert.equal(document.title,'Books Arranger','the engine is not answering now: no state is claimed');
run('busyShown=false;renderJobs()');assert.equal(document.title,'Books Arranger: all done');
context.fixture={};run('state=fixture;renderJobs()');assert.equal(document.title,'Books Arranger','no jobs part');
reset();assert.equal(show({state:''}),'Books Arranger: checking what is left','an engine that sends no state: the page is still confirming, as its status line says');

// 3. Never ahead of the badge (1.2): in the 3 s before a badge comes up the title reads "checking what is left", never a
// finished state the badge has not confirmed; and a job under 1 s does not take the finished title away.
reset();
assert.equal(show({state:'all_done',pending:pending({any:false})},{},false),'Books Arranger: checking what is left');assert.equal(get('jobs-state').hidden,true);
run('badgeSeen.since-=2900;renderJobs()');assert.equal(document.title,'Books Arranger: checking what is left','2.9 s: not yet');
run('badgeSeen.since-=200;renderJobs()');assert.equal(document.title,'Books Arranger: all done');assert.equal(get('jobs-state').hidden,false);
assert.equal(show({state:'working',rows:[]},{state:'Running'},false),'Books Arranger: all done','the badge is still up: so is its title');
run('badgeSeen.since-=1000;renderJobs()');assert.equal(get('jobs-state').hidden,true);assert.notEqual(document.title,'Books Arranger: all done');

// 4. It changes only when the state changes: polls in the same state write nothing, and while working the title does not
// follow the book (a title that changed with every book would flicker in the taskbar).
reset();show({state:'working',rows:[conversion('Dune')]},{state:'Running'});
const before=written.length;
for(const book of ['Dune','Оно','Граф Ноль','Тёмный лес'])assert.equal(show({state:'working',rows:[conversion(book)]},{state:'Running'},false),'Books Arranger: working');
show({state:'working',rows:[conversion('Dune'),conversion('Оно')]},{state:'Running'},false);
assert.match(get('jobs-status-text').textContent,/^2 tasks running · /);assert.equal(document.title,'Books Arranger: working');
assert.equal(written.length,before,'five more polls of the same state: the title was not written again');
reset();show({state:'continues',counts:{queued_conversions:1}});const at=written.length;
assert.equal(document.title,'Books Arranger: continues by itself');assert.equal(written.length,at);
show({state:'continues',counts:{queued_conversions:2}});assert.equal(written.length,at);

// 5. It follows what the status line shows, not only the engine's word.
// A main row the engine does not report under a finished state (a page-owned loop): the line names it, the title says working.
reset();assert.equal(show({state:'all_done',pending:pending({any:false}),rows:[conversion()]},{state:'Running'}),'Books Arranger: working');
// A look-up row alone is no main work: the badge leads, and its title.
reset();assert.equal(show({state:'background_only',pending:pending({lookups:{series:1,details:0,all:1}}),rows:[series()]}),'Books Arranger: background look-ups only');
// Writing a series into a finished file is main work (third round): working, never a finished title.
reset();assert.equal(show({state:'working',pending:pending({writes:1}),rows:[series('updating')]}),'Books Arranger: working');
// A paused queue that names a look-up still running (G7) is paused.
reset();assert.equal(show({state:'paused',rows:[series()]},{state:'Paused'}),'Books Arranger: paused');assert.match(get('jobs-status-text').textContent,/^Paused · Finding series/);
reset();assert.equal(show({state:'paused'},{state:'Pausing'}),'Books Arranger: paused');
assert.match(get('jobs-status-text').textContent,/^Pausing audiobook jobs…/,'a queue still pausing keeps its own words');
// R31 (Sergei 2026-11-23; Futaba's 0.31.0 M1): Stop automatic processing. The engine says paused while the audiobook queue
// itself is not paused: the status line and the title say Paused at the first poll, never "checking what is left".
reset();assert.equal(show({state:'paused',waits_for_you:['attention'],pending:pending({attention:4})},{attention_counts:{other:4}},false),'Books Arranger: paused','at once');
assert.match(get('jobs-status-text').textContent,/^Paused · /);assert.equal(get('jobs-state').hidden,true,'Paused is no finished state: no badge');
reset();assert.equal(show({state:'unknown',waits_for_you:['attention'],pending:pending({attention:4})},{attention_counts:{other:4}},false),'Books Arranger: checking what is left','control: an engine still counting');
// A drive that is not answering (R14): waiting for you.
reset();assert.equal(show({state:'waiting_for_you',waits_for_you:['drive'],pending:pending({drives:1}),waiting:[{id:'drive:Z',kind:'drive',subject:'Z:\\Audiobooks'}]}),'Books Arranger: waiting for you');
// Books with a series found that is not applied do not change it (check 26).
reset();assert.equal(show({state:'all_done',pending:pending({any:false,moves:61})}),'Books Arranger: all done');

// 6. Only these titles are ever written.
const allowed=new Set(['Books Arranger',...['all done','waiting for you','background look-ups only','working','paused','continues by itself','checking what is left'].map(words=>'Books Arranger: '+words)]);
for(const title of written)assert.ok(allowed.has(title),title);

// 7. F3, the shell: an Electron window's title follows its page's title unless a page-title-updated handler prevents it.
// The main window is created with the name alone and the shell neither prevents nor sets a title afterwards, so the page's
// title is the window's, the taskbar's and Alt+Tab's. Only the main window: the set-up window has its own page and title.
const shell=fs.readFileSync(path.join(__dirname,'../desktop/main.js'),'utf8');
assert.match(shell,/show: false, title: 'Books Arranger', backgroundColor/,'the main window starts with the name alone');
assert.doesNotMatch(shell,/page-title-updated/,'nothing stops the window from taking the page\'s title');
assert.doesNotMatch(shell,/\.setTitle\(/,'and the shell sets no title of its own later');
assert.match(shell,/title:'Books Arranger — Choose data folder'/,'the set-up window keeps its own title');
assert.doesNotMatch(fs.readFileSync(path.join(__dirname,'../desktop/setup.html'),'utf8'),/app\.js/,'the set-up window does not load the page that writes the title');
// No flash, focus or sound comes with it: the page only writes document.title.
const page=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8'),body=page.slice(page.indexOf('function renderWindowTitle'),page.indexOf('function renderBadge'));
assert.doesNotMatch(body,/focus|flash|Audio|Notification|alert/);
console.log('PASS 0.31.0 window title: one title per state, the plain name when not known, never ahead of the badge, written only on a change, working without the book, the shell takes the page title');

// Startup in the page (ruling 28; Judy's 0.22.1 UX spec, 3.2-3.7): the first frame from disk, the load strip's states
// from a fake clock, every part withheld in turn renders no digit, controls that wait for loading say why (and a press
// is answered in the message line), Stopped, Restart engine, and the settle. app.js with load-state.js in a vm; no browser.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const ALL={library:true,status:true,books:true,attention:true,jobs:true};
const STATUS={state:'completed',count:52311,checked:0,reused:0,pending:0,errors:0,unresolved_errors:0,current:'',scan_issues:[]};
const JOBS={state:'Paused',queued:0,failed:0,jobs:[],attention_counts:{retry:0},candidate_total:600,not_approved_total:100,approved:500,converted:430};
const AUTOMATIC={state:'Idle',can_start:true,can_stop:false,research:{researching:0,waiting:0,held:0}};

function harness({protocol='http:',desktop=true}={}){
  const nodes=new Map(),fields=new Map(),listeners={};let clock=1000000;
  function make(id='',tag='div'){
    let text='';const attributes=new Map(),classes=new Set();
    const element={id,tagName:tag.toUpperCase(),value:id==='library'?'Audiobooks':'',hidden:false,disabled:false,title:'',dataset:{},style:{},children:[],handlers:{},readOnly:false,
      get textContent(){return text;},set textContent(value){text=String(value);},
      addEventListener(type,fn){this.handlers[type]=fn;},
      setAttribute(name,value){attributes.set(name,String(value));},getAttribute(name){return attributes.has(name)?attributes.get(name):null;},
      hasAttribute(name){return attributes.has(name);},removeAttribute(name){attributes.delete(name);},
      classList:{add:name=>classes.add(name),remove:name=>classes.delete(name),contains:name=>classes.has(name),toggle(name,force){const on=force===undefined?!classes.has(name):!!force;if(on)classes.add(name);else classes.delete(name);return on;}},
      replaceChildren(...items){this.children=items;text=items.map(item=>typeof item==='string'?item:item.textContent).join('');},
      append(...items){this.children.push(...items);},insertAdjacentElement(_where,child){nodes.set(child.id,child);},
      focus(){},contains:()=>false,closest(){return attributes.has('data-not-yet')?this:null;},
      get firstElementChild(){return this.children[0];}};
    return element;
  }
  function node(id){if(!nodes.has(id))nodes.set(id,make(id,['library','view','filter'].includes(id)?'select':['search','select-page'].includes(id)?'input':'button'));return nodes.get(id);}
  for(const name of ['original_language','title','author','canonical_author','narrator','universe','series','number','genre','topic','multi_author','anthology'])fields.set(name,{value:'',checked:false,options:[{}],append(value){this.options.push(value);}});
  node('review-form').elements={namedItem:name=>fields.get(name)};
  node('select-page').type='checkbox';node('search').type='search';
  const segments=[0,1,2,3].map(i=>{const segment=make('segment-'+i);segment.children=[make('fill-'+i)];return segment;});
  // The page's own initial placeholders (index.html).
  const initial={status:'Library status: loading…',root:'Source folders: loading…','automatic-status':'Automatic processing: loading…','research-status':'Research: loading…',
    'jobs-status':'Jobs: loading…','book-candidate-counts':'Book candidates: loading…',empty:'Loading your books…',page:'Loading your books…','automatic-start-reason':'Automatic processing can start when loading finishes.'};
  for(const [id,text] of Object.entries(initial))node(id).textContent=text;
  node('jobs-idle').hidden=true;node('version').hidden=true;node('load-actions').hidden=true;node('load-details').hidden=true;node('load-restart').hidden=true;node('load-retry').hidden=true;
  // M3 (Judy's implementation check): the book list's body is busy while the books part is missing; <body> never is,
  // so the live regions under it (#load-announce) are not held while loading.
  const body=make('body');node('inventory').setAttribute('aria-busy','true');
  let answer=null,mode='answer',calls={state:0,inventory:0},startupListener=null,restarts=0;
  const shell={startup:async()=>startupValue,onStartup:fn=>{startupListener=fn;},restartEngine:async()=>{restarts++;return true;}};
  let startupValue={phase:'launching',startedAt:clock-500,lastLoadMs:99000,exited:null,portPid:null};
  const response=(value,ok=true,status=200)=>({ok,status,json:async()=>value});
  class FakeDate extends Date{static now(){return clock;}}
  const context=vm.createContext({console,Date:FakeDate,location:{protocol,origin:'http://127.0.0.1:5212'},window:desktop?{booksDesktop:shell}:{},
    document:{body,getElementById:id=>['connection-notice','inventory-intro'].includes(id)?nodes.get(id)||null:node(id),
      querySelector:()=>({content:'fixture-token'}),
      querySelectorAll:selector=>selector==='#load-bar .load-segment'?segments:selector==='[data-not-yet]'?[...nodes.values()].filter(item=>item.hasAttribute('data-not-yet')):[],
      createElement:tag=>make('',tag),addEventListener:(type,fn)=>{(listeners[type] ||= []).push(fn);},activeElement:null},
    setTimeout:()=>0,clearTimeout(){},
    fetch:async route=>{
      if(route.startsWith('/api/state')){calls.state++;if(mode==='silent')return new Promise(()=>{});if(mode==='busy')return response({error:'Status is still updating; retrying'},false,503);return response(JSON.parse(JSON.stringify(answer)));}
      if(route.startsWith('/api/inventory')){calls.inventory++;return response({rows:[],total:0});}
      throw new Error('Unexpected fixture route '+route);
    }});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/load-state.js'),'utf8'),context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8'),context);
  const press=(target,type='click')=>{const event={type,key:'Enter',target,prevented:false,stopped:false,preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;}};for(const fn of listeners[type] || [])fn(event);return event;};
  return {node,body,context,calls,segments,press,
    get clock(){return clock;},advance(ms){clock+=ms;vm.runInContext('loadTick()',context);},jump(ms){clock+=ms;},
    set answer(value){answer=value;},set mode(value){mode=value;},
    get restarts(){return restarts;},
    startup(value){startupValue={...startupValue,...value};startupListener?.(startupValue);},
    poll:()=>vm.runInContext('poll()',context),run:code=>vm.runInContext(code,context)};
}
const loading=(extra={})=>({step:'session',n:3,of:4,done:120,total:508,unit:'items',progress_age_ms:0,waiting_for:null,restart_safe:true,parts:{library:true,status:true,books:false,attention:false,jobs:false},took_ms:null,error:'',...extra});
const answerWith=(load,parts)=>{const value={application:'Books Arranger',version:'0.22.1',library:'Audiobooks',root:'C:/fixture/Audiobooks',source_roots:['C:/fixture/Audiobooks'],libraries:['Audiobooks','Podcasts','Ebooks'],genres:['Horror'],audiobook_output_root:'C:/fixture/Sorted',active_library:null,stopping:false,loading:load};
  if(load.parts.status)value.status=STATUS;if(load.parts.jobs)Object.assign(value,{audiobook_jobs:JOBS,automatic_processing:AUTOMATIC,activities:[]});return value;};
const digitFree=(h,ids)=>{for(const id of ids)assert.doesNotMatch(h.node(id).textContent,/\d/,`${id} shows no number before its part: "${h.node(id).textContent}"`);};

(async()=>{
  // 1. The first frame from disk: Step 1, every placeholder, no request to an engine that does not exist yet.
  {
    const h=harness({protocol:'file:'});await flush();
    assert.equal(h.calls.state,0,'the first frame asks no engine');
    assert.equal(h.node('load-word').textContent,'Working');assert.equal(h.node('load-text').textContent,'Step 1 of 4: Starting the engine');
    assert.match(h.node('load-detail').textContent,/running 0:00 · no answer from the engine yet · last load took 1 min 39 s/);
    assert.equal(h.node('filter').children.length,1);assert.equal(h.node('filter').children[0].textContent,'Loading…');
    assert.equal(h.node('version').hidden,true);assert.equal(h.node('jobs-idle').hidden,true);
    digitFree(h,['status','root','automatic-status','research-status','jobs-status','book-candidate-counts','empty','page']);
    assert.equal(h.node('start').getAttribute('aria-disabled'),'true');assert.equal(h.node('start').disabled,false,'inert, never the disabled attribute');
    assert.equal(h.node('start').title,'Not yet: Books Arranger is still loading. This works when loading finishes.');
    assert.equal(h.node('library').title,'Not yet: Books Arranger is still loading. You can switch library when loading finishes.');
    assert.equal(h.node('filter').title,'Not yet: your books are still loading. This works as soon as they appear.');
    const event=h.press(h.node('start'));
    assert.equal(event.prevented && event.stopped,true,'the press does nothing else');
    assert.equal(h.node('message').textContent,'Not yet: Books Arranger is still loading. This works when loading finishes.');
    // No answer: Waiting at 3 s, Stuck at 10 s, with Restart engine (desktop), Copy details and Technical details.
    h.advance(2600);assert.equal(h.node('load-word').textContent,'Waiting');
    assert.equal(h.node('load-text').textContent,"Step 1 of 4: Starting the engine. The engine hasn't answered for 3 s.");
    for(let s=0;s<7;s++)h.advance(1000);  // one tick a second: a longer gap is a sleep (3.4)
    assert.equal(h.node('load-word').textContent,'Stuck');
    assert.equal(h.node('load-actions').hidden,false);assert.equal(h.node('load-restart').hidden,false);assert.equal(h.node('load-details').hidden,false);
    assert.equal(h.node('load-announce').textContent,"Loading is stuck. The engine hasn't answered for 10 s. Restart engine is available.");
    await h.node('load-restart').handlers.click();assert.equal(h.restarts,1);assert.equal(h.node('load-announce').textContent,'Restarting the engine.');
    // The shell reports the exit: Stopped, its last lines, Try again; placeholders become "not loaded".
    h.startup({phase:'stopped',exited:{code:1,lastLines:'RuntimeError: Pending output moves need recovery first'}});
    assert.equal(h.node('load-word').textContent,'Stopped');assert.equal(h.node('load-text').textContent,'The engine stopped while loading. Your files are not touched.');
    assert.equal(h.node('inventory').getAttribute('aria-busy'),null,'stopped: nothing is on its way, so the list is not busy');
    assert.equal(h.node('load-retry').hidden,false);assert.equal(h.node('load-restart').hidden,true);assert.equal(h.node('load-detail').hidden,true);
    assert.match(h.node('load-technical').textContent,/Pending output moves need recovery first/);
    assert.equal(h.node('status').textContent,'Library status: not loaded.');assert.equal(h.node('empty').textContent,'Your books are not loaded.');
    assert.equal(h.node('jobs-status').textContent,'Jobs: not loaded.');assert.equal(h.node('book-candidate-counts').textContent,'Book candidates: not loaded.');
    assert.equal(h.node('load-announce').textContent,'Books Arranger stopped loading. Try again is available.');
    // A taken port names the other process.
    const p=harness({protocol:'file:'});await flush();p.startup({phase:'stopped',portPid:4321,exited:{code:1,lastLines:''}});
    assert.equal(p.node('load-text').textContent,'Another copy of Books Arranger is running (process 4321). Quit it from the tray, then try again.');
  }
  // 2. Every part withheld in turn renders no digit for it; the list is not read before the books part.
  for(const withheld of ['status','jobs','attention','books']){
    const h=harness();h.answer=answerWith(loading({parts:{...ALL,[withheld]:false}}));await h.poll();await flush();
    if(withheld==='status')digitFree(h,['status']);
    if(withheld==='jobs')digitFree(h,['jobs-status','book-candidate-counts','automatic-status','research-status']);
    assert.equal(h.body.getAttribute('aria-busy'),null,'never on <body>');
    if(withheld==='books'){assert.equal(h.node('inventory').getAttribute('aria-busy'),'true','busy while the books part is missing');digitFree(h,['empty','page']);assert.equal(h.calls.inventory,0,'no list read before the books part');assert.equal(h.node('filter').title,'Not yet: your books are still loading. This works as soon as they appear.');}
    else{assert.equal(h.node('load-word').textContent,'Working');}
    assert.equal(h.node('version').hidden,true,'the version shows only after loading');
  }
  // 3. Progress silence while answering: Waiting at 10 s, Stuck at 30 s, Working again when it moves; a sleep gap is not Stuck.
  {
    const h=harness();await flush();
    h.answer=answerWith(loading({progress_age_ms:0}));await h.poll();
    assert.equal(h.node('load-text').textContent,'Step 3 of 4: Checking the last session');
    assert.match(h.node('load-detail').textContent,/120 of 508 items · running 0:00 · engine answered 0 s ago · last load took 1 min 39 s/);
    for(let s=1;s<=14;s++){h.jump(1000);h.answer=answerWith(loading({progress_age_ms:s*1000}));await h.poll();h.advance(0);}
    assert.equal(h.node('load-word').textContent,'Waiting');
    assert.equal(h.node('load-text').textContent,'Step 3 of 4: Checking the last session. Nothing new for 14 s. The engine is still answering.');
    for(let s=15;s<=31;s++){h.jump(1000);h.answer=answerWith(loading({progress_age_ms:s*1000}));await h.poll();h.advance(0);}
    assert.equal(h.node('load-word').textContent,'Stuck');assert.equal(h.node('load-restart').hidden,false);
    assert.ok(h.segments[2].classList.contains('alert'),'the current segment turns --warning');
    h.answer=answerWith(loading({progress_age_ms:0,restart_safe:false}));await h.poll();
    assert.equal(h.node('load-word').textContent,'Working');assert.equal(h.node('load-announce').textContent,'Loading is moving again.');
    h.jump(60000);h.advance(1000);assert.notEqual(h.node('load-word').textContent,'Stuck','a sleep gap restarts the clocks');
    for(let s=1;s<=31;s++){h.jump(1000);h.answer=answerWith(loading({progress_age_ms:s*1000,restart_safe:false}));await h.poll();h.advance(0);}
    assert.equal(h.node('load-restart').getAttribute('aria-disabled'),'true');
    assert.equal(h.node('load-restart').title,'Not safe right now: the engine is changing the catalog. Wait for it to finish.');
    await h.node('load-restart').handlers.click();assert.equal(h.restarts,0);assert.equal(h.node('message').textContent,'Not safe right now: the engine is changing the catalog. Wait for it to finish.');
    // N4 (Judy's implementation check): the announcement never offers a Restart engine that is inert.
    assert.equal(h.node('load-announce').textContent,'Loading is stuck. No progress for 30 s. The engine is changing the catalog, so Restart engine waits.');
    // A "still updating" answer is an answer: no engine-quiet line.
    h.mode='busy';for(let s=0;s<5;s++){h.jump(1000);await h.poll();h.advance(0);}
    assert.doesNotMatch(h.node('load-text').textContent,/hasn't answered/);
  }
  // 4. Settle: every part, took_ms and the first list on screen; one pass makes everything live.
  {
    const h=harness();await flush();
    h.answer=answerWith(loading({step:'books',n:4,parts:ALL,took_ms:null}));await h.poll();await flush();
    assert.equal(h.node('filter').getAttribute('aria-disabled'),null,'looking works once the books are on screen');
    assert.equal(h.node('start').getAttribute('aria-disabled'),'true','changing still waits');
    h.press(h.node('start'));
    h.node('load-strip').getBoundingClientRect=()=>({height:111.5});  // the loading strip's rendered height
    h.answer=answerWith(loading({step:'done',n:4,parts:ALL,took_ms:99400}));await h.poll();await flush();
    assert.equal(h.node('load-word').textContent,'Ready');assert.equal(h.node('load-text').textContent,'Loaded in 1 min 39 s');
    // Futaba's 0.22.1 QA, m-6: the settled strip keeps the height it had while loading (Judy 3.7, the fallback), so
    // Quit and everything under it never move (they moved 53 px; the limit is 48).
    assert.equal(h.node('load-strip').style.minHeight,'111.5px');
    for(const id of ['load-bar','load-detail','load-actions','load-details'])assert.equal(h.node(id).hidden,true,id);
    assert.equal(h.node('start').hasAttribute('data-not-yet'),false);assert.equal(h.node('start').getAttribute('aria-disabled'),null);
    assert.notEqual(h.node('start').title,'Not yet: Books Arranger is still loading. This works when loading finishes.');
    assert.equal(h.node('message').textContent,'','the Not yet sentence leaves the message line');
    assert.equal(h.body.getAttribute('aria-busy'),null);assert.equal(h.node('inventory').getAttribute('aria-busy'),null,'the books arrived');
    assert.equal(h.node('load-announce').textContent,'Books Arranger is ready.');
    assert.equal(h.node('version').textContent,'v0.22.1');assert.equal(h.node('version').hidden,false);
    assert.match(h.node('status').textContent,/Files cataloged 52311/);
    h.press(h.node('start'));assert.equal(h.node('message').textContent,'','after the settle a press is the control\'s own');
  }
  // 5. An engine without a loading object is loaded: no strip at all.
  {
    const h=harness({desktop:false});await flush();
    const value=answerWith(loading({parts:ALL}));delete value.loading;h.answer=value;await h.poll();await flush();
    assert.equal(h.node('load-strip').hidden,true);assert.equal(h.node('start').getAttribute('aria-disabled'),null);
  }
  console.log('PASS startup: first frame, states from silence, parts withheld, inert controls, Stopped, restart_safe, settle');
})().catch(error=>{console.error(error);process.exitCode=1;});

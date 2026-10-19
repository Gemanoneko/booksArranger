'use strict';
// RefusedRetry spec (Judy, 2026-10-19), section 7 checks on seeded rows: the refused row's status, hint, controls and
// Technical detail per typed cause; the stale state; the "· N left out" count; focus when a Retry goes away; and the
// pressed row held in Can retry showing its refusal. Real frontend on the Retry test's DOM/transport doubles.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
// A text node for the status cell's own text (statusInPlace changes it without rebuilding the row).
Object.defineProperty(Element.prototype,'firstChild',{get(){const element=this;return element.textContent?{nodeType:3,get nodeValue(){return element.textContent;},set nodeValue(value){element.textContent=value;}}:null;}});
const M4B_REASON='M4B preservation requires review: Unsupported structural box';
function m4bRow(name,job={}){
  return blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name}},
    {job_id:'job-'+name,reason:M4B_REASON,attention:{group:'retry',cause:null,originals_untouched:true},retry:{allowed:true,reason:''},...job});
}
function refusedRow(name,cause,extra={},job={}){
  const fix={unsupported_file:'update',working_files:'wait',source_changed:'review',file_problem:'user',unknown:'update'}[cause];
  const group=cause==='unsupported_file'?'unsupported':'other',retry=fix==='user'?{allowed:true,reason:''}:fix==='wait'?{allowed:false,reason:NOT_YET}:undefined;
  return m4bRow(name,{attention:{group,cause:null,originals_untouched:true},retry,readmission:{accepted:false,queued_next:false,kind:'retry',state:'refused',
    reason:'Failed M4B retained: Unsupported structural box',cause,fix,app_version:'0.19.0',key:'k',at:'2026-10-19T08:00:00+00:00',stale:false,...extra},...job});
}
function statusCell(tr){return tr.children[4];}
function actionButtons(tr){return tr.children[5].children[0].children;}
function rowOf(name){return [...get('inventory').children].find(tr=>tr.dataset.path==='cand-'+name);}
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');}
const BANNED=/retained|structural|\bbox\b|brand|atom|table|extent|proof|admission|preservation|parent|child/i;
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";viewControls()');

  // Observed case: unsupported_file. No Retry anywhere, the UI's words, both raw facts only in Technical detail.
  const refused=refusedRow('u','unsupported_file');paint([refused]);
  let tr=rowOf('u');
  assert.equal(statusCell(tr).textContent,"Can't convert — M4B not supported");
  assert.equal(statusCell(tr).children[0].textContent,"Retry was refused: the app doesn't support how this M4B is built. Nothing to do for now. Originals are untouched.");
  assert.ok(statusCell(tr).children[0].classes.has('retry-refused'),'--warning, the existing refused mechanism');
  assert.ok(![...actionButtons(tr)].some(button=>/Retry|Repair/.test(button.textContent)),'no Retry, not even disabled');
  const left=[...actionButtons(tr)].filter(button=>button.type==='button').map(button=>button.textContent);assert.equal(left.length,2);assert.equal(left[0],'View metadata');assert.match(left[1],/^(Source folders|Open folder)$/);
  assert.equal(statusCell(tr).title,'Technical detail: Failed M4B retained: Unsupported structural box; earlier failure: '+M4B_REASON);
  context.fixture=refused;run('select(fixture,true);controls()');
  assert.equal(get('retry-block').hidden,true,'the details panel has no Retry either');
  assert.equal(get('automatic-result-status').textContent,"Can't convert — M4B not supported");
  assert.equal(get('automatic-technical').textContent,'Technical detail: Failed M4B retained: Unsupported structural box; earlier failure: '+M4B_REASON);
  assert.equal(run('attentionText('+JSON.stringify(refusedRow('v','unsupported_file',{},{attention:{group:'unsupported',cause:null,originals_untouched:false}}))+').hint'),
    "Retry was refused: the app doesn't support how this M4B is built. Nothing to do for now.",'the sentence only where the app confirms it');
  // Positive control: an M4B row with no refusal is still ready, Retry enabled.
  paint([m4bRow('p')]);tr=rowOf('p');
  assert.equal(statusCell(tr).textContent,'Stopped — ready to retry');assert.equal(actionButtons(tr)[0].textContent,'Retry');assert.equal(actionButtons(tr)[0].disabled,false);

  // Every cause: status and hint from the copy map; behaviour from the fix; none of the internal words.
  // working_files: superseded by follow-up 2, section 2.2 (the live state of the files decides, see test_working_frontend.js);
  // source_changed: the hint names Start over (follow-up 2, section 1.2).
  const expected={
    source_changed:['Stopped — review changed',"Retry was refused: the book's review or source files changed. Start over sends it back to automatic processing."],
    file_problem:['Stopped — file problem',"Retry was refused: the app couldn't read or write a file. Check the folder, then retry."],
    unknown:['Stopped — retry refused','Retry was refused. Select the row to read why.']};
  for(const [cause,[status,hint]] of Object.entries(expected)){
    const text=run('attentionText('+JSON.stringify(refusedRow('c',cause))+')');
    assert.equal(text.status,status,cause);assert.equal(text.hint,hint,cause);assert.equal(text.warn,true,cause);
    assert.doesNotMatch(text.status+' '+text.hint,BANNED,cause);
  }
  assert.doesNotMatch(run('attentionText('+JSON.stringify(refused)+').hint'),BANNED);
  for(const missing of [{cause:undefined,fix:undefined},{cause:'from_the_future',fix:undefined}]){
    const text=run('attentionText('+JSON.stringify(refusedRow('m','unknown',missing))+')');
    assert.deepEqual([text.status,text.hint],expected.unknown,'a missing or unrecognised cause reads as unknown');
  }
  // The verb follows the refusal's kind (follow-up point 3b): a refused Repair never says "retry".
  assert.equal(run('attentionText('+JSON.stringify(refusedRow('r','file_problem',{kind:'repair'}))+').hint'),"Repair was refused: the app couldn't read or write a file. Check the folder, then repair.");
  paint([refusedRow('w','working_files'),refusedRow('s','source_changed'),refusedRow('f','file_problem'),refusedRow('k','unknown')]);
  const waiting=actionButtons(rowOf('w'))[0];
  assert.equal(waiting.textContent,'Retry');assert.equal(waiting.disabled,true);assert.equal(waiting.title,NOT_YET,'tooltip exactly as section 3');
  assert.equal(statusCell(rowOf('w')).children[0].textContent,NOT_YET,'the same text in the hint while disabled');
  assert.ok(![...actionButtons(rowOf('s'))].some(button=>button.textContent==='Retry'),'review: no control');
  assert.ok(![...actionButtons(rowOf('k'))].some(button=>button.textContent==='Retry'),'unknown: no control');
  assert.equal(actionButtons(rowOf('f'))[0].textContent,'Retry');assert.equal(actionButtons(rowOf('f'))[0].disabled,false,'file problem: Sergei can fix it');
  assert.equal(actionButtons(rowOf('f'))[0].title,READY);
  paint([refusedRow('w','working_files',{},{retry:{allowed:true,reason:''}})]);
  assert.equal(actionButtons(rowOf('w'))[0].disabled,false,'enabled once the folder check passes');

  // Stale (the deciding code changed): Stopped — try again, muted, Retry enabled; the version when known.
  const stale=refusedRow('t','unsupported_file',{stale:true,app_version:'0.18.0'},{attention:{group:'retry',cause:null,originals_untouched:true},retry:{allowed:true,reason:''}});
  paint([stale]);tr=rowOf('t');
  assert.equal(statusCell(tr).textContent,'Stopped — try again');
  assert.equal(statusCell(tr).children[0].textContent,'Retry was refused in v0.18.0; the app was updated since. It may work now.');
  assert.equal(statusCell(tr).children[0].classes.has('retry-refused'),false,'--muted: information, not an obstacle');
  assert.equal(actionButtons(tr)[0].textContent,'Retry');assert.equal(actionButtons(tr)[0].disabled,false);
  assert.equal(run('attentionText('+JSON.stringify(refusedRow('t','unsupported_file',{stale:true,app_version:''},{attention:{group:'retry',cause:null,originals_untouched:true}}))+').hint'),
    'Retry was refused before the app was updated. It may work now.');
  assert.equal(run('candidateStatus('+JSON.stringify(refusedRow('t','unsupported_file',{stale:true},{attention:{group:'unsupported',cause:null,originals_untouched:true}}))+')'),
    "Can't convert — M4B not supported",'refused again by this build\'s own check: the group says so');

  // Selection: the tick stays; the bulk count leaves the refused book out and says so.
  paint([m4bRow('a'),m4bRow('b'),refused]);
  run('for(const row of rows)selectedBooks.set(row.id,row.revision);renderRows(true);batchCounts();controls()');
  assert.equal(get('batch-count').textContent,'3 selected · 2 can be retried or repaired · 1 left out');
  assert.equal(get('retry-selected').textContent,'Retry selected (2)');
  paint([m4bRow('a'),m4bRow('b'),refused]);run('batchCounts()');
  assert.equal(rowOf('u').children[0].children[0].children[0].checked,true,'the refused row keeps its tick after a refresh');
  run('selectedBooks.clear();batchCounts()');assert.equal(get('batch-count').textContent,'0 selected · 0 can be retried or repaired','no "left out" at zero');

  // Focus: a refusal lands while Sergei is on the row's Retry. The row updates in place, focus goes to the same row.
  paint([m4bRow('x'),m4bRow('y')]);
  actionButtons(rowOf('x'))[0].focus();assert.equal(document.activeElement.textContent,'Retry');
  context.fixture=[refusedRow('x','unsupported_file'),m4bRow('y')];run('rows=fixture.map(row=>({...row}));renderRows(false);controls()');
  tr=rowOf('x');
  assert.equal(document.activeElement,actionButtons(tr)[1],'View metadata of the same row, never the page or a neighbour');
  assert.equal(document.activeElement.textContent,'View metadata');
  assert.equal(statusCell(tr).textContent,"Can't convert — M4B not supported",'the status changed in place');
  assert.match(statusCell(tr).children[0].textContent,/^Retry was refused: the app doesn't support/);
  // The same from the details panel's Retry.
  paint([m4bRow('z')]);run('select(rows[0],true);controls()');
  assert.equal(get('retry-block').hidden,false);get('retry-job').focus();
  context.fixture=[refusedRow('z','unsupported_file')];run('rows=fixture.map(row=>({...row}));renderRows(false);controls()');
  assert.equal(get('retry-block').hidden,true);
  assert.equal(document.activeElement,actionButtons(rowOf('z'))[0],'the panel Retry hands focus to the row, not to the page');assert.equal(document.activeElement.textContent,'View metadata');

  // While on screen: the pressed book leaves Can retry when refused; it is held in place showing the refusal.
  run('attentionGroup="retry"');
  const held=m4bRow('h'),heldQueued={...held,creation:{...held.creation,job:{...held.creation.job,retry:undefined,readmission:{accepted:true,queued_next:true,position:1,kind:'retry',state:'queued'}}}};
  context.fixture=heldQueued;run('rows=[fixture];renderRows(true);heldRow={path:fixture.path,index:0,context:listContext(),row:fixture,until:Date.now()+60000}');
  const searched=[];const listFetch=context.fetch;
  context.fetch=async(route,options)=>{
    if(route.startsWith('/api/inventory') && route.includes('status=all')){searched.push(route);return {ok:true,json:async()=>({rows:[refusedRow('h','unsupported_file')],total:1})};}
    if(route.startsWith('/api/inventory'))return {ok:true,json:async()=>({rows:[],total:0})};
    return listFetch(route,options);
  };
  await run('loadList(listContext(),"Audiobooks",view,filters[view],0,"",retryEpoch,false)');
  for(let i=0;i<5;i++)await tick();
  assert.equal(searched.length,1,'re-read once');assert.match(searched[0],/search=Title%20h/);
  tr=rowOf('h');assert.ok(tr,'still in place');
  assert.equal(statusCell(tr).textContent,"Can't convert — M4B not supported",'never a stale Queued');
  await run('loadList(listContext(),"Audiobooks",view,filters[view],0,"",retryEpoch,false)');for(let i=0;i<5;i++)await tick();
  assert.equal(searched.length,1,'one re-read per hold');assert.equal(statusCell(rowOf('h')).textContent,"Can't convert — M4B not supported");
  context.fetch=listFetch;run('heldRow=null;attentionGroup="all"');

  context.setTimeout=()=>0;
  console.log('PASS refused Retry rows per typed cause, stale state, left-out count, focus hand-off, held refused row');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_refused_retry_frontend.js'),module);m.filename=path.join(__dirname,'test_refused_retry_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

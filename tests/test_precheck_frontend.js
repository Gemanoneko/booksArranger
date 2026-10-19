'use strict';
// RefusedRetry follow-up (Judy, 2026-10-19) on seeded rows: the M4B pre-check states ("checking", "can't open"), a stale
// refusal whose check passed, the Checking strip group, the Repair verb in refused rows (3b), and the working folder in
// the Technical detail line only (3c). Real frontend on the Retry test's DOM/transport doubles.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
// A text node for the status cell's own text (statusInPlace changes it without rebuilding the row).
Object.defineProperty(Element.prototype,'firstChild',{get(){const element=this;return element.textContent?{nodeType:3,get nodeValue(){return element.textContent;},set nodeValue(value){element.textContent=value;}}:null;}});
const M4B_REASON='M4B preservation requires review: Unsupported structural box';
// The spec's words, pinned here.
const CHECKING='The app is checking this M4B before offering Retry. The row updates itself.';
const CANT_OPEN="The app couldn't open this M4B to check it. Check that the library drive is connected, then retry.";
const UNOPENED='Source unavailable: [Errno 2] No such file or directory';
const FOLDER='C:\\Users\\fixture\\AppData\\Local\\Books Arranger\\data\\merge-cache\\audio-staging\\job-w';
function m4bRow(name,job={}){
  return blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name}},
    {job_id:'job-'+name,reason:M4B_REASON,attention:{group:'retry',cause:null,originals_untouched:true,precheck:'passed'},retry:{allowed:true,reason:''},...job});
}
function pendingRow(name){return m4bRow(name,{attention:{group:'checking',cause:null,originals_untouched:true,precheck:'pending'},retry:{allowed:false,reason:CHECKING}});}
function unopenedRow(name){return m4bRow(name,{attention:{group:'other',cause:null,originals_untouched:true,precheck:'unavailable',precheck_reason:UNOPENED},retry:{allowed:true,reason:''}});}
function refusal(cause,extra={}){
  const fix={unsupported_file:'update',working_files:'wait',source_changed:'review',file_problem:'user',unknown:'update'}[cause];
  return {accepted:false,queued_next:false,kind:'retry',state:'refused',reason:'Failed M4B retained: fixture',cause,fix,app_version:'0.18.0',key:'k',at:'2026-10-19T08:00:00+00:00',stale:false,...extra};
}
function statusCell(tr){return tr.children[4];}
function actionButtons(tr){return tr.children[5].children[0].children;}
function rowOf(name){return [...get('inventory').children].find(tr=>tr.dataset.path==='cand-'+name);}
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');}
function counts(values){context.counts=values;run('state={...state,audiobook_jobs:{...state.audiobook_jobs,attention_counts:counts}};renderAttentionGroups()');}
const text=row=>run('attentionText('+JSON.stringify(row)+')');
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";viewControls()');

  // (a) Not finished: muted hint; Retry present and disabled, the same text as tooltip and hint.
  paint([pendingRow('p')]);let tr=rowOf('p');
  assert.equal(statusCell(tr).textContent,'Stopped — checking the M4B');
  assert.equal(statusCell(tr).children[0].textContent,CHECKING);
  assert.equal(statusCell(tr).children[0].classes.has('retry-refused'),false,'--muted: it clears by itself');
  assert.equal(actionButtons(tr)[0].textContent,'Retry');assert.equal(actionButtons(tr)[0].disabled,true);assert.equal(actionButtons(tr)[0].title,CHECKING);
  assert.equal(statusCell(tr).title,'Technical detail: '+M4B_REASON,'the job reason only');
  context.fixture=pendingRow('p');run('select(fixture,true);controls()');
  assert.equal(get('automatic-result-status').textContent,'Stopped — checking the M4B');
  assert.equal(get('retry-block').hidden,false);assert.equal(get('retry-job').disabled,true);assert.equal(get('retry-job').title,CHECKING);assert.equal(get('retry-note').textContent,CHECKING);

  // (b) Could not open the source: warning hint; Retry enabled with its usual tooltip; the check's raw text in Technical detail.
  paint([unopenedRow('u')]);tr=rowOf('u');
  assert.equal(statusCell(tr).textContent,"Stopped — can't open the M4B");
  assert.equal(statusCell(tr).children[0].textContent,CANT_OPEN);
  assert.ok(statusCell(tr).children[0].classes.has('retry-refused'),'--warning: Sergei can fix it');
  assert.equal(actionButtons(tr)[0].textContent,'Retry');assert.equal(actionButtons(tr)[0].disabled,false);assert.equal(actionButtons(tr)[0].title,READY);
  assert.equal(statusCell(tr).title,'Technical detail: '+UNOPENED+'; earlier failure: '+M4B_REASON);
  context.fixture=unopenedRow('u');run('select(fixture,true);controls()');
  assert.equal(get('automatic-technical').textContent,'Technical detail: '+UNOPENED+'; earlier failure: '+M4B_REASON);

  // Positive control: a passed check is still "ready to retry" with Retry enabled.
  paint([m4bRow('r')]);tr=rowOf('r');
  assert.equal(statusCell(tr).textContent,'Stopped — ready to retry');assert.equal(statusCell(tr).children[0].textContent,'Safe to retry now.');assert.equal(actionButtons(tr)[0].disabled,false);

  // Selection: a ticked pending row is left out; a ticked can't-open row goes into Retry selected.
  paint([m4bRow('a'),pendingRow('p'),unopenedRow('u')]);
  run('for(const row of rows)selectedBooks.set(row.id,row.revision);renderRows(true);batchCounts();controls()');
  assert.equal(get('batch-count').textContent,'3 selected · 2 can be retried or repaired · 1 left out');
  assert.equal(get('retry-selected').textContent,'Retry selected (2)');
  assert.deepEqual(run('retrySelectable().map(item=>item.row.id)'),['cand-a','cand-u']);
  run('selectedBooks.clear();batchCounts()');

  // A stale refusal with the check: pending reads Checking, can't open reads (b), passed reads ready with the update hint,
  // refused reads M4B not supported; "Stopped — try again" stays only for a row the check does not cover.
  const stale=(name,attention,extra={})=>m4bRow(name,{attention:{cause:null,originals_untouched:true,...attention},readmission:refusal('unsupported_file',{stale:true,...extra})});
  let value=text(stale('s1',{group:'checking',precheck:'pending'}));
  assert.deepEqual([value.status,value.hint],['Stopped — checking the M4B',CHECKING]);
  value=text(stale('s2',{group:'other',precheck:'unavailable',precheck_reason:UNOPENED}));
  assert.deepEqual([value.status,value.hint,value.warn],["Stopped — can't open the M4B",CANT_OPEN,true]);
  value=text(stale('s3',{group:'retry',precheck:'passed'}));
  assert.deepEqual([value.status,value.hint,!!value.warn],['Stopped — ready to retry','Retry was refused in v0.18.0. The app was updated, and this M4B now passes its check.',false]);
  assert.equal(text(stale('s4',{group:'retry',precheck:'passed'},{app_version:''})).hint,'Retry was refused. The app was updated, and this M4B now passes its check.','no stored version: the clause is dropped');
  assert.equal(run('candidateStatus('+JSON.stringify(stale('s5',{group:'unsupported'}))+')'),"Can't convert — M4B not supported");
  assert.equal(text(stale('s6',{group:'retry',precheck:undefined})).status,'Stopped — try again','positive control: a row the check does not cover');
  // A current refusal comes before the pre-check.
  assert.equal(text(m4bRow('s7',{attention:{group:'other',cause:null,originals_untouched:true,precheck:'pending'},readmission:refusal('file_problem')})).status,'Stopped — file problem');

  // The Checking strip group: after Can repair, counted in All, hidden at zero.
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
  assert.match(html,/id="group-repair"[^>]*>[^<]*<\/button><button id="group-checking" type="button" class="quiet attention-group" aria-pressed="false" title="Show books the app is still checking before it offers Retry\." hidden>Checking · 0<\/button>/);
  assert.deepEqual([...run('attentionKeys')],['all','retry','repair','checking','changed','audiobook','other','unsupported']);
  run('attentionGroup="all"');
  counts({retry:2,repair:0,checking:3,changed:0,audiobook:0,other:1,unsupported:0});
  assert.equal(get('group-checking').textContent,'Checking · 3');assert.equal(get('group-checking').hidden,false);assert.equal(get('group-all').textContent,'All · 6');
  counts({retry:2,repair:0,checking:0,changed:0,audiobook:0,other:1,unsupported:0});
  assert.equal(get('group-checking').hidden,true,'hidden at zero');
  // Checking empties while selected: the view moves to Can retry (the books he waited for), not to All.
  run('attentionGroup="checking"');counts({retry:3,repair:0,checking:0,changed:0,audiobook:0,other:1,unsupported:0});
  assert.equal(run('attentionGroup'),'retry');
  run('attentionGroup="other"');counts({retry:3,repair:0,checking:0,changed:0,audiobook:0,other:0,unsupported:0});
  assert.equal(run('attentionGroup'),'all','positive control: any other group still empties into All');

  // 3b: the verb follows the refusal kind; a refused Repair's main lines never say "retry".
  const repair=(cause,job={})=>m4bRow('rp',{attention:{group:'other',cause:null,originals_untouched:true},readmission:refusal(cause,{kind:'repair'}),...job});
  assert.equal(text(repair('unknown')).status,'Stopped — repair refused');
  assert.equal(text(m4bRow('rt',{attention:{group:'other',cause:null,originals_untouched:true},readmission:refusal('unknown')})).status,'Stopped — retry refused','positive control: a Retry says retry');
  assert.equal(text(repair('working_files')).hint,'Repair was refused: working files from an earlier attempt are still present. Repair after they are cleared.');
  assert.equal(text(repair('file_problem')).hint,"Repair was refused: the app couldn't read or write a file. Check the folder, then repair.");
  for(const cause of ['unknown','working_files','file_problem','source_changed','unsupported_file']){const lines=text(repair(cause));assert.doesNotMatch(lines.status+' '+lines.hint,/retry/i,cause);}

  // 3c: the absolute working folder is in Technical detail only (panel and hover title), for working_files only.
  const waiting=m4bRow('w',{attention:{group:'other',cause:null,originals_untouched:true,working_folder:FOLDER},retry:{allowed:false,reason:NOT_YET},readmission:refusal('working_files')});
  paint([waiting]);tr=rowOf('w');
  assert.equal(statusCell(tr).title,'Technical detail: Failed M4B retained: fixture; earlier failure: '+M4B_REASON+'; working folder: '+FOLDER);
  assert.ok(!statusCell(tr).children[0].textContent.includes('audio-staging'),'never in the hint');
  context.fixture=waiting;run('select(fixture,true);controls()');
  assert.match(get('automatic-technical').textContent,/; working folder: C:\\Users\\fixture\\.*\\job-w$/);
  const problem=m4bRow('f',{attention:{group:'other',cause:null,originals_untouched:true,working_folder:FOLDER},readmission:refusal('file_problem')});
  assert.ok(!run('technicalText('+JSON.stringify(problem)+')').includes('working folder'),'positive control: another cause never names it');

  context.setTimeout=()=>0;
  console.log('PASS pre-check checking and can\'t-open rows, stale refusal with a passed check, Checking strip group, Repair verb, working folder in Technical detail');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_precheck_frontend.js'),module);m.filename=path.join(__dirname,'test_precheck_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

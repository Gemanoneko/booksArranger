'use strict';
// v0.16.8 kept files (Docs/BooksArranger_AttentionActions_Spec.md section 3, 6 and 10): completed books whose
// recovery copies the backup rule keeps show as Original changed or Audiobook problem, offer Keep files
// through the Retry machinery (one request, pending copy, Queued-style flip, landed check on no reply), and
// the strip hides empty groups. The Jobs panel counts the same total as All. Runs the real frontend on the
// Retry test's DOM and transport doubles; no server, no library, no deletion.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const CHANGED='Original bytes differ from reviewed sources';
function keptRow(name,group,cause=null,reason=CHANGED){
  const row=blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name},status:'Audiobook created',audiobook_ready:true},
    {job_id:'job-'+name,state:'Audiobook created',stage:'done',reason:'',retry:undefined,attention:{group,cause,reason,originals_untouched:false},keep:{allowed:true,reason:''}});
  return {...row,creation:{...row.creation,status:'Audiobook created',reasons:[]}};
}
function keptByChoiceRow(name){const row=keptRow(name,'changed');const job={...row.creation.job,kept:true};delete job.attention;delete job.keep;return {...row,creation:{...row.creation,job}};}
function statusCell(tr){return tr.children[4];}
function actionButtons(tr){return tr.children[5].children[0].children;}
const posted=route=>calls.filter(call=>call.route===route);
let keepOverride=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  if(route==='/api/audiobook/keep'){calls.push({route,options});const data=JSON.parse(options.body);return keepOverride?keepOverride(data):{ok:true,status:202,json:async()=>({job_id:data.job_id,kept:true})};}
  return baseFetch(route,options);
};
const settle=(ms=30)=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";viewControls()');
  // Classes and copy (section 1): the API group and cause decide, never the reason text.
  const changed=keptRow('a','changed'),missing=keptRow('b','audiobook','missing','The system cannot find the file specified'),unverified=keptRow('c','audiobook','unverified','Completed output identity changed');
  const status=row=>run('candidateStatus('+JSON.stringify(row)+')');
  assert.equal(status(changed),'Original changed since checked');assert.equal(status(missing),'Audiobook missing');assert.equal(status(unverified),'Audiobook not verified');
  assert.equal(status({...changed,creation:{...changed.creation,job:{...changed.creation.job,attention:undefined}}}),'Audiobook Ready','positive control: a completed book without a kept class reads as before');

  // Rows: status, hint, technical detail on hover; Keep files is the only action (no remedy is offered yet).
  context.fixture=[changed,missing,unverified];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');
  const trs=get('inventory').children;assert.equal(trs.length,3);
  for(const tr of trs)assert.equal(statusCell(tr).children[0].textContent,'Recovery copies are kept until you decide.');
  assert.equal(statusCell(trs[0]).title,'Technical detail: '+CHANGED,'the kept reason, not the empty job reason');
  assert.equal(statusCell(trs[1]).title,'Technical detail: The system cannot find the file specified');
  const keep=actionButtons(trs[0])[0];
  assert.equal(keep.textContent,'Keep files');assert.equal(keep.title,"Keep this book's files and stop flagging it. Nothing is deleted.");
  assert.equal(keep.getAttribute('aria-label'),'Keep files: Title a');assert.ok(keep.className.split(' ').includes('quiet'));assert.equal(keep.disabled,false);
  for(const tr of trs)assert.ok(![...actionButtons(tr)].some(button=>/^(Retry|Repair|Check again|Convert again)$/.test(button.textContent)),'no remedy button and no disabled ghost');
  run('busy=true;controls()');assert.equal(keep.disabled,true);assert.equal(keep.title,'Another operation is in progress.');run('busy=false;controls()');

  // Keep files: one request (double press ignored), pending copy, then "Files kept at your choice." before the list reloads.
  let answer;keepOverride=()=>new Promise(resolve=>{answer=resolve;});let listGate;inventoryOverride=()=>new Promise(resolve=>{listGate=resolve;});
  const sent=calls.length;keep.handlers.click({stopPropagation(){}});await settle(5);
  assert.equal(keep.textContent,'Keeping…');assert.equal(statusCell(trs[0]).children[0].textContent,'Keeping these files…');assert.equal(keep.getAttribute('aria-disabled'),'true');
  keep.handlers.click({stopPropagation(){}});
  answer({ok:true,status:202,json:async()=>({job_id:'job-a',kept:true})});await settle(10);
  assert.equal(posted('/api/audiobook/keep').length,1,'one request');assert.deepEqual(JSON.parse(posted('/api/audiobook/keep')[0].options.body),{library:'Audiobooks',id:'cand-a',revision:4,job_id:'job-a'});
  assert.ok(!calls.slice(sent).some(call=>call.route==='/api/audiobook/retry'),'Keep files never queues a job');
  assert.equal(statusCell(trs[0]).children[0].textContent,'Files kept at your choice.');assert.equal(keep.hidden,true,'nothing left to press');
  listGate({ok:true,json:async()=>({rows:[missing,unverified],total:2})});await settle(10);inventoryOverride=null;keepOverride=null;
  assert.equal(get('inventory').children.length,2,'the kept book leaves the filter');

  // A refusal shows the server message in the hint; the button stays.
  keepOverride=async()=>({ok:false,status:409,json:async()=>({error:"This book's status changed. Check the updated status above."})});
  inventoryRows=[missing,unverified];const row0=()=>get('inventory').children[0];actionButtons(row0())[0].handlers.click({stopPropagation(){}});await settle();
  assert.equal(statusCell(row0()).children[0].textContent,"This book's status changed. Check the updated status above.");assert.ok(statusCell(row0()).children[0].classes.has('retry-refused'));
  assert.equal(actionButtons(row0())[0].textContent,'Keep files');keepOverride=null;

  // No reply in time but it landed: the page reads the book back and shows it kept, with no connection alarm.
  context.fixture=[missing];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');
  keepOverride=async()=>{throw new TypeError('Failed to fetch');};const keptMissing=keptByChoiceRow('b');inventoryRows=[keptMissing];context.setTimeout=setTimeout;
  actionButtons(get('inventory').children[0])[0].handlers.click({stopPropagation(){}});await settle(60);
  assert.equal(run('recoveryDisconnected'),false);assert.equal(statusCell(get('inventory').children[0]).children[0].textContent,'Files kept at your choice.');
  assert.ok(![...actionButtons(get('inventory').children[0])].some(button=>button.textContent==='Keep files' && !button.hidden));keepOverride=null;

  // A kept book elsewhere: the row says so, the details panel keeps the line, and there is no action to press.
  run('filters.candidates="all";viewControls()');const kept=keptByChoiceRow('k');
  context.fixture=[kept];run('rows=fixture.map(row=>({...row}));renderRows(true);controls()');
  assert.equal(statusCell(get('inventory').children[0]).children[0].textContent,'Files kept at your choice.');
  assert.ok(![...actionButtons(get('inventory').children[0])].some(button=>button.textContent==='Keep files'));
  show(kept);run('automaticResultKey=null;renderAutomaticResult(fixture);controls()');
  assert.equal(get('automatic-result-hint').textContent,'You chose to keep these files.');assert.equal(get('automatic-result-hint').hidden,false);assert.equal(get('retry-block').hidden,true);
  // The details panel action reads Keep files for a kept-files book.
  show(changed);run('controls()');assert.equal(get('retry-job').textContent,'Keep files');assert.equal(get('retry-block').hidden,false);
  run('filters.candidates="output_attention";viewControls()');

  // Strip (section 6): the two groups in order; a zero group is hidden except All and Can retry.
  const strip=get('attention-groups');for(const key of ['all','retry','repair','changed','audiobook','other','unsupported'])strip.append(get('group-'+key));
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:{retry:0,repair:0,changed:2,audiobook:1,other:0,unsupported:0}}};run('state='+JSON.stringify(backend)+';controls()');
  assert.equal(get('group-all').textContent,'All · 3');assert.equal(get('group-changed').textContent,'Original changed · 2');assert.equal(get('group-audiobook').textContent,'Audiobook problem · 1');
  assert.equal(get('group-retry').hidden,false,'Can retry is always shown');assert.equal(get('group-all').hidden,false);
  for(const key of ['repair','other','unsupported'])assert.equal(get('group-'+key).hidden,true,key+' at zero is hidden');
  assert.equal(get('group-changed').hidden,false);assert.equal(get('group-audiobook').hidden,false);
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
  assert.ok(html.indexOf('id="group-repair"')<html.indexOf('id="group-changed"') && html.indexOf('id="group-changed"')<html.indexOf('id="group-audiobook"') && html.indexOf('id="group-audiobook"')<html.indexOf('id="group-other"'),'strip order');
  assert.match(html,/title="Show books whose original changed after the check\."/);assert.match(html,/title="Show books whose audiobook is missing or not verified\."/);
  inventoryRows=[changed];let before=calls.length;await get('group-changed').handlers.click();
  assert.match(calls.slice(before).find(call=>call.route.startsWith('/api/inventory')).route,/&status=output_attention&group=changed$/);
  assert.equal(get('group-changed').getAttribute('aria-pressed'),'true');
  // The selected group reaches zero: back to All, the list reloads without a group, focus moves to All.
  get('group-changed').focus();before=calls.length;
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:{retry:0,repair:0,changed:0,audiobook:1,other:0,unsupported:0}}};run('state='+JSON.stringify(backend)+';controls()');
  await settle();assert.equal(run('attentionGroup'),'all');assert.equal(get('group-all').getAttribute('aria-pressed'),'true');assert.equal(get('group-changed').hidden,true);
  assert.match(calls.slice(before).find(call=>call.route.startsWith('/api/inventory')).route,/&status=output_attention$/);assert.equal(document.activeElement,get('group-all'));
  // A group with focus stays visible at zero (focus is never dropped by a poll).
  get('group-audiobook').focus();backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:{retry:0,repair:0,changed:0,audiobook:0,other:0,unsupported:0}}};run('state='+JSON.stringify(backend)+';controls()');
  assert.equal(get('group-audiobook').hidden,false);document.activeElement=null;run('controls()');assert.equal(get('group-audiobook').hidden,true);

  // Jobs panel (section 10, O2): the same total as All when the server sends the counts; the old count otherwise.
  run('state='+JSON.stringify({...backend,audiobook_jobs:{state:'Needs attention',queued:0,failed:1,attention_counts:{retry:2,repair:1,changed:1,audiobook:1,other:0,unsupported:1}}})+';renderJobs()');
  assert.match(get('jobs-status').textContent,/ · 6 output issues$/);
  run('state='+JSON.stringify({...backend,audiobook_jobs:{state:'Needs attention',queued:0,failed:4}})+';renderJobs()');assert.match(get('jobs-status').textContent,/ · 4 output issues$/);
  // Empty source folders hold nothing: the server sends no folder note, so the panel shows none.
  run('state='+JSON.stringify({...backend,audiobook_jobs:{state:'Completed',queued:0,failed:0,folder_cleanup_notes:[]}})+';renderJobs()');
  assert.doesNotMatch(get('jobs-help').textContent,/Empty source folders/);
  context.setTimeout=()=>0;
  console.log('PASS kept-files classes and copy, Keep files row and panel action (one request, pending, refused, landed), kept-by-choice lines, strip groups and zero hiding with fallback, Jobs panel total');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_kept_frontend.js'),module);m.filename=path.join(__dirname,'test_kept_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

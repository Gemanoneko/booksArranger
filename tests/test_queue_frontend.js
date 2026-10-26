'use strict';
// Queued Retry, Repair and Delete book (0.22.1, backlog 2 and 3; Judy's spec, section 1). A press while another operation
// runs is queued by the engine, not refused: the row shows "Retry queued" / "Delete queued" with what it waits for and its
// own Cancel; the strip counts the queue; Cancel, "too late", every outcome line of 1.6; the blocked Delete dialog; the
// siblings of a queued delete go inert; bulk leaves queued rows out. Real frontend on the Retry test's DOM/transport
// doubles (Futaba's checks 1 to 7 of section 8, without a server). No server, no library, no file is deleted.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const FOLDER='Z:\\Audiobooks\\Сборники\\Новая плоть (2016)';
function askRow(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:['Иван Петров'],members:[{path:FOLDER+'\\01.m4b'},{path:FOLDER+'\\02.m4b'},{path:FOLDER+'\\03.m4b',missing:true}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['Files missing']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const missing=(name,present=2)=>askRow(name,{kind:'files_missing',also:null,why:'',reasons:['Files missing'],fields:{title:{proposal:'Новая плоть',basis:'tag'},author:{proposal:'Иван Петров',basis:'tag'}},candidates:[],
  missing:{folders:[FOLDER],files:[FOLDER+'\\03.m4b'],present,total:3},destination:{path:'Петров Иван\\Новая плоть - Петров Иван.m4b',absolute:'',taken:false,reason:''},delete:{kind:'files_missing',present}});
function attentionRow(name,group='retry'){
  return blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name}},{job_id:'job-'+name,reason:'raw reason '+name,attention:{group,cause:null,originals_untouched:true}});
}
let answers={};const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(answers[route]){calls.push({route,options});return answers[route](data);}
  return baseFetch(route,options);
};
const ok=(value,status=200)=>({ok:status<400,status,json:async()=>value});
const posted=route=>calls.filter(call=>call.route===route).map(call=>JSON.parse(call.options.body));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
const byText=(tr,text)=>buttonsOf(tr).find(b=>b.textContent===text);
const hint=tr=>{const h=statusCell(tr).children[0];return h.textContent+(h.children || []).map(s=>s.textContent).join('');};
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
function queue(state){context.queueFixture=state;run('syncQueue(queueFixture);controls()');}
const item=(id,action,book,position,kind='scan',extra={})=>({id,action,book_id:book,title:'Title '+book.slice(5),position,blocker:{kind},...extra});
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  paint([attentionRow('a'),attentionRow('b'),attentionRow('c')]);
  let tr=trOf('cand-a');
  assert.equal(byText(tr,'Retry').title,"Check this book again and queue its audiobook job.",'control: nothing blocks it, the tooltip is unchanged');
  assert.equal(byText(tr,'Cancel retry').hidden,true,'Cancel waits hidden beside the face');
  // 1. A scan runs: Retry stays enabled and says it will queue (1.4, the blocked tooltip). The press sends queue: true.
  run('state={...state,active_library:"Audiobooks"};controls()');
  let retry=byText(tr,'Retry');assert.equal(retry.disabled,false);assert.equal(retry.getAttribute('aria-disabled'),null);
  assert.equal(retry.title,'Queue this retry. A scan is running; it starts when the scan finishes.');
  answers['/api/audiobook/retry']=()=>ok({queued:true,id:'q-1',position:1,blocker:{kind:'scan'}},202);
  inventoryRows=[attentionRow('a'),attentionRow('b'),attentionRow('c')];
  // As a browser does, rebuilding the list drops focus from a removed button to the page body.
  const inventory=get('inventory'),plainReplace=inventory.replaceChildren.bind(inventory);document.body=new Element('body');
  inventory.replaceChildren=(...items)=>{const lost=inventory.contains(document.activeElement);plainReplace(...items);if(lost)document.activeElement=document.body;};
  retry.focus();
  await retry.handlers.click({stopPropagation(){}});for(let i=0;i<6;i++)await tick();
  assert.equal(document.activeElement,buttonsOf(trOf('cand-a'))[0],"focus is back on the row's queued face after the list is rebuilt (1.7)");
  assert.deepEqual(posted('/api/audiobook/retry').at(-1),{library:'Audiobooks',id:'cand-a',revision:4,job_id:'job-a',queue:true,title:'Title a'});
  tr=trOf('cand-a');retry=buttonsOf(tr)[0];const cancel=byText(tr,'Cancel retry');
  assert.equal(retry.textContent,'Retry queued');assert.equal(retry.getAttribute('aria-disabled'),'true');assert.equal(retry.disabled,false,'keeps keyboard focus');
  assert.equal(retry.getAttribute('aria-label'),'Retry queued: Title a');assert.equal(retry.title,'Retry is queued. It starts when the scan finishes.');
  assert.equal(cancel.hidden,false);assert.equal(cancel.title,'Take this retry out of the queue. Nothing was started.');assert.equal(cancel.getAttribute('aria-label'),'Cancel retry: Title a');
  assert.equal(buttonsOf(tr).indexOf(cancel),buttonsOf(tr).indexOf(retry)+1,'Cancel directly after the face (1.7)');
  assert.equal(hint(tr),'Retry queued. Starts when the scan finishes.');
  assert.equal(get('queue-announce').textContent,'Retry queued: Title a.');
  // A double click on the queued face does nothing (1.1).
  const sent=posted('/api/audiobook/retry').length;await retry.handlers.click({stopPropagation(){}});await tick();assert.equal(posted('/api/audiobook/retry').length,sent);
  // 2. Order and count from /api/state: "{n} ahead", the strip line, a fresh press goes behind.
  queue({queued_actions:[item('q-1','retry','cand-a',1),item('q-2','retry','cand-b',2),item('q-3','repair','cand-c',3)],queue_running:null,queue_outcomes:[]});
  assert.equal(hint(trOf('cand-b')),'Retry queued, 1 ahead. Starts when the scan finishes.');
  assert.equal(hint(trOf('cand-c')),'Repair queued, 2 ahead. Starts when the scan finishes.');assert.equal(buttonsOf(trOf('cand-c'))[0].textContent,'Repair queued');
  assert.equal(byText(trOf('cand-c'),'Cancel repair').hidden,false);
  assert.equal(get('queue-line').textContent,'3 actions queued. They run one at a time when the scan finishes.');assert.equal(get('queue-line').hidden,false);
  // The details panel shows the same pair (1.3): the queued face, Cancel repair beside it, the hint in #retry-note.
  run('select(rows.find(row=>row.id==="cand-c"),true)');
  assert.equal(get('retry-job').textContent,'Repair queued');assert.equal(get('retry-job').getAttribute('aria-disabled'),'true');
  assert.equal(get('retry-cancel').hidden,false);assert.equal(get('retry-cancel').textContent,'Cancel repair');
  assert.equal(get('retry-note').textContent,'Repair queued, 2 ahead. Starts when the scan finishes.');
  answers['/api/queue/cancel']=()=>ok({cancelled:true});await get('retry-cancel').handlers.click({});for(let i=0;i<4;i++)await tick();
  assert.deepEqual(posted('/api/queue/cancel').at(-1),{id:'q-3'});assert.equal(get('queue-announce').textContent,'Repair cancelled: Title c.');
  queue({queued_actions:[item('q-1','retry','cand-a',1)],queue_running:null,queue_outcomes:[]});
  assert.equal(get('queue-line').textContent,'1 action queued. It runs when the scan finishes.');
  // 3. Cancel: out of the queue, nothing starts, the row returns to Retry, focus on the restored button.
  answers['/api/queue/cancel']=data=>ok({cancelled:true});
  const cancelA=byText(trOf('cand-a'),'Cancel retry');cancelA.focus();await cancelA.handlers.click({stopPropagation(){}});for(let i=0;i<6;i++)await tick();
  assert.deepEqual(posted('/api/queue/cancel').at(-1),{id:'q-1'});
  tr=trOf('cand-a');assert.equal(buttonsOf(tr)[0].textContent,'Retry');assert.equal(byText(tr,'Cancel retry').hidden,true);
  assert.equal(get('queue-announce').textContent,'Retry cancelled: Title a.');assert.equal(document.activeElement,buttonsOf(tr)[0],'focus on the restored Retry');
  // Too late: the engine has started it; the line says so, Cancel goes, the run state follows.
  queue({queued_actions:[item('q-4','retry','cand-a',1)],queue_running:null,queue_outcomes:[]});
  answers['/api/queue/cancel']=()=>ok({error:'It has already started.',code:'started'},409);
  await byText(trOf('cand-a'),'Cancel retry').handlers.click({stopPropagation(){}});for(let i=0;i<4;i++)await tick();
  queue({queued_actions:[],queue_running:{id:'q-4',action:'retry',book_id:'cand-a',title:'Title a'},queue_outcomes:[]});
  tr=trOf('cand-a');assert.equal(hint(tr),'Too late to cancel: the retry has already started.');assert.equal(byText(tr,'Cancel retry').hidden,true);
  assert.equal(buttonsOf(tr)[0].textContent,'Checking…');assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true');
  // 1.6: it ran and was refused; the line leads "Retry cancelled:", in --warning, with the typed reason.
  queue({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o-1',action:'retry',book_id:'cand-a',title:'Title a',result:'refused',code:'changed',error:"This book's status changed. Check the updated status above."},
    {id:'o-2',action:'retry',book_id:'cand-b',title:'Title b',result:'refused',code:'busy',error:'Working files from an earlier attempt are still present. Retry after they are cleared.'},
    {id:'o-3',action:'repair',book_id:'cand-c',title:'Title c',result:'refused',code:'failed'}]});
  assert.equal(hint(trOf('cand-a')),'Retry cancelled: this book needs another look. Check its status above.');assert.ok(statusCell(trOf('cand-a')).children[0].classes.has('retry-refused'));
  assert.equal(hint(trOf('cand-b')),'Retry cancelled: working files from an earlier attempt are still present. Retry after they are cleared.');
  assert.equal(hint(trOf('cand-c')),'Repair cancelled: it was not accepted. Check the status above.');
  assert.equal(get('queue-announce').textContent,'Title c: Repair cancelled: it was not accepted. Check the status above.');
  assert.equal(posted('/api/queue/ack').length,0,'kept until the line is dismissed, so a reload still shows it');
  queue({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o-1',action:'retry',book_id:'cand-a',title:'Title a',result:'refused',code:'changed'}]});
  assert.equal(get('queue-announce').textContent,'Title c: Repair cancelled: it was not accepted. Check the status above.','an outcome is applied once');
  // A line outlives the first list read after the run (the rows on screen predate it), then ends when the status changes.
  inventoryRows=[attentionRow('a'),attentionRow('b'),attentionRow('c')];await run('refresh(true)');for(let i=0;i<4;i++)await tick();
  assert.equal(hint(trOf('cand-a')),'Retry cancelled: this book needs another look. Check its status above.','the first list read after the run keeps the line');
  inventoryRows=[queued(attentionRow('a')),attentionRow('b'),attentionRow('c')];await run('refresh(true)');for(let i=0;i<4;i++)await tick();
  assert.equal(run('queueNotes.has("cand-a")'),false,'a status change ends it');
  inventoryRows=[attentionRow('a'),attentionRow('b'),attentionRow('c')];paint(inventoryRows);
  run('resetStrip()');await tick();
  assert.deepEqual(posted('/api/queue/ack').map(body=>body.ids[0]).sort(),['o-1','o-2','o-3'],'a filter change dismisses the lines and acknowledges them');
  // A queued retry that ran: the existing strip line names the book.
  queue({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o-4',action:'retry',book_id:'cand-b',title:'Title b',result:'done',answer:{position:1,queued_next:true}}]});
  assert.equal(get('retry-all-status').textContent,'Title b queued — runs next');
  // Bulk: a row with a queued action is left out of Retry selected and counted (1.3).
  queue({queued_actions:[item('q-5','retry','cand-a',1)],queue_running:null,queue_outcomes:[]});
  run('selectedBooks.set("cand-a",4);selectedBooks.set("cand-c",4);batchCounts()');
  assert.deepEqual(run('retrySelectable().map(item=>item.row.id)'),['cand-c']);assert.match(get('batch-count').textContent,/ · 1 already queued/);
  run('selectedBooks.clear();batchCounts()');queue({queued_actions:[],queue_running:null,queue_outcomes:[]});
  run('state={...state,active_library:null};controls()');

  // 4. Delete book while a scan runs: the preview names it, the dialog opens in its blocked variant, confirm queues.
  paint([missing('m'),missing('z',0)]);inventoryRows=[missing('m'),missing('z',0)];run('state={...state,active_library:"Audiobooks"};controls()');
  tr=trOf('cand-m');let del=byText(tr,'Delete book');
  assert.equal(del.title,'Delete this book. A scan is running, so the delete is queued after you confirm.');assert.equal(del.getAttribute('aria-disabled'),null);
  const FILES=[{path:FOLDER+'\\01.m4b',size:700*1024*1024},{path:FOLDER+'\\02.m4b',size:700*1024*1024}];
  answers['/api/candidate/delete-preview']=()=>ok({files:FILES,bytes:1400*1024*1024,folders:[],stay:{items:0},refusal:null,kind:'files_missing',blocked:{kind:'scan'}});
  await del.handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/candidate/delete-preview').at(-1),{library:'Audiobooks',id:'cand-m',revision:2,queue:true});
  assert.equal(get('delete-dialog-title').textContent,'Delete this book?');assert.equal(document.activeElement,get('delete-cancel'),'Cancel has focus');
  assert.equal(get('delete-dialog-blocked').hidden,false);assert.equal(get('delete-dialog-blocked').textContent,'A scan is running, so this delete waits its turn.');
  assert.match(get('delete-dialog-files').textContent,/^These 2 files \(1[.,]4 GB\) will be deleted from your disk when it runs\. The app can't undo this\.$/);
  assert.equal(get('delete-dialog-recheck').hidden,false);assert.equal(get('delete-dialog-recheck').textContent,'The app checks this book and these files again first. If anything differs, nothing is deleted.');
  assert.equal(get('delete-confirm').textContent,'Queue delete of 2 files');
  assert.equal(get('delete-confirm').title,"Queue this delete. It runs when the scan finishes, after the app checks the book and files again. The app can't undo it.");
  let release;answers['/api/candidate/delete']=()=>new Promise(resolve=>{release=resolve;});
  const confirming=get('delete-confirm').handlers.click({});await tick();
  assert.equal(get('delete-confirm').textContent,'Queuing…');assert.equal(get('delete-confirm').getAttribute('aria-disabled'),'true');
  assert.equal(get('delete-dialog-status').textContent,'Queuing this delete…');assert.equal(get('delete-cancel').title,"Queuing can't be stopped.");
  release(ok({queued:true,id:'d-1',position:1,blocker:{kind:'scan'}},202));await confirming;for(let i=0;i<8;i++)await tick();
  assert.deepEqual(posted('/api/candidate/delete').at(-1),{library:'Audiobooks',id:'cand-m',revision:2,paths:FILES.map(f=>f.path),folders:[],queue:true,title:'Title m'});
  assert.equal(run('deleteDialog'),null,'the dialog closes');
  tr=trOf('cand-m');del=buttonsOf(tr).find(b=>b.className.includes('danger'));
  assert.equal(del.textContent,'Delete queued');assert.equal(del.getAttribute('aria-disabled'),'true');assert.equal(document.activeElement,del,'focus on the queued face');
  assert.equal(del.title,'Delete is queued. Nothing is deleted until it runs, when the scan finishes.');assert.equal(del.getAttribute('aria-label'),'Delete queued: Title m');
  assert.equal(byText(tr,'Cancel delete').hidden,false);assert.equal(byText(tr,'Cancel delete').title,'Take this delete out of the queue. Nothing was deleted.');
  assert.equal(get('queue-announce').textContent,'Delete queued: Title m.');
  assert.equal(hint(tr),'Delete queued. Nothing is deleted yet. It runs when the scan finishes.');
  // Siblings go inert with their tooltip; View metadata stays live (1.3).
  for(const face of ['Scan again',"Convert what's there"]){const b=byText(tr,face);assert.equal(b.getAttribute('aria-disabled'),'true',face);assert.equal(b.title,'A delete is queued for this book. Cancel it to use this.',face);}
  assert.equal(byText(tr,'View metadata').getAttribute('aria-disabled'),null);
  // 5. It runs: "Deleting 2 files…", then finished: the strip names it, no dialog opens, focus does not move.
  queue({queued_actions:[],queue_running:{id:'d-1',action:'delete',book_id:'cand-m',title:'Title m',n:2},queue_outcomes:[]});
  assert.equal(del.textContent,'Deleting…');assert.equal(del.title,"Deleting can't be stopped.");assert.equal(hint(trOf('cand-m')),'Deleting 2 files…');assert.equal(byText(tr,'Cancel delete').hidden,true);
  get('filter').focus();
  queue({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o-d1',action:'delete',book_id:'cand-m',title:'Title m',result:'done',deleted:2,bytes:1400*1024*1024,failed:[],folders:{removed:0,stayed:0},n:2}]});
  assert.match(get('retry-all-status').textContent,/^Queued delete finished: Title m\. Deleted 1 book and 2 files \(1[.,]4 GB\)\.$/);
  assert.equal(run('deleteDialog'),null,'no dialog opens');assert.equal(document.activeElement,get('filter'),'focus stays where it was');
  assert.equal(run('deleteNotes.get("cand-m").text'),'Deleted. The book is gone from the app.');
  // 6. Run-time cancels, each verbatim; nothing was deleted.
  paint([missing('p'),missing('s'),missing('t'),missing('u'),missing('w')]);
  queue({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o-p',action:'delete',book_id:'cand-p',title:'Title p',result:'refused',code:'files_changed'},
    {id:'o-s',action:'delete',book_id:'cand-s',title:'Title s',result:'refused',code:'changed'},{id:'o-t',action:'delete',book_id:'cand-t',title:'Title t',result:'refused',code:'shared',files:[{path:'a',other:'x'},{path:'b',other:'y'}]},
    {id:'o-u',action:'delete',book_id:'cand-u',title:'Title u',result:'refused',code:'offline',root:'Z:\\Audiobooks'},{id:'o-w',action:'delete',book_id:'cand-w',title:'Title w',result:'refused',code:'sorted'},
    {id:'o-x',action:'delete',book_id:'cand-x',title:'Title x',result:'refused',code:'not_listed'}]});
  assert.equal(hint(trOf('cand-p')),"Delete cancelled: the files don't match the list you confirmed. Nothing was deleted. Press Delete book to see the current list.");
  assert.equal(hint(trOf('cand-s')),"Delete cancelled: this book doesn't match what you confirmed. Nothing was deleted. Open its details and try again.");
  assert.equal(hint(trOf('cand-t')),'Delete cancelled: 2 files also belong to other books. Nothing was deleted.');
  assert.equal(hint(trOf('cand-u')),"Delete cancelled: can't reach Z:\\Audiobooks. Nothing was deleted.");
  assert.equal(hint(trOf('cand-w')),'Delete cancelled: a finished audiobook of this book is in Audiobooks Sorted. Nothing was deleted.');
  assert.equal(get('retry-all-status').textContent,"Delete cancelled for Title x: the book isn't listed. Nothing was deleted.");
  assert.equal(byText(trOf('cand-p'),'Delete book').hidden,false,'Delete book returns');
  // 7. Partial: the counts, each file with its cause, then what to do; the book stays listed.
  paint([missing('k')]);
  queue({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o-k',action:'delete',book_id:'cand-k',title:'Title k',result:'partial',deleted:1,n:2,failed:[{path:FOLDER+'\\02.m4b',cause:'in_use'}]}]});
  assert.equal(hint(trOf('cand-k')),'Deleted 1 of 2 files. 1 is still on disk.'+FOLDER+'\\02.m4b'+'In use by another program.'+'The book stays listed. Press Delete book to try again.');
  assert.equal(get('retry-all-status').textContent,'Deleted 1 of 2 files. The book stays listed with the 1 that could not be deleted.');
  // An unblocked dialog whose confirm comes back queued (the engine became busy): it closes and the row shows it.
  run('state={...state,active_library:null};controls()');paint([missing('n')]);inventoryRows=[missing('n')];
  answers['/api/candidate/delete-preview']=()=>ok({files:FILES,bytes:10,folders:[],stay:{items:0},refusal:null,kind:'files_missing',blocked:null});
  await byText(trOf('cand-n'),'Delete book').handlers.click({stopPropagation(){}});await tick();
  assert.equal(get('delete-dialog-blocked').hidden,true);assert.equal(get('delete-dialog-recheck').hidden,true);assert.equal(get('delete-confirm').textContent,'Delete book and 2 files','the face is the best guess');
  answers['/api/candidate/delete']=()=>ok({queued:true,id:'d-2',position:1,blocker:{kind:'operation'}},202);
  await get('delete-confirm').handlers.click({});for(let i=0;i<4;i++)await tick();
  assert.equal(run('deleteDialog'),null);assert.equal(buttonsOf(trOf('cand-n')).find(b=>b.className.includes('danger')).textContent,'Delete queued');
  assert.equal(hint(trOf('cand-n')),'Delete queued. Nothing is deleted yet. It runs when the current operation finishes.');
  // Approve as is leaves a row with a queued delete out (1.3).
  assert.equal(run('deleteQueued(rows[0])'),true);
  // Section 5 (n = 0): the files line and the face.
  queue({queued_actions:[],queue_running:null,queue_outcomes:[]});paint([missing('z',0)]);
  answers['/api/candidate/delete-preview']=()=>ok({files:[],bytes:0,folders:[],stay:{items:0},refusal:null,kind:'files_missing',blocked:null});
  await byText(trOf('cand-z'),'Delete book').handlers.click({stopPropagation(){}});await tick();
  assert.equal(get('delete-dialog-files').textContent,'No files will be deleted from your disk.');assert.equal(get('delete-confirm').textContent,'Delete book');
  assert.equal(get('delete-confirm').title,'Remove this book from the app. No files are touched.');
  await get('delete-cancel').handlers.click({});
  answers['/api/candidate/delete-preview']=()=>ok({files:[],bytes:0,folders:[],stay:{items:0},refusal:null,kind:'files_missing',blocked:{kind:'book'}});
  await byText(trOf('cand-z'),'Delete book').handlers.click({stopPropagation(){}});await tick();
  assert.equal(get('delete-dialog-blocked').textContent,'This book is being processed, so this delete waits its turn.');
  assert.equal(get('delete-dialog-files').textContent,'No files will be deleted from your disk.');assert.equal(get('delete-confirm').textContent,'Queue delete');
  assert.equal(get('delete-dialog-recheck').textContent,'The app checks this book again first. If it differs, nothing is deleted.');
  assert.equal(get('delete-confirm').title,'Queue removing this book from the app. No files are touched.');
  await get('delete-cancel').handlers.click({});
  // The queue arrives with the status read (refresh), and the page names the bulk approval it runs itself.
  backend={...backend,queued_actions:[item('q-9','retry','cand-a',1,'operation')],queue_running:null,queue_outcomes:[]};
  await run('refresh(true)');assert.equal(run('queueState.queued.length'),1);
  run('askBulk=true');assert.equal(run('queueS("operation")'),'A bulk approval is in progress');run('askBulk=false');
  assert.equal(run('queueS("no_such_kind")'),'Another operation is in progress','an unknown kind reads as operation');
  // N1 (Judy's implementation check): Delete book on a row with a queued Retry or Repair says which, not "Another
  // operation is in progress." (nothing else runs); inert, focus kept. The mirror of the sibling sentence above.
  paint([missing('w')]);queue({queued_actions:[item('q-r','retry','cand-w',1)],queue_running:null,queue_outcomes:[]});run('updateDeleteButtons()');
  del=byText(trOf('cand-w'),'Delete book');assert.equal(del.getAttribute('aria-disabled'),'true');assert.equal(del.title,'A retry is queued for this book. Cancel it to use this.');
  queue({queued_actions:[item('q-p','repair','cand-w',1)],queue_running:null,queue_outcomes:[]});run('updateDeleteButtons()');
  assert.equal(byText(trOf('cand-w'),'Delete book').title,'A repair is queued for this book. Cancel it to use this.');
  queue({queued_actions:[],queue_running:{id:'q-p',action:'repair',book_id:'cand-w',title:'Title w'},queue_outcomes:[]});run('updateDeleteButtons()');
  assert.equal(byText(trOf('cand-w'),'Delete book').title,'Another operation is in progress.','a running repair is another operation');
  queue({queued_actions:[],queue_running:null,queue_outcomes:[]});
  console.log('PASS queued Retry and Delete book: blocked tooltips, queued faces with Cancel, order and count, cancel and too late, every outcome line, the blocked dialog, inert siblings, bulk left out, n = 0 copy');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_queue_frontend.js'),module);m.filename=path.join(__dirname,'test_queue_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

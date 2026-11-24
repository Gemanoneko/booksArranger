'use strict';
// Join into one book (0.30.0 item D; Judy's 0.30.0 spec, section 8) and Sergei's answer 9 (Cancel on a row whose accepted
// Retry or Repair has not started). The «Впусти меня» shape: five part rows selected, the bulk bar's button and its enable
// states, the dialog (parts in the engine's order, Move up and Move down keeping focus, the order line, Title and Author,
// Goes to, What happens, refusals, the wait behind a converting part, focus and Escape), the press (always queued), each
// part row's queued line with Cancel, the outcome on #join-status with Show it, the jobs panel's words, and the row Cancel
// of an accepted Repair. Real frontend on the Retry test's DOM and transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted',FOLDER='Z:\\Audiobooks\\Unsorted\\Линдквист - Впусти меня';
function partRow(n,extra={}){
  return {id:'part-'+n,path:'part-'+n,kind:'candidate',library:'Audiobooks',revision:3,fingerprint:String(n).repeat(64),scope:'fixture scope',preview:{reason:'fixture',path:''},
    metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],title_clue:'Впусти меня '+n,conflicts:[],coverage:'',companions:[],artists:['John Ajvide Lindqvist'],
    members:[{path:FOLDER+'\\Впусти меня '+n+'.m4b'}],track_order:[],included:[],review:{},review_context:{},status:'Needs review',automatic:null,
    creation:{status:'Needs review',can_create:false,reasons:[],job:null},source_directory_count:1,...extra};
}
const finished=partRow(9,{title_clue:'Готовая книга',audiobook_ready:true,status:'Audiobook Ready'});
const part=(n,extra={})=>({id:'part-'+n,revision:3,title:'Впусти меня '+n,files:1,hours:1.5,seconds:5400+n,track:n,track_total:5,state:'candidate',
  has_queued_job:false,has_failed_job:false,has_repair_request:false,has_approval:false,request_kind:null,m4b:true,...extra});
const PREVIEW={parts:[part(1),part(2,{has_queued_job:true,has_approval:true,state:'queued'}),part(3,{has_repair_request:true,has_failed_job:true,request_kind:'repair',state:'failed'}),part(4,{has_queued_job:true}),part(5,{has_approval:true})],
  order:{basis:'album_tracks',first:1,last:5,total:5,missing:[],duplicate:null},title:'Впусти меня',author:'Lindqvist John Ajvide',authors:['Lindqvist John Ajvide'],
  series:{dropped:{name:'Впусти меня',numbers:['1','2','3','4']},kept:null},goes_to:{path:'Lindqvist John Ajvide\\Впусти меня - Lindqvist John Ajvide.m4b',absolute:ROOT+'\\Lindqvist John Ajvide\\Впусти меня - Lindqvist John Ajvide.m4b',taken:false,reason:''},
  refusals:[],effects:{queued:2,failed:1,requests:1,approvals:2},blocked:null};
let previewAnswer=null,joinAnswer=null,cancelAnswer=null,withdrawAnswer=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/candidate/join-preview'){calls.push({route,options});return previewAnswer(data);}
  if(route==='/api/candidate/join'){calls.push({route,options});return joinAnswer(data);}
  if(route==='/api/queue/cancel'){calls.push({route,options});return cancelAnswer(data);}
  if(route==='/api/audiobook/retry-cancel'){calls.push({route,options});return withdrawAnswer(data);}
  return baseFetch(route,options);
};
const ok=value=>({ok:true,status:200,json:async()=>value}),refused=(status,value)=>({ok:false,status,json:async()=>value});
const posted=route=>calls.filter(call=>call.route===route).map(call=>JSON.parse(call.options.body));
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const buttonsOf=tr=>[...tr.children[5].children[0].children];
const joinHintOf=tr=>tr.children[4].children.find(child=>String(child.className).includes('join-hint'));
const joinCancelOf=tr=>buttonsOf(tr).find(b=>b.textContent==='Cancel' && b.title==='Cancel the whole join. Nothing is changed.');
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
function select(...ids){run('selectedBooks.clear();'+ids.map(id=>'selectedBooks.set('+JSON.stringify(id)+',3);').join('')+'batchCounts()');}
const joinButton=get('join-selected'),dialogText=()=>get('join-effects').children.map(li=>li.textContent);
(async()=>{
  backend={...backend,audiobook_output_root:ROOT,queued_actions:[],queue_running:null,queue_outcomes:[]};
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="all";viewControls()');
  paint([1,2,3,4,5].map(n=>partRow(n)).concat([finished]));
  // 1. The button (8.1): hidden with nothing selected, shown from one row, disabled until the selection can be joined.
  assert.equal(joinButton.hidden,true,'positive control: nothing selected, no button');
  select('part-1');assert.equal(joinButton.hidden,false);assert.equal(joinButton.textContent,'Join into one book (1)');assert.equal(joinButton.disabled,true);
  assert.equal(joinButton.title,'Select at least 2 books to join them.');
  select('part-1','part-9');assert.equal(joinButton.disabled,true);assert.equal(joinButton.title,'«Готовая книга» is already a finished audiobook. Join books that are not converted yet.');
  select('part-3','part-1','part-5','part-2','part-4');
  assert.equal(joinButton.disabled,false);assert.equal(joinButton.getAttribute('aria-disabled'),null);assert.equal(joinButton.textContent,'Join into one book (5)');
  assert.equal(joinButton.title,'Join the selected books into one audiobook. You choose the order, title and author first. Nothing is converted yet.');
  run('selectedBooks.set("part-elsewhere",7);batchCounts()');assert.equal(joinButton.textContent,'Join into one book (6)','selection across pages counts');
  run('selectedBooks.delete("part-elsewhere");batchCounts()');
  // 2. The dialog opens at once, Cancel focused, "Checking these books…", Join inert until the engine answers.
  let release;previewAnswer=()=>new Promise(resolve=>{release=()=>resolve(ok(PREVIEW));});
  joinButton.handlers.click();await tick();
  assert.deepEqual(posted('/api/candidate/join-preview').at(-1),{library:'Audiobooks',items:[1,2,3,4,5].map(n=>({id:'part-'+n,revision:3}))},'the list order; the engine orders the parts');
  assert.equal(get('join-dialog-title').textContent,'Join 5 books into one book?');assert.equal(document.activeElement,get('join-cancel'));
  assert.equal(get('join-dialog-checking').hidden,false);assert.equal(get('join-dialog-checking').textContent,'Checking these books…');
  assert.equal(get('join-confirm').getAttribute('aria-disabled'),'true');assert.equal(get('join-confirm').title,'Checking these books…');
  await get('join-confirm').handlers.click({});assert.equal(posted('/api/candidate/join').length,0,'an inert Join does nothing');
  release();await tick();
  // 3. The parts in the engine's order with their facts and plain words; the order line; the fields; Goes to; What happens.
  assert.equal(get('join-dialog-checking').hidden,true);
  const lines=get('join-dialog-list').children;assert.equal(lines.length,5);
  assert.deepEqual(lines[0].children.slice(0,2).map(c=>c.textContent),['Впусти меня 1','1 file · 1:30:01 · track 1 of 5']);
  assert.deepEqual(lines.map(li=>li.children.find(c=>c.className==='join-part-word')?.textContent || ''),['','Queued','Repair asked','Queued','Approved']);
  assert.equal(lines[0].children[0].title,'Впусти меня 1','the full title in its tooltip');
  assert.equal(lines[0].moveUp.getAttribute('aria-disabled'),'true');assert.equal(lines[0].moveUp.title,'Move this part earlier in the book.');assert.equal(lines[4].moveDown.title,'Move this part later in the book.');
  assert.equal(get('join-dialog-order').textContent,'Order from the album track numbers: 1/5 to 5/5. All 5 parts are here.');
  assert.equal(get('join-title').value,'Впусти меня');assert.equal(get('join-author').value,'Lindqvist John Ajvide');assert.equal(get('join-author-note').hidden,true);
  assert.equal(get('join-goes').textContent,'Audiobooks Sorted\\Lindqvist John Ajvide\\Впусти меня - Lindqvist John Ajvide.m4b');
  assert.deepEqual(dialogText(),['2 queued conversions are taken off the queue.','1 Repair request is cancelled. The conversion repairs damaged parts itself.',
    '1 failed attempt is set aside. Its entry leaves Needs attention.','Approvals on these books are removed. Approve the joined book when it looks right.',
    'The series «Впусти меня» No. 1-4 on these rows is dropped. It came from the part names.']);
  assert.equal(get('join-dialog-repair').hidden,false);assert.equal(get('join-dialog-repair').textContent,'Damaged M4B parts are repaired automatically when the book is converted.');
  assert.equal(get('join-dialog-wait').hidden,true);
  assert.equal(get('join-confirm').textContent,'Join into one book');assert.equal(get('join-confirm').getAttribute('aria-disabled'),null);
  assert.equal(get('join-confirm').title,'Join these 5 books into one book. Nothing is converted yet.');
  assert.equal(get('join-title').title,'The title of the joined book.');assert.equal(get('join-author').title,'The author of the joined book, as it is filed.');
  assert.equal(get('join-cancel').title,'Close without joining. Nothing changes.');
  // 4. Move down keeps focus on the same button of the moved part; the order becomes his.
  await lines[0].moveDown.handlers.click();
  let moved=get('join-dialog-list').children;assert.deepEqual(moved.map(li=>li.children[0].textContent),['Впусти меня 2','Впусти меня 1','Впусти меня 3','Впусти меня 4','Впусти меня 5']);
  assert.equal(document.activeElement,moved[1].moveDown,'focus stays on the moved part\'s Move down');assert.equal(get('join-dialog-order').textContent,'Order set by you.');
  await moved[1].moveUp.handlers.click();moved=get('join-dialog-list').children;assert.equal(document.activeElement,moved[0].moveUp,'at the top its Move up keeps focus (aria-disabled)');
  assert.equal(moved[0].moveUp.getAttribute('aria-disabled'),'true');
  // 5. Title required, author optional; Enter in a field submits nothing.
  get('join-title').value='  ';get('join-title').handlers.input();
  assert.equal(get('join-confirm').getAttribute('aria-disabled'),'true');assert.equal(get('join-confirm').title,'Type a title first.');
  let prevented=false;get('join-title').handlers.keydown({key:'Enter',preventDefault(){prevented=true;}});assert.ok(prevented);assert.equal(posted('/api/candidate/join').length,0);
  get('join-title').value='Впусти меня';get('join-author').value='';get('join-author').handlers.input();
  assert.equal(get('join-author-note').textContent,'No author yet. The book needs one before it can be approved.');assert.equal(get('join-confirm').getAttribute('aria-disabled'),null);
  // 6. Escape cancels: nothing joined, focus to Select this page.
  get('join-dialog').handlers.cancel({preventDefault(){}});assert.equal(run('joinDialog'),null);assert.equal(document.activeElement,get('select-page'));
  assert.equal(posted('/api/candidate/join').length,0,'Cancel joins nothing');
  // 7. A refusal shows and makes Join inert with its reason; parts naming different authors leave Author empty with a line.
  previewAnswer=()=>ok({...PREVIEW,author:'',authors:['Lindqvist John Ajvide','Линдквист Йон'],refusals:[{id:'part-9',title:'Готовая книга',cause:'finished'}]});
  joinButton.handlers.click();await tick();
  assert.equal(get('join-confirm').getAttribute('aria-disabled'),'true');assert.equal(get('join-confirm').title,'«Готовая книга» is already a finished audiobook. Join books that are not converted yet.');
  assert.equal(get('join-dialog-refusals').hidden,false);assert.equal(get('join-author-note').textContent,'The parts name different authors: Lindqvist John Ajvide, Линдквист Йон. Type the author.');
  get('join-cancel').handlers.click();
  // 8. A part converting now: the join waits its turn (2.2 sentence) and the button reads Queue the join.
  previewAnswer=()=>ok({...PREVIEW,order:{...PREVIEW.order,missing:[3],last:5},parts:PREVIEW.parts.filter(p=>p.track!==3),blocked:{kind:'book',cause:'conversion',title:'Впусти меня 2',book_id:'part-2',count:null}});
  joinButton.handlers.click();await tick();
  assert.equal(get('join-confirm').textContent,'Queue the join');assert.equal(get('join-dialog-wait').textContent,'Converting: Впусти меня 2 is running, so this join waits its turn.');
  assert.equal(get('join-dialog-order').textContent,'Order from the album track numbers. The album has 5 parts; part 3 is not selected.');
  get('join-cancel').handlers.click();
  previewAnswer=()=>ok({...PREVIEW,order:{...PREVIEW.order,duplicate:2}});joinButton.handlers.click();await tick();
  assert.equal(get('join-dialog-order').textContent,'Two parts claim track 2. Check the order.');assert.ok(get('join-dialog-order').classList.contains('warn'),'warning colour');
  get('join-cancel').handlers.click();
  // 9. Join: closes, clears the selection, focus to Select this page; always queued; each part row shows it with Cancel.
  previewAnswer=()=>ok(PREVIEW);joinButton.handlers.click();await tick();
  const ITEM={id:'join-1',action:'join',book_id:'part-1',title:'Впусти меня',parts:['part-1','part-2','part-3','part-4','part-5'],n:5,position:1,blocker:{kind:'book',cause:'conversion',title:'Впусти меня 2',book_id:'part-2',count:null}};
  joinAnswer=()=>({ok:true,status:202,json:async()=>({queued:true,id:'join-1',position:1,blocker:ITEM.blocker})});
  backend={...backend,queued_actions:[ITEM]};run('state='+JSON.stringify(backend));inventoryRows=[1,2,3,4,5].map(n=>partRow(n));
  await get('join-confirm').handlers.click({});await tick();
  assert.deepEqual(posted('/api/candidate/join').at(-1),{library:'Audiobooks',items:[1,2,3,4,5].map(n=>({id:'part-'+n,revision:3})),title:'Впусти меня',author:'Lindqvist John Ajvide',queue:true});
  assert.equal(run('joinDialog'),null);assert.equal(run('selectedBooks.size'),0,'the selection clears');assert.equal(document.activeElement,get('select-page'));
  assert.equal(joinButton.hidden,true,'no selection, no button');
  paint([1,2,3,4,5].map(n=>partRow(n)));
  for(const n of [1,3,5]){
    const tr=trOf('part-'+n);assert.equal(joinHintOf(tr).hidden,false);
    assert.equal(joinHintOf(tr).textContent,'Join queued: «Впусти меня», 5 books. It runs when Converting: Впусти меня 2 finishes.');
    const cancel=joinCancelOf(tr);assert.equal(cancel.hidden,false);assert.equal(cancel.getAttribute('aria-label'),'Cancel the whole join: Впусти меня');
  }
  // The jobs panel's words (1.5a, 1.6): one Waiting item and, while it runs, the action row with its step.
  assert.equal(run('queueWord("join")'),'Join into one book');
  assert.equal(run('workLabel({kind:"action",label_key:"join"})'),'Join into one book');
  assert.equal(run('workStep({kind:"action",label_key:"join",count:5,state:"running"},false)'),'Joining 5 books into one book');
  assert.equal(run('workDetail({kind:"action",label_key:"join",count:5,state:"running"},false)'),'','the count is in the step, never "5 files"');
  // 10. Cancel on a part row cancels the whole join.
  cancelAnswer=()=>ok({cancelled:true});backend={...backend,queued_actions:[]};run('state='+JSON.stringify(backend));
  await joinCancelOf(trOf('part-4')).handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/queue/cancel').at(-1),{id:'join-1'});
  assert.equal(joinHintOf(trOf('part-1')).hidden,true);assert.equal(joinCancelOf(trOf('part-1')).hidden,true);
  // 11. The outcome on #join-status with Show it (8.6): with effects, without, and a changed part.
  run('syncQueue('+JSON.stringify({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o1',action:'join',book_id:'part-1',title:'Впусти меня',at:1,result:'done',
    answer:{book_id:'joined',title:'Впусти меня',parts:5,queued:2,requests:1,failed:1,approvals:2,request_kind:'repair'}}]})+')');
  assert.equal(get('join-status').textContent,'Joined 5 books into «Впусти меня». 2 queued conversions taken off the queue. 1 Repair request cancelled. 1 failed attempt set aside.');
  assert.equal(get('join-show').hidden,false);assert.equal(get('join-show').title,'List this book: sets Status to All and searches for its title.');assert.equal(get('join-show').getAttribute('aria-label'),'Show it: Впусти меня');
  run('syncQueue('+JSON.stringify({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o2',action:'join',book_id:'part-1',title:'Впусти меня',at:1,result:'done',answer:{book_id:'joined',title:'Впусти меня',parts:5,queued:0,requests:0,failed:0}}]})+')');
  assert.equal(get('join-status').textContent,'Joined 5 books into «Впусти меня». Approve it when it looks right.');
  run('syncQueue('+JSON.stringify({queued_actions:[],queue_running:null,queue_outcomes:[{id:'o3',action:'join',book_id:'part-1',title:'Впусти меня',at:1,result:'refused',code:'changed',part:'Впусти меня 2',error:'Join cancelled: «Впусти меня 2» changed. Nothing was joined.'}]})+')');
  assert.equal(get('join-status').textContent,'Join cancelled: «Впусти меня 2» changed. Nothing was joined.');assert.ok(get('join-status').classList.contains('retry-refused'));assert.equal(get('join-show').hidden,true);
  // 12. Answer 9: an accepted Repair that has not started has its Cancel on the row, worded as a queued press's Cancel.
  const accepted=blocked({id:'cand-r',path:'cand-r',title_clue:'Ремонт',review:{title:'Ремонт'}},{job_id:'job-r',reason:'Damaged part',retry:undefined,repair:{allowed:true,reason:''},
    readmission:{accepted:true,queued_next:true,position:1,kind:'repair',state:'queued',parent_job_id:'job-r',child_job_id:null},attention:{group:'repair'}});
  run('view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  paint([accepted]);
  const rowCancel=buttonsOf(trOf('cand-r')).find(b=>b.textContent==='Cancel repair');
  assert.ok(rowCancel,'positive control for the face below: the row has its Cancel');assert.equal(rowCancel.hidden,false);
  assert.equal(rowCancel.title,'Take this repair out of the queue. Nothing was started.');assert.equal(rowCancel.getAttribute('aria-label'),'Cancel repair: Ремонт');
  withdrawAnswer=()=>refused(409,{error:'Too late to cancel: the repair has already started.',code:'started'});
  await rowCancel.handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/audiobook/retry-cancel').at(-1),{library:'Audiobooks',id:'cand-r',revision:4,job_id:'job-r'});
  assert.equal(run('retryResult?.text'),'Too late to cancel: the repair has already started.');
  assert.equal(get('retry-note').textContent,'Too late to cancel: the repair has already started.','the details panel says it too');
  const admitted=blocked({id:'cand-s',path:'cand-s'},{job_id:'job-s',retry:undefined,repair:{allowed:true,reason:''},readmission:{accepted:true,queued_next:true,position:1,kind:'repair',state:'admitted',parent_job_id:'job-s',child_job_id:'job-t'},attention:{group:'repair'}});
  paint([admitted]);
  const none=buttonsOf(trOf('cand-s')).find(b=>String(b.textContent).startsWith('Cancel'));assert.ok(!none || none.hidden,'its check began: no Cancel (the existing queued face)');
  withdrawAnswer=()=>ok({withdrawn:true,kind:'repair'});paint([accepted]);
  await buttonsOf(trOf('cand-r')).find(b=>b.textContent==='Cancel repair').handlers.click({stopPropagation(){}});await tick();
  assert.equal(posted('/api/audiobook/retry-cancel').length,2);
  // 13. A15: a joined book not yet approved and with no job offers the existing Keep as separate books, which undoes the join.
  run('view="candidates";filters.candidates="all";viewControls()');
  const JOINED={joined:{version:'book-join-v1',join_id:'j1',files:5,books:5},title_clue:'Впусти меня'};
  const keepOf=tr=>buttonsOf(tr).find(b=>b.textContent==='Keep as separate books' || b.textContent==='Keeping...');
  inventoryRows=[partRow(7,JOINED),partRow(8,{...JOINED,metadata_approved:true}),partRow(6,{...JOINED,creation:{status:'Queued',can_create:false,reasons:[],job:{job_id:'job-6',state:'Queued'}}}),partRow(5)];paint(inventoryRows);
  const keep=keepOf(trOf('part-7'));assert.ok(keep,'the joined book offers Keep as separate books');
  assert.equal(keep.title,'Make each file shown its own book. Nothing is joined. Each book is checked again.');assert.equal(keep.getAttribute('aria-label'),'Keep as separate books: Впусти меня');
  assert.equal(keepOf(trOf('part-8')),undefined,'approved: no undo');assert.equal(keepOf(trOf('part-6')),undefined,'with a job: no undo');
  assert.equal(keepOf(trOf('part-5')),undefined,'positive control: a book nobody joined has no such button');
  let keepAnswer=()=>refused(409,{error:'Keep as separate books was not accepted. Nothing was changed.',code:'refused'});const keepFetch=context.fetch;
  context.fetch=async(route,options)=>route==='/api/candidate/keep-separate'?(calls.push({route,options}),keepAnswer(JSON.parse(options.body))):keepFetch(route,options);
  await keep.handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/candidate/keep-separate').at(-1),{library:'Audiobooks',id:'part-7',revision:3,queue:true,title:'Впусти меня'});
  assert.equal(joinHintOf(trOf('part-7')).textContent,'Keep as separate books was not accepted. Nothing was changed.');assert.equal(joinHintOf(trOf('part-7')).hidden,false);
  keepAnswer=()=>ok({kept:5});await keepOf(trOf('part-7')).handlers.click({stopPropagation(){}});await tick();
  assert.equal(posted('/api/candidate/keep-separate').length,2);assert.equal(run('askDone.get("part-7")'),'separate');
  // 14. The Book metadata line (item E) for a joined book.
  assert.equal(run('scopeBasisText({kind:"joined",basis:5,album:"Впусти меня",artist:"John Ajvide Lindqvist",track:null,track_total:null,repaired:false,folders:[]})'),'Joined by you from 5 books. Album «Впусти меня».');
  assert.equal(run('scopeBasisText({kind:"joined",basis:3,album:null,repaired:false,folders:[]})'),'Joined by you from 3 books.');
  // 15. QA D1: a queued join nothing blocks (blocker null; it is about to run) shows no waiting line and no Cancel on its parts,
  // and no Waiting item; a press behind it still says what it waits for.
  run('view="candidates";filters.candidates="all";viewControls()');
  const IDLE={id:'join-2',action:'join',book_id:'part-1',title:'Впусти меня',parts:['part-1','part-2'],n:2,position:1,blocker:null};
  run('queueState={queued:'+JSON.stringify([IDLE])+',running:null}');inventoryRows=[partRow(1),partRow(2)];paint(inventoryRows);
  assert.equal(joinHintOf(trOf('part-1')).hidden,true,'no waiting line');assert.equal(joinCancelOf(trOf('part-1')).hidden,true,'no Cancel for an instant');
  run('queueState={queued:'+JSON.stringify([{...IDLE,blocker:{kind:'scan',cause:'scan'}}])+',running:null};controls()');
  assert.equal(joinHintOf(trOf('part-1')).textContent,'Join queued: «Впусти меня», 2 books. It runs when the library scan finishes. Stop scanning to run it sooner.','positive control: a real blocker is said');
  // 0.31.0: the page's own work view also carries the look-ups between tries (workView's lookups; none here).
  const waitingOf=item=>run('waitingList('+JSON.stringify({waiting:[item],counts:{},lookups:[]})+').length');
  assert.equal(waitingOf({id:'action:join-2',kind:'action',label_key:'join',subject:'Впусти меня',book_id:'part-1',blocker:null,ahead:0}),0,'no Waiting item');
  assert.equal(waitingOf({id:'action:join-2',kind:'action',label_key:'join',subject:'Впусти меня',book_id:'part-1',blocker:{kind:'scan',cause:'scan'},ahead:0}),1);
  assert.equal(run('queueHint('+JSON.stringify(partRow(5))+')'),null);
  run('queueState={queued:'+JSON.stringify([{id:'ap',action:'approve',book_id:'part-5',title:'Впусти меня 5',position:1,blocker:null}])+',running:null}');
  assert.equal(run('queueHint('+JSON.stringify(partRow(5))+')'),'Approve queued.','an Approve nothing blocks names no wait');
  run('queueState={queued:[],running:null}');
  // 16. Futaba's QA, slice D item 2: the queue strip names no wait for an action nothing blocks (it read "It runs when the app
  // is free."); with a blocker it still says what the action waits for.
  run("view='candidates';filters[view]='output_attention'");
  run('queueState={queued:'+JSON.stringify([{id:'ap',action:'approve',book_id:'part-5',title:'Впусти меня 5',position:1,blocker:null}])+',running:null};renderAttentionGroups()');
  assert.equal(get('queue-line').textContent,'1 action waiting.');assert.equal(get('queue-line').hidden,false);
  run('queueState={queued:'+JSON.stringify([{id:'ap',action:'approve',book_id:'part-5',title:'Впусти меня 5',position:1,blocker:null},{id:'jn',action:'join',book_id:'part-1',title:'Впусти меня',position:2,blocker:{kind:'operation',cause:'operation'}}])+',running:null};renderAttentionGroups()');
  assert.equal(get('queue-line').textContent,'2 actions waiting, one at a time. First: Approve: Впусти меня 5.');
  run('queueState={queued:'+JSON.stringify([{id:'ap',action:'approve',book_id:'part-5',title:'Впусти меня 5',position:1,blocker:{kind:'scan',cause:'scan'}}])+',running:null};renderAttentionGroups()');
  assert.equal(get('queue-line').textContent,'1 action waiting. It runs when the library scan finishes. Stop scanning to run it sooner.','positive control: a real blocker is said');
  run("queueState={queued:[],running:null};view='candidates';filters[view]='all'");
  console.log('PASS Join into one book: button states, dialog (order, moves and focus, fields, Goes to, What happens, refusals, waiting), queued press with each part row\'s line and Cancel, outcome with Show it, jobs panel words; answer 9 row Cancel; A15 Keep as separate books on a joined book; the joined Book metadata line; D1 no waiting line without a blocker; the queue strip without a blocker');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_join_frontend.js'),module);m.filename=path.join(__dirname,'test_join_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

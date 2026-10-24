'use strict';
// Judy's 0.22.0 review of the to-do list (Docs/BooksArranger_AttentionTodo_UX_2026-10-24.md, part "0.22.0 review"): the
// three hold chips with one row per typed cause, the file list Approve uses, the per-chip faces, Change order / Choose
// files, Scan again on a hold row, Other's catch-all, the "No choice" lines, unsaved panel edits, Retry selected hidden in
// every "Needs your answer" chip, the "Still checking" line and empty state, and the copy changes. Real frontend on the
// Retry test's DOM/transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted';
function askRow(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'Z:\\Audiobooks\\'+name+'\\01.mp3'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['Playback order uncertain']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const dest=p=>({path:p,absolute:ROOT+'\\'+p,taken:false,reason:''});
const named={title:{proposal:'Колесо Времени',basis:'tag'},author:{proposal:'Роберт Джордан',basis:'tag'}};
const files=(n,folder='Z:\\Audiobooks\\Колесо')=>Array.from({length:Math.min(n,6)},(_,i)=>({name:String(i+1).padStart(2,'0')+' Глава.mp3',folder,path:folder+'\\'+String(i+1).padStart(2,'0')+' Глава.mp3',track:'',disc:'',flag:false}));
function hold(name,kind,cause,facts={},extra={}){return askRow(name,{kind,also:null,why:'',reasons:['x'],fields:named,candidates:[],cause,facts,files:files(12),file_count:12,flagged:[],saved_tracks:false,reason:'',destination:dest('Джордан Роберт\\Колесо Времени - Джордан Роберт.m4b'),...extra});}
const COUNTS={files_missing:1,title_author:0,author_unclear:1,same_author:1,name_taken:0,part_of_book:6,files_unclear:7,order_unclear:5,retry:1,repair:0,reacquire:0,checking:0,changed:0,audiobook:0,other:1,unsupported:0};
backend={...backend,audiobook_output_root:ROOT,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:COUNTS,todo_still_checking:0}};
let scanAnswer=null,approveAnswer=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/candidate/scan-again'){calls.push({route,options});return scanAnswer?scanAnswer(data):{ok:true,status:200,json:async()=>({found:true,changed:false})};}
  if(route==='/api/candidate/approve'){calls.push({route,options});return approveAnswer?approveAnswer(data):{ok:true,status:200,json:async()=>({approved:true,job_id:'j',row:{}})};}
  if(route==='/api/candidate/approve-preview'){calls.push({route,options});return {ok:true,status:200,json:async()=>({preview:{path:'x.m4b',taken:false}})};}
  return baseFetch(route,options);
};
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const texts=tr=>walk(statusCell(tr)).map(e=>e.textContent);
const hint=tr=>{const h=statusCell(tr).children[0];return h.textContent+h.children.map(s=>s.textContent).join('');};
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  // Chips: the three join "Needs your answer"; All = the sum of every chip.
  run('controls();renderJobs()');
  assert.equal(get('group-part_of_book').textContent,'Part of a bigger book · 6');assert.equal(get('group-files_unclear').textContent,'Files unclear · 7');
  assert.equal(get('group-order_unclear').textContent,'Order unclear · 5');
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
  for(const [key,tip] of [['part_of_book','Show books that may be only one part of a bigger book.'],['files_unclear',"Show books where the app isn't sure which files belong."],['order_unclear',"Show books where the app isn't sure of the playback order."]])
    assert.ok(html.includes('id="group-'+key+'" type="button" class="quiet attention-group" aria-pressed="false" title="'+tip+'" hidden>'),key);
  assert.equal(get('group-all').textContent,'All · 23');assert.equal(get('attention-shortcut').textContent,'Needs attention · 23');assert.match(get('jobs-status').textContent,/ · 23 need attention$/);

  // Order unclear: one sentence per cause, the "Playback order" list of 5, then "+ n more".
  const order=[hold('o1','order_unclear','no_tracks',{missing:12,total:12}),hold('o2','order_unclear','some_missing',{missing:3,total:12}),hold('o3','order_unclear','some_missing',{missing:1,total:12}),
    hold('o4','order_unclear','tied'),hold('o5','order_unclear','gaps'),hold('o6','order_unclear','unknown'),hold('o7','order_unclear','conflict'),hold('o8','order_unclear','odd_tracks')];
  paint(order);
  assert.deepEqual(order.map(r=>hint(trOf(r.id))),['No file has a track number. The order comes from the file names.','3 of 12 files have no track number.','1 of 12 files has no track number.',
    'Some files share a track number.',"Track numbers skip or don't start at 1.","The app can't be sure of the playback order.",
    'The file names and the track tags number the files differently.',"Some track tags aren't plain numbers."]);
  let tr=trOf('cand-o1');
  assert.equal(run('candidateStatus(rows[0])'),'Order unclear');
  const list=walk(statusCell(tr)).find(e=>e.className==='path ask-order');assert.equal(list.getAttribute('aria-label'),'Playback order');
  assert.deepEqual(list.children.map(li=>li.textContent),['01 Глава.mp3','02 Глава.mp3','03 Глава.mp3','04 Глава.mp3','05 Глава.mp3']);
  assert.ok(texts(tr).includes('Playback order'));assert.ok(texts(tr).includes('+ 7 more, listed in the details panel.'));
  assert.deepEqual(buttonsOf(tr).slice(0,3).map(b=>b.textContent),['Approve this order','Change order','Scan again']);
  assert.equal(buttonsOf(tr)[0].title,'Approve the order shown: convert if needed, rename, move to Audiobooks Sorted.');assert.equal(buttonsOf(tr)[0].getAttribute('aria-label'),'Approve this order: Title o1');
  assert.equal(buttonsOf(tr)[1].title,'Change the playback order in the details panel. Save it there, then approve.');
  assert.equal(buttonsOf(tr)[2].title,"Check this book's folders again, for example after you rename or add files. Nothing is changed or deleted.");
  assert.ok(buttonsOf(tr).slice(0,3).every(b=>b.className.includes('ask-convert')),'faces at least 152 wide');
  // Change order: the row is selected, Manual review opens and focus lands on its included-files heading.
  get('manual-review').open=false;await buttonsOf(tr)[1].handlers.click({stopPropagation(){}});
  assert.equal(run('selectedPath'),'cand-o1');assert.equal(get('manual-review').open,true);assert.equal(document.activeElement,get('member-count'));
  // Unsaved order edits in the panel: Approve waits for them (0.22.0 review A5).
  run('trackDirty=true;trackDraft={id:"cand-o1"};controls()');
  assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true');assert.equal(buttonsOf(tr)[0].title,'Save or discard the edits in the details panel first.');
  run('trackDirty=false;trackDraft=null;controls()');assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);
  // Approve this order sends the row as shown.
  await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(JSON.parse(calls.filter(c=>c.route==='/api/candidate/approve').at(-1).options.body),{library:'Audiobooks',id:'cand-o1',revision:2});
  // Scan again on a hold row: unchanged -> "Checked hh:mm. No change."; changed -> the book leaves and is checked again.
  tr=trOf('cand-o2');await buttonsOf(tr)[2].handlers.click({stopPropagation(){}});await tick();
  assert.match(hint(tr),/^3 of 12 files have no track number\. Checked \d\d:\d\d\. No change\.$/);
  scanAnswer=()=>({ok:true,status:200,json:async()=>({found:true,changed:true,scan_started:false,scan_later:false})});
  await buttonsOf(tr)[2].handlers.click({stopPropagation(){}});await tick();
  assert.equal(statusCell(tr).children[0].textContent,'Changes found. The book is checked again.');assert.equal(get('retry-all-status').textContent,'Changes found. The book is checked again.');
  scanAnswer=()=>({ok:true,status:200,json:async()=>({found:false,changed:true,scan_started:false,scan_later:true})});
  tr=trOf('cand-o3');await buttonsOf(tr)[2].handlers.click({stopPropagation(){}});await tick();
  assert.equal(get('retry-all-status').textContent,'Changes found. The next library scan will pick them up.');scanAnswer=null;
  // The audio-format gate is named in the refusal line (B5.4).
  approveAnswer=()=>({ok:false,status:409,json:async()=>({error:'Audio format needs an encoding decision',code:'format',row:null})});
  tr=trOf('cand-o4');await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();
  assert.equal(statusCell(tr).children[0].textContent,"The audio format needs a decision the app can't make yet. Select the row to read why.");approveAnswer=null;

  // Files unclear: every cause, the "In" folder line and 3 names (files without the title first), mixed albums.
  const flagged=[{name:'Реклама.mp3',folder:'Z:\\Audiobooks\\Дюна',path:'x',flag:true}];
  const filesRows=[hold('f1','files_unclear','track_total',{tags_say:12,here:9}),hold('f2','files_unclear','disc_total',{tags_say:3,here:2}),hold('f3','files_unclear','one_of_many',{index:7,total:20}),
    hold('f4','files_unclear','lack_title',{missing:1,total:9},{flagged}),hold('f5','files_unclear','lack_title',{missing:2,total:9}),
    hold('f6','files_unclear','mixed',{albums:[{name:'A',files:5},{name:'(none)',files:3},{name:'C',files:2},{name:'D',files:1}],artists:[]}),hold('f9','files_unclear','mixed',{albums:[],artists:[{name:'P',files:2},{name:'(none)',files:1}]}),hold('f7','files_unclear','parts'),hold('f8','files_unclear','unknown')];
  paint(filesRows);
  assert.deepEqual(filesRows.map(r=>hint(trOf(r.id))),['The tags say 12 tracks, but 9 files are here.','The tags say 3 discs, but 2 are here.',"This file is tagged as track 7 of 20. The other tracks aren't here.",
    "1 of 9 files doesn't mention this book's title.","2 of 9 files don't mention this book's title.",'The files carry different albums or artists. They may be more than one book.',
    'The files carry different albums or artists. They may be more than one book.',"The parts of this set don't number cleanly.","The app can't be sure which files belong to this book."]);
  tr=trOf('cand-f1');assert.deepEqual(texts(tr).filter(t=>/^In |\.mp3$|more, listed/.test(t)),['In Z:\\Audiobooks\\Колесо\\','01 Глава.mp3','02 Глава.mp3','03 Глава.mp3','+ 9 more, listed in the details panel.']);
  assert.deepEqual(buttonsOf(tr).slice(0,3).map(b=>b.textContent),['Approve these files','Choose files','Scan again']);
  assert.equal(buttonsOf(tr)[1].title,'Choose which files belong in the details panel. Save it there, then approve.');
  assert.ok(texts(trOf('cand-f4')).includes('Реклама.mp3'),'the file without the title is named first');
  assert.ok(texts(trOf('cand-f6')).includes('Albums: A (5 files) · No album (3 files) · C (2 files) + 1 more'));assert.ok(texts(trOf('cand-f9')).includes('Artists: P (2 files) · No artist (1 file)'),'copy check, nice-to-have 1');

  // Part of a bigger book: every cause; Title always shows; Approve as one book + Scan again, no list editing.
  const parts=[hold('p1','part_of_book','chapter'),hold('p2','part_of_book','numbered_part'),hold('p3','part_of_book','siblings',{beside:1}),hold('p4','part_of_book','siblings',{beside:3}),
    hold('p5','part_of_book','part_set',{index:2,total:5,set:'Торадора!'}),hold('p6','part_of_book','unreadable'),hold('p7','part_of_book','unknown')];
  paint(parts);
  assert.deepEqual(parts.map(r=>hint(trOf(r.id))),['This file is named as one chapter.','The name marks this as one numbered part.','Another file beside it carries the same title.',
    '3 other files beside it carry the same title.','Part 2 of 5 of "Торадора!".',"The other files in this folder couldn't be checked.","The app can't tell if this is a whole book."]);
  tr=trOf('cand-p1');assert.equal(walk(statusCell(tr)).filter(e=>e.type==='text')[0].value,'Колесо Времени','Title always shows here');
  assert.deepEqual(buttonsOf(tr).slice(0,2).map(b=>b.textContent),['Approve as one book','Scan again']);assert.ok(!buttonsOf(tr).some(b=>/Change order|Choose files/.test(b.textContent)));

  // Also: the next hold, first sentence only; Other's catch-all with its short reason.
  const both=hold('b1','files_unclear','track_total',{tags_say:12,here:9},{also:'order_unclear',also_cause:'tied',also_facts:{}});
  const other=askRow('x1',{kind:'other',also:null,why:'',reasons:['Manual draft retained'],reason:'Manual draft retained',fields:named,candidates:[],destination:dest('a.m4b')});
  const otherLong=askRow('x2',{kind:'other',also:null,why:'',reasons:['x'.repeat(90)],reason:'x'.repeat(90),fields:named,candidates:[],destination:dest('b.m4b')});
  const reader=askRow('r1',{kind:'files_missing',also:'author_unclear',why:'reader',reasons:['Files missing'],fields:{title:{proposal:'Тайна',basis:'tag'},author:{proposal:'',basis:''}},candidates:[{name:'Иван Петров',source:'file name',reader_count:3}],
    missing:{folders:['Z:\\a'],files:['Z:\\a\\1.mp3'],present:1,total:2},destination:dest('Без автора\\Тайна.m4b')});
  paint([both,other,otherLong,reader]);
  assert.ok(texts(trOf('cand-b1')).includes('Also: some files share a track number.'));
  assert.equal(run('candidateStatus(rows[1])'),'Needs you');assert.equal(hint(trOf('cand-x1')),'This book needs your decision.');
  assert.ok(texts(trOf('cand-x1')).includes('Reason: Manual draft retained'));assert.ok(!texts(trOf('cand-x2')).some(t=>t.startsWith('Reason:')),'a long reason stays in Technical details');
  assert.ok(texts(trOf('cand-r1')).includes('Also: the only name credited may be the reader.'),'first sentence only (A1a)');
  // Reader-only: nothing chosen, the line says what Approve alone does; choosing hides it (A2).
  tr=trOf('cand-r1');const line=walk(statusCell(tr)).find(e=>e.className==='field-help ask-nochoice');
  assert.equal(line.textContent,'No choice files it under Без автора.');assert.equal(line.hidden,false);
  const radio=walk(statusCell(tr)).find(e=>e.type==='radio');radio.checked=true;await radio.handlers.change();await tick();assert.equal(line.hidden,true);
  // Same author?: its own line while nothing is chosen (A3).
  const same=askRow('s1',{kind:'same_author',also:null,why:'near',reasons:['Same author?'],fields:named,candidates:[],same_author:{new:'Terry Pratchet',existing:'Terry Pratchett',existing_books:41,why:'near',count:1},destination:dest('c.m4b')});
  paint([same]);assert.equal(walk(statusCell(trOf('cand-s1'))).find(e=>e.className==='field-help ask-nochoice').textContent,'No choice files it as written. Nothing is remembered.');

  // Retry selected hides in every "Needs your answer" chip; it stays in All. Approve as is never in the three new chips.
  for(const key of ['files_missing','same_author','part_of_book','files_unclear','order_unclear']){run('attentionGroup="'+key+'";controls()');assert.equal(get('retry-selected').hidden,true,key);assert.equal(get('approve-selected').hidden,true,key);}
  run('attentionGroup="all";controls()');assert.equal(get('retry-selected').hidden,false);

  // Still checking: the strip line in both states, and the empty list (B5.2).
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,todo_still_checking:1203},automatic_processing:{...state.automatic_processing,state:"Running"}};controls()');
  assert.equal(get('attention-sweep').textContent,'Still checking 1,203 books. More may appear here.');assert.equal(get('attention-sweep').hidden,false);
  paint([]);assert.equal(get('empty').textContent,'Nothing needs your attention yet. Still checking 1,203 books.','running: checking');
  run('state={...state,automatic_processing:{...state.automatic_processing,state:"Idle"}};controls()');
  assert.equal(get('attention-sweep').textContent,'1,203 books are waiting to be checked. Start automatic processing to check them.');
  // Judy's copy check (must-fix): not running, the empty list never says "checking" under a line that says "waiting".
  paint([]);assert.equal(get('empty').textContent,'Nothing needs your attention yet. 1,203 books are waiting to be checked.');
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,todo_still_checking:1}};controls()');
  assert.equal(get('attention-sweep').textContent,'1 book is waiting to be checked. Start automatic processing to check it.','one book: "it" (copy check, nice-to-have 3)');
  paint([]);assert.equal(get('empty').textContent,'Nothing needs your attention yet. 1 book is waiting to be checked.');
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,todo_still_checking:0}};controls()');assert.equal(get('attention-sweep').hidden,true,'hidden at zero');
  paint([]);assert.equal(get('empty').textContent,'Nothing needs your attention.');

  // Copy: the Copy failure names the key (A1d); the activity line points at the list (A6).
  context.navigator=undefined;await get('copy-technical').handlers.click();assert.equal(get('copy-technical-status').textContent,"Couldn't copy. Select the text and press Ctrl+C.");
  context.fixture={kind:'conversion',state:'attention',reason:'Full audio decode failed:\n[Parsed_...]'};assert.equal(run('activityStep(fixture,false)'),'On hold — see Needs attention');
  context.setTimeout=()=>0;
  console.log('PASS to-do 0.22.0 review: three hold chips, one sentence per cause, lists and faces, Change order, Scan again, catch-all, No choice lines, unsaved edits, Retry selected, Still checking, copy');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_todo_holds_frontend.js'),module);m.filename=path.join(__dirname,'test_todo_holds_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

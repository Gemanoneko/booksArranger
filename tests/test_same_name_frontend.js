'use strict';
// 0.31.0 (Judy's Docs/BooksArranger_0.31.0_UX.md, section 4 as amended by G9; Sergei's R15 and R17): two books, one
// destination. The engine reports destination.shared on every to-do row whose planned name another book also has. Only a
// row the engine holds for the clash itself (ask.hold.kind same_destination, listed under Name taken) reads "Same name as
// another book" (class S). A file with the name on disk keeps the 0.30.0 Name taken row (class D). Every other row keeps its
// own status, sentence, fields and buttons and gains three things while shared is set: the label, its approve press
// prevented with the reason, and Show both books (class Q). Also the engine's same_name refusal, the Name taken chip's
// tooltip, the Place line's origin suffix and the details line of a volume named from its own tags (4.3).
// Real frontend on the Retry test's DOM/transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted',SHARED='Gibson William\\Sprawl Trilogy - Gibson William.m4b';
function askRow(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,fingerprint:'a'.repeat(64),scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'Z:\\Audiobooks\\William Gibson\\'+name+'.m4b'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['x']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const other=(name,kind='row',extra={})=>({book_id:'other-'+name,kind,name,title:'Sprawl Trilogy',author:'William Gibson',...(kind==='queued'?{job_id:'job-'+name}:{}),...extra});
const shared=(...others)=>({kind:'same_destination',detail:'',destination:SHARED,absolute:ROOT+'\\'+SHARED,count:others.length,others});
const more=n=>({...shared(other('02-Граф Ноль'),other('03-Мона Лиза овердрайв')),count:n});
const dest=(extra={})=>({path:SHARED,absolute:ROOT+'\\'+SHARED,taken:false,reason:'',shared:null,...extra});
const named={title:{proposal:'Sprawl Trilogy',basis:'tag'},author:{proposal:'William Gibson',basis:'tag'}};
const base=(kind,extra={})=>({kind,also:null,why:'',reasons:['x'],fields:named,candidates:[],hold:{kind:''},destination:dest(),...extra});
// Class S: the engine holds the row for the clash alone.
const sameName=(name,held,extra={})=>askRow(name,base('name_taken',{reasons:['Another book would get the same name'],hold:{kind:'same_destination',count:held.count,others:held.others},destination:dest({shared:held}),...extra}));
const files=n=>Array.from({length:n},(_,i)=>({name:'0'+(i+1)+'.m4b',folder:'Z:\\Audiobooks\\William Gibson',path:'Z:\\Audiobooks\\William Gibson\\0'+(i+1)+'.m4b',track:'',disc:'',flag:false}));
const holdRow=(name,kind,cause,held,extra={})=>askRow(name,base(kind,{cause,facts:{index:2,total:3,set:'Sprawl Trilogy',beside:2},files:files(3),file_count:3,flagged:[],saved_tracks:false,reason:'',hold:{kind:'piece'},destination:dest({shared:held}),...extra}));
const COUNTS={files_missing:1,title_author:1,author_unclear:1,same_author:0,name_taken:5,part_of_book:2,files_unclear:1,order_unclear:1,retry:0,repair:0,reacquire:0,checking:0,changed:0,audiobook:0,other:1,unsupported:0};
backend={...backend,audiobook_output_root:ROOT,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:COUNTS,todo_still_checking:0}};
let approveAnswer=null,previewAnswer=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/candidate/approve'){calls.push({route,options});if(approveAnswer)return approveAnswer(data);return {ok:true,status:200,json:async()=>({approved:true,job_id:'j',row:{}})};}
  if(route==='/api/candidate/approve-preview'){calls.push({route,options});if(previewAnswer)return previewAnswer(data);return {ok:true,status:200,json:async()=>({preview:{path:'Gibson William\\'+(data.title || 'x')+' - Gibson William.m4b',absolute:'',taken:false,shared:null}})};}
  return baseFetch(route,options);
};
const posted=route=>calls.filter(call=>call.route===route).map(call=>JSON.parse(call.options.body));
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],actions=tr=>tr.children[5],buttonsOf=tr=>[...actions(tr).children[0].children];
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const hint=tr=>{const h=statusCell(tr).children[0];return h.textContent+h.children.map(s=>s.textContent).join('');};
const inputs=tr=>walk(statusCell(tr)).filter(e=>e.type==='text');
const line=tr=>walk(statusCell(tr)).find(e=>e.className==='goes-to');
const goesTo=tr=>{const found=line(tr);return found.hidden?'':found.children.map(c=>c.textContent).join(' ');};
const warned=tr=>line(tr).classes.has('taken');
const reason=tr=>{const block=actions(tr).children[1];return block.hidden?'':block.children[0].textContent;};
const faces=tr=>buttonsOf(tr).filter(b=>b.id==='button' && !b.hidden).map(b=>b.textContent);
const showBoth=tr=>buttonsOf(tr).find(b=>/^Show (both|all \d+) books$/.test(b.textContent));
const press={stopPropagation(){}};
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row,ask:{...row.ask,destination:{...row.ask.destination}}}));totalRows=rows.length;askDrafts.clear();askResults.clear();renderRows(true);controls()');}
const BLOCK='Another book would get this name. Change the title, author, series or number.';
const TIP='List the books that would get this name: sets Status to All and searches for this title.';
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls();controls()');
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
  // The chip counts both kinds of taken name and its tooltip says so (4.1).
  assert.ok(html.includes('id="group-name_taken" type="button" class="quiet attention-group" aria-pressed="false" title="Show books whose name is already used, in Audiobooks Sorted or by another book here." hidden>'));
  assert.equal(get('group-name_taken').textContent,'Name taken · 5');

  // 1. Class S (check 11): held for the clash alone. Status, the sentence naming the other book's file or folder, the label
  // in the warning style, Approve prevented with its reason, Show both books right after Approve.
  const one=sameName('s1',shared(other('03-Мона Лиза овердрайв'))),queued=sameName('s2',shared(other('Нейромант (Гибсон)','queued'))),three=sameName('s3',more(2)),many=sameName('s4',more(14));
  paint([one,queued,three,many]);
  let tr=trOf('cand-s1');
  assert.equal(statusCell(tr).textContent,'Same name as another book');assert.equal(run('candidateStatus(rows[0])'),'Same name as another book');
  assert.equal(hint(tr),'Another book would get this file name: «03-Мона Лиза овердрайв». Change a title, author, series or number so they differ.');
  assert.equal(goesTo(tr),'Both go to Audiobooks Sorted\\'+SHARED);assert.equal(warned(tr),true,'the warning style Already there uses');
  assert.deepEqual(faces(tr).slice(0,2),['Approve','Show both books'],'in the action order after Approve');
  assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true');assert.equal(buttonsOf(tr)[0].title,BLOCK,'a prevented press says why in its tooltip');assert.equal(reason(tr),BLOCK);
  assert.equal(showBoth(tr).title,TIP);assert.equal(showBoth(tr).getAttribute('aria-disabled'),null,'never disabled');assert.equal(showBoth(tr).getAttribute('aria-label'),'Show both books: Title s1');
  assert.ok(String(showBoth(tr).className || '').split(' ').includes('quiet') && String(showBoth(tr).className || '').split(' ').includes('row-retry'),'quiet, 96 x 32 minimum (.row-actions .row-retry)');
  // Never on a class S row: Part of a bigger book, Approve as one book, Keep as separate books, a Join hint.
  for(const never of ['Approve as one book','Keep as separate books'])assert.ok(!faces(tr).includes(never),never);
  assert.ok(!walk(tr).some(e=>/Part of a bigger book|Join/.test(e.textContent)),'no Part of a bigger book and no Join hint on a class S row');
  // Title and Author on the row, as a Name taken row.
  assert.deepEqual(inputs(tr).map(input=>input.dataset.name),['title','author']);
  let sent=posted('/api/candidate/approve').length;await buttonsOf(tr)[0].handlers.click(press);assert.equal(posted('/api/candidate/approve').length,sent,'prevented, not refused');
  // A book waiting to convert has the name.
  assert.equal(hint(trOf('cand-s2')),'A book waiting to convert has this file name: «Нейромант (Гибсон)». Change a title, author, series or number so they differ.');
  assert.equal(goesTo(trOf('cand-s2')),'Both go to Audiobooks Sorted\\'+SHARED);
  // Several: the count is the engine's (it names at most ten one by one), plus this book.
  tr=trOf('cand-s3');assert.equal(hint(tr),'2 other books would get this file name. Change a title, author, series or number so they differ.');
  assert.equal(goesTo(tr),'All 3 go to Audiobooks Sorted\\'+SHARED);assert.equal(showBoth(tr).textContent,'Show all 3 books');
  tr=trOf('cand-s4');assert.equal(hint(tr),'14 other books would get this file name. Change a title, author, series or number so they differ.');
  assert.equal(goesTo(tr),'All 15 go to Audiobooks Sorted\\'+SHARED);assert.equal(showBoth(tr).textContent,'Show all 15 books');

  // A name he types that is free: the label and the press return to normal at once and Show both books goes. The row is
  // still the engine's same-name row (its own hold), so its status and what held the name stay until it is checked again.
  tr=trOf('cand-s1');let [title]=inputs(tr);title.value='Граф Ноль';title.handlers.input();await title.handlers.blur();await tick();
  assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null,'enabled as soon as this row\'s Goes to differs');assert.equal(reason(tr),'');
  assert.equal(goesTo(tr),'Goes to Audiobooks Sorted\\Gibson William\\Граф Ноль - Gibson William.m4b');assert.equal(warned(tr),false);assert.equal(showBoth(tr).hidden,true);
  assert.equal(run('candidateStatus(rows[0])'),'Same name as another book');assert.match(hint(tr),/^Another book would get this file name: «03-Мона Лиза овердрайв»\./);
  // A typed name another book has too: the latest answer decides (the preview carries shared).
  previewAnswer=data=>({ok:true,status:200,json:async()=>({preview:{path:'Gibson William\\'+data.title+' - Gibson William.m4b',absolute:'',taken:false,shared:{...shared(other('01-Нейромант','queued')),destination:'x'}}})});
  title.value='Нейромант';title.handlers.input();await title.handlers.blur();await tick();
  assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true');assert.equal(reason(tr),BLOCK);assert.match(goesTo(tr),/^Both go to /);assert.equal(showBoth(tr).hidden,false);
  assert.match(hint(tr),/^A book waiting to convert has this file name: «01-Нейромант»\./);
  // A typed name that is on disk: the name on disk wins (the 0.30.0 line and reason), Show both books goes.
  previewAnswer=data=>({ok:true,status:200,json:async()=>({preview:{path:'Gibson William\\'+data.title+'.m4b',absolute:'',taken:true,shared:shared(other('01-Нейромант'))}})});
  title.value='Нейромант 1';title.handlers.input();await title.handlers.blur();await tick();
  assert.match(goesTo(tr),/^Already there /);assert.equal(reason(tr),'That name is already in Audiobooks Sorted. Change the title or author.');assert.equal(showBoth(tr).hidden,true);
  previewAnswer=null;

  // The live check names no other book any more (the clash ended, the row waits to be checked again): the sentence keeps
  // what the engine recorded when it held the row; nothing is prevented.
  paint([askRow('s5',base('name_taken',{hold:{kind:'same_destination',count:1,others:[other('03-Мона Лиза овердрайв')]},destination:dest()}))]);tr=trOf('cand-s5');
  assert.equal(statusCell(tr).textContent,'Same name as another book');assert.match(hint(tr),/^Another book would get this file name: «03-Мона Лиза овердрайв»\./);
  assert.match(goesTo(tr),/^Goes to /);assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);assert.equal(showBoth(tr).hidden,true);

  // 2. Class D: a file with the name is on disk. The 0.30.0 Name taken row, unchanged; shared adds nothing to it.
  const disk=askRow('d1',base('name_taken',{reasons:['An audiobook already exists at this path.'],destination:dest({taken:true,shared:shared(other('03-Мона Лиза овердрайв'))})}));
  paint([disk]);tr=trOf('cand-d1');
  assert.equal(statusCell(tr).textContent,'Name taken');assert.equal(hint(tr),'A book with this name is already in Audiobooks Sorted.');
  assert.equal(goesTo(tr),'Already there Audiobooks Sorted\\'+SHARED);assert.equal(buttonsOf(tr)[0].title,'That name is already in Audiobooks Sorted. Change the title or author.');
  assert.equal(reason(tr),'That name is already in Audiobooks Sorted. Change the title or author.');assert.equal(showBoth(tr).hidden,true);
  assert.ok(!faces(tr).some(face=>/^Show (both|all)/.test(face)));

  // 3. Class Q (check 15): pieces of one book that all carry the set's name. Each keeps Part of a bigger book, its own
  // sentence, Approve as one book (prevented, with the reason) and Keep as separate books (enabled); the label counts them;
  // Show all 3 books is the last button of the row. shared.kind reads same_destination here too: it is never the test.
  const piece=holdRow('q1','part_of_book','set_unclear',more(2)),sibling=holdRow('q2','part_of_book','part_set',more(2));
  paint([piece,sibling,sameName('s6',shared(other('02-Граф Ноль')))]);tr=trOf('cand-q1');
  assert.equal(piece.ask.destination.shared.kind,'same_destination');
  assert.equal(statusCell(tr).textContent,'Part of a bigger book');assert.equal(hint(tr),"The chapters don't show whether these files make one book.");
  assert.equal(hint(trOf('cand-q2')),'Part 2 of 3 of "Sprawl Trilogy".');
  assert.deepEqual(faces(tr).slice(0,3),['Approve as one book','Keep as separate books','Scan again'],'its own buttons, faces unchanged');
  assert.equal(buttonsOf(tr)[0].title,BLOCK);assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true');assert.equal(reason(tr),BLOCK);
  assert.equal(buttonsOf(tr)[1].getAttribute('aria-disabled'),null,'Keep as separate books stays enabled');assert.equal(buttonsOf(tr)[2].getAttribute('aria-disabled'),null,'Scan again too');
  assert.equal(goesTo(tr),'All 3 go to Audiobooks Sorted\\'+SHARED,'in place of As one book');assert.equal(warned(tr),true);
  assert.equal(faces(tr).at(-1),'Show all 3 books','the last button of the row');assert.equal(showBoth(tr).title,TIP);
  assert.ok(!walk(tr).some(e=>e.textContent==='Same name as another book'),'never the class S presentation');
  assert.ok(!walk(statusCell(tr)).some(e=>/^Also:/.test(e.textContent) && !e.hidden),'no Also line and no second sentence');
  // Positive control for the split (check 15): a class S row on the same list, from the same shared fact.
  assert.equal(statusCell(trOf('cand-s6')).textContent,'Same name as another book');
  sent=posted('/api/candidate/approve').length;await buttonsOf(tr)[0].handlers.click(press);assert.equal(posted('/api/candidate/approve').length,sent,'prevented, not refused');
  // Typing a free title enables the approve press at once; the label returns to the row's own.
  [title]=inputs(tr);title.value='Sprawl Trilogy (все три)';title.handlers.input();await title.handlers.blur();await tick();
  assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);assert.equal(buttonsOf(tr)[0].title,'Join the files shown, in this order, into one book: re-encode the audio once, rename, move to Audiobooks Sorted.');
  assert.equal(reason(tr),'');assert.match(goesTo(tr),/^As one book /);assert.equal(warned(tr),false);assert.equal(showBoth(tr).hidden,true);

  // Every other group keeps its status, sentence and approve face; the three additions come with shared.
  const two=shared(other('03-Мона Лиза овердрайв'));
  const groups=[
    [askRow('g1',base('title_author',{why:'title_series',destination:dest({shared:two})})),'Title unclear','The title starts with what looks like a series name and number.','Approve'],
    [askRow('g2',base('author_unclear',{why:'two_people',candidates:[{name:'William Gibson',source:'artist tag',reader_count:0},{name:'Иван Литвинов',source:'album artist tag',reader_count:4}],destination:dest({shared:two})})),'Author unclear',"Two people are credited. The app can't tell who wrote it.",'Approve'],
    [askRow('g3',base('same_author',{same_author:{new:'W. Gibson',existing:'William Gibson',existing_books:3,why:'near',count:1},destination:dest({shared:two})})),'Same author?','Is "W. Gibson" the same author as "William Gibson"?','Approve'],
    [holdRow('g4','files_unclear','mixed',two),'Files unclear','The files carry different albums or artists. They may be more than one book.','Approve these files'],
    [holdRow('g5','files_unclear','folder_books',two),'Files unclear','This folder may hold more than one book.',null],
    [holdRow('g6','order_unclear','tied',two),'Order unclear','Some files share a track number.','Approve this order'],
    [holdRow('g7','part_of_book','chapter',two),'Part of a bigger book','This file is named as one chapter.','Approve as one book'],
    [askRow('g8',base('other',{reason:'Something odd',files:files(1),file_count:1,cause:'',facts:{},flagged:[],destination:dest({shared:two})})),'Needs you','This book needs your decision.','Approve']];
  paint(groups.map(([row])=>row));
  for(const [row,status,sentence,face] of groups){
    tr=trOf(row.id);assert.equal(statusCell(tr).textContent,status,row.id);assert.equal(hint(tr),sentence,row.id);
    if(face)assert.equal(faces(tr)[0],face,row.id);else assert.equal(faces(tr)[0],run('FOLDER_QUESTION.approve[0]'),'the folder question keeps its own face');
    assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true',row.id);assert.equal(reason(tr),BLOCK,row.id);
    assert.equal(goesTo(tr),'Both go to Audiobooks Sorted\\'+SHARED,row.id);assert.equal(warned(tr),true,row.id);
    assert.equal(faces(tr).at(-1),'Show both books',row.id);
  }
  // Missing files (class Q): the row's own approve press is Convert what's there, its second button; the reason stands
  // under the buttons there too, Scan again stays enabled, and Show both books sits before Delete book's own line.
  const FOLDER='Z:\\Audiobooks\\William Gibson\\Sprawl\\';
  const gone=askRow('m1',base('files_missing',{also:null,missing:{folders:[FOLDER.slice(0,-1)],files:[FOLDER+'03.m4b'],present:2,total:3},delete:{kind:'files_missing',present:2},destination:dest({shared:two})}));
  paint([gone]);tr=trOf('cand-m1');
  assert.equal(statusCell(tr).textContent,'Missing files');assert.equal(hint(tr),'1 of 3 files is missing.');
  assert.deepEqual(faces(tr).slice(0,2),['Scan again',"Convert what's there"]);assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);
  assert.equal(buttonsOf(tr)[1].getAttribute('aria-disabled'),'true');assert.equal(buttonsOf(tr)[1].title,BLOCK);assert.equal(reason(tr),BLOCK);
  const order=buttonsOf(tr).filter(b=>!b.hidden).map(b=>b.textContent),at=order.indexOf('Show both books');
  assert.ok(at>0 && order.indexOf('Delete book')===order.length-1 && at<order.indexOf('Delete book'),'Show both books before Delete book, which keeps its own last line: '+order.join(' | '));
  // A row with shared and a file on disk too: the name on disk wins and the row shows as it does today (4.2a).
  paint([holdRow('q3','part_of_book','set_unclear',more(2),{destination:dest({taken:true,shared:more(2)})})]);tr=trOf('cand-q3');
  assert.match(goesTo(tr),/^Already there /);assert.equal(reason(tr),'That name is already in Audiobooks Sorted. Change the title or author.');assert.equal(showBoth(tr).hidden,true);
  // A row whose name no other book has: nothing of this shows (control for every assertion above).
  paint([holdRow('q4','part_of_book','set_unclear',null)]);tr=trOf('cand-q4');
  assert.match(goesTo(tr),/^As one book /);assert.equal(warned(tr),false);assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);assert.equal(reason(tr),'');assert.equal(showBoth(tr).hidden,true);
  assert.ok(!faces(tr).some(face=>/^Show (both|all)/.test(face)));

  // 4. The clash appears only at the press (the engine's same_name refusal, on a row of any class): Approve answers with
  // the sentence, and the row's Goes to line is read again, so its label, reason and Show both books follow.
  const late=askRow('l1',base('title_author',{why:'title_series'}));paint([late]);tr=trOf('cand-l1');
  assert.match(goesTo(tr),/^Goes to /);assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);
  approveAnswer=()=>({ok:false,status:409,json:async()=>({error:'Another book would get the same name. Change the title, author, series or number. Nothing was changed.',code:'same_name',row:null})});
  previewAnswer=()=>({ok:true,status:200,json:async()=>({preview:{path:SHARED,absolute:ROOT+'\\'+SHARED,taken:false,reason:'',shared:two}})});
  const asked=posted('/api/candidate/approve-preview').length;
  await buttonsOf(tr)[0].handlers.click(press);await tick();await tick();
  assert.equal(statusCell(tr).children[0].textContent,'Approval not saved: Another book would get this name. Change the title, author, series or number, then approve.');
  assert.ok(statusCell(tr).children[0].classes.has('retry-refused'));
  assert.deepEqual(posted('/api/candidate/approve-preview').slice(asked),[{library:'Audiobooks',id:'cand-l1',revision:2}],'nothing typed: the row\'s own line is asked for once');
  assert.equal(goesTo(tr),'Both go to Audiobooks Sorted\\'+SHARED);assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true');assert.equal(showBoth(tr).hidden,false);
  assert.equal(statusCell(tr).textContent,'Title unclear','a row of another class keeps its own status');
  approveAnswer=null;previewAnswer=null;
  assert.equal(run('APPROVE_REFUSALS.same_name'),'Another book would get this name. Change the title, author, series or number, then approve.');

  // 5. Show both books: Status All and a search for the shared title, so the rows sit together.
  paint([sameName('s7',shared(other('03-Мона Лиза овердрайв')))]);tr=trOf('cand-s7');
  inventoryRows=[run('rows[0]')];get('search').value='';run('filters.candidates="output_attention";attentionGroup="name_taken"');
  await showBoth(tr).handlers.click(press);await tick();
  assert.equal(get('search').value,'Sprawl Trilogy');assert.equal(run('filters.candidates'),'all');assert.equal(run('attentionGroup'),'all');
  run('filters.candidates="output_attention";attentionGroup="all"');get('search').value='';inventoryRows=[];

  // 6. The Place line says where the series and number came from, by the engine's origin key (4.3, amended).
  const place=(origin,extra={})=>run('placeText('+JSON.stringify({universe:'',series:'Sprawl Trilogy',number:'2',collection:false,origin,...extra})+')');
  assert.equal(place('tags'),"Series: Sprawl Trilogy · No. 2 · from the file's tags");
  assert.equal(place('folders'),'Series: Sprawl Trilogy · No. 2 · from the folder names');
  assert.equal(place('entered'),'Series: Sprawl Trilogy · No. 2 · entered by you');
  assert.equal(place('unknown'),'Series: Sprawl Trilogy · No. 2','unknown: no suffix');assert.equal(place(undefined),'Series: Sprawl Trilogy · No. 2');
  for(const [provider,name] of [['wikidata','Wikidata'],['fantlab','FantLab'],['goodreads','Goodreads'],['litres','Litres'],['publisher',"the publisher's site"]])
    assert.equal(place('source',{provider}),'Series: Sprawl Trilogy · No. 2 · found on '+name,provider);
  assert.equal(place('source',{provider:'openlibrary'}),'Series: Sprawl Trilogy · No. 2 · found online','a source with no name');assert.equal(place('source'),'Series: Sprawl Trilogy · No. 2 · found online');
  assert.equal(run('placeText({universe:"Warhammer 40,000",series:"Ересь Хоруса",number:"3",origin:"tags"})'),"Universe: Warhammer 40,000 · Series: Ересь Хоруса · No. 3 · from the file's tags");
  assert.equal(run('placeText({universe:"Warhammer 40,000",series:"",number:"",origin:"tags"})'),'Universe: Warhammer 40,000','no series, no origin');
  assert.equal(run('placeText({series:"",number:"",origin:"tags"})'),'');
  // On the row: the status cell's Place line carries it; a question row's series line is not repeated because of it.
  const filed={...askRow('p1',null),ask:undefined,status:'Queued',automatic:{state:'Queued',reasons:[]},review:{title:'Граф Ноль',series:'Sprawl Trilogy',number:'2'},place:{universe:'',series:'Sprawl Trilogy',number:'2',collection:false,origin:'tags'},entered:[],title_from_title_tag:true,
    scope_view:{kind:'volume',basis:'each file carries its own title',album:'Sprawl Trilogy',folders:['Z:\\Audiobooks\\William Gibson']}};
  context.fixture=[filed];run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');
  assert.equal(walk(statusCell(trOf('cand-p1'))).find(e=>String(e.className || '').split(' ').includes('book-place')).textContent,"Series: Sprawl Trilogy · No. 2 · from the file's tags");
  const asking=askRow('p2',base('title_author',{why:'title_series',series:{name:'Sprawl Trilogy',number:'2',basis:'research',origin:'tags'}}),{place:{universe:'',series:'Sprawl Trilogy',number:'2',collection:false,origin:'tags'}});
  paint([asking]);assert.equal(run('seriesLine(rows[0])'),'','the Place line already says it, origin or not');
  // The details panel's line of a volume named from its own tags (4.3): two sentences after "Kept as a separate book".
  const view={kind:'volume',basis:'each file carries its own title',album:'Sprawl Trilogy'};
  context.fixture={view,row:filed};
  assert.equal(run('scopeBasisText(fixture.view,fixture.row)'),"Kept as a separate book: each file carries its own title. Title from this file's own title tag. Series and number from its tags. Album «Sprawl Trilogy». If these files are one book, select them and use Join into one book.");
  assert.equal(run('scopeBasisText(fixture.view,{...fixture.row,title_from_title_tag:false,place:{...fixture.row.place,origin:"source",provider:"fantlab"}})'),'Kept as a separate book: each file carries its own title. Album «Sprawl Trilogy». If these files are one book, select them and use Join into one book.','neither is true: neither is said');
  assert.equal(run('scopeBasisText(fixture.view)'),'Kept as a separate book: each file carries its own title. Album «Sprawl Trilogy». If these files are one book, select them and use Join into one book.','0.30.0 line unchanged without the facts');
  assert.equal(run('scopeBasisText({kind:"album",album:"Sprawl Trilogy"},fixture.row)'),'Grouped by album «Sprawl Trilogy».','only a volume gains them');

  // Overlap (spec section 8): everything new is in normal flow, so it can only wrap or push. No new rule positions an
  // element out of flow, and the three additions reuse existing classes (the taken label, the block line, a row button).
  const css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');
  assert.ok(!/position\s*:\s*(absolute|fixed|sticky)[^}]*\}\s*[^{]*(goes-to|block-why|row-retry|book-place)/.test(css) && !/(goes-to|block-why|row-retry|book-place)[^{}]*\{[^}]*position\s*:\s*(absolute|fixed|sticky)/.test(css),'no out-of-flow rule on the label, the reason line, the row buttons or the Place line');
  assert.ok(/\.row-actions\{display:flex;flex-wrap:wrap/.test(css),'row buttons wrap');assert.ok(/\.row-actions \.row-retry\{min-width:96px;min-height:32px\}/.test(css),'96 x 32 minimum');
  assert.ok(/\.goes-to\.taken \.goes-label\{color:var\(--warning\)\}/.test(css),'the warning style of the label');
  assert.ok(!source.includes("shared.kind") && !source.includes("shared?.kind"),'destination.shared.kind is never the test (G9)');
  console.log('Same-name frontend passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_same_name_frontend.js'),module);m.filename=path.join(__dirname,'test_same_name_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

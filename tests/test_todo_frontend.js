'use strict';
// The one to-do list (Judy, Docs/BooksArranger_AttentionTodo_UX_2026-10-24.md; Sergei's rulings 6a, 6b, 10, 11a, 12, 14):
// the five "Needs your answer" chips and their counts, the shortcut and Jobs line, the row's sentence, fields and Goes to
// line, Approve (as is / typed / Ctrl+Enter, never Enter), Name taken, missing files, Same author?, bulk Approve as is and
// its dialog, Technical details. Runs the real frontend on the Retry test's DOM/transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted';
function askRow(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'Z:\\Audiobooks\\Unsorted\\'+name+'\\01.mp3'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['Title or author missing']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const dest=(p,taken=false)=>({path:p,absolute:ROOT+'\\'+p,taken,reason:''});
const noAuthor=askRow('a',{kind:'title_author',also:null,why:'author_missing',reasons:['Title or author missing'],fields:{title:{proposal:'Шестёрка воронов 1',basis:'number_rule'},author:{proposal:'',basis:''}},candidates:[],destination:dest('Без автора\\Шестёрка воронов 1.m4b')});
const both=askRow('b',{kind:'title_author',also:null,why:'both_missing',reasons:['Title or author missing'],fields:{title:{proposal:'Sbornik_Deti_Primarhov',basis:'folder_name'},author:{proposal:'',basis:''}},candidates:[],destination:dest('Без автора\\Sbornik_Deti_Primarhov.m4b')});
const unclear=askRow('u',{kind:'author_unclear',also:null,why:'two_people',reasons:['Author unclear'],fields:{title:{proposal:'Солдаты смерти',basis:'tag'},author:{proposal:'Джо Шрайбер',basis:'tag'}},
  candidates:[{name:'Джо Шрайбер',source:'artist tag',reader_count:0},{name:'Пухов Сергей',source:'album artist tag',reader_count:9}],destination:dest('Шрайбер Джо\\Солдаты смерти - Шрайбер Джо.m4b')});
const reader=askRow('r',{kind:'author_unclear',also:null,why:'reader',reasons:['Author unclear'],fields:{title:{proposal:'Тайна',basis:'tag'},author:{proposal:'',basis:''}},
  candidates:[{name:'Иван Петров',source:'file name',reader_count:3}],destination:dest('Без автора\\Тайна.m4b')});
const taken=askRow('t',{kind:'name_taken',also:null,why:'',reasons:['An audiobook already exists at this path.'],fields:{title:{proposal:'Хроники Нарнии 2',basis:''},author:{proposal:'Клайв Стейплз Льюис',basis:''}},candidates:[],
  destination:dest('Льюис Клайв Стейплз\\Хроники Нарнии 2 - Льюис Клайв Стейплз.m4b',true)});
const FOLDER='Z:\\Audiobooks\\Сборники\\Новая плоть (2016)\\';
const someGone=askRow('m',{kind:'files_missing',also:'title_author',why:'author_missing',reasons:['Files missing'],fields:{title:{proposal:'Новая плоть',basis:'tag'},author:{proposal:'',basis:''}},candidates:[],
  missing:{folders:[FOLDER.slice(0,-1)],files:[FOLDER+'03 - Засор.m4b'],present:8,total:9},destination:dest('Без автора\\Новая плоть.m4b')});
const allGone=askRow('g',{kind:'files_missing',also:null,why:'',reasons:['Files missing'],fields:{},candidates:[],
  missing:{folders:['Z:\\Audiobooks\\Unsorted\\Бойся Чужого'],files:[1,2,3,4,5].map(n=>'Z:\\Audiobooks\\Unsorted\\Бойся Чужого\\Iron Inferno '+n+'.mp3'),present:0,total:5}});
const same=askRow('s',{kind:'same_author',also:null,why:'near',reasons:['Same author?'],fields:{title:{proposal:'Пастушья корона 20',basis:'tag'},author:{proposal:'Terry Pratchet',basis:'tag'}},candidates:[],
  same_author:{new:'Terry Pratchet',existing:'Terry Pratchett',existing_books:41,why:'near',count:3},destination:dest('Pratchet Terry\\Пастушья корона 20 - Pratchet Terry.m4b')});
const COUNTS={files_missing:2,title_author:2,author_unclear:2,same_author:1,name_taken:1,retry:1,repair:0,reacquire:0,checking:0,changed:0,audiobook:0,other:0,unsupported:0};
backend={...backend,audiobook_output_root:ROOT,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:COUNTS}};
let approveAnswer=null,previewAnswer=null,scanAnswer=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/candidate/approve'){calls.push({route,options});if(approveAnswer)return approveAnswer(data,options);return {ok:true,status:200,json:async()=>({approved:true,job_id:'job-'+data.id,row:{id:data.id}})};}
  if(route==='/api/candidate/approve-preview'){calls.push({route,options});if(previewAnswer)return previewAnswer(data);return {ok:true,status:200,json:async()=>({preview:{path:(data.author || 'Без автора')+'\\'+(data.title || 'x')+'.m4b',absolute:'',taken:false,title:data.title,author:data.author}})};}
  if(route==='/api/candidate/scan-again'){calls.push({route,options});return scanAnswer?scanAnswer(data):{ok:true,status:200,json:async()=>({found:false})};}
  if(route==='/api/candidate/dismiss'){calls.push({route,options});return {ok:true,status:200,json:async()=>({removed:true})};}
  return baseFetch(route,options);
};
const posted=route=>calls.filter(call=>call.route===route).map(call=>JSON.parse(call.options.body));
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>tr.children[5].children[0].children;
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const inputs=tr=>walk(statusCell(tr)).filter(e=>e.type==='text');
const radios=tr=>walk(statusCell(tr)).filter(e=>e.type==='radio');
const goesTo=tr=>{const line=walk(statusCell(tr)).find(e=>e.className==='goes-to');return line.hidden?'':line.children.map(c=>c.textContent).join(' ');};
const key=(k,extra={})=>({key:k,ctrlKey:false,stopPropagation(){},preventDefault(){},...extra});
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  // 1. Chips: the "Needs your answer" set first, All = the sum = the shortcut = the Jobs line; zero chips hidden.
  run('controls();renderJobs()');
  assert.equal(get('group-files_missing').textContent,'Missing files · 2');assert.equal(get('group-title_author').textContent,'Title or author · 2');
  assert.equal(get('group-same_author').textContent,'Same author? · 1');assert.equal(get('group-name_taken').hidden,false);assert.equal(get('group-all').textContent,'All · 9');
  assert.equal(get('attention-set-needs').hidden,false);
  assert.equal(get('attention-shortcut').textContent,'Needs attention · 9');assert.equal(get('attention-shortcut').hidden,false);
  assert.match(get('jobs-status').textContent,/ · 9 need attention$/);
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,attention_counts:{...state.audiobook_jobs.attention_counts,files_missing:0,title_author:0,author_unclear:0,same_author:0,name_taken:0}}};controls()');
  assert.equal(get('group-title_author').hidden,true);assert.equal(get('attention-set-needs').hidden,true,'a set with no chips hides its label');
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,attention_counts:{retry:0}}};controls()');assert.equal(get('attention-shortcut').hidden,true,'hidden at zero');
  run('state='+JSON.stringify(backend)+';controls()');
  // Shortcut: Book candidates, Output needs attention, All, focus on All.
  run('filters.candidates="all";attentionGroup="retry";viewControls()');get('search').value='x';
  await get('attention-shortcut').handlers.click();
  assert.equal(run('filters.candidates'),'output_attention');assert.equal(run('attentionGroup'),'all');assert.equal(get('search').value,'');assert.equal(document.activeElement,get('group-all'));
  // Empty list: one plain line.
  paint([]);assert.equal(get('empty').textContent,'Nothing needs your attention.');assert.equal(get('page').textContent,'Nothing needs your attention.');

  // 2. Title or author: sentence, fields prefilled with the proposal, the basis line, Goes to under Без автора.
  paint([noAuthor,both,unclear,reader,taken,someGone,allGone,same]);
  let tr=trOf('cand-a');
  assert.equal(statusCell(tr).textContent,'Author missing');assert.equal(statusCell(tr).children[0].textContent,'No author in the tags, file name or folder name.');
  let [title,author]=inputs(tr);assert.equal(title.value,'Шестёрка воронов 1');assert.equal(author.value,'');assert.equal(author.placeholder,'Empty files it under Без автора.');
  assert.equal(title.getAttribute('aria-label'),'Title: Title a');assert.equal(author.title,'The author this book is filed under. Leave empty to use Без автора.');
  assert.ok(walk(statusCell(tr)).some(e=>e.textContent==='Set name + part number.'),'basis line under a guessed title');
  assert.equal(goesTo(tr),'Goes to Audiobooks Sorted\\Без автора\\Шестёрка воронов 1.m4b');
  assert.equal(buttonsOf(tr)[0].textContent,'Approve');assert.equal(buttonsOf(tr)[0].getAttribute('aria-label'),'Approve: Title a');assert.ok(buttonsOf(tr)[0].className.includes('quiet'));
  assert.equal(inputs(trOf('cand-b')).length,2);assert.ok(walk(statusCell(trOf('cand-b'))).some(e=>e.textContent==='Title from the folder name.'));
  assert.equal(statusCell(trOf('cand-b')).textContent,'Title and author missing');
  // A space typed in a field never reaches the row; Enter refreshes Goes to and never approves.
  let stopped=false;title.handlers.keydown(key(' ',{stopPropagation(){stopped=true;}}));assert.ok(stopped,'the row never sees keys typed in a field');
  author.value='Лей Бардуго';author.handlers.input();
  await title.handlers.keydown(key('Enter'));await tick();
  assert.equal(posted('/api/candidate/approve').length,0,'Enter alone never approves');
  assert.deepEqual(posted('/api/candidate/approve-preview').at(-1),{library:'Audiobooks',id:'cand-a',revision:2,author:'Лей Бардуго'});
  assert.equal(goesTo(tr),'Goes to Audiobooks Sorted\\Лей Бардуго\\x.m4b','the line shows what the planner returns');
  // A stale preview reply never replaces a newer one.
  let release;previewAnswer=()=>new Promise(resolve=>{release=resolve;});author.value='Old';author.handlers.input();const slow=author.handlers.blur();
  previewAnswer=null;author.value='Лей Бардуго';author.handlers.input();await author.handlers.blur();
  release({ok:true,status:200,json:async()=>({preview:{path:'Old\\stale.m4b',taken:false}})});await slow;await tick();
  assert.equal(goesTo(tr),'Goes to Audiobooks Sorted\\Лей Бардуго\\x.m4b','a stale reply is ignored');
  // An empty title: Approve is inert with its tooltip; the last good path stays.
  title.value='';title.handlers.input();assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true');assert.equal(buttonsOf(tr)[0].title,'Type a title first.');
  assert.equal(goesTo(tr),'Goes to Audiobooks Sorted\\Лей Бардуго\\x.m4b');
  title.value='Шестёрка воронов 1';title.handlers.input();assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);
  assert.equal(buttonsOf(tr)[0].title,'Approve with the values shown: convert if needed, rename, move to Audiobooks Sorted. Ctrl+Enter in a field does the same.');
  // Drafts survive a poll that rebuilds the list (and a chip change): the typed author is still there.
  paint([noAuthor,both,unclear,reader,taken,someGone,allGone,same]);tr=trOf('cand-a');[title,author]=inputs(tr);assert.equal(author.value,'Лей Бардуго');
  // Ctrl+Enter approves with exactly what is shown: the typed author, not the untouched title.
  buttonsOf(tr)[0].focus();document.activeElement=author;
  await author.handlers.keydown(key('Enter',{ctrlKey:true}));await tick();
  assert.deepEqual(posted('/api/candidate/approve').at(-1),{library:'Audiobooks',id:'cand-a',revision:2,author:'Лей Бардуго',path:'Лей Бардуго\\x.m4b',queue:true,label:'Title a'},'the Goes to line shown (m1)');
  // The cell's own text changes in place (statusInPlace, a text node the doubles don't model): read it as a rebuild would.
  assert.equal(run('candidateStatus(rows.find(row=>row.id==="cand-a"))'),'Queued');assert.equal(statusCell(tr).children[0].textContent,'Approved. Converts if needed, then renames and moves it to Audiobooks Sorted.');
  assert.equal(buttonsOf(tr)[0].textContent,'Queued');assert.equal(buttonsOf(tr)[0].disabled,true);
  assert.equal(walk(statusCell(tr)).find(e=>e.className==='ask-fields').hidden,true,'no fields once approved');
  assert.equal(get('retry-all-status').textContent,'Approved 1 book. Track it under Queued / creating.');
  assert.equal(document.activeElement,inputs(trOf('cand-b'))[0],"focus moves to the next row's first field");
  // Approve as is: nothing typed sends no values.
  await buttonsOf(trOf('cand-b'))[0].handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/candidate/approve').at(-1),{library:'Audiobooks',id:'cand-b',revision:2,path:'Без автора\\Sbornik_Deti_Primarhov.m4b',queue:true,label:'Title b'});
  // The approved rows leave at the next refresh, even with focus elsewhere in the list.
  document.activeElement=buttonsOf(trOf('cand-u'))[0];context.fixture=[unclear,reader,taken,someGone,allGone,same];run('rows=fixture.map(row=>({...row}));renderRows(false)');
  assert.equal(trOf('cand-a'),undefined);assert.equal(trOf('cand-b'),undefined);assert.ok(trOf('cand-u'));

  // 3. Author unclear: a radio group, preselected best guess, reader evidence shown; choosing another sends it.
  tr=trOf('cand-u');let options=radios(tr);
  assert.equal(statusCell(tr).children[0].textContent,"Two people are credited. The app can't tell who wrote it.");
  assert.deepEqual(options.map(r=>r.value),['c0','c1','other']);assert.deepEqual(options.map(r=>!!r.checked),[true,false,false]);
  assert.ok(walk(statusCell(tr)).some(e=>e.textContent==='album artist tag · reader on 9 other books'));
  assert.equal(options[0].title,'Use Джо Шрайбер as the author.');
  // Ruling 14: when the only name may be the reader, nothing is preselected and Goes to shows Без автора.
  assert.deepEqual(radios(trOf('cand-r')).map(r=>!!r.checked),[false,false]);assert.equal(goesTo(trOf('cand-r')),'Goes to Audiobooks Sorted\\Без автора\\Тайна.m4b');
  assert.equal(statusCell(trOf('cand-r')).children[0].textContent,"The only name credited may be the reader. The app can't tell who wrote it.");
  options[1].checked=true;await options[1].handlers.change();await tick();
  assert.deepEqual(posted('/api/candidate/approve-preview').at(-1),{library:'Audiobooks',id:'cand-u',revision:2,author:'Пухов Сергей'});
  // Other: its input selects Other; the typed name is used.
  const other=inputs(tr).find(e=>e.className==='ask-other');other.value='Джо Шрайбер-мл.';other.handlers.input();assert.equal(radios(tr)[2].checked,true);
  assert.deepEqual(JSON.parse(run('JSON.stringify(askValues(rows.find(row=>row.id==="cand-u")))')),{author:'Джо Шрайбер-мл.'});

  // 4. Name taken: Approve inert, "Already there"; a free name enables it.
  tr=trOf('cand-t');assert.equal(statusCell(tr).textContent,'Name taken');
  assert.equal(goesTo(tr),'Already there Audiobooks Sorted\\Льюис Клайв Стейплз\\Хроники Нарнии 2 - Льюис Клайв Стейплз.m4b');
  assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),'true');assert.equal(buttonsOf(tr)[0].title,'That name is taken. Change the title or author.');
  const sent=posted('/api/candidate/approve').length;await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});assert.equal(posted('/api/candidate/approve').length,sent,'a taken name is prevented, not refused');
  [title]=inputs(tr);title.value='Хроники Нарнии 2 (другое издание)';title.handlers.input();await title.handlers.blur();await tick();
  assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);assert.match(goesTo(tr),/^Goes to /);
  // A race refuses it anyway: the row says so and shows the gate again, his title kept.
  approveAnswer=()=>({ok:false,status:409,json:async()=>({error:'An audiobook already exists at this path.',code:'name_taken',row:null})});
  previewAnswer=data=>({ok:true,status:200,json:async()=>({preview:{path:'Льюис\\'+data.title+'.m4b',absolute:'',taken:true}})});
  await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();
  // «Спящие красавицы» (2026-10-26): the gate's own reason and next step, never the bare refusal.
  assert.equal(statusCell(tr).children[0].textContent,'An audiobook with this name is already in Audiobooks Sorted. Change the title or author, then approve.');assert.ok(statusCell(tr).children[0].classes.has('retry-refused'));
  assert.match(goesTo(tr),/^Already there /);assert.equal(inputs(tr)[0].value,'Хроники Нарнии 2 (другое издание)');
  approveAnswer=()=>({ok:false,status:409,json:async()=>({error:'Candidate changed; reload evidence before reviewing',code:'changed',row:null})});previewAnswer=null;
  title.value='Хроники Нарнии 2 (третье)';title.handlers.input();await title.handlers.blur();await tick();
  await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();assert.equal(statusCell(tr).children[0].textContent,'This book changed. Review its details and try again.');
  approveAnswer=null;

  // 5. Missing files: what is missing and where; Scan again, Convert what's there, Remove from list.
  tr=trOf('cand-m');assert.equal(statusCell(tr).textContent,'Missing files');assert.equal(statusCell(tr).children[0].textContent,'1 of 9 files is missing.');
  assert.equal(walk(statusCell(tr)).find(e=>e.className==='field-help attention-also').textContent,'Also: no author in the tags, file name or folder name.');
  const lines=walk(statusCell(tr)).filter(e=>e.className==='path').map(e=>e.textContent);assert.deepEqual(lines.slice(0,2),['In '+FOLDER,'03 - Засор.m4b']);
  assert.deepEqual([...buttonsOf(tr)].slice(0,2).map(b=>b.textContent),['Scan again',"Convert what's there"]);
  assert.equal(buttonsOf(tr)[0].title,"Look for the missing files in this book's folders. Nothing is changed or deleted.");
  await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();
  {const hint=statusCell(tr).children[0];assert.match(hint.textContent+hint.children.map(span=>span.textContent).join(''),/^1 of 9 files is missing\. Checked \d\d:\d\d\. Not found\.$/);}
  await buttonsOf(tr)[1].handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/candidate/approve').at(-1),{library:'Audiobooks',id:'cand-m',revision:2,without_missing:true,path:'Без автора\\Новая плоть.m4b',queue:true,label:'Title m'});
  assert.equal(statusCell(tr).children[0].textContent,'Approved without the missing files. Converts, renames and moves it to Audiobooks Sorted.');
  assert.equal(get('retry-all-status').textContent,'Approved 1 book without its missing files. Track it under Queued / creating.');
  tr=trOf('cand-g');assert.equal(statusCell(tr).textContent,'All files missing');assert.equal(statusCell(tr).children[0].textContent,'All 5 files are missing.');
  assert.equal(goesTo(tr),'','no destination for a book with nothing left');
  assert.ok(walk(statusCell(tr)).some(e=>e.textContent==='+ 2 more, listed in the details panel.'),'up to 3 names in the row');
  assert.deepEqual([...buttonsOf(tr)].slice(0,2).map(b=>b.textContent),['Scan again','Remove from list']);
  // The engine's own sentence (2026-10-26), never the bare "Scan did not finish".
  scanAnswer=()=>({ok:false,status:409,json:async()=>({error:"The book's folder can't be read",code:'refused'})});await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();
  assert.equal(statusCell(tr).children[0].textContent,"The book's folder can't be read. Nothing was changed.");scanAnswer=null;
  await buttonsOf(tr)[1].handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/candidate/dismiss').at(-1),{library:'Audiobooks',id:'cand-g',revision:2,queue:true,title:'Title g'});
  assert.equal(get('retry-all-status').textContent,'Removed 1 book from the list. No files were touched.');

  // 6. Same author?: nothing preselected; Approve with no choice remembers nothing; a choice is sent and announced.
  tr=trOf('cand-s');assert.equal(statusCell(tr).children[0].textContent,'Is "Terry Pratchet" the same author as "Terry Pratchett"?');
  assert.ok(walk(statusCell(tr)).some(e=>e.textContent==='Spelled almost like an author you have (41 books).'));
  assert.ok(walk(statusCell(tr)).some(e=>e.textContent==='Applies to 3 books.'));
  assert.deepEqual(radios(tr).map(r=>!!r.checked),[false,false,false]);
  assert.deepEqual(walk(statusCell(tr)).filter(e=>e.parentElement?.className==='ask-radio' && e.tagName!=='input' && e.type!=='radio').map(e=>e.textContent).slice(0,2),['Same author: use "Terry Pratchett"','Different author: keep "Terry Pratchet"']);
  assert.deepEqual(JSON.parse(run('JSON.stringify(askValues(rows.find(row=>row.id==="cand-s")))')),{},'no choice: as written, nothing remembered');
  radios(tr)[0].checked=true;await radios(tr)[0].handlers.change();await tick();
  assert.deepEqual(posted('/api/candidate/approve-preview').at(-1),{library:'Audiobooks',id:'cand-s',revision:2,author:'Terry Pratchett'});
  await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/candidate/approve').at(-1),{library:'Audiobooks',id:'cand-s',revision:2,choice:'same',path:'Terry Pratchett\\x.m4b',queue:true,label:'Title s'});
  assert.equal(get('retry-all-status').textContent,'Remembered. 3 books continue.');

  // 7. Bulk Approve as is: only in the two chips, selected rows only, never typed rows, inert rows or a reader author.
  run('attentionGroup="all";selectedBooks.clear();controls()');assert.equal(get('approve-selected').hidden,true,'not in All');
  run('attentionGroup="name_taken";controls()');assert.equal(get('approve-selected').hidden,true);
  run('attentionGroup="author_unclear";controls()');assert.equal(get('approve-selected').hidden,false);assert.equal(get('retry-selected').hidden,true,'Retry selected hides here');
  const u2=askRow('u2',{...unclear.ask}),u3=askRow('u3',{...unclear.ask,destination:dest('Шрайбер Джо\\Другая.m4b')});
  paint([unclear,reader,u2,u3]);
  run('selectedBooks.set("cand-u",2);selectedBooks.set("cand-r",2);selectedBooks.set("cand-u2",2);selectedBooks.set("cand-u3",2);batchCounts()');
  assert.equal(get('approve-selected').textContent,'Approve as is (2)','the typed row and the reader row are left out');
  assert.equal(get('batch-count').textContent,'4 selected · 2 can be approved as is · 2 left out');
  assert.equal(get('batch-help').textContent,'Approve as is uses the names shown on each row. Books that need a different action are left out.');
  get('approve-selected').handlers.click();
  assert.equal(get('approve-dialog-title').textContent,'Approve 2 books as is?');assert.equal(document.activeElement,get('approve-cancel'),'Cancel has focus');
  assert.deepEqual(get('approve-dialog-list').children.map(p=>p.textContent),['Audiobooks Sorted\\Шрайбер Джо\\Солдаты смерти - Шрайбер Джо.m4b','Audiobooks Sorted\\Шрайбер Джо\\Другая.m4b']);
  assert.equal(get('approve-dialog-left').textContent,'2 selected books are left out. They need a different action.');assert.equal(get('approve-dialog-left').hidden,false);
  get('approve-cancel').handlers.click();assert.equal(document.activeElement,get('approve-selected'));
  get('approve-selected').handlers.click();
  let first=true;approveAnswer=data=>{if(data.id==='cand-u3')return {ok:false,status:409,json:async()=>({error:'Split book parts are different recordings (audio profiles differ)',code:'profiles'})};return {ok:true,status:200,json:async()=>({approved:true,job_id:'j',row:{}})};};
  const before=posted('/api/candidate/approve').length;const runs=[get('approve-confirm').handlers.click(),get('approve-confirm').handlers.click()];await Promise.all(runs);await tick();
  const bulk=posted('/api/candidate/approve').slice(before);
  assert.deepEqual(bulk,[{library:'Audiobooks',id:'cand-u2',revision:2,path:'Шрайбер Джо\\Солдаты смерти - Шрайбер Джо.m4b',queue:true,label:'Title u2'},{library:'Audiobooks',id:'cand-u3',revision:2,path:'Шрайбер Джо\\Другая.m4b',queue:true,label:'Title u3'}],'once each, as is, despite a double click; each with the path the dialog listed');
  assert.equal(get('retry-all-status').textContent,'Approved 1 of 2. 1 stays listed with its reason.');
  assert.equal(statusCell(trOf('cand-u3')).children[0].textContent,'The files are different recordings (their audio differs). Choose the files that belong in the details panel, then approve.');
  assert.equal(document.activeElement,get('group-author_unclear'),'focus returns to the active chip');
  approveAnswer=null;

  // Futaba's 0.22.0 QA, M-2: a missing part. Still absent: "Checked. Not found."; restored beside the book: the server scans
  // its folder's source and answers changed (never found), so the row says what happened and leaves.
  const partRow=askRow('p',{kind:'files_missing',also:null,why:'',reasons:['Parts of this book are missing'],fields:{},candidates:[],
    missing:{folders:['Z:\\Audiobooks\\Unsorted\\Strangers'],files:['Part 2 of 3'],present:2,total:3},destination:dest('Кунц Дин\\Незнакомцы - Кунц Дин.m4b')});
  paint([partRow]);tr=trOf('cand-p');
  scanAnswer=()=>({ok:true,status:200,json:async()=>({found:false,changed:false,scan_started:false,scan_later:false})});
  await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();
  {const hint=statusCell(tr).children[0];assert.match(hint.textContent+hint.children.map(span=>span.textContent).join(''),/Checked \d\d:\d\d\. Not found\.$/);}
  scanAnswer=()=>({ok:true,status:200,json:async()=>({found:false,changed:true,scan_started:true,scan_later:false})});
  await buttonsOf(tr)[0].handlers.click({stopPropagation(){}});await tick();
  assert.equal(statusCell(tr).children[0].textContent,'Changes found. The book is checked again.');assert.equal(get('retry-all-status').textContent,'Changes found. The book is checked again.');
  scanAnswer=null;

  // 8. Technical details: collapsed, the whole message, Copy. The cell tooltip is the row's plain sentence, never the raw reason
  // (Futaba's 0.22.0 QA, m-6: the spec's check 3 over its section 4.6).
  const long=askRow('l',{...noAuthor.ask,reasons:['x'.repeat(300)]});paint([long]);tr=trOf('cand-l');
  assert.equal(statusCell(tr).title,'No author in the tags, file name or folder name.');assert.ok(!statusCell(tr).title.includes('xxxxxxxxxx'));
  run('select(rows[0],true)');assert.equal(get('technical-details').hidden,false);assert.equal(get('technical-details').open,false);
  assert.equal(get('automatic-technical').textContent,'Technical detail: '+'x'.repeat(300));
  let copied='';context.navigator={clipboard:{writeText:async text=>{copied=text;}}};await get('copy-technical').handlers.click();
  assert.equal(copied,'Technical detail: '+'x'.repeat(300));assert.equal(get('copy-technical-status').textContent,'Copied.');
  assert.deepEqual(get('names-found-list').children.map(li=>li.textContent),['Title: Шестёрка воронов 1 - set name + part number']);
  get('technical-details').open=true;run('select('+JSON.stringify({...both,kind:'candidate'})+',true)');assert.equal(get('technical-details').open,false,'closed again on every selection');
  assert.equal(get('copy-technical-status').textContent,'','Copied. stays only until the selection changes');
  // Futaba's 0.22.0 QA, m-4: the opened Accepted evidence shows no names or rule numbers; the stored text stays recorded.
  {
    const basis='Approved by you on 2026-10-25 (Sergei 2026-10-24, ruling 6b): "Мор" by "Pratchett Terry"';
    const note='author tag; Sergei\'s rule (ruling 12) for "Терри Пратчетт"; a reader named in Sergei ruling 1 (2026-10-13); Set name + part number (rulings 13 and 15); Sergei: not an author';
    const stored={...noAuthor,kind:'candidate',review_context:{metadata_actor:'user',metadata_evidence:[{field:'title',reviewer_identity:'Sergei (Approve)',basis,note}],manual_note:'(Sergei 2026-10-24, ruling 6a)'}};
    run('select('+JSON.stringify(stored)+',true)');
    for(const id of ['automatic-accepted-evidence']){  // ruling 36: the metadata panel's evidence display is gone
      const text=get(id).textContent;assert.ok(text.includes('Approved by you on 2026-10-25'),id+': positive control, the evidence is shown');
      assert.doesNotMatch(text,/Sergei|ruling/i,id);
    }
  }
  // Futaba's 0.22.0 QA, m-2: raw OS text ("[WinError 2] ...") is never in the All status cell or the panel's reasons: one
  // plain sentence is, and the raw text is only in the collapsed Technical details.
  {
    const raw='Cannot protect exact file: [WinError 2] The system cannot find the file specified.';
    const gone={...askRow('w',null),automatic:{state:'Needs attention',reasons:[raw]}};
    paint([gone]);const cell=statusCell(trOf('cand-w'));
    assert.equal(cell.textContent,"Needs attention — A source file is missing or can't be opened.");
    run('select(rows[0],true)');
    assert.deepEqual(get('automatic-reasons').children.map(li=>li.textContent),["A source file is missing or can't be opened."]);
    assert.equal(get('technical-details').hidden,false);assert.equal(get('technical-details').open,false);
    assert.match(get('automatic-technical').textContent,/\[WinError 2\] The system cannot find the file specified/,'the raw text, in Technical details only');
  }
  // Futaba's 0.22.0 QA, M-4: the server answers Approve on a 77-file book after 24.5 s; the page gave up at 15 s with
  // "Connection interrupted" and a second press got a 409. Long timers run here at 1/1000 speed and the request aborts for
  // real: the old 15 s limit is 15 ms, the server answers at 25 ms.
  context.AbortController=AbortController;context.clearTimeout=id=>clearTimeout(id);context.setTimeout=(fn,ms)=>ms>=10000?setTimeout(fn,ms/1000):0;
  approveAnswer=(data,options)=>new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>resolve({ok:true,status:200,json:async()=>({approved:true,job_id:'job-'+data.id,row:{id:data.id}})}),25);
    options?.signal?.addEventListener?.('abort',()=>{clearTimeout(timer);reject(Object.assign(new Error('This operation was aborted'),{name:'AbortError'}));});});
  paint([askRow('slow',{...noAuthor.ask})]);
  const heavy=buttonsOf(trOf('cand-slow'))[0],heavySent=posted('/api/candidate/approve').length;
  heavy.handlers.click({stopPropagation(){}});await new Promise(resolve=>setTimeout(resolve,5));
  assert.equal(heavy.textContent,'Approving...');assert.equal(heavy.getAttribute('aria-disabled'),'true','pending until the answer: no second press');
  heavy.handlers.click({stopPropagation(){}});
  await new Promise(resolve=>setTimeout(resolve,120));
  assert.equal(posted('/api/candidate/approve').length-heavySent,1,'one request');
  assert.equal(run('askDone.get("cand-slow")'),'approve','the answer came and was taken');
  assert.equal(run('askResults.get("cand-slow")'),undefined,'no "Connection interrupted"');
  context.setTimeout=()=>0;context.clearTimeout=()=>{};delete context.AbortController;approveAnswer=null;
  // Futaba's 0.22.0 QA, m-13: the included-source table marks a missing file "Not found" (Judy's to-do spec, section 7).
  run("trackDraft={id:'cand-m13',revision:2,order:['k1','k2','k3'],included:['k1','k2','k3']};renderMembers({id:'cand-m13',members:[{member_key:'k1',path:'B/01.mp3',duration:1},{member_key:'k2',path:'B/02.mp3',duration:1},{member_key:'k3',path:'B/03.mp3',duration:0.5,missing:true}]},true)");
  assert.deepEqual(get('candidate-members').children.map(tr=>tr.children[2].textContent.split('\n').includes('Not found')),[false,false,true]);
  context.setTimeout=()=>0;
  console.log('PASS to-do list: chips and counts, shortcut, row fields and Goes to, Approve as is / typed / Ctrl+Enter, author choices (ruling 14), Name taken, missing files, Same author?, bulk Approve as is, Technical details');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_todo_frontend.js'),module);m.filename=path.join(__dirname,'test_todo_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

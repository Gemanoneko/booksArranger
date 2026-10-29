'use strict';
// Judy's 0.23.1 review rows (Docs/BooksArranger_0.23.1_UX_2026-10-29.md, Part A, slices A-D; Futaba's checks 1-12 that run
// headless): one "Open source folder" on every book row with the live list shape, its folder list, the "In" source line, the
// Book and Author / reader columns of a question row, the Numbers and membership lines, the gap face, Includes and the raised
// folder question. Real frontend on the Retry test's DOM/transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted';
// The live list row: no source_directory_count of 1 unless the engine sends it (Judy check 4).
function bookRow(name,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:['Artist '+name],members:[{path:'Z:\\Audiobooks\\'+name+'\\01.mp3'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['x']},creation:{status:'Held',can_create:false,reasons:[]},...extra};
}
const dest=p=>({path:p,absolute:ROOT+'\\'+p,taken:false,reason:''});
const named={title:{proposal:'Колесо Времени',basis:'tag'},author:{proposal:'Джордан Роберт',basis:'tag'}};
function asked(name,ask,extra={}){return bookRow(name,{ask:{also:null,why:'',reasons:['x'],fields:named,candidates:[],destination:dest('Джордан Роберт\\Колесо Времени - Джордан Роберт.m4b'),...ask},...extra});}
const files=(n,folder='Z:\\Audiobooks\\Колесо')=>Array.from({length:Math.min(n,6)},(_,i)=>({name:String(i+1).padStart(2,'0')+'.mp3',folder,path:folder+'\\'+String(i+1).padStart(2,'0')+'.mp3',track:'',disc:'',flag:false}));
function hold(name,kind,cause,facts={},ask={},extra={}){return asked(name,{kind,cause,facts,files:files(12),file_count:12,flagged:[],saved_tracks:false,reason:'',...ask},extra);}
const folders=n=>Array.from({length:n},(_,i)=>({id:'dir-'+i,path:'Z:\\Audiobooks\\Книга\\CD '+(i+1),files:10+i}));
backend={...backend,audiobook_output_root:ROOT,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:{},todo_still_checking:0}};
let openAnswer=null;const opened=[];const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/open-folder'){calls.push({route,options});opened.push(data);return openAnswer?openAnswer(data):{ok:true,status:200,json:async()=>({opened:true})};}
  if(route==='/api/candidate/approve-preview'){calls.push({route,options});return {ok:true,status:200,json:async()=>({preview:{path:'x.m4b',taken:false}})};}
  return baseFetch(route,options);
};
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const shown=element=>{for(let e=element;e;e=e.parentElement)if(e.hidden)return false;return true;};
const texts=element=>walk(element).filter(shown).map(e=>e.textContent).filter(Boolean);
const lineText=e=>e.children.length?e.children.map(c=>c.textContent).join(' '):e.textContent;
const folderButtons=tr=>buttonsOf(tr).filter(b=>/^(Open source folder|Open book folder|Source folders|Open folder)$/.test(b.textContent));
const sourceLine=tr=>walk(statusCell(tr)).find(e=>e.className==='goes-to source-line');
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  // Check 1: one "Open source folder" on every row kind, the live row shape; never "Source folders" or "Open folder".
  const kinds=[hold('o','order_unclear','no_tracks',{missing:12,total:12}),hold('f','files_unclear','track_total',{tags_say:38,here:34},{reasons:['Source membership uncertain']}),
    hold('p','part_of_book','numbered_part'),asked('m',{kind:'files_missing',missing:{folders:['Z:\\Audiobooks\\m'],files:['Z:\\Audiobooks\\m\\02.mp3'],present:1,total:2}}),
    asked('s',{kind:'same_author',same_author:{new:'A',existing:'B',existing_books:2,count:1}}),asked('n',{kind:'name_taken'}),asked('t',{kind:'title_author',why:'title_missing',fields:{title:{proposal:'',basis:''},author:{proposal:'X',basis:'tag'}}}),
    bookRow('stopped',{status:'Output needs attention',creation:{status:'Output needs attention',can_create:false,reasons:[],job:{job_id:'job-s',state:'Output needs attention',stage:'queued',reason:'x',retry:{allowed:true,reason:''}}}})];
  paint(kinds);
  assert.equal(get('inventory-head').children[0].children.map(th=>th.textContent).join('|'),'Select|Book|Author / reader|Audio files|Review status|Actions');
  for(const row of kinds){const tr=trOf(row.id),faces=folderButtons(tr).map(b=>b.textContent);assert.deepEqual(faces,['Open source folder'],row.id);
    assert.equal(folderButtons(tr)[0].getAttribute('aria-label'),'Open source folder: Title '+row.id.slice(5));assert.equal(folderButtons(tr)[0].getAttribute('aria-describedby'),'folder-help');
    assert.ok(buttonsOf(tr).filter(b=>b.type==='button' && !b.hidden).length<=6,'six-button budget: '+row.id);}
  assert.equal(run('lookingOnly(rows[0]&&{getAttribute:()=>"Open source folder: x"})'),true,'inert like View metadata while loading (check 5)');
  assert.equal(run('lookingOnly({getAttribute:()=>"Open book folder: x"})'),true);
  // Check 2: one folder opens at once: its id, no scroll, no panel, no selection change, focus stays, an empty message.
  paint([bookRow('one',{source_directories:[{id:'dir-one',path:'Z:\\Audiobooks\\one',files:1}],source_directory_count:1})]);
  let tr=trOf('cand-one');const one=folderButtons(tr)[0];one.focus();const before=run('selectedPath');
  assert.equal(one.title,"Open this book's source folder in File Explorer.");assert.equal(one.getAttribute('aria-expanded'),null);
  await one.handlers.click({stopPropagation(){}});
  assert.deepEqual(opened.at(-1),{library:'Audiobooks',view:'candidates',id:'cand-one',folder_kind:'source',directory_id:'dir-one'});
  assert.equal(run('selectedPath'),before,'the press does not select the row');assert.equal(document.activeElement,one,'focus stays on the button');
  assert.equal(calls.some(c=>c.route==='/api/inspect'),false,'no details panel opens');
  assert.equal(buttonsOf(tr)[buttonsOf(tr).indexOf(one)+1].textContent,'','no message on success');
  assert.equal(lineText(sourceLine(tr)),'In Z:\\Audiobooks\\one');assert.equal(sourceLine(tr).title,'Z:\\Audiobooks\\one');
  openAnswer=()=>({ok:false,status:409,json:async()=>({error:'Folder unavailable. Connect the library drive and try again.'})});
  await one.handlers.click({stopPropagation(){}});
  assert.equal(buttonsOf(tr)[buttonsOf(tr).indexOf(one)+1].textContent,'Folder unavailable. Connect the library drive and try again.');assert.equal(one.getAttribute('aria-disabled'),null,'stays enabled');
  openAnswer=null;
  // Without the engine's list (an older engine) one folder still opens, without an id (3.2).
  paint([bookRow('plain')]);tr=trOf('cand-plain');await folderButtons(tr)[0].handlers.click({stopPropagation(){}});
  assert.deepEqual(opened.at(-1),{library:'Audiobooks',view:'candidates',id:'cand-plain',folder_kind:'source'});
  // Check 3: several folders toggle an in-flow list under "In 3 folders"; focus moves into it; each opens its own id; Esc closes.
  paint([bookRow('many',{source_directories:folders(3),source_directory_count:3,members:[{path:'Z:\\Audiobooks\\Книга\\CD 1\\01.mp3'},{path:'Z:\\Audiobooks\\Книга\\CD 2\\01.mp3'},{path:'Z:\\Audiobooks\\Книга\\CD 3\\01.mp3'}]})]);
  tr=trOf('cand-many');let button=folderButtons(tr)[0];
  assert.equal(lineText(sourceLine(tr)),'In 3 folders');assert.equal(button.getAttribute('aria-expanded'),'false');assert.equal(button.getAttribute('aria-controls'),'source-list-cand-many');
  assert.equal(button.title,"This book's files are in 3 folders. Show them and open any one.");
  let list=walk(statusCell(tr)).find(e=>e.className==='folder-list-box');assert.equal(list.hidden,true);assert.equal(list.getAttribute('role'),'group');assert.equal(list.getAttribute('aria-label'),'Source folders');
  await button.handlers.click({stopPropagation(){}});
  assert.equal(list.hidden,false);assert.equal(button.getAttribute('aria-expanded'),'true');assert.equal(button.title,'Hide the list of source folders.');
  const items=list.children.map(line=>line.children.find(c=>c.textContent==='Open folder'));
  assert.equal(document.activeElement,items[0],'focus moves to the first Open folder');
  assert.deepEqual(list.children.map(line=>line.children[0].textContent),['Z:\\Audiobooks\\Книга\\CD 1','Z:\\Audiobooks\\Книга\\CD 2','Z:\\Audiobooks\\Книга\\CD 3']);
  assert.deepEqual(list.children.map(line=>line.children[1].textContent),['10 files','11 files','12 files']);
  assert.equal(items[1].getAttribute('aria-label'),'Open folder 2 of 3: Z:\\Audiobooks\\Книга\\CD 2');assert.equal(items[1].title,'Open this folder in File Explorer.');
  assert.equal(opened.length,3,'the list opens nothing by itself');await items[1].handlers.click({stopPropagation(){}});assert.equal(opened.at(-1).directory_id,'dir-1');
  items[2].handlers.keydown({key:'Escape',stopPropagation(){},preventDefault(){}});assert.equal(list.hidden,true);assert.equal(document.activeElement,button,'Esc returns focus');
  await button.handlers.click({stopPropagation(){}});
  // The open state is kept per book across polls (rebuilds) and chips.
  for(let i=0;i<10;i++)paint([bookRow('many',{source_directories:folders(3),source_directory_count:3})]);
  tr=trOf('cand-many');list=walk(statusCell(tr)).find(e=>e.className==='folder-list-box');assert.equal(list.hidden,false,'still open after 10 polls');
  // 12 folders: every one is reachable, inside its own scrolling box (no cap).
  paint([bookRow('twelve',{source_directories:folders(12),source_directory_count:12})]);tr=trOf('cand-twelve');
  await folderButtons(tr)[0].handlers.click({stopPropagation(){}});list=walk(statusCell(tr)).find(e=>e.className==='folder-list-box');
  assert.equal(list.children.length,12);assert.equal(list.tabIndex,0);
  const css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8');assert.match(css,/\.folder-list-box\{[^}]*max-height:232px[^}]*overflow-y:auto/);
  // A row whose own list prints "In {folder}" gets no second line; a book with no source folder at all is aria-disabled.
  paint([hold('fu','files_unclear','lack_title',{missing:1,total:12},{reasons:['Source membership uncertain']})]);
  assert.equal(sourceLine(trOf('cand-fu')).hidden,true,'the row list wins');
  paint([bookRow('none',{members:[]})]);button=folderButtons(trOf('cand-none'))[0];
  assert.equal(button.getAttribute('aria-disabled'),'true');assert.equal(button.title,'This book has no source files to open a folder for.');
  // The details panel lists folders with the same builder.
  context.inspectorFixture={sections:[],source_directories:[{id:'a',path:'Z:\\A'},{id:'b',path:'Z:\\B'}]};run('renderInspector(inspectorFixture,rows[0],inspectSequence)');
  assert.deepEqual(get('folder-list').children.map(line=>line.children.find(c=>c.textContent==='Open folder').getAttribute('aria-label')),['Open folder 1 of 2: Z:\\A','Open folder 2 of 2: Z:\\B']);
  assert.equal(get('folder-list').children[0].children.find(c=>c.textContent==='Open folder').title,'Open this folder in File Explorer.');

  // Check 6: identity. The title Approve uses first; the raw clue only when it differs, with its role; Reader and Clue lines.
  const narrator=asked('hat',{kind:'title_author',why:'',fields:{title:{proposal:'Шляпа полная небес',basis:'tag',clue:{text:'исп. Капитан Абр и Nelly',role:'narrator'}},
    author:{proposal:'Pratchett Terry',basis:'tag',clue:{text:'Терри Пратчетт. Шляпа полная небес',role:'author_and_title'}}},reader:'Капитан Абр и Nelly'},{members:Array.from({length:105},(_,i)=>({path:'Z:\\Audiobooks\\hat\\'+i+'.mp3'}))});
  const flagged=asked('flag',{kind:'title_author',why:'',fields:{title:{proposal:'исп. Капитан Абр и Nelly',basis:'tag',flag:'narrator'},author:{proposal:'Pratchett Terry',basis:'tag',clue:{text:'Òåððè Ïðàò÷åòò',role:'garbled'},flag:'garbled'}}});
  const plain=asked('same',{kind:'title_author',why:'',fields:{title:{proposal:'Title same',basis:'tag'},author:{proposal:'Artist same',basis:'tag'}}});
  const series=asked('ser',{kind:'title_author',why:'',series:{name:'Discworld',number:'32',basis:'research'}});
  const clue=asked('clue',{kind:'title_author',why:'',series_clue:'Книга Нового Солнца #3'});
  paint([narrator,flagged,plain,series,clue,bookRow('noask')]);
  const book=tr=>texts(tr.children[1]),author=tr=>walk(tr.children[2]).filter(e=>e.className==='goes-to id-line' && !e.hidden).map(lineText);
  assert.deepEqual(book(trOf('cand-hat')).filter(t=>!/audio files?$/.test(t)),['Шляпа полная небес','Title clue: исп. Капитан Абр и Nelly · narrator credit']);
  assert.deepEqual(author(trOf('cand-hat')),['Author Pratchett Terry','Reader Капитан Абр и Nelly','Clue Терри Пратчетт. Шляпа полная небес · author and title together']);
  assert.equal(walk(trOf('cand-hat').children[1]).find(e=>String(e.className).includes('title-facts')).textContent,'Pratchett Terry · Reader: Капитан Абр и Nelly · 105 audio files','folded into the title cell below 800 px (check 7)');
  assert.ok(book(trOf('cand-flag')).includes('Check this title: it looks like a narrator credit.'));assert.ok(texts(trOf('cand-flag').children[2]).includes('Check this author: it looks garbled.'));
  assert.ok(author(trOf('cand-flag')).includes('Clue Òåððè Ïðàò÷åòò · garbled'));
  const folded=walk(trOf('cand-flag').children[1]).find(e=>String(e.className).includes('author-flag-folded'));
  assert.ok(folded && !folded.hidden && /title-facts/.test(folded.className),'the author flag stays visible in the narrow bands (check 7)');assert.equal(folded.textContent,'Check this author: it looks garbled.');
  assert.equal(walk(trOf('cand-hat').children[1]).find(e=>String(e.className).includes('author-flag-folded')).hidden,true,'no flag: no folded line');
  const titleInput=walk(statusCell(trOf('cand-flag'))).find(e=>e.dataset?.name==='title');assert.ok(titleInput,'a flagged title shows the Title field');assert.equal(titleInput.value,'исп. Капитан Абр и Nelly');
  assert.equal(buttonsOf(trOf('cand-flag'))[0].textContent,'Approve');assert.equal(buttonsOf(trOf('cand-flag'))[0].getAttribute('aria-disabled'),null,'Approve is not blocked by a flag');
  assert.deepEqual(book(trOf('cand-same')).filter(t=>!/audio files?$/.test(t)),['Title same'],'no clue line when it equals the title; no flag, series or Includes');
  assert.deepEqual(author(trOf('cand-same')),['Author Artist same'],'no Reader, no Clue (it equals the author)');
  assert.ok(book(trOf('cand-ser')).includes('Series: Discworld · No. 32'));
  assert.ok(book(trOf('cand-clue')).includes('The title mentions a series: Книга Нового Солнца #3. Not used in the file name.'));
  assert.equal(trOf('cand-noask').children[1].textContent,'Title clue: Title noask','a row without a question keeps its clue cell');
  assert.equal(run('placeText({series:"Discworld",number:"32"})'),'Series: Discworld · No. 32','the Place line prints a plain series too');

  // Check 8: the Numbers line prints exactly the tokens the engine sends; contiguous numbering prints none.
  const numbersOf=tr=>walk(statusCell(tr)).find(e=>e.className==='field-help ask-numbers');
  const membershipOf=tr=>walk(statusCell(tr)).find(e=>e.className==='field-help ask-membership');
  paint([hold('g1','order_unclear','no_tracks',{},{numbers:{source:'names',first:'004',last:'017',skipped:['007','009-016'],skipped_total:2},membership:'established'},{members:Array.from({length:13},(_,i)=>({path:'Z:\\Audiobooks\\g1\\'+i+'.mp3'}))}),
    hold('g2','order_unclear','gaps',{},{numbers:{source:'tags',first:'1',last:'38',skipped:['35'],skipped_total:1}}),
    hold('g3','order_unclear','no_tracks',{},{numbers:{source:'names',first:'01',last:'38',skipped:[],skipped_total:0}}),
    hold('g4','order_unclear','no_tracks',{},{numbers:{source:'names',first:'05',last:'07',skipped:[],skipped_total:0},membership:'established'},{members:[1,2,3].map(i=>({path:'Z:\\Audiobooks\\g4\\0'+i+'.mp3'}))}),
    hold('g5','order_unclear','gaps',{},{numbers:{source:'names',first:'1',last:'40',skipped:['2','4','6','8','10','12','14','16'],skipped_total:8}}),
    hold('g6','order_unclear','no_tracks')]);
  assert.equal(numbersOf(trOf('cand-g1')).textContent,'File names run from 004 to 017. Skipped: 007, 009-016.');
  assert.equal(numbersOf(trOf('cand-g2')).textContent,'Tags run from 1 to 38. Skipped: 35.');
  assert.equal(numbersOf(trOf('cand-g3')).hidden,true,'contiguous from 1: no line');
  assert.equal(numbersOf(trOf('cand-g4')).textContent,'File names run from 05 to 07.');
  assert.equal(numbersOf(trOf('cand-g5')).textContent,'File names run from 1 to 40. Skipped: 2, 4, 6, 8, 10, 12 + 2 more.');
  assert.equal(numbersOf(trOf('cand-g6')).hidden,true,'nothing sent: no line');
  assert.equal(run('numbersLine({numbers:{source:"names",first:"004",skipped:["007"]}})'),'','an incomplete fact prints nothing, never "undefined"');
  assert.equal(membershipOf(trOf('cand-g1')).textContent,'The source folder holds only these 13 files.');assert.equal(membershipOf(trOf('cand-g4')).textContent,'The source folder holds only these 3 files.');
  assert.equal(membershipOf(trOf('cand-g6')).hidden,true);
  // Check 10: a gap or late start takes "Approve these files"; a real order question keeps "Approve this order".
  const gapTip='Approve the files shown as one book, gaps included: convert if needed, rename, move to Audiobooks Sorted.';
  for(const id of ['cand-g1','cand-g2','cand-g4','cand-g5']){assert.equal(buttonsOf(trOf(id))[0].textContent,'Approve these files',id);assert.equal(buttonsOf(trOf(id))[0].title,gapTip,id);}
  assert.equal(buttonsOf(trOf('cand-g3'))[0].textContent,'Approve this order');assert.equal(buttonsOf(trOf('cand-g6'))[0].textContent,'Approve this order');
  assert.equal(statusCell(trOf('cand-g6')).children[0].textContent,'The tags have no track numbers. The file names set the order.');
  // Check 9: while membership is checking nothing says missing or "aren't here"; Approve works with its checking tooltip.
  paint([hold('c1','files_unclear','one_of_many',{index:36,total:38},{membership:'checking',reasons:['Source membership uncertain']}),
    hold('c2','files_unclear','one_of_many',{index:36,total:38},{reasons:['Source membership uncertain']}),
    hold('c3','order_unclear','gaps',{},{membership:'checking',numbers:{source:'names',first:'004',last:'017',skipped:['007'],skipped_total:1}})]);
  tr=trOf('cand-c1');assert.equal(statusCell(tr).children[0].textContent,'This file is tagged as track 36 of 38.');
  assert.equal(membershipOf(tr).textContent,'Still checking which other files belong to this book.');
  assert.ok(!texts(tr).some(t=>/missing|aren't here/i.test(t)),'no missing claim while checking');
  assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);assert.equal(buttonsOf(tr)[0].title,'The app is still checking which other files belong to this book. This approves only the files shown.');
  assert.equal(statusCell(trOf('cand-c2')).children[0].textContent,"This file is tagged as track 36 of 38. The other tracks aren't here.",'positive control: settled or unsent keeps the sentence');
  assert.equal(buttonsOf(trOf('cand-c3'))[0].textContent,'Approve these files');assert.equal(buttonsOf(trOf('cand-c3'))[0].title,'The app is still checking which other files belong to this book. This approves only the files shown.');
  assert.ok(!texts(trOf('cand-c3')).some(t=>/missing|aren't here/i.test(t)));

  // Check 11: Includes on one row for a novel plus stories; the raised folder question with Books, Approve as one book first.
  paint([asked('krieg',{kind:'title_author',why:'',contents:{stories:[{title:'Исход',author:'Стив Лайонс',files:1},{title:'Сильные среди нас',author:'X',files:1},{title:'Среди мертвецов',author:'Y',files:1}],other_authors:2}}),
    asked('five',{kind:'title_author',why:'',contents:{stories:['А','Б','В','Г','Д'].map(title=>({title,author:'',files:1})),other_authors:1}}),
    hold('folder','files_unclear','folder_books',{works:[{name:'Book A',files:34},{name:'Book B',files:12}]},{reasons:['Source membership uncertain']})]);
  assert.ok(book(trOf('cand-krieg')).includes('Includes 3 stories: Исход, Сильные среди нас, Среди мертвецов.'));assert.ok(book(trOf('cand-krieg')).includes('2 of them credit another author.'));
  assert.ok(book(trOf('cand-five')).includes('Includes 5 stories: А, Б, В + 2 more.'));assert.ok(book(trOf('cand-five')).includes('1 of them credits another author.'));
  tr=trOf('cand-folder');assert.equal(statusCell(tr).children[0].textContent,'This folder may hold more than one book.');
  assert.ok(texts(tr).includes('Books: Book A (34 files) · Book B (12 files)'));
  assert.deepEqual(buttonsOf(tr).slice(0,3).map(b=>b.textContent),['Approve as one book','Keep as separate books','Scan again']);
  assert.equal(buttonsOf(tr)[0].title,'File everything in this folder as one book: convert if needed, rename, move to Audiobooks Sorted.');
  assert.equal(buttonsOf(tr)[1].title,'Keep each book on the Books line as its own book. Nothing is joined. Each is checked again.');
  assert.equal(walk(statusCell(tr)).find(e=>e.className==='goes-to').children[0].textContent,'As one book');
  // Check 12: the source line makes a divided folder visible: two rows that print the same folder (the S5 control shape).
  const split=[bookRow('k1',{source_directories:[{id:'d',path:'Z:\\Audiobooks\\Криг',files:34}]}),bookRow('k2',{source_directories:[{id:'d',path:'Z:\\Audiobooks\\Криг',files:1}]})];paint(split);
  const printed=split.map(r=>lineText(sourceLine(trOf(r.id))));assert.equal(new Set(printed).size,1,'the deliberately split fixture prints one folder twice');
  console.log('PASS 0.23.1 rows: Open source folder (one, several, 12, gone list, details builder), the In line, Book / Author / reader lines, Numbers and membership lines, gap faces, Includes, the raised folder question');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_0231_rows_frontend.js'),module);m.filename=path.join(__dirname,'test_0231_rows_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

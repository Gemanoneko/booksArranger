'use strict';
// 0.31.0 (Judy's Docs/BooksArranger_0.31.0_UX.md, section 4.4, fourth round; Sergei's R22 and R25): a book that is not
// converted yet no longer asks about a doubtful series. "Number unclear", "Title unclear" for a title that only looks like
// a series name and number, and "Sources disagree" about a series are gone: such a book is an ordinary row (its real
// status, no sentence, no inline fields, no Approve, no Place line), the details panel's "Sources disagree" block is hidden
// whole when no other question is left, and nothing about the dropped series is shown anywhere. Every question that is
// not about a doubtful series keeps its status, sentence, fields and buttons. Real frontend on the Retry test's
// DOM/transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted',DROPPED='Лабиринты Ехо';  // the series a source named and the engine dropped as doubtful
function book(name,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,fingerprint:'a'.repeat(64),scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'Z:\\Audiobooks\\Фрай Макс\\'+name+'\\01.mp3',member_key:'one'}],track_order:['one'],included:['one'],review:{},review_context:{},status:'Queued',entered:[],
    automatic:{state:'Queued',reasons:[],sources:[]},creation:{status:'Queued',can_create:false,reasons:[],destination:'Фрай Макс\\Title '+name+' - Фрай Макс.m4b'},source_directory_count:1,place:{universe:'',series:'',number:'',collection:false},...extra};
}
const doubt=[{provider:'fantlab',name:DROPPED,number:'3',why:'number_mismatch',source_url:'https://fantlab.ru/work1'}];
// What the engine sends since R22 for each former question: no ask, no series, the dropped series only as a stored fact.
const dropped=(name,extra={})=>book(name,{series_dropped:doubt,metadata_facts:{original_language:{status:'known',value:'Russian'},series_state:'omitted_unknown',gap_search:{gaps:['series'],unfilled:['series'],series_doubt:doubt}},
  metadata_questions:{signature:'s',questions:[],unresolved_count:0,dropped_as_doubtful:['series'],decision_history:[],manual_source_ids:[]},...extra});
const dest=p=>({path:p,absolute:ROOT+'\\'+p,taken:false,reason:'',shared:null});
const held=(name,ask,extra={})=>book(name,{status:'Held',automatic:{state:'Held',reasons:[ask.reasons[0]]},creation:{status:'Held',can_create:false,reasons:[]},ask,...extra});
// A question as the engine sent it before R22, still on a row (the engine's re-check has not taken it yet).
const titleSeries=held('ts',{kind:'title_author',also:null,why:'title_series',odd_name:true,reasons:['Title or author missing'],fields:{title:{proposal:'Чужак',basis:'tag'},author:{proposal:'Фрай Макс',basis:'tag'}},candidates:[],
  split:{series:DROPPED,number:'1',title:'Чужак'},destination:dest('Фрай Макс\\Чужак - Фрай Макс.m4b')});
const numberUnclear=held('nu',{kind:'title_author',also:null,why:'number_unclear',odd_name:true,reasons:['Title or author missing'],volume:{title_number:2,series_number:'3',provider:'fantlab'},
  fields:{title:{proposal:'Волонтёры вечности',basis:'tag'},author:{proposal:'Фрай Макс',basis:'tag'},series:{proposal:DROPPED,basis:'source'},number:{proposal:'2',basis:'title'}},candidates:[],
  destination:dest('Фрай Макс\\'+DROPPED+'\\2 - Волонтёры вечности - Фрай Макс.m4b')});
// The questions that are not about a doubtful series.
const people=held('pe',{kind:'author_unclear',also:null,why:'two_people',reasons:['Author unclear'],fields:{title:{proposal:'Good Omens',basis:'tag'},author:{proposal:'Neil Gaiman',basis:'tag'}},
  candidates:[{name:'Neil Gaiman',source:'author tag',reader_count:0},{name:'Terry Pratchett',source:'author tag',reader_count:0}],hold:{kind:''},destination:dest('Gaiman Neil\\Good Omens.m4b')});
const part=held('pb',{kind:'part_of_book',also:null,why:'',cause:'chapter',reasons:['One file may be part of a bigger book'],facts:{},files:[{name:'Глава 05.mp3',folder:'Z:\\Audiobooks\\Фрай Макс\\pb'}],file_count:1,flagged:[],
  fields:{title:{proposal:'Глава 05',basis:'file_name'},author:{proposal:'Фрай Макс',basis:'tag'}},candidates:[],hold:{kind:''},destination:dest('Фрай Макс\\Глава 05 - Фрай Макс.m4b')});
const bitrate=held('br',{kind:'title_author',also:null,why:'title_bitrate',odd_name:true,reasons:['Title or author missing'],fields:{title:{proposal:'Антитела 128',basis:'tag'},author:{proposal:'Андерсон Кевин',basis:'tag'}},candidates:[],
  hold:{kind:''},destination:dest('Андерсон Кевин\\Антитела 128.m4b')});
const latin=held('la',{kind:'title_author',also:null,why:'title_latin',odd_name:true,reasons:['Title or author missing'],fields:{title:{proposal:'Master vetrov i zakatov',basis:'tag'},author:{proposal:'Фрай Макс',basis:'tag'}},candidates:[],
  hold:{kind:''},destination:dest('Фрай Макс\\Master vetrov i zakatov.m4b')});
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children].filter(b=>b.textContent && !b.hidden);
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const hasClass=(element,name)=>String(element.className || '').split(' ').includes(name);
const deepText=element=>[element.hidden?'':element.textContent,...(element.hidden?[]:element.children.map(deepText))].join('\n');
const hints=tr=>walk(statusCell(tr)).filter(e=>(hasClass(e,'attention-hint') || hasClass(e,'attention-also') || hasClass(e,'ask-why')) && !e.hidden && e.textContent).map(e=>e.textContent);
const inputs=tr=>walk(statusCell(tr)).filter(e=>e.type==='text' || e.type==='radio');
const placeLine=tr=>{const line=walk(statusCell(tr)).find(e=>hasClass(e,'book-place'));return line && !line.hidden?line.textContent:'';};
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;view="candidates";filters.candidates="all";attentionGroup="all";askDrafts.clear();namesState.clear();selectedBooks.clear();renderRows(true);controls()');}
function open(row){context.fixture1=row;run('automaticResultKey=null;mergeRenderKey=null;selectedPath=null;select(fixture1,true)');}
// Everything the page shows outside the list: every element the page reads by id (the details panel, the jobs panel).
const panelText=()=>[...nodes.entries()].filter(([id])=>id!=='inventory').map(([,element])=>deepText(element)).join('\n');
const ORDINARY=['Edit names','View metadata','Open source folder'];
(async()=>{
  const source=fs.readFileSync(path.join(__dirname,'..','web','app.js'),'utf8'),html=fs.readFileSync(path.join(__dirname,'..','web','index.html'),'utf8');
  run('state='+JSON.stringify({...backend,audiobook_output_root:ROOT}));

  // 1. The three former questions as the engine sends them now: each book is an ordinary row and goes on to convert.
  paint([dropped('a'),dropped('b',{status:'',automatic:{state:'Pending',reasons:[],sources:[]},creation:{status:'Needs metadata review',can_create:false,reasons:[]}}),dropped('c',{status:'Converting',creation:{status:'Converting',can_create:false,reasons:[]}})]);
  for(const [id,status] of [['cand-a','Queued'],['cand-b','Pending'],['cand-c','Processing']]){
    const tr=trOf(id);
    assert.equal(statusCell(tr).textContent,status,id+': the status its real state gives');
    assert.deepEqual(hints(tr),[],id+': no sentence');assert.deepEqual(inputs(tr),[],id+': no Title, Series or Number field on the row');
    assert.deepEqual(buttonsOf(tr).map(b=>b.textContent),ORDINARY,id+': the ordinary buttons, and no Approve');
    assert.equal(placeLine(tr),'',id+': no Place line');
    assert.ok(!deepText(tr).includes(DROPPED),id+': nothing about the dropped series on the row');
  }
  // The details panel: no "Sources disagree" block, no Resolve metadata, no Save choices, and nothing about the series,
  // the recorded facts' dump included. Positive control: that dump still prints the book's other facts.
  open(dropped('a'));
  assert.equal(get('metadata-questions').hidden,true,'the block is hidden whole');assert.equal(get('edit-held-metadata').hidden,true);
  assert.equal(get('metadata-question-fields').children.length,0);
  assert.ok(!panelText().includes(DROPPED),'the dropped series is nowhere in the panels');
  assert.match(get('automatic-accepted-evidence').textContent,/"original_language"/,'positive control: the facts are printed');
  assert.match(get('automatic-accepted-evidence').textContent,/"gap_search"/);assert.doesNotMatch(get('automatic-accepted-evidence').textContent,/series_doubt|number_mismatch/);
  assert.equal(run('JSON.stringify(shownFacts({gap_search:{gaps:["series"],series_doubt:[1]},x:1}))'),'{"gap_search":{"gaps":["series"]},"x":1}');
  assert.equal(run('shownFacts(null)'),null);assert.equal(run('JSON.stringify(shownFacts({x:1}))'),'{"x":1}','facts without the entry are printed as they are');
  for(const word of ['Number unclear','Title unclear','Sources disagree — choose again','possible series','Possible series'])assert.ok(!panelText().includes(word) && !deepText(get('inventory')).includes(word),word);

  // 2. A question from before the update that is still on a row: the same ordinary row, never the old words, fields or
  // button, and never the generic "Title and author missing" in their place.
  paint([titleSeries,numberUnclear]);
  for(const id of ['cand-ts','cand-nu']){
    const tr=trOf(id);
    assert.equal(run('askOf(rows.find(row=>row.id==="'+id+'"))'),null,id+': no question');
    assert.deepEqual(hints(tr),[],id+': no sentence');assert.deepEqual(inputs(tr),[],id+': no inline fields');
    assert.deepEqual(buttonsOf(tr).map(b=>b.textContent),ORDINARY,id+': no Approve left behind');
    assert.equal(placeLine(tr),'');
    for(const word of ['Number unclear','Title unclear','Title and author missing','says book','looks like a series',DROPPED])assert.ok(!deepText(tr).includes(word),id+': '+word);
  }
  open(numberUnclear);
  for(const word of ['Number unclear','says book',DROPPED])assert.ok(!panelText().includes(word),'panel: '+word);
  assert.equal(get('names-found').hidden,true,'no "Names found" list for a question that is not asked');
  // Edit names proposes nothing from that question: Series and Number are his to type, as on every row.
  assert.equal(run('namesProposal("cand-nu","series")'),'');assert.equal(run('namesProposal("cand-nu","number")'),'');
  // Select all and bulk "Approve as is" never take such a row.
  run('attentionGroup="title_author";filters.candidates="output_attention";viewControls()');paint([titleSeries,numberUnclear,bitrate]);
  run('selectedBooks.set("cand-ts",2);selectedBooks.set("cand-nu",2);batchCounts()');assert.equal(run('approveSelectable().items.length'),0);
  run('attentionGroup="all";filters.candidates="all";selectedBooks.clear();viewControls()');

  // 3. A Missing files row never carries "Also: the title starts with what looks like a series name and number." and
  // keeps no field for that cause; it is a plain Missing files row with its own buttons.
  const missing=why=>held('mf',{kind:'files_missing',also:'title_author',why,reasons:['Files missing'],missing:{total:3,present:2,files:['Z:\\Audiobooks\\Фрай Макс\\mf\\03.mp3']},
    fields:{title:{proposal:'Чужак',basis:'tag'},author:{proposal:'Фрай Макс',basis:'tag'}},candidates:[],hold:{kind:''},destination:dest('Фрай Макс\\Чужак - Фрай Макс.m4b')});
  for(const why of ['title_series','number_unclear']){
    paint([missing(why)]);const tr=trOf('cand-mf');
    assert.equal(statusCell(tr).textContent,'Missing files',why);assert.deepEqual(hints(tr),['1 of 3 files is missing.'],why+': its own sentence, and no Also line');
    assert.deepEqual(inputs(tr),[],why+': no field for the withdrawn cause');
    assert.deepEqual(buttonsOf(tr).map(b=>b.textContent).slice(0,2),['Scan again',"Convert what's there"],why);
  }
  // Positive control: a second cause that is still a question keeps its Also line and its field.
  paint([missing('title_bitrate')]);
  assert.deepEqual(hints(trOf('cand-mf')),['1 of 3 files is missing.','Also: the title ends with a number that looks like a bitrate.']);
  assert.deepEqual(inputs(trOf('cand-mf')).map(e=>e.dataset.name),['title']);

  // 4. Not changed: every question that is not about a doubtful series. Author unclear keeps its choices and its inline
  // Series and Number pair; Part of a bigger book keeps its face; Title unclear keeps its two other causes.
  paint([people,part,bitrate,latin]);
  let tr=trOf('cand-pe');
  assert.equal(statusCell(tr).textContent,'Author unclear');assert.deepEqual(hints(tr),["Two people are credited. The app can't tell who wrote it."]);
  assert.deepEqual(inputs(tr).filter(e=>e.type==='radio').map(e=>e.value),['c0','c1','other'],'its choices');
  assert.deepEqual(inputs(tr).filter(e=>e.type==='text').map(e=>e.dataset.name || 'other'),['other','title','series','number'],'Other, then Title with the Series and Number pair');
  assert.equal(buttonsOf(tr)[0].textContent,'Approve');assert.equal(buttonsOf(tr)[0].getAttribute('aria-disabled'),null);
  tr=trOf('cand-pb');
  assert.equal(statusCell(tr).textContent,'Part of a bigger book');assert.deepEqual(hints(tr),['This file is named as one chapter.']);
  assert.equal(buttonsOf(tr)[0].textContent,'Approve as one book');assert.ok(buttonsOf(tr).some(b=>b.textContent==='Scan again'));
  assert.deepEqual(inputs(tr).map(e=>e.dataset.name),['title'],'the Title field of the question');
  for(const [id,sentence,value] of [['cand-br','The title ends with a number that looks like a bitrate.','Антитела 128'],['cand-la','The title looks like Russian written in Latin letters.','Master vetrov i zakatov']]){
    tr=trOf(id);assert.equal(statusCell(tr).textContent,'Title unclear',id);assert.deepEqual(hints(tr),[sentence],id);
    assert.deepEqual(inputs(tr).map(e=>[e.dataset.name,e.value]),[['title',value]],id);assert.equal(buttonsOf(tr)[0].textContent,'Approve',id);
  }
  // An Approve on a question that stays is sent as before.
  const posts=[];const baseFetch=context.fetch;
  context.fetch=async(route,options)=>{if(route==='/api/candidate/approve'){posts.push(JSON.parse(options.body));return {ok:true,status:200,json:async()=>({approved:true,job_id:'job-1',row:{id:'cand-br'}})};}return baseFetch(route,options);};
  await buttonsOf(trOf('cand-br'))[0].handlers.click({stopPropagation(){}});await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(posts.at(-1)?.id,'cand-br','positive control: the row\'s Approve still presses');
  context.fetch=baseFetch;

  // 5. The details panel's block with a question left: it lists that one and only that one. A series or number question
  // is never among them (the engine sends none; the test's own list has none).
  const option=(id,values,provider)=>({id,values,sources:[{provider,id:'r-'+id,retrieved_utc:'2026-11-22T10:00:00Z',evidence:{}}]});
  const question={id:'q-title',type:'field',field:'title',label:'Which title should this book use?',profile_fields:[],options:[option('o1',{title:'Чужак'},'fantlab'),option('o2',{title:'Чужак (сборник)'},'litres')],not_supplied:[],
    evidence_signature:'e',resolved:false,decision:null};
  open(dropped('q',{metadata_questions:{signature:'s2',questions:[question],unresolved_count:1,dropped_as_doubtful:['series','number'],decision_history:[],manual_source_ids:[]}}));
  assert.equal(get('metadata-questions').hidden,false,'positive control: two sources that differ in the title still show the block');
  const listed=get('metadata-question-fields').children.map(fieldset=>fieldset.children[0].textContent);
  assert.deepEqual(listed,['Which title should this book use?']);
  assert.equal(get('edit-held-metadata').hidden,false);assert.equal(get('edit-held-metadata').textContent,'Resolve metadata question');
  assert.ok(!panelText().includes('Which series should this book use?') && !panelText().includes('Which number should this book use?'));
  assert.ok(!panelText().includes(DROPPED));
  // With that question gone too the block hides whole again: no heading over an empty list, no Save choices to press.
  open(dropped('q'));assert.equal(get('metadata-questions').hidden,true);assert.equal(get('edit-held-metadata').hidden,true);

  // 6. The page has no words left for the two questions, and their paths are gone: the sentence, the status, the number
  // sentence, the inline pair for a title question. The asks are named only where the page turns them away.
  for(const gone of ['Number unclear','The title starts with what looks like a series name and number.','says book','numberUnclear'])assert.ok(!source.includes(gone) && !html.includes(gone),gone);
  assert.equal(source.split("'title_series'").length-1,1,'named once: the list of withdrawn questions');assert.equal(source.split("'number_unclear'").length-1,1);
  assert.equal(run('ODD_TITLE.join()'),'title_bitrate,title_latin');assert.equal(run("Object.hasOwn(ASK_COPY,'title_series')"),false);
  assert.equal(run('inlineNames({kind:"candidate",ask:{kind:"title_author",why:"title_bitrate",fields:{title:{proposal:"x"},author:{proposal:"y"}}}})'),false,'a title question has no Series and Number pair');
  console.log('PASS 0.31.0 withdrawn series questions: an ordinary row for each former question (new and left-over), no Also on Missing files, the Sources disagree block hidden whole, nothing about the dropped series; Author unclear, Part of a bigger book and Title unclear\'s other causes unchanged');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_series_questions_frontend.js'),module);m.filename=path.join(__dirname,'test_series_questions_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

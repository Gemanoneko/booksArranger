'use strict';
// 0.31.0 (Judy's Docs/BooksArranger_0.31.0_UX.md, section 5, fourth round; Sergei's R2 and R20): a book may wait a few tries
// for its online answer before it converts. Its row reads "Waiting for an online answer" with a hint that prints the
// engine's own "Try N of M" and time; the Waiting list has one item for these books (online waits only, in the place of
// 0.30.0's "Metadata sources" item); the Automatic block says the same; and the wait ends in one of four ways, each worded
// differently (5.2). A book that waits for the library drive or for the catalog keeps "Waiting for source". No "Convert
// now". Real frontend on the Retry test's DOM/transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const NOW=Date.now(),AT=Math.floor(NOW/1000)+3600;  // the engine's next try, epoch seconds (the look-up record's clock)
function book(name,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,fingerprint:'a'.repeat(64),scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Тёмный лес',conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'D:\\Audiobooks\\Лю Цысинь\\Тёмный лес\\'+name+'.mp3'}],track_order:[],included:[],review:{},review_context:{},status:'',entered:[],
    creation:{status:'Needs metadata review',can_create:false,reasons:[]},source_directory_count:1,...extra};
}
const record=(extra={})=>({asked:{title:'Тёмный лес',author:'Лю Цысинь',gaps:['original_title','series']},asking:['original_title','series'],waiting_for:['fantlab','wikidata'],fields:{original_title:'waiting',series:'waiting'},
  tries:1,limit:3,next_try:2,next_at:AT,waiting:true,ended:'',...extra});
const waiting=(name,lookup=record(),waits='online_answer',extra={})=>book(name,{automatic:{state:'Waiting for source',waits_for:waits,reasons:['Waiting for the series: its sources are busy. The app tries again by itself.'],sources:[],retry_at:AT,
  wait:{source:'fantlab',kind:'source_unavailable',retry_at:AT},lookup},...(lookup?{lookup:{asked:lookup.asked,fields:lookup.fields,tries:lookup.tries,limit:lookup.limit,next_at:lookup.next_at,waiting:lookup.waiting,ended:lookup.ended}}:{}),...extra});
const before=(extra={})=>({count:1,next_at:AT*1000,waiting:[{book_id:'cand-w',title:'Тёмный лес',limit:3,next_try:2}],limits:{per_source:3,min_spacing_seconds:600,max_spacing_seconds:21600,max_wait_seconds:43200,sources:['fantlab','wikidata','goodreads']},tries_continue:true,...extra});
const jobs={state:'Completed',approved_total:10,converted_total:10,queued:0,failed:0,attention_counts:{},candidate_total:11,not_approved_total:1};
function world(lookups,automatic={},work={}){
  context.fixture={...backend,audiobook_output_root:'Z:\\Audiobooks Sorted',audiobook_jobs:jobs,automatic_processing:{...backend.automatic_processing,state:'Running',phase:'waiting',can_start:false,can_stop:true,automatic_retry_enabled:true,next_retry_at:AT,research:{researching:0,waiting:1,held:0},...automatic},
    work:{rows:[],waiting:[],counts:{},unread:[],snapshot_age_ms:0,refreshing:false,state:'continues',pending:{lookups:{series:0,details:0,all:0}},background:{},lookups_waiting:[],...(lookups===undefined?{}:{lookup_before_review:lookups}),...work}};
  run('state=fixture');
}
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const hasClass=(element,name)=>String(element.className || '').split(' ').includes(name);
const hintOf=tr=>{const hint=walk(statusCell(tr)).find(e=>hasClass(e,'attention-hint'));return hint && !hint.hidden?hint.textContent:'';};
function paint(list){context.fixture2=list;run('rows=fixture2.map(row=>({...row}));totalRows=rows.length;view="candidates";filters.candidates="all";renderRows(true);controls()');}
const waits=()=>get('jobs-wait').children.map(item=>({line1:item.children[0].children[0].children.map(part=>part.textContent).join(''),line2:item.children[0].children[1].textContent,tip:item.children[0].children[1].title,button:item.children[1]}));
const facts=()=>{const list=get('automatic-facts').children,out={};for(let i=0;i<list.length;i+=2)out[list[i].textContent]=list[i+1].textContent;return out;};
function panel(row){context.fixture3=row;run('automaticResultKey=null;renderAutomaticResult(fixture3)');return {status:get('automatic-result-status').textContent,hint:get('automatic-result-hint').hidden?'':get('automatic-result-hint').textContent,facts:facts()};}
(async()=>{
  const source=fs.readFileSync(path.join(__dirname,'..','web','app.js'),'utf8'),html=fs.readFileSync(path.join(__dirname,'..','web','index.html'),'utf8');
  const clock=run('waitingClock('+AT+')');assert.match(clock,/^\d\d:\d\d$/);

  // 1. While a book waits (5.1): the status, and the hint with what is asked, the engine's try numbers and time.
  world(before());paint([waiting('w')]);
  let tr=trOf('cand-w');
  assert.equal(statusCell(tr).textContent,'Waiting for an online answer');
  assert.equal(hintOf(tr),'No online answer yet about its English title and series. Try 2 of 3 at '+clock+'. Nothing to do.');
  // It is not a question: the row keeps its ordinary buttons and gains none.
  assert.deepEqual(buttonsOf(tr).filter(b=>b.textContent && !b.hidden).map(b=>b.textContent),['Edit names','View metadata','Open source folder']);
  assert.equal(run('askOf(rows[0])'),null);
  // The asked part follows the book.
  for(const [asking,words] of [[['original_title'],'its English title'],[['series'],'its series'],[['series_name'],'the English name of its series'],[['original_title','series_name'],'its English title and series name'],
      [['original_title','series'],'its English title and series'],[['original_title','series','series_name'],'its English title and series'],[['series','series_name'],'its series'],[[],'this book'],[['something_new'],'this book']]){
    paint([waiting('w',record({asking}))]);assert.equal(hintOf(trOf('cand-w')),'No online answer yet about '+words+'. Try 2 of 3 at '+clock+'. Nothing to do.',JSON.stringify(asking));
  }
  // A record that does not list what still waits is read from its fields; one that says nothing: "this book".
  paint([waiting('w',record({asking:undefined,fields:{original_title:'answered',series:'waiting'}}))]);assert.match(hintOf(trOf('cand-w')),/^No online answer yet about its series\. /);
  paint([waiting('w',record({asking:undefined,fields:undefined}))]);assert.match(hintOf(trOf('cand-w')),/^No online answer yet about this book\. /);
  // The tries are the engine's numbers: change them and the text follows. No time: "is next". No numbers, or numbers that
  // cannot both be true: the sentence is left out, never a guess.
  paint([waiting('w',record({next_try:3,limit:5}))]);assert.equal(hintOf(trOf('cand-w')),'No online answer yet about its English title and series. Try 3 of 5 at '+clock+'. Nothing to do.');
  paint([waiting('w',record({next_try:1,limit:3}))]);assert.match(hintOf(trOf('cand-w')),/ Try 1 of 3 at /,"the app's own hourly limit is no try: try 1 can still be ahead");
  paint([waiting('w',record({next_try:2,limit:2}))]);assert.match(hintOf(trOf('cand-w')),/ Try 2 of 2 at /);
  paint([waiting('w',record({next_at:null}))]);assert.equal(hintOf(trOf('cand-w')),'No online answer yet about its English title and series. Try 2 of 3 is next. Nothing to do.');
  for(const broken of [{next_try:null},{limit:undefined},{next_try:4,limit:3},{next_try:0},{next_try:'2'}]){
    paint([waiting('w',record(broken))]);assert.equal(hintOf(trOf('cand-w')),'No online answer yet about its English title and series. Nothing to do.',JSON.stringify(broken));
  }
  // The details panel's Automatic result shows the same status and hint.
  paint([waiting('w')]);
  let shown=panel(waiting('w'));
  assert.equal(shown.status,'Waiting for an online answer');assert.equal(shown.hint,'No online answer yet about its English title and series. Try 2 of 3 at '+clock+'. Nothing to do.');

  // 2. Automatic processing stopped: the tries do not go on, so no try number, no time and no "Nothing to do."; the hint
  // names the button that starts them (its face is Resume while automatic processing is paused).
  world(before({tries_continue:false}),{state:'Idle',phase:'idle',can_start:true,can_stop:false});paint([waiting('w')]);
  assert.equal(statusCell(trOf('cand-w')).textContent,'Waiting for an online answer');
  assert.equal(hintOf(trOf('cand-w')),'No online answer yet about its English title and series. Press Start automatic processing to try again.');
  assert.equal(panel(waiting('w')).hint,'No online answer yet about its English title and series. Press Start automatic processing to try again.');
  world(before({tries_continue:false}),{state:'Paused',phase:'research',can_start:true,can_stop:false});paint([waiting('w')]);
  assert.equal(hintOf(trOf('cand-w')),'No online answer yet about its English title and series. Press Resume automatic processing to try again.');
  // An engine that does not say whether the tries go on gets neither ending.
  world(undefined);paint([waiting('w')]);assert.equal(hintOf(trOf('cand-w')),'No online answer yet about its English title and series.');

  // 3. Only an online wait (control): a book that waits for the library drive, the catalog, a cover or another source
  // keeps "Waiting for source" and has no hint.
  world(before());
  for(const waits_for of ['library','catalog','cover','source','',null]){  // '' and null: an engine that does not say
    paint([waiting('w',record(),waits_for)]);tr=trOf('cand-w');
    assert.equal(statusCell(tr).textContent,'Waiting for source',String(waits_for));assert.equal(hintOf(tr),'',String(waits_for));
    assert.equal(panel(waiting('w',record(),waits_for)).status,'Waiting for source');
  }

  // 4. The Waiting item (5.1): several books are counted and have no button; one is named and has Show in list.
  const several=before({count:3,waiting:[{book_id:'cand-w',title:'Тёмный лес'},{book_id:'cand-x',title:'Вечная жизнь смерти'},{book_id:'cand-y',title:'Задача трёх тел'}]});
  world(several);run('renderJobs()');
  let listed=waits();
  assert.equal(get('jobs-wait-block').hidden,false);assert.equal(listed.length,1);
  assert.equal(listed[0].line1,'Waiting for an online answer: 3 books');assert.equal(listed[0].line2,'Next try '+clock+'. After 3 tries a book converts with the names from its files.');
  assert.equal(listed[0].button.hidden,true,'several books: no button');assert.equal(listed[0].tip,'','line 2 is all there is: no tooltip');
  world(before());run('renderJobs()');listed=waits();
  assert.equal(listed[0].line1,'Waiting for an online answer: Тёмный лес');assert.equal(listed[0].line2,'Next try '+clock+'. After 3 tries a book converts with the names from its files.');
  assert.equal(listed[0].button.hidden,false);assert.equal(listed[0].button.textContent,'Show in list');
  assert.equal(listed[0].button.title,'List this book: sets Status to All and searches for its title.');assert.equal(listed[0].button.getAttribute('aria-label'),'Show in list: Тёмный лес');
  assert.equal(run('JSON.stringify(waitingItems.get("online_answer").target)'),'{"id":"cand-w","title":"Тёмный лес"}','the button lists that book');
  // One book the engine sends without a title: counted, and no button (there is nothing to search for).
  world(before({waiting:[{book_id:'cand-w',title:''}]}));run('renderJobs()');listed=waits();
  assert.equal(listed[0].line1,'Waiting for an online answer: 1 book');assert.equal(listed[0].button.hidden,true);
  // The limit and the time are the engine's: change the limit and the text follows; one try reads as one; no time, no
  // limit: each part is left out.
  world(before({limits:{per_source:5}}));run('renderJobs()');assert.equal(waits()[0].line2,'Next try '+clock+'. After 5 tries a book converts with the names from its files.');
  world(before({limits:{per_source:1}}));run('renderJobs()');assert.equal(waits()[0].line2,'Next try '+clock+'. After 1 try a book converts with the names from its files.');
  world(before({next_at:null}));run('renderJobs()');assert.equal(waits()[0].line2,'After 3 tries a book converts with the names from its files.');
  world(before({limits:null}));run('renderJobs()');assert.equal(waits()[0].line2,'Next try '+clock+'.');
  // It takes the place of 0.30.0's "Metadata sources" item for these books. Books that wait for something else keep that
  // item, counted without the online waits, so no book is counted twice.
  const sources=count=>({id:'metadata_sources',kind:'metadata_sources',count,at:AT*1000});
  const around=[{id:'conversions',kind:'conversions',count:2,subject:'Next'},null,{id:'drive:Z',kind:'drive',subject:'Z:\\Audiobooks'},{id:'automatic',kind:'automatic',label_key:'automatic_waiting'}];
  const order=()=>waits().map(item=>item.line1.split(':')[0]);
  world(several,{},{waiting:around.map(item=>item || sources(3)),lookups_waiting:[{id:'series_lookup',kind:'series_lookup',count:212,at:AT*1000}]});run('renderJobs()');
  assert.deepEqual(order(),['Waiting to convert','Waiting for an online answer','Finding series for finished audiobooks','Drive not answering','Automatic processing'],'in its place, and the old item is gone');
  world(several,{},{waiting:around.map(item=>item || sources(5))});run('renderJobs()');
  assert.deepEqual(order(),['Waiting to convert','Waiting for an online answer','Metadata sources','Drive not answering','Automatic processing']);
  assert.equal(waits()[2].line2,'2 books wait for a source to answer. Next try '+clock+'.','the drive and catalog waits only');
  world(several,{},{waiting:around.filter(Boolean)});run('renderJobs()');
  assert.deepEqual(order(),['Waiting to convert','Waiting for an online answer','Drive not answering','Automatic processing'],'no old item sent: the same place');
  // Control: with no online wait the 0.30.0 item is drawn as before.
  world(before({count:0,waiting:[],next_at:null}),{},{waiting:around.map(item=>item || sources(4))});run('renderJobs()');
  assert.deepEqual(order(),['Waiting to convert','Metadata sources','Drive not answering','Automatic processing']);assert.equal(waits()[1].line2,'4 books wait for a source to answer. Next try '+clock+'.');
  world(undefined,{},{waiting:around.map(item=>item || sources(4))});run('renderJobs()');assert.deepEqual(order(),['Waiting to convert','Metadata sources','Drive not answering','Automatic processing'],'an engine that sends no such fact');
  // Automatic processing stopped: nothing is waiting to run by itself, so there is no item.
  world(before({tries_continue:false}),{state:'Idle'});run('renderJobs()');assert.equal(waits().length,0);assert.equal(get('jobs-wait-block').hidden,true);

  // 5. The Automatic block's line (5.1): it replaces "Waiting for metadata sources; ..." and both of its endings while
  // books wait for an online source; with no time it stands alone; other waits keep the 0.30.0 line.
  world(before());run('renderAutomatic()');assert.equal(get('automatic-detail').textContent,'Waiting for an online answer. Next try '+clock+'.');
  world(before({next_at:null}));run('renderAutomatic()');assert.equal(get('automatic-detail').textContent,'Waiting for an online answer.');
  world(before({count:0,waiting:[],next_at:null}));run('renderAutomatic()');assert.match(get('automatic-detail').textContent,/^Waiting for metadata sources; saved research retries automatically\. Next automatic retry check: /);
  world(undefined);run('renderAutomatic()');assert.match(get('automatic-detail').textContent,/^Waiting for metadata sources; /);

  // 6. How the wait ends (5.2). No answer after the limit: the book converts under the names from its files, with one note
  // in the hint's place while it is Queued or Processing and nothing afterwards. The number is the engine's (the tries
  // made); the asked part follows what got no answer.
  world(before({count:0,waiting:[],next_at:null}),{state:'Running',phase:'conversion'});
  const ended=(fields,extra={})=>({asked:{title:'Тёмный лес',author:'Лю Цысинь',gaps:Object.keys(fields)},fields,tries:3,limit:3,next_at:null,waiting:false,ended:'',...extra});
  const after=(name,status,lookup,extra={})=>book(name,{status,creation:{status,can_create:false,reasons:[]},automatic:{state:'Queued',waits_for:null,reasons:[],sources:[],lookup},lookup,...extra});
  const unanswered=ended({original_title:'no_answer',series:'no_answer'});
  paint([after('q','Queued',unanswered),after('p','Converting',unanswered)]);
  assert.equal(statusCell(trOf('cand-q')).textContent,'Queued');assert.equal(hintOf(trOf('cand-q')),'No online answer about its English title and series after 3 tries.');
  assert.equal(statusCell(trOf('cand-p')).textContent,'Processing');assert.equal(hintOf(trOf('cand-p')),'No online answer about its English title and series after 3 tries.');
  paint([after('q','Queued',ended({original_title:'answered',series:'no_answer'}))]);assert.equal(hintOf(trOf('cand-q')),'No online answer about its series after 3 tries.','a title that was answered is not named');
  paint([after('q','Queued',ended({original_title:'no_answer',series:'nothing_found'}))]);assert.equal(hintOf(trOf('cand-q')),'No online answer about its English title after 3 tries.');
  paint([after('q','Queued',ended({original_title:'no_answer',series:'no_answer'},{tries:2,ended:'time'}))]);assert.equal(hintOf(trOf('cand-q')),'No online answer about its English title and series after 2 tries.','the tries made, as the engine counts them');
  paint([after('q','Queued',ended({series:'no_answer'},{tries:1,limit:1}))]);assert.equal(hintOf(trOf('cand-q')),'No online answer about its series after 1 try.');
  paint([after('q','Queued',ended({series:'no_answer'},{tries:0,limit:3}))]);assert.equal(hintOf(trOf('cand-q')),'No online answer about its series after 3 tries.','no try counted: the limit');
  paint([after('q','Queued',ended({series:'no_answer'},{tries:null,limit:null}))]);assert.equal(hintOf(trOf('cand-q')),'','no number sent: no note');
  // After that the row says nothing: a finished audiobook and a held book carry no note.
  paint([after('q','Completed',unanswered,{audiobook_ready:true}),after('h','Held',unanswered,{automatic:{state:'Held',reasons:['Possible duplicate recording'],sources:[],lookup:unanswered}})]);
  assert.equal(statusCell(trOf('cand-q')).textContent,'Audiobook Ready');assert.equal(hintOf(trOf('cand-q')),'');assert.equal(hintOf(trOf('cand-h')),'');
  // Answered, nothing found, and a doubtful answer (which arrives as nothing found): the row says nothing about the wait.
  for(const fields of [{original_title:'answered',series:'answered'},{original_title:'nothing_found',series:'nothing_found'},{}]){
    paint([after('q','Queued',ended(fields))]);assert.equal(statusCell(trOf('cand-q')).textContent,'Queued');assert.equal(hintOf(trOf('cand-q')),'',JSON.stringify(fields));
  }
  paint([after('q','Queued',null)]);assert.equal(hintOf(trOf('cand-q')),'','a book with no look-up record');

  // The details panel's facts. The fact is labelled "English title" (it was "Original title"). Answered: the title.
  // Nothing found and no answer are different sentences, never merged; a missing series gets a line only when it got no
  // answer; a doubtful answer shows nothing.
  const titled=state=>({original_title_lookup:state});
  shown=panel(after('q','Queued',ended({original_title:'answered',series:'answered'}),{metadata_facts:titled({state:'found',title:'The Dark Forest',provider:'wikidata',url:'https://www.wikidata.org/wiki/Q607112'})}));
  assert.equal(shown.facts['English title'],'The Dark Forest');assert.equal('Original title' in shown.facts,false);assert.equal(shown.hint,'');
  shown=panel(after('q','Queued',ended({original_title:'nothing_found',series:'nothing_found'}),{metadata_facts:titled({state:'none',title:''})}));
  assert.equal(shown.facts['English title'],'No English title found online. Filed under the Russian title.');assert.equal('Series' in shown.facts,false,'no line for a missing series');assert.equal(shown.hint,'');
  shown=panel(after('q','Queued',unanswered,{metadata_facts:{...titled({state:'no_answer',title:'',tries:3,limit:3}),gap_search:{lookup:unanswered}}}));
  assert.equal(shown.facts['English title'],'No online answer after 3 tries. Filed under the Russian title.');assert.equal(shown.facts.Series,'No online answer after 3 tries.');
  assert.equal(shown.hint,'No online answer about its English title and series after 3 tries.','the panel shows the row\'s note while it is Queued');
  shown=panel(after('q','Completed',ended({original_title:'no_answer',series:'no_answer'},{tries:1,limit:1}),{audiobook_ready:true,metadata_facts:titled({state:'no_answer',title:'',tries:1,limit:1})}));
  assert.equal(shown.facts['English title'],'No online answer after 1 try. Filed under the Russian title.');assert.equal(shown.facts.Series,'No online answer after 1 try.','read from the look-up record when the facts carry none');
  assert.equal(shown.hint,'','after it has converted the row says nothing; the facts stay');
  // A series the book has (found elsewhere, or typed by him) is never overwritten by the note.
  shown=panel(after('q','Queued',unanswered,{place:{series:'Remembrance of Earth\'s Past',number:'2',origin:'entered'},metadata_facts:titled({state:'no_answer',title:'',tries:3,limit:3})}));
  assert.equal('Series' in shown.facts,false);
  assert.equal(run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"entered",title:""}}})'),'Entered by you.');
  assert.equal(run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"no_answer",title:"",tries:null,limit:null}}})'),'','no number sent: no sentence');
  assert.equal(run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"russian",title:""}}})'),'','a Russian original has no such fact');
  assert.notEqual(run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"none"}}})'),run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"no_answer",tries:3}}})'),'never worded alike');

  // 7. No new control anywhere in this section, and no "Convert now" (Sergei's answers, Question 5).
  for(const text of [source,html])assert.doesNotMatch(text,/Convert now/i);
  for(const gone of ['Not found. Filed under the Russian title.',"values['Original title']"])assert.ok(!source.includes(gone),gone);
  console.log('PASS 0.31.0 waiting for an online answer: row status and both hints from the engine\'s numbers, drive and catalog waits unchanged, the Waiting item, the Automatic line, the four ends, the English title fact');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_online_wait_frontend.js'),module);m.filename=path.join(__dirname,'test_online_wait_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

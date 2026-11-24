'use strict';
// 0.29.0 items 1, 3 and 5 on the real frontend (Judy's 0.29.0 UX, sections 1 and 3), with the Retry test's DOM and
// transport doubles. No server, no library.
// - A library root that does not answer (or answers empty) gets one warning line under the Source lines, with its book
//   count and Check again; its books stay. Checking… while it checks; "still isn't available" when it still does not.
// - The check pass's removals: one line ("Removed 3 books whose files are gone. No files were touched." or, with folders,
//   "Deleted 2 source folders that held only leftover files."), Details (at most 10, then + N more) and Dismiss.
// - Rows whose problem no longer applies: the Needs attention strip says why, once, with Show it for one book.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const answers={};const posts=[];const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(answers[route]){posts.push({route,data});return answers[route](data);}
  return baseFetch(route,options);
};
const ok=(value,status=200)=>({ok:status<400,status,json:async()=>value});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const texts=element=>element.children.map(child=>child.children.length?child.children.map(item=>item.textContent).join(' | '):child.textContent);
(async()=>{
  const away={path:'Z:\\Audiobooks',available:false,empty:false,books:412};
  run('state='+JSON.stringify({...backend,library_roots:[away,{path:'Y:\\Books',available:true,empty:false,books:3}]})+';renderJobs()');
  assert.equal(get('library-notices').hidden,false);
  assert.deepEqual(texts(get('library-notices')),["Z:\\Audiobooks isn't available. Its 412 books stay on the list. Check that the drive is connected. | Check again"]);
  const button=get('library-notices').children[0].children[1];
  assert.equal(button.title,"Check whether Z:\\Audiobooks answers now. Nothing is removed while it doesn't.");
  // Empty answers read as a failed mount; an unknown count says "Its books".
  run('state={...state,library_roots:[{path:"Z:\\\\Audiobooks",available:true,empty:true,books:0}]};renderJobs()');
  assert.deepEqual(texts(get('library-notices')),["Z:\\Audiobooks answers but is empty. Its books stay on the list. Check that the drive is connected. | Check again"]);
  // Check again: Checking… (button inert), then "still isn't available" when it still does not answer.
  let answer;answers['/api/sources/check']=()=>new Promise(resolve=>{answer=resolve;});
  run('state={...state,library_roots:['+JSON.stringify(away)+']};renderJobs()');
  const checking=get('library-notices').children[0].children[1].handlers.click();
  assert.equal(get('library-notices').children[0].children[0].textContent,'Checking Z:\\Audiobooks…');
  assert.equal(get('library-notices').children[0].children[1].getAttribute('aria-disabled'),'true');
  answer(ok({source_check:{roots:[away]},checking:false}));await checking;await tick();
  assert.equal(get('library-notices').children[0].children[0].textContent,"Z:\\Audiobooks still isn't available. Its 412 books stay on the list.");
  assert.equal(posts.filter(p=>p.route==='/api/sources/check').length,1);
  // It answers again: the line goes at once (no "available again" line).
  run('state={...state,library_roots:[{path:"Z:\\\\Audiobooks",available:true,empty:false,books:412}]};renderJobs()');
  assert.equal(get('library-notices').hidden,true);
  // More than 3 roots away: three lines, then +N more with the full list in its title.
  const many=[1,2,3,4,5].map(n=>({path:'R'+n+':\\Books',available:false,empty:false,books:n}));
  run('state={...state,library_roots:'+JSON.stringify(many)+'};renderJobs()');
  assert.equal(get('library-notices').children.length,4);assert.equal(get('library-notices').children[3].textContent,'+2 more');
  assert.match(get('library-notices').children[3].title,/R4:\\Books isn't available/);
  run('state={...state,library_roots:[]};renderJobs()');
  // The removed line: books only, then with folders; Details lists them; Dismiss hides it.
  run('state={...state,source_check:{removed:3,removed_list:[{id:"a",title:"Абсолютное зеро",path:"Z:\\\\Audiobooks\\\\Unsorted\\\\Сборник"}],removed_more:0,folders:0,folder_list:[],folders_more:0,cleared:[]}};renderJobs()');
  assert.equal(get('source-removed').hidden,false);
  assert.equal(get('source-removed-line').textContent,'Removed 3 books whose files are gone. No files were touched.');
  run('state={...state,source_check:{...state.source_check,folders:2,folder_list:[{path:"Z:\\\\Audiobooks\\\\A",files:["cover.jpg"]}],removed_more:12}};renderJobs()');
  assert.equal(get('source-removed-line').textContent,'Removed 3 books whose files are gone. Deleted 2 source folders that held only leftover files.');
  assert.doesNotMatch(get('source-removed-line').textContent,/No files were touched/,'never printed when a folder was deleted');
  run('globalThis.kept=sourceRemovedText({removed:2,folders:0,files_removed:1})');assert.equal(run('kept'),'Removed 2 books whose files are gone.','Senua S-m7: nor when leftover files went from a folder that stayed');
  assert.equal(run('sourceRemovedText({removed:2,folders:0,files_removed:0})'),'Removed 2 books whose files are gone. No files were touched.');
  get('source-details').handlers.click();
  assert.deepEqual(get('source-details-list').children.map(item=>item.textContent),['Абсолютное зеро — Z:\\Audiobooks\\Unsorted\\Сборник','+ 12 more','Z:\\Audiobooks\\A — cover.jpg']);
  answers['/api/sources/dismiss']=()=>ok({source_check:{removed:0,folders:0,cleared:[]}});
  await get('source-dismiss').handlers.click();await tick();
  assert.equal(get('source-removed').hidden,true);
  // Item 3: in the Needs attention view, one cleared Name taken row says why, with Show it; several share one line.
  run('view="candidates";filters.candidates="output_attention";state={...state,source_check:{removed:0,folders:0,cleared:[{id:"n2",title:"Неисповедимый путь 2",cause:"name_taken"}]}};renderJobs()');
  assert.equal(run('stripNote'),'«Неисповедимый путь 2» left this list: the name is free now. The book is checked again.');
  assert.equal(run('stripShow.id'),'n2');
  run('state={...state,source_check:{removed:0,folders:0,cleared:[{id:"x1",title:"A",cause:"other"},{id:"x2",title:"B",cause:"other"},{id:"x3",title:"C",cause:"name_taken"}]}};renderJobs()');
  assert.equal(run('stripNote'),'3 books left this list: their problem no longer applies. They are checked again.');
  run('stripNote="kept";renderJobs()');assert.equal(run('stripNote'),'kept','said once, never repeated on every poll');
  // Never under his cursor: a cleared row whose Edit names editor is open stays in place with its line, and goes after.
  run('state={...state,source_check:{removed:0,folders:0,cleared:[{id:"n2",title:"Неисповедимый путь 2",cause:"name_taken"}]}}');
  run('namesState.set("n2",{open:true,draft:{},data:null})');
  run('globalThis.kept=keepUnderCursor([{id:"a"},{id:"c"}],[{id:"a"},{id:"n2",title_clue:"Неисповедимый путь 2"},{id:"c"}])');
  assert.equal(run('kept.map(row=>row.id).join(",")'),'a,n2,c','the row stays where it was');
  assert.equal(run('candidateStatus(kept[1])'),'The name is free now. This row leaves the list when you close this editor.');
  run('namesState.delete("n2")');
  assert.equal(run('keepUnderCursor([{id:"a"},{id:"c"}],kept).map(row=>row.id).join(",")'),'a,c','it leaves once the editor is closed');
  assert.equal(run('keepUnderCursor([{id:"a"}],[{id:"a"},{id:"b"}]).map(row=>row.id).join(",")'),'a','a row nobody works on leaves at once');
  // Item 7 extras (Judy section 7), 0.30.0 from the engine's work rows: the check pass row (after 1 s), its folder phase, a
  // move, a queued action, a stall.
  const view=id=>run('activityRows.get("'+id+'")'),line=id=>[view(id).label.textContent,view(id).subject.textContent,view(id).detail.textContent,view(id).step.textContent];
  const work=rows=>run('state={...state,work:'+JSON.stringify({rows,waiting:[],counts:{},unread:[]})+'};renderJobs()');
  run('rows=[];queueState={queued:[],running:null}');work([{id:'source_check',kind:'source_check',state:'running',done:1,total:412,unit:'books',started:Date.now()}]);
  assert.equal(view('source_check'),undefined,'a pass under 1 s is not shown');
  work([{id:'source_check',kind:'source_check',state:'running',done:120,total:412,unit:'books',started:Date.now()-5000}]);
  assert.deepEqual(line('source_check'),['Checking source folders','','120 of 412 books','Checking 412 books']);
  assert.match(get('jobs-status-text').textContent,/^Checking source folders · /);
  work([{id:'source_folders',kind:'source_folders',state:'running',started:Date.now()-2000}]);
  assert.deepEqual(line('source_folders'),['Removing source folders','','','Checking leftovers']);assert.equal(view('source_folders').bar.hidden,false);
  run('rows=[{id:"m",kind:"candidate",title_clue:"Dune",move:{state:"moving",progress:45,target:"Z:/Sorted/Herbert/Dune.m4b"}}]');
  work([{id:'move:q1',kind:'move',subject:'Dune',book_id:'m',state:'running',done:45,total:100,unit:'percent',fraction:0.45,started:Date.now()-2000}]);
  assert.deepEqual(line('move:q1'),['Moving: ','Dune','45%','Copying to Herbert']);
  run('updateActivity(activityRows.get("move:q1"),Date.now()+301000)');
  assert.equal(view('move:q1').step.textContent,'No progress for 5 min','a running row whose detail has not moved for 5 min says so');
  run('rows=[{id:"b",kind:"candidate",title_clue:"Foo"}];queueState={queued:[],running:{id:"q",book_id:"b",action:"cleanup",title:"Foo"}}');
  work([{id:'action:q',kind:'action',label_key:'cleanup',subject:'Foo',book_id:'b',state:'running',started:Date.now()-2000}]);
  assert.deepEqual(line('action:q').slice(0,2),['Retry cleanup: ','Foo']);
  // One row per piece of work: the engine sends one row for it, the page draws what it sends.
  work([{id:'cleanup:j',kind:'cleanup',subject:'Foo',job_id:'j',step:'originals',state:'running',done:1,total:4,unit:'files',started:Date.now()-2000}]);
  assert.equal(view('action:q'),undefined);assert.equal(view('cleanup:j').subject.textContent,'Foo');
  run('queueState={queued:[],running:null};rows=[]');work([]);
  // The counts keep a leaving row until it leaves the page.
  run('leavingRows.set("n9",{id:"n9",leaving:"name_free"});globalThis.counted={audiobook_jobs:{attention_counts:{name_taken:2}}};leavingCounts(counted)');
  assert.equal(run('counted.audiobook_jobs.attention_counts.name_taken'),3);
  run('leavingRows.delete("n9")');
  // Futaba M-4: a Name taken row open in Edit names when its name becomes free.
  run('stripNote="";leavingRows.clear();view="candidates";filters.candidates="output_attention"');
  const listed=()=>run('rows.map(row=>row.id).join(",")');
  run('globalThis.plain={id:"a",path:"a",kind:"candidate",title_clue:"A",members:[]};rows=[plain,{id:"n3",path:"n3",kind:"candidate",title_clue:"Книга Тета",members:[],ask:{kind:"name_taken",fields:{title:{proposal:"Книга Тета"},author:{proposal:"Волкова Ольга"}},destination:{path:"X",taken:true}}}]');
  assert.match(run('askInert(rows[1])'),/already in Audiobooks Sorted/,'positive control: the Name taken refusal before the name is free');
  run('namesState.set("n3",{open:true,draft:{},data:{fields:{}},openDraft:{names:{},ask:null}})');
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,attention_counts:{name_taken:1}},source_check:{removed:0,folders:0,cleared:[{id:"n3",title:"Книга Тета",cause:"name_taken"}]}};renderJobs()');
  assert.doesNotMatch(run('stripNote'),/left this list/,'(b) the strip waits while the row is still on the page');
  run('rows=keepUnderCursor([plain],rows)');assert.equal(listed(),'a,n3','the list read keeps it while the editor is open');
  const kept=()=>run('rows.find(row=>row.id==="n3")');
  assert.doesNotMatch(run('askInert(rows.find(row=>row.id==="n3"))'),/already in Audiobooks Sorted/,'(a) the stale Name taken refusal is gone');
  assert.doesNotMatch(run('approveBlock(rows.find(row=>row.id==="n3")).text'),/already in Audiobooks Sorted/);
  // A later pass replaces source_check.cleared: the row keeps its cause, its line and its count (it read "gone" before).
  run('state={...state,source_check:{...state.source_check,cleared:[]}};rows=keepUnderCursor([plain],rows)');
  assert.equal(kept().leaving,'name_free');assert.equal(run('candidateStatus(rows.find(row=>row.id==="n3"))'),'The name is free now. This row leaves the list when you close this editor.');
  // (c) Discard: the row leaves at once, the counts drop with it, and the strip says why.
  run('namesClose("n3")');
  assert.equal(listed(),'a','it leaves the moment the editor closes, not at a later list read');
  assert.equal(run('state.audiobook_jobs.attention_counts.name_taken'),0,'the count drops with the row');
  assert.equal(run('leavingRows.has("n3")'),false);
  assert.equal(run('stripNote'),'«Книга Тета» left this list: the name is free now. The book is checked again.');
  // A closed editor whose proposals merely differ from the row's question is not his work: nothing holds the row.
  run('namesState.set("n4",{open:false,draft:{},data:{fields:{title:{proposal:"Иное"}}}})');
  assert.equal(run('underCursor({id:"n4",title_clue:"Другое",members:[]})'),false);
  run('namesState.set("n4",{open:false,draft:{title:"Моё"},data:{fields:{title:{proposal:"Иное"}}}})');
  assert.equal(run('underCursor({id:"n4",title_clue:"Другое",members:[]})'),true,'positive control: a typed draft holds it');
  run('namesState.delete("n4");namesState.delete("n3")');
  // Futaba N-1: a real Author unclear row, rendered by the page in its default state (its best-guess radio preselected,
  // nothing typed, no editor), is nobody's work: a chip change or a gone book drops it from the page at once.
  run('stripNote="";leavingRows.clear();sourceClearedWaiting.clear();askDrafts.clear();askRows.clear();view="candidates";filters.candidates="output_attention";attentionGroup="all"');
  globalThis.unclear={id:'au1',path:'au1',kind:'candidate',library:'Audiobooks',revision:1,fingerprint:'b'.repeat(64),scope:'private fixture',preview:{path:''},metadata:{tags:{}},title_clue:'Тайна дома',artists:[],members:[{path:'X:\\private\\au1.mp3'}],review:{},review_context:{},status:'Held',creation:{status:'Held',can_create:false,reasons:[]},automatic:{state:'Held'},source_directory_count:1,
    place:{series:'',number:'',universe:'',collection:false},ask:{kind:'author_unclear',why:'two_people',fields:{title:{proposal:'Тайна дома',basis:'tag'},author:{proposal:'Толстой Лев',basis:'tag'}},candidates:[{name:'Толстой Лев'},{name:'Чехов Антон'}],destination:{path:'Толстой Лев\\Тайна дома.m4b'}}};
  context.unclear=globalThis.unclear;context.taken={id:'nt1',path:'nt1',kind:'candidate',title_clue:'Книга НТ',members:[]};
  run('rows=[unclear,taken];renderRows(true)');
  assert.equal(run('askDraft("au1").choice'),'c0','positive control: rendering preselected the best guess, as on the page');
  assert.equal(run('underCursor(rows[0])'),false,'an untouched Author unclear row is not his work');
  // A chip change (Name taken) or a scan that found the book gone: the next list read does not have the row.
  inventoryRows=[context.taken];
  await run('loadList(listContext(),"Audiobooks","candidates","output_attention",0,"",retryEpoch,true)');
  assert.equal(listed(),'nt1','the untouched row left the page with the list read');
  assert.equal(run('leavingRows.has("au1")'),false);
  assert.equal(get('inventory').children.some(tr=>JSON.stringify(tr.children.map(td=>td.textContent)).includes('leaves the list when you close')),false,'no "leaves the list" line without an editor');
  // Positive control: his own choice of another author is his work; the row stays, in place, with its line.
  inventoryRows=[context.unclear,context.taken];
  await run('loadList(listContext(),"Audiobooks","candidates","output_attention",0,"",retryEpoch,true)');
  const radio=value=>run('askRows.get("au1").controls').find(c=>c.type==='radio' && c.value===value);
  radio('c1').checked=true;radio('c1').handlers.change();
  assert.equal(run('underCursor(rows.find(row=>row.id==="au1"))'),true,'a different author picked is unsaved work');
  inventoryRows=[context.taken];
  await run('loadList(listContext(),"Audiobooks","candidates","output_attention",0,"",retryEpoch,true)');
  assert.equal(listed(),'au1,nt1','his picked row stays where it was');
  assert.equal(run('candidateStatus(rows[0])'),'This row leaves the list when you close this editor.');
  // Back to the preselected author: nothing differs from the row's own proposal, so it goes with the next read.
  radio('c0').checked=true;radio('c0').handlers.change();
  assert.equal(run('underCursor(rows[0])'),false,'the preselected author picked again is no edit');
  await run('loadList(listContext(),"Audiobooks","candidates","output_attention",0,"",retryEpoch,true)');
  assert.equal(listed(),'nt1');
  run('askDrafts.clear();askRows.clear();leavingRows.clear();rows=[]');inventoryRows=[];
  console.log('PASS 0.29.0 source check on the page: drive lines with Check again, the removed line with Details and Dismiss, cleared rows in the strip');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_source_check_frontend.js'),module);m.filename=path.join(__dirname,'test_source_check_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

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
  // Item 7 extras (Judy section 7): the check pass row (after 1 s), its folder phase, a move, a queued action, a stall.
  const view=kind=>run('activityRows.get("'+kind+'")'),line=kind=>[view(kind).label.textContent,view(kind).subject.textContent,view(kind).detail.textContent,view(kind).step.textContent];
  run('rows=[];queueState={queued:[],running:null};state={...state,source_check:null,source_check_progress:{phase:"checking",done:1,total:412,started:Date.now()}};renderJobs()');
  assert.equal(view('checks'),undefined,'a pass under 1 s is not shown');
  run('state={...state,source_check_progress:{phase:"checking",done:120,total:412,started:Date.now()-5000}};renderJobs()');
  assert.deepEqual(line('checks'),['Checking source folders','','120 of 412 books','Checking 412 books']);
  assert.match(get('jobs-status').textContent,/^Checking source folders · /);
  run('state={...state,source_check_progress:{phase:"folders",started:Date.now()}};renderJobs()');
  assert.deepEqual(line('sources'),['Removing source folders','','','Checking leftovers']);assert.equal(view('sources').bar.hidden,false);
  run('state={...state,source_check_progress:null};rows=[{id:"m",kind:"candidate",title_clue:"Dune",move:{state:"moving",progress:45,target:"Z:/Sorted/Herbert/Dune.m4b"}}];renderJobs()');
  assert.deepEqual(line('move'),['Moving: ','Dune','45%','Copying to Herbert']);
  run('updateActivity(activityRows.get("move"),Date.now()+301000)');
  assert.equal(view('move').step.textContent,'No progress for 5 min','a running row whose detail has not moved for 5 min says so');
  run('rows=[{id:"b",kind:"candidate",title_clue:"Foo"}];queueState={queued:[],running:{id:"q",book_id:"b",action:"cleanup"}};renderJobs()');
  assert.deepEqual(line('action').slice(0,2),['Retry cleanup: ','Foo']);
  // One row per piece of work: while the engine shows the cleanup itself, the queued Retry cleanup is not a second row.
  run('state={...state,activities:[{id:"cleanup",kind:"cleanup",subject:"Foo",step:"originals",state:"running",done:1,total:4,unit:"files"}]};renderJobs()');
  assert.equal(view('action'),undefined);assert.equal(view('cleanup').subject.textContent,'Foo');
  run('state={...state,activities:[]};queueState={queued:[],running:null};rows=[];renderJobs()');
  // The counts keep a leaving row until it leaves the page.
  run('leavingRows.set("n9",{id:"n9",leaving:"name_free"});globalThis.counted={audiobook_jobs:{attention_counts:{name_taken:2}}};leavingCounts(counted)');
  assert.equal(run('counted.audiobook_jobs.attention_counts.name_taken'),3);
  run('leavingRows.delete("n9")');
  console.log('PASS 0.29.0 source check on the page: drive lines with Check again, the removed line with Details and Dismiss, cleared rows in the strip');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_source_check_frontend.js'),module);m.filename=path.join(__dirname,'test_source_check_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

'use strict';
// Delete book (Sergei's ruling 23, 2026-10-25; Judy's "Delete book - spec" in Docs/BooksArranger_AttentionTodo_UX_2026-10-24.md):
// the button only with the server's typed offer, last in the row on its own line with its tooltip; the dialog lists the
// files, Cancel has focus and Enter in the body confirms nothing; the confirm sends exactly the paths shown; success,
// partial failure, a typed refusal and a lost connection each say what happened. Real frontend on the Retry test's
// DOM/transport doubles. No server, no library, no file is deleted.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted',FOLDER='Z:\\Audiobooks\\Сборники\\Новая плоть (2016)';
function askRow(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:['Иван Петров'],members:[{path:FOLDER+'\\01.m4b'},{path:FOLDER+'\\02.m4b'},{path:FOLDER+'\\03.m4b',missing:true}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['Files missing']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const missing=(name,offer)=>askRow(name,{kind:'files_missing',also:null,why:'',reasons:['Files missing'],fields:{title:{proposal:'Новая плоть',basis:'tag'},author:{proposal:'Иван Петров',basis:'tag'}},candidates:[],
  missing:{folders:[FOLDER],files:[FOLDER+'\\03.m4b'],present:2,total:3},destination:{path:'Петров Иван\\Новая плоть - Петров Иван.m4b',absolute:'',taken:false,reason:''},...(offer?{delete:offer}:{})});
function attentionRow(name,group,attention={}){
  return blocked({id:'cand-'+name,path:'cand-'+name,title_clue:'Title '+name,review:{title:'Title '+name}},{job_id:'job-'+name,reason:'raw reason '+name,attention:{group,cause:null,originals_untouched:true,...attention}});
}
const reacquire=attentionRow('r','reacquire',{reacquire:{state:'required',certainty:'measured',reason:'Measured damaged audio',repair_limit:'Cannot preserve speech',originals:[{path:'Z:/shared/one.mp3'}],source_presence:'present'},delete:{kind:'audio_damaged',present:1}});
const canRetry=attentionRow('c','retry',{});
let previewAnswer=null,deleteAnswer=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/candidate/delete-preview'){calls.push({route,options});return previewAnswer(data);}
  if(route==='/api/candidate/delete'){calls.push({route,options});return deleteAnswer(data);}
  return baseFetch(route,options);
};
const ok=value=>({ok:true,status:200,json:async()=>value});
const posted=route=>calls.filter(call=>call.route===route).map(call=>JSON.parse(call.options.body));
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
const deleteButton=tr=>buttonsOf(tr).find(b=>b.textContent==='Delete book' || b.textContent==='Checking...');
const hint=tr=>{const h=statusCell(tr).children[0];return h.textContent+(h.children || []).map(s=>s.textContent).join('');};
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
const FILES=[{path:FOLDER+'\\01.m4b',size:700*1024*1024},{path:FOLDER+'\\02.m4b',size:700*1024*1024}];
(async()=>{
  backend={...backend,audiobook_output_root:ROOT};
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  paint([missing('m',{kind:'files_missing',present:2}),missing('n',null),reacquire,canRetry,missing('z',{kind:'files_missing',present:0})]);
  // 1. Only rows with the server's offer, last in the row behind a line break, with its tooltip and name.
  let tr=trOf('cand-m');const buttons=buttonsOf(tr),del=buttons.at(-1);
  assert.equal(del.textContent,'Delete book');assert.ok(del.className.includes('danger'));assert.equal(buttons.at(-2).className,'row-break');
  assert.ok(buttons.indexOf(buttons.find(b=>b.textContent==='View metadata'))<buttons.indexOf(del),'after View metadata and the folder buttons');
  assert.equal(del.title,"Delete this book's files from disk and remove the book from the app. You confirm first.");
  assert.equal(del.getAttribute('aria-label'),'Delete book: Title m');
  assert.equal(deleteButton(trOf('cand-n')),undefined,'no offer, no button');
  assert.equal(deleteButton(trOf('cand-c')),undefined,'Can retry: the app can still fix it');
  assert.equal(deleteButton(trOf('cand-r')).title,"Delete this book's files from disk and remove the book from the app. You confirm first.",'Need to reacquire');
  assert.equal(deleteButton(trOf('cand-z')).title,'Remove this book from the app for good. No files are left to delete. You confirm first.');
  assert.equal(run('attentionText(rows.find(row=>row.id==="cand-r")).hint'),'The audio is damaged and cannot be repaired safely. Delete the book, then get a new copy.','section 7');
  // 2. The press reads the list; the dialog opens with Cancel focused; Enter in the body or list confirms nothing; Cancel closes.
  previewAnswer=()=>ok({files:FILES,bytes:1400*1024*1024,refusal:null,kind:'files_missing'});
  await del.handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/candidate/delete-preview').at(-1),{library:'Audiobooks',id:'cand-m',revision:2});
  assert.equal(get('delete-dialog-title').textContent,'Delete this book?');assert.equal(document.activeElement,get('delete-cancel'),'Cancel has focus');
  assert.equal(get('delete-dialog-book').textContent,'Новая плоть — Иван Петров');assert.equal(get('delete-dialog-reason').textContent,'1 of 3 files is missing.');
  assert.match(get('delete-dialog-files').textContent,/^These 2 files \(1[.,]4 GB\) will be deleted from your disk\. The app can't undo this\.$/);
  assert.deepEqual(get('delete-dialog-list').children.map(p=>p.textContent),FILES.map(f=>f.path));
  assert.equal(get('delete-dialog-folder').hidden,false);
  assert.equal(get('delete-dialog-forget').textContent,"The app forgets this book. If you get it again, it's found as a new book. Nothing in Audiobooks Sorted is touched.");
  assert.equal(get('delete-confirm').textContent,'Delete book and 2 files');assert.equal(get('delete-confirm').title,"Delete this book and its 2 files. The app can't undo this.");
  let prevented=false;get('delete-dialog').handlers.keydown({key:'Enter',target:get('delete-dialog-list'),preventDefault(){prevented=true;}});
  assert.ok(prevented,'Enter in the list does nothing');assert.equal(posted('/api/candidate/delete').length,0);
  await get('delete-cancel').handlers.click({});assert.equal(run('deleteDialog'),null);assert.equal(document.activeElement,deleteButton(trOf('cand-m')),'focus back on Delete book');
  assert.equal(posted('/api/candidate/delete').length,0,'Cancel deletes nothing');
  // 3. Confirm: a repeated key press is ignored; the confirm sends exactly the paths shown; success says what went.
  await deleteButton(trOf('cand-m')).handlers.click({stopPropagation(){}});await tick();
  await get('delete-confirm').handlers.click({repeat:true});assert.equal(posted('/api/candidate/delete').length,0,'a held Enter confirms nothing');
  deleteAnswer=()=>ok({deleted:2,bytes:1400*1024*1024,failed:[],forgotten:true});
  await get('delete-confirm').handlers.click({});await tick();
  assert.deepEqual(posted('/api/candidate/delete').at(-1),{library:'Audiobooks',id:'cand-m',revision:2,paths:FILES.map(f=>f.path)});
  assert.equal(run('deleteDialog'),null,'closed on success');
  assert.match(get('retry-all-status').textContent,/^Deleted 1 book and 2 files \(1[.,]4 GB\)\.$/);
  assert.equal(run('deleteNotes.get("cand-m").text'),'Deleted. The book is gone from the app.');await tick();
  assert.equal(trOf('cand-m'),undefined,'the row leaves at the answer (the list is read again)');
  // 4. Partial failure: the dialog names each file and why; the row keeps the book.
  deleteAnswer=()=>ok({deleted:1,bytes:5,failed:[{path:FOLDER+'\\02.m4b',cause:'in_use',detail:'[WinError 32] ...'}],forgotten:false});
  paint([missing('p',{kind:'files_missing',present:2})]);
  await deleteButton(trOf('cand-p')).handlers.click({stopPropagation(){}});await tick();await get('delete-confirm').handlers.click({});await tick();
  assert.equal(get('delete-dialog-title').textContent,'Not everything was deleted');assert.equal(get('delete-dialog-files').textContent,'Deleted 1 of 2 files. 1 could not be deleted:');
  assert.deepEqual(get('delete-dialog-list').children.map(p=>p.textContent),[FOLDER+'\\02.m4b','In use by another program.']);
  assert.equal(get('delete-dialog-status').textContent,'The book stays listed. Press Delete book to try these again.');
  assert.equal(document.activeElement,get('delete-close'));assert.ok(!JSON.stringify(get('delete-dialog-list').children.map(p=>p.textContent)).includes('WinError'),'raw text never shown');
  await get('delete-close').handlers.click({});
  assert.equal(hint(trOf('cand-p')),'Deleted 1 of 2 files. 1 is still on disk.');
  assert.equal(get('retry-all-status').textContent,'Deleted 1 of 2 files. The book stays listed with the 1 that could not be deleted.');
  // 5. A refusal found by the preview opens the dialog in its refusal state: nothing to confirm.
  previewAnswer=()=>ok({files:[],bytes:0,refusal:{code:'shared',files:[{path:FOLDER+'\\01.m4b',other:'Другая книга'}]}});
  await deleteButton(trOf('cand-p')).handlers.click({stopPropagation(){}});await tick();
  assert.equal(get('delete-dialog-title').textContent,"Can't delete this book");
  assert.equal(get('delete-dialog-files').textContent,'"'+FOLDER+'\\01.m4b" also belongs to "Другая книга". Nothing was deleted.');
  assert.equal(get('delete-confirm').hidden,true);assert.equal(document.activeElement,get('delete-close'));await get('delete-close').handlers.click({});
  // 6. A typed refusal at the confirm, and a lost connection: the second never says "Nothing was deleted".
  previewAnswer=()=>ok({files:FILES,bytes:10,refusal:null});
  deleteAnswer=()=>({ok:false,status:409,json:async()=>({error:'x',code:'files_changed'})});
  await deleteButton(trOf('cand-p')).handlers.click({stopPropagation(){}});await tick();await get('delete-confirm').handlers.click({});await tick();
  assert.equal(get('delete-dialog-files').textContent,"The folder doesn't match the list, so nothing was deleted. Press Delete book to see the current list.");await get('delete-close').handlers.click({});
  deleteAnswer=()=>{throw new TypeError('Failed to fetch');};
  await deleteButton(trOf('cand-p')).handlers.click({stopPropagation(){}});await tick();await get('delete-confirm').handlers.click({});await tick();
  assert.equal(get('delete-dialog-title').textContent,'Delete may not have finished');
  assert.equal(get('delete-dialog-files').textContent,'Connection interrupted, so the delete may have gone through. Check the list before trying again.');
  assert.doesNotMatch(get('delete-dialog-files').textContent,/Nothing was deleted/);
  console.log('PASS Delete book: offer-only button, last with its tooltip, dialog with Cancel focused, Enter confirms nothing, exact paths, success, partial, refusals, lost connection');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_delete_frontend.js'),module);m.filename=path.join(__dirname,'test_delete_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

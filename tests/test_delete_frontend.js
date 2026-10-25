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
  assert.equal(get('delete-dialog-folder').hidden,true,'audio only and nothing stays: no stay line (update spec 2.2)');
  assert.equal(get('delete-dialog-last').hidden,true);assert.equal(get('delete-dialog-sorted').hidden,true);
  assert.ok(get('delete-dialog-list').children.every(p=>p.className!=='delete-group'),'audio only: no subheads, as before');
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
  assert.deepEqual(posted('/api/candidate/delete').at(-1),{library:'Audiobooks',id:'cand-m',revision:2,paths:FILES.map(f=>f.path),folders:[]});
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
  // Futaba's 0.22.0 QA, m-11: after a partial delete, Scan again on the row shows its result line (spec check 12).
  await buttonsOf(trOf('cand-p')).find(b=>b.textContent==='Scan again').handlers.click({stopPropagation(){}});await tick();
  assert.match(hint(trOf('cand-p')),/Checked \d\d:\d\d\. Not found\.$/);
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
  await get('delete-close').handlers.click({});
  run('recoveryDisconnected=false;controls()');  // the connection is back (the lost one above set it, as a failed poll does)
  // Futaba's 0.22.0 QA, m-10: after a successful Delete with other rows left, focus goes to the next row's first working
  // control (the list is read again; here it holds the next row only), not to the page.
  previewAnswer=()=>ok({files:FILES,bytes:10,refusal:null});deleteAnswer=()=>ok({deleted:2,bytes:10,failed:[],forgotten:true,folders:{removed:0,stayed:0}});
  paint([missing('f1',{kind:'files_missing',present:2}),missing('f2',{kind:'files_missing',present:2})]);
  inventoryOverride=()=>({ok:true,json:async()=>({rows:[missing('f2',{kind:'files_missing',present:2})],total:1})});
  await deleteButton(trOf('cand-f1')).handlers.click({stopPropagation(){}});await tick();await get('delete-confirm').handlers.click({});await tick();await tick();
  assert.equal(trOf('cand-f1'),undefined);assert.ok(trOf('cand-f2').contains(document.activeElement),'focus is on the next row');
  inventoryOverride=null;
  // Futaba's m-3: every Stopped row shows its Goes to line (Judy's to-do spec 1.6 and section 4), from its job.
  const going=blocked({id:'cand-d',path:'cand-d',title_clue:'Title d',review:{title:'Title d'}},{job_id:'job-d',reason:'x',destination:{path:'Иван Петров\\Железный ад.m4b',absolute:ROOT+'\\Иван Петров\\Железный ад.m4b'},attention:{group:'retry',cause:null,originals_untouched:true}});
  paint([going,canRetry]);
  const line=tr=>{const found=[];const walk=e=>{for(const c of e.children || []){if(c.className==='goes-to')found.push(c);walk(c);}};walk(statusCell(tr));return found;};
  assert.deepEqual(line(trOf('cand-d')).map(l=>l.children.map(c=>c.textContent)),[['Goes to','Audiobooks Sorted\\Иван Петров\\Железный ад.m4b']]);
  assert.equal(line(trOf('cand-d'))[0].title,ROOT+'\\Иван Петров\\Железный ад.m4b');
  assert.deepEqual(line(trOf('cand-c')),[],'no destination from the server: no line');
  // 7. Rulings 24 and 26 (Judy's update spec 2.2, 2.3): labelled groups in order, the folders, the stay line, the
  // last-copy line; the confirm sends the folders shown; the strip names the folders removed and those that stayed.
  const WORK='C:\\Books\\data\\audio-staging\\job\\attempt\\source00000.m4b';
  previewAnswer=()=>ok({files:[{path:FOLDER+'\\02.m4b',size:10,kind:'audio'},{path:FOLDER+'\\cover.jpg',size:5,kind:'other'},{path:WORK,size:10,kind:'working'},{path:FOLDER+'\\01.m4b',size:10,kind:'audio'}],
    bytes:35,folders:[FOLDER],stay:{items:2},last_copy:'some',refusal:null,kind:'files_missing'});
  paint([missing('g',{kind:'files_missing',present:4}),missing('h',{kind:'files_missing',present:4})]);
  await deleteButton(trOf('cand-g')).handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(get('delete-dialog-list').children.map(p=>p.textContent),['Audio files (2)',FOLDER+'\\01.m4b',FOLDER+'\\02.m4b',"Other files in this book's folder (1)",FOLDER+'\\cover.jpg',
    "The app's working files (1)",WORK,'Folders left empty are removed (1)',FOLDER]);
  assert.deepEqual(get('delete-dialog-list').children.filter(p=>p.className==='delete-group').length,4,'four subheads');
  assert.equal(get('delete-dialog-list').getAttribute('aria-label'),'Files and folders to delete');
  assert.equal(get('delete-dialog-last').hidden,false);assert.equal(get('delete-dialog-last').textContent,"Some originals are already gone. The app's working files hold the last copy of that audio.");
  assert.equal(get('delete-dialog-folder').hidden,false);assert.equal(get('delete-dialog-folder').textContent,"2 other items stay where they are. They belong to other books, or the app can't tell whose they are.");
  assert.match(get('delete-dialog-files').textContent,/^These 4 files \(.+\) will be deleted from your disk\. The app can't undo this\.$/,'every file counts, folders do not');
  assert.equal(get('delete-confirm').textContent,'Delete book and 4 files');
  deleteAnswer=()=>ok({deleted:4,bytes:35,failed:[],forgotten:true,folders:{removed:1,stayed:0}});
  await get('delete-confirm').handlers.click({});await tick();
  assert.deepEqual(posted('/api/candidate/delete').at(-1).folders,[FOLDER]);
  assert.match(get('retry-all-status').textContent,/^Deleted 1 book, 4 files \(.+\) and 1 folder\.$/);
  paint([missing('h',{kind:'files_missing',present:4})]);await deleteButton(trOf('cand-h')).handlers.click({stopPropagation(){}});await tick();
  deleteAnswer=()=>ok({deleted:4,bytes:35,failed:[],forgotten:true,folders:{removed:0,stayed:1}});
  await get('delete-confirm').handlers.click({});await tick();
  assert.match(get('retry-all-status').textContent,/^Deleted 1 book and 4 files \(.+\)\. 1 folder stayed\.$/,'a folder that stayed never keeps the book');
  // The last copy, all originals gone: the line says so; a stay of one item is singular.
  previewAnswer=()=>ok({files:[{path:WORK,size:10,kind:'working'}],bytes:10,folders:[],stay:{items:1},last_copy:'all',refusal:null,kind:'audio_damaged'});
  paint([reacquire]);await deleteButton(trOf('cand-r')).handlers.click({stopPropagation(){}});await tick();
  assert.equal(get('delete-dialog-last').textContent,"The originals are already gone. The app's working files are the last copy of this book's audio.");
  assert.equal(get('delete-dialog-folder').textContent,"1 other item stays where it is. It belongs to another book, or the app can't tell whose it is.");
  assert.deepEqual(get('delete-dialog-list').children.map(p=>p.textContent),["The app's working files (1)",WORK]);assert.equal(get('delete-dialog-list').getAttribute('aria-label'),'Files to delete');
  await get('delete-cancel').handlers.click({});
  // 8. Remove this copy (ruling 25, Judy's update spec section 3). Futaba's m-3: no Approve on either duplicate row.
  const duplicate=(name,copy,kind='verified')=>askRow(name,{kind:'other',also:null,why:'',reasons:['Identical verified recording already arranged — duplicate sources preserved'],reason:'',
    fields:{title:{proposal:'Inferno',basis:'tag'},author:{proposal:'Dan Brown',basis:'tag'}},candidates:[],destination:{path:'Brown Dan\\Inferno.m4b',absolute:'',taken:true,reason:''},
    duplicate:kind,...(copy?{copy}:{})},{members:[{path:FOLDER+'\\01.mp3'},{path:FOLDER+'\\02.mp3'}],review:{title:'Inferno',canonical_author:'Dan Brown'}});
  paint([duplicate('v',{kind:'verified_duplicate',present:3}),duplicate('w',{kind:'verified_duplicate',present:3}),duplicate('q',null,'possible')]);
  tr=trOf('cand-v');const removeButton=tr=>buttonsOf(tr).find(b=>b.textContent==='Remove this copy' || b.textContent==='Checking...');
  assert.equal(buttonsOf(tr).find(b=>b.textContent==='Approve'),undefined,'no inert Approve on a duplicate row');
  assert.equal(buttonsOf(trOf('cand-q')).find(b=>b.textContent==='Approve'),undefined,'nor on a possible duplicate');
  assert.equal(removeButton(trOf('cand-q')),undefined,'a possible duplicate has no proof: no Remove this copy');assert.equal(deleteButton(tr),undefined,'never both buttons');
  const remove=buttonsOf(tr).at(-1);assert.equal(remove,removeButton(tr),'last in the row');assert.ok(remove.className.includes('danger'));assert.equal(buttonsOf(tr).at(-2).className,'row-break');
  assert.equal(remove.title,"Delete this copy's files from disk. The app shows the audiobook in Audiobooks Sorted first, and you confirm.");
  assert.equal(remove.getAttribute('aria-label'),'Remove this copy: Title v');
  assert.equal(hint(tr),'This recording is already in Audiobooks Sorted. The audio files here are exact copies of the files it was arranged from.');
  const COPY=[{path:FOLDER+'\\01.mp3',size:10,kind:'audio'},{path:FOLDER+'\\02.mp3',size:10,kind:'audio'}];
  previewAnswer=()=>ok({files:COPY,bytes:20,folders:[],stay:{items:0},last_copy:null,sorted:{path:ROOT+'\\Brown Dan\\Inferno.m4b',size:612*1024*1024,verified_at:'2026-10-25T14:32:00+00:00'},refusal:null,kind:'verified_duplicate'});
  await remove.handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(posted('/api/candidate/delete-preview').at(-1),{library:'Audiobooks',id:'cand-v',revision:2,mode:'copy'});
  assert.equal(get('delete-dialog-title').textContent,'Remove this copy?');assert.equal(document.activeElement,get('delete-cancel'),'Cancel has focus');
  assert.equal(get('delete-dialog-book').textContent,'Inferno — Dan Brown');assert.equal(get('delete-dialog-reason').textContent,hint(tr));
  assert.equal(get('delete-dialog-sorted').hidden,false);assert.equal(get('delete-dialog-sorted-title').textContent,'Stays in Audiobooks Sorted');
  assert.equal(get('delete-dialog-sorted-path').textContent,ROOT+'\\Brown Dan\\Inferno.m4b');
  assert.match(get('delete-dialog-sorted-facts').textContent,/^.+\. Verified \d\d:\d\d: the file is there and unchanged since the app arranged it\.$/);
  assert.equal(get('delete-dialog-last').hidden,true,'a copy that is also in Sorted is not the last copy');
  assert.equal(get('delete-dialog-forget').textContent,"The app forgets this copy. If the same files turn up again, they're found as a new book. Nothing in Audiobooks Sorted is touched.");
  assert.equal(get('delete-confirm').textContent,'Remove this copy and 2 files');
  assert.equal(get('delete-confirm').title,"Delete this copy's 2 files. The audiobook in Audiobooks Sorted stays. The app can't undo this.");
  prevented=false;get('delete-dialog').handlers.keydown({key:'Enter',target:get('delete-dialog-list'),preventDefault(){prevented=true;}});assert.ok(prevented,'Enter confirms nothing in copy mode either');
  deleteAnswer=()=>ok({deleted:2,bytes:20,failed:[],forgotten:true,folders:{removed:0,stayed:0}});
  await get('delete-confirm').handlers.click({});await tick();
  assert.deepEqual(posted('/api/candidate/delete').at(-1),{library:'Audiobooks',id:'cand-v',revision:2,paths:COPY.map(f=>f.path),folders:[],mode:'copy'});
  assert.match(get('retry-all-status').textContent,/^Removed 1 copy and 2 files \(.+\)\.$/);assert.equal(run('deleteNotes.get("cand-v").text'),'Removed. The copy is gone from the app.');
  // Refusals in copy mode: the audiobook gone, changed, a copy file no longer matching; never next to the Sorted block.
  previewAnswer=()=>ok({files:[],bytes:0,folders:[],stay:{items:0},last_copy:null,sorted:null,refusal:{code:'sorted_missing',message:'x'}});
  paint([duplicate('w',{kind:'verified_duplicate',present:3})]);await removeButton(trOf('cand-w')).handlers.click({stopPropagation(){}});await tick();
  assert.equal(get('delete-dialog-title').textContent,"Can't remove this copy");assert.equal(get('delete-dialog-sorted').hidden,true);
  assert.equal(get('delete-dialog-files').textContent,'The audiobook is not where the app put it in Audiobooks Sorted. Nothing was deleted.');await get('delete-close').handlers.click({});
  previewAnswer=()=>ok({files:COPY,bytes:20,folders:[],stay:{items:0},last_copy:null,sorted:null,refusal:null});
  await removeButton(trOf('cand-w')).handlers.click({stopPropagation(){}});await tick();
  assert.equal(get('delete-dialog-files').textContent,'Remove was not accepted. Nothing was deleted.','no proof shown, nothing to confirm');assert.equal(get('delete-confirm').hidden,true);await get('delete-close').handlers.click({});
  previewAnswer=()=>ok({files:COPY,bytes:20,folders:[],stay:{items:0},last_copy:null,sorted:{path:'x',size:1,verified_at:'2026-10-25T14:32:00+00:00'},refusal:null});
  for(const [code,line] of [['sorted_changed','The audiobook in Audiobooks Sorted has changed since the app arranged it. Nothing was deleted.'],['not_identical','These files no longer match the ones the audiobook was arranged from. Nothing was deleted.'],
    ['files_changed',"The folder doesn't match the list, so nothing was deleted. Press Remove this copy to see the current list."]]){
    deleteAnswer=()=>({ok:false,status:409,json:async()=>({error:'x',code})});
    await removeButton(trOf('cand-w')).handlers.click({stopPropagation(){}});await tick();await get('delete-confirm').handlers.click({});await tick();
    assert.equal(get('delete-dialog-files').textContent,line,code);await get('delete-close').handlers.click({});
  }
  deleteAnswer=()=>{throw new TypeError('Failed to fetch');};
  await removeButton(trOf('cand-w')).handlers.click({stopPropagation(){}});await tick();await get('delete-confirm').handlers.click({});await tick();
  assert.equal(get('delete-dialog-title').textContent,'Removal may not have finished');
  assert.equal(get('delete-dialog-files').textContent,'Connection interrupted, so the removal may have gone through. Check the list before trying again.');
  console.log('PASS Delete book: offer-only button, last with its tooltip, dialog with Cancel focused, Enter confirms nothing, exact paths, success, partial, refusals, lost connection; groups, folders, stay and last-copy lines; Remove this copy with its proof, refusals and no Approve on duplicate rows');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_delete_frontend.js'),module);m.filename=path.join(__dirname,'test_delete_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

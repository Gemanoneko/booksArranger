'use strict';
// Judy 0.22.2 section 5 (Sergei 2026-10-26, Sigma Force 9 "All files missing"): after Delete book said "Deleted. The book
// is gone from the app." the row was still listed with Scan again / View metadata / Source folders. The row leaves in the
// same render as the answer, its chip count drops, and a list or status answer from before the delete (here a stub that
// still lists the book) cannot bring it back; a list without it ends the guard. Real frontend on the Retry test's DOM and
// transport doubles; no server, no file.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const FOLDER='Z:\\Audiobooks\\James Rollins\\Sigma Force\\9. Bloodline';
function missingRow(name){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Sigma Force '+name,conflicts:[],coverage:'',companions:[],artists:['James Rollins'],members:[{path:FOLDER+'\\01.mp3',missing:true}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['Files missing']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,
    ask:{kind:'files_missing',also:null,why:'',reasons:['Files missing'],fields:{title:{proposal:'Bloodline',basis:'tag'},author:{proposal:'James Rollins',basis:'tag'}},candidates:[],
      missing:{folders:[FOLDER],files:[FOLDER+'\\01.mp3'],present:0,total:1},destination:{path:'',absolute:'',taken:false,reason:''},delete:{kind:'files_missing',present:0}}};
}
let previewAnswer=null,deleteAnswer=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/candidate/delete-preview'){calls.push({route,options});return previewAnswer(data);}
  if(route==='/api/candidate/delete'){calls.push({route,options});return deleteAnswer(data);}
  return baseFetch(route,options);
};
const ok=value=>({ok:true,status:200,json:async()=>value});
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const buttonsOf=tr=>[...tr.children[5].children[0].children];
const deleteButton=tr=>buttonsOf(tr).find(b=>b.textContent==='Delete book');
const texts=()=>{const found=[];const walk=node=>{if(!node)return;if(node.textContent)found.push(node.textContent);for(const child of node.children || [])walk(child);};walk(get('inventory'));return found.join(' | ');};
(async()=>{
  const nine=missingRow('9'),eight=missingRow('8');
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:{files_missing:2}}};
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  context.fixture=[nine,eight];run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);paintedContext=listContext();controls()');
  // The stub still lists the book (and still counts it): a list or status computed before the delete.
  inventoryOverride=()=>({ok:true,json:async()=>({rows:[nine,eight],total:2})});
  previewAnswer=()=>ok({files:[],bytes:0,refusal:null,kind:'files_missing',folders:[],stay:{items:0},last_copy:null});
  await deleteButton(trOf('cand-9')).handlers.click({stopPropagation(){}});await tick();
  deleteAnswer=()=>ok({deleted:0,bytes:0,failed:[],forgotten:true,folders:{removed:0,stayed:0}});
  await get('delete-confirm').handlers.click({});
  // In the same render as the answer: the row and its count are gone.
  assert.equal(trOf('cand-9'),undefined,'the row left at the answer');
  assert.equal(run('state.audiobook_jobs.attention_counts.files_missing'),1,'its chip count dropped');
  assert.equal(run('totalRows'),1);
  assert.doesNotMatch(texts(),/Deleted\. The book is gone from the app\./,'no row shows the settled line');
  assert.ok(trOf('cand-8'),'positive control: the other book stays');
  // The list and status read again: the stale answer cannot bring it back, nor its count.
  await tick();await run('refresh(true)');await tick();
  assert.equal(trOf('cand-9'),undefined,'a stale list answer did not bring it back');
  assert.doesNotMatch(texts(),/Deleted\. The book is gone from the app\./);
  backend={...backend,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:{files_missing:2}}};
  context.stale=Date.now()-60000;
  run('deletedCounts(stale_state={audiobook_jobs:{attention_counts:{files_missing:2}}},'+context.stale+')');
  assert.equal(run('stale_state.audiobook_jobs.attention_counts.files_missing'),1,'a status sent before the delete still counted it: corrected');
  // A fresh list without the book ends the guard.
  inventoryOverride=()=>({ok:true,json:async()=>({rows:[eight],total:1})});
  await run('refresh(true)');await tick();
  assert.equal(run('deletedBooks.has("cand-9")'),false,'the guard ends once a list answer sent after the delete is without it');
  console.log('PASS a deleted book leaves in the same render, its count drops, and a stale list or status cannot bring it back');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_delete_leaves_frontend.js'),module);m.filename=path.join(__dirname,'test_delete_leaves_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

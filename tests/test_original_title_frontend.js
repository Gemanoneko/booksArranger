'use strict';
// Ruling 29 (Judy 0.22.2 section 4): "Waiting for the original title" is its own row state, with its fallback stated (the
// path Approve files now, labelled "If none is found, goes to"), its Approve ("Stop waiting: …") and, in the details panel,
// the "Original title" fact. Ruling 33's Author unclear row for a Latin name with a Russian first name has its sentence.
// Runs the real frontend on the Retry test's doubles.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted';
function row(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Джек из Тени',conflicts:[],coverage:'',companions:[],artists:['Roger Zelazny'],members:[{path:'Z:\\Audiobooks\\Roger Zelazny\\Джек из Тени.m4b'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Waiting for source',reasons:['Waiting for the original title'],wait:{kind:'original_title'}},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const waiting=row('w',{kind:'original_title',why:'',odd_name:true,reasons:['Waiting for the original title'],fields:{title:{proposal:'Джек из Тени',basis:''},author:{proposal:'Roger Zelazny',basis:''}},candidates:[],
  destination:{path:'Zelazny Roger\\Джек из Тени - Zelazny Roger.m4b',absolute:ROOT+'\\Zelazny Roger\\Джек из Тени - Zelazny Roger.m4b',taken:false,reason:''}});
const language=row('l',{kind:'author_unclear',why:'name_language',odd_name:true,reasons:['Author unclear'],fields:{title:{proposal:'Звезда',basis:'tag'},author:{proposal:'Marchenko Ilya',basis:'tag'}},
  candidates:[{name:'Marchenko Ilya',source:'spelling',reader_count:0},{name:'Марченко Илья',source:'spelling',reader_count:0}],destination:{path:'Marchenko Ilya\\Звезда - Marchenko Ilya.m4b',absolute:'',taken:false,reason:''}},
  {automatic:{state:'Held',reasons:['Author unclear']}});
backend={...backend,audiobook_output_root:ROOT};
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="held";viewControls()');
  paint([waiting,language]);
  let tr=trOf('cand-w');
  assert.equal(statusCell(tr).textContent,'Waiting for the original title');
  assert.equal(statusCell(tr).children[0].textContent,'Looking for its English title. If none is found, it converts under the Russian title.');
  const line=walk(statusCell(tr)).find(e=>e.className && String(e.className).includes('goes-to'));
  assert.ok(line,'the Goes to line');assert.equal(line.children[0].textContent,'If none is found, goes to');
  assert.equal(line.children[1].textContent,'Audiobooks Sorted\\Zelazny Roger\\Джек из Тени - Zelazny Roger.m4b');
  assert.equal(walk(statusCell(tr)).filter(e=>e.type==='text').length,0,'no fields on the row itself');
  const approve=buttonsOf(tr).find(b=>b.textContent==='Approve');
  assert.ok(approve,'its own Approve');assert.equal(approve.title,'Stop waiting: file this book as shown. Converts if needed, renames, moves to Audiobooks Sorted.');
  assert.equal(run('originalTitleFact(fixture[0])'),'Waiting for an English title.');
  assert.equal(run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"found",title:"Jack of Shadows"}}})'),'Jack of Shadows');
  assert.equal(run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"none",title:""}}})'),'Not found. Filed under the Russian title.');
  tr=trOf('cand-l');
  assert.equal(statusCell(tr).textContent,'Author unclear');
  assert.equal(statusCell(tr).children[0].textContent,"The author's name is in Latin letters. The app can't tell if they write in Russian.");
  console.log('PASS Waiting for the original title: status, hint, fallback path, Approve and the details fact; the name-language sentence');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_original_title_frontend.js'),module);m.filename=path.join(__dirname,'test_original_title_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

'use strict';
// Ruling 38 (Sergei 2026-10-27; it replaces the waiting part of ruling 29): there is no "Waiting for the original title"
// state, so its row, Approve tooltip, Goes to label, editor help and saved line are gone (Judy 0.22.2 section 4). The
// details panel keeps its "Original title" fact (found, not found, entered), with no waiting line. Ruling 33's Author
// unclear row for a Latin name with a Russian first name keeps its sentence. Runs the real frontend on the Retry
// test's doubles.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted';
function row(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Звезда',conflicts:[],coverage:'',companions:[],artists:['Ilya Marchenko'],members:[{path:'Z:\\Audiobooks\\Unsorted\\Ilya Marchenko - Zvezda.m4b'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['Author unclear']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const language=row('l',{kind:'author_unclear',why:'name_language',odd_name:true,reasons:['Author unclear'],fields:{title:{proposal:'Звезда',basis:'tag'},author:{proposal:'Marchenko Ilya',basis:'tag'}},
  candidates:[{name:'Marchenko Ilya',source:'spelling',reader_count:0},{name:'Марченко Илья',source:'spelling',reader_count:0}],destination:{path:'Marchenko Ilya\\Звезда - Marchenko Ilya.m4b',absolute:'',taken:false,reason:''}});
backend={...backend,audiobook_output_root:ROOT};
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4];
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
(async()=>{
  const page=fs.readFileSync(path.join(__dirname,'..','web','app.js'),'utf8');
  assert.ok(page.includes("The author's name is in Latin letters."),'positive control: the scan reads the page source');
  for(const gone of ['Waiting for the original title','Looking for its English title','If none is found, goes to','Stop waiting:','Type the English title to stop waiting.',
                     'Waiting for an English title.','Saved. The title is used as entered.',"kind==='original_title'"])assert.ok(!page.includes(gone),'gone: '+gone);
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="held";viewControls()');
  paint([language]);
  const tr=trOf('cand-l');
  assert.equal(statusCell(tr).textContent,'Author unclear');
  assert.equal(statusCell(tr).children[0].textContent,"The author's name is in Latin letters. The app can't tell if they write in Russian.");
  // Ruling 39: no English spelling found for a foreign author credited only in Cyrillic: keep the name, or type it (Other).
  const spelling=row('s',{kind:'author_unclear',why:'english_spelling',odd_name:true,credit:'Вестерфельд Скотт',reasons:['Author unclear'],fields:{title:{proposal:'Голиаф',basis:'tag'},author:{proposal:'Вестерфельд Скотт',basis:'tag'}},
    candidates:[{name:'Вестерфельд Скотт',source:'spelling',reader_count:0}],destination:{path:'Вестерфельд Скотт\\Голиаф - Вестерфельд Скотт.m4b',absolute:'',taken:false,reason:''}},
    {title_clue:'Голиаф',artists:['Скотт Вестерфельд'],members:[{path:'Z:\\Audiobooks\\Steampunk\\Голиаф.m4b'}]});
  paint([language,spelling]);
  const asked=trOf('cand-s');
  assert.equal(statusCell(asked).textContent,'Author unclear');
  assert.equal(statusCell(asked).children[0].textContent,"The app found no English spelling of this author's name online. Type one under Other, or keep this name if the author writes in Russian.",'Judy 15.1');
  assert.equal(run('askFieldPlan(fixture[1].ask).author'),'radio','the Author unclear choices: this name, or Other');
  // Judy 15.1: the Cyrillic choice is tagged "Russian spelling"; ruling 33's pair keeps "spelling" (control).
  const tags=tr=>walk(statusCell(tr)).filter(e=>e.parentElement?.className==='ask-radio' && String(e.className).includes('field-help')).map(e=>e.textContent);
  assert.deepEqual(tags(asked),['Russian spelling']);
  assert.deepEqual(tags(trOf('cand-l')),['spelling','spelling'],'positive control: the name-language row draws its tags');
  assert.ok(run('askNames(fixture[1].ask)').includes('Author: Вестерфельд Скотт - Russian spelling'),'the names summary says the same');
  assert.equal(run('originalTitleFact({automatic:{state:"Waiting for source",wait:{kind:"original_title"}}})'),'','a record a 0.22.2 candidate left: no waiting line');
  assert.equal(run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"found",title:"Jack of Shadows"}}})'),'Jack of Shadows');
  assert.equal(run('originalTitleFact({metadata_facts:{original_title_lookup:{state:"none",title:""}}})'),'Not found. Filed under the Russian title.');
  assert.equal(run('originalTitleFact({entered:["title"],metadata_facts:{original_title_lookup:{state:"none",title:""}}})'),'Entered by you.');
  assert.equal(run('originalTitleFact({})'),'','no lookup, no fact');
  console.log('PASS no waiting state, row or copy; the Original title fact; the name-language sentence');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_original_title_frontend.js'),module);m.filename=path.join(__dirname,'test_original_title_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

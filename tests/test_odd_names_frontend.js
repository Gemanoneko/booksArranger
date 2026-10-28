'use strict';
// The odd-name questions of 0.22.1 (Q3, ASK guards only): a bitrate, a series or number, or Latin letters in a title, and a
// folder name used as an author, each reach the to-do list on the existing rows (Title or author / Author unclear) with
// one sentence that says what looks wrong (Judy's section 11), the field to check prefilled with the proposal, and Approve
// as is filing it unchanged. Two people in one author reuse the Author unclear row. Select all and the bulk "Approve as
// is" never take these rows: each is approved on its own row. Runs the real frontend on the Retry test's doubles.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted';
function askRow(name,ask){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'Z:\\Audiobooks\\Unsorted\\'+name+'\\01.mp3'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:[ask.reasons[0]]},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask};
}
const dest=p=>({path:p,absolute:ROOT+'\\'+p,taken:false,reason:''});
const titleAsk=(name,why,title,author)=>askRow(name,{kind:'title_author',also:null,why,odd_name:true,reasons:['Title or author missing'],fields:{title:{proposal:title,basis:'tag'},author:{proposal:author,basis:'tag'}},candidates:[],
  destination:dest(author+'\\'+title+'.m4b')});
const bitrate=titleAsk('br','title_bitrate','Антитела 128','Андерсон Кевин');
const series=titleAsk('se','title_series','Сновидения Ехо #3','Фрай Макс');
const latin=titleAsk('la','title_latin','Master vetrov i zakatov','Фрай Макс');
const folder=titleAsk('fo','author_folder','Лабиринт','Ричард Форд');
const people=askRow('pe',{kind:'author_unclear',also:null,why:'two_people',odd_name:true,reasons:['Author unclear'],fields:{title:{proposal:'Good Omens',basis:'tag'},author:{proposal:'Neil Gaiman',basis:'tag'}},
  candidates:[{name:'Neil Gaiman',source:'author tag',reader_count:0},{name:'Terry Pratchett',source:'author tag',reader_count:0}],destination:dest('Gaiman Neil\\Good Omens.m4b')});
// Controls: the rows bulk Approve as is was built for (0.22.0, section 5) keep it.
const plain=askRow('pl',{kind:'title_author',also:null,why:'author_missing',reasons:['Title or author missing'],fields:{title:{proposal:'Шестёрка воронов 1',basis:'tag'},author:{proposal:'',basis:''}},candidates:[],
  destination:dest('Без автора\\Шестёрка воронов 1.m4b')});
const tagged=askRow('tg',{kind:'author_unclear',also:null,why:'two_people',reasons:['Author unclear'],fields:{title:{proposal:'Солдаты смерти',basis:'tag'},author:{proposal:'Джо Шрайбер',basis:'tag'}},
  candidates:[{name:'Джо Шрайбер',source:'artist tag',reader_count:0},{name:'Пухов Сергей',source:'album artist tag',reader_count:0}],destination:dest('Шрайбер Джо\\Солдаты смерти - Шрайбер Джо.m4b')});
backend={...backend,audiobook_output_root:ROOT};
const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/candidate/approve'){calls.push({route,options});return {ok:true,status:200,json:async()=>({approved:true,job_id:'job-'+data.id,row:{id:data.id}})};}
  if(route==='/api/candidate/approve-preview'){calls.push({route,options});return {ok:true,status:200,json:async()=>({preview:{path:'x.m4b',absolute:'',taken:false}})};}
  return baseFetch(route,options);
};
const posted=route=>calls.filter(call=>call.route===route).map(call=>JSON.parse(call.options.body));
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>tr.children[5].children[0].children;
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const inputs=tr=>walk(statusCell(tr)).filter(e=>e.type==='text');
const radios=tr=>walk(statusCell(tr)).filter(e=>e.type==='radio');
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  paint([bitrate,series,latin,folder,people]);
  // A title the guards doubt: "Title unclear", the reason, and the Title field prefilled with the name as found.
  for(const [id,hint,value] of [['cand-br','The title ends with a number that looks like a bitrate.','Антитела 128'],
    ['cand-se','The title starts with what looks like a series name and number.','Сновидения Ехо #3'],
    ['cand-la','The title looks like Russian written in Latin letters.','Master vetrov i zakatov']]){
    const tr=trOf(id);
    assert.equal(statusCell(tr).textContent,'Title unclear',id);assert.equal(statusCell(tr).children[0].textContent,hint,id);
    const fields=inputs(tr);assert.deepEqual(fields.map(e=>e.dataset.name),id==='cand-se'?['title','series','number']:['title'],id+': one title, the series pair only for title_series, no author field');assert.equal(fields[0].value,value,id);
  }
  // A folder name as the author: "Author unclear", the reason, and the Author field prefilled with the cleaned name.
  let tr=trOf('cand-fo');
  assert.equal(statusCell(tr).textContent,'Author unclear');
  assert.equal(statusCell(tr).children[0].textContent,"The author's name has underscores and may include more than a name.");
  assert.ok(!statusCell(tr).textContent.includes('Check it'),'one sentence, no instruction (section 11.2)');
  let fields=inputs(tr);assert.deepEqual(fields.map(e=>e.dataset.name),['author','title','series','number'],'author question exposes Title and paired Series/Number (ruling62)');assert.equal(fields[0].value,'Ричард Форд');
  // Two people in one author: the existing Author unclear row, one radio per person.
  tr=trOf('cand-pe');assert.equal(statusCell(tr).textContent,'Author unclear');
  assert.equal(statusCell(tr).children[0].textContent,"Two people are credited. The app can't tell who wrote it.");
  assert.ok(radios(tr).length>=2,'a choice between the people');
  // Approve as is files the book unchanged: nothing typed sends no title or author.
  await buttonsOf(trOf('cand-br'))[0].handlers.click({stopPropagation(){}});await tick();
  const sent=posted('/api/candidate/approve').at(-1);assert.equal(sent.id,'cand-br');assert.equal('title' in sent,false);assert.equal('author' in sent,false);

  // The chip holds rows where nothing is missing (Judy 11.4, item 1): "Title or author", with its tooltip.
  assert.equal(run('attentionLabels.title_author'),'Title or author');
  const html=require('node:fs').readFileSync(require('node:path').join(__dirname,'../web/index.html'),'utf8');
  assert.match(html,/id="group-title_author"[^>]*title="Show books whose title or author is missing or looks wrong\."[^>]*>Title or author · 0</);
  assert.ok(!html.includes('Missing title or author'),'the old chip name is gone from the page');

  // Select all and bulk "Approve as is" never take an odd-name row (Judy 11.4, item 2; Jane for Sergei 2026-10-26):
  // "Антитела 128" is never filed unseen. Each is approved on its own row; the rows the bulk action was built for keep it.
  run('attentionGroup="title_author";selectedBooks.clear();viewControls()');
  paint([bitrate,series,latin,folder,plain]);
  get('select-page').checked=true;get('select-page').handlers.change();
  assert.equal(run('JSON.stringify([...selectedBooks.keys()])'),'["cand-pl"]','Select all leaves the odd-name rows unselected');
  assert.equal(get('select-page').checked,true,'every row Select all takes is selected');assert.equal(get('select-page').indeterminate,false);
  assert.equal(get('approve-selected').textContent,'Approve as is (1)');
  run('selectedBooks.set("cand-br",2);batchCounts()');  // ticked by hand: still left out of the bulk action
  assert.equal(get('approve-selected').textContent,'Approve as is (1)');assert.equal(get('batch-count').textContent,'2 selected · 1 can be approved as is · 1 left out');
  get('approve-selected').handlers.click();
  assert.deepEqual(get('approve-dialog-list').children.map(p=>p.textContent),['Audiobooks Sorted\\Без автора\\Шестёрка воронов 1.m4b']);
  assert.equal(get('approve-dialog-left').textContent,'1 selected book is left out. It needs a different action.');
  get('approve-cancel').handlers.click();
  get('select-page').checked=false;get('select-page').handlers.change();assert.equal(run('selectedBooks.size'),0,'Clear all clears every row, a hand-ticked one too');
  run('attentionGroup="author_unclear";selectedBooks.clear();viewControls()');
  paint([people,tagged]);
  get('select-page').checked=true;get('select-page').handlers.change();
  assert.equal(run('JSON.stringify([...selectedBooks.keys()])'),'["cand-tg"]','two people from the odd-name check stay out; two people from the tags keep the bulk action');
  assert.equal(get('approve-selected').textContent,'Approve as is (1)');
  console.log('PASS odd-name questions: Title unclear, Author unclear from a folder, two people; chip Title or author; never in Select all or bulk Approve as is');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_odd_names_frontend.js'),module);m.filename=path.join(__dirname,'test_odd_names_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

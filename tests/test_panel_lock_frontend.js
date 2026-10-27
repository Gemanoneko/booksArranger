'use strict';
// 0.22.3 (Sergei 2026-10-27, «Джеймс Герберт - Крысы 1. Крысы» and «Крампус. Повелитель Йоля»): the row's Save and Approve
// stayed grey with "Save or discard the edits in the details panel first." though nothing was edited in the panel. Clicking
// a row of a multi-MP3 book selects it; the details panel then applies its own chapter default (chapters on, not saved
// yet) as trackDirty, and askPanelEdits read that as an unsaved panel edit of the same book. It came back after every
// restart because the default is applied on every selection. Only an edit Sergei made in the panel holds the row's
// buttons now. Real frontend on the Retry test's DOM/transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted',LOCK='The details panel has unsaved edits for this book: the track order or included files. Save them there, or discard them.';
// A multi-MP3 book whose chapter choice was never saved: the panel defaults chapters on for it (chapter_plan.default).
function mp3Row(name,folder,ask){
  const members=[1,2,3].map(n=>({path:'Z:\\Audiobooks\\'+folder+'\\0'+n+'.mp3',member_key:'k'+n,duration:600}));
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:[],members,track_order:members.map(m=>m.member_key),included:members.map(m=>m.member_key),review:{},
    review_context:{chapters_choice_saved:false},status:'Held',automatic:{state:'Held',reasons:['Title unclear']},
    creation:{status:'Tracks need review',can_create:false,reasons:[],chapters_default:true,chapters_available:true},source_directory_count:1,ask};
}
const dest=p=>({path:p,absolute:ROOT+'\\'+p,taken:false,reason:''});
const rats=mp3Row('rats','Джеймс Герберт - Крысы 1. Крысы',{kind:'title_author',also:null,why:'title_series',odd_name:true,reasons:['Title unclear'],
  fields:{title:{proposal:'Крысы 1. Крысы',basis:'folder_name'},author:{proposal:'Джеймс Герберт',basis:'folder_name'}},candidates:[],destination:dest('Герберт Джеймс\\Крысы 1. Крысы - Герберт Джеймс.m4b')});
const krampus=mp3Row('krampus','Крампус. Повелитель Йоля',{kind:'same_author',also:null,why:'near',reasons:['Same author?'],fields:{title:{proposal:'Крампус. Повелитель Йоля',basis:'tag'},author:{proposal:'Бром Джеральд',basis:'tag'}},
  candidates:[],same_author:{new:'Бром Джеральд',existing:'Brom',existing_books:1,why:'near',count:1},destination:dest('Бром Джеральд\\Крампус. Повелитель Йоля - Бром Джеральд.m4b')});
backend={...backend,audiobook_output_root:ROOT};
const answers={};const posts=[];const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(answers[route]){posts.push({route,data});return answers[route](data);}
  return baseFetch(route,options);
};
const ok=(value,status=200)=>({ok:status<400,status,json:async()=>value});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
const byText=(tr,text)=>buttonsOf(tr).find(b=>b.textContent===text);
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const radios=tr=>walk(statusCell(tr)).filter(e=>e.type==='radio');
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
(async()=>{
  answers['/api/candidate/approve-preview']=data=>ok({preview:{path:'x.m4b',absolute:'',taken:false,title:data.title,author:data.author}});
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  paint([rats,krampus]);

  // 1. «Крысы»: Sergei clicks the row (the panel opens on it with its chapter default), then types in Edit names.
  await trOf('cand-rats').handlers.click();
  assert.equal(run('selectedPath'),'cand-rats');
  assert.equal(run('trackDirty'),true,'the panel applies its chapter default to the selected book (unchanged)');
  assert.equal(run('manualTrackTouched'),false,'Sergei changed nothing in the panel');
  let approve=buttonsOf(trOf('cand-rats'))[0];
  assert.notEqual(approve.title,LOCK,'Approve is not held by the panel\'s own default');assert.equal(approve.getAttribute('aria-disabled'),null);
  answers['/api/candidate/names']=()=>ok({editor:{fields:{title:{proposal:'Крысы 1. Крысы',basis:'folder_name'},author:{proposal:'Джеймс Герберт',basis:'folder_name'},series:{proposal:'',basis:''},number:{proposal:'',basis:''},universe:{proposal:'',basis:''},collection:{proposal:false,basis:''}},
    read:{},remembered:[],universes:[],series:[],job:'none',place:{universe:'',series:'',number:'',collection:false},destination:dest('x.m4b'),entered:[],applies:1}});
  await byText(trOf('cand-rats'),'Edit names').handlers.click({stopPropagation(){}});await tick();await tick();
  const fields=walk(statusCell(trOf('cand-rats'))).filter(e=>e.type==='text'),label=name=>fields.find(f=>(f.getAttribute('aria-label') || '').startsWith(name+':'));
  for(const [name,value] of [['Title','The Rats'],['Author','James Herbert'],['Series','The Rats'],['Number','1']]){label(name).value=value;label(name).handlers.input();}
  await tick();
  const save=walk(statusCell(trOf('cand-rats'))).find(e=>e.id==='button' && e.textContent==='Save');
  assert.notEqual(save.title,LOCK,'Edit names Save is not held');assert.equal(save.getAttribute('aria-disabled'),null,'Edit names Save works');
  approve=buttonsOf(trOf('cand-rats'))[0];assert.equal(approve.getAttribute('aria-disabled'),null,'Approve works with the typed names');

  // 2. «Крампус» (Same author?): the row clicked, one radio picked, nothing else: Approve works.
  await trOf('cand-krampus').handlers.click();
  assert.equal(run('selectedPath'),'cand-krampus');assert.equal(run('trackDirty'),true);
  radios(trOf('cand-krampus'))[0].checked=true;await radios(trOf('cand-krampus'))[0].handlers.change();await tick();
  approve=buttonsOf(trOf('cand-krampus'))[0];
  assert.notEqual(approve.title,LOCK);assert.equal(approve.getAttribute('aria-disabled'),null,'Approve works after only a radio choice');

  // 3. Positive control: a change Sergei makes in the panel itself still holds the row's Approve, with the same words.
  get('add-chapters').checked=false;get('add-chapters').handlers.change();
  approve=buttonsOf(trOf('cand-krampus'))[0];
  assert.equal(approve.title,LOCK,'a real panel edit holds Approve');assert.equal(approve.getAttribute('aria-disabled'),'true');
  // Judy 0.22.3 section 3: the cause is visible text under Approve, with Discard panel edits; one click and Approve works.
  const blockOf=id=>trOf(id).children[5].children[1],block=blockOf('cand-krampus');
  assert.equal(block.hidden,false);assert.equal(block.children[0].textContent,LOCK,'the sentence is on screen, not only in the tooltip');
  assert.ok(approve.getAttribute('aria-describedby').split(' ').includes('block-why-cand-krampus'));
  const discard=block.children[1];assert.equal(discard.textContent,'Discard panel edits');
  assert.equal(discard.title,'Throw away the unsaved edits in the details panel for this book. Nothing is saved.');
  discard.handlers.click({stopPropagation(){}});
  approve=buttonsOf(trOf('cand-krampus'))[0];assert.equal(approve.getAttribute('aria-disabled'),null,'the blocked button works at once');
  assert.equal(blockOf('cand-krampus').children[0].textContent,'Discarded the unsaved edits in the details panel.');
  assert.equal(run('manualTrackTouched'),false);
  // A different book's row is never held by it.
  assert.notEqual(buttonsOf(trOf('cand-rats'))[0].title,LOCK);
  console.log('PASS panel lock: the panel\'s own chapter default never holds a row\'s Save or Approve; a real panel edit still does, said on screen with Discard panel edits');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_panel_lock_frontend.js'),module);m.filename=path.join(__dirname,'test_panel_lock_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

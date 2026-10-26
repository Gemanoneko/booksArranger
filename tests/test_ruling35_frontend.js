'use strict';
// Ruling 35 (Sergei 2026-10-26: "Save my input somewhere and queue the task") and Edit names (Judy 0.22.2 section 1) on
// the real frontend, with the Retry test's DOM and transport doubles. No server, no library.
// - A row's Approve is sent with queue: true; the engine's "queued" answer shows on the row (Queued, its line, Cancel), the
//   outcome lands later: done as the press would have, a refusal with its gate's own words.
// - Another row's press never holds a press back; no "Another operation is in progress." anywhere.
// - A Start over pressed while another press of the page runs waits for it (Queued, Cancel) and runs then.
// - A toolbar press made while the page is busy waits; pressed again, it is taken back.
// - Edit names: the editor opens with one read, Series and Number go together, "Applies to {n} books.", Save is queued
//   when the engine says so, the row line says what Save did, and Place and Entered by you show on the closed row.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted';
function askRow(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'Z:\\Audiobooks\\SCP\\'+name+'.m4b'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['Title or author missing']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const dest=p=>({path:p,absolute:ROOT+'\\'+p,taken:false,reason:''});
const scp=askRow('a',{kind:'title_author',also:null,why:'title_series',odd_name:true,reasons:['Title or author missing'],fields:{title:{proposal:'Пртоколы SCP. Сейф №1',basis:'tag'},author:{proposal:'Разные авторы',basis:''}},candidates:[],
  destination:dest('Сборники\\Пртоколы SCP. Сейф №1 - Разные авторы.m4b')},{place:{universe:'',series:'',number:'',collection:true},entered:[]});
const other=askRow('b',{kind:'title_author',also:null,why:'author_missing',reasons:['Title or author missing'],fields:{title:{proposal:'Тайна',basis:'tag'},author:{proposal:'Иван Петров',basis:'tag'}},candidates:[],destination:dest('Петров Иван\\Тайна - Петров Иван.m4b')});
const stopped={...askRow('c',null),ask:undefined,automatic:{state:'Needs attention',reasons:[]},place:{universe:'',series:'Протоколы SCP',number:'2',collection:true},entered:['series','number'],
  creation:{status:'Output needs attention',can_create:false,reasons:[],job:{job_id:'00000000-0000-4000-8000-000000000003',state:'Output needs attention',stage:'queued',reason:'x',
    attention:{group:'retry',cause:'unsupported_file',originals_untouched:true,startover:'automatic'},retry:{allowed:true,reason:''},destination:{path:'Сборники\\x.m4b',absolute:''}}}};
backend={...backend,audiobook_output_root:ROOT};
const answers={};const posts=[];const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(answers[route]){posts.push({route,data});return answers[route](data);}
  return baseFetch(route,options);
};
const ok=(value,status=200)=>({ok:status<400,status,json:async()=>value});
const sent=route=>posts.filter(p=>p.route===route).map(p=>p.data);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
const byText=(tr,text)=>buttonsOf(tr).find(b=>b.textContent===text);
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const texts=tr=>walk(statusCell(tr)).map(e=>e.textContent).filter(Boolean);
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  paint([scp,other,stopped]);
  // 1. Approve: accepted and queued with his values; the row says so, with Cancel; the outcome lands on the row.
  answers['/api/candidate/approve']=data=>ok({queued:true,id:'q-'+data.id,position:1,blocker:{kind:'scan'}},202);
  let tr=trOf('cand-b');await byText(tr,'Approve').handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(sent('/api/candidate/approve').at(-1),{library:'Audiobooks',id:'cand-b',revision:2,path:'Петров Иван\\Тайна - Петров Иван.m4b',queue:true,label:'Title b'});
  tr=trOf('cand-b');
  assert.equal(byText(tr,'Queued').getAttribute('aria-disabled'),'true','its face: Queued, inert');
  assert.equal(statusCell(tr).children[0].textContent,'Approve queued. Your choices are saved. It runs when the scan finishes.');
  const cancel=buttonsOf(tr).find(b=>b.textContent==='Cancel approve');assert.ok(cancel && !cancel.hidden,'its own Cancel');
  assert.equal(walk(get('inventory')).some(e=>e.title==='Another operation is in progress.'),false,'never "Another operation is in progress."');
  // The outcome: refused, with its gate's words.
  run('syncQueue('+JSON.stringify({queued_actions:[],queue_running:null,queue_outcomes:[{id:'q-cand-b',action:'approve',book_id:'cand-b',title:'Title b',result:'refused',code:'profiles',error:'Split book parts are different recordings (audio profiles differ)'}]})+');renderRows(true);controls()');
  tr=trOf('cand-b');
  assert.equal(statusCell(tr).children[0].textContent,'Approve cancelled: the files are different recordings (their audio differs). Choose the files that belong in the details panel, then approve.');
  // Done: as the press would have been.
  run('syncQueue('+JSON.stringify({queued_actions:[],queue_running:null,queue_outcomes:[{id:'q2',action:'approve',book_id:'cand-b',title:'Title b',result:'done',answer:{job_id:'j'}}]})+');controls()');
  assert.equal(run('askDone.get("cand-b")'),'approve');assert.equal(get('retry-all-status').textContent,'Approved 1 book. Track it under Queued / creating.');
  // 2. Another row's press never holds this one.
  let release;answers['/api/candidate/approve']=data=>new Promise(resolve=>{release=()=>resolve(ok({queued:true,id:'q3',position:1,blocker:{kind:'operation'}},202));});
  run('askDone.clear();askResults.clear();queueNotes.clear()');paint([scp,other,stopped]);
  const first=byText(trOf('cand-b'),'Approve').handlers.click({stopPropagation(){}});await tick();
  assert.equal(byText(trOf('cand-a'),'Approve').getAttribute('aria-disabled'),null,'the other row\'s Approve stays ready');
  release();await first;await tick();
  // 3. A Start over pressed while another press of the page runs: held, with Cancel, run when the page is free.
  answers['/api/audiobook/startover']=data=>ok({outcome:'automatic',set_aside:true,job_id:data.job_id,row:null},202);
  run('busy=true;controls()');
  await run('restartPress(rows.find(r=>r.id==="cand-c"),{kind:"startover",endpoint:"/api/audiobook/startover"},null)');
  tr=trOf('cand-c');assert.equal(statusCell(tr).children[0].textContent,'Start over queued. It runs when the current action finishes.');
  assert.equal(sent('/api/audiobook/startover').length,0,'nothing sent while the page is busy');
  const held=buttonsOf(tr).find(b=>b.textContent==='Cancel start over');assert.ok(held && !held.hidden,'its Cancel');
  run('busy=false;controls()');await tick();await tick();
  assert.equal(sent('/api/audiobook/startover').length,1,'it ran when the page was free');
  // 4. A toolbar press made while busy waits; pressed again, it is taken back.
  run('busy=true;controls()');get('pause-jobs').handlers.click();
  assert.equal(get('message').textContent,'Pause audiobook jobs queued. It runs when the current action finishes. Press it again to cancel.');
  assert.equal(get('pause-jobs').getAttribute('aria-disabled'),'true');get('pause-jobs').handlers.click();
  assert.equal(get('pause-jobs').getAttribute('aria-disabled'),null,'taken back');assert.equal(run('laterPresses.length'),0);run('busy=false;controls()');
  // 5. Edit names on the SCP row.
  answers['/api/candidate/names']=()=>ok({editor:{fields:{title:{proposal:'Пртоколы SCP. Сейф №1',basis:'tag'},author:{proposal:'Разные авторы',basis:''},series:{proposal:'',basis:''},number:{proposal:'',basis:''},universe:{proposal:'',basis:''},collection:{proposal:true,basis:''}},
    read:{},remembered:[],universes:['Warhammer 40,000'],series:['Протоколы SCP'],job:'none',place:{universe:'',series:'',number:'',collection:true},destination:dest('Сборники\\x.m4b'),entered:[],applies:1}});
  answers['/api/candidate/approve-preview']=data=>ok({preview:{path:'Сборники\\'+(data.names?.series || 'x')+'\\y.m4b',absolute:'',taken:false,title:data.title,author:'',place:{universe:'',series:data.names?.series || '',number:data.names?.number || '',collection:true},applies:3}});
  inventoryRows=[scp,other,stopped];paint([scp,other,stopped]);tr=trOf('cand-a');
  const edit=byText(tr,'Edit names');assert.ok(edit,'on every book row');assert.equal(edit.title,'Correct this book\'s title, author, series or universe. Nothing is converted or moved.');
  assert.equal(buttonsOf(tr).indexOf(edit)+1,buttonsOf(tr).indexOf(byText(tr,'View metadata')),'right before View metadata');
  await edit.handlers.click({stopPropagation(){}});await tick();await tick();
  assert.equal(sent('/api/candidate/names').length,1,'one read for one row');
  tr=trOf('cand-a');const fields=walk(statusCell(tr)).filter(e=>e.type==='text'),label=name=>fields.find(f=>(f.getAttribute('aria-label') || '').startsWith(name+':'));
  assert.ok(label('Title') && label('Author') && label('Series') && label('Number') && label('Universe'),'every field, labelled');
  assert.equal(label('Series').getAttribute('list'),'names-series-cand-a','with its pick-list');
  label('Series').value='Протоколы SCP';label('Series').handlers.input();
  const save=()=>walk(statusCell(trOf('cand-a'))).find(e=>e.id==='button' && ['Save','Saving…'].includes(e.textContent));
  assert.equal(save().getAttribute('aria-disabled'),'true');assert.equal(save().title,'Type the number in the series, or clear the series.');
  label('Number').value='1';label('Number').handlers.input();await run('namesPreview("cand-a",0)');await tick();
  assert.ok(texts(trOf('cand-a')).includes('Saved values are remembered, so a new scan of these files uses them. Applies to 3 books.'));
  assert.ok(texts(trOf('cand-a')).includes('Collection · Series: Протоколы SCP · No. 1'),'the Place line follows the draft');
  assert.equal(save().getAttribute('aria-disabled'),null);
  answers['/api/candidate/names-save']=data=>ok({queued:true,id:'qn',position:1,blocker:{kind:'book'}},202);
  await save().handlers.click({stopPropagation(){}});await tick();
  const body=sent('/api/candidate/names-save').at(-1);
  assert.deepEqual(body.names,{title:'Пртоколы SCP. Сейф №1',author:'Разные авторы',series:'Протоколы SCP',number:'1',universe:'',collection:true});assert.equal(body.queue,true);
  assert.equal(save().textContent,'Saving…','queued: Saving…');
  run('syncQueue('+JSON.stringify({queued_actions:[],queue_running:null,queue_outcomes:[{id:'qn',action:'names',book_id:'cand-a',title:'Title a',result:'done',answer:{outcome:'saved',applies:3,entered:['series','number']}}]})+')');await tick();
  tr=trOf('cand-a');assert.equal(statusCell(tr).children[0].textContent,'Saved. Approve uses these names.');
  assert.equal(get('retry-all-status').textContent,'Saved names for Title a. Applies to 3 books.');
  // The closed Stopped row: its Place and Entered by you lines.
  assert.ok(texts(trOf('cand-c')).includes('Collection · Series: Протоколы SCP · No. 2'));assert.ok(texts(trOf('cand-c')).includes('Entered by you: series, number.'));
  console.log('PASS ruling 35 on the page: queued Approve with Cancel and its outcome, rows never hold each other, held Start over and toolbar presses; Edit names: read, pairing, Applies to, queued Save, row line, Place and Entered');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_ruling35_frontend.js'),module);m.filename=path.join(__dirname,'test_ruling35_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

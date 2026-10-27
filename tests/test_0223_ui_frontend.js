'use strict';
// Judy's 0.22.3 spec (Docs/BooksArranger_0.22.3_UX_2026-10-27.md) on the real frontend, with the Retry test's DOM and
// transport doubles. No server, no library.
// 1. One names editor (ruling 40): a book's panel shows its names as facts, its name inputs are off, Edit names opens the row.
// 2. Save feedback: the clock under Save, the strip's "Goes to", "It left this list" with Show it.
// 3. A blocked Save says why under the button, with its one-click fix.
// 4. Author rules learned online: the list, Find author, Take back with its confirmation, the strip line, a failure.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted';
function askRow(name,ask,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{}},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'Z:\\Audiobooks\\'+name+'\\01.m4b'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['Title or author missing']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,ask,...extra};
}
const dest=p=>({path:p,absolute:ROOT+'\\'+p,taken:false,reason:''});
const rats=askRow('rats',{kind:'title_author',also:null,why:'author_missing',reasons:['Title or author missing'],fields:{title:{proposal:'Крысы',basis:'folder_name'},author:{proposal:'Джеймс Герберт',basis:'folder_name'}},candidates:[],
  destination:dest('Герберт Джеймс\\Крысы - Герберт Джеймс.m4b')});
const other=askRow('other',{kind:'title_author',also:null,why:'author_missing',reasons:['Title or author missing'],fields:{title:{proposal:'Тайна',basis:'tag'},author:{proposal:'Иван Петров',basis:'tag'}},candidates:[],destination:dest('Петров Иван\\Тайна - Петров Иван.m4b')});
const editor={fields:{title:{proposal:'Крысы',basis:'folder_name'},author:{proposal:'Джеймс Герберт',basis:'folder_name'},series:{proposal:'Крысы',basis:'folder_name'},number:{proposal:'1',basis:'folder_name'},universe:{proposal:'',basis:''},collection:{proposal:false,basis:''}},
  read:{},remembered:[],universes:[],series:['Крысы'],job:'none',place:{universe:'',series:'Крысы',number:'1',collection:false},destination:dest('x.m4b'),entered:[],applies:1};
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
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
const cls=(tr,name)=>walk(statusCell(tr)).find(e=>String(e.className || '').split(' ').includes(name));
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  inventoryRows=[rats,other];paint([rats,other]);
  answers['/api/candidate/names']=()=>ok({editor});
  answers['/api/candidate/approve-preview']=data=>ok({preview:{path:'Герберт Джеймс\\'+(data.names?.series || '-')+'\\y.m4b',absolute:'',taken:false,title:data.title,author:data.author,place:{universe:'',series:data.names?.series || '',number:data.names?.number || '',collection:false},applies:1}});

  // 1. The book panel: names as facts, its name inputs off, Edit names opens the row's editor (ruling 40).
  await trOf('cand-rats').handlers.click();await tick();await tick();
  assert.equal(get('names-facts').hidden,false);
  assert.equal(get('names-fact-title').textContent,'Крысы');assert.equal(get('names-fact-series').textContent,'Крысы · No. 1');
  assert.equal(get('names-fact-universe').textContent,'None');assert.equal(get('names-fact-collection').textContent,'No');
  for(const field of ['title','author','universe','series','number','anthology'])assert.equal(run('form.elements.namedItem('+JSON.stringify(field)+').disabled'),true,field+' cannot be typed in');
  for(const field of ['narrator','canonical_author','topic'])assert.notEqual(run('form.elements.namedItem('+JSON.stringify(field)+').disabled'),true,field+' stays editable');
  assert.equal(get('save-metadata').title,"Save these values as a draft and a metadata source for this book. Names are edited on the book's row.");
  assert.equal(get('names-facts-edit').getAttribute('aria-disabled'),null);
  await get('names-facts-edit').handlers.click({stopPropagation(){}});await tick();await tick();
  assert.equal(run('namesOpen("cand-rats")'),true,'the row\'s own editor opens');
  // Not on the current page: inert, with the sentence on screen.
  run('rows=rows.filter(row=>row.id!=="cand-rats");renderNamesFacts()');
  assert.equal(get('names-facts-edit').getAttribute('aria-disabled'),'true');
  assert.equal(get('names-facts-why').textContent,"This book isn't on the current page. Clear the filters or find it in the list, then press Edit names.");assert.equal(get('names-facts-why').hidden,false);
  paint([rats,other]);

  // 3. Save says why it waits, under the button, with its fix: nothing changed, then a series with no number (Clear series).
  let tr=trOf('cand-rats');const save=()=>walk(statusCell(trOf('cand-rats'))).find(e=>e.id==='button' && ['Save','Saving…'].includes(e.textContent));
  const why=()=>cls(trOf('cand-rats'),'block-why');
  assert.equal(save().getAttribute('aria-disabled'),'true');assert.equal(why().hidden,false);
  assert.equal(why().children[0].textContent,'Nothing to save: these are the names the app already has.','visible text, not only the tooltip');
  assert.equal(save().title,'Nothing to save: these are the names the app already has.','the tooltip repeats it');
  const fields=()=>walk(statusCell(trOf('cand-rats'))).filter(e=>e.type==='text'),label=name=>fields().find(f=>(f.getAttribute('aria-label') || '').startsWith(name+':'));
  label('Number').value='';label('Number').handlers.input();
  assert.equal(why().children[0].textContent,'Type the number in the series, or clear the series.');
  const fix=why().children[1];assert.equal(fix.textContent,'Clear series');assert.equal(fix.title,'Empty the Series field.');
  fix.handlers.click({stopPropagation(){}});await tick();
  assert.equal(run('namesValues(rows.find(row=>row.id==="cand-rats")).series'),'','one click clears it');
  assert.equal(save().getAttribute('aria-disabled'),null,'the blocked Save works at once');

  // 2. Saving: "Saving these names…", then the clock and the ladder; the result names where the book goes.
  let release;answers['/api/candidate/names-save']=()=>new Promise(resolve=>{release=resolve;});
  const pressed=Date.now();await save().handlers.click({stopPropagation(){}});await tick();
  const status=()=>cls(trOf('cand-rats'),'names-status');
  assert.equal(save().textContent,'Saving…');assert.equal(status().textContent,'Saving these names…');
  run('pressTick('+(pressed+7400)+')');
  assert.match(status().textContent,/^Saving these names… 0:0[78] The app is busy with background work, so this takes longer\.$/,status().textContent);
  run('pressTick('+(pressed+61000)+')');
  assert.match(status().textContent,/^Saving these names… 1:0[01] Still waiting \(1 min\)\. The app is busy with background work\. It may still go through\. Don't press Save again\.$/);
  inventoryRows=[other];  // the reload no longer lists it: it left this chip
  release(ok({outcome:'saved',applies:1,job:'none',entered:['series'],destination:{path:'Герберт Джеймс\\Крысы - Герберт Джеймс.m4b',absolute:''},
    list_row:{...rats,ask:undefined,automatic:{state:'Queued',reasons:[]},status:'Queued'}}));
  await tick();await tick();await tick();await tick();
  assert.equal(get('retry-all-status').textContent,'Saved names for Title rats. Goes to Audiobooks Sorted\\Герберт Джеймс\\Крысы - Герберт Джеймс.m4b. It left this list: '+run('candidateStatus({...fixture[0],ask:undefined,automatic:{state:"Queued",reasons:[]},status:"Queued"})')+'.');
  assert.equal(get('strip-show').hidden,false,'Show it after the sentence');
  assert.equal(get('strip-show').title,'List this book: sets Status to All and searches for its title.');
  inventoryRows=[rats,other];await get('strip-show').handlers.click();await tick();await tick();
  assert.equal(run('filters.candidates'),'all');assert.equal(get('search').value,'Title rats');assert.equal(run('selectedPath'),'cand-rats','the book is listed and selected');

  // 4. Author rules learned online.
  const rules=[{rule_id:'r2',kind:'same_as',credit:'Страуд Джонатан',target:'Stroud Jonathan',source:'https://fantlab.ru/work1',saved_utc:'2026-10-27T10:00:00+00:00',question:'Лестница'},
    {rule_id:'r1',kind:'keep',credit:'Бром Джеральд',target:'',source:'https://fantlab.ru/work843689',saved_utc:'2026-10-26T10:00:00+00:00',question:'Крампус'}];
  answers['/api/author-rules']=()=>ok({rules,total:2});
  await run('loadAuthorRules()');
  assert.equal(get('author-rules-summary').textContent,'Author rules learned online · 2');
  const entries=()=>get('author-rules-list').children;
  assert.equal(entries().length,2);
  assert.equal(entries()[0].children[0].children[0].textContent,'Страуд Джонатан → Stroud Jonathan');
  assert.equal(entries()[1].children[0].children[0].textContent,'Бром Джеральд stays as written. The author writes in Russian.');
  const link=entries()[0].children[0].children[1].children[0];assert.equal(link.textContent,'Found on fantlab.ru');assert.equal(link.rel,'noopener noreferrer');
  assert.equal(entries()[0].children[0].children[1].children[1].textContent,' · Learned 2026-10-27 · First seen on «Лестница»');
  get('author-rules-find').value='бром';get('author-rules-find').handlers.input();assert.equal(entries().length,1,'Find author filters');
  get('author-rules-find').value='nobody';get('author-rules-find').handlers.input();assert.equal(get('author-rules-note').textContent,'No rule matches «nobody».');
  get('author-rules-find').value='';get('author-rules-find').handlers.input();
  // Take back needs its confirmation; Keep rule closes it.
  const take=()=>walk(entries()[0]).find(e=>e.textContent==='Take back');
  take().handlers.click({stopPropagation(){}});
  const confirmText=walk(entries()[0]).find(e=>String(e.className || '')==='author-rule-confirm');
  assert.equal(confirmText.children[0].textContent,'Take back this rule? The app stops filing Страуд Джонатан as Stroud Jonathan and asks about this name again. Books already filed keep their folders.');
  assert.equal(document.activeElement?.textContent,'Keep rule','focus on the safe default');assert.equal(take(),undefined,'Take back hides while it asks');
  walk(entries()[0]).find(e=>e.textContent==='Keep rule').handlers.click({stopPropagation(){}});assert.ok(take(),'closed, the rule stays');assert.equal(sent('/api/author-rule/retract').length,0);
  // Taken back: gone from the list, the count drops, the strip says what follows.
  answers['/api/author-rule/retract']=()=>ok({retracted:'r2',requeued:1});
  take().handlers.click({stopPropagation(){}});await walk(entries()[0]).find(e=>e.textContent==='Take back rule').handlers.click({stopPropagation(){}});await tick();
  assert.deepEqual(sent('/api/author-rule/retract').at(-1),{rule_id:'r2'});
  assert.equal(get('author-rules-summary').textContent,'Author rules learned online · 1');assert.equal(entries().length,1);
  assert.equal(get('author-rules-status').textContent,'Took back the rule for Страуд Джонатан. 1 waiting book is checked again.','the line beside the list (and the strip in the to-do list)');assert.equal(run('stripNote'),get('author-rules-status').textContent);
  // A failure keeps the rule, with the engine's sentence.
  answers['/api/author-rules']=()=>ok({rules:[rules[1]],total:1});  // the reload after the failure reads the list again
  answers['/api/author-rule/retract']=()=>ok({error:'This author rule was already replaced or taken back. Nothing was changed.',code:'refused'},409);
  take().handlers.click({stopPropagation(){}});await walk(entries()[0]).find(e=>e.textContent==='Take back rule').handlers.click({stopPropagation(){}});await tick();
  const alert=walk(entries()[0]).find(e=>e.className==='rule-error');
  assert.equal(alert.textContent,'This author rule was already replaced or taken back. Nothing was changed.');assert.equal(alert.getAttribute('role'),'alert');
  assert.ok(take(),'Take back is available again');
  console.log('PASS 0.22.3 UI: names as facts and Edit names (ruling 40); the Save clock, Goes to, It left this list and Show it; block lines with fixes; learned author rules with Take back');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_0223_ui_frontend.js'),module);m.filename=path.join(__dirname,'test_0223_ui_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

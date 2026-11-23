'use strict';
// 0.31.0 (Judy's Docs/BooksArranger_0.31.0_UX.md, section 4.5, fourth round; Sergei's R1 and R3): a translated book is filed
// under its English title, in a series folder named in English. Its row says once where the English came from and asks
// nothing: the Title line "English title found on <source>." directly above the Place line, and the Place line's addition
// " · English name from <source>" only where the name's source is not the origin already named. A book written in Russian,
// a book no English title was found for (R3: the row says nothing) and a title he typed have no Title line. Neither is a
// control. Real frontend on the Retry test's DOM/transport doubles. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const answers={},posts=[];const baseFetch=context.fetch;
context.fetch=async(route,options)=>{const data=options?.body?JSON.parse(options.body):undefined;if(answers[route]){posts.push({route,data});return answers[route](data);}return baseFetch(route,options);};
const ok=value=>({ok:true,status:200,json:async()=>value});const tick=()=>new Promise(r=>setImmediate(r));
const SERIES="Remembrance of Earth's Past";
function book(name,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,fingerprint:'a'.repeat(64),scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Тёмный лес',conflicts:[],coverage:'',companions:[],artists:[],members:[{path:'D:\\Audiobooks\\Лю Цысинь\\Тёмный лес\\'+name+'.mp3'}],track_order:[],included:[],review:{},review_context:{},status:'Queued',entered:[],
    automatic:{state:'Queued',reasons:[],sources:[]},creation:{status:'Queued',can_create:false,reasons:[],destination:'Liu Cixin\\'+SERIES+'\\2 - The Dark Forest - Liu Cixin.m4b'},source_directory_count:1,...extra};
}
const found=(provider='wikidata',extra={})=>({original_title_lookup:{state:'found',title:'The Dark Forest',provider,url:'https://example.invalid/'+provider,...extra}});
const placed=(extra={})=>({universe:'',series:SERIES,number:'2',collection:false,origin:'source',provider:'wikidata',...extra});
const translated=(name,extra={})=>book(name,{metadata_facts:found(),title_origin:{origin:'source',rule:'english',split:false,provider:'wikidata',source_url:''},place:placed(),...extra});
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4];
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const hasClass=(element,name)=>String(element.className || '').split(' ').includes(name);
const byClass=(tr,name)=>walk(statusCell(tr)).find(e=>hasClass(e,name));
const lineOf=(tr,name)=>{const line=byClass(tr,name);return line && !line.hidden?line.textContent:'';};
const titleLine=tr=>lineOf(tr,'book-english-title'),placeLine=tr=>lineOf(tr,'book-place');
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;view="candidates";filters.candidates="all";askDrafts.clear();namesState.clear();renderRows(true);controls()');}
(async()=>{
  run('state='+JSON.stringify({...backend,audiobook_output_root:'Z:\\Audiobooks Sorted'}));
  const source=fs.readFileSync(path.join(__dirname,'..','web','app.js'),'utf8'),css=fs.readFileSync(path.join(__dirname,'..','web','style.css'),'utf8');

  // 1. The spec's own row: «Тёмный лес», a row that asks nothing. The Title line, then the Place line, then In and Goes to.
  paint([translated('t')]);
  let tr=trOf('cand-t'),cell=statusCell(tr);
  assert.equal(cell.textContent,'Queued');
  assert.equal(titleLine(tr),'English title found on Wikidata.');
  assert.equal(placeLine(tr),"Series: Remembrance of Earth's Past · No. 2 · found on Wikidata",'the same source for the series and its English name: unchanged');
  const order=cell.children.map(child=>String(child.className || ''));
  assert.equal(order.indexOf('field-help book-english-title')+1,order.indexOf('field-help book-place'),'directly above the Place line');
  assert.ok(order.indexOf('field-help book-place')<order.indexOf('source-box'),'both above the In line');
  // In the Place line's look, and not a control: no tooltip, no focus stop, no handler, and no rule of its own in the
  // stylesheet (it is in normal flow, so it can only wrap or push the lines below it down).
  const line=byClass(tr,'book-english-title');
  assert.ok(hasClass(line,'field-help'));assert.equal(line.title,'');assert.equal(line.tabIndex,undefined);assert.deepEqual(Object.keys(line.handlers),[]);assert.equal(line.getAttribute('role'),null);
  for(const name of ['book-english-title','lookup-note'])assert.ok(!css.includes(name),name+' has no style rule of its own');
  // Source names are those of 4.3; a source with no name the page knows reads "online".
  for(const [provider,words] of [['wikidata','English title found on Wikidata.'],['fantlab','English title found on FantLab.'],['FantLab','English title found on FantLab.'],['goodreads','English title found on Goodreads.'],
    ['litres','English title found on Litres.'],['publisher',"English title found on the publisher's site."],['somewhere-new','English title found online.'],['','English title found online.']]){
    paint([translated('t',{metadata_facts:found(provider),title_origin:null})]);assert.equal(titleLine(trOf('cand-t')),words,provider);
  }
  // It is on every row of the book, before and after conversion.
  paint([translated('t',{status:'Completed',audiobook_ready:true,creation:{status:'Completed',can_create:false,reasons:[]},metadata_approved:true,review:{title:'The Dark Forest',series:SERIES,number:'2'},review_context:{automatic_approval:{matcher_version:'m',work_id:'w'}}})]);
  assert.equal(statusCell(trOf('cand-t')).textContent,'Audiobook Ready');assert.equal(titleLine(trOf('cand-t')),'English title found on Wikidata.');
  // With no Place line it stands in that line's place.
  paint([translated('t',{place:{universe:'',series:'',number:'',collection:false}})]);tr=trOf('cand-t');
  assert.equal(titleLine(tr),'English title found on Wikidata.');assert.equal(placeLine(tr),'');
  const alone=statusCell(tr).children.map(child=>String(child.className || ''));
  assert.equal(alone.indexOf('field-help book-english-title')+1,alone.indexOf('field-help book-place'));assert.ok(alone.indexOf('field-help book-english-title')<alone.indexOf('source-box'));

  // 2. No Title line: the files' own title (a book written in Russian, a book titled in English already: no such fact),
  // no English title found, no answer (R3: the row says nothing), a title he typed. Such a row keeps the cell it had.
  const none=[['no fact',{metadata_facts:{},title_origin:{origin:'files',rule:'russian_original',split:false}}],['no facts at all',{metadata_facts:null,title_origin:null}],
    ['a Russian original',{metadata_facts:{original_title_lookup:{state:'russian',title:''}}}],['nothing found',{metadata_facts:{original_title_lookup:{state:'none',title:''}}}],
    ['no answer',{metadata_facts:{original_title_lookup:{state:'no_answer',title:'',tries:3,limit:3}}}],['entered, by the engine',{metadata_facts:{original_title_lookup:{state:'entered',title:''}}}],
    ['a title among his entered names',{entered:['title']}],['a review he saved himself',{review_context:{metadata_actor:'user'}}],['found, with no title',{metadata_facts:{original_title_lookup:{state:'found',title:'',provider:'wikidata'}}}]];
  for(const [why,extra] of none){
    paint([translated('t',extra)]);tr=trOf('cand-t');
    assert.equal(titleLine(tr),'',why);assert.equal(byClass(tr,'book-english-title'),undefined,why+': no element');
    assert.equal(placeLine(tr),"Series: Remembrance of Earth's Past · No. 2 · found on Wikidata",why+': the Place line is its own');
  }
  // English names from a source never make a question: such a row has no hint and no Approve.
  paint([translated('t')]);tr=trOf('cand-t');
  assert.equal(walk(statusCell(tr)).some(e=>hasClass(e,'attention-hint') && !e.hidden && e.textContent),false);
  assert.equal([...tr.children[5].children[0].children].some(b=>/^Approve/.test(b.textContent) && !b.hidden),false);

  // 3. The Place line (R1). The origin suffix keeps its meaning (where the series and number came from); the new part is
  // added only where the name's source is another one, so the line never names a source the name is not from.
  const place=extra=>run('placeText('+JSON.stringify(placed(extra))+')'),head="Series: Remembrance of Earth's Past · No. 2";
  assert.equal(place({}),head+' · found on Wikidata');
  assert.equal(place({name_from:'wikidata'}),head+' · found on Wikidata','the same source: unchanged');
  assert.equal(place({provider:'fantlab',name_from:'wikidata'}),head+' · found on FantLab · English name from Wikidata');
  assert.equal(place({provider:'fantlab',name_from:'FantLab'}),head+' · found on FantLab');
  for(const [origin,suffix] of [['tags'," · from the file's tags"],['title_tag',' · from the title tag'],['file_name',' · from the file name'],['brackets',' · from the brackets in its name'],['folders',' · from the folder names']])
    assert.equal(place({origin,provider:undefined,name_from:'wikidata'}),head+suffix+' · English name from Wikidata',origin);
  assert.equal(place({origin:'tags',provider:undefined,name_from:'fantlab'}),head+" · from the file's tags · English name from FantLab");
  assert.equal(place({origin:'tags',provider:undefined,name_from:'a-new-source'}),head+" · from the file's tags · English name found online",'a source with no name the page knows');
  assert.equal(place({origin:'entered',provider:undefined,name_from:'wikidata'}),head+' · entered by you','he typed the series: unchanged');
  assert.equal(place({origin:'tags',provider:undefined}),head+" · from the file's tags",'a book written in Russian, or no English name found: unchanged');
  for(const empty of ['',null,undefined,'  ',7])assert.equal(place({origin:'tags',provider:undefined,name_from:empty}),head+" · from the file's tags",String(empty));
  assert.equal(place({origin:'unknown',provider:undefined,name_from:'wikidata'}),head+' · English name from Wikidata','an origin the record does not prove has no words; the name\'s source is still true');
  assert.equal(run('placeText({series:"",number:"",origin:"tags",name_from:"wikidata"})'),'','no series, no line');
  assert.equal(run('placeText({universe:"Warhammer 40,000",series:"",number:"",origin:"tags",name_from:"wikidata"})'),'Universe: Warhammer 40,000','no series: neither part');
  // On the row, with the longest line (two origin parts).
  paint([translated('t',{place:placed({origin:'tags',provider:undefined,name_from:'wikidata'})})]);tr=trOf('cand-t');
  assert.equal(placeLine(tr),head+" · from the file's tags · English name from Wikidata");assert.equal(titleLine(tr),'English title found on Wikidata.');

  // 4. On a row that asks: the Title field and "Title clue:" above, the lines below it. A title he types is his answer
  // ("Entered by you: title." says so once saved), so the line goes at once and comes back with the proposal.
  const ask={kind:'author_unclear',also:null,why:'two_people',reasons:['Author unclear'],fields:{title:{proposal:'The Dark Forest',basis:'tag'},author:{proposal:'Liu Cixin',basis:'tag'}},
    candidates:[{name:'Liu Cixin',source:'artist tag',reader_count:0},{name:'Иван Литвинов',source:'album artist tag',reader_count:4}],hold:{kind:''},destination:{path:'Liu Cixin\\x.m4b',absolute:'',taken:false,reason:'',shared:null}};
  answers['/api/candidate/approve-preview']=data=>ok({preview:{path:'Liu Cixin\\'+(data.title || 'x')+'.m4b',absolute:'',taken:false,place:{},applies:1}});
  paint([translated('a',{status:'Held',automatic:{state:'Held',reasons:['Author unclear']},creation:{status:'Held',can_create:false,reasons:[]},ask})]);tr=trOf('cand-a');
  assert.equal(statusCell(tr).textContent,'Author unclear','the question is its own');assert.equal(titleLine(tr),'English title found on Wikidata.');
  const asked=statusCell(tr).children.map(child=>String(child.className || ''));
  assert.ok(asked.indexOf('ask-fields')<asked.indexOf('field-help book-english-title'),'below the fields');assert.equal(asked.indexOf('field-help book-english-title')+1,asked.indexOf('field-help book-place'));
  const title=run('askRows.get("cand-a").controls').find(control=>control.dataset.name==='title');
  title.value='Тёмный лес (мой вариант)';title.handlers.input();assert.equal(titleLine(tr),'','a typed title: no line, at once');
  title.value='The Dark Forest';title.handlers.input();assert.equal(titleLine(tr),'English title found on Wikidata.','the proposal again');
  title.value='  The Dark Forest ';title.handlers.input();assert.equal(titleLine(tr),'English title found on Wikidata.','spaces around the proposal are not a typed title');

  // 5. With Edit names open on a row that asks nothing: both lines are in the editor, the Title line above the Place line.
  // The editor's place carries the origin but not the English name's source; before he types it shows the row's own
  // series, so its source, and afterwards it follows the engine's preview (the source is on the preview's series).
  const tagged=translated('e',{place:placed({origin:'tags',provider:undefined,name_from:'wikidata'})});
  const editor=(series=SERIES)=>({editor:{fields:{title:{proposal:'The Dark Forest'},author:{proposal:'Liu Cixin'},series:{proposal:series},number:{proposal:'2'},universe:{proposal:''},collection:{proposal:false}},universes:[],series:[],remembered:[],entered:[],job:'none',
    place:{universe:'',series,number:'2',collection:false,origin:'tags'},applies:1}});
  answers['/api/candidate/names']=()=>ok(editor());
  // The engine's preview: the place with its origin, and the series with the source of its English name.
  const previewOf=data=>({preview:{path:'p.m4b',absolute:'',taken:false,applies:1,place:{universe:'',series:data.names.series,number:data.names.number,collection:false,origin:data.names.series===SERIES?'tags':'entered'},
    series:data.names.series===SERIES?{name:SERIES,number:'2',origin:'tags',name_from:'fantlab'}:{name:data.names.series,number:data.names.number,origin:'entered'}}});
  let release;answers['/api/candidate/approve-preview']=data=>new Promise(resolve=>{release=()=>resolve(ok(previewOf(data)));});
  paint([tagged]);await run('namesToggle("cand-e")');await tick();await tick();tr=trOf('cand-e');
  assert.equal(run('namesOpen("cand-e")'),true);assert.ok(run('namesData("cand-e")'),'the editor read its names');
  const box=run('namesRows.get("cand-e").box'),inBox=box.children.map(child=>String(child.className || ''));
  assert.equal(inBox.indexOf('field-help book-english-title')+1,inBox.indexOf('field-help book-place'),'in the editor, directly above the Place line');
  assert.equal(titleLine(tr),'English title found on Wikidata.');assert.equal(placeLine(tr),head+" · from the file's tags · English name from Wikidata",'nothing typed: the row\'s own series and its name\'s source');
  // The preview answers: the name's source is the preview's own.
  assert.equal(typeof release,'function','the open editor asked for its preview');release();await tick();await tick();
  assert.equal(placeLine(tr),head+" · from the file's tags · English name from FantLab",'the preview\'s own answer');
  answers['/api/candidate/approve-preview']=data=>ok(previewOf(data));
  // He types a title: the Title line goes, at once.
  const inputs=run('namesRows.get("cand-e").inputs');
  inputs.title.value='Мой заголовок';inputs.title.handlers.input();assert.equal(titleLine(tr),'','a typed title in the editor');
  inputs.title.value='The Dark Forest';inputs.title.handlers.input();assert.equal(titleLine(tr),'English title found on Wikidata.');
  // A series he types is his: "entered by you", and no English-name part.
  inputs.series.value='Моя серия';inputs.series.handlers.input();await inputs.series.handlers.blur();await tick();await tick();
  assert.equal(placeLine(tr),'Series: Моя серия · No. 2 · entered by you');
  // An editor that reads another series than the row shows (no preview yet) says nothing it cannot know.
  answers['/api/candidate/names']=()=>ok(editor('Другая серия'));answers['/api/candidate/approve-preview']=()=>new Promise(()=>{});
  paint([tagged]);await run('namesToggle("cand-e")');await tick();await tick();
  assert.equal(placeLine(trOf('cand-e')),"Series: Другая серия · No. 2 · from the file's tags");

  // 6. Nothing is added for the title itself or for the author's name (no new words, no origin for the spelling).
  for(const absent of ['English author','Author found on','Author name from','surname'])assert.ok(!source.includes(absent),absent);
  assert.equal(source.split('English title found on ').length-1,1,'one home for the sentence');
  console.log('PASS 0.31.0 English names: the Title line (sources, place, none for Russian, not found, no answer or a typed title), the Place line\'s English-name part only where true, on asking rows and in the open editor');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_english_names_frontend.js'),module);m.filename=path.join(__dirname,'test_english_names_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

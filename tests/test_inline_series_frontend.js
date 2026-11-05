'use strict';
// Ruling62: real row code, one inline draft/preview/Approve; DOM/transport doubles only.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const posts=[],answers={};const baseFetch=context.fetch;
context.fetch=async(route,options)=>{const data=options?.body?JSON.parse(options.body):undefined;if(answers[route]){posts.push({route,data});return answers[route](data);}return baseFetch(route,options);};
const ok=value=>({ok:true,status:200,json:async()=>value});const tick=()=>new Promise(r=>setImmediate(r));
const row={id:'cand-inline',path:'cand-inline',kind:'candidate',library:'Audiobooks',revision:1,fingerprint:'a'.repeat(64),scope:'private fixture',preview:{path:''},metadata:{tags:{}},title_clue:'Мистер Вечный Канун. Уэлихолн',artists:[],members:[{path:'X:\\private\\story.mp3'}],review:{},review_context:{},status:'Held',creation:{status:'Held',can_create:false,reasons:[]},automatic:{state:'Held'},source_directory_count:1,
 place:{series:'',number:'',universe:'',collection:false},ask:{kind:'author_unclear',why:'two_people',fields:{title:{proposal:'Мистер Вечный Канун. Уэлихолн',basis:'tag'},author:{proposal:'Олег Яковлев',basis:'tag'}},candidates:[{name:'Олег Яковлев'},{name:'Владимир Торин'}],destination:{path:'old.m4b'}}};
function paint(){context.fixture=row;run('rows=[fixture];view="candidates";filters.candidates="output_attention";renderRows(true);controls()');}
function controls(){return run('askRows.get("cand-inline").controls');}function input(name){return controls().find(x=>x.dataset.name===name);}function type(name,value){const e=input(name);e.value=value;e.handlers.input();}
const call=route=>posts.filter(p=>p.route===route).at(-1)?.data;
(async()=>{
 answers['/api/candidate/approve-preview']=data=>ok({preview:{path:(data.names?.series || 'standalone')+'\\'+(data.names?.number || '')+' - '+(data.title || row.title_clue)+'.m4b',absolute:'',taken:false,place:{},applies:1}});
 answers['/api/candidate/approve']=data=>ok({queued:true,id:'q-inline',position:1,blocker:{kind:'scan'}});
 answers['/api/candidate/names']=()=>ok({editor:{fields:{title:{proposal:row.title_clue},author:{proposal:'Олег Яковлев'},series:{proposal:''},number:{proposal:''},universe:{proposal:'Existing universe'},collection:{proposal:false}},universes:[],series:['Existing series'],remembered:[],entered:[],job:'none'}});
 paint();
 for(const name of ['title','series','number'])assert.equal(controls().filter(x=>x.dataset.name===name).length,1,'one '+name+' without Edit names');
 assert.equal(input('title').value,row.title_clue,'no automatic prefix stripping');assert.equal(run('namesFor(rows[0])'),null,'untouched blank pair not an answer');assert.equal(posts.filter(p=>p.route==='/api/candidate/names').length,0,'no per-row editor read');
 assert.ok(controls().indexOf(controls().find(x=>String(x.className).includes('ask-other')))<controls().indexOf(input('title')),'Author Other precedes Title');
 run('attentionGroup="author_unclear";selectedBooks.set("cand-inline",1)');type('series','Temporary');type('number','1');input('number').handlers.blur();await tick();assert.equal(Object.hasOwn(call('/api/candidate/approve-preview'),'title'),false,'untouched nonempty proposed Title is not promoted to user authority (R49)');assert.equal(Object.hasOwn(call('/api/candidate/approve-preview'),'author'),false,'unchanged proposed author is not an English-spelling answer (R59)');assert.equal(run('approveSelectable().items.length'),0,'typed inline series cannot be bulk-approved as is');run('delete askDraft("cand-inline").series;delete askDraft("cand-inline").number');paint();
 const other=run('askRows.get("cand-inline").other');other.value='Олег Яковлев, Владимир Торин';other.handlers.input();type('title','Уэлихолн');type('series','Мистер Вечный Канун');
 assert.equal(run('askInert(rows[0])'),'Type the number in the series, or clear the series.');assert.equal(run('askValues(rows[0]).author'),'Олег Яковлев, Владимир Торин');
 type('number','1');input('number').handlers.blur();await tick();assert.equal(run('askInert(rows[0])'),'');
 assert.deepEqual(call('/api/candidate/approve-preview').names,{series:'Мистер Вечный Канун',number:'1'});assert.equal(call('/api/candidate/approve-preview').title,'Уэлихолн');assert.equal(call('/api/candidate/approve-preview').author,other.value);
 // Refresh retains one draft and author choice, then full editor adds only broader controls.
 paint();assert.equal(input('series').value,'Мистер Вечный Канун');assert.equal(input('title').value,'Уэлихолн');assert.equal(run('askDraft("cand-inline").choice'),'other');
 const normalNames=answers['/api/candidate/names'];let releaseNames;answers['/api/candidate/names']=()=>new Promise(resolve=>{releaseNames=()=>resolve(normalNames());});const opening=run('namesToggle("cand-inline")');await tick();assert.deepEqual(JSON.parse(run('JSON.stringify(namesFor(rows[0]))')),{series:'Мистер Вечный Канун',number:'1'},'opening broader editor never drops inline payload while loading');type('number','');assert.equal(run('askInert(rows[0])'),'Type the number in the series, or clear the series.','loading cannot bypass paired validation');type('number','1');releaseNames();await opening;await tick();
 for(const name of ['title','series','number'])assert.equal(controls().filter(x=>x.dataset.name===name).length,1,'no duplicated '+name+' in editor');
 assert.equal(run('namesValues(rows[0]).author'),'Олег Яковлев, Владимир Торин','full editor shares radio/Other author');assert.equal(input('series').value,'Мистер Вечный Канун','late names read never overwrites edited series');
 run('namesClose("cand-inline",true)');assert.equal(input('number').value,'1','collapse retains inline draft');
 await run('askPreview(askRows.get("cand-inline"),0)');await run('askPress(askRows.get("cand-inline"),"approve")');
 const sent=call('/api/candidate/approve');assert.equal(sent.author,'Олег Яковлев, Владимир Торин');assert.equal(sent.title,'Уэлихолн');assert.deepEqual(sent.names,{series:'Мистер Вечный Канун',number:'1'});assert.equal(sent.path,'Мистер Вечный Канун\\1 - Уэлихолн.m4b');assert.equal(posts.filter(p=>p.route==='/api/candidate/names-save').length,0,'one Approve, no earlier Save');
 run('askDone.clear();queueState.queued=[];queueState.running=null;askPendings.clear()');
 type('series','');type('number','');assert.deepEqual(JSON.parse(run('JSON.stringify(namesFor(rows[0]))')),{series:'',number:''},'intentional clearing is explicit');assert.equal(input('title').value,'Уэлихолн');assert.equal(run('askValues(rows[0]).author'),'Олег Яковлев, Владимир Торин');

 // Title-unclear/title_series reuses the exact inline pair without adding an author or a second Title.
 Object.assign(row,{title_clue:'Оттенки магии01. Темный оттенок магии',place:{series:'',number:''},ask:{kind:'title_author',why:'title_series',fields:{title:{proposal:'Темный оттенок магии',basis:'tag'},author:{proposal:'Schwab Victoria',basis:'tag'}},split:{series:'Оттенки магии',number:'1',title:'Темный оттенок магии'},destination:{path:'preview.m4b'}}});
 run('askDrafts.clear();namesState.clear();askDone.clear();askResults.clear();queueState.queued=[];queueState.running=null');paint();
 for(const name of ['title','series','number'])assert.equal(controls().filter(e=>e.dataset.name===name).length,1);
 assert.equal(controls().filter(e=>e.dataset.name==='author').length,0,'Title question gains no author field');
 type('series','Оттенки магии');type('number','1');input('number').handlers.blur();await tick();
 assert.equal(Object.hasOwn(call('/api/candidate/approve-preview'),'title'),false,'pair-only Title-row edit preserves R49 untouched title authority');
 assert.equal(Object.hasOwn(call('/api/candidate/approve-preview'),'author'),false,'pair-only never reanswers English author');
 answers['/api/candidate/names']=()=>ok({editor:{fields:{title:{proposal:'Темный оттенок магии'},author:{proposal:'Schwab Victoria'},series:{proposal:''},number:{proposal:''},universe:{proposal:''},collection:{proposal:false}},universes:['Warhammer 40K','SCP','Eve Online','World of Warcraft','Learned custom universe'],series:[],remembered:[],entered:[],job:'none'}});
 await run('namesToggle("cand-inline")');for(const name of ['title','author','series','number'])assert.equal(controls().filter(e=>e.dataset.name===name).length,1,'full editor retains one '+name);assert.equal(input('series').value,'Оттенки магии');run('namesClose("cand-inline",true)');assert.equal(input('number').value,'1');assert.equal(controls().filter(e=>e.dataset.name==='author').length,0,'collapse restores title-only inline author plan');
 await run('namesToggle("cand-inline")');
 const universeList=run('namesRows.get("cand-inline").box').children.find(element=>element.id==='names-universes-cand-inline');
 assert.deepEqual(universeList.children.map(option=>option.value),['Warhammer 40K','SCP','Eve Online','World of Warcraft','Learned custom universe']);
 const universeInput=run('namesRows.get("cand-inline").inputs.universe');
 universeInput.value='My new custom universe';universeInput.handlers.input();
 assert.equal(run('namesValues(rows[0]).universe'),'My new custom universe','suggestions remain an editable field');
 universeInput.value='SCP';universeInput.handlers.input();assert.equal(run('namesValues(rows[0]).universe'),'SCP');
 universeInput.value='';universeInput.handlers.input();
 run('namesClose("cand-inline",true)');
 const receipt='Answer saved. This book still needs its series confirmed. Enter Series and Number, then press Approve. This book has not been queued or filed.';
 answers['/api/candidate/approve']=()=>ok({saved:true,code:'series_needed',message:receipt});
 const focus=input('number');context.document.activeElement=focus;await run('askPress(askRows.get("cand-inline"),"approve")');paint();
 assert.equal(run('askResults.get("cand-inline").text'),'Approval saved for Оттенки магии01. Темный оттенок магии. '+receipt);assert.equal(run('askResults.get("cand-inline").warn'),false);assert.equal(run('askDone.has("cand-inline")'),false);
 assert.equal(input('series').value,'Оттенки магии');assert.equal(input('number').value,'1');assert.equal(context.document.activeElement,focus,'saved receipt never moves focus');
 run('applyQueueOutcome({id:"saved-q",action:"approve",book_id:"cand-inline",result:"saved",code:"series_needed",answer:{saved:true,code:"series_needed",message:'+JSON.stringify(receipt)+'}})');
 assert.equal(run('askResults.get("cand-inline").text'),receipt);assert.equal(run('askResults.get("cand-inline").warn'),false);assert.equal(run('askDone.has("cand-inline")'),false);
 run('applyQueueOutcome({id:"failed-q",action:"approve",book_id:"cand-inline",result:"refused",code:"refused",error:"Unexpected fixture refusal"})');
 assert.ok(run('askResults.get("cand-inline").text').includes('Approve cancelled: unexpected fixture refusal'),'unrelated failures retain the existing refusal path');

 answers['/api/queue/ack']=()=>ok({acked:true});run('rows=[];askRows.clear()');
 run('applyQueueOutcome({id:"saved-absent",action:"approve",book_id:"absent-book",title:"Hidden book",result:"saved",code:"series_needed",answer:{saved:true,code:"series_needed",message:'+JSON.stringify(receipt)+'}})');await tick();
 assert.equal(run('askResults.get("absent-book").text'),receipt,'saved receipt retained when row is filtered/paged away');assert.equal(run('askResults.get("absent-book").warn'),false);assert.ok(posts.filter(p=>p.route==='/api/queue/ack').some(p=>p.data.ids.includes('saved-absent')),'missing-row saved outcome acknowledged without a throw');paint();

 type('title','My explicit title');type('series','My series');type('number','2');await run('askPreview(askRows.get("cand-inline"),0)');answers['/api/candidate/approve']=data=>ok({queued:true,id:'q-title',position:1,blocker:{kind:'scan'}});await run('askPress(askRows.get("cand-inline"),"approve")');
 assert.equal(call('/api/candidate/approve').title,'My explicit title');assert.deepEqual(call('/api/candidate/approve').names,{series:'My series',number:'2'});

 // The normal Edit names entry must terminate an unusable reply and allow a fresh read.
 run('askPendings.clear();askDone.clear();queueState.queued=[];queueState.running=null;namesState.clear();namesNotes.clear()');paint();
 const beforeLoad=run('JSON.stringify(askDraft("cand-inline"))');
 answers['/api/candidate/names']=()=>ok({editor:null});
 run('namesRows.get("cand-inline").button.handlers.click({stopPropagation(){}})');await tick();await tick();
 assert.equal(run('namesOpen("cand-inline")'),false,'a malformed successful response must not leave Loading these names forever');
 assert.equal(run('namesNotes.get("cand-inline").text'),"Couldn't load this book's names. Press Edit names to try again.");
 assert.equal(run('JSON.stringify(askDraft("cand-inline"))'),beforeLoad,'failed loading preserves the pre-existing title/series draft');
 answers['/api/candidate/names']=()=>ok({editor:{fields:{title:{proposal:'Server title'},author:{proposal:'Schwab Victoria'},series:{proposal:'Server series'},number:{proposal:'1'},universe:{proposal:'Existing universe'},collection:{proposal:false}},remembered:[],entered:[],job:'none'}});
 run('namesRows.get("cand-inline").button.handlers.click({stopPropagation(){}})');await tick();await tick();
 assert.equal(run('namesOpen("cand-inline")'),true);assert.ok(run('namesRows.get("cand-inline").inputs.universe'),'Universe is reachable without optional suggestion lists');
 assert.equal(run('namesValues(rows[0]).title'),'My explicit title','loading never resets a title entered before opening');
 assert.equal(run('namesValues(rows[0]).series'),'My series','the inline series and full editor share one draft');
 run('namesChangedField(rows[0],"title","Editor-only title");namesClose("cand-inline")');
 assert.equal(input('title').value,'My explicit title','Discard restores the title draft that existed before opening');
 const validNames=answers['/api/candidate/names'];let oldReply,newReply;
 run('namesState.get("cand-inline").data=null');answers['/api/candidate/names']=()=>new Promise(resolve=>oldReply=resolve);
 run('namesRows.get("cand-inline").button.handlers.click({stopPropagation(){}})');await tick();
 run('namesClose("cand-inline",true)');answers['/api/candidate/names']=()=>new Promise(resolve=>newReply=resolve);
 run('namesRows.get("cand-inline").button.handlers.click({stopPropagation(){}})');await tick();
 const currentNames=await validNames();currentNames.json=async()=>({editor:{fields:{title:{proposal:'Fresh title'},author:{proposal:'Schwab Victoria'},series:{proposal:'Fresh series'},number:{proposal:'1'},universe:{proposal:'Fresh universe'},collection:{proposal:false}},remembered:[],entered:[],job:'none'}});
 newReply(currentNames);await tick();await tick();oldReply(await validNames());await tick();await tick();
 assert.equal(run('namesData("cand-inline").fields.universe.proposal'),'Fresh universe','a closed older request cannot overwrite a reopened editor');
 run('namesClose("cand-inline",true);namesState.get("cand-inline").data=null');
 answers['/api/candidate/names']=()=>new Promise(resolve=>oldReply=resolve);
 run('namesRows.get("cand-inline").button.handlers.click({stopPropagation(){}})');await tick();row.revision+=1;paint();oldReply(await validNames());await tick();await tick();
 assert.equal(run('namesOpen("cand-inline")'),false,'an answer for a stale revision ends loading and can be retried');
 assert.equal(run('namesNotes.get("cand-inline").text'),"Couldn't load this book's names. Press Edit names to try again.");
 // A read that never answers has the existing 30-second read deadline, then the same actionable retry.
 const savedFetch=context.fetch,savedTimer=context.setTimeout;let deadline;
 context.AbortController=AbortController;context.setTimeout=(callback,ms)=>{if(ms===30000)deadline=callback;return 0;};
 context.fetch=(route,options)=>route==='/api/candidate/names'?new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('aborted')))):savedFetch(route,options);
 run('namesRows.get("cand-inline").button.handlers.click({stopPropagation(){}})');await tick();assert.equal(typeof deadline,'function');deadline();await tick();await tick();
 assert.equal(run('namesOpen("cand-inline")'),false,'a stalled read cannot keep Loading these names visible indefinitely');
 assert.equal(run('namesNotes.get("cand-inline").text'),"Couldn't load this book's names. Press Edit names to try again.");
 context.fetch=savedFetch;context.setTimeout=savedTimer;
 context.extraRow={creation:{job:{task_kind:'duplicate_source_cleanup',state:'Extra source removed. Finished audiobook kept.'}},audiobook_ready:false};
 assert.equal(run('candidateStatus(extraRow)'),'Extra source removed. Finished audiobook kept.');
 context.extraActivity={kind:'conversion',task_kind:'duplicate_source_cleanup',step:'checking extra source',state:'running'};
 assert.equal(run('activityLabel(extraActivity)'),'Checking extra source');assert.equal(run('activityStep(extraActivity,false)'),'Checking extra source');
 context.extraActivity.kind='cleanup';assert.equal(run('activityLabel(extraActivity)'),'Removing extra source');
 context.extraActivity.state='attention';assert.equal(run('activityLabel(extraActivity)'),'Extra source kept');
 console.log('inline author/title/series draft, preview, approval and editor reuse: passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
eval(harness);

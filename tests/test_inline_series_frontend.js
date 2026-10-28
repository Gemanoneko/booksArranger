'use strict';
// Ruling62: real row code, one inline draft/preview/Approve; DOM/transport doubles only.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const posts=[],answers={};const baseFetch=context.fetch;
context.fetch=async(route,options)=>{const data=options?.body?JSON.parse(options.body):undefined;if(answers[route]){posts.push({route,data});return answers[route](data);}return baseFetch(route,options);};
const ok=value=>({ok:true,status:200,json:async()=>value});const tick=()=>new Promise(r=>setImmediate(r));
const row={id:'cand-inline',path:'cand-inline',kind:'candidate',library:'Audiobooks',revision:1,scope:'private fixture',preview:{path:''},metadata:{tags:{}},title_clue:'Мистер Вечный Канун. Уэлихолн',artists:[],members:[{path:'X:\\private\\story.mp3'}],review:{},review_context:{},status:'Held',creation:{status:'Held',can_create:false,reasons:[]},automatic:{state:'Held'},source_directory_count:1,
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
 console.log('inline author/title/series draft, preview, approval and editor reuse: passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
eval(harness);

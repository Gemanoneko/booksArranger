'use strict';
// 0.29.0 item 4 (Light novel, Judy's 0.29.0 UX section 4) on the real frontend, with the Retry test's DOM and transport
// doubles: the Edit names field, its Place lead and Entered line, the Remembered Yes/No, and the details panel's review.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
(async()=>{
  run('state='+JSON.stringify(backend));
  assert.equal(run('JSON.stringify(NAMES_FIELDS)'),JSON.stringify(['title','author','series','number','universe','collection','light_novel']));
  assert.equal(run('NAMES_LABELS.light_novel'),'Light novel');
  assert.equal(run('NAMES_TIPS.light_novel'),'File this book under Light Novels, then by author and series as usual. Use it for light novels.');
  // The Place line gains the lead; a plain book reads as before.
  assert.equal(run("placeText({universe:'',series:'Иная',number:'1',collection:false,light_novel:true})"),'Light novel · Series: Иная · No. 1');
  assert.equal(run("placeText({universe:'',series:'Иная',number:'1',collection:false})"),'Series: Иная · No. 1');
  assert.equal(run("enteredText(['series','light_novel'])"),'Entered by you: series, light novel.');
  assert.equal(run("enteredText(['collection'])"),'Entered by you: collection.');
  assert.equal(run("NAMES_BOOL.has('light_novel') && NAMES_BOOL.has('collection')"),true);
  // Futaba O-r2-1: Light novel ticked in Edit names, Save: the Goes to line keeps the Light Novels path until the list
  // brings the engine's own (it flipped back to the old path for about 1.6 s).
  const answers={},baseFetch=context.fetch,ok=value=>({ok:true,status:200,json:async()=>value}),tick=()=>new Promise(resolve=>setImmediate(resolve));
  context.fetch=async(route,options)=>answers[route]?answers[route](options?.body?JSON.parse(options.body):undefined):baseFetch(route,options);
  const OLD='Толстой Лев\\Книга Без - Толстой Лев.m4b',LN='Light Novels\\Толстой Лев\\Книга Без - Толстой Лев.m4b',SHOWN='Audiobooks Sorted\\'+LN;
  context.book={id:'ln1',path:'ln1',kind:'candidate',library:'Audiobooks',revision:1,fingerprint:'c'.repeat(64),scope:'private fixture',preview:{path:''},metadata:{tags:{}},title_clue:'Книга Без',artists:[],members:[{path:'X:\\private\\ln1.mp3'}],review:{},review_context:{},status:'Held',creation:{status:'Held',can_create:false,reasons:[]},automatic:{state:'Held'},source_directory_count:1,
    ask:{kind:'title_author',why:'author_missing',fields:{title:{proposal:'Книга Без',basis:'tag'},author:{proposal:'Толстой Лев',basis:'folder_name'}},candidates:[],destination:{path:OLD,absolute:'',taken:false,reason:''}}};
  const proposal=value=>({proposal:value,basis:''});
  answers['/api/candidate/names']=()=>ok({editor:{fields:{title:proposal('Книга Без'),author:proposal('Толстой Лев'),series:proposal(''),number:proposal(''),universe:proposal(''),collection:proposal(false),light_novel:proposal(false)},read:{},remembered:[],universes:[],series:[],job:'none',place:{universe:'',series:'',number:'',collection:false},destination:{path:OLD},entered:[],applies:1}});
  answers['/api/candidate/approve-preview']=data=>ok({preview:{path:data.names?.light_novel===true?LN:OLD,absolute:'',taken:false,place:{},applies:1}});
  answers['/api/candidate/names-save']=()=>ok({outcome:'saved',applies:1,job:'none',entered:['light_novel']});
  run('state={...state,audiobook_output_root:"Z:\\\\Audiobooks Sorted"};view="candidates";filters.candidates="output_attention";rows=[book];renderRows(true)');
  await run('namesToggle("ln1")');await tick();await tick();
  assert.equal(run('namesOpen("ln1")'),true);
  run('namesChangedField(rows[0],"light_novel",true)');await run('askPreview(askRows.get("ln1"),0)');await tick();
  assert.equal(run('destPlan(rows[0]).path'),SHOWN,'positive control: the live preview follows the box');
  await run('namesSave("ln1")');await tick();
  assert.match(run('namesNotes.get("ln1").text'),/^Saved names/);
  assert.equal(run('destPlan(rows.find(row=>row.id==="ln1")).path'),SHOWN,'after Save the line keeps the saved path, never the old one');
  // The next list read brings the engine's path, which then stands on its own.
  run('rows=[{...book,ask:{...book.ask,destination:{path:'+JSON.stringify(LN)+',absolute:"",taken:false,reason:""}}}];renderRows(true)');
  assert.equal(run('destPlan(rows[0]).path'),SHOWN);
  console.log('PASS 0.29.0 Light novel on the page: Edit names field, Place lead, Entered line, Goes to after Save');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_light_novel_frontend.js'),module);m.filename=path.join(__dirname,'test_light_novel_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

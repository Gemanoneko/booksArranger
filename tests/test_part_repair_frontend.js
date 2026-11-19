'use strict';
// 0.30.0 item C (Judy's spec section 9) on the real page, with the Retry test's DOM and transport doubles: a damaged M4B part
// repaired before the join. The jobs panel and the manual job block read the same conversion row (step `repairing`, unit
// `parts`, the file in the tooltip); the manual window's track count line, its stop lines and its end line; the Needs
// attention row sentence.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const server=new Map(),folder='Z:\\Audiobooks\\Впусти меня';
let picked=[folder+'\\Впусти меня 1.m4b',folder+'\\Впусти меня 3.m4b'];
const baseFetch=context.fetch,response=result=>({ok:true,status:200,json:async()=>result});
context.booksDesktop={chooseFolder:async()=>null,chooseAudioFiles:async()=>null,chooseAudiobookOutput:async()=>null};
for(const id of ['manual-folder-load','pause-jobs','resume-jobs'])get(id).click=()=>get(id).handlers.click?.();
context.fetch=async(route,options)=>{
  if(!route.startsWith('/api/manual-conversion'))return baseFetch(route,options);
  const body=options.body?JSON.parse(options.body):null;
  if(route==='/api/manual-conversion')return response({drafts:[...server.values()]});
  if(route.endsWith('/inspect'))return response({source:body,tracks:picked.map(p=>({path:p,included:true})),suggestions:{title:'Впусти меня',author:'Линдквист'},
    inspections:picked.map((_,i)=>String(i).repeat(64)),match_source:''});
  throw new Error('Unexpected manual route '+route);
};
const click=id=>get(id).handlers.click();
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const row=extra=>({id:'conversion:j1',kind:'conversion',label_key:'conversion',subject:'Впусти меня',book_id:'b1',job_id:'j1',step:'repairing',step_text:'Впусти меня 3.m4b',
  state:'running',done:1,total:2,unit:'parts',fraction:null,started:1,count:null,task_kind:null,...extra});
(async()=>{
  run('state='+JSON.stringify(backend));
  // One string, two places: the step and the measure of the conversion row (positive control: "Working" and "50%" before).
  context.r=row({});
  assert.equal(run('workStep(r,false)'),'Step 1 of 4 - Repairing a damaged part');
  assert.equal(run('workDetail(r,false)'),'1 of 2 parts');
  assert.equal(run('repairTip(r)'),'Repairing Впусти меня 3.m4b');
  context.r=row({state:'paused'});assert.equal(run('workStep(r,false)'),'Paused - Step 1 of 4 - Repairing a damaged part');
  context.r=row({done:0,total:1});assert.equal(run('workDetail(r,false)'),'0 of 1 part');
  context.r=row({done:null,total:null,unit:null});assert.equal(run('workDetail(r,false)'),'','slides until the engine knows how many parts are damaged');
  context.r=row({step:'encoding',step_text:null});assert.equal(run('repairTip(r)'),'','no tooltip outside the repair');
  // The jobs panel row: its step line and the file in its tooltip.
  run('activityRows.clear()');context.r=row({});run('renderActivities([r],{state:"Running"})');
  const view=run('activityRows.get("conversion:j1")');
  assert.equal(view.step.textContent,'Step 1 of 4 - Repairing a damaged part');assert.equal(view.step.title,'Repairing Впусти меня 3.m4b');assert.equal(view.detail.textContent,'1 of 2 parts');

  // The manual window's stop lines and end line.
  const stopped={state:'failed',originals_untouched:true,reopen_allowed:true};
  context.d={...stopped,part_repair:{kind:'unrepairable',file:'Впусти меня 3.m4b'}};
  // Sergei's ruling on damaged parts (2026-11-19): get a new copy; no Retry and no Reopen draft hint, whatever stopped the repair.
  assert.equal(run('partRepairLine(d)'),"Conversion stopped. Впусти меня 3.m4b is damaged and can't be repaired safely. Original kept. Get a new copy of this book.");
  context.d={...stopped,originals_untouched:false,part_repair:{kind:'failed',file:'Впусти меня 3.m4b'}};
  assert.equal(run('partRepairLine(d)'),"Conversion stopped. Впусти меня 3.m4b is damaged and can't be repaired safely. Get a new copy of this book.");
  context.d={state:'converted',repaired_parts:1,originals_untouched:true};assert.equal(run('repairedPartsLine(d)'),' Repaired 1 damaged part. Original kept.');
  context.d={state:'cleanup',repaired_parts:2,originals_untouched:false};assert.equal(run('repairedPartsLine(d)'),' Repaired 2 damaged parts.');
  context.d={state:'running',repaired_parts:1};assert.equal(run('repairedPartsLine(d)'),'','only when the job ends');
  context.d={state:'failed',reason:'x'};assert.equal(run('partRepairLine(d)'),'');

  // The Needs attention row: the same sentence, " Original kept." only when the engine says so.
  const media=code=>({media_failure:{schema:'books-media-failure-v1',code,filename:'Впусти меня 3.m4b',status:'Need to reacquire',
    hint:'Впусти меня 3.m4b is damaged and cannot be repaired safely. Delete the book, then get a new copy.'},originals_untouched:true});
  context.a=media('m4b_part_unrepairable');
  assert.deepEqual(JSON.parse(JSON.stringify(run('mediaFailureText(a)'))),{status:'Need to reacquire',hint:'Впусти меня 3.m4b is damaged and cannot be repaired safely. Delete the book, then get a new copy. Original kept.',warn:true});
  context.a=media('m4b_part_repair_failed');assert.equal(run('mediaFailureText(a)').status,'Need to reacquire');

  // The window before queueing: the track count line says the repair, only for a join that includes an .m4b.
  click('manual-conversion-tab');await flush();
  const radio=get('manual-source-folder');radio.checked=true;radio.handlers.change();
  const input=get('manual-folder-path');input.value=folder;input.handlers.input();
  await click('manual-folder-load');await flush();
  assert.equal(get('manual-track-count').textContent,'2 included files. One M4B plays them in the order shown. Damaged M4B parts are repaired automatically when this book is converted.');
  const boxes=get('manual-track-list').children.map(item=>item.children[1].children[2].children[0]);
  boxes[1].checked=false;boxes[1].handlers.change();
  assert.equal(get('manual-track-count').textContent,'1 included file. One M4B plays them in the order shown.','one file is not joined: nothing to repair');
  console.log('PASS 0.30.0 damaged M4B parts on the page: the repair step, the stop and end lines, the row sentence');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
new Function('require','__dirname',harness)(require,__dirname);

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

  // Futaba 0.30.0 slice D, follow-up 1 (Sergei's ruling: "just tell me to reacquire"): a draft stopped by a part the app
  // can't repair shows the stop line alone. No Retry and no Reopen draft, though the engine would still accept a reopen.
  const stoppedDraft={id:'d0a1b2c3-0000-4000-8000-000000000001',revision:2,state:'failed',job_id:'job-stopped',candidate_id:'d0a1b2c3-0000-4000-8000-000000000001',
    source:{kind:'folder',path:folder},tracks:picked.map(p=>({path:p,included:true})),metadata:{title:'Впусти меня (остановлено)',author:'Линдквист'},destination:'D:\\Готово\\Впусти меня.m4b',
    reason:'Source 2 of 2 failed full audio decoding',stage:'checking sources',part_repair:{kind:'unrepairable',file:'Впусти меня 3.m4b'},originals_untouched:true,
    retry_allowed:false,reopen_allowed:true};
  server.set(stoppedDraft.id,stoppedDraft);
  click('manual-conversion-tab');await flush();
  const stoppedButton=get('manual-books').children.map(row=>row.children[0]).find(button=>button.textContent===stoppedDraft.metadata.title);
  assert(stoppedButton,'the stopped draft is listed');stoppedButton.handlers.click();
  assert.match(get('manual-editor-status').textContent,/Get a new copy of this book\.$/);
  assert.equal(get('manual-job-retry').hidden,true,'no Retry');
  assert.equal(get('manual-job-reopen').hidden,true,'no Reopen draft: the stop line stands alone');
  // Futaba 0.30.0 slice D, follow-up 3: a single M4B cut inside its last frame failed its full decode (so the engine keeps a
  // replace-source fact), yet its damage is repairable: the row is "Damaged — can repair", never "the MP3 ... can't be repaired".
  const remedied=(group,path,extra={})=>({id:'r1',kind:'candidate',creation:{job:{state:'Output needs attention',job_id:'job-r1',attention:{group,originals_untouched:true,
    remedy:{kind:'replace_source',cause:'source_decode_failed',path,source_index:0,source_count:1},...extra}}}});
  context.fixture=remedied('repair','Z:\\Audiobooks\\Впусти меня.m4b',{damage:[{kind:'truncated_final_frames',frames:1,replaced_ticks:1024,timescale:44100,description:'d'}],repair:{allowed:true,reason:''}});
  const cutText=run('attentionText(fixture)');
  assert.equal(cutText.status,'Damaged — can repair');assert.doesNotMatch(JSON.stringify(cutText),/MP3|can't be repaired/);
  // The replace-source line names the file's own type (positive control for the word: always "The MP3" before).
  context.fixture=remedied('other','Z:\\Audiobooks\\Книга.mp3');
  assert.equal(run('attentionText(fixture)').hint,"The MP3 failed its full audio check and can't be repaired by the app. Delete the book, then get a new copy.");
  context.fixture=remedied('other','Z:\\Audiobooks\\Книга.flac');
  assert.equal(run('attentionText(fixture)').hint,"The FLAC file failed its full audio check and can't be repaired by the app. Delete the book, then get a new copy.");
  // Any other stopped draft keeps its Reopen draft.
  server.set(stoppedDraft.id,{...stoppedDraft,part_repair:undefined,reason:'An output already exists'});
  click('manual-conversion-tab');await flush();
  get('manual-books').children.map(row=>row.children[0]).find(button=>button.textContent===stoppedDraft.metadata.title).handlers.click();
  assert.equal(get('manual-job-reopen').hidden,false);
  console.log('PASS 0.30.0 damaged M4B parts on the page: the repair step, the stop and end lines, the row sentence');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
new Function('require','__dirname',harness)(require,__dirname);

'use strict';
// Real renderer, existing in-memory DOM/transport doubles. No app, dialog,
// browser, network, source files or personal library is opened.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const value=expression=>JSON.parse(JSON.stringify(run(expression)));
function stateWith(jobs={},automatic={}){
  backend={...backend,activities:[],audiobook_jobs:{state:'Paused',queued:2,failed:0,approved_total:2,converted_total:0,...jobs},automatic_processing:{state:'Paused',can_start:true,can_stop:false,research:{researching:0,waiting:2,held:0},reason:'',...automatic}};
  run('state='+JSON.stringify(backend)+';ended=false;recoveryDisconnected=false;renderJobs();renderAutomatic();controls()');
}
const answer=body=>({ok:true,status:200,json:async()=>body});
(async()=>{
  // Known and historical pause origins remain distinct; old restart flags do not invent an origin.
  for(const [origin,copy] of [['user','Paused by you.'],['update','Paused for an update.'],['closing','Paused when Books Arranger closed.'],['interrupted','Paused after an interruption.'],['unknown','Paused.']]){
    stateWith({pause:{origin}},{pause:{origin},restart_paused:true});
    assert.ok(get('jobs-help').textContent.includes(copy+' Resume continues pending work.'));
    assert.equal(get('automatic-detail').textContent,copy+' Start automatic processing to continue.');
  }
  stateWith({}, {restart_paused:true});assert.equal(get('automatic-detail').textContent,'Paused. Start automatic processing to continue.');
  stateWith({}, {reason:'The saved drive cannot be reached.'});assert.equal(get('automatic-detail').textContent,'The saved drive cannot be reached. Start automatic processing to continue.');

  // A real start check takes priority over saved paused cleanup; no invented count/bar/clock.
  stateWith({start_admission:{state:'checking',generation:9},maintenance:{phase:'Checking the audiobook before source-folder cleanup',job_id:'old',title:'Earlier book',state:'checking',cancel_requested:false}});
  run("state.activities=[{kind:'cleanup',state:'paused',step:'originals',done:0,total:19,unit:'files',step_started_at:1}];renderJobs();controls()");
  assert.ok(get('jobs-status').textContent.includes('Checking pending audiobook work'));
  assert.equal(get('pause-jobs').disabled,false);assert.equal(get('resume-jobs').disabled,true);
  assert.equal(get('pause-jobs').title,'Pause the start checks and keep pending work. The current read may finish before stopping.');
  assert.equal(get('jobs-rows').children[0].dataset.kind,'admission');
  assert.equal(run("activityRows.get('admission').bar.hidden"),true);assert.equal(run("activityRows.get('admission').time.hidden"),true);
  assert.equal(run("activityRows.get('maintenance').subject.textContent"),'Earlier book');
  assert.equal(run("activityRows.get('maintenance').detail.textContent"),'');
  assert.equal(run("activityRows.get('cleanup').detail.textContent"),'0 of 19 files');
  assert.equal(get('pause-jobs').getAttribute('aria-describedby'),'jobs-help jobs-status');
  stateWith({start_admission:{state:'running'}});assert.equal(run("activityRows.has('admission')"),false);assert.equal(run("activityRows.has('maintenance')"),false);
  stateWith({start_admission:{state:'stale'}});assert.ok(get('jobs-help').textContent.includes('Start checks stopped. Pending work is kept.'));
  stateWith({start_admission:{state:'closing'}});assert.equal(get('resume-jobs').disabled,true);assert.equal(get('resume-jobs').title,'Books Arranger is closing. Pending work is kept.');
  stateWith({maintenance:{state:'stopping',cancel_requested:true,phase:'Checking finished output'}});assert.equal(get('pause-jobs').disabled,true);assert.ok(get('jobs-help').textContent.startsWith('Stopping finished-book checks…'));
  for(const total of [null,-1,0,'4',NaN]){context.fixture={maintenance:{state:'checking',completed:0,total}};assert.equal(run("checkActivities([],fixture)[0].phase_only"),true);}

  // One Resume in flight; Pause is independently reachable once a real backend check is known.
  let resumeAnswer,pauseAnswer;const sent=[];const originalFetch=context.fetch;
  context.fetch=async(route,options)=>{
    if(route==='/api/audiobook/resume'){sent.push(route);return new Promise(resolve=>resumeAnswer=resolve);}
    if(route==='/api/audiobook/pause'){sent.push(route);return new Promise(resolve=>pauseAnswer=resolve);}
    return originalFetch(route,options);
  };
  stateWith();document.activeElement=get('resume-jobs');const resume=run("action('/api/audiobook/resume',{})");
  assert.ok(get('jobs-help').textContent.includes('Resume requested. Waiting for the app to respond.'));
  await run("action('/api/audiobook/resume',{})");assert.equal(sent.filter(x=>x.endsWith('/resume')).length,1);
  stateWith({start_admission:{state:'checking'}});const pausing=run("action('/api/audiobook/pause',{})");
  assert.equal(sent.filter(x=>x.endsWith('/pause')).length,1);assert.ok(get('jobs-help').textContent.includes('Pausing start checks…'));
  assert.equal(get('pause-jobs').disabled,true);
  await run("action('/api/audiobook/pause',{})");assert.equal(sent.length,2);
  stateWith({start_admission:{state:'stale'}});pauseAnswer(answer({state:'Paused'}));await pausing;
  resumeAnswer(answer({start_admission:{state:'stale'}}));await resume;
  assert.equal(document.activeElement,get('resume-jobs'),'requests do not move focus');

  // Queued Resume cancellation and race use explicit acknowledgement, never disappearance.
  context.fetch=async(route,options)=>route==='/api/audiobook/resume-cancel'?answer({cancelled:true}):originalFetch(route,options);
  stateWith({start_admission:{state:'waiting',reason:'pause'}});assert.equal(get('resume-jobs').title,'Resume queued. It starts when the pause finishes. Press Resume again to cancel.');
  backend.audiobook_jobs.start_admission={state:'stale'};await run("action('/api/audiobook/resume-cancel',{})");assert.equal(get('message').textContent,'Resume cancelled. Pending work is kept.');
  context.fetch=async(route,options)=>route==='/api/audiobook/resume-cancel'?{ok:false,status:409,json:async()=>({code:'started',error:'Already started'})}:originalFetch(route,options);
  await run("action('/api/audiobook/resume-cancel',{})");assert.ok(get('message').textContent.startsWith('Too late to cancel:'));

  // Slow automatic Start remains one request with purpose and adjacent explanation.
  let startAnswer;context.fetch=async(route,options)=>route==='/api/automatic/start'?new Promise(resolve=>{sent.push(route);startAnswer=resolve;}):originalFetch(route,options);
  stateWith();const starting=run("automaticAction('start')");assert.equal(get('automatic-request').textContent,'Start requested. Waiting for the app to respond.');assert.equal(get('start-automatic').disabled,true);
  await run("automaticAction('start')");assert.equal(sent.filter(x=>x==='/api/automatic/start').length,1);
  backend.automatic_processing={...backend.automatic_processing,state:'Running',can_start:false,can_stop:true};startAnswer(answer({automatic_processing:backend.automatic_processing}));await starting;
  for(const cancelled of [false,true]){
    stateWith({}, {start_pending:{kind:'scan'},can_start:false});
    context.fetch=async(route,options)=>route==='/api/automatic/cancel-start'?answer({cancelled,automatic_processing:{...backend.automatic_processing,start_pending:null}}):originalFetch(route,options);
    await run("automaticAction('cancel-start')");assert.equal(get('message').textContent,cancelled?'Start cancelled. Pending work is kept.':'Too late to cancel: automatic processing has already started.');
  }
  context.fetch=originalFetch;

  // Missing activity is neutral, both for membership and the attention-list sweep.
  stateWith({}, {state:'Running',research:{researching:0,waiting:2,held:0}});assert.equal(run('researchChecking()'),false);
  stateWith({}, {state:'Running',research:{researching:1,waiting:2,held:0}});assert.equal(run('researchChecking()'),true);
  const group=blocked({creation:{},ask:{kind:'files_unclear',membership:'checking',membership_checking:false,membership_reason:'unresolved_siblings',fields:{title:{proposal:'Book'},author:{proposal:'Author'}}}});
  context.fixture=group;assert.equal(run('membershipLine(fixture)'),'Other files in this folder may belong to this book.');
  group.ask.membership_reason='incomplete_scan';assert.equal(run('membershipLine(fixture)'),'The source folder has not been fully checked.');
  group.ask.membership_checking=true;assert.equal(run('membershipLine(fixture)'),'Checking which other files belong to this book.');
  assert.equal(run('CHECKING_TIP'),'Approve only the files shown as one book. Other files are not included.');

  // Exact diagnostic identity, unbounded times, condition and available recovery action.
  const d={file:'Очень длинное имя '.repeat(20)+'.m4b',path:'C:/private-fixture/source.m4b',chapter_title:'Длинная глава '.repeat(40),chapter_id:7,chapter_index:3,predicate:'end_exceeds_audio',start:2,end:442800.123,duration:4};
  context.diagnostic=d;assert.equal(run('chapterTime(diagnostic.end)'),'123:00:00.123');
  const refusal=run('chapterRefusal(diagnostic,fixture)');assert.ok(refusal.includes(d.file));assert.ok(refusal.includes(d.chapter_title));assert.ok(refusal.includes('123:00:00.123'));assert.ok(refusal.endsWith('Replace this source file, then Scan again.'));assert.ok(!refusal.includes('Nothing was changed'));
  for(const [predicate,copy] of [['start_before_audio','starts before the audio'],['end_not_after_start','has an end before its start'],['overlap','overlaps chapter “Earlier”'],['start_beyond_audio','starts beyond the audio'],['unreadable_time','has an unreadable time']]){d.predicate=predicate;d.previous_chapter_title='Earlier';assert.ok(run('chapterRefusal(diagnostic,fixture)').includes(copy));}
  d.predicate='complete_audio_unverified';d.reason='Decoder could not read packet 91';d.chapter_title='';assert.ok(run('chapterRefusal(diagnostic,fixture)').includes('chapter 7, the complete audio could not be verified: Decoder could not read packet 91'));
  group.admission_error={chapter_diagnostic:d};assert.ok(run('technicalText(fixture)').includes(d.path));assert.ok(run('technicalText(fixture)').includes('complete_audio_unverified'));
  context.failure={httpStatus:409,body:{admission_error:{chapter_diagnostic:d}}};assert.equal(run("askErrorText(failure,'approve',fixture)"),run('chapterRefusal(diagnostic,fixture)'));
  for(const [origin,copy] of [['automatic','with the automatic names'],['user','with your approved names'],['unknown','converting.']]){context.failure={httpStatus:409,body:{code:'book_converting',job_origin:origin}};const line=run("askErrorText(failure,'approve',fixture)");assert.ok(line.includes(copy));assert.ok(line.endsWith('Your new names were not applied.'));}
  assert.equal(run("namesSavedText(fixture,{outcome:'replanned'})"),'Names saved. Approve to queue this book with these names.');
  group.admission_error=undefined;group.chapter_corrections=[{file:'source.m4b',chapter_title:'Last',original_end:999,corrected_end:4}];group.audiobook_ready=false;assert.ok(!run('technicalText(fixture)').includes('corrected in the audiobook'));group.audiobook_ready=true;assert.ok(run('technicalText(fixture)').startsWith('Final chapter end corrected in the audiobook. Chapter names and start times are kept.'));
  group.chapter_check={phase:'Checking source audio',reason:'terminal_chapter_end',file:'source.m4b'};run('rows=[fixture];renderJobs()');assert.equal(run("activityRows.get('chapter').label.textContent"),'Checking source audio: ');assert.equal(run("activityRows.get('chapter').bar.hidden"),true);assert.ok(run('technicalText(fixture)').startsWith('Checking source audio:'));
  delete group.chapter_check;run('renderJobs()');assert.equal(run("activityRows.has('chapter')"),false,'no stale checking row after callback ends');run('rows=[]');

  // Protective folders and audio-like leftovers name the actual subject without an automatic retry promise.
  context.cleanupRow={creation:{job:{folder_cleanup:{protected:[{path:'C:/private-fixture/library',reason:'Source library folder is kept'},{path:'C:/private-fixture/library/author',reason:'Top-level source folder is kept'}],retained_details:[{path:'C:/private-fixture/library/author/book',state:'retained_nonempty',reason:'Audio files remain in the folder; retained: bonus.mp3.txt'}],retryable:false,absent_after_intent:1}}}};
  const retained=value('folderCleanupFacts(cleanupRow)');assert.ok(retained[0].includes('Source folder retained — it is a library folder.'));assert.ok(retained[1].includes('it is directly inside a library folder.'));assert.ok(retained[2].includes('audio may remain in bonus.mp3.txt.'));assert.ok(!retained.join(' ').includes('retry automatically'));assert.ok(retained.join(' ').includes('Removal outcome not confirmed'));
  context.cleanupRow.creation.job.folder_cleanup.retryable=true;context.cleanupRow.creation.job.folder_cleanup.reason='The source folder cannot be reached';context.cleanupRow.creation.job.folder_cleanup.retry_at=1893456000;
  const waiting=value('folderCleanupFacts(cleanupRow)').join(' ');assert.ok(waiting.includes('The app will retry automatically.'));assert.ok(waiting.includes('Next retry:'));

  // Current identity facts and computed shared destinations are displayed without changing credit.
  for(const [title,author,series,number,universe,destination] of [
    ['The Two Towers','J. R. R. Tolkien','Властелин колец',2,'Middle-earth','Middle-earth/Властелин колец/The Two Towers.m4b'],
    ['The Return of the King','J. R. R. Tolkien','Властелин колец',3,'Middle-earth','Middle-earth/Властелин колец/The Return of the King.m4b'],
    ['Omen','David Seltzer','Omen',1,'','Omen/Omen - David Seltzer.m4b']]){
    const row=blocked({creation:{},review:{},ask:{kind:'files_unclear',fields:{title:{proposal:title},author:{proposal:author}},series:{name:series,number},destination:{path:destination,absolute:'C:/private-fixture/sorted/'+destination}},place:{universe,series,number:String(number)}});context.identity=row;
    assert.equal(run('bookTitleText(identity)'),title);assert.equal(run('bookAuthor(identity)'),author);assert.equal(run('seriesLine(identity)'),'');assert.ok(run('placeText(identity.place)').includes('Series: '+series));assert.equal(run('destPlan(identity).absolute'),'C:/private-fixture/sorted/'+destination);
  }
  console.log('PASS 0.24.2 frontend: admission, maintenance, cancellation, pause origins, membership, chapter diagnostics, names, identity and routing display');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_0242_frontend.js'),module);m.filename=path.join(__dirname,'test_0242_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

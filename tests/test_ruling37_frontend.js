'use strict';
// The rest of ruling 35 (Sergei, ruling 37, 2026-10-26: "Finish ALL remaining 'wait until…' refusals before release") on
// the real frontend, with the Retry test's DOM and transport doubles. No server, no library.
// - Resume audiobook jobs is no longer disabled while jobs pause; pressed then, the engine keeps it ("It starts when the
//   pause finishes"), the button says so and, pressed again, takes it back.
// - Retry all and Convert pressed while a scan runs wait for it ("Scanning is running. Retry when it stops." was the
//   refusal) and are sent when it ends; a scan that began after the page looked (409 code scanning) is waited for too.
// - Delete recovery copies during a scan is accepted: the panel says it is queued and offers Cancel deletion.
// - S6: a delete refusal with no line of the page's own is said in the engine's words, never "Delete was not accepted".
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const answers={};const posts=[];const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(answers[route]){posts.push({route,data});return answers[route](data);}
  return baseFetch(route,options);
};
const ok=(value,status=200)=>({ok:status<400,status,json:async()=>value});
const sent=route=>posts.filter(p=>p.route===route).map(p=>p.data);
const tick=async(n=4)=>{for(let i=0;i<n;i++)await new Promise(resolve=>setImmediate(resolve));};
const JOB='00000000-0000-4000-8000-0000000000c1';
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";controls()');
  // 1. Resume audiobook jobs while the jobs pause: enabled (it was disabled), kept by the engine, cancelled by a second press.
  run('state={...state,active_library:null,audiobook_jobs:{...state.audiobook_jobs,state:"Pausing",queued:1}};controls()');
  assert.equal(get('resume-jobs').disabled,false,'no longer disabled while Pausing');
  answers['/api/audiobook/resume']=()=>ok({state:'Pausing',start_admission:{state:'waiting',reason:'pause'}});
  answers['/api/state']=()=>ok({...backend,audiobook_jobs:{...backend.audiobook_jobs,state:'Pausing',queued:1,start_waiting:{reason:'pause'}}});
  get('resume-jobs').handlers.click();await tick(8);
  assert.equal(sent('/api/audiobook/resume').length,1);
  assert.equal(get('message').textContent,'Resume audiobook jobs queued. It starts when the pause finishes. Press it again to cancel.');
  run('state={...state,audiobook_jobs:{...state.audiobook_jobs,state:"Pausing",queued:1,start_waiting:{reason:"pause"}}};controls()');
  assert.equal(get('resume-jobs').title,'Resume audiobook jobs queued. It starts when the pause finishes. Press it again to cancel.');
  answers['/api/audiobook/resume-cancel']=()=>ok({cancelled:true});
  answers['/api/state']=()=>ok({...backend,audiobook_jobs:{...backend.audiobook_jobs,state:'Paused',queued:1}});
  get('resume-jobs').handlers.click();await tick(8);
  assert.equal(sent('/api/audiobook/resume-cancel').length,1,'the same button takes it back');assert.equal(sent('/api/audiobook/resume').length,1);
  assert.equal(get('message').textContent,'Resume audiobook jobs cancelled. Nothing was started.');
  delete answers['/api/state'];
  // 2. Retry all while a scan runs: held, sent when the scan ends; a scan that began after the page looked is waited for.
  answers['/api/audiobook/retry-all']=()=>ok({retry_all:{id:'r1',state:'running',mode:'all',total:1,done:0,accepted:0,queued:0,refused:0}},202);
  run('state={...state,active_library:"Audiobooks"};retryAllConfirm={count:1};controls()');
  get('retry-all-go').handlers.click();
  assert.equal(sent('/api/audiobook/retry-all').length,0,'nothing sent while the scan runs');
  assert.equal(get('message').textContent,'Retry all queued. It runs when the scan finishes. Press it again to cancel.');
  run('state={...state,active_library:null};controls()');await tick(8);
  assert.equal(sent('/api/audiobook/retry-all').length,1,'sent when the scan ended');
  answers['/api/audiobook/retry-all']=()=>ok({error:'Scanning is running. Retry when it stops.',code:'scanning'},409);
  run('retryAllConfirm={count:1};retryAllRun=null;busy=false;state={...state,audiobook_jobs:{...state.audiobook_jobs,retry_all:null}};controls()');await run('startRetryAll()');
  assert.deepEqual([run('laterPresses.length'),run('laterPresses[0].kind')],[1,'retry_all'],'held again, never "Retry when it stops"');
  assert.match(run('stripNote'),/^Retry all queued\. It runs when the scan finishes\./,'the strip line says so');
  run('laterPresses.length=0;controls()');
  // 3. Convert (Confirm and convert) while a scan runs: held for the scan, then sent with his two statements.
  const convert={id:'cand-v',path:'cand-v',kind:'candidate',library:'Audiobooks',revision:3,title_clue:'Сказка',review:{},members:[],status:'Output needs attention',
    creation:{status:'Output needs attention',job:{job_id:JOB,state:'Output needs attention',attention:{group:'other',producer_recovery:{schema:'books-producer-recovery-capability-v1',state:'ready',can_confirm_origin:true,checkpoint_id:'c',cause:'origin'}}}}};
  context.convertRow=convert;answers['/api/audiobook/confirm-convert']=()=>ok({job_id:JOB,queued_next:true,position:1},202);
  run('rows=[convertRow];state={...state,active_library:"Audiobooks"};controls()');
  await run('convertPress(convertRow,null)');
  assert.equal(sent('/api/audiobook/confirm-convert').length,0,'nothing sent while the scan runs');
  assert.deepEqual([run('laterPresses.length'),run('laterPresses[0].kind'),run('laterLine(laterPresses[0])')],[1,'convert','Convert queued. It runs when the scan finishes.']);
  run('state={...state,active_library:null};controls()');await tick(10);
  assert.equal(sent('/api/audiobook/confirm-convert').length,1,'sent when the scan ended');
  assert.equal(sent('/api/audiobook/confirm-convert')[0].statements.length,2,'with both statements he ticked');
  // 4. Delete recovery copies during a scan: accepted and queued; the panel says so and offers Cancel deletion.
  const recovered={id:'cand-r',path:'cand-r',kind:'candidate',library:'Audiobooks',revision:2,title_clue:'Book',review:{title:'Book',canonical_author:'Author'},members:[],
    creation:{status:'Audiobook created',job_id:JOB,job:{job_id:JOB}},
    cleanup:{recovery:{state:'retained',eligible:true,queued:true,waits:'scan',count:2,bytes:4096,token:'a'.repeat(64),location:'C:/recovery',expires_at:'2026-11-26T00:00:00Z'}}};
  context.recoveredRow=recovered;run('recoveryDisconnected=false;rows=[recoveredRow];selectedPath="cand-r";selectedRow=recoveredRow;recoveryPanel=null;globalThis.__panel=makeRecoveryPanel()');
  assert.equal(run('recoveryPanel.values.Status.value.textContent'),'Deletion queued. It runs when the scan finishes.');
  assert.deepEqual([run('recoveryPanel.button.textContent'),run('recoveryPanel.button.disabled'),run('recoveryReason()')],['Cancel deletion',false,'']);
  answers['/api/audiobook/recovery/cancel']=()=>ok({cancelled:true});
  await run('cancelRecoveryDeletion()');
  assert.deepEqual(sent('/api/audiobook/recovery/cancel'),[{job_id:JOB}]);
  assert.equal(run('recoveryPanel.status.textContent'),'Deletion cancelled. Nothing was deleted.');
  // Not queued, a scan running: the press is offered (it was disabled with "Wait for the scan to stop…").
  run('recoveryDisconnected=false;selectedRow={...recoveredRow,cleanup:{recovery:{...recoveredRow.cleanup.recovery,queued:false}}};rows=[selectedRow];updateRecovery()');
  assert.equal(run('recoveryPanel.button.disabled'),false);assert.equal(run('recoveryPanel.button.textContent'),'Delete recovery copies…');
  assert.match(run('recoveryPanel.button.title'),/A scan is running, so the deletion is queued after you confirm\.$/);
  // 5. S6: a delete refusal the page has no line for is said in the engine's words.
  const link="A folder on the way to these files is a link or a junction, so the app can't prove what deleting would reach. Nothing was deleted.";
  assert.equal(run('deleteRefusalText('+JSON.stringify({code:'link',message:link})+')'),link);
  assert.equal(run('queueDeleteText('+JSON.stringify({code:'second_name',message:'A file of this book is a link or has a second name on disk (a hard link), so deleting it wouldn\'t remove it safely. Nothing was deleted.'})+')'),
               "Delete cancelled: a file of this book is a link or has a second name on disk (a hard link), so deleting it wouldn't remove it safely. Nothing was deleted.");
  // 6. A media check past its deadline (0.22.2): a record saved before is never shown raw; any other reason as it is.
  assert.equal(run('plainReason("Owned media operation exceeded its deadline")'),'The library drive answered slowly while the app checked this book. It tries again by itself.');
  assert.equal(run('plainReason("Source files changed")'),'Source files changed','control');
  console.log('PASS the rest of ruling 35 on the page: Resume kept while pausing and cancelled by a second press, Retry all and Convert wait for a scan, recovery deletion queued with Cancel, S6 delete refusals in the engine\'s words');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_ruling37_frontend.js'),module);m.filename=path.join(__dirname,'test_ruling37_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

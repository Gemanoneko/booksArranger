// Pure plan/accounting for five isolated workers inside the canonical owner Job.
const serialServerModules=new Set(['test_desktop_host.py','test_desktop_quit.py','test_web.py','test_merge_http.py','test_blocked_retry.py','test_status_snapshot.py','test_status_read_contention.py','test_startup_published_check.py','test_producer_recovery_http.py','test_attention_repair.py']);
// 0.21.1: two workers no longer fit the 540 s deadline (2026-10-23, both concurrent: 499 s and 601 s, the real MP3
// fixture case not included). A third worker gets the same isolated copy, cwd and TEMP as the others. Modules are
// placed longest first on the least-loaded worker by these measured seconds (unlisted modules weigh 2); serial server
// modules stay together on worker 0, and each worker keeps the declared order. Only placement changes: every pattern
// still runs exactly once, and every report must be complete.
// 0.22.0: three workers no longer fit either (2026-10-24 evening: one worker 495 s, the other two past the 540 s
// deadline). Every gate module timed alone with the pinned Python, one after another on an idle 32-core machine, sums
// to 1,461 s (the heavy suites 15-45 % above their 0.21 weights, 0.22.0 suites added). A fourth worker; the weights
// below are those times, rounded up, for every module of 5 s or more.
// 2026-10-25: four workers reached 430 of the 432 s the projection allows (real 304-388 s); a fifth worker brings the
// projection to about 345 s per worker, so new suites fit without recounting. The weights stay the measured times.
const measuredSeconds={'test_inplace_m4b.py':338,'test_automatic_media.py':111,'test_series_backfill.py':87,'test_iron_skazka.py':72,'test_approve_as_is.py':100,
  'test_destination_admission.py':69,'test_automatic_media_policy.py':63,'test_migration_planning.py':55,'test_standing_admission.py':51,'test_working_lifecycle.py':45,
  'test_retry_intent.py':37,'test_automatic_processing.py':36,'test_working_precision.py':36,'test_output_migration.py':33,'test_source_proofs.py':24,
  'test_sorted_wiring.py':20,'test_replacement_jobs.py':19,'test_local_admission.py':19,'test_progress_rows.py':18,'test_mp3_tag_repair.py':17,'test_source_folders.py':16,
  'test_attempt_working_lifecycle.py':15,'test_local_identity_fixes.py':14,'test_derived_migration.py':14,'test_relocated_chapter_repair.py':13,'test_m4b_preservation.py':12,
  'test_recovery_retention.py':12,'test_catalog_paging.py':12,'test_published_snapshot_lifecycle.py':10,'test_attention_list.py':9,'test_cleanup_resume.py':9,
  'test_storage_cleanup.py':9,'test_review_backend.py':8,'test_startup_published_check.py':7,'test_web.py':7,'test_sqlite_busy.py':7,'test_source_cleanup.py':6,
  'test_desktop_host.py':6,'test_blocked_retry.py':5,'test_list_speed.py':2,'test_todo_holds.py':20,'test_join_parts.py':8,
  // Senua's 0.22.0 early review: m7 gates test_split_books and test_collection_identity; the review fixes add Approve cases (71 -> 100 s).
  'test_split_books.py':60,'test_collection_identity.py':7,'test_m4b_join.py':25,'test_part_sets.py':62};
export const PYTHON_WORKERS=5;
// What each worker is expected to take, from the weights above: the gate keeps every worker well under its deadline.
export function projectedSeconds(batches){return batches.map(batch=>batch.reduce((sum,pattern)=>sum+(measuredSeconds[pattern]??2),0));}
// Senua 0.22.0 early review, m5: the projection is a proxy (each module timed alone), so the gate prints what every worker
// really took beside it. realSeconds: one number per worker.
export function workerSecondsReport(batches,realSeconds){
  if(!Array.isArray(realSeconds)||realSeconds.length!==PYTHON_WORKERS||realSeconds.some(s=>typeof s!=='number'||!Number.isFinite(s)||s<0))throw Error('One real time per Python worker');
  const real=realSeconds.map(s=>Math.round(s*10)/10),projected=projectedSeconds(batches);
  return {real,projected,lines:real.map((s,i)=>'Python worker '+i+': '+s+' s real, '+projected[i]+' s projected, 540 s deadline')};
}
export function pythonWorkerLayout(index){
  if(!Number.isInteger(index)||index<0||index>=PYTHON_WORKERS)throw Error('Unknown Python worker');
  return {relative:'scratch/'+index,requiredDirectories:['scratch/tmp','scratch/source-fallback-2026-10-11']};
}
export function pythonBatches(patterns){
  if(!Array.isArray(patterns)||patterns.length<PYTHON_WORKERS||patterns.some(p=>typeof p!=='string'||!/^test_[a-z0-9_]+\.py$/.test(p))||new Set(patterns).size!==patterns.length)throw Error('Invalid Python pattern inventory');
  const weight=pattern=>measuredSeconds[pattern]??2,load=Array(PYTHON_WORKERS).fill(0),worker=new Map();
  for(const pattern of patterns)if(serialServerModules.has(pattern)){worker.set(pattern,0);load[0]+=weight(pattern);}
  const rest=patterns.filter(pattern=>!serialServerModules.has(pattern)).sort((a,b)=>weight(b)-weight(a)||patterns.indexOf(a)-patterns.indexOf(b));
  for(const pattern of rest){const least=load.indexOf(Math.min(...load));worker.set(pattern,least);load[least]+=weight(pattern);}
  const batches=Array.from({length:PYTHON_WORKERS},()=>[]);
  for(const pattern of patterns)batches[worker.get(pattern)].push(pattern);
  if(batches.some(b=>!b.length))throw Error('Empty Python batch');
  return batches;
}
export function validatePythonReports(patterns,batches,reports){
  const expected=pythonBatches(patterns);
  if(JSON.stringify(batches)!==JSON.stringify(expected)||!Array.isArray(reports)||reports.length!==PYTHON_WORKERS)throw Error('Python partition differs');
  const all=[];
  for(let i=0;i<PYTHON_WORKERS;i++){
    const r=reports[i];
    if(!r||r.batch!==i||JSON.stringify(r.patterns)!==JSON.stringify(batches[i])||!Array.isArray(r.ids)||!r.ids.length||r.ids.some(id=>typeof id!=='string'||!id)||r.discovered!==r.ids.length||r.completed!==r.discovered||r.skipped!==0||r.failures!==0||r.errors!==0||r.success!==true)throw Error('Python batch incomplete or failed');
    all.push(...r.ids); // repeated loader IDs are separate required occurrences
  }
  return {count:all.length,ids:all};
}

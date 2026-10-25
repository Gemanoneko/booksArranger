// Pure plan/accounting for six isolated workers inside the canonical owner Job.
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
// 2026-10-25, after the 0.22.0 QA gate runs: those weights were each module timed ALONE, but the gate runs them five at a time,
// and five workers really took 509/345/438/444/450 s against about 350 s projected (worker 0 left 4 s of the 540 s deadline,
// on a quiet machine). Every module below is now its real seconds while five workers ran together, the gate's own condition
// (rounded up; modules under 3 s weigh the default 2): 101 modules, 2,243 s. A sixth worker brings the projection to about
// 390 s per worker, and the test now holds the projection to 80 % of the deadline with these concurrent weights.
const measuredSeconds={'test_inplace_m4b.py':339,'test_automatic_media.py':129,'test_approve_as_is.py':128,'test_part_sets.py':124,'test_destination_admission.py':100,
  'test_iron_skazka.py':90,'test_series_backfill.py':84,'test_migration_planning.py':80,'test_split_books.py':75,'test_standing_admission.py':62,
  'test_attention_list.py':60,'test_automatic_media_policy.py':59,'test_m4b_join.py':53,'test_retry_intent.py':50,'test_todo_holds.py':49,
  'test_working_lifecycle.py':44,'test_replacement_jobs.py':39,'test_automatic_processing.py':38,'test_published_snapshot_lifecycle.py':33,
  'test_output_migration.py':32,'test_recovery_retention.py':30,'test_source_proofs.py':28,'test_attempt_working_lifecycle.py':28,
  'test_working_precision.py':28,'test_source_folders.py':27,'test_catalog_paging.py':27,'test_local_admission.py':25,'test_book_delete.py':140,
  'test_cleanup_resume.py':22,'test_web.py':33,'test_sorted_wiring.py':21,'test_derived_migration.py':19,'test_progress_rows.py':18,
  'test_relocated_chapter_repair.py':18,'test_local_identity_fixes.py':17,'test_mp3_tag_repair.py':14,'test_review_backend.py':13,
  'test_m4b_preservation.py':12,'test_multisource.py':11,'test_source_cleanup.py':10,'test_groups_filters.py':10,'test_blocked_retry.py':10,
  'test_join_parts.py':9,'test_attention_repair.py':9,'test_failed_m4b_retry.py':9,'test_public_work_identity.py':9,'test_storage_cleanup.py':9,
  'test_working_cleanup.py':8,'test_startup_published_check.py':8,'test_sqlite_busy.py':8,'test_desktop_host.py':8,'test_relocated_replacement.py':8,
  'test_collection_identity.py':7,'test_catalog_contention.py':6,'test_attention_actions.py':6,'test_local_identity.py':6,'test_producer_recovery.py':5,
  'test_author_rules.py':5,'test_openlibrary_index.py':5,'test_publication_consumers.py':5,'test_series_research.py':5,
  'test_automatic_record_retry.py':5,'test_candidate_source_refresh.py':4,'test_inventory.py':4,'test_zone_identifier.py':4};
export const PYTHON_WORKERS=6;
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

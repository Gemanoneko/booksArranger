// Pure plan/accounting for seven isolated workers inside the canonical owner Job.
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
// 2026-10-25, after the c0052d2 entry check: six workers really took 404-447 s against 408-410 s projected, past 80 % of the
// deadline, because the weights were measured with five workers running and every added worker slows every module. The
// gate was run with each pattern's suite timed on its own inside its worker (same tests, order and workers; a scratch copy
// only): six workers took 2,551 s of module time, seven 2,737 s. A seventh worker; the weights below are each module's real
// seconds while SEVEN workers ran together (rounded up; modules under 3 s weigh the default 2): 101 modules, 2,814 s, about
// 403 s per worker (75 % of the deadline), and that run's seven workers really took 384-408 s.
// 2026-10-26 (0.22.1, branch ender/0221c): the b03eea7 entry check ran worker 3 at 517.7 s (96 % of the deadline) against
// 429 s projected, and a fresh-copy gate at 1179f59 at 459.1 s against 430 s. The gate now prints each module's real seconds
// in its worker (check-desktop.mjs); that run showed test_book_delete.py at 216 s (weighed 170) and test_attention_actions.py
// at 29 s (weighed 4) on worker 3, while test_inplace_m4b.py took 336 s (weighed 377). Every weight below is that run's real
// seconds with seven workers running together (rounded up; modules under 3 s weigh the default 2): 64 modules, 2,367 s, about
// 350 s projected per worker (65 % of the deadline).
const measuredSeconds={'test_inplace_m4b.py':336,'test_book_delete.py':216,'test_lock_timing.py':148,'test_approve_as_is.py':120,'test_part_sets.py':114,
  'test_automatic_media.py':112,'test_destination_admission.py':84,'test_series_backfill.py':83,'test_iron_skazka.py':76,'test_split_books.py':67,
  'test_automatic_media_policy.py':66,'test_migration_planning.py':65,'test_attention_list.py':50,'test_working_lifecycle.py':49,
  'test_standing_admission.py':47,'test_m4b_join.py':45,'test_retry_intent.py':42,'test_todo_holds.py':41,'test_automatic_processing.py':39,
  'test_working_precision.py':36,'test_output_migration.py':32,'test_replacement_jobs.py':30,'test_attention_actions.py':29,'test_source_proofs.py':25,
  'test_catalog_paging.py':22,'test_desktop_update.py':20,'test_local_admission.py':19,'test_progress_rows.py':19,'test_recovery_retention.py':18,
  'test_sorted_wiring.py':18,'test_attempt_working_lifecycle.py':17,'test_derived_migration.py':17,'test_published_snapshot_lifecycle.py':17,
  'test_relocated_chapter_repair.py':16,'test_source_folders.py':16,'test_m4b_preservation.py':15,'test_mp3_tag_repair.py':15,'test_web.py':15,
  'test_cleanup_resume.py':13,'test_gap_fill.py':12,'test_review_backend.py':12,'test_desktop_catalog.py':8,'test_desktop_host.py':8,
  'test_join_parts.py':8,'test_multisource.py':8,'test_storage_cleanup.py':8,'test_blocked_retry.py':7,'test_collection_identity.py':7,
  'test_groups_filters.py':7,'test_sqlite_busy.py':7,'test_startup_published_check.py':7,'test_attention_repair.py':6,'test_relocated_replacement.py':6,
  'test_source_cleanup.py':6,'test_catalog_contention.py':5,'test_folder_structure.py':5,'test_openlibrary_index.py':5,'test_author_rules.py':4,
  'test_failed_m4b_retry.py':4,'test_inventory.py':4,'test_public_work_identity.py':4,'test_working_cleanup.py':4,'test_automatic_record_retry.py':3,
  'test_build_guard.py':3,
  // 0.22.2 suites, from their run alone times 1.5 for seven workers (2026-10-26); the gate's next run prints their real seconds.
  'test_entered_names.py':55,'test_catalog_busy.py':15,'test_start_while_converting.py':10,'test_original_title_wait.py':10,'test_identity_0222.py':8,
  'test_live_cases_0222.py':5,'test_no_evidence.py':4,'test_ruling35.py':3};
export const PYTHON_WORKERS=7;
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

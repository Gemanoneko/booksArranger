// Pure plan/accounting for isolated workers inside the canonical owner Job.
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
// 2026-10-26 (0.22.2, branch ender/0222): the gate at b39e180 printed every module's real seconds with seven workers running
// (115 modules, 2492 s); the weights below are those seconds, rounded up (modules under 3 s weigh the default 2).
// That run's workers took 323-414 s (worker 1, with test_inplace_m4b.py at 394 s, 77 % of the deadline).
// 2026-10-26 (0.22.2, branch ender/0222): the passing gate at a2e097f printed every module's real seconds with seven workers
// running (115 modules, 3004 s); the weights below are those seconds, rounded up (modules under 3 s weigh the default 2).
// That run's workers took 389-475 s on the earlier weights (worker 3, test_lock_timing.py at 186 s, 88 % of the deadline): every
// module ran 1.1-1.3x slower than at b39e180 under the machine's own load, so the total itself is about 80 % of 7 x 540 s.
// 0.22.3: test_inplace_m4b.py (389 s) was the floor no worker count lowers: it is run as two halves on two workers, by its
// test classes ("module.py:Class,Class" runs those classes, "module.py:-Class,Class" every other class, so together they
// run the whole module once, whatever classes it gains). Weighted by its classes timed alone (2026-10-27: 51.0 + 34.6 +
// 18.9 s of 215.8 s for the first half), scaled to the module's 389 s.
const measuredSeconds={'test_inplace_m4b.py':389,'test_inplace_m4b.py:EligiblePathTests,FallbackTests,RecoveryWiringTests':189,
  'test_inplace_m4b.py:-EligiblePathTests,FallbackTests,RecoveryWiringTests':201,'test_book_delete.py':285,'test_lock_timing.py':187,'test_approve_as_is.py':173,
  'test_set_release.py':200,  // 0.22.3: six real automatic runs with conversions, 150 s alone (2026-10-28), scaled for the workers at once
  'test_part_sets.py':163,'test_automatic_media.py':118,'test_series_backfill.py':110,'test_iron_skazka.py':107,'test_destination_admission.py':85,
  'test_split_books.py':78,'test_migration_planning.py':70,'test_automatic_media_policy.py':67,'test_m4b_join.py':62,'test_retry_intent.py':62,
  'test_todo_holds.py':58,'test_attention_list.py':56,'test_working_lifecycle.py':54,'test_standing_admission.py':54,'test_entered_names.py':48,
  'test_attention_actions.py':41,'test_recovery_retention.py':40,'test_automatic_processing.py':40,'test_working_precision.py':34,
  'test_output_migration.py':34,'test_source_folders.py':32,'test_local_admission.py':30,'test_replacement_jobs.py':30,'test_desktop_update.py':28,
  'test_sorted_wiring.py':27,'test_catalog_paging.py':26,'test_source_proofs.py':24,'test_progress_rows.py':19,'test_attempt_working_lifecycle.py':19,
  'test_original_title_wait.py':18,'test_published_snapshot_lifecycle.py':18,'test_derived_migration.py':18,'test_relocated_chapter_repair.py':17,
  'test_m4b_preservation.py':16,'test_web.py':16,'test_mp3_tag_repair.py':15,'test_gap_fill.py':14,'test_cleanup_resume.py':14,
  'test_attention_repair.py':13,'test_review_backend.py':12,'test_multisource.py':12,'test_join_parts.py':11,'test_catalog_busy.py':11,
  'test_storage_cleanup.py':10,'test_public_work_identity.py':9,'test_desktop_catalog.py':9,'test_desktop_host.py':8,'test_folder_structure.py':8,
  'test_collection_identity.py':7,'test_source_cleanup.py':7,'test_blocked_retry.py':7,'test_author_rules.py':7,'test_startup_published_check.py':7,
  'test_sqlite_busy.py':6,'test_relocated_replacement.py':6,'test_working_cleanup.py':6,'test_openlibrary_index.py':5,'test_catalog_contention.py':5,
  'test_identity_v5.py':5,'test_local_identity.py':4,'test_groups_filters.py':4,'test_startup_loading.py':4,'test_start_while_converting.py':4,
  'test_inventory.py':4,'test_failed_m4b_retry.py':4,'test_live_cases_0222.py':4,'test_build_guard.py':4};
// 0.22.2: with those weights seven workers project 440-442 s each (over 80 % of the deadline); an eighth brings it near 375 s.
// 0.22.3: with test_inplace_m4b.py split, a ninth worker lowers every worker (8: 385-387 s, 9: 342-344 s projected, 64 % of
// the deadline); before the split no count went under its 389 s. The weights are eight-worker seconds: the entry check's
// printed seconds re-measure them.
// 0.23.0 capacity proposal: 13 workers on the 24-core/32-thread QA host. The unchanged 540/580/600 s
// bounds still apply; existing weights are historical proxies, never a real-wall-time guarantee.
export const PYTHON_WORKERS=13;
// 0.22.3 (the 0.22.2 gates: workers at 81-88 % of the deadline, and one run lost two workers because copying the sources
// took 170 s of it): every Python worker has its own 540 s, counted from its own start, so copies taking up to 40 s before
// it leave its time whole; past that the gate total binds first (workerDeadline). The gate as a whole still ends inside the
// entry check's 600 s: past 580 s from its start it stops itself and says which deadline ran out.
export const PYTHON_WORKER_DEADLINE_SECONDS=540,GATE_TOTAL_SECONDS=580;
export function workerDeadline(gateStartMs,workerStartMs){
  const own=workerStartMs+PYTHON_WORKER_DEADLINE_SECONDS*1000,total=gateStartMs+GATE_TOTAL_SECONDS*1000;
  return own<=total?{at:own,kind:'worker'}:{at:total,kind:'gate total'};
}
// What each worker is expected to take, from the weights above: the gate keeps every worker well under its deadline.
export function projectedSeconds(batches){return batches.map(batch=>batch.reduce((sum,pattern)=>sum+(measuredSeconds[pattern]??2),0));}
// Senua 0.22.0 early review, m5: the projection is a proxy (each module timed alone), so the gate prints what every worker
// really took beside it. realSeconds: one number per worker.
export function workerSecondsReport(batches,realSeconds){
  if(!Array.isArray(realSeconds)||realSeconds.length!==PYTHON_WORKERS||realSeconds.some(s=>typeof s!=='number'||!Number.isFinite(s)||s<0))throw Error('One real time per Python worker');
  const real=realSeconds.map(s=>Math.round(s*10)/10),projected=projectedSeconds(batches);
  const share=s=>Math.round(s/PYTHON_WORKER_DEADLINE_SECONDS*100);
  return {real,projected,workers:PYTHON_WORKERS,deadline:PYTHON_WORKER_DEADLINE_SECONDS,
    lines:real.map((s,i)=>'Python worker '+i+': '+s+' s real, '+projected[i]+' s projected, '+PYTHON_WORKER_DEADLINE_SECONDS+' s deadline ('+share(s)+' %)')
      .concat('Python workers: '+PYTHON_WORKERS+', each with '+PYTHON_WORKER_DEADLINE_SECONDS+' s from its own start; the slowest used '+share(Math.max(...real))+' %')};
}
export function pythonWorkerLayout(index){
  if(!Number.isInteger(index)||index<0||index>=PYTHON_WORKERS)throw Error('Unknown Python worker');
  return {relative:'scratch/'+index,requiredDirectories:['scratch/tmp','scratch/source-fallback-2026-10-11']};
}
// A module, or one half of a split module: its classes ("test_x.py:A,B") or every other class ("test_x.py:-A,B").
export const PATTERN=/^test_[a-z0-9_]+\.py(?::-?[A-Z][A-Za-z0-9_]*(?:,[A-Z][A-Za-z0-9_]*)*)?$/;
export function pythonBatches(patterns){
  if(!Array.isArray(patterns)||patterns.length<PYTHON_WORKERS||patterns.some(p=>typeof p!=='string'||!PATTERN.test(p))||new Set(patterns).size!==patterns.length)throw Error('Invalid Python pattern inventory');
  // A split module is exactly two halves, the same classes kept and left out, and never also run whole.
  const halves=new Map();
  for(const pattern of patterns.filter(p=>p.includes(':'))){const [module,spec]=pattern.split(':');(halves.get(module) || halves.set(module,[]).get(module)).push(spec);}
  for(const [module,specs] of halves)if(patterns.includes(module)||specs.length!==2||!specs.some(s=>s.startsWith('-'))||new Set(specs.map(s=>s.replace(/^-/,''))).size!==1)throw Error('Invalid Python pattern inventory: '+module+' must be split into two complementary halves');
  const weight=pattern=>measuredSeconds[pattern]??2,load=Array(PYTHON_WORKERS).fill(0),worker=new Map();
  for(const pattern of patterns)if(serialServerModules.has(pattern)){worker.set(pattern,0);load[0]+=weight(pattern);}
  const rest=patterns.filter(pattern=>!serialServerModules.has(pattern)).sort((a,b)=>weight(b)-weight(a)||patterns.indexOf(a)-patterns.indexOf(b));
  for(const pattern of rest){const least=load.indexOf(Math.min(...load));worker.set(pattern,least);load[least]+=weight(pattern);}
  // 2026-10-28, 8b24ce8: workers 4 and 6 reached 540 s; worker 2 had only 1.2 s left. Reuse the measured spare
  // capacity without more workers or longer deadlines. The prior complete run measured original_title_wait at
  // 119.9 s (weight 18), working_lifecycle at 71.1 s and source_proofs at 40.8 s. These five whole modules move;
  // discovery, the two complementary in-place halves, server serialization and declared order are unchanged.
  // Only the complete production inventory has this group; smaller diagnostic inventories retain normal placement.
  // 0.23.0: move this whole module off book_delete's worker to new worker 12; the other four pins stay.
  const rebalance=new Map([['test_original_title_wait.py',12],['test_review_backend.py',4],
    ['test_published_snapshot_lifecycle.py',4],['test_working_lifecycle.py',5],['test_source_proofs.py',4]]);
  if([...rebalance.keys()].every(pattern=>worker.has(pattern)))for(const [pattern,target] of rebalance)worker.set(pattern,target);
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

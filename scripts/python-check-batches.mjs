// Pure plan/accounting for three isolated workers inside the canonical owner Job.
const serialServerModules=new Set(['test_desktop_host.py','test_desktop_quit.py','test_web.py','test_merge_http.py','test_blocked_retry.py','test_status_snapshot.py','test_status_read_contention.py','test_startup_published_check.py','test_producer_recovery_http.py','test_attention_repair.py']);
// 0.21.1: two workers no longer fit the 540 s deadline (2026-10-23, both concurrent: 499 s and 601 s, the real MP3
// fixture case not included). A third worker gets the same isolated copy, cwd and TEMP as the others. Modules are
// placed longest first on the least-loaded worker by these measured seconds (unlisted modules weigh 2); serial server
// modules stay together on worker 0, and each worker keeps the declared order. Only placement changes: every pattern
// still runs exactly once, and every report must be complete.
const measuredSeconds={'test_inplace_m4b.py':283,'test_automatic_media.py':76,'test_series_backfill.py':68,'test_automatic_media_policy.py':60,
  'test_migration_planning.py':56,'test_destination_admission.py':55,'test_standing_admission.py':38,'test_working_lifecycle.py':38,'test_retry_intent.py':36,
  'test_iron_skazka.py':31,'test_working_precision.py':30,'test_automatic_processing.py':30,'test_output_migration.py':23,'test_replacement_jobs.py':21,
  'test_source_proofs.py':20,'test_progress_rows.py':18,'test_recovery_retention.py':17,'test_relocated_chapter_repair.py':15,'test_derived_migration.py':14,
  'test_cleanup_resume.py':14,'test_mp3_tag_repair.py':13,'test_m4b_preservation.py':12,'test_attempt_working_lifecycle.py':11,
  'test_source_folders.py':7,'test_source_cleanup.py':3};  // 0.21.3 audit M1, measured alone with the pinned Python (2026-10-24)
export const PYTHON_WORKERS=3;
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

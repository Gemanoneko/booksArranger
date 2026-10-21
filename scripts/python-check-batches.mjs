// Pure plan/accounting for two isolated workers inside the canonical owner Job.
const serialServerModules=new Set(['test_desktop_host.py','test_desktop_quit.py','test_web.py','test_merge_http.py','test_blocked_retry.py','test_status_snapshot.py','test_status_read_contention.py','test_startup_published_check.py','test_producer_recovery_http.py','test_attention_repair.py']);
export function pythonBatches(patterns){
  if(!Array.isArray(patterns)||patterns.length<2||patterns.some(p=>typeof p!=='string'||!/^test_[a-z0-9_]+\.py$/.test(p))||new Set(patterns).size!==patterns.length)throw Error('Invalid Python pattern inventory');
  let next=0;const batches=[[],[]];
  for(const pattern of patterns)batches[serialServerModules.has(pattern)?0:next++%2].push(pattern);
  if(batches.some(b=>!b.length))throw Error('Empty Python batch');
  return batches;
}
export function validatePythonReports(patterns,batches,reports){
  const expected=pythonBatches(patterns);
  if(JSON.stringify(batches)!==JSON.stringify(expected)||!Array.isArray(reports)||reports.length!==2)throw Error('Python partition differs');
  const all=[];
  for(let i=0;i<2;i++){
    const r=reports[i];
    if(!r||r.batch!==i||JSON.stringify(r.patterns)!==JSON.stringify(batches[i])||!Array.isArray(r.ids)||!r.ids.length||r.ids.some(id=>typeof id!=='string'||!id)||r.discovered!==r.ids.length||r.completed!==r.discovered||r.skipped!==0||r.failures!==0||r.errors!==0||r.success!==true)throw Error('Python batch incomplete or failed');
    all.push(...r.ids); // repeated loader IDs are separate required occurrences
  }
  return {count:all.length,ids:all};
}

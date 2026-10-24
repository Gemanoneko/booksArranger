import test from 'node:test';
import assert from 'node:assert/strict';
import {pythonBatches,validatePythonReports,pythonWorkerLayout,PYTHON_WORKERS,projectedSeconds,workerSecondsReport} from '../scripts/python-check-batches.mjs';
const patterns=['test_desktop_host.py','test_alpha.py','test_beta.py','test_web.py','test_gamma.py','test_delta.py'];
const reports=()=>pythonBatches(patterns).map((p,batch)=>({batch,patterns:p,ids:p.map(x=>'case.'+x),discovered:p.length,completed:p.length,skipped:0,failures:0,errors:0,success:true}));
test('both short worker layouts retain the original fallback prerequisite',()=>{
 assert.equal(PYTHON_WORKERS,5);  // 0.22.0: three no longer fit the 540 s deadline; four reached 430 of the 432 s projection (2026-10-25)
 for(let i=0;i<PYTHON_WORKERS;i++){const layout=pythonWorkerLayout(i);assert.equal(layout.relative,'scratch/'+i);assert.deepEqual(layout.requiredDirectories,['scratch/tmp','scratch/source-fallback-2026-10-11']);}
 assert.throws(()=>pythonWorkerLayout(PYTHON_WORKERS));assert.throws(()=>pythonWorkerLayout(-1));assert.throws(()=>pythonWorkerLayout(1.5));assert.throws(()=>pythonWorkerLayout('../escape'));
});
test('fixed short fixture bounds leave the existing 240-character output guard intact',()=>{
 const root='C:/Antigravity Projects/Worktrees/Books Arranger/q20/entry-run-XXXXXX/'+pythonWorkerLayout(0).relative;
 const destination=root+'/scratch/f/retry-intent/tmpXXXXXXXX/Sorted Recording/Author Name/Series/Series - 2 - Book - Author Name - Reader - recording-1234567890abcdef.m4b';
 const series=root+'/scratch/s/tmpXXXXXXXX/library/Обухова Лена/Нормальное аномальное/Нормальное аномальное - 10 - Призраки белых ночей - Обухова Лена.m4b';
 assert.equal(destination.length,224);assert.equal(series.length,213);assert(destination.length<240&&series.length<240);
});
test('server conflicts remain serial and every declared pattern appears exactly once',()=>{
 const b=pythonBatches(patterns);assert.equal(b.length,PYTHON_WORKERS);assert(b[0].includes('test_desktop_host.py'));assert(b[0].includes('test_web.py'));assert.deepEqual(b.flat().sort(),[...patterns].sort());
});
test('measured heavy modules spread longest first; serial modules stay together; declared order is kept',()=>{
 const declared=['test_alpha.py','test_desktop_host.py','test_inplace_m4b.py','test_beta.py','test_automatic_media.py','test_web.py','test_series_backfill.py','test_gamma.py','test_iron_skazka.py'];
 const b=pythonBatches(declared);
 assert.deepEqual(b,[['test_alpha.py','test_desktop_host.py','test_beta.py','test_web.py','test_gamma.py'],['test_inplace_m4b.py'],['test_automatic_media.py'],['test_series_backfill.py'],['test_iron_skazka.py']]);
 assert.deepEqual(pythonBatches([...declared]),b,'deterministic');
 for(const batch of b)assert.deepEqual(batch,declared.filter(p=>batch.includes(p)),'each worker keeps the declared order');
 assert.throws(()=>pythonBatches(['test_a.py','test_b.py']),/Invalid/);  // fewer modules than workers
});
test('the real inventory projects every worker under the deadline from its measured seconds',async()=>{
 const fs=await import('node:fs');const source=fs.readFileSync(new URL('../scripts/check-desktop.mjs',import.meta.url),'utf8');
 const real=new Function(source.split(/\r?\n/).filter(l=>/^(const patterns=|patterns\.push\()/.test(l)).join('\n')+'\nreturn patterns;')();
 const b=pythonBatches(real);assert.equal(b.length,PYTHON_WORKERS);assert.deepEqual(b.flat().sort(),[...real].sort());
 assert(b[0].includes('test_desktop_host.py')&&b[0].includes('test_merge_http.py'));assert.equal(b.filter(batch=>batch.includes('test_inplace_m4b.py')).length,1);
 // The projection itself (0.22.0: placement alone never caught three workers running past the deadline): every worker's
 // measured seconds stay under 80 % of the 540 s deadline, leaving room for the copy and for the workers at once. Five
 // workers (2026-10-25) leave the projection well under it, so new suites fit without a recount.
 const loads=projectedSeconds(b);assert.equal(loads.length,PYTHON_WORKERS);assert(Math.max(...loads)<=0.7*540,'projected worker seconds '+loads.join(', '));
});
test('the gate prints every worker\'s real seconds beside its projection (Senua 0.22.0 early review, m5)',async()=>{
 const b=pythonBatches(patterns),report=workerSecondsReport(b,[431.24,402.5,388,12.04,7]);
 assert.deepEqual(report.real,[431.2,402.5,388,12,7]);assert.deepEqual(report.projected,projectedSeconds(b));
 assert.equal(report.lines.length,PYTHON_WORKERS);assert.match(report.lines[0],/^Python worker 0: 431\.2 s real, \d+ s projected, 540 s deadline$/);
 assert.throws(()=>workerSecondsReport(b,[1,2,3,4]),/worker/);assert.throws(()=>workerSecondsReport(b,[1,2,3,4,NaN]),/worker/);
 const fs=await import('node:fs');const source=fs.readFileSync(new URL('../scripts/check-desktop.mjs',import.meta.url),'utf8');
 assert.match(source,/workerSecondsReport\(batches,results\.map\(r=>r\.seconds\)\)/,'the gate reports the measured times');
 assert.match(source,/python_worker_seconds:/,'and records them in its pass line');
});
test('duplicate and malformed patterns cannot silently change discovery',()=>{assert.throws(()=>pythonBatches([...patterns,patterns[0]]));assert.throws(()=>pythonBatches(['../test_a.py','test_b.py']));});
test('actual complete occurrence count is summed without deduplicating loader IDs',()=>{const r=reports();r[0].ids[1]=r[0].ids[0];assert.equal(validatePythonReports(patterns,pythonBatches(patterns),r).count,patterns.length);});
for(const [label,change] of [
 ['omitted completion',r=>r[0].completed--],['skipped case',r=>r[0].skipped=1],['failure',r=>r[0].failures=1],['error',r=>r[0].errors=1],['missing ID',r=>r[0].ids.pop()],['false success',r=>r[0].success=false],['wrong worker',r=>r[0].batch=1],['unknown pattern',r=>r[0].patterns=['test_extra.py']],['missing worker',r=>r.pop()]
])test('refuses '+label,()=>{const r=reports();change(r);assert.throws(()=>validatePythonReports(patterns,pythonBatches(patterns),r));});

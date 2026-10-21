import test from 'node:test';
import assert from 'node:assert/strict';
import {pythonBatches,validatePythonReports,pythonWorkerLayout} from '../scripts/python-check-batches.mjs';
const patterns=['test_desktop_host.py','test_alpha.py','test_beta.py','test_web.py','test_gamma.py'];
const reports=()=>pythonBatches(patterns).map((p,batch)=>({batch,patterns:p,ids:p.map(x=>'case.'+x),discovered:p.length,completed:p.length,skipped:0,failures:0,errors:0,success:true}));
test('both short worker layouts retain the original fallback prerequisite',()=>{
 for(const i of [0,1]){const layout=pythonWorkerLayout(i);assert.equal(layout.relative,'scratch/'+i);assert.deepEqual(layout.requiredDirectories,['scratch/tmp','scratch/source-fallback-2026-10-11']);}
 assert.throws(()=>pythonWorkerLayout(2));assert.throws(()=>pythonWorkerLayout('../escape'));
});
test('fixed short fixture bounds leave the existing 240-character output guard intact',()=>{
 const root='C:/Antigravity Projects/Worktrees/Books Arranger/q20/entry-run-XXXXXX/'+pythonWorkerLayout(0).relative;
 const destination=root+'/scratch/f/retry-intent/tmpXXXXXXXX/Sorted Recording/Author Name/Series/Series - 2 - Book - Author Name - Reader - recording-1234567890abcdef.m4b';
 const series=root+'/scratch/s/tmpXXXXXXXX/library/Обухова Лена/Нормальное аномальное/Нормальное аномальное - 10 - Призраки белых ночей - Обухова Лена.m4b';
 assert.equal(destination.length,224);assert.equal(series.length,213);assert(destination.length<240&&series.length<240);
});
test('server conflicts remain serial and every declared pattern appears exactly once',()=>{
 const b=pythonBatches(patterns);assert.equal(b.length,2);assert(b[0].includes('test_desktop_host.py'));assert(b[0].includes('test_web.py'));assert.deepEqual(b.flat().sort(),[...patterns].sort());
});
test('duplicate and malformed patterns cannot silently change discovery',()=>{assert.throws(()=>pythonBatches([...patterns,patterns[0]]));assert.throws(()=>pythonBatches(['../test_a.py','test_b.py']));});
test('actual complete occurrence count is summed without deduplicating loader IDs',()=>{const r=reports();r[0].ids[1]=r[0].ids[0];assert.equal(validatePythonReports(patterns,pythonBatches(patterns),r).count,patterns.length);});
for(const [label,change] of [
 ['omitted completion',r=>r[0].completed--],['skipped case',r=>r[0].skipped=1],['failure',r=>r[0].failures=1],['error',r=>r[0].errors=1],['missing ID',r=>r[0].ids.pop()],['false success',r=>r[0].success=false],['wrong worker',r=>r[0].batch=1],['unknown pattern',r=>r[0].patterns=['test_extra.py']],['missing worker',r=>r.pop()]
])test('refuses '+label,()=>{const r=reports();change(r);assert.throws(()=>validatePythonReports(patterns,pythonBatches(patterns),r));});

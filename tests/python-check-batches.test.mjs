import test from 'node:test';
import assert from 'node:assert/strict';
import {pythonBatches,validatePythonReports} from '../scripts/python-check-batches.mjs';
const patterns=['test_desktop_host.py','test_alpha.py','test_beta.py','test_web.py','test_gamma.py'];
const reports=()=>pythonBatches(patterns).map((p,batch)=>({batch,patterns:p,ids:p.map(x=>'case.'+x),discovered:p.length,completed:p.length,skipped:0,failures:0,errors:0,success:true}));
test('server conflicts remain serial and every declared pattern appears exactly once',()=>{
 const b=pythonBatches(patterns);assert.equal(b.length,2);assert(b[0].includes('test_desktop_host.py'));assert(b[0].includes('test_web.py'));assert.deepEqual(b.flat().sort(),[...patterns].sort());
});
test('duplicate and malformed patterns cannot silently change discovery',()=>{assert.throws(()=>pythonBatches([...patterns,patterns[0]]));assert.throws(()=>pythonBatches(['../test_a.py','test_b.py']));});
test('actual complete occurrence count is summed without deduplicating loader IDs',()=>{const r=reports();r[0].ids[1]=r[0].ids[0];assert.equal(validatePythonReports(patterns,pythonBatches(patterns),r).count,patterns.length);});
for(const [label,change] of [
 ['omitted completion',r=>r[0].completed--],['skipped case',r=>r[0].skipped=1],['failure',r=>r[0].failures=1],['error',r=>r[0].errors=1],['missing ID',r=>r[0].ids.pop()],['false success',r=>r[0].success=false],['wrong worker',r=>r[0].batch=1],['unknown pattern',r=>r[0].patterns=['test_extra.py']],['missing worker',r=>r.pop()]
])test('refuses '+label,()=>{const r=reports();change(r);assert.throws(()=>validatePythonReports(patterns,pythonBatches(patterns),r));});

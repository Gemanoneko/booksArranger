/** Finite POST shape/capability fakes; never native QA acceptance. */
export async function runResultChecks(api,assert){
  let checks=0;const check=fn=>{fn();checks++;};
  const expected={invocation_id:'11111111-2222-3333-4444-555555555555',registry_sha256:'a'.repeat(64),context_sha256:'b'.repeat(64),source_sha256:'c'.repeat(64),watchdog_sha256:'d'.repeat(64)};
  const frame={schema:'books-native-terminal-proposed-v1',...expected,exit_code:0,active:0,unsignaled:0,pipe_eof:true,checked_closes:true,elapsed_ms:99,output_bytes:12};
  const result={schema:'books-original-tool-result-proposed-v1',invocation_id:expected.invocation_id,exit_code:0,signal:null,terminal:true,stdout_bytes:10,stderr_bytes:2};
  check(()=>assert.equal(api.validateTerminalFrame(frame,expected).authority,false));check(()=>assert.equal(api.validateOriginalResult(result,expected).authority,false));
  for(const patch of [{schema:'Books native watcher v2'},{registry_sha256:'0'.repeat(64)},{context_sha256:'0'.repeat(64)},{source_sha256:'0'.repeat(64)},{invocation_id:'99999999-2222-3333-4444-555555555555'},{exit_code:1},{active:1},{unsignaled:1},{pipe_eof:false},{checked_closes:false},{elapsed_ms:600001},{output_bytes:16777217},{extra:true}])check(()=>assert.throws(()=>api.validateTerminalFrame({...frame,...patch},expected)));
  for(const patch of [{exit_code:1},{signal:'terminated'},{terminal:false},{invocation_id:'other'},{stdout_bytes:-1},{stderr_bytes:Infinity},{closed:true}])check(()=>assert.throws(()=>api.validateOriginalResult({...result,...patch},expected)));
  const events=[],observation={};const caps={observeOriginalTool:async actual=>{assert.equal(actual,result);events.push('observe');return observation;},readNativeTerminal:async actual=>{assert.equal(actual,observation);events.push('frame');return {frame,frames:1,trailing_bytes:0,child_lookalike:false};},verifyOriginalOwnership:async actual=>{assert.equal(actual,observation);events.push('ownership');return true;},closeObservation:async actual=>{assert.equal(actual,observation);events.push('close');return true;}};
  const answer=await api.exercisePostBoundary(result,expected,caps);check(()=>assert.deepEqual(events,['observe','frame','ownership','close']));check(()=>assert.equal(answer.accepted,false));check(()=>assert.equal(answer.production,false));
  await assert.rejects(()=>api.exercisePostBoundary(result,expected,caps),error=>error.code==='replay');checks++;
  const freshCaps=patch=>({observeOriginalTool:async()=>({}),readNativeTerminal:async()=>({frame,frames:1,trailing_bytes:0,child_lookalike:false}),verifyOriginalOwnership:async()=>true,closeObservation:async()=>true,...patch});
  for(const patch of [{frames:2},{trailing_bytes:1},{child_lookalike:true}]){await assert.rejects(()=>api.exercisePostBoundary(result,expected,freshCaps({readNativeTerminal:async()=>({frame,frames:1,trailing_bytes:0,child_lookalike:false,...patch})})),error=>error.code==='framing');checks++;}
  await assert.rejects(()=>api.exercisePostBoundary(result,expected,freshCaps({verifyOriginalOwnership:async()=>false})),error=>error.code==='origin');checks++;
  await assert.rejects(()=>api.exercisePostBoundary(result,expected,freshCaps({closeObservation:async()=>false})),error=>error.code==='close');checks++;
  await assert.rejects(()=>api.acceptProtectedResult(result,expected,caps),error=>error.code==='native_framing_missing');checks++;
  return {suite:'protected-result-pure',checks,passed:true,native_executed:false,qa_accepted:false};
}

/** Finite pure checks. Caller supplies this new module and in-process assert. */
export async function runAdmissionChecks(api,assert){
  let checks=0;const check=fn=>{fn();checks++;};
  const p={schema:'books-protected-admission-policy-v1',enabled:true,operation:'entry',registry_sha256:'a'.repeat(64),context_sha256:'b'.repeat(64),source_sha256:'c'.repeat(64),runtime_sha256:'d'.repeat(64),bootstrap_sha256:'e'.repeat(64),manifest_sha256:'f'.repeat(64),watchdog_sha256:'1'.repeat(64)};
  const input={cmd:"& '"+api.WATCHDOG+"' --registry-sha "+p.registry_sha256,workdir:api.STUDIO,login:false,yield_time_ms:10000,max_output_tokens:1000};
  const raw=value=>JSON.stringify({tool_input:value});
  check(()=>{const r=api.validatePreRequest(raw(input),p);assert.equal(r.authority,false);assert.equal(r.execution_bound_from_observation,false);assert.equal(r.observation.yield_time_ms,10000);});
  for(const patch of [{shell:'powershell'},{tty:false},{timeout:600000},{login:true},{yield_time_ms:600000},{max_output_tokens:Infinity},{cmd:input.cmd+'; echo later'},{workdir:api.SOURCE},{command:input.cmd},{cwd:api.STUDIO}])check(()=>assert.throws(()=>api.validatePreRequest(raw({...input,...patch}),p)));
  for(const patch of [{enabled:false},{operation:'pack'},{registry_sha256:'bad'},{source_sha256:'0'.repeat(63)},{extra:true}])check(()=>assert.throws(()=>api.validatePreRequest(raw(input),{...p,...patch})));
  const deny=["node '"+api.BASE+"/launch-books-qa.mjs' --deadline 999", "npm run pack",'node scripts/qa-owned-guardian-v2.mjs',"node C:/Studio/run_entry_checks.mjs --context C:/private/qa-entry-context/context.json",'powershell -Command "npm run test"',"cmd /c node '"+api.SOURCE+"/scripts/test.mjs'", "custom-wrapper '"+api.SOURCE+"/scripts/test.mjs'",'& { npm run test }'];
  for(const cmd of deny)check(()=>assert.equal(api.classifyRequest(raw({...input,cmd,workdir:api.SOURCE})).route,'deny',cmd));
  for(const cmd of ['echo safe; npm run test','Write-Output "$(npm run test)"','echo safe | node scripts/test.mjs','git -c "alias.qa=!npm run test" qa','n`pm run test'])check(()=>assert.equal(api.classifyRequest(raw({...input,cmd,workdir:api.SOURCE})).route,'deny',cmd));
  for(const cmd of ["echo 'launch-books-qa.mjs npm run test'","rg 'books-qa-watchdog.exe' web/app.js","Get-Content '"+api.SOURCE+"/package.json'",'git diff -- package.json'])check(()=>assert.equal(api.classifyRequest(raw({...input,cmd,workdir:api.SOURCE})).route,'opaque-fallback'));
  check(()=>assert.equal(api.classifyRequest(raw({...input,cmd:'npm run test',workdir:'C:/other-project'})).route,'opaque-fallback'));
  check(()=>{const opaque=raw({...input,cmd:"echo 'npm run test'"});assert.equal(api.classifyRequest(opaque).opaque_input,opaque);});
  check(()=>assert.equal(api.classifyRequest('opaque original input',{originalOwned:true}).route,'original-owned'));
  for(const opaque of [
    JSON.stringify({tool_input:{cmd:'echo hello',workdir:api.STUDIO,login:false}}),
    JSON.stringify({tool_input:{cmd:'echo hello'}}),
    JSON.stringify({tool_name:'exec_command',call_id:'fixture',tool_input:{cmd:'echo hello',workdir:api.STUDIO,login:false}}),
    '{ "tool_input": { "cmd": "echo hello", "workdir": "C:/other" }, "host": {"future":true} }'
  ])check(()=>{const r=api.classifyRequest(opaque);assert.equal(r.route,'opaque-fallback');assert.equal(r.opaque_input,opaque);assert.equal(r.authority,false);});
  // Unknown envelopes/aliases are opaque data, NOT newly supported host transports.
  for(const opaque of ['{not-json','opaque original bytes',JSON.stringify({tool_input:{command:'echo hello',cwd:'C:/other'}})])check(()=>{const r=api.classifyRequest(opaque);assert.equal(r.route,'opaque-fallback');assert.equal(r.opaque_input,opaque);assert.equal(r.integration_stop,true);assert.equal(r.authority,false);});
  for(const opaque of [
    JSON.stringify({tool_input:{command:"echo 'run_entry_checks.mjs'",cwd:'C:/other'}}),
    JSON.stringify({tool_input:{command:'rg "books-qa-watchdog.exe" files',cwd:'C:/other'}}),
    JSON.stringify({tool_input:{command:"Get-Content 'launch-books-qa.mjs'",cwd:'C:/other'}}),
    JSON.stringify({tool_input:{command:'node scripts/run_entry_checks.mjs',cwd:api.SOURCE}}),
    '{"tool_input":{"cmd":"echo run_entry_checks.mjs"',
    JSON.stringify({tool_input:{cmd:42,workdir:api.SOURCE}}),
    JSON.stringify({tool_input:{cmd:"echo 'run_entry_checks.mjs",workdir:api.SOURCE}}),
    JSON.stringify({tool_input:{cmd:'echo run_entry_checks.mjs\n',workdir:api.SOURCE}})
  ])check(()=>{const r=api.classifyRequest(opaque);assert.equal(r.route,'opaque-fallback');assert.equal(r.opaque_input,opaque);assert.equal(r.integration_stop,true);assert.equal(r.authority,false);});
  for(const cmd of [
    'run_entry_checks.mjs','./scripts/run_entry_checks.mjs arbitrary',
    "& 'C:/example/scripts/run_entry_checks.mjs'",
    '"C:/example/scripts/run_entry_checks.mjs" arbitrary',
    "& './scripts/run_entry_checks.mjs' --anything",
    'C:\\example\\scripts\\run_entry_checks.mjs',
    'node scripts/run_entry_checks.mjs','custom-wrapper scripts/run_entry_checks.mjs'
  ])check(()=>assert.equal(api.classifyRequest(raw({...input,cmd,workdir:api.STUDIO})).route,'deny',cmd));
  for(const cmd of ["echo 'run_entry_checks.mjs'",'rg "run_entry_checks.mjs" scripts',"Get-Content 'C:/example/run_entry_checks.mjs'"])
    check(()=>{const opaque=JSON.stringify({tool_input:{cmd,workdir:api.STUDIO}});assert.equal(api.classifyRequest(opaque).opaque_input,opaque);});
  for(const opaque of [JSON.stringify({tool_input:{cmd:'npm run test',workdir:api.SOURCE}}),JSON.stringify({host:'fixture',tool_input:{cmd:'node scripts/run_entry_checks.mjs'}})])check(()=>assert.equal(api.classifyRequest(opaque).route,'deny'));
  check(()=>{const opaque=JSON.stringify({tool_input:{cmd:'node scripts/run_entry_checks.mjs'}});assert.equal(api.classifyRequest(opaque,{originalOwned:true}).opaque_input,opaque);assert.equal(api.classifyRequest(opaque,{originalOwned:true}).route,'original-owned');});
  check(()=>{const opaque=JSON.stringify({tool_input:{cmd:input.cmd,workdir:api.STUDIO,login:false}});assert.equal(api.classifyRequest(opaque).route,'watchdog-candidate');assert.throws(()=>api.validatePreRequest(opaque,p));});
  check(()=>{const opaque=JSON.stringify({host:'fixture',tool_input:input});assert.equal(api.classifyRequest(opaque).route,'watchdog-candidate');assert.throws(()=>api.validatePreRequest(opaque,p));});
  let getter=0;const evil={...p};Object.defineProperty(evil,'enabled',{get(){getter++;return true;},enumerable:true});check(()=>assert.throws(()=>api.validatePreRequest(raw(input),evil)));check(()=>assert.equal(getter,0));
  let coerced=0;check(()=>assert.throws(()=>api.validatePreRequest(raw(input),{...p,registry_sha256:{toString(){coerced++;return p.registry_sha256;}}})));check(()=>assert.equal(coerced,0));
  const lease={},events=[];const caps={observeTrustedHost:async literal=>{events.push('host');return {defaultShell:'WindowsPowerShell',requestLiteral:literal};},freezeProtectedInputs:async()=>{events.push('freeze');return lease;},revalidateProtectedInputs:async actual=>{assert.equal(actual,lease);events.push('revalidate');return true;},closeProtectedInputs:async actual=>{assert.equal(actual,lease);events.push('close');return true;}};
  const result=await api.exercisePreBoundary(raw(input),p,caps);check(()=>assert.deepEqual(events,['host','freeze','revalidate','close']));check(()=>assert.equal(result.authority,false));check(()=>assert.equal(result.canonical_runs,0));
  await assert.rejects(()=>api.exercisePreBoundary(raw(input),p,{...caps,revalidateProtectedInputs:async()=>false}),error=>error.code==='input_drift');checks++;
  await assert.rejects(()=>api.exercisePreBoundary(raw(input),p,{...caps,closeProtectedInputs:async()=>false}),error=>error.code==='close');checks++;
  await assert.rejects(()=>api.exercisePreBoundary(raw(input),p,{...caps,observeTrustedHost:async()=>({defaultShell:'caller asserted',requestLiteral:raw(input)})}),error=>error.code==='host');checks++;
  await assert.rejects(()=>api.verifyProtectedAdmission(raw(input),p,caps),error=>error.code==='native_contract_missing');checks++;
  return {suite:'protected-admission-pure',checks,passed:true,native_executed:false,admission_authority:false};
}

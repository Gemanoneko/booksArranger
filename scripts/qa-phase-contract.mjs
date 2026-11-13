// Pure, fixed QA phase and evidence contracts. No process or registry operations.
import {createHash} from 'node:crypto';
import path from 'node:path';
export const PA1_ENTRY='tests/real-shell-update.test.mjs';
export const PA1_TITLE='PA-1: in the real shell, an installer that cannot start keeps the app running; the old engine starts again';
export const ORIGINAL_NODE_ENTRIES=Object.freeze([
  "tests/release-contract.test.mjs",
  "tests/release-flow.test.mjs",
  "tests/update-controller.test.mjs",
  "tests/engine-update.test.mjs",
  "tests/launch-options.test.mjs",
  "tests/release-leased-executables.test.mjs",
  "tests/status-flight.test.mjs",
  "tests/quit-watch.test.mjs",
  "tests/python-check-batches.test.mjs",
  "tests/gate-source-guard.test.mjs",
  "tests/load-state.test.mjs",
  "tests/startup.test.mjs",
  "tests/desktop-loading.test.mjs",
  "tests/main-startup.test.mjs",
  "tests/qa-entry-context.test.mjs",
  "tests/real-shell-update.test.mjs",
  "tests/desktop-folder-picker.test.mjs",
  "tests/gate-scratch.test.mjs"
]);
export const CONTRACT_ENTRY='tests/real-shell-update-contract.test.mjs';
export const CANONICAL_NODE_ENTRIES=Object.freeze([...ORIGINAL_NODE_ENTRIES.filter(name=>name!==PA1_ENTRY),CONTRACT_ENTRY]);
export const PA1_ASSERTIONS=Object.freeze(['update_available_next_version','download_sha512_verified','shell_still_running_after_failed_install','installer_blocked_cause','windows_refusal_positive_control','fake_github_download_seen','old_engine_health_version','normal_quit_ends_shell']);
export const NATIVE_CASE=Object.freeze({phase:'PA-1',entry:PA1_ENTRY,title:PA1_TITLE});
export const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const hex=n=>new RegExp('^[a-f0-9]{'+n+'}$');
const need=(value,message)=>{if(!value)throw Error(message);};
const exact=(value,keys,label)=>{need(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|'),label+' fields differ');};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function phaseAccounting(canonical=CANONICAL_NODE_ENTRIES,native=[PA1_ENTRY]){
 need(Array.isArray(canonical)&&Array.isArray(native),'Phase lists required');
 const all=[...canonical,...native],expected=[...ORIGINAL_NODE_ENTRIES,CONTRACT_ENTRY];
 need(new Set(all).size===all.length&&same([...all].sort(),expected.sort()),'QA phase dropped, duplicated or renamed an entry');
 need(same(canonical,CANONICAL_NODE_ENTRIES)&&same(native,[PA1_ENTRY]),'Fixed canonical/native partition differs');
 return {schema:'books-qa-phases-v1',canonical:{scope:'non-app; owned Python/codec CLI fixtures and Node/DOM doubles',node_entries:[...canonical]},native:{...NATIVE_CASE,required:true,status:'PENDING; separate authority and normal native proof required'},prior_node_entries:18,total_node_entries:19};
}
export function requiresNativeQa(version){
 need(typeof version==='string'&&/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version),'Canonical release version required');
 const v=version.split('.').map(Number);return v[0]>0||v[1]>24||v[1]===24&&v[2]>=2;
}
export function binding(value){
 exact(value,['version','source_head','product_digest','build_id','artifact_manifest_sha256','runtime_manifest_sha256','phase_contract_sha256'],'Candidate binding');
 need(requiresNativeQa(value.version),'Native phase binding is before supported release');
 need(hex(40).test(value.source_head)&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value.build_id),'Candidate source/build identity differs');
 for(const k of ['product_digest','artifact_manifest_sha256','runtime_manifest_sha256','phase_contract_sha256'])need(hex(64).test(value[k]),'Candidate hash missing: '+k);
 return structuredClone(value);
}
export function sameBinding(actual,expected){binding(actual);binding(expected);need(Object.keys(expected).every(k=>actual[k]===expected[k]),'Native phase accepts a different candidate');}
export function normalOwned(result){
 need(result&&result.ok===true&&result.closed===true&&result.outputComplete===true&&result.code===0&&result.signal===null&&result.error===null,'Original normal owned result missing');
 for(const flag of ['forced','timedOut','overflow','truncated'])need(result[flag]===false,'Abnormal owned result: '+flag);
 need(result.closureError===null&&result.reason===null&&result.native?.complete===true&&result.native?.zero===true,'Original native closure proof missing');
 for(const field of ['active','assigned','listed','unsignaled'])need(result.native[field]===0,'Native processes not closed: '+field);
 need(Number.isSafeInteger(result.native.retained)&&result.native.retained>0&&Number.isSafeInteger(result.native.sampling?.queries)&&result.native.sampling.queries>0&&Number.isSafeInteger(result.native.sampling?.incompleteQueries)&&result.native.sampling.incompleteQueries>=0&&result.native.sampling.incompleteQueries<result.native.sampling.queries,'Native observation incomplete');
 need(typeof result.out==='string'&&typeof result.err==='string'&&result.ownership==='private-job','Exact private Job owner missing');
 return result;
}
export function validateAuthority(authority,expected){
 exact(authority,['schema','binding','approved_by','decision_ref','decision_text','approved_at','effects'],'Native authority');
 need(authority.schema==='books-native-qa-authority-v1'&&authority.approved_by==='Sergei','Explicit release-specific user authority absent');
 sameBinding(authority.binding,expected);
 need(typeof authority.decision_ref==='string'&&authority.decision_ref.length>=12&&authority.decision_ref.length<=512&&!/pending|placeholder|fixture|example|synthetic/i.test(authority.decision_ref),'Actual consent reference required');
 need(typeof authority.decision_text==='string'&&authority.decision_text.trim().length>=12&&authority.decision_text.length<=4096&&Number.isFinite(Date.parse(authority.approved_at)),'Actual consent decision required');
 exact(authority.effects,['hidden_private_app','invalid_installer_attempt','own_new_leaf_delete','leave_numeric_history_reference','ui_order_list_write'],'Authority effects');
 for(const k of ['hidden_private_app','invalid_installer_attempt','own_new_leaf_delete','leave_numeric_history_reference'])need(authority.effects[k]===true,'Consent does not allow '+k);
 need(authority.effects.ui_order_list_write===false,'Shared UIOrderList writes are forbidden');return authority;
}
export function validateFunctional(value,expected){
 sameBinding(value.binding,expected);need(value.schema==='books-pa1-functional-v1'&&same(value.case,NATIVE_CASE),'Exact PA-1 case proof missing');
 need(same(value.assertions,PA1_ASSERTIONS),'Original eight PA-1 assertions missing or reordered');
 for(const k of ['downloadVerified','invalidInstallerRefused','oldEngineRecovered','shellStayedRunning','healthVersionMatched','closedByQuit','payloadUnchanged','endpointsOwned','noVisibleOwnWindow'])need(value[k]===true,'PA-1 functional proof missing: '+k);
 need(value.intrusion===null&&typeof value.fixture_root==='string'&&typeof value.exe==='string','PA-1 private invocation proof missing');return value;
}
// Node's TAP reporter doubles diagnostic backslashes after JSON serialization.
// Decode only the plan's exact path spellings; never unescape arbitrary JSON or
// normalize an observed path (which could hide traversal or extra separators).
export function readFunctionalMarker(output,plan){
 const markers=[...output.matchAll(/^# BOOKS_PA1_FUNCTIONAL (.+)\r?$/gm)];need(markers.length===1,'Exactly one original PA-1 functional marker required');
 const value=JSON.parse(markers[0][1]),root=plan.fixture_root;
 need(typeof root==='string'&&/^[A-Z]:[\\/]/i.test(root)&&!/[\0\r\n]/.test(root)&&!/[. ]([\\/]|$)/.test(root)&&!root.slice(2).includes(':')&&!/[\\/]$/.test(root)&&root.replaceAll('\\','/')===path.win32.normalize(root).replaceAll('\\','/'),'Canonical planned fixture path required');
 const exe=path.win32.join(root,'app','Books Arranger.exe'),slashExe=exe.replaceAll('\\','/'),doubled=text=>text.replaceAll('\\','\\\\');
 const plain=value.fixture_root===root&&(value.exe===exe||value.exe===slashExe);
 const tap=value.fixture_root===doubled(root)&&value.exe===doubled(exe);
 need(plain||tap,'Functional paths differ from the exact planned fixture');
 if(!plain){value.fixture_root=root;value.exe=exe;}
 return validateFunctional(value,plan.binding);
}
export const NATIVE_ROLES=Object.freeze(['authority','plan','owned','controller_owned','callback','stdout','stderr','controller_stdout','controller_stderr','functional','postflight','cleanup']);
export function nativeEvidencePath(version){requiresNativeQa(version);return 'Docs/BooksArranger_NativeQA_v'+version+'.json';}
export function nativeEvidenceReportHash(text){const m=[...text.matchAll(/^Native QA evidence SHA256:\s*([a-f0-9]{64})\s*$/gm)];need(m.length===1,'Exact native QA evidence hash missing or ambiguous');return m[0][1];}
export function nativeRecordReferences(summary,version){
 need(summary?.schema==='books-native-qa-v1','Unsupported native evidence schema');exact(summary.records,NATIVE_ROLES,'Native record references');const paths=new Set();
 return NATIVE_ROLES.map(role=>{const ref=summary.records[role];exact(ref,['path','sha256','size'],'Native record');need(typeof ref.path==='string'&&new RegExp('^Docs/BooksArranger_NativeQA_v'+version.replaceAll('.','\\.')+'_Evidence/[a-z0-9-]+\\.(json|log)$').test(ref.path)&&!paths.has(ref.path),'Unsafe/duplicate native evidence path');paths.add(ref.path);need(hex(64).test(ref.sha256)&&Number.isSafeInteger(ref.size)&&ref.size>=0&&ref.size<=32*1024*1024,'Native record bounds');return [role,ref];});
}
export function validateNativeEvidence(summary,records,expected){
 exact(summary,['schema','binding','case','records'],'Native evidence');need(summary.schema==='books-native-qa-v1','Unsupported native evidence schema');sameBinding(summary.binding,expected);need(same(summary.case,NATIVE_CASE),'Native case identity changed');
 exact(summary.records,NATIVE_ROLES,'Native record references');exact(records,NATIVE_ROLES,'Native raw records');const decoded={},refs=new Set();
 for(const role of NATIVE_ROLES){const ref=summary.records[role];exact(ref,['path','sha256','size'],'Native '+role+' reference');need(typeof ref.path==='string'&&new RegExp('^Docs/BooksArranger_NativeQA_v'+expected.version.replaceAll('.','\\.')+'_Evidence/[a-z0-9-]+\\.(json|log)$').test(ref.path)&&!refs.has(ref.path),'Unsafe/duplicate native evidence path');refs.add(ref.path);need(hex(64).test(ref.sha256)&&Number.isSafeInteger(ref.size)&&ref.size>=0&&ref.size<=32*1024*1024,'Native record bounds');const raw=Buffer.from(records[role]);need(raw.length===ref.size&&hash(raw)===ref.sha256,'Native raw record changed: '+role);if(!['stdout','stderr','controller_stdout','controller_stderr'].includes(role))decoded[role]=JSON.parse(raw.toString('utf8'));}
 const authority=validateAuthority(decoded.authority,expected),plan=decoded.plan;need(plan.schema==='books-real-shell-plan-v1','Native plan missing');sameBinding(plan.binding,expected);need(plan.authority.sha256===summary.records.authority.sha256&&plan.phase_contract_sha256===expected.phase_contract_sha256&&same(plan.case,NATIVE_CASE),'Native plan authority/phase mismatch');
 const owned=normalOwned(decoded.owned),controller=normalOwned(decoded.controller_owned),callback=decoded.callback;need(callback.callback_received===true&&callback.error===null&&callback.start_write_error===null&&Array.isArray(callback.write_errors)&&callback.write_errors.length===0,'Original controller callback incomplete');
 need(callback.plan_sha256===summary.records.plan.sha256&&callback.binding_sha256===hash(JSON.stringify(expected))&&callback.owned_sha256===summary.records.owned.sha256&&callback.controller_owned_sha256===summary.records.controller_owned.sha256,'Controller callback binding differs');
 for(const role of ['stdout','stderr'])need(callback[role+'_sha256']===summary.records['controller_'+role].sha256&&callback[role+'_bytes']===summary.records['controller_'+role].size,'Outer callback must bind original controller streams, not inner TAP');
 need(Buffer.from(records.controller_stdout).toString('utf8')===controller.out&&Buffer.from(records.controller_stderr).toString('utf8')===controller.err,'Original controller output differs');
 need(Buffer.from(records.stdout).toString('utf8')===owned.out&&Buffer.from(records.stderr).toString('utf8')===owned.err,'Original owned output differs');
 need(/^# tests 1\r?$/m.test(owned.out)&&/^# pass 1\r?$/m.test(owned.out)&&/^# fail 0\r?$/m.test(owned.out)&&/^# skipped 0\r?$/m.test(owned.out)&&/^# cancelled 0\r?$/m.test(owned.out),'Exact mandatory PA-1 execution missing');
 need(same(readFunctionalMarker(owned.out,plan),decoded.functional),'Original functional output missing or changed');validateFunctional(decoded.functional,expected);
 const controllerMarkers=[...controller.out.matchAll(/^BOOKS_PA1_CONTROLLER (.+)\r?$/gm)];need(controllerMarkers.length===1,'Original controller marker missing');const control=JSON.parse(controllerMarkers[0][1]);need(control.schema==='books-pa1-controller-v1'&&control.plan_sha256===summary.records.plan.sha256&&control.owned_sha256===summary.records.owned.sha256&&control.cleanup_sha256===summary.records.cleanup.sha256&&control.postflight_sha256===summary.records.postflight.sha256,'Controller output does not bind native records');
 const post=decoded.postflight;sameBinding(post.binding,expected);need(post.schema==='books-native-postflight-v1'&&post.unchanged===true&&post.plan_sha256===summary.records.plan.sha256&&post.owned_sha256===summary.records.owned.sha256,'Native input/payload postflight missing');
 const cleanup=decoded.cleanup;sameBinding(cleanup.binding,expected);need(cleanup.schema==='books-own-tray-cleanup-v1'&&cleanup.authority_sha256===summary.records.authority.sha256&&cleanup.owned_sha256===summary.records.owned.sha256,'Cleanup authority/owner mismatch');
 for(const k of ['exactNewLeaf','sameHandle','deleted','closed','absenceVerified','preexistingUnchanged'])need(cleanup[k]===true,'Cleanup incomplete: '+k);
 need(cleanup.uiOrderListWritten===false&&cleanup.ownReferenceCount===1&&cleanup.ownReferenceBytes===8&&cleanup.partial===false&&cleanup.error===null&&hex(64).test(cleanup.uiOrderListSha256),'Cleanup residual/proof differs');
 need(cleanup.exe===decoded.functional.exe&&cleanup.fixture_root===decoded.functional.fixture_root&&/^\d+$/.test(cleanup.ownId),'Cleanup private identity differs');
 return {version:expected.version,case:NATIVE_CASE,passed:true,authority_ref:authority.decision_ref};
}

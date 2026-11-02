#!/usr/bin/env node
// One fixed, separately admitted PA-1 phase. No application is launched by import.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {randomBytes} from 'node:crypto';
import {hash,NATIVE_CASE,NATIVE_ROLES,normalOwned,readFunctionalMarker,validateNativeEvidence} from './qa-phase-contract.mjs';
import {need,readPin,ordinary,within,validatePlan,verifyInputs,verifyRecovery,freshFixture,treeFiles,sameFileTree,nativeAdapters,ownLeafDelta,cleanupOwnLeaf} from '../tests/real-shell-update-support.mjs';
const encode=value=>Buffer.from(JSON.stringify(value));
async function freshWrite(file,bytes){await fs.writeFile(file,bytes,{flag:'wx'});return {path:file,sha256:hash(bytes),size:bytes.length};}
// The external reviewed driver owns this controller with unchanged runOwned.
// Its original normal-zero receipt is mandatory before finalizeNativeEvidence.
export async function runFixedPhase(planPath,planSha,deadline,adapters=null){
 const stat=await ordinary(planPath,{file:true});need(stat.size>0&&stat.size<=16*1024*1024,'Bounded private plan required');
 const raw=await fs.readFile(planPath);need(hash(raw)===planSha,'Externally pinned plan differs');const plan=JSON.parse(raw);
 const authority=JSON.parse(await readPin(plan.authority));validatePlan(plan,authority);need(within(planPath,plan.evidence_root),'Plan outside own evidence arena');
 need(Number.isSafeInteger(deadline)&&deadline>Date.now()&&deadline-Date.now()<=600000,'One original remaining deadline required');
 const remaining=()=>{const left=deadline-Date.now();need(left>0,'Whole native phase deadline expired');return left;};remaining();
 const manifest=await verifyInputs(plan);remaining();
 need(hash(await fs.readFile(process.execPath))===plan.node.sha256,'Controller Node differs');
 const app=await freshFixture(plan,manifest);remaining();
 const native=adapters||nativeAdapters(plan,authority);native.monitor.checkWindows();
 const current=await native.registry.snapshot();let before=current;
 if(plan.recovery){
  const prior=await verifyRecovery(plan),own=ownLeafDelta(prior.baseline,current,path.join(app,'Books Arranger.exe'),plan.expected_tray_types);
  before=prior.baseline;
  await freshWrite(path.join(plan.evidence_root,'recovery-preflight.private.json'),encode({original_plan_sha256:plan.recovery.original_plan.sha256,original_controller_owned_sha256:plan.recovery.original_controller_owned.sha256,original_forced_failure:true,original_final_native_zero:true,baseline_sha256:hash(encode(before)),ownId:own.id,existingOwnLeaf:true,ownReferenceCount:1,ownReferenceBytes:8,foreignUnchanged:true,uiOrderListWritten:false}));
 }
 await freshWrite(path.join(plan.evidence_root,'baseline.private.json'),encode(before));
 const owner=adapters?.runOwned||(await import(pathToFileURL(plan.helper.path).href)).runOwned;
 const nonce=randomBytes(32).toString('hex');
 const result=await owner(plan.node.path,['--test','--test-reporter=tap',path.join(plan.source_root,NATIVE_CASE.entry)],{
  cwd:plan.source_root,env:{...plan.environment,BOOKS_PA1_PLAN:planPath,BOOKS_PA1_PLAN_SHA:planSha,BOOKS_PA1_NONCE:nonce,BOOKS_PA1_DEADLINE:String(deadline)},
  timeoutMs:remaining(),koffiRoot:plan.koffi_root});
 const owned=await freshWrite(path.join(plan.evidence_root,'owned.json'),encode(result));
 await freshWrite(path.join(plan.evidence_root,'stdout.log'),Buffer.from(result.out||''));await freshWrite(path.join(plan.evidence_root,'stderr.log'),Buffer.from(result.err||''));
 normalOwned(result);remaining();
 const functional=readFunctionalMarker(result.out,plan);
 await freshWrite(path.join(plan.evidence_root,'functional.json'),encode(functional));
 let cleanup;try{cleanup=await cleanupOwnLeaf({plan,authority,owned:result,before,adapter:native.registry,deadline});}
 catch(error){if(error.cleanup)await freshWrite(path.join(plan.evidence_root,'cleanup-failure.json'),encode(error.cleanup));throw error;}
 const cleanupRef=await freshWrite(path.join(plan.evidence_root,'cleanup.json'),encode(cleanup));remaining();
 await verifyInputs(plan);need(sameFileTree(await treeFiles(app),manifest.payload.files),'Copied payload changed after normal closure');remaining();
 const post={schema:'books-native-postflight-v1',binding:plan.binding,unchanged:true,plan_sha256:planSha,owned_sha256:owned.sha256,baseline_sha256:hash(encode(before))};
 const postRef=await freshWrite(path.join(plan.evidence_root,'postflight.json'),encode(post));native.monitor.dispose();
 const marker={schema:'books-pa1-controller-v1',plan_sha256:planSha,owned_sha256:owned.sha256,cleanup_sha256:cleanupRef.sha256,postflight_sha256:postRef.sha256};
 console.log('BOOKS_PA1_CONTROLLER '+JSON.stringify(marker));return marker;
}
// This is the actual fixed outer-driver stream behavior. A successful transport
// forwards the original controller streams byte-for-byte; it never forwards the
// inner TAP stream as though it came from this process.
export async function forwardControllerStreams(result,streams){
 normalOwned(result);
 for(const [name,text] of [['stdout',result.out],['stderr',result.err]]){
  const bytes=Buffer.from(text,'utf8');
  await new Promise((resolve,reject)=>streams[name].write(bytes,error=>error?reject(error):resolve()));
 }
}
export async function runNativeController(planPath,planSha,deadline){
 const stat=await ordinary(planPath,{file:true});need(stat.size>0&&stat.size<=16*1024*1024,'Bounded private plan required');
 const raw=await fs.readFile(planPath);need(hash(raw)===planSha,'Externally pinned plan differs');const plan=JSON.parse(raw);
 const authority=JSON.parse(await readPin(plan.authority));validatePlan(plan,authority);need(within(planPath,plan.evidence_root),'Plan outside own evidence arena');
 need(Number.isSafeInteger(deadline)&&deadline>Date.now()&&deadline-Date.now()<=600000,'One original remaining deadline required');
 await verifyInputs(plan);need(hash(await fs.readFile(process.execPath))===plan.node.sha256,'Driver Node differs');
 const {runOwned}=await import(pathToFileURL(plan.helper.path).href),nonce=randomBytes(32).toString('hex');
 const remaining=deadline-Date.now();need(remaining>0,'Whole native phase deadline expired');
 const result=await runOwned(plan.node.path,[path.join(plan.source_root,'scripts/qa-real-shell-phase.mjs'),'--owned-phase',planPath,planSha,nonce],{cwd:plan.source_root,env:{...plan.environment,BOOKS_PA1_CONTROLLER_NONCE:nonce,BOOKS_PA1_CONTROLLER_DEADLINE:String(deadline)},timeoutMs:remaining,koffiRoot:plan.koffi_root});
 await freshWrite(path.join(plan.evidence_root,'controller-owned.json'),encode(result));
 await freshWrite(path.join(plan.evidence_root,'controller-stdout.log'),Buffer.from(result.out||''));
 await freshWrite(path.join(plan.evidence_root,'controller-stderr.log'),Buffer.from(result.err||''));
 normalOwned(result);await verifyInputs(plan);need(Date.now()<deadline,'Whole native phase deadline expired');
 await forwardControllerStreams(result,{stdout:process.stdout,stderr:process.stderr});return result;
}
// Called only after the fixed outer driver has its durable actual callback and
// original normal controller closure. Raw foreign registry baseline is excluded.
export function evidenceSummary(binding,rawRecords){
 const records={};for(const role of NATIVE_ROLES){const raw=Buffer.from(rawRecords[role]);records[role]={path:'Docs/BooksArranger_NativeQA_v'+binding.version+'_Evidence/'+role.replaceAll('_','-')+(['stdout','stderr','controller_stdout','controller_stderr'].includes(role)?'.log':'.json'),sha256:hash(raw),size:raw.length};}
 const summary={schema:'books-native-qa-v1',binding,case:NATIVE_CASE,records};validateNativeEvidence(summary,rawRecords,binding);return summary;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  if(process.argv.length===5&&process.argv[2]==='--run'){
   await runNativeController(process.argv[3],process.argv[4],Date.now()+600000);
  }else{
   need(process.argv.length===6&&process.argv[2]==='--owned-phase','Default refused: use the exact reviewed owned native invocation');
   need(process.env.BOOKS_PA1_CONTROLLER_NONCE===process.argv[5]&&/^[a-f0-9]{64}$/.test(process.argv[5]),'Original owned controller nonce absent');
   await runFixedPhase(process.argv[3],process.argv[4],Number(process.env.BOOKS_PA1_CONTROLLER_DEADLINE));
  }
 }catch(error){console.error(error.message);process.exitCode=1;}
}

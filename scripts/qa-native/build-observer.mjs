/** SOURCE-ONLY finite engineering build observer; not canonical QA admission.
 * Installed Node/runOwned/Koffi/Windows pre-Job startup is trusted and unbounded.
 * Ordinary final filesystem/stdio IO is trusted, not forcibly bounded; late exit never accepts.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';
import {runOwned} from 'file:///C:/Antigravity%20Projects/Studio%20Illuminati/.claude/skills/qa-handoff/scripts/bounded-check.mjs';
import {createEngineeringOwner,newOwnerId,validateOwnedResult,matchController,NODE} from './engineering-owner.mjs';
import {Leases} from './build-worker.mjs';
import {validateBuildPlan} from './build-watchdog.mjs';
const KOFFI='C:/Antigravity Projects/Studio Illuminati/WIP/QuickLaunch/node_modules/koffi';
const WORKER='C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/scripts/qa-native/build-worker.mjs';
const STUDIO='C:/Antigravity Projects/Studio Illuminati';
const PLAN_PARENT='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-joint-v4-LJpbEG';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const requireThat=(v,m)=>{if(!v)throw Error(m);};const same=(a,b)=>typeof a==='string'&&typeof b==='string'&&path.win32.resolve(a).toLowerCase()===path.win32.resolve(b).toLowerCase();
const ENGINEERING_SOURCE_REVIEWED=false;
const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function bindWire(result,evidence,ownerId,plan,planSha){
 const identity=validateOwnedResult(result,evidence,ownerId);const lines=result.out.trim().split('\n');requireThat(lines.length===1&&lines[0].length<1048576,'One bounded controller protocol record required');const wire=JSON.parse(lines[0]);
 requireThat(wire.schema==='books-native-engineering-wire-v2'&&wire.outer_owner_id===ownerId&&wire.invocation_id===plan.invocation_id&&wire.plan_sha256===planSha&&wire.source_sha256===plan.source_sha256&&wire.recipe_sha256===plan.recipe_sha256&&wire.toolchain_manifest_sha256===plan.toolchain_manifest_sha256,'Controller wire binding mismatch');matchController(identity,wire.worker);return {wire,identity};
}
export function validateRecords(wire,startup,work,plan,planSha,ownerId){
 const expected={invocation_id:plan.invocation_id,plan_sha256:planSha,source_sha256:plan.source_sha256,recipe_sha256:plan.recipe_sha256,toolchain_manifest_sha256:plan.toolchain_manifest_sha256,outer_owner_id:ownerId};
 for(const record of [startup,work]){requireThat(record.authoritative===false,'Preliminary record cannot authorize completion');for(const [key,value]of Object.entries(expected))requireThat(record[key]===value,'Frozen record binding mismatch: '+key);requireThat(eq(record.worker,wire.worker),'Frozen worker identity mismatch');}
 requireThat(startup.schema==='books-native-engineering-startup-v2'&&work.schema==='books-native-engineering-work-v2'&&eq(work.startup,wire.startup)&&eq(work.directories,wire.directories),'Startup/work/schema/namespace digest linkage mismatch');
 requireThat(work.inner_owner_id!==ownerId,'Inner and outer owners must differ');validateOwnedResult(work.inner_result,work.inner_evidence,work.inner_owner_id);
 requireThat(Array.isArray(work.outputs)&&work.outputs.length===2,'Exact two compiler outputs required');
}
function verifyTrustedEngineeringStartup(plan){
 requireThat(/^[a-f0-9]{64}$/.test(plan.owner_admission_sha256)&&plan.owner_admission_sha256!=='0'.repeat(64),'Pinned accepted source/admission required');
 const raw=fs.readFileSync(plan.trusted_base_manifest);requireThat(raw.length<1048576&&hash(raw)===plan.trusted_base_manifest_sha256,'Trusted startup base manifest drift');const base=JSON.parse(raw);requireThat(base.schema==='books-engineering-trusted-startup-base-v1'&&base.files.length===95,'Exact engineering installed base required');
 for(const item of base.files){const s=fs.lstatSync(item.path,{bigint:true});requireThat(s.isFile()&&!s.isSymbolicLink()&&s.nlink===1n&&String(s.dev)===item.dev&&String(s.ino)===item.ino&&String(s.mtimeNs)===item.mtimeNs&&Number(s.size)===item.size&&hash(fs.readFileSync(item.path))===item.sha256,'Trusted engineering input changed');}
 // This verification is NOT a pre-import lease/sandbox: input quiescence remains mandatory.
}
export async function observe(argv){
 requireThat(ENGINEERING_SOURCE_REVIEWED,'Observer/worker/adapter/source/manifest/invocation await independent admission; no compilation');
 requireThat(argv.length===4&&argv[0]==='--plan'&&argv[2]==='--plan-sha'&&/^[a-f0-9]{64}$/.test(argv[3]),'Exact plan/hash arguments required');const planPath=path.win32.resolve(argv[1]);requireThat(same(path.win32.dirname(planPath),PLAN_PARENT),'Unknown engineering plan directory');
 const raw=fs.readFileSync(planPath);requireThat(raw.length<1048576&&hash(raw)===argv[3],'Startup plan drift');const plan=JSON.parse(raw),p=validateBuildPlan(plan);verifyTrustedEngineeringStartup(plan);
 const ownerId=newOwnerId(),owner=createEngineeringOwner(KOFFI,{ownerId}); // Explicit unbounded trusted PRE-JOB startup.
 const started=performance.now(),epochDeadline=Date.now()+600000;
 const result=await runOwned(NODE,[WORKER,'--plan',planPath,'--plan-sha',argv[3],'--deadline',String(epochDeadline),'--outer-owner',ownerId],{cwd:STUDIO,env:{SystemRoot:'C:\Windows',WINDIR:'C:\Windows',PATH:'C:\Program Files\nodejs;C:\Windows\System32'},timeoutMs:598000,koffiRoot:KOFFI,maxBytes:1048576,jobFactory:()=>owner});
 const evidence=owner.evidence();const {wire,identity}=bindWire(result,evidence,ownerId,plan,argv[3]);requireThat(performance.now()-started<598000,'No final namespace IO after closure reserve');
 const io=new Leases(epochDeadline);let finalRecord;try{
  // Reacquire ONLY the ORIGINAL native objects authenticated by trusted controller wire, never a replacement.
  io.rejoinDirectories(wire.directories);const frozenPlan=io.freeze({path:planPath,size:raw.length,sha256:argv[3]});requireThat(hash(frozenPlan.bytes)===argv[3],'Frozen plan mismatch');
  requireThat(same(wire.startup.path,p.evidence+'/startup.json')&&same(wire.work.path,p.evidence+'/worker-result.json'),'Unexpected evidence path');
  const startup=io.readRecord(wire.startup),work=io.readRecord(wire.work);validateRecords(wire,startup,work,plan,argv[3],ownerId);
  const wanted=['books-qa-watchdog.exe','books-qa-watchdog.obj'].map(n=>p.out+'/'+n);for(const output of work.outputs){requireThat(wanted.some(x=>same(x,output.path)),'Unexpected output path');wanted.splice(wanted.findIndex(x=>same(x,output.path)),1);io.readRecordBytes(output);}requireThat(wanted.length===0,'Duplicate/missing output proof');
  const tc=io.freeze({path:plan.toolchain_manifest,size:plan.toolchain_manifest_size,sha256:plan.toolchain_manifest_sha256});const allowed=new Set(JSON.parse(tc.bytes).files.filter(x=>/\.exe$/i.test(x.path)).map(x=>path.win32.resolve(x.path).toLowerCase()));allowed.add(path.win32.resolve(NODE).toLowerCase());for(const member of identity.observed)requireThat(allowed.has(path.win32.resolve(member.image_path_at_admission).toLowerCase()),'Outer observed image outside exact fixed runtime/toolchain');
  // This record is explicitly NONAUTHORITATIVE. No success/accepted artifact can survive a late fsync as a grant.
  finalRecord=io.writeRecord(p.evidence+'/observer-result.json',{schema:'books-native-engineering-observer-record-v2',authoritative:false,invocation_id:plan.invocation_id,plan_sha256:argv[3],outer_owner_id:ownerId,startup:wire.startup,work:wire.work,outer_native:evidence,requirements:['exact records and digests','actual same-owner native closure','observed observer exit0','final assigned-work elapsed under600000']});
  io.readRecordBytes(finalRecord);requireThat(performance.now()-started<600000,'Final durability exceeded engineering budget');
 }finally{io.teardown();}
 requireThat(performance.now()-started<600000,'Final native fence teardown exceeded budget');
 console.log(JSON.stringify({schema:'books-native-engineering-observer-completion-v2',requires_observed_exit0:true,invocation_id:plan.invocation_id,plan_sha256:argv[3],outer_owner_id:ownerId,record:finalRecord,final_elapsed_ms:performance.now()-started,deadline_epoch_ms:epochDeadline}));
 return {code:0,started};
}
if(typeof process!=='undefined'&&process.argv[1]&&same(process.argv[1],fileURLToPath(import.meta.url)))observe(process.argv.slice(2)).then(({code,started})=>{process.exitCode=code;process.on('exit',()=>{if(performance.now()-started>=600000)process.exitCode=2;});}).catch(error=>{console.error('Engineering observer REFUSED: '+error.message);process.exitCode=2;});

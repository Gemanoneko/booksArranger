#!/usr/bin/env node
// Pure-node handoff graph; the outer protocol-2 supervisor owns its descendants.
// No GUI launch, installer execution, live catalog or source-library access.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {spawn} from 'node:child_process';import {fileURLToPath} from 'node:url';
import {pythonBatches,validatePythonReports,pythonWorkerLayout,workerSecondsReport} from './python-check-batches.mjs';
import {liveCatalogRefusal} from './gate-source-guard.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
// A live checkout (data/ holds its catalog) is refused before anything is read, copied or written (2026-10-24).
{const refusal=liveCatalogRefusal(root);if(refusal){fs.writeSync(2,refusal+'\n');process.exit(1);}}
const fixture=JSON.parse(fs.readFileSync(path.join(root,'scripts/qa-runtime.json'),'utf8'));
// The QA runtime is identified by the pinned hashes below; its folder is machine-local. BOOKS_QA_RUNTIME_ROOT names a
// folder holding python/ and ffmpeg/ (the pinned default lived in a worktree that no longer exists).
const runtimeRoot=process.env.BOOKS_QA_RUNTIME_ROOT;
if(runtimeRoot){if(!path.isAbsolute(runtimeRoot))throw Error('BOOKS_QA_RUNTIME_ROOT must be an absolute path');fixture.python.path=path.join(runtimeRoot,'python','python.exe');fixture.ffmpeg.root=path.join(runtimeRoot,'ffmpeg');}
const python=fixture.python.path,sha=fixture.python.sha256;
for(const [name,expected] of Object.entries(fixture.ffmpeg.files)){const file=path.join(fixture.ffmpeg.root,name),stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.size!==expected.size||createHash('sha256').update(fs.readFileSync(file)).digest('hex')!==expected.sha256)throw Error('Bundled QA media runtime differs');}
if(createHash('sha256').update(fs.readFileSync(python)).digest('hex')!==sha)throw Error('QA Python runtime differs');
fs.mkdirSync(path.join(root,'scratch','source-fallback-2026-10-11'),{recursive:true});
const fixtureRootMap = {"test_automatic_processing.AREA":"scratch/a","test_local_identity.AREA":"scratch/a","test_local_identity_fixes.AREA":"scratch/a","test_split_books.AREA":"scratch/a","test_multisource.SCRATCH":"scratch/multisource","test_local_gate_consistency.ROOT":"scratch/local-gate","test_series_backfill.AREA":"scratch/s"};
const deadline=Date.now()+540000;
// 2026-10-25 (the gate left 4 s of its 540 s deadline on a quiet machine): the syntax checks, the node cases and the page
// scripts run in one chain beside the Python workers; they used to run before and after them, on the deadline's critical
// path. Same checks, in the same order inside the chain, each bounded by the same deadline, and a failure still fails the
// gate, but only after every Python worker and the chain have finished.
const sideEnv={...process.env,PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:'',BOOKS_QA_RUN_ROOT:root,BOOKS_QA_FIXTURE_ROOT:path.join(root,'scratch','f'),PATH:fixture.ffmpeg.root+path.delimiter+(process.env.PATH||'')};
function runAsync(exe,args){return new Promise(resolve=>{const out=[],err=[];let error=null,timedOut=false;const child=spawn(exe,args,{cwd:root,env:sideEnv,windowsHide:true,stdio:['ignore','pipe','pipe']});const timer=setTimeout(()=>{timedOut=true;child.kill();},Math.max(1,deadline-Date.now()));child.stdout.on('data',d=>out.push(d));child.stderr.on('data',d=>err.push(d));child.on('error',e=>{error=e.message;});child.on('close',status=>{clearTimeout(timer);resolve({status,error,timedOut,stdout:Buffer.concat(out).toString('utf8'),stderr:Buffer.concat(err).toString('utf8')});});});}
const syntaxFiles=['desktop/main.js','desktop/preload.js','desktop/update-controller.js','desktop/engine-update.js','desktop/launch-options.js','desktop/status-flight.js','desktop/quit-watch.js','web/desktop-ui.js','desktop/startup.js','web/load-state.js'],nodeTests=['tests/release-contract.test.mjs','tests/release-flow.test.mjs','tests/update-controller.test.mjs','tests/engine-update.test.mjs','tests/launch-options.test.mjs','tests/release-leased-executables.test.mjs','tests/status-flight.test.mjs','tests/quit-watch.test.mjs','tests/python-check-batches.test.mjs','tests/gate-source-guard.test.mjs','tests/load-state.test.mjs','tests/startup.test.mjs','tests/desktop-loading.test.mjs','tests/main-startup.test.mjs','tests/qa-entry-context.test.mjs','tests/real-shell-update.test.mjs'];
const frontendScripts=fs.readdirSync(path.join(root,'tests')).filter(name=>/^test_.*\.js$/.test(name)).sort();
function sideChecks(){return (async()=>{const log=[];let failure=null,nodeOutput='';
 const step=async(exe,args)=>{if(failure)return null;const r=await runAsync(exe,args);log.push(r.stdout,r.stderr);if(r.error||r.timedOut||r.status!==0)failure=(r.error||(r.timedOut?'deadline':'exit '+r.status))+': '+args.join(' ');return r;};
 for(const name of syntaxFiles)await step(process.execPath,['--check',name]);
 const node=await step(process.execPath,['--test','--test-reporter=tap',...nodeTests]);if(node)nodeOutput=node.stdout;
 for(const name of frontendScripts)await step(process.execPath,[path.join('tests',name)]);
 return {log,failure,nodeOutput};})();}
// Extend the original desktop/media graph with every integrated maintenance and
// automatic/status boundary. Report discovery rather than a stale literal count.
const patterns=['test_desktop_quit.py','test_desktop_catalog.py','test_desktop_host.py','test_build_guard.py','test_working_cleanup.py','test_working_precision.py','test_working_lifecycle.py','test_storage_cleanup.py','test_automatic_media_policy.py','test_automatic_media.py','test_standing_admission.py','test_attempt_working_lifecycle.py','test_published_snapshot_lifecycle.py','test_attention_failure_policy.py','test_automatic_record_retry.py','test_web.py','test_sqlite_busy.py','test_automatic_processing.py','test_status_read_contention.py'];
patterns.push('test_destination_admission.py');
patterns.push('test_groups_filters.py','test_candidate_source_refresh.py','test_local_identity_fixes.py');
patterns.push('test_desktop_owner_recovery.py','test_failed_m4b_retry.py');
patterns.push('test_m4b_preservation.py','test_m4b_dispatch.py');
patterns.push('test_zone_identifier.py');
patterns.push('test_status_snapshot.py');
patterns.push('test_startup_published_check.py');
patterns.push('test_replacement_jobs.py');
patterns.push('test_cleanup_resume.py','test_blocked_retry.py');
patterns.push('test_progress_rows.py','test_progress.py');
patterns.push('test_reacquire_sources.py','test_mp3_tag_repair.py','test_library_settings.py','test_multisource.py','test_local_gate_consistency.py','test_publication_locations.py','test_publication_binding.py','test_publication_consumers.py','test_directory_flush.py','test_relocation_progress.py','test_output_migration.py','test_migration_operation.py','test_migration_planning.py','test_derived_migration.py','test_relocated_replacement.py','test_relocated_chapter_repair.py','test_metadata_choices.py','test_attention_audio_admission.py','test_manual_research.py','test_manual_metadata.py','test_organization.py','test_attention_actions.py','test_review_backend.py','test_attention_repair.py','test_quiet_status.py','test_status_under_load.py','test_backup_rule.py');
patterns.push('test_manifest_compatibility.py','test_producer_recovery.py','test_producer_recovery_http.py','test_retry_intent.py','test_merge_http.py');
patterns.push('test_recovery_retention.py');  // the recovery-purge module's own suite (Senua v0.16.8 F3)
patterns.push('test_series_research.py','test_local_identity.py');  // v0.16.11 series research
patterns.push('test_series_backfill.py','test_quicktime_chapters.py','test_inventory.py');  // v0.16.12 series backfill, list reads
patterns.push('test_series_fallbacks.py','test_openlibrary_index.py','test_public_work_identity.py');  // v0.18 source/ordinal, shared quotas, authenticated sparse imports
patterns.push('test_bulk_retry_receipts.py','test_catalog_contention.py');
patterns.push('test_retry_start_fence.py');
patterns.push('test_inplace_m4b.py','test_source_proofs.py');  // v0.21.0 in-place single-M4B edit, attempt-scoped source fingerprints
patterns.push('test_iron_skazka.py');  // v0.21.1 legacy MP3 tag-repair retry, Confirm and convert, no-restart proof, verified old-file removal
patterns.push('test_local_admission.py','test_catalog_paging.py');  // local-agreement identity end to end; review paging/filters without source reads. Both broke unseen outside the gate (0cf4376, d2ff261)
patterns.push('test_source_cleanup.py','test_source_folders.py','test_safety_boundaries.py','test_cleanup_scope.py');  // 0.21.3 audit M1: the source-removal suites (Sergei's deletion rule, rulings 2 and 1a)
patterns.push('test_identity_v5.py');  // 0.22.0: title + author is enough (Sergei 2026-10-24, rulings 6, 6a, 13, 14, 15)
patterns.push('test_sorted_wiring.py');  // Senua 0.21.3 F6: the production output-folder wiring, no fixture
patterns.push('test_approve_as_is.py');  // 0.22.0: Sergei as a source and Approve as is (rulings 6a, 6b, 10, 11a)
patterns.push('test_author_rules.py');  // 0.22.0: Sergei's lasting author rules (ruling 12) and his 2026-10-24 answers
patterns.push('test_attention_list.py');  // 0.22.0: the one to-do list, its reasons, counts and stale rows (ruling 10)
patterns.push('test_list_speed.py');  // 0.22.0: the book list never waits for group_lock behind an approval (ruling 18)
patterns.push('test_todo_holds.py');  // 0.22.0 review: the three hold rows, their causes, saved order, coverage (Judy)
patterns.push('test_join_parts.py');  // 0.22.0: ruling 19, the parts of one book in one folder are joined
patterns.push('test_split_books.py','test_collection_identity.py');  // Senua 0.22.0 early review m7: changed in 0.22.0, were outside the gate
patterns.push('test_m4b_join.py','test_part_sets.py');  // 0.22.0: rulings 19a and 19 (M4B parts joined keeping their chapters; bare-numbered sets decided by their chapters)
patterns.push('test_book_delete.py');  // 0.22.0: ruling 23, Delete book (only its own files, never Sorted, records last)
patterns.push('test_lock_timing.py');  // 0.22.1: presses never wait behind background work (group_lock, the approval's re-check, list limit)
patterns.push('test_gap_fill.py');  // 0.22.1: approval on local identity at once, optional fields in the background, per-site lanes
patterns.push('test_folder_structure.py');  // 0.22.1: items 9 and 10, Sergei's folder structure, clean file-name order, number-titled books
patterns.push('test_desktop_update.py');  // 0.22.1: the fail-less updater's engine fence, the busy-engine matrix (ruling 27)
patterns.push('test_startup_loading.py');  // 0.22.1: the engine answers at once and loads in the background (ruling 28)
patterns.push('test_action_queue.py');  // 0.22.1: queued Retry, Repair and Delete book (backlog 2 and 3; Judy section 1)
patterns.push('test_identity_0222.py');  // 0.22.2: W17, W18, «Призрак дома на холме», «Джек из Тени», m-14, ruling 33
patterns.push('test_catalog_busy.py');  // 0.22.2: a busy catalog never stops a run (cache reads never write, presync, busy is a wait)
patterns.push('test_start_while_converting.py');  // 0.22.2: ruling 34, Start works while audiobooks convert; the scan waits
patterns.push('test_original_title_wait.py');  // 0.22.2: ruling 29, a translation waits for its English original title
const code=`import sys,unittest,json,pathlib,time
sys.path.insert(0,sys.argv[1]);loader=unittest.defaultTestLoader;s=unittest.TestSuite();patterns=json.loads(sys.argv[2])
for p in patterns:s.addTests(loader.discover(sys.argv[1]+'/tests',pattern=p))
runroot=pathlib.Path(sys.argv[1]).resolve();mapping=json.loads(sys.argv[3]);mapped=[];absent=[]
for target,relative in mapping.items():
 module,attr=target.rsplit('.',1);destination=(runroot/relative).resolve()
 if not destination.is_relative_to(runroot/'scratch'):raise ValueError('Fixture root outside private scratch')
 if module not in sys.modules:absent.append(target);continue
 obj=sys.modules[module]
 if not isinstance(getattr(obj,attr,None),pathlib.Path):raise ValueError('Fixture alias changed: '+target)
 destination.mkdir(parents=True,exist_ok=True);setattr(obj,attr,destination);mapped.append(target)
def ids(suite):
 for item in suite:
  if isinstance(item,unittest.TestSuite):yield from ids(item)
  else:yield item.id()
inventory=list(ids(s));print('Fixture root map:',json.dumps({'mapped':mapped,'absent':absent}),flush=True)
print('Integrated Python batch cases:',len(inventory),flush=True)
class Timed(unittest.TextTestResult):
 seconds={};last=None
 def startTestRun(self):super().startTestRun();Timed.last=time.perf_counter()
 def stopTest(self,test):
  super().stopTest(test);now=time.perf_counter();name=type(test).__module__.split('.')[0]+'.py';Timed.seconds[name]=Timed.seconds.get(name,0)+now-Timed.last;Timed.last=now
r=unittest.TextTestRunner(verbosity=2,resultclass=Timed).run(s)
report={'batch':int(sys.argv[4]),'patterns':patterns,'ids':inventory,'discovered':len(inventory),'completed':r.testsRun,'skipped':len(r.skipped),'failures':len(r.failures),'errors':len(r.errors),'success':r.wasSuccessful(),
 'module_seconds':{k:round(v,1) for k,v in sorted(Timed.seconds.items(),key=lambda item:-item[1])}}
print('BOOKS_PYTHON_BATCH_RESULT '+json.dumps(report),flush=True)
sys.exit(not r.wasSuccessful() or bool(r.skipped) or r.testsRun!=len(inventory))
`;
// Copy only canonical source inputs. Runtime dependencies and generated scratch
// are not mutable test inputs; each Python worker gets its own source/cwd/TEMP.
function inventory(directory,relative=''){
 const files=[];
 for(const item of fs.readdirSync(path.join(directory,relative),{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){
  if(!relative&&['scratch','node_modules','.git','dist','build-cache'].includes(item.name))continue;
  const name=path.join(relative,item.name),file=path.join(directory,name),stat=fs.lstatSync(file);
  if(stat.isSymbolicLink())throw Error('Linked Python batch input');
  if(stat.isDirectory())files.push(...inventory(directory,name));
  else if(stat.isFile())files.push([name,createHash('sha256').update(fs.readFileSync(file)).digest('hex')]);
  else throw Error('Nonordinary Python batch input');
 }
 return files;
}
const inputs=inventory(root),batches=pythonBatches(patterns);
const side=sideChecks();  // beside the Python workers (see sideChecks)
const workers=batches.map((batch,i)=>{
 const layout=pythonWorkerLayout(i),directory=path.join(root,layout.relative);fs.mkdirSync(directory); // fresh or refuse
 for(const [name,sha] of inputs){const destination=path.join(directory,name),bytes=fs.readFileSync(path.join(root,name));if(createHash('sha256').update(bytes).digest('hex')!==sha)throw Error('Python batch source changed during copy');fs.mkdirSync(path.dirname(destination),{recursive:true});fs.writeFileSync(destination,bytes,{flag:'wx'});}
 if(JSON.stringify(inventory(directory))!==JSON.stringify(inputs))throw Error('Python batch copy differs');
 for(const relative of layout.requiredDirectories)fs.mkdirSync(path.join(directory,relative),{recursive:true});
 const temp=path.join(directory,'scratch','tmp');
 return {directory,temp,batch,i};
});
let outputBytes=0,overflow=false;
const results=await Promise.all(workers.map(worker=>new Promise(resolve=>{
 const started=performance.now();
 const env={...process.env,PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:'',BOOKS_QA_RUN_ROOT:worker.directory,BOOKS_QA_FIXTURE_ROOT:path.join(worker.directory,'scratch','f'),TEMP:worker.temp,TMP:worker.temp,PATH:fixture.ffmpeg.root+path.delimiter+(process.env.PATH||'')};
 for(const key of Object.keys(env))if(/^GIT_(DIR|WORK_TREE|INDEX_FILE|COMMON_DIR)$/i.test(key))delete env[key];
 const out=[],err=[];let error=null,timedOut=false;
 const child=spawn(python,['-I','-B','-c',code,worker.directory,JSON.stringify(worker.batch),JSON.stringify(fixtureRootMap),String(worker.i)],{cwd:worker.directory,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
 const timer=setTimeout(()=>{timedOut=true;child.kill();},Math.max(1,deadline-Date.now()));
 const capture=chunks=>data=>{outputBytes+=data.length;if(outputBytes>16*1024*1024){overflow=true;child.kill();return;}chunks.push(data);};
 child.stdout.on('data',capture(out));child.stderr.on('data',capture(err));child.on('error',e=>{error=e.message;});
 child.on('close',status=>{clearTimeout(timer);resolve({status,error,timedOut,seconds:(performance.now()-started)/1000,out:Buffer.concat(out).toString('utf8'),err:Buffer.concat(err).toString('utf8')});});
})));
// Never return on one worker's failure while the others are still running.
for(let i=0;i<results.length;i++){process.stdout.write(results[i].out);process.stderr.write(results[i].err);}
const sideResult=await side;process.stdout.write(sideResult.log.join(''));
const workerSeconds=workerSecondsReport(batches,results.map(r=>r.seconds));for(const line of workerSeconds.lines)console.log(line);
for(const worker of workers)if(JSON.stringify(inventory(worker.directory))!==JSON.stringify(inputs))throw Error('Python batch source changed during tests');
if(overflow||results.some(r=>r.error||r.timedOut||r.status!==0))throw Error('Python batch failed, exceeded output cap or original deadline');
if(sideResult.failure)throw Error('Focused desktop check failed: '+sideResult.failure);
const nodeOutput=sideResult.nodeOutput,nodeCount=Number(/^# tests (\d+)$/m.exec(nodeOutput)?.[1]);
if(!nodeCount||!/^# fail 0$/m.test(nodeOutput)||!/^# skipped 0$/m.test(nodeOutput)||!/^# cancelled 0$/m.test(nodeOutput))throw Error('Node cases were not completely executed');
if(JSON.stringify(inventory(root))!==JSON.stringify(inputs))throw Error('Gate source changed during the checks');  // the chain ran beside the copies
const reports=results.map(r=>{const matches=[...r.out.matchAll(/^BOOKS_PYTHON_BATCH_RESULT (.+)$/gm)];if(matches.length!==1)throw Error('Python batch completion missing or duplicated');return JSON.parse(matches[0][1]);});
const pythonCount=validatePythonReports(patterns,batches,reports).count;
// What each module really took in its worker, under the gate's own load (each test's time since the one before, so class
// setups count): the data the weights in python-check-batches.mjs are made from (2026-10-26, a worker at 96 % of its deadline).
for(const report of reports)console.log('Python worker '+report.batch+' module seconds: '+JSON.stringify(report.module_seconds||{}));
console.log('Integrated Python cases: '+pythonCount);
// Senua's v0.21.2 E1: the pass line names the QA runtime the gate really used (its folder and the digest of every file in
// it, python/ and ffmpeg/, beyond the three pinned executables) and the private MP3 fixture, so a receipt cannot name one
// runtime while the gate ran another.
const {manifestOf,treeDigest}=await import('./qa-entry-context.mjs');  // loaded only here: the source guard runs first
const usedRuntime=runtimeRoot || path.dirname(path.dirname(python)),fixtureFile=process.env.BOOKS_MP3_REAL_FIXTURE || '';
const qaRuntime={root:usedRuntime,sha256:treeDigest(await manifestOf(usedRuntime))};
// Senua's 0.22.1 review, W10: the whole runtime tree is pinned, not only its three executables.
if(!fixture.tree||qaRuntime.sha256!==fixture.tree.sha256)throw Error('QA runtime refused: its files differ from the runtime tree in scripts/qa-runtime.json ('+qaRuntime.sha256+')');
const mp3Fixture={path:fixtureFile,sha256:fixtureFile?createHash('sha256').update(fs.readFileSync(fixtureFile)).digest('hex'):''};
console.log('BOOKS_INTEGRATED_CHECKS_PASS '+JSON.stringify({python_cases:pythonCount,node_cases:nodeCount,frontend_scripts:frontendScripts,syntax_files:syntaxFiles.length,python_worker_seconds:workerSeconds.real,qa_runtime:qaRuntime,mp3_fixture:mp3Fixture}));

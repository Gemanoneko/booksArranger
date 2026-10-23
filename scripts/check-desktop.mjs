#!/usr/bin/env node
// Pure-node handoff graph; the outer protocol-2 supervisor owns its descendants.
// No GUI launch, installer execution, live catalog or source-library access.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {spawnSync,spawn} from 'node:child_process';import {fileURLToPath} from 'node:url';
import {pythonBatches,validatePythonReports,pythonWorkerLayout} from './python-check-batches.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
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
function run(exe,args){const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',windowsHide:true,timeout:Math.max(1,deadline-Date.now()),maxBuffer:16*1024*1024,env:{...process.env,PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:'',BOOKS_QA_RUN_ROOT:root,BOOKS_QA_FIXTURE_ROOT:path.join(root,'scratch','f'),PATH:fixture.ffmpeg.root+path.delimiter+(process.env.PATH||'')}});process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');if(r.error||r.status!==0)throw Error(r.error?.message||'Focused desktop check failed');return r.stdout;}
for(const name of ['desktop/main.js','desktop/preload.js','desktop/update-controller.js','desktop/engine-update.js','desktop/launch-options.js','desktop/status-flight.js','desktop/quit-watch.js','web/desktop-ui.js'])run(process.execPath,['--check',name]);
const nodeOutput=run(process.execPath,['--test','--test-reporter=tap','tests/release-contract.test.mjs','tests/release-flow.test.mjs','tests/update-controller.test.mjs','tests/engine-update.test.mjs','tests/launch-options.test.mjs','tests/release-leased-executables.test.mjs','tests/status-flight.test.mjs','tests/quit-watch.test.mjs','tests/python-check-batches.test.mjs']);
const nodeCount=Number(/^# tests (\d+)$/m.exec(nodeOutput)?.[1]);
if(!nodeCount||!/^# fail 0$/m.test(nodeOutput)||!/^# skipped 0$/m.test(nodeOutput)||!/^# cancelled 0$/m.test(nodeOutput))throw Error('Node cases were not completely executed');
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
const code=`import sys,unittest,json,pathlib
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
r=unittest.TextTestRunner(verbosity=2).run(s)
report={'batch':int(sys.argv[4]),'patterns':patterns,'ids':inventory,'discovered':len(inventory),'completed':r.testsRun,'skipped':len(r.skipped),'failures':len(r.failures),'errors':len(r.errors),'success':r.wasSuccessful()}
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
 const env={...process.env,PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:'',BOOKS_QA_RUN_ROOT:worker.directory,BOOKS_QA_FIXTURE_ROOT:path.join(worker.directory,'scratch','f'),TEMP:worker.temp,TMP:worker.temp,PATH:fixture.ffmpeg.root+path.delimiter+(process.env.PATH||'')};
 for(const key of Object.keys(env))if(/^GIT_(DIR|WORK_TREE|INDEX_FILE|COMMON_DIR)$/i.test(key))delete env[key];
 const out=[],err=[];let error=null,timedOut=false;
 const child=spawn(python,['-I','-B','-c',code,worker.directory,JSON.stringify(worker.batch),JSON.stringify(fixtureRootMap),String(worker.i)],{cwd:worker.directory,env,windowsHide:true,stdio:['ignore','pipe','pipe']});
 const timer=setTimeout(()=>{timedOut=true;child.kill();},Math.max(1,deadline-Date.now()));
 const capture=chunks=>data=>{outputBytes+=data.length;if(outputBytes>16*1024*1024){overflow=true;child.kill();return;}chunks.push(data);};
 child.stdout.on('data',capture(out));child.stderr.on('data',capture(err));child.on('error',e=>{error=e.message;});
 child.on('close',status=>{clearTimeout(timer);resolve({status,error,timedOut,out:Buffer.concat(out).toString('utf8'),err:Buffer.concat(err).toString('utf8')});});
})));
// Never return on one worker's failure while the others are still running.
for(let i=0;i<results.length;i++){process.stdout.write(results[i].out);process.stderr.write(results[i].err);}
for(const worker of workers)if(JSON.stringify(inventory(worker.directory))!==JSON.stringify(inputs))throw Error('Python batch source changed during tests');
if(overflow||results.some(r=>r.error||r.timedOut||r.status!==0))throw Error('Python batch failed, exceeded output cap or original deadline');
const reports=results.map(r=>{const matches=[...r.out.matchAll(/^BOOKS_PYTHON_BATCH_RESULT (.+)$/gm)];if(matches.length!==1)throw Error('Python batch completion missing or duplicated');return JSON.parse(matches[0][1]);});
const pythonCount=validatePythonReports(patterns,batches,reports).count;
console.log('Integrated Python cases: '+pythonCount);
const frontendScripts=fs.readdirSync(path.join(root,'tests')).filter(name=>/^test_.*\.js$/.test(name)).sort();
for(const name of frontendScripts)run(process.execPath,[path.join('tests',name)]);
console.log('BOOKS_INTEGRATED_CHECKS_PASS '+JSON.stringify({python_cases:pythonCount,node_cases:nodeCount,frontend_scripts:frontendScripts,syntax_files:8}));

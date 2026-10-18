#!/usr/bin/env node
// Pure-node handoff graph; the outer protocol-2 supervisor owns its descendants.
// No GUI launch, installer execution, live catalog or source-library access.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const fixture=JSON.parse(fs.readFileSync(path.join(root,'scripts/qa-runtime.json'),'utf8'));
const python=fixture.python.path,sha=fixture.python.sha256;
for(const [name,expected] of Object.entries(fixture.ffmpeg.files)){const file=path.join(fixture.ffmpeg.root,name),stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.size!==expected.size||createHash('sha256').update(fs.readFileSync(file)).digest('hex')!==expected.sha256)throw Error('Bundled QA media runtime differs');}
if(createHash('sha256').update(fs.readFileSync(python)).digest('hex')!==sha)throw Error('QA Python runtime differs');
fs.mkdirSync(path.join(root,'scratch','source-fallback-2026-10-11'),{recursive:true});
const deadline=Date.now()+540000;
function run(exe,args){const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',windowsHide:true,timeout:Math.max(1,deadline-Date.now()),maxBuffer:16*1024*1024,env:{...process.env,PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:'',PATH:fixture.ffmpeg.root+path.delimiter+(process.env.PATH||'')}});process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');if(r.error||r.status!==0)throw Error(r.error?.message||'Focused desktop check failed');return r.stdout;}
for(const name of ['desktop/main.js','desktop/preload.js','desktop/update-controller.js','desktop/engine-update.js','desktop/launch-options.js','desktop/status-flight.js','desktop/quit-watch.js','web/desktop-ui.js'])run(process.execPath,['--check',name]);
const nodeOutput=run(process.execPath,['--test','--test-reporter=tap','tests/release-contract.test.mjs','tests/release-flow.test.mjs','tests/update-controller.test.mjs','tests/engine-update.test.mjs','tests/launch-options.test.mjs','tests/release-leased-executables.test.mjs','tests/status-flight.test.mjs','tests/quit-watch.test.mjs']);
const nodeCount=Number(/^# tests (\d+)$/m.exec(nodeOutput)?.[1]);
if(!nodeCount||!/^# fail 0$/m.test(nodeOutput)||!/^# skipped 0$/m.test(nodeOutput)||!/^# cancelled 0$/m.test(nodeOutput))throw Error('Node cases were not completely executed');
// Extend the original desktop/media graph with every integrated maintenance and
// automatic/status boundary. Report discovery rather than a stale literal count.
const patterns=['test_desktop_quit.py','test_desktop_catalog.py','test_desktop_host.py','test_build_guard.py','test_working_cleanup.py','test_working_precision.py','test_working_lifecycle.py','test_storage_cleanup.py','test_automatic_media_policy.py','test_automatic_media.py','test_standing_admission.py','test_attempt_working_lifecycle.py','test_published_snapshot_lifecycle.py','test_attention_failure_policy.py','test_automatic_record_retry.py','test_web.py','test_sqlite_busy.py','test_automatic_processing.py','test_status_read_contention.py'];
patterns.push('test_desktop_owner_recovery.py','test_failed_m4b_retry.py');
patterns.push('test_m4b_preservation.py','test_m4b_dispatch.py');
patterns.push('test_zone_identifier.py');
patterns.push('test_status_snapshot.py');
patterns.push('test_startup_published_check.py');
patterns.push('test_replacement_jobs.py');
patterns.push('test_cleanup_resume.py','test_blocked_retry.py');
patterns.push('test_progress_rows.py','test_progress.py');
patterns.push('test_attention_actions.py','test_review_backend.py','test_attention_repair.py','test_quiet_status.py','test_status_under_load.py','test_backup_rule.py');
patterns.push('test_recovery_retention.py');  // the recovery-purge module's own suite (Senua v0.16.8 F3)
const code="import sys,unittest,json;sys.path.insert(0,sys.argv[1]);loader=unittest.defaultTestLoader;s=unittest.TestSuite();[s.addTests(loader.discover(sys.argv[1]+'/tests',pattern=p)) for p in json.loads(sys.argv[2])];print('Integrated Python cases:',s.countTestCases(),flush=True);r=unittest.TextTestRunner(verbosity=2).run(s);sys.exit(not r.wasSuccessful() or bool(r.skipped))";
const pythonOutput=run(python,['-I','-B','-c',code,root,JSON.stringify(patterns)]);
const pythonCount=Number(/^Integrated Python cases: (\d+)$/m.exec(pythonOutput)?.[1]);
if(!pythonCount)throw Error('Python discovery result missing');
const frontendScripts=fs.readdirSync(path.join(root,'tests')).filter(name=>/^test_.*\.js$/.test(name)).sort();
for(const name of frontendScripts)run(process.execPath,[path.join('tests',name)]);
console.log('BOOKS_INTEGRATED_CHECKS_PASS '+JSON.stringify({python_cases:pythonCount,node_cases:nodeCount,frontend_scripts:frontendScripts,syntax_files:7}));

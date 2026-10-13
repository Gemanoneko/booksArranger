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
function run(exe,args){const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',windowsHide:true,timeout:Math.max(1,deadline-Date.now()),maxBuffer:16*1024*1024,env:{...process.env,PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:'',PATH:fixture.ffmpeg.root+path.delimiter+(process.env.PATH||'')}});process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');if(r.error||r.status!==0)throw Error(r.error?.message||'Focused desktop check failed');}
for(const name of ['desktop/main.js','desktop/preload.js','desktop/update-controller.js','desktop/engine-update.js','desktop/launch-options.js','web/desktop-ui.js'])run(process.execPath,['--check',name]);
run(process.execPath,['--test','tests/release-contract.test.mjs','tests/release-flow.test.mjs','tests/update-controller.test.mjs','tests/engine-update.test.mjs','tests/launch-options.test.mjs','tests/release-leased-executables.test.mjs']);
const code="import sys,unittest;sys.path.insert(0,sys.argv[1]);loader=unittest.defaultTestLoader;s=unittest.TestSuite();[s.addTests(loader.discover(sys.argv[1]+'/tests',pattern=p)) for p in ['test_desktop_quit.py','test_desktop_catalog.py','test_desktop_host.py','test_build_guard.py','test_working_cleanup.py','test_working_precision.py','test_working_lifecycle.py','test_storage_cleanup.py','test_automatic_media_policy.py','test_automatic_media.py','test_standing_admission.py']];print('Focused Python cases:',s.countTestCases());assert s.countTestCases()==137;r=unittest.TextTestRunner(verbosity=2).run(s);sys.exit(not r.wasSuccessful() or bool(r.skipped))";
run(python,['-I','-B','-c',code,root]);

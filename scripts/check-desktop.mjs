#!/usr/bin/env node
// Pure-node handoff graph; the outer protocol-2 supervisor owns its descendants.
// No GUI launch, installer execution, live catalog or source-library access.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const python='C:/Python314/python.exe';const sha='434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f';
if(createHash('sha256').update(fs.readFileSync(python)).digest('hex')!==sha)throw Error('QA Python runtime differs');
const deadline=Date.now()+540000;
function run(exe,args){const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',windowsHide:true,timeout:Math.max(1,deadline-Date.now()),maxBuffer:16*1024*1024,env:{...process.env,PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:''}});process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');if(r.error||r.status!==0)throw Error(r.error?.message||'Focused desktop check failed');}
for(const name of ['desktop/main.js','desktop/preload.js','desktop/update-controller.js','web/desktop-ui.js'])run(process.execPath,['--check',name]);
run(process.execPath,['--test','tests/release-contract.test.mjs','tests/release-flow.test.mjs','tests/update-controller.test.mjs','tests/release-leased-executables.test.mjs']);
const code="import sys,unittest;sys.path.insert(0,sys.argv[1]);loader=unittest.defaultTestLoader;s=unittest.TestSuite();[s.addTests(loader.discover(sys.argv[1]+'/tests',pattern=p)) for p in ['test_desktop_quit.py','test_desktop_catalog.py','test_desktop_host.py','test_build_guard.py']];print('Focused Python cases:',s.countTestCases());r=unittest.TextTestRunner(verbosity=2).run(s);sys.exit(not r.wasSuccessful())";
run(python,['-I','-B','-c',code,root]);

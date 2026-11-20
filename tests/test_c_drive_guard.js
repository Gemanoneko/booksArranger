'use strict';
// The desktop check's C: guard (Sergei 2026-11-19: nothing we run may write to C:). Pure checks on private folders in this
// checkout's scratch: no C: folder is written here. The deliberate C: write that proves the guard on the real drive is
// a separate demonstration (Docs, 0.30.0 decision log), not part of every run.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const repo=path.join(__dirname,'..');
const scratch=path.resolve(process.env.BOOKS_QA_FIXTURE_ROOT||path.join(repo,'scratch'));fs.mkdirSync(scratch,{recursive:true});
const root=fs.mkdtempSync(path.join(scratch,'c-drive-guard-'));
(async()=>{
 try{
  const guard=await import('../scripts/c-drive-guard.mjs');
  const anyDir=path.join(root,'drive-root'),temp=path.join(root,'user-temp'),missing=path.join(root,'never-made'),file=path.join(root,'not-a-folder');
  for(const dir of [anyDir,temp])fs.mkdirSync(dir);
  fs.writeFileSync(file,'x');
  fs.mkdirSync(path.join(anyDir,'Windows'));fs.mkdirSync(path.join(anyDir,'BA-left-from-before'));fs.writeFileSync(path.join(temp,'tmpold_1234'),'x');
  const places=[{dir:anyDir,mode:'any',label:'the C: drive root'},{dir:temp,mode:'ours',label:'the real user Temp folder'},{dir:missing,mode:'any',label:'a folder made during the run'},{dir:file,mode:'any',label:'an unreadable place'}];

  // 1. Nothing new: no violation; a place that cannot be listed is reported as not checked, never as a pass or a failure.
  let run=guard.startCDriveGuard({places,exceptions:[]});
  let result=run.finish();
  assert.deepEqual(result.violations,[]);
  assert.equal(result.error,null);
  assert.deepEqual(result.notChecked.map(n=>n.dir),[file]);

  // 2. Positive control: a new folder in the drive root, a new test-named entry in Temp and a new folder inside a place
  // that did not exist at the start each fail the run, and the message names every path.
  run=guard.startCDriveGuard({places,exceptions:[]});
  fs.mkdirSync(path.join(anyDir,'BASF-c057a522e3'));
  fs.mkdirSync(path.join(temp,'books-main-AbC123'));
  fs.writeFileSync(path.join(temp,'tmpk3_9xq0a'),'x');
  fs.mkdirSync(path.join(missing,'leak'),{recursive:true});
  // Not ours: another program's Temp entry is not this run's write; removing something old is not a write either.
  fs.writeFileSync(path.join(temp,'SomeOtherApp-2026.log'),'x');fs.writeFileSync(path.join(temp,'tmp1A2B.tmp'),'x');
  fs.rmdirSync(path.join(anyDir,'BA-left-from-before'));
  result=run.finish();
  const named=result.violations.map(v=>v.path).sort();
  assert.deepEqual(named,[path.join(anyDir,'BASF-c057a522e3'),path.join(missing),path.join(temp,'books-main-AbC123')].sort());
  assert.ok(result.error,'the guard fails the run');
  for(const p of named)assert.ok(result.error.includes(p),'the failure names '+p);
  assert.ok(result.lines.some(line=>line.includes('the C: drive root')));
  // Python's default temporary name (tmp + 8): any program's Python makes these (two empty ones from another program
  // appeared in the real Temp within 6 minutes on 2026-11-19), so it is named in a note but never fails the run.
  assert.deepEqual(result.notes.map(n=>n.path),[path.join(temp,'tmpk3_9xq0a')]);
  assert.ok(result.lines.some(line=>line.includes('note: new in the real user Temp folder, not counted: '+path.join(temp,'tmpk3_9xq0a'))),result.lines.join('\n'));
  assert.ok(!result.error.includes('tmpk3_9xq0a'));

  // 3. Removing the write makes the next run pass (the same guard, nothing else changed).
  fs.rmSync(path.join(anyDir,'BASF-c057a522e3'),{recursive:true});fs.rmSync(path.join(temp,'books-main-AbC123'),{recursive:true});fs.rmSync(path.join(temp,'tmpk3_9xq0a'));fs.rmSync(missing,{recursive:true});
  run=guard.startCDriveGuard({places,exceptions:[]});
  assert.deepEqual(run.finish().violations,[]);

  // 4. An allowed exception covers exactly its own path: a sibling still fails.
  const allowed=path.join(anyDir,'Allowed-For-A-Reason');
  run=guard.startCDriveGuard({places,exceptions:[{path:allowed,reason:'fixture reason'}]});
  fs.mkdirSync(allowed);fs.mkdirSync(allowed+'-sibling');
  result=run.finish();
  assert.deepEqual(result.violations.map(v=>v.path),[allowed+'-sibling']);
  assert.deepEqual(result.allowed.map(a=>a.path),[allowed]);
  fs.rmdirSync(allowed);fs.rmdirSync(allowed+'-sibling');

  // 4b. Senua 0.30.0 m5: a write INSIDE a folder that was already there. Folders and files whose names only Books Arranger
  // uses (Books Arranger, books-*, BA-*, BASF-*, codex-books-*) are walked at the start and the end: a new entry at any depth,
  // or a file whose size or time changed, fails the run and is named. Another program's folder is still read only by its
  // name at the top, so its own work inside it never fails a run (and a write of ours there is not seen).
  const own=path.join(anyDir,'Books Arranger'),record=path.join(anyDir,'books-arranger-installation.json'),otherApp=path.join(anyDir,'SomeOtherApp');
  fs.mkdirSync(path.join(own,'Local Storage','leveldb'),{recursive:true});fs.writeFileSync(path.join(own,'desktop-settings.json'),'{}');
  fs.writeFileSync(record,'{"a":1}');fs.mkdirSync(otherApp);
  run=guard.startCDriveGuard({places,exceptions:[]});
  fs.writeFileSync(path.join(own,'Local Storage','leveldb','leak.log'),'x');
  fs.writeFileSync(path.join(own,'desktop-settings.json'),'{"dataDir":"C:\\\\x"}');
  fs.writeFileSync(record,'{"a":22}');
  fs.writeFileSync(path.join(otherApp,'its-own-log.txt'),'x');
  result=run.finish();
  assert.deepEqual(result.violations.map(v=>v.path).sort(),[path.join(own,'Local Storage','leveldb','leak.log'),path.join(own,'desktop-settings.json'),record].sort());
  assert.ok(result.lines.some(l=>l.includes('NEW on C: during this run: '+path.join(own,'Local Storage','leveldb','leak.log'))),result.lines.join('\n'));
  assert.ok(result.lines.some(l=>l.includes('CHANGED on C: during this run: '+path.join(own,'desktop-settings.json'))),result.lines.join('\n'));
  assert.ok(result.error.includes(record));
  // The write removed (the changed files stay as they now are): the next run passes.
  fs.rmSync(path.join(own,'Local Storage','leveldb','leak.log'));
  run=guard.startCDriveGuard({places,exceptions:[]});
  assert.deepEqual(run.finish().violations,[]);
  // Bounded: a folder of ours over the entry limit is reported as partly checked, never failed on what was not read.
  run=guard.startCDriveGuard({places,exceptions:[],limits:{entries:2,depth:8}});
  fs.writeFileSync(path.join(own,'late.txt'),'x');
  result=run.finish();
  assert.deepEqual(result.violations,[]);
  assert.ok(result.notChecked.some(n=>n.dir===own&&/over 2 entries/.test(n.why)),JSON.stringify(result.notChecked));
  fs.rmSync(path.join(own,'late.txt'));fs.rmSync(otherApp,{recursive:true});fs.rmSync(own,{recursive:true});fs.rmSync(record);

  // 5. The committed exception list: each entry is absolute, on C:, has a reason, and none is a whole folder the guard watches.
  const defaults=guard.cDrivePlaces();
  for(const e of guard.C_DRIVE_EXCEPTIONS){
   assert.ok(path.win32.isAbsolute(e.path)&&/^c:/i.test(e.path)&&typeof e.reason==='string'&&e.reason.length>10,'exception '+JSON.stringify(e));
   assert.ok(!defaults.some(p=>p.dir.toLowerCase()===e.path.toLowerCase()),'an exception never allows a whole watched folder');
  }

  // 6. The default places: the C: root (anything new) and the real user Temp (our names), from the real profile, never
  // from TEMP (the check points TEMP at its own scratch).
  const home=require('node:os').userInfo().homedir;
  assert.ok(defaults.some(p=>p.dir.toLowerCase()==='c:\\'&&p.mode==='any'));
  assert.ok(defaults.some(p=>p.dir.toLowerCase()===path.win32.join(home,'AppData','Local','Temp').toLowerCase()&&p.mode==='ours'));
  // Where the installer keeps its records (books-arranger-installation.json and the others beside it): our names there.
  assert.ok(defaults.some(p=>p.dir.toLowerCase()===path.win32.join(home,'AppData','Local','Programs').toLowerCase()&&p.mode==='ours'));
  for(const p of defaults)assert.ok(/^c:\\/i.test(p.dir)&&p.label,'place '+JSON.stringify(p));

  // 7. Every temporary name prefix our tests and engine use is recognised in Temp, as Python (8 characters) and Node
  // (6 characters) make them, so a new prefix cannot slip past the guard unnoticed.
  const prefixes=new Set();
  const sources=[...fs.readdirSync(path.join(repo,'tests')).map(n=>path.join(repo,'tests',n)),...fs.readdirSync(repo).map(n=>path.join(repo,n)),...fs.readdirSync(path.join(repo,'scripts')).map(n=>path.join(repo,'scripts',n))]
   .filter(p=>/\.(py|js|mjs)$/.test(p)&&fs.statSync(p).isFile());
  for(const file of sources){
   const text=fs.readFileSync(file,'utf8');
   for(const m of text.matchAll(/(?:mkdtemp|mkstemp|TemporaryDirectory|NamedTemporaryFile|TemporaryFile)\([^)]*?prefix\s*=\s*(['"])([^'"{}%]*)\1/g))if(m[2])prefixes.add(m[2]);
   for(const m of text.matchAll(/mkdtemp(?:Sync)?\(\s*path\.join\(\s*[\w.]+(?:\(\))?\s*,\s*(['"])([\w.-]+)\1\s*\)/g))prefixes.add(m[2]);
  }
  assert.ok(prefixes.size>=40,'the scan found the prefixes ('+prefixes.size+')');
  for(const prefix of prefixes){
   assert.ok(guard.isOurTempName(prefix+'k3_9xq0a'),'Python-made name with prefix '+JSON.stringify(prefix));
   assert.ok(guard.isOurTempName(prefix+'AbC123'),'Node-made name with prefix '+JSON.stringify(prefix));
  }
  for(const name of ['codex-books-2026-10-20','BA-Portable-0287-x','BASF-c057a522e3','books-main-OitQOh'])assert.ok(guard.isOurTempName(name),name);
  assert.ok(!guard.isOurTempName('tmpk3_9xq0a')&&guard.isPythonDefaultTempName('tmpk3_9xq0a')&&!guard.isPythonDefaultTempName('tmp1A2B.tmp'));
  // etilqs_* is SQLite's temporary file for ANY program (one from another program sat in the real Temp on 2026-11-19), so
  // it is not ours: counting it would fail a run on another program's work.
  for(const name of ['tmp1A2B.tmp','codex-clipboard-0e8f.png','claude','node-compile-cache','python-languageserver-cancellation','SomeOtherApp-2026.log','etilqs_4f2a9c'])assert.ok(!guard.isOurTempName(name),name);

  // 8. The desktop check wires it: its side chain gets a private TEMP, and the guard spans the whole run.
  const check=fs.readFileSync(path.join(repo,'scripts','check-desktop.mjs'),'utf8');
  assert.ok(/import \{startCDriveGuard,cDriveEnvRefusal\} from '\.\/c-drive-guard\.mjs'/.test(check),'check-desktop imports the guard');
  const started=check.indexOf('startCDriveGuard('),preflight=check.indexOf('test_registry_rename_containment.py'),finished=check.indexOf('cDrive.finish()');
  assert.ok(started>0&&started<preflight&&finished>preflight,'the guard starts before the first child and finishes after the last');
  assert.ok(/sideEnv=\{[^\n]*TEMP:sideTemp,TMP:sideTemp,TMPDIR:sideTemp/.test(check),'the side chain gets the check\'s own TEMP');

  // 9. A BOOKS_* fixture root on C: is refused before anything runs (C:\BASF-* came from BOOKS_OPERATOR_C_ROOT); inputs the
  // checks only read, and a checkout that itself lives on C: (the laptop's approved root), are not.
  const refusal=guard.cDriveEnvRefusal({BOOKS_RELOCATION_FIXTURE_SOURCE:'C:\\BA-fixture',BOOKS_QA_RUNTIME_ROOT:'C:\\runtime',BOOKS_QA_FIXTURE_ROOT:'I:\\f',TEMP:'C:\\Temp'},'I:\\AI Projects\\checkout');
  assert.ok(refusal&&refusal.includes('BOOKS_RELOCATION_FIXTURE_SOURCE=C:\\BA-fixture')&&!refusal.includes('BOOKS_QA_RUNTIME_ROOT')&&!refusal.includes('TEMP='),refusal);
  for(const [approved,outside] of [['I:/AI Projects','I:/x'],['C:/Antigravity Projects','C:/x']]){
   const checkout=approved+'/checkout';
   for(const escaped of [outside,approved+'-old/x',approved+'/../escape','../escape','C:relative','//server/share/output']){
    assert.match(guard.cDriveEnvRefusal({BOOKS_QA_FIXTURE_ROOT:escaped},checkout,approved),/BOOKS_QA_FIXTURE_ROOT/);
   }
   assert.equal(guard.cDriveEnvRefusal({BOOKS_QA_FIXTURE_ROOT:checkout+'/scratch',BOOKS_MP3_REAL_FIXTURE:'C:/input.mp3'},checkout,approved),null);
  }
  // The real check script, copied into a private root on I:, refuses with that message, exit 1, and makes nothing.
  const gate=path.join(root,'gate');fs.mkdirSync(path.join(gate,'scripts'),{recursive:true});
  for(const name of ['check-desktop.mjs','python-check-batches.mjs','gate-source-guard.mjs','gate-scratch.mjs','qa-phase-contract.mjs','c-drive-guard.mjs'])fs.copyFileSync(path.join(repo,'scripts',name),path.join(gate,'scripts',name));
  if(!/^c:/i.test(gate)){
   const never='C:\\BA-guard-never-made-'+process.pid;
   const run=require('node:child_process').spawnSync(process.execPath,[path.join(gate,'scripts','check-desktop.mjs')],{cwd:gate,encoding:'utf8',windowsHide:true,timeout:60000,env:{...process.env,BOOKS_OPERATOR_C_ROOT:never}});
   assert.equal(run.status,1,run.stderr);
   assert.match(run.stderr,/^Refusing to run the checks: .*BOOKS_OPERATOR_C_ROOT=C:\\BA-guard-never-made-\d+ .*inside I:\/AI Projects/m);
   assert.ok(!fs.existsSync(never),'nothing made on C:');
   assert.deepEqual(fs.readdirSync(gate),['scripts'],'refused before any scratch was made');
  }
  console.log('C: guard: new C: entries fail the run and are named, our Temp names, exact exceptions, C: fixture roots refused, the wiring');
 }finally{
  assert.ok(root.startsWith(scratch+path.sep));fs.rmSync(root,{recursive:true,force:true});
 }
})().catch(error=>{console.error(error);process.exitCode=1;});

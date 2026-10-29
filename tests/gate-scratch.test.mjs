// The gate removes the scratch it made (13 Python worker copies, its fallback folder) when it ends, pass or fail; a failure
// keeps only the copies it names as its evidence (2026-10-29: every gate run left scratch/0..12 behind, and the next run
// in the same folder refused at scratch/0). BOOKS_GATE_SCRIPT points the end-to-end cases at another copy of
// check-desktop.mjs (e.g. the committed one, as a negative control).
import test from 'node:test';import assert from 'node:assert/strict';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {spawn,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';import {fileURLToPath} from 'node:url';
import {trackGateScratch} from '../scripts/gate-scratch.mjs';
import {PYTHON_WORKERS} from '../scripts/python-check-batches.mjs';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const gateScript=process.env.BOOKS_GATE_SCRIPT?path.resolve(process.env.BOOKS_GATE_SCRIPT):path.join(repo,'scripts','check-desktop.mjs');
const IS_WIN=process.platform==='win32';
function sandbox(t){const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ba-gate-scratch-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));return dir;}
const put=(file,body='x')=>{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,body);};
const workerNames=Array.from({length:PYTHON_WORKERS},(_,i)=>String(i));

// A gate run's scratch, as check-desktop.mjs makes it: the fallback folder, then one source copy per worker.
function makeRun(root){
 const s=trackGateScratch(root);
 fs.mkdirSync(s.claim('scratch/source-fallback-2026-10-11'),{recursive:true});s.claim('scratch/f');
 for(const name of workerNames){const dir=s.claim('scratch/'+name);fs.mkdirSync(dir);put(path.join(dir,'app.py'),'copy');put(path.join(dir,'scratch','tmp','t.txt'));put(path.join(dir,'scratch','f','fixture.m4b'));}
 return s;
}

test('a passing run removes every entry it made and nothing that was there before',t=>{
 const root=sandbox(t);
 put(path.join(root,'scratch','source-fallback-2026-10-11','proof.json'),'retained proof');  // retained before the run
 put(path.join(root,'scratch','earlier','note.txt'),'not the gate\'s');
 const s=makeRun(root);s.evidence('scratch/4','marked, but the run passed');
 put(path.join(root,'scratch','f','side.txt'));  // the side chain's fixture root, made during the run
 const r=s.finish(false);
 assert.deepEqual(r.removed.sort(),[...workerNames,'f'].sort());assert.deepEqual(r.kept,[]);assert.deepEqual(r.left,[]);
 assert.deepEqual(fs.readdirSync(path.join(root,'scratch')).sort(),['earlier','source-fallback-2026-10-11']);
 assert.equal(fs.readFileSync(path.join(root,'scratch','source-fallback-2026-10-11','proof.json'),'utf8'),'retained proof');
 assert.match(r.lines[0],/^Gate scratch removed: .*scratch\/0, .*scratch\/12/);
});

test('a failing run keeps only the copies it names as evidence, and says so',t=>{
 const root=sandbox(t);const s=makeRun(root);
 s.evidence('scratch/3','its source copy changed during the tests');
 const r=s.finish(true);
 assert.deepEqual(fs.readdirSync(path.join(root,'scratch')),['3']);
 assert.ok(fs.existsSync(path.join(root,'scratch','3','scratch','f','fixture.m4b')),'the evidence is kept whole');
 assert.deepEqual(r.kept,[{name:'3',evidence:'its source copy changed during the tests'}]);
 assert.ok(r.lines.some(l=>l.includes('kept as the evidence this failure names: '+path.join(root,'scratch','3')+' (its source copy changed during the tests)')),r.lines.join('\n'));
 // A later run never claims what an earlier run kept: it stays until its owner deletes it.
 const later=trackGateScratch(root);later.claim('scratch/3');
 assert.deepEqual(later.finish(false).removed,[]);assert.ok(fs.existsSync(path.join(root,'scratch','3','app.py')));
});

test('a scratch folder the run made goes too, once empty; links inside are unlinked, never followed',t=>{
 const root=sandbox(t),outside=path.join(sandbox(t),'outside');put(path.join(outside,'precious.txt'),'keep me');
 const s=makeRun(root);
 fs.symlinkSync(outside,path.join(root,'scratch','5','scratch','f','jn'),IS_WIN?'junction':'dir');
 const r=s.finish(false);
 assert.equal(r.removedDir,true);assert.ok(!fs.existsSync(path.join(root,'scratch')));
 assert.equal(fs.readFileSync(path.join(outside,'precious.txt'),'utf8'),'keep me','the junction target is untouched');
});

test('an entry still in use is reported, not hidden',{skip:!IS_WIN&&'needs a Windows image lock'},async t=>{
 const root=sandbox(t);const s=makeRun(root);
 const exe=path.join(root,'scratch','7','held.exe');fs.copyFileSync(path.join(process.env.SystemRoot||'C:\\Windows','System32','PING.EXE'),exe);
 const held=spawn(exe,['-n','60','127.0.0.1'],{stdio:'ignore',windowsHide:true});
 try{
  await new Promise(r=>setTimeout(r,300));
  const r=s.finish(false);
  assert.deepEqual(r.left.map(x=>x.name),['7']);assert.ok(r.lines.some(l=>l.startsWith('Gate scratch NOT removed: '+path.join(root,'scratch','7'))),r.lines.join('\n'));
 }finally{const gone=new Promise(r=>held.once('exit',r));held.kill();await gone;}
});

// The real gate in a throwaway root. Its "Python" is this Node (hash-pinned the same way), so every worker starts and fails
// at once: a failing run after all 13 worker copies were made, with no QA runtime needed.
function gateRoot(t,{preexisting}={}){
 const box=sandbox(t),root=path.join(box,'root'),ff=path.join(box,'ff');
 fs.mkdirSync(path.join(root,'scripts'),{recursive:true});fs.mkdirSync(ff);
 fs.copyFileSync(gateScript,path.join(root,'scripts','check-desktop.mjs'));
 for(const name of ['python-check-batches.mjs','gate-source-guard.mjs','gate-scratch.mjs'])fs.copyFileSync(path.join(repo,'scripts',name),path.join(root,'scripts',name));
 const sha=createHash('sha256').update(fs.readFileSync(process.execPath)).digest('hex');
 fs.writeFileSync(path.join(root,'scripts','qa-runtime.json'),JSON.stringify({schema:1,python:{path:process.execPath,sha256:sha},ffmpeg:{root:ff,files:{}}}));
 put(path.join(root,'tests','README.txt'),'placeholder');
 if(preexisting)put(path.join(root,'scratch','kept-proof','proof.json'),'retained');
 return root;
}
function runGate(root){
 const env={...process.env};delete env.BOOKS_QA_RUNTIME_ROOT;delete env.BOOKS_MP3_REAL_FIXTURE;
 return spawnSync(process.execPath,[path.join(root,'scripts','check-desktop.mjs')],{cwd:root,encoding:'utf8',windowsHide:true,timeout:120000,env});
}

test('the real gate removes its worker copies and the scratch folder it made when it fails',t=>{
 const root=gateRoot(t),run=runGate(root);
 assert.equal(run.status,1,run.stderr);
 assert.match(run.stdout,new RegExp('Sources copied into the '+PYTHON_WORKERS+' Python workers'),'the workers were made');
 assert.match(run.stderr,/Python batch failed or exceeded output cap/,'the original failure is still the gate\'s error');
 assert.match(run.stderr,/Gate scratch removed: .*scratch\/0, .*scratch\/12/);
 assert.deepEqual(fs.readdirSync(root).sort(),['scripts','tests'],'no scratch left behind');
});

test('the real gate leaves what was in scratch before it ran',t=>{
 const root=gateRoot(t,{preexisting:true}),run=runGate(root);
 assert.equal(run.status,1,run.stderr);
 assert.deepEqual(fs.readdirSync(path.join(root,'scratch')),['kept-proof']);
 assert.equal(fs.readFileSync(path.join(root,'scratch','kept-proof','proof.json'),'utf8'),'retained');
});

test('a passing gate cleans up before it prints its pass line',()=>{
 const source=fs.readFileSync(gateScript,'utf8');
 const begin=source.search(/^try\{\r?\nfs\.mkdirSync\(gateScratch\.claim\(/m),inputs=source.indexOf('const inputs=inventory(root)'),finish=source.indexOf('gateScratch.finish('),pass=source.indexOf('console.log(passLine);');
 assert.ok(begin>0&&inputs>begin,'every worker copy is made inside the guarded block');
 assert.ok(finish>inputs&&pass>finish,'the cleanup runs on every path, and the pass line is printed after it');
 assert.ok(source.includes('if(gateError)throw gateError;'),'a failure keeps its own error and exit code');
});

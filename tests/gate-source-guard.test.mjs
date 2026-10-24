// The gate refuses a source root that holds data/ (a live checkout) before it copies or writes anything
// (2026-10-24: a gate run in the main checkout copied the live catalog into its workers).
import test from 'node:test';import assert from 'node:assert/strict';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
import {liveCatalogRefusal} from '../scripts/gate-source-guard.mjs';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const catalogBytes=Buffer.from('SQLite format 3\0 stand-in for the live catalog');

function sandbox(t){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ba-gate-guard-'));
 t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 return dir;
}
// The real gate script and the modules it imports, in a throwaway root; nothing else (no qa-runtime.json), so a
// script that gets past the guard stops at its first runtime read instead of running anything.
function gateCopy(dir){
 fs.mkdirSync(path.join(dir,'scripts'));
 for(const name of ['check-desktop.mjs','python-check-batches.mjs','gate-source-guard.mjs'])fs.copyFileSync(path.join(repo,'scripts',name),path.join(dir,'scripts',name));
}
function runGate(dir){
 const env={...process.env};delete env.BOOKS_QA_RUNTIME_ROOT;
 return spawnSync(process.execPath,[path.join(dir,'scripts','check-desktop.mjs')],{cwd:dir,encoding:'utf8',windowsHide:true,timeout:60000,env});
}

test('a root without data/ is not refused',t=>{
 assert.equal(liveCatalogRefusal(sandbox(t)),null);
});

test('data/ in any form marks a live checkout',t=>{
 const withCatalog=sandbox(t);fs.mkdirSync(path.join(withCatalog,'data'));fs.writeFileSync(path.join(withCatalog,'data','inventory.sqlite3'),catalogBytes);
 const empty=sandbox(t);fs.mkdirSync(path.join(empty,'data'));
 const file=sandbox(t);fs.writeFileSync(path.join(file,'data'),'');
 for(const root of [withCatalog,empty,file]){
  const refusal=liveCatalogRefusal(root);
  assert.match(refusal,/^Refusing to run the gate: /);
  assert.ok(refusal.includes(path.join(root,'data')),refusal);
  assert.match(refusal,/separate worktree/);
 }
});

test('check-desktop.mjs refuses a live checkout before it copies or writes anything',t=>{
 const dir=sandbox(t);gateCopy(dir);
 fs.mkdirSync(path.join(dir,'data'));fs.writeFileSync(path.join(dir,'data','inventory.sqlite3'),catalogBytes);
 const run=runGate(dir);
 assert.equal(run.status,1,run.stderr);
 assert.match(run.stderr,/^Refusing to run the gate: .*data exists/m);
 assert.doesNotMatch(run.stderr,/ENOENT|qa-runtime/,'refused before reading the QA runtime');
 assert.deepEqual(fs.readdirSync(dir).sort(),['data','scripts'],'no scratch or worker folder was made');
 assert.deepEqual(fs.readdirSync(path.join(dir,'data')),['inventory.sqlite3']);
 assert.ok(fs.readFileSync(path.join(dir,'data','inventory.sqlite3')).equals(catalogBytes),'catalog bytes untouched');
});

test('positive control: without data/ the same copy gets past the guard',t=>{
 const dir=sandbox(t);gateCopy(dir);
 const run=runGate(dir);
 assert.notEqual(run.status,0,'a bare copy has no QA runtime and must still fail');
 assert.doesNotMatch(run.stderr,/Refusing to run the gate/);
 assert.match(run.stderr,/qa-runtime\.json/,'it stopped at the runtime read, after the guard');
});

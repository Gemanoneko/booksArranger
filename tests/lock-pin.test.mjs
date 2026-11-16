// The lockfile pin check that `npm run pack` runs before any guarded build work (2026-11-16; stale at 0.28.5 and 0.28.13).
// The pack cases run the real scripts/build-step.mjs from a throwaway root whose guarded-io.mjs is a stub that only reports
// it was reached: nothing native starts, and nothing outside the throwaway root is read or written.
import test from 'node:test';import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';import fs from 'node:fs';import path from 'node:path';import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {lockPinProblem} from '../scripts/lock-pin.mjs';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const REACHED='GUARDED BUILD REACHED';
function box(t){
 const parent=process.env.BOOKS_QA_FIXTURE_ROOT||path.join(repo,'scratch');fs.mkdirSync(parent,{recursive:true});
 const root=fs.mkdtempSync(path.join(parent,'lock-pin-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 fs.mkdirSync(path.join(root,'scripts'));
 for(const name of ['build-step.mjs','lock-pin.mjs'])fs.copyFileSync(path.join(repo,'scripts',name),path.join(root,'scripts',name));
 fs.writeFileSync(path.join(root,'scripts','guarded-io.mjs'),
  "export function runNativeOwned(){process.stdout.write('"+REACHED+"\\n');process.exit(42);}\n"+
  "export function validateChildLease(){throw Error('not in this fixture');}\n");
 return root;
}
function write(root,lockText,pin){
 fs.writeFileSync(path.join(root,'package-lock.json'),lockText);
 fs.writeFileSync(path.join(root,'scripts','build-inputs.json'),JSON.stringify({schema:'books-pack-inputs-v1',packageLockSha256:pin}));
}
const pack=root=>spawnSync(process.execPath,[path.join(root,'scripts','build-step.mjs'),'pack'],{cwd:root,encoding:'utf8',windowsHide:true,timeout:60000});
const bumped='{\n  "name": "books-arranger",\n  "version": "9.9.10",\n  "lockfileVersion": 3\n}\n';
const before='{\n  "name": "books-arranger",\n  "version": "9.9.9",\n  "lockfileVersion": 3\n}\n';

test('this checkout\'s committed pin matches its package-lock.json',()=>{
 assert.equal(lockPinProblem(repo),null);
});

test('a stale pin stops npm run pack before any guarded build work, naming both hashes',t=>{
 const root=box(t);write(root,bumped,sha(before));
 const r=pack(root);
 assert.ok(!r.stdout.includes(REACHED),'the guarded build must not start: '+r.stdout);
 assert.equal(r.status,1,r.stderr);
 assert.match(r.stderr,/^Stale lockfile pin/);
 assert.ok(r.stderr.includes(sha(bumped))&&r.stderr.includes(sha(before)),r.stderr);
 assert.match(r.stderr,/packageLockSha256/);
});

test('a matching pin lets npm run pack through to the guarded build',t=>{
 const root=box(t);write(root,bumped,sha(bumped));
 const r=pack(root);
 assert.equal(r.status,42,r.stderr);assert.ok(r.stdout.includes(REACHED));
});

test('a difference in line endings only is named as such, not as a bump',t=>{
 const root=box(t);
 write(root,bumped.replace(/\n/g,'\r\n'),sha(bumped));
 assert.match(lockPinProblem(root),/only in its line endings \(this copy has CRLF, the pin was taken from LF\)/);
 write(root,bumped,sha(bumped.replace(/\n/g,'\r\n')));
 assert.match(lockPinProblem(root),/only in its line endings \(this copy has LF, the pin was taken from CRLF\)/);
});

test('a missing or malformed pin and an unreadable lockfile are refused with a reason',t=>{
 const root=box(t);
 for(const pin of [undefined,'','ABC',sha(before).toUpperCase(),42]){write(root,bumped,pin);assert.match(lockPinProblem(root),/no valid packageLockSha256/);}
 fs.writeFileSync(path.join(root,'scripts','build-inputs.json'),'{not json');assert.match(lockPinProblem(root),/cannot read scripts\/build-inputs\.json/);
 write(root,bumped,sha(bumped));fs.rmSync(path.join(root,'package-lock.json'));assert.match(lockPinProblem(root),/cannot read package-lock\.json \(ENOENT\)/);
});

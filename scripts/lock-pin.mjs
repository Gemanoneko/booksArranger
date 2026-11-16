// The pack's lockfile pin, checked before any guarded build work (2026-11-16). scripts/build_native.py refuses the pack
// unless scripts/build-inputs.json packageLockSha256 is the SHA-256 of package-lock.json's raw bytes on disk. A version
// bump rewrites package-lock.json, so the pin goes stale unless the bump commit updates it too: missed at 0.28.5 and at
// 0.28.13, each found only when the guarded pack refused, with "Pack lockfile fingerprint changed" and no hashes.
// Read-only: it never writes the pin. A changed lockfile can also be a dependency change, which needs review first.
import {createHash} from 'node:crypto';import fs from 'node:fs';import path from 'node:path';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const lineEndings=(bytes,crlf)=>{const lf=Buffer.from(bytes.toString('latin1').replace(/\r\n/g,'\n'),'latin1');return crlf?Buffer.from(lf.toString('latin1').replace(/\n/g,'\r\n'),'latin1'):lf;};

// Returns null when the pin matches, else the message to print. Hashes exactly the bytes build_native.py hashes.
export function lockPinProblem(root){
 const inputs=path.join(root,'scripts','build-inputs.json'),lockPath=path.join(root,'package-lock.json');
 let pinned,lock;
 try{pinned=JSON.parse(fs.readFileSync(inputs,'utf8')).packageLockSha256;}catch(error){return 'Lockfile pin check: cannot read scripts/build-inputs.json ('+(error.code||error.message)+').';}
 if(typeof pinned!=='string'||!/^[a-f0-9]{64}$/.test(pinned))return 'Lockfile pin check: scripts/build-inputs.json has no valid packageLockSha256.';
 try{lock=fs.readFileSync(lockPath);}catch(error){return 'Lockfile pin check: cannot read package-lock.json ('+(error.code||error.message)+').';}
 const actual=sha(lock);
 if(actual===pinned)return null;
 const crlf=lock.includes('\r\n');
 if(sha(lineEndings(lock,!crlf))===pinned)
  return 'Lockfile pin check: package-lock.json differs from the pin only in its line endings (this copy has '+(crlf?'CRLF':'LF')+
   ', the pin was taken from '+(crlf?'LF':'CRLF')+'). The pack hashes the raw file, so it will refuse. This is not a version bump: '+
   'check package-lock.json out with the pinned line endings. Re-pinning here would break the pack in checkouts that have the other line endings.';
 return 'Stale lockfile pin: the pack will refuse.\n'+
  '  package-lock.json SHA-256:                     '+actual+'\n'+
  '  scripts/build-inputs.json packageLockSha256:   '+pinned+'\n'+
  'After a version bump, check that the lockfile diff touches only its two "version" fields. Then set packageLockSha256 to '+actual+
  ' and commit it in the same commit as the bump. Any other lockfile change is a dependency change: review it before re-pinning.';
}

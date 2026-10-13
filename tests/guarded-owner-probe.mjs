import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import {runNativeOwned,validateChildLease} from '../scripts/guarded-io.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
if(process.argv.length===2)runNativeOwned({mode:'probe',root,script:'tests/guarded-owner-probe.mjs'});
else {
 if(process.argv[2]!=='--owned-probe')throw Error('Invalid probe argv');
 const lease=validateChildLease({mode:'probe',root});
 if(lease.deadline<=Date.now())throw Error('Expired lease');
 let refused=false;try{fs.renameSync(lease.lease_path,lease.lease_path+'.swap');}catch{refused=true;}
 if(!refused)throw Error('Native held lease could be renamed');
 const raw={...lease};delete raw.manifestPath;raw.nonce='0'.repeat(64);
 const result=spawnSync('C:/Python314/python.exe',['-I','-B',path.join(root,'scripts/build_native.py'),'lease-check'],{cwd:root,input:JSON.stringify(raw),encoding:'utf8',windowsHide:true,timeout:30000,env:process.env});
 if(result.status!==1||!result.stderr.includes('Lease nonce/context/expiration mismatch'))throw Error('Forged nonce was not refused: '+result.stderr);
 console.log('Native owner probe PASS: exact supervisor generation/program, stdin capability, held lease, forged nonce refusal.');
}

import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
const PYTHON='C:/Python314/python.exe';
const PYTHON_SHA='e67f33a86fc64a07798a136af126f38a8e0d3c0a25787c635fb1678c2b66b12a';
function ordinary(file){const absolute=path.resolve(file);let current=absolute;while(true){const s=fs.lstatSync(current);if(s.isSymbolicLink())throw Error('Bootstrap reparse path refused');const parent=path.dirname(current);if(parent===current)break;current=parent;}return absolute;}
function hash(file){return createHash('sha256').update(fs.readFileSync(file)).digest('hex');}
function invoke(root,args,input){ordinary(PYTHON);if(hash(PYTHON)!==PYTHON_SHA)throw Error('Bootstrap Python fingerprint changed');const helper=ordinary(path.join(root,'scripts/build_native.py'));const result=spawnSync(PYTHON,['-I','-B',helper,...args],{cwd:root,input:JSON.stringify(input),encoding:'utf8',windowsHide:true,timeout:600000,maxBuffer:16*1024*1024,env:{...process.env,PYTHONPATH:'',PYTHONHOME:'',NODE_OPTIONS:'',NODE_PATH:''}});if(result.error||result.status!==0)throw Error(result.error?.message||result.stderr||'Native guard refused');return result.stdout;}
export function runNativeOwned({mode,root,script,timeoutMs=600000}){if(timeoutMs!==600000)throw Error('Expected finite ten-minute budget');const stdout=invoke(root,[],{mode,root:path.resolve(root),script,timeoutMs,node:process.execPath,node_sha256:hash(ordinary(process.execPath))});process.stdout.write(stdout);}
export function validateChildLease({mode,root}){const proof=JSON.parse(fs.readFileSync(0,'utf8'));if(proof.schema!=='books-build-lease-v1'||proof.mode!==mode||proof.root!==path.resolve(root)||proof.node!==process.execPath||!/^([a-f0-9]{64})$/.test(proof.nonce||''))throw Error('Missing exact owned-child lease');const result=JSON.parse(invoke(root,['lease-check'],proof));if(result.valid!==true)throw Error('Lease refused');return {...proof,manifestPath:path.join(root,'dist','release-artifacts.json')};}

#!/usr/bin/env node
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {runNativeOwned,validateChildLease} from './guarded-io.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
if(process.argv.length===2||(process.argv.length===3&&process.argv[2]==='pack'))runNativeOwned({mode:'build',root,script:'scripts/build-step.mjs'});
else if(process.argv.length===3&&process.argv[2]==='--owned-build'){
 const lease=validateChildLease({mode:'build',root});
 const result=spawnSync('C:/Python314/python.exe',['-I','-B',path.join(root,'scripts/build_phase.py')],{cwd:root,input:JSON.stringify(lease),encoding:'utf8',windowsHide:true,timeout:Math.max(1,lease.deadline-Date.now()),maxBuffer:16*1024*1024,env:process.env});
 if(result.error||result.status!==0)throw Error(result.error?.message||result.stderr||'Guarded staging failed');
 process.stdout.write(result.stdout);

}else throw Error('Unsupported build invocation');

/** Fixed private native-fixture child. Existing installed Node only; no compiler/media/global IO. */
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {spawn} from 'node:child_process';import {fileURLToPath} from 'node:url';
const NODE='C:/Program Files/nodejs/node.exe',SELF='C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/scripts/qa-native/native-fixture-child.mjs';
const SHARED='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared';const requireThat=(v,m)=>{if(!v)throw Error(m);};
export function fixtureChildLaunch(kind,planPath,planSha,root){
 requireThat(kind==='short-leaf'||kind==='linger-leaf','Only fixed descendant roles');
 return {file:NODE,args:[SELF,'--plan',planPath,'--plan-sha',planSha,'--case',kind],options:{cwd:root,env:{SystemRoot:'C:\\Windows',WINDIR:'C:\\Windows',PATH:'C:\\Program Files\\nodejs;C:\\Windows\\System32',TEMP:root+'/tmp',TMP:root+'/tmp'},windowsHide:true,detached:kind==='linger-leaf',stdio:['ignore','inherit','inherit']}};
}
async function childEntry(argv){
requireThat(argv.length===6&&argv[0]==='--plan'&&argv[2]==='--plan-sha'&&argv[4]==='--case','Exact fixed fixture child arguments');
const raw=fs.readFileSync(argv[1]);requireThat(raw.length<1048576&&crypto.createHash('sha256').update(raw).digest('hex')===argv[3],'Fixture plan drift');const plan=JSON.parse(raw);requireThat(plan.schema==='books-native-private-fixture-v1'&&plan.fixture_root===SHARED+'/native-fixture-'+plan.invocation_id,'Unknown private fixture root');
const spawnFixed=kind=>{const launch=fixtureChildLaunch(kind,argv[1],argv[3],plan.fixture_root);return spawn(launch.file,launch.args,launch.options);};
async function main(kind){
 if(kind==='short-leaf'){process.stdout.write('short-leaf-final\n');return;}
 if(kind==='nested-final'){await Promise.all(Array.from({length:8},()=>new Promise((resolve,reject)=>{const c=spawnFixed('short-leaf');c.on('error',reject);c.on('close',(code,signal)=>code===0&&!signal?resolve():reject(Error('Nested leaf failed')));})));process.stderr.write('root-stderr-final\n');process.stdout.write('root-stdout-final\n');return;}
 if(kind==='linger-root'){spawnFixed('linger-leaf');process.stdout.write('linger-root-final\n');process.exit(0);}
 if(kind==='linger-leaf'){await new Promise(resolve=>setTimeout(resolve,250));let denied=false;try{const f=fs.openSync(plan.fixture_root+'/lease.txt','r+');fs.closeSync(f);}catch(error){denied=['EPERM','EACCES','EBUSY'].includes(error.code);}requireThat(denied,'Lingering descendant opened write access despite held source lease');process.stdout.write('linger-lease-denied-final\n');return;}
 if(kind==='flood'){const block='x'.repeat(8192);setInterval(()=>{process.stdout.write(block);process.stderr.write(block);},1);return;}
 if(kind==='wait'){setInterval(()=>{},1000);return;}
 throw Error('No generic fixture child mode');
}
await main(argv[5]);
}
if(typeof process!=='undefined'&&process.argv[1]&&path.win32.resolve(process.argv[1]).toLowerCase()===path.win32.resolve(fileURLToPath(import.meta.url)).toLowerCase())childEntry(process.argv.slice(2)).catch(error=>{console.error(error.message);process.exitCode=2;});

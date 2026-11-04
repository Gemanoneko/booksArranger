import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [harness,koffiRoot,python,runner,directory,resultFile,...cases]=process.argv.slice(2);
const {runOwned}=await import(pathToFileURL(harness));
const base=path.dirname(directory);
const env={
 SystemRoot:process.env.SystemRoot,WINDIR:process.env.WINDIR,
 PATH:path.resolve(python,'../../ffmpeg')+';C:/Program Files/nodejs;C:/Program Files/Git/cmd;C:/Windows/System32',
 TEMP:path.join(base,'temp'),TMP:path.join(base,'temp'),TMPDIR:path.join(base,'temp'),
 USERPROFILE:path.join(base,'profile'),APPDATA:path.join(base,'profile'),LOCALAPPDATA:path.join(base,'profile'),
 BOOKS_QA_RUN_ROOT:directory,BOOKS_QA_FIXTURE_ROOT:path.join(base,'fixtures'),
 PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:''
};
const r=await runOwned(python,['-I','-B',runner,...cases],{cwd:directory,env,koffiRoot,timeoutMs:600000,maxBytes:4194304});
fs.writeFileSync(resultFile,JSON.stringify(r,null,2));
fs.writeFileSync(resultFile+'.log',r.out+r.err);
console.log(r.out,r.err,JSON.stringify({code:r.code,ok:r.ok,closed:r.closed,native:r.native,elapsedMs:r.elapsedMs}));
process.exitCode=r.ok?0:1;

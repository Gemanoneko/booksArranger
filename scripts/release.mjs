#!/usr/bin/env node
// One local release route: native owned lease -> exact accepted installer ->
// electron-builder artifact publisher. Authentication comes only from gh CLI.
import fs from 'node:fs';
import path from 'node:path';
import https from 'node:https';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { releaseFlow } from './release-flow.mjs';
import { leasedExecutable } from './release-contract.mjs';
import cleanup from './cleanup-releases.js';
import { runNativeOwned, validateChildLease } from './guarded-io.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(import.meta.url);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
function baseEnv() {
  const env={...process.env,GIT_OPTIONAL_LOCKS:'0'};
  for(const key of ['GH_TOKEN','GITHUB_TOKEN','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN','GH_HOST','NODE_OPTIONS','NODE_PATH','ELECTRON_RUN_AS_NODE'])delete env[key];
  return env;
}
function inspectFile(file) {
  const stat=fs.lstatSync(file);
  if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==1)throw new Error('Expected native-held regular single-link file');
  const hash=createHash('sha256'),fd=fs.openSync(file,'r');
  try {
    const buffer=Buffer.alloc(1024*1024);let count;
    while((count=fs.readSync(fd,buffer,0,buffer.length,null))>0)hash.update(buffer.subarray(0,count));
  } finally {fs.closeSync(fd);}
  return {sha256:hash.digest('hex'),size:stat.size};
}
function inspectTree(folder) {
  const files={};
  const walk=(dir,relative='')=>{
    for(const name of fs.readdirSync(dir)) {
      const full=path.join(dir,name),key=relative?relative+'/'+name:name,stat=fs.lstatSync(full);
      if(stat.isSymbolicLink())throw new Error('Unexpected reparse/symlink in held payload');
      if(stat.isDirectory())walk(full,key);
      else if(stat.isFile())files[key]=inspectFile(full);
      else throw new Error('Special payload member refused');
    }
  };
  walk(folder);return files;
}
function sameMap(actual,expected) {
  if(!expected||typeof expected!=='object'||Array.isArray(expected))throw new Error('Missing payload hash map');
  const keys=Object.keys(actual).sort(),wanted=Object.keys(expected).sort();
  if(JSON.stringify(keys)!==JSON.stringify(wanted))throw new Error('Payload file membership changed');
  for(const key of keys)if(actual[key].sha256!==expected[key].sha256||actual[key].size!==expected[key].size)throw new Error('Payload file changed: '+key);
}
async function ownedRelease() {
  // The option is not authority: this checks a per-launch stdin nonce, native
  // supervisor generation/image and retained lease. No fallback is permitted.
  const ownership=await validateChildLease({mode:'release',root});
  if(ownership.root!==root||!path.isAbsolute(ownership.ownedRoot)||!path.resolve(ownership.ownedRoot).startsWith(path.join(root,'build-cache','builds')+path.sep)||!Number.isFinite(ownership.deadline)||ownership.deadline<=Date.now())throw new Error('Invalid native release lease');
  let token=null;
  const safePath=relative=>{
    if(typeof relative!=='string'||relative.includes('\\')||path.isAbsolute(relative)||relative.split('/').some(p=>!p||p==='.'||p==='..'))throw new Error('Unsafe release path');
    return path.join(root,...relative.split('/'));
  };
  const run=async(command,args,{credential=false}={})=>{
    if(Date.now()>=ownership.deadline)throw new Error('Owned release deadline reached');
    const builder=command==='node-builder';
    if(!['git','gh','node-builder'].includes(command))throw new Error('Unapproved release subprocess');
    if(credential&&(!builder||!token))throw new Error('Credential child is not the artifact publisher');
    const executable=leasedExecutable(ownership,command);
    const argv=builder?[require.resolve('electron-builder/out/cli/cli.js'),...args]:args;
    const env=baseEnv();if(credential)env.GH_TOKEN=token;
    const result=spawnSync(executable,argv,{cwd:root,env,encoding:'utf8',windowsHide:true,shell:false,maxBuffer:16*1024*1024,timeout:Math.max(1,Math.min(builder?550000:30000,ownership.deadline-Date.now()))});
    // Every descendant remains in the native Job, including timeout paths.
    if(builder){const output=(result.stdout||'')+(result.stderr||'');console.log(token?output.split(token).join('[credential redacted]'):output);}
    if(result.error||result.status!==0)throw new Error(command+' failed (exit '+result.status+').'+(command==='gh'?' Authenticate GitHub CLI with gh auth login.':''));
    return {stdout:result.stdout||'',stderr:result.stderr||''};
  };
  const api=async(method,route,{allow404=false}={})=>{
    if(!token)throw new Error('No CLI authentication');
    if(!['GET','DELETE'].includes(method)||!/^\/repos\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\//.test(route))throw new Error('Unapproved release API call');
    return await new Promise((resolve,reject)=>{
      const request=https.request({hostname:'api.github.com',path:route,method,headers:{Authorization:'Bearer '+token,'User-Agent':'books-arranger-local-release',Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}},response=>{
        let text='',bytes=0;
        response.on('data',chunk=>{bytes+=chunk.length;if(bytes>4*1024*1024)request.destroy(new Error('GitHub response exceeded bound'));else text+=chunk;});
        response.on('error',reject);
        response.on('end',()=>{
          if(allow404&&response.statusCode===404)return resolve(null);
          if(response.statusCode<200||response.statusCode>=300)return reject(new Error('GitHub '+method+' failed with HTTP '+response.statusCode));
          try {resolve(text?JSON.parse(text):null);}catch{reject(new Error('Invalid GitHub JSON response'));}
        });
      });
      request.setTimeout(Math.max(1,Math.min(30000,ownership.deadline-Date.now())),()=>request.destroy(new Error('GitHub request timed out')));
      request.on('error',reject);request.end();
    });
  };
  const io={run,
    read:async relative=>fs.readFileSync(safePath(relative),'utf8'),
    exists:async relative=>fs.existsSync(safePath(relative)),
    hash:async relative=>inspectFile(safePath(relative)),
    prepare:async()=>{throw new Error('No accepted candidate. Run npm run pack under its native guard, then obtain QA/review before release.');},
    authenticate:async()=>{
      const result=await run('gh',['auth','token','--hostname','github.com']);
      token=result.stdout.trim();
      if(!token||/[\r\n\s]/.test(token))throw new Error('gh auth token returned no usable credential. Run gh auth login.');
      console.log('[release] Authentication acquired from GitHub CLI; token is supplied only to the publisher child.');
    },api,
    verifyPayload:async manifest=>{
      const unpacked=safePath('dist/'+manifest.unpacked),actual=inspectTree(unpacked);
      sameMap(actual,manifest.payload.files);
      const runtime=Object.fromEntries(Object.entries(actual).filter(([key])=>key.startsWith('resources/python/')||key.startsWith('resources/ffmpeg/')));
      sameMap(runtime,manifest.runtime?.files);
      if(sha(fs.readFileSync(safePath('desktop/runtime-pins.json')))!==manifest.runtime?.pins_sha256)throw new Error('Runtime pins changed');
      for(const name of ['replacement_eye_plan.json','public_source_leads.json']){
        const shipped='resources/backend/'+name,source=inspectFile(safePath(name));
        if(source.sha256!==actual[shipped]?.sha256||source.size!==actual[shipped]?.size||source.sha256!==manifest.payload.protected_data_files?.[name]?.sha256||source.size!==manifest.payload.protected_data_files?.[name]?.size)throw new Error('Protected source JSON differs in installer');
      }
      const asar=require('@electron/asar'),archive=path.join(unpacked,'resources','app.asar');
      const pkg=JSON.parse(asar.extractFile(archive,'package.json').toString('utf8'));
      if(pkg.version!==manifest.version||fs.readFileSync(path.join(unpacked,'resources','backend','VERSION'),'utf8')!==manifest.version+'\n')throw new Error('Actual packaged VERSION mismatch');
      for(const filename of asar.listPackage(archive)) {
        const relative=filename.replace(/^[/\\]/,'').replaceAll('\\','/');
        if(relative.startsWith('desktop/')&&!relative.endsWith('/')&&fs.existsSync(safePath(relative))&&fs.lstatSync(safePath(relative)).isFile()){
          if(!asar.extractFile(archive,relative).equals(fs.readFileSync(safePath(relative))))throw new Error('Packaged shell differs from accepted source');
        }
      }
    },
    cleanup:async(route,tag)=>{
      const result=await cleanup.cleanupReleases(api,route,tag);
      console.log('[release] Keep-four verified; Sully must now git fetch --prune --prune-tags and verify local tag parity.');
      return result;
    }
  };
  const result=await releaseFlow(io);
  console.log('[release] Published '+result.tag+' from '+result.head+'; verified '+result.assets.length+' assets.');
  if(result.cleanupWarning)console.warn('[release] Published successfully; cleanup warning: '+result.cleanupWarning);
}
try {
  if(process.argv.slice(2).length===0)await runNativeOwned({mode:'release',root,script:'scripts/release.mjs'});
  else if(process.argv.slice(2).join(' ')==='--owned-release')await ownedRelease();
  else throw new Error('Unsupported release arguments');
} catch(error) {
  console.error('[release] '+error.message);process.exitCode=1;
}

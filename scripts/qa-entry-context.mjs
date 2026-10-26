#!/usr/bin/env node
// Assembles one protocol-2 entry-check context for the qa-handoff entry check (Futaba's and Ender's identical receipt).
// Replaces scripts/qa-context-assembly.py and -v2.py (their roots were fixed to runs that no longer exist) and the 0.21.2
// to 0.22.0 one-off copies (Docs/assemble-entry-0212.mjs), with Senua's v0.21.2 addendum fixed:
//   E1  the wrapper that runs the check is generated into harness/ (the harness digest covers it) and sets the runtime
//       and fixture the context pins; the gate prints the runtime root and its manifest digest in its pass line;
//   E2  graph.json records this assembler's own SHA-256;
//   E3  the QA runtime must match the snapshot's scripts/qa-runtime.json pins, else nothing is written;
//   E4  Git runs with every GIT_* variable removed, GIT_OPTIONAL_LOCKS=0 and core.fsmonitor=false;
//   E5  every path and the expected HEAD are arguments; nothing is a literal of one run.
//
// node scripts/qa-entry-context.mjs --worktree <clean checkout> --run <run parent> --head <expected 40-hex HEAD>
//      --runtime <QA runtime: python/ and ffmpeg/> --fixture <private MP3 fixture file> [--checker <qa-handoff scripts>]
//      [--port <fixture port, default 5212>]
// Run it with the Node that will run the check (its folder is pinned as the node installation). Writes only
// <run>/context and refuses if it exists. Runs no checks. Prints the context's path and SHA-256.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

export const CORE=['run_entry_checks.mjs','entry-main.mjs','entry-identity.mjs','bounded-check.mjs','bounded-child.mjs'];
export const CHECK_NAMES=['pre-qa','post-build','check-electron','check','test:smoke'];
const DEFAULT_CHECKER='C:\\Antigravity Projects\\Studio Illuminati\\.claude\\skills\\qa-handoff\\scripts';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const fileSha=async file=>sha(await fs.readFile(file));

export function parseArgs(argv){
  const allowed=new Set(['--worktree','--run','--head','--runtime','--fixture','--checker','--port']),out={};
  for(let i=0;i<argv.length;i+=2){
    if(!allowed.has(argv[i])||Object.hasOwn(out,argv[i].slice(2))||argv[i+1]===undefined)throw Error('Unknown, repeated or empty argument: '+argv[i]);
    out[argv[i].slice(2)]=argv[i+1];
  }
  for(const name of ['worktree','run','head','runtime','fixture'])if(!out[name])throw Error('--'+name+' is required');
  if(!/^[0-9a-f]{40}$/.test(out.head))throw Error('--head must be the full expected commit (40 hex digits)');
  out.checker??=DEFAULT_CHECKER;
  for(const name of ['worktree','run','runtime','fixture','checker'])if(!path.isAbsolute(out[name]))throw Error('--'+name+' must be an absolute path');
  out.port=Number(out.port??5212);
  if(!Number.isInteger(out.port)||out.port<1024||out.port>65535)throw Error('--port must be a port number');
  return out;
}

// E4: Git never reads the caller's GIT_* variables, never takes optional locks, never asks fsmonitor.
export function cleanGitEnv(env=process.env){
  const clean={};for(const [key,value] of Object.entries(env))if(!/^GIT_/i.test(key))clean[key]=value;
  clean.GIT_OPTIONAL_LOCKS='0';return clean;
}
// The runner is a parameter of assemble() so its test needs no Git: the qa-handoff entry checker gives the checks it
// runs only Node and System32 on PATH, and the 0.22.1 entry check failed on the test's own `git` (ENOENT, 2026-10-26).
export function gitIn(worktree,exec=execFileSync){
  const env=cleanGitEnv();
  return args=>exec('git',['-c','core.fsmonitor=false','-C',worktree,...args],{encoding:'utf8',windowsHide:true,maxBuffer:64*1024*1024,env});
}

// Same walk shape as the checker's verifyFiles: '/'-joined relative paths, no links, no special entries.
export async function walk(root){
  const out=[];
  async function rec(dir,prefix){
    for(const ent of await fs.readdir(dir,{withFileTypes:true})){
      const rel=prefix+ent.name;
      if(ent.isSymbolicLink())throw Error('Link refused: '+path.join(root,rel));
      if(ent.isDirectory())await rec(path.join(dir,ent.name),rel+'/');
      else if(ent.isFile())out.push(rel);
      else throw Error('Special entry refused: '+path.join(root,rel));
    }
  }
  await rec(root,'');
  return out.sort();
}
export async function manifestOf(root){const files=[];for(const rel of await walk(root))files.push({path:rel,sha256:await fileSha(path.join(root,rel))});return {files};}
// One digest for a whole tree: the SHA-256 of its sorted "path<TAB>sha256" lines (the gate prints the runtime's, E1).
export function treeDigest(manifest){return sha(manifest.files.map(item=>item.path+'\t'+item.sha256).join('\n'));}

// E3: the QA runtime must be the one the snapshot pins (python.exe, ffmpeg.exe, ffprobe.exe by SHA-256 and size).
export async function checkRuntime(runtime,pins){
  const python=path.join(runtime,'python','python.exe');
  if(await fileSha(python).catch(()=>'')!==pins.python.sha256)throw Error('QA runtime refused: python.exe differs from scripts/qa-runtime.json');
  for(const [name,expected] of Object.entries(pins.ffmpeg.files)){
    const file=path.join(runtime,'ffmpeg',name),stat=await fs.lstat(file).catch(()=>null);
    if(!stat?.isFile()||stat.size!==expected.size||await fileSha(file)!==expected.sha256)throw Error('QA runtime refused: '+name+' differs from scripts/qa-runtime.json');
  }
}

export async function assemble(options,{node=process.execPath,log=console.log,git=gitIn(options.worktree)}={}){
  const W=options.worktree,Q=options.run,C=path.join(Q,'context'),HEAD=options.head;
  const NODE_DIR=path.dirname(node);
  try{await fs.lstat(C);throw Error('Context folder already exists; refusing to adopt it: '+C);}catch(error){if(error.code!=='ENOENT')throw error;}
  if(git(['rev-parse','HEAD']).trim()!==HEAD)throw Error('Worktree HEAD is not '+HEAD);
  if(git(['status','--porcelain']).trim())throw Error('Worktree is dirty');
  const list=[...new Set(git(['ls-files','--cached','--others','--exclude-standard','-z']).split('\0').filter(Boolean))].sort();
  const pins=JSON.parse(await fs.readFile(path.join(W,'scripts','qa-runtime.json'),'utf8'));
  await checkRuntime(options.runtime,pins);  // before anything is written (E3)
  const fixtureStat=await fs.lstat(options.fixture).catch(()=>null);
  if(!fixtureStat?.isFile())throw Error('The MP3 fixture is not a file: '+options.fixture);
  const self=fileURLToPath(import.meta.url),assembler={path:self,sha256:await fileSha(self)};  // E2
  // Every runtime tree is read first: a link or special entry refuses before anything is written.
  const trees=[{name:'dependencies',root:path.join(W,'node_modules')},{name:'ownership',root:path.join(Q,'ownership')},
    {name:'bundled-media',root:options.runtime},{name:'mp3-fixture',root:path.dirname(options.fixture)},{name:'node-installation',root:NODE_DIR}];
  for(const tree of trees)tree.manifest=await manifestOf(tree.root);

  await fs.mkdir(C);
  const sha256Of=async(rel,bytes)=>{const file=path.join(C,rel);await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,bytes,{flag:'wx'});return {path:file,sha256:sha(bytes)};};
  const emit=(rel,value)=>sha256Of(rel,Buffer.from(JSON.stringify(value,null,1)+'\n'));
  // 1. The complete source snapshot, byte for byte from the clean worktree.
  const sourceRoot=path.join(C,'source'),sourceFiles=[];
  for(const rel of list){
    const bytes=await fs.readFile(path.join(W,rel)),to=path.join(sourceRoot,rel);
    await fs.mkdir(path.dirname(to),{recursive:true});await fs.writeFile(to,bytes,{flag:'wx'});
    sourceFiles.push({path:rel,sha256:sha(bytes)});
  }
  if((await walk(sourceRoot)).join('\n')!==list.join('\n'))throw Error('Snapshot differs from the Git file list');
  const sourceRef=await emit('source-manifest.json',{files:sourceFiles});
  // 2. The harness: the declared check graph and the wrapper that runs the check with the pinned runtime (E1).
  const pkg=JSON.parse(await fs.readFile(path.join(W,'package.json'),'utf8'));
  const route=sourceFiles.find(item=>item.path==='scripts/check-desktop.mjs');
  if(!route)throw Error('The snapshot has no scripts/check-desktop.mjs');
  const auditedNodes=[{path:route.path,sha256:route.sha256,kind:'pure-node',command:'node scripts/check-desktop.mjs'}];
  const environment={BOOKS_QA_RUNTIME_ROOT:options.runtime,BOOKS_MP3_REAL_FIXTURE:options.fixture};
  const graph={schema:'books-entry-graph-v3',source_head:HEAD,version:pkg.version,assembler,
    declared_scripts:Object.fromEntries(CHECK_NAMES.filter(name=>Object.hasOwn(pkg.scripts || {},name)).map(name=>[name,pkg.scripts[name]])),
    audited_nodes:auditedNodes,required_free_ports:[options.port],environment,
    limits:'No GUI launch, installer execution, live catalog or library access. The gate runs in a fresh copy under the run parent.'};
  const quote=value=>"'"+String(value).replaceAll("'","'\\''")+"'";
  const wrapper=['#!/bin/bash',
    '# Generated by scripts/qa-entry-context.mjs for '+HEAD+'. Runs the qa-handoff entry check on this context with the',
    '# runtime and fixture this context pins (Senua v0.21.2 E1). Usage: bash run-entry.sh <absolute run root>',
    'set -euo pipefail',
    'export BOOKS_QA_RUNTIME_ROOT='+quote(options.runtime),
    'export BOOKS_MP3_REAL_FIXTURE='+quote(options.fixture),
    'context='+quote(path.join(C,'context.json')),
    'exec '+quote(node)+' '+quote(path.join(options.checker,'run_entry_checks.mjs'))+' --context "$context" --context-sha "$(cat "$context.sha256")" --run-root "$1"',''].join('\n');
  const harnessRoot=path.join(C,'harness');
  const graphRef=await emit('harness/graph.json',graph),wrapperRef=await sha256Of('harness/run-entry.sh',Buffer.from(wrapper));
  const harnessRef=await emit('harness-manifest.json',{files:[{path:'graph.json',sha256:graphRef.sha256},{path:'run-entry.sh',sha256:wrapperRef.sha256}]});
  // 3. Runtime trees, each a complete manifest (read above), checked again unchanged as they are written.
  const manifests=[],counts={};
  for(const tree of trees){
    const manifest=await manifestOf(tree.root);
    if(JSON.stringify(manifest)!==JSON.stringify(tree.manifest))throw Error('A runtime tree changed during assembly: '+tree.root);
    counts[tree.name]=manifest.files.length;manifests.push({name:tree.name,root:tree.root,manifest:await emit('runtime-'+tree.name+'.json',manifest)});
  }
  const exe=async(name,file)=>({name,path:file,sha256:await fileSha(file)});
  const runtime={node:await exe('node',node),npmCli:await exe('npmCli',path.join(NODE_DIR,'node_modules','npm','bin','npm-cli.js')),
    shell:await exe('shell','C:\\Windows\\System32\\cmd.exe'),npmShim:await exe('npmShim',path.join(NODE_DIR,'npm.cmd')),
    manifests,koffiRoot:path.join(Q,'ownership','node_modules','koffi')};
  const tooling=[];for(const name of CORE)tooling.push({path:name,sha256:await fileSha(path.join(options.checker,name))});
  const context={schema:2,deadlineMs:600000,ownership:'private-job-or-process-group',
    source:{repo:W,root:sourceRoot,head:HEAD,dirty:'N',manifest:sourceRef},
    harness:{root:harnessRoot,manifest:harnessRef},runtime,tooling:{files:tooling},
    execution:{runRootParent:Q,requiredFreePorts:[options.port],auditedNodes}};
  if(git(['rev-parse','HEAD']).trim()!==HEAD||git(['status','--porcelain']).trim())throw Error('Worktree changed during assembly');
  const contextRef=await emit('context.json',context);
  await fs.writeFile(contextRef.path+'.sha256',contextRef.sha256+'\n',{flag:'wx'});
  const result={context:contextRef,assembler,sourceFiles:sourceFiles.length,runtimeCounts:counts};
  log(JSON.stringify(result));
  return result;
}

if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{await assemble(parseArgs(process.argv.slice(2)));}catch(error){console.error(error.message);process.exitCode=1;}
}

// Assemble one protocol-2 entry-check context for Books Arranger 0.21.2 (139d2c6).
// Writes only under qa-run-0212/context (refuses if it exists). Runs no checks.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const W='C:\\Antigravity Projects\\Worktrees\\Books Arranger\\cand-0212';
const Q='C:\\Antigravity Projects\\Worktrees\\Books Arranger\\qa-run-0212';
const C=path.join(Q,'context');
const HEAD='139d2c681c5a91beebfc5ec1c53efa73eed8336b';
const CHECKER='C:\\Antigravity Projects\\Studio Illuminati\\.claude\\skills\\qa-handoff\\scripts';
const CORE=['run_entry_checks.mjs','entry-main.mjs','entry-identity.mjs','bounded-check.mjs','bounded-child.mjs'];
const NODE_DIR='C:\\Program Files\\nodejs';
const NODE=path.join(NODE_DIR,'node.exe');
const FIXTURE_DIR='C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\private-fixtures\\ba-mp3-fixture';
const FIXTURE=path.join(FIXTURE_DIR,'fixture.mp3');
const QA_RUNTIME=path.join(Q,'qa-runtime');
const CHECK_NAMES=['pre-qa','post-build','check-electron','check','test:smoke'];

const sha=b=>createHash('sha256').update(b).digest('hex');
const fileSha=async p=>sha(await fs.readFile(p));
const git=args=>execFileSync('git',['-C',W,...args],{encoding:'utf8',windowsHide:true,maxBuffer:64*1024*1024});

// Same walk shape as entry-identity verifyFiles: '/'-joined relative paths, no links, no special entries.
async function walk(root){
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
async function manifestOf(root){const files=[];for(const rel of await walk(root))files.push({path:rel,sha256:await fileSha(path.join(root,rel))});return{files};}
async function emit(rel,value){
  const file=path.join(C,rel),bytes=Buffer.from(JSON.stringify(value,null,1)+'\n');
  await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,bytes,{flag:'wx'});
  return{path:file,sha256:sha(bytes)};
}

if(path.resolve(process.execPath).toLowerCase()!==NODE.toLowerCase())throw Error('Run this with '+NODE);
try{await fs.lstat(C);throw Error('Context folder already exists; refusing to adopt it: '+C);}catch(error){if(error.code!=='ENOENT')throw error;}
if(git(['rev-parse','HEAD']).trim()!==HEAD)throw Error('Worktree HEAD is not '+HEAD);
if(git(['status','--porcelain']).trim())throw Error('Worktree is dirty');
const list=[...new Set(git(['ls-files','--cached','--others','--exclude-standard','-z']).split('\0').filter(Boolean))].sort();

await fs.mkdir(C);
// 1. Complete source snapshot, byte-for-byte from the clean worktree.
const sourceRoot=path.join(C,'source'),sourceFiles=[];
for(const rel of list){
  const bytes=await fs.readFile(path.join(W,rel)),to=path.join(sourceRoot,rel);
  await fs.mkdir(path.dirname(to),{recursive:true});await fs.writeFile(to,bytes,{flag:'wx'});
  sourceFiles.push({path:rel,sha256:sha(bytes)});
}
if((await walk(sourceRoot)).join('\n')!==list.join('\n'))throw Error('Snapshot differs from the Git file list');
const sourceRef=await emit('source-manifest.json',{files:sourceFiles});

// 2. Declared check graph (harness). Only scripts/check-desktop.mjs is an audited node route.
const pkg=JSON.parse(await fs.readFile(path.join(W,'package.json'),'utf8'));
const route=sourceFiles.find(item=>item.path==='scripts/check-desktop.mjs');
const auditedNodes=[{path:route.path,sha256:route.sha256,kind:'pure-node',command:'node scripts/check-desktop.mjs'}];
const graph={schema:'books-entry-graph-0212',source_head:HEAD,version:pkg.version,
  declared_scripts:Object.fromEntries(CHECK_NAMES.filter(name=>Object.hasOwn(pkg.scripts,name)).map(name=>[name,pkg.scripts[name]])),
  audited_nodes:auditedNodes,required_free_ports:[5212],
  environment:{BOOKS_QA_RUNTIME_ROOT:QA_RUNTIME,BOOKS_MP3_REAL_FIXTURE:FIXTURE},
  limits:'No GUI launch, installer execution, live catalog or library access. The gate runs in a fresh copy under the run parent.'};
const harnessRoot=path.join(C,'harness');
const graphRef=await emit('harness/graph.json',graph);
const harnessRef=await emit('harness-manifest.json',{files:[{path:'graph.json',sha256:graphRef.sha256}]});

// 3. Runtime trees, each a complete manifest.
const trees=[
  {name:'dependencies',root:path.join(W,'node_modules')},
  {name:'ownership',root:path.join(Q,'ownership')},
  {name:'bundled-media',root:QA_RUNTIME},
  {name:'mp3-fixture',root:FIXTURE_DIR},
  {name:'node-installation',root:NODE_DIR},
];
const manifests=[],counts={};
for(const tree of trees){const manifest=await manifestOf(tree.root);counts[tree.name]=manifest.files.length;manifests.push({name:tree.name,root:tree.root,manifest:await emit('runtime-'+tree.name+'.json',manifest)});}
const exe=async(name,file)=>({name,path:file,sha256:await fileSha(file)});
const runtime={node:await exe('node',NODE),npmCli:await exe('npmCli',path.join(NODE_DIR,'node_modules','npm','bin','npm-cli.js')),
  shell:await exe('shell','C:\\Windows\\System32\\cmd.exe'),npmShim:await exe('npmShim',path.join(NODE_DIR,'npm.cmd')),
  manifests,koffiRoot:path.join(Q,'ownership','node_modules','koffi')};
const tooling=[];for(const name of CORE)tooling.push({path:name,sha256:await fileSha(path.join(CHECKER,name))});

const context={schema:2,deadlineMs:600000,ownership:'private-job-or-process-group',
  source:{repo:W,root:sourceRoot,head:HEAD,dirty:'N',manifest:sourceRef},
  harness:{root:harnessRoot,manifest:harnessRef},runtime,tooling:{files:tooling},
  execution:{runRootParent:Q,requiredFreePorts:[5212],auditedNodes}};
if(git(['rev-parse','HEAD']).trim()!==HEAD||git(['status','--porcelain']).trim())throw Error('Worktree changed during assembly');
const contextRef=await emit('context.json',context);
console.log(JSON.stringify({context:contextRef,sourceFiles:sourceFiles.length,runtimeCounts:counts}));

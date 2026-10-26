// The QA entry-context assembler (scripts/qa-entry-context.mjs; Senua's v0.21.2 addendum, E1-E5): its refusals write
// nothing (an existing context folder, a dirty tree, a wrong HEAD, a QA runtime that differs from the pins, a link in a
// tree), Git ignores the caller's GIT_* variables, and a good run pins the wrapper in the harness and its own hash in the
// graph. A private temporary repository and fake runtime, checker and Node folders; no gate is run.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {assemble,parseArgs,cleanGitEnv,CORE} from '../scripts/qa-entry-context.mjs';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const git=(cwd,...args)=>execFileSync('git',['-C',cwd,...args],{encoding:'utf8',windowsHide:true,env:cleanGitEnv()});

async function fixture(t){
  const base=await fs.mkdtemp(path.join(os.tmpdir(),'qa-entry-'));
  t.after(()=>fs.rm(base,{recursive:true,force:true}));
  const W=path.join(base,'w'),runtime=path.join(base,'runtime'),checker=path.join(base,'checker'),nodeDir=path.join(base,'node'),run=path.join(base,'run');
  const python=Buffer.from('fake python'),ffmpeg=Buffer.from('fake ffmpeg'),ffprobe=Buffer.from('fake ffprobe');
  await fs.mkdir(path.join(W,'scripts'),{recursive:true});await fs.mkdir(path.join(W,'node_modules','dep'),{recursive:true});
  await fs.writeFile(path.join(W,'node_modules','dep','index.js'),'x');
  await fs.writeFile(path.join(W,'scripts','check-desktop.mjs'),'// gate\n');
  await fs.writeFile(path.join(W,'package.json'),JSON.stringify({version:'0.22.1',scripts:{check:'node scripts/check-desktop.mjs'}}));
  await fs.writeFile(path.join(W,'.gitignore'),'node_modules/\n');
  await fs.writeFile(path.join(W,'scripts','qa-runtime.json'),JSON.stringify({schema:1,python:{sha256:sha(python)},ffmpeg:{files:{'ffmpeg.exe':{sha256:sha(ffmpeg),size:ffmpeg.length},'ffprobe.exe':{sha256:sha(ffprobe),size:ffprobe.length}}}}));
  git(base,'init','-q','w');git(W,'config','user.email','qa@example.invalid');git(W,'config','user.name','qa');git(W,'config','core.autocrlf','false');
  git(W,'add','-A');git(W,'commit','-q','-m','fixture');
  const head=git(W,'rev-parse','HEAD').trim();
  await fs.mkdir(path.join(runtime,'python'),{recursive:true});await fs.mkdir(path.join(runtime,'ffmpeg'),{recursive:true});
  await fs.writeFile(path.join(runtime,'python','python.exe'),python);await fs.writeFile(path.join(runtime,'ffmpeg','ffmpeg.exe'),ffmpeg);await fs.writeFile(path.join(runtime,'ffmpeg','ffprobe.exe'),ffprobe);
  await fs.mkdir(checker,{recursive:true});for(const name of CORE)await fs.writeFile(path.join(checker,name),'// '+name);
  await fs.mkdir(path.join(nodeDir,'node_modules','npm','bin'),{recursive:true});await fs.writeFile(path.join(nodeDir,'node.exe'),'node');
  await fs.writeFile(path.join(nodeDir,'npm.cmd'),'npm');await fs.writeFile(path.join(nodeDir,'node_modules','npm','bin','npm-cli.js'),'cli');
  await fs.mkdir(path.join(run,'ownership'),{recursive:true});await fs.writeFile(path.join(run,'ownership','owner.txt'),'o');
  const fixtureDir=path.join(base,'fixture');await fs.mkdir(fixtureDir);await fs.writeFile(path.join(fixtureDir,'fixture.mp3'),'mp3');
  const options={worktree:W,run,head,runtime,fixture:path.join(fixtureDir,'fixture.mp3'),checker,port:5212};
  return {base,W,run,runtime,options,node:path.join(nodeDir,'node.exe')};
}
const quiet={log(){}};
const absent=async file=>{await assert.rejects(fs.lstat(file),{code:'ENOENT'});};

test('arguments: every path and the expected HEAD are required, absolute and exact (E5)',()=>{
  const ok=['--worktree','C:\\w','--run','C:\\r','--head','a'.repeat(40),'--runtime','C:\\q','--fixture','C:\\f.mp3'];
  assert.equal(parseArgs(ok).port,5212);
  assert.throws(()=>parseArgs(ok.slice(0,4).concat(ok.slice(6))),/--head is required/);
  assert.throws(()=>parseArgs(ok.map(v=>v==='a'.repeat(40)?'abc123':v)),/full expected commit/);
  assert.throws(()=>parseArgs(ok.map(v=>v==='C:\\r'?'relative':v)),/absolute/);
  assert.throws(()=>parseArgs([...ok,'--extra','x']),/Unknown/);
});

test('git ignores the caller\'s GIT_* variables and takes no optional locks (E4)',()=>{
  const env=cleanGitEnv({PATH:'p',GIT_DIR:'C:\\other',git_work_tree:'x',HOME:'h'});
  assert.deepEqual(env,{PATH:'p',HOME:'h',GIT_OPTIONAL_LOCKS:'0'});
});

test('a good run pins the wrapper in the harness and the assembler in the graph (E1, E2)',async t=>{
  const f=await fixture(t);
  const before=process.env.GIT_DIR;process.env.GIT_DIR=path.join(f.base,'nowhere');  // a stray GIT_DIR is ignored (E4)
  t.after(()=>{if(before===undefined)delete process.env.GIT_DIR;else process.env.GIT_DIR=before;});
  const result=await assemble(f.options,{node:f.node,...quiet});
  const C=path.join(f.run,'context'),context=JSON.parse(await fs.readFile(path.join(C,'context.json'),'utf8'));
  assert.equal(context.source.head,f.options.head);assert.equal(result.context.sha256,sha(await fs.readFile(path.join(C,'context.json'))));
  assert.equal((await fs.readFile(path.join(C,'context.json.sha256'),'utf8')).trim(),result.context.sha256);
  const harness=JSON.parse(await fs.readFile(path.join(C,'harness-manifest.json'),'utf8'));
  assert.deepEqual(harness.files.map(item=>item.path),['graph.json','run-entry.sh'],'the wrapper is covered by the harness digest');
  const wrapper=await fs.readFile(path.join(C,'harness','run-entry.sh'),'utf8');
  assert.match(wrapper,new RegExp('BOOKS_QA_RUNTIME_ROOT='+"'"+f.runtime.replaceAll('\\','\\\\')+"'"));assert.match(wrapper,/--context-sha "\$\(cat "\$context.sha256"\)"/);
  const graph=JSON.parse(await fs.readFile(path.join(C,'harness','graph.json'),'utf8'));
  assert.equal(graph.assembler.sha256,sha(await fs.readFile(new URL('../scripts/qa-entry-context.mjs',import.meta.url))));
  assert.deepEqual(graph.environment,{BOOKS_QA_RUNTIME_ROOT:f.runtime,BOOKS_MP3_REAL_FIXTURE:f.options.fixture});
});

test('refusals write nothing: an existing context, a dirty tree, a wrong HEAD, a runtime that differs, a link',async t=>{
  const f=await fixture(t),C=path.join(f.run,'context');
  await fs.mkdir(C);await assert.rejects(assemble(f.options,{node:f.node,...quiet}),/already exists/);await fs.rm(C,{recursive:true});
  await assert.rejects(assemble({...f.options,head:'0'.repeat(40)},{node:f.node,...quiet}),/HEAD is not/);await absent(C);
  await fs.writeFile(path.join(f.W,'package.json'),'{}');
  await assert.rejects(assemble(f.options,{node:f.node,...quiet}),/dirty/);await absent(C);
  git(f.W,'checkout','--','package.json');
  await fs.writeFile(path.join(f.runtime,'python','python.exe'),'another python');
  await assert.rejects(assemble(f.options,{node:f.node,...quiet}),/python.exe differs/);await absent(C);  // E3
  await fs.writeFile(path.join(f.runtime,'python','python.exe'),'fake python');
  await fs.writeFile(path.join(f.runtime,'ffmpeg','ffprobe.exe'),'fake ffprobX');
  await assert.rejects(assemble(f.options,{node:f.node,...quiet}),/ffprobe.exe differs/);await absent(C);
  await fs.writeFile(path.join(f.runtime,'ffmpeg','ffprobe.exe'),'fake ffprobe');
  await fs.symlink(path.join(f.base,'checker'),path.join(f.W,'node_modules','linked'),'junction');
  await assert.rejects(assemble(f.options,{node:f.node,...quiet}),/Link refused/);await absent(C);
});

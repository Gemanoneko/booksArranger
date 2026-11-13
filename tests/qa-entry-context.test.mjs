// The QA entry-context assembler (scripts/qa-entry-context.mjs; Senua's v0.21.2 addendum, E1-E5): its refusals write
// nothing (an existing context folder, a dirty tree, a wrong HEAD, a QA runtime that differs from the pins, a link in a
// tree), Git ignores the caller's GIT_* variables, and a good run pins the wrapper in the harness and its own hash in the
// graph. A private temporary worktree with a stand-in for Git, and fake runtime, checker and Node folders; no gate is run.
// Git and PowerShell runtimes are inert private fixture bytes. The real Git command line is checked through its
// injected executor; every child-process export is guarded before the production module is imported.
import test,{after} from 'node:test';
import childProcess from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {readdirSync,readFileSync,writeFileSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
const childRestores=[];let nativeAttempts=0;
for(const key of ['spawn','spawnSync','exec','execSync','execFile','execFileSync','fork']){const original=childProcess[key];childRestores.push(()=>{childProcess[key]=original;});childProcess[key]=()=>{nativeAttempts++;throw Error('No actual child is permitted in assembler fixture tests');};}
syncBuiltinESMExports();
after(()=>{for(const restore of childRestores.reverse())restore();syncBuiltinESMExports();assert.equal(nativeAttempts,0,'No Git, PowerShell, app or other child was launched');});
const {assemble,parseArgs,cleanGitEnv,gitIn,manifestOf,treeDigest,CORE}=await import('../scripts/qa-entry-context.mjs');

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');

// The fixture's files as Git would list them: '/'-joined, the ignored top-level node_modules/ left out.
function listed(W){
  const out=[];
  const rec=(dir,prefix)=>{for(const ent of readdirSync(dir,{withFileTypes:true})){
    const rel=prefix+ent.name;if(!prefix&&ent.name==='node_modules')continue;
    if(ent.isDirectory())rec(path.join(dir,ent.name),rel+'/');else out.push(rel);
  }};
  rec(W,'');return out.sort();
}
// A stand-in for Git that answers the assembler's three questions (HEAD, status, the file list) from the bytes committed
// when the fixture was made, records every call, and refuses any other question.
function fakeGit(W,committed,head,calls){
  return args=>{
    calls.push(args);const key=args.join(' ');
    if(key==='rev-parse HEAD')return head+'\n';
    const files=listed(W);
    if(key==='status --porcelain'){
      const lines=[];
      for(const [rel,bytes] of committed){if(!files.includes(rel))lines.push(' D '+rel);else if(!readFileSync(path.join(W,rel)).equals(bytes))lines.push(' M '+rel);}
      for(const rel of files)if(!committed.has(rel))lines.push('?? '+rel);
      return lines.map(line=>line+'\n').join('');
    }
    if(key==='ls-files --cached --others --exclude-standard -z')return [...new Set([...committed.keys(),...files])].sort().map(rel=>rel+'\0').join('');
    throw Error('Unexpected git call: '+key);
  };
}

async function fixture(t){
  const base=await fs.mkdtemp(path.join(os.tmpdir(),'qa-entry-'));
  t.after(()=>fs.rm(base,{recursive:true,force:true}));
  const W=path.join(base,'w'),runtime=path.join(base,'runtime'),checker=path.join(base,'checker'),nodeDir=path.join(base,'node'),run=path.join(base,'run');
  const python=Buffer.from('fake python'),ffmpeg=Buffer.from('fake ffmpeg'),ffprobe=Buffer.from('fake ffprobe');
  await fs.mkdir(path.join(W,'scripts'),{recursive:true});await fs.mkdir(path.join(W,'node_modules','dep'),{recursive:true});
  await fs.writeFile(path.join(W,'node_modules','dep','index.js'),'x');
  await fs.writeFile(path.join(W,'scripts','check-desktop.mjs'),'// gate\n');
  await fs.writeFile(path.join(W,'scripts','qa-phase-contract.mjs'),await fs.readFile(new URL('../scripts/qa-phase-contract.mjs',import.meta.url)));
  await fs.writeFile(path.join(W,'package.json'),JSON.stringify({version:'0.22.1',scripts:{check:'node scripts/check-desktop.mjs'}}));
  await fs.writeFile(path.join(W,'.gitignore'),'node_modules/\n');
  await fs.mkdir(path.join(runtime,'python'),{recursive:true});await fs.mkdir(path.join(runtime,'ffmpeg'),{recursive:true});
  await fs.writeFile(path.join(runtime,'python','python.exe'),python);await fs.writeFile(path.join(runtime,'ffmpeg','ffmpeg.exe'),ffmpeg);await fs.writeFile(path.join(runtime,'ffmpeg','ffprobe.exe'),ffprobe);
  await fs.writeFile(path.join(runtime,'ffmpeg','avcodec.dll'),'fake codec');  // pinned only by the whole tree (W10)
  const tree=await manifestOf(runtime);
  await fs.writeFile(path.join(W,'scripts','qa-runtime.json'),JSON.stringify({schema:1,python:{sha256:sha(python)},ffmpeg:{files:{'ffmpeg.exe':{sha256:sha(ffmpeg),size:ffmpeg.length},'ffprobe.exe':{sha256:sha(ffprobe),size:ffprobe.length}}},
    tree:{files:tree.files.length,sha256:treeDigest(tree)}}));
  const committed=new Map(listed(W).map(rel=>[rel,readFileSync(path.join(W,rel))])),head=sha('fixture commit').slice(0,40),calls=[];
  await fs.mkdir(checker,{recursive:true});for(const name of CORE)await fs.writeFile(path.join(checker,name),'// '+name);
  await fs.mkdir(path.join(nodeDir,'node_modules','npm','bin'),{recursive:true});await fs.writeFile(path.join(nodeDir,'node.exe'),'node');
  await fs.writeFile(path.join(nodeDir,'npm.cmd'),'npm');await fs.writeFile(path.join(nodeDir,'node_modules','npm','bin','npm-cli.js'),'cli');
  await fs.mkdir(path.join(run,'ownership'),{recursive:true});await fs.writeFile(path.join(run,'ownership','owner.txt'),'o');
  const fixtureDir=path.join(base,'fixture');await fs.mkdir(fixtureDir);await fs.writeFile(path.join(fixtureDir,'fixture.mp3'),'mp3');
  const gitRoot=path.join(base,'git'),systemRoot=path.join(base,'Windows'),powershellRoot=path.join(systemRoot,'System32','WindowsPowerShell','v1.0');
  await fs.mkdir(path.join(gitRoot,'cmd'),{recursive:true});await fs.writeFile(path.join(gitRoot,'cmd','git.exe'),'fake git');
  await fs.writeFile(path.join(gitRoot,'git-dependency.dll'),'fake git dependency');
  await fs.mkdir(powershellRoot,{recursive:true});await fs.writeFile(path.join(powershellRoot,'powershell.exe'),'fake powershell');
  await fs.writeFile(path.join(powershellRoot,'System.Management.Automation.dll'),'fake metadata runtime');
  const options={worktree:W,run,head,runtime,fixture:path.join(fixtureDir,'fixture.mp3'),checker,port:5212,'git-root':gitRoot,'powershell-root':powershellRoot};
  return {base,W,run,runtime,gitRoot,powershellRoot,systemRoot,options,committed,calls,node:path.join(nodeDir,'node.exe'),git:fakeGit(W,committed,head,calls)};
}
const quiet={log(){}};
const absent=async file=>{await assert.rejects(fs.lstat(file),{code:'ENOENT'});};

test('arguments: every path and the expected HEAD are required, absolute and exact (E5)',()=>{
  const ok=['--worktree','C:\\w','--run','C:\\r','--head','a'.repeat(40),'--runtime','C:\\q','--fixture','C:\\f.mp3','--git-root','C:\\Git','--powershell-root','C:\\Windows\\System32\\WindowsPowerShell\\v1.0','--checker','C:\\checker'];
  assert.equal(parseArgs(ok).port,5212);
  for(const key of ['--git-root','--powershell-root']){const i=ok.indexOf(key);assert.throws(()=>parseArgs(ok.slice(0,i).concat(ok.slice(i+2))),new RegExp(key+' is required'));assert.throws(()=>parseArgs(ok.map((v,j)=>j===i+1?'relative':v)),/absolute/);}
  assert.throws(()=>parseArgs(ok.slice(0,4).concat(ok.slice(6))),/--head is required/);
  assert.throws(()=>parseArgs(ok.map(v=>v==='a'.repeat(40)?'abc123':v)),/full expected commit/);
  assert.throws(()=>parseArgs(ok.map(v=>v==='C:\\r'?'relative':v)),/absolute/);
  assert.throws(()=>parseArgs([...ok,'--extra','x']),/Unknown/);
  for(const flag of ['--schema','--deadline-ms','--timeout'])assert.throws(()=>parseArgs([...ok,flag,'900001']),/Unknown/);
});

test('git ignores the caller\'s GIT_* variables and takes no optional locks (E4)',()=>{
  const env=cleanGitEnv({PATH:'p',GIT_DIR:'C:\\other',git_work_tree:'x',HOME:'h'});
  assert.deepEqual(env,{PATH:'p',HOME:'h',GIT_OPTIONAL_LOCKS:'0'});
});

test('the assembler\'s Git command: -c core.fsmonitor=false -C <worktree>, no caller GIT_DIR, hidden window (E4)',t=>{
  const before=process.env.GIT_DIR;process.env.GIT_DIR='C:\\nowhere';  // a stray GIT_DIR is not passed on
  t.after(()=>{if(before===undefined)delete process.env.GIT_DIR;else process.env.GIT_DIR=before;});
  const seen=[],run=gitIn('C:\\w',(file,args,options)=>{seen.push({file,args,options});return 'answer';});
  assert.equal(run(['rev-parse','HEAD']),'answer');
  assert.equal(seen.length,1);assert.equal(seen[0].file,'git');
  assert.deepEqual(seen[0].args,['-c','core.fsmonitor=false','-C','C:\\w','rev-parse','HEAD']);
  assert.equal(Object.keys(seen[0].options.env).some(key=>/^GIT_DIR$/i.test(key)),false);
  assert.equal(seen[0].options.env.GIT_OPTIONAL_LOCKS,'0');assert.equal(seen[0].options.windowsHide,true);
  const fixed='C:/pinned/Git/cmd/git.exe';gitIn('C:\\w',(file,args,options)=>{assert.equal(file,fixed);assert.equal(options.env.GIT_OPTIONAL_LOCKS,'0');assert.equal(options.windowsHide,true);return 'ok';},fixed)(['status','--porcelain']);
});

test('a good run pins the wrapper in the harness and the assembler in the graph (E1, E2)',async t=>{
  const f=await fixture(t);
  const result=await assemble(f.options,{node:f.node,git:f.git,...quiet});
  const C=path.join(f.run,'context'),context=JSON.parse(await fs.readFile(path.join(C,'context.json'),'utf8'));
  assert.equal(context.schema,3);assert.equal(context.deadlineMs,900000);
  assert.equal(context.source.head,f.options.head);assert.equal(context.source.dirty,'N');
  assert.equal(result.context.sha256,sha(await fs.readFile(path.join(C,'context.json'))));
  assert.equal((await fs.readFile(path.join(C,'context.json.sha256'),'utf8')).trim(),result.context.sha256);
  const source=JSON.parse(await fs.readFile(path.join(C,'source-manifest.json'),'utf8'));
  assert.deepEqual(source.files.map(item=>item.path),[...f.committed.keys()].sort(),'the snapshot is the listed files, node_modules left out');
  assert.deepEqual(f.calls,[['rev-parse','HEAD'],['status','--porcelain'],['ls-files','--cached','--others','--exclude-standard','-z'],['rev-parse','HEAD'],['status','--porcelain']],
    'HEAD and a clean tree are checked before the snapshot and again after it');
  const harness=JSON.parse(await fs.readFile(path.join(C,'harness-manifest.json'),'utf8'));
  assert.deepEqual(harness.files.map(item=>item.path),['graph.json','run-entry.sh'],'the wrapper is covered by the harness digest');
  const wrapper=await fs.readFile(path.join(C,'harness','run-entry.sh'),'utf8');
  assert.match(wrapper,new RegExp('BOOKS_QA_RUNTIME_ROOT='+"'"+f.runtime.replaceAll('\\','\\\\')+"'"));assert.match(wrapper,/--context-sha "\$\(cat "\$context.sha256"\)"/);
  const graph=JSON.parse(await fs.readFile(path.join(C,'harness','graph.json'),'utf8'));
  assert.equal(graph.assembler.sha256,sha(await fs.readFile(new URL('../scripts/qa-entry-context.mjs',import.meta.url))));
  assert.deepEqual(graph.environment,{BOOKS_QA_RUNTIME_ROOT:f.runtime,BOOKS_MP3_REAL_FIXTURE:f.options.fixture,SystemRoot:f.systemRoot,WINDIR:f.systemRoot});
  for(const [name,root] of [['git',f.gitRoot],['powershell',f.powershellRoot]]){const runtime=context.runtime.manifests.find(x=>x.name===name);assert.equal(runtime.root,root);const bytes=await fs.readFile(runtime.manifest.path);assert.equal(runtime.manifest.sha256,sha(bytes));assert.deepEqual(JSON.parse(bytes),await manifestOf(root));}
  assert.deepEqual(context.runtime.git,{name:'git',path:path.join(f.gitRoot,'cmd','git.exe'),sha256:sha('fake git')});
  assert.deepEqual(graph.metadata_hygiene.powershell,{path:path.join(f.powershellRoot,'powershell.exe'),sha256:sha('fake powershell')});
  assert.equal(graph.metadata_hygiene.system_root,f.systemRoot);assert.equal(graph.metadata_hygiene.helper,'entry-identity.mjs');
  assert.ok(wrapper.includes('export SystemRoot='+"'"+f.systemRoot+"'"));assert.ok(wrapper.includes('export WINDIR='+"'"+f.systemRoot+"'"));
  assert.equal(graph.schema,'books-entry-graph-v4');assert.equal(graph.phases.prior_node_entries,18);assert.equal(graph.phases.total_node_entries,19);
  assert.equal(graph.phases.canonical.node_entries.length,18);assert.equal(graph.phases.canonical.node_entries.includes('tests/real-shell-update.test.mjs'),false);
  assert.equal(graph.phases.native.required,true);assert.match(graph.phases.native.status,/PENDING/);
  assert.equal(graph.phases.contract.sha256,sha(await fs.readFile(new URL('../scripts/qa-phase-contract.mjs',import.meta.url))));
});

test('refusals write nothing: an existing context, a dirty tree, a wrong HEAD, a runtime that differs, a link',async t=>{
  const f=await fixture(t),C=path.join(f.run,'context'),deps={node:f.node,git:f.git,...quiet};
  await fs.mkdir(C);await assert.rejects(assemble(f.options,deps),/already exists/);await fs.rm(C,{recursive:true});
  await assert.rejects(assemble({...f.options,head:'0'.repeat(40)},deps),/HEAD is not/);await absent(C);
  await fs.writeFile(path.join(f.W,'package.json'),'{}');
  await assert.rejects(assemble(f.options,deps),/dirty/);await absent(C);
  await fs.writeFile(path.join(f.W,'package.json'),f.committed.get('package.json'));
  await fs.writeFile(path.join(f.W,'untracked.txt'),'new');
  await assert.rejects(assemble(f.options,deps),/dirty/);await absent(C);
  await fs.rm(path.join(f.W,'untracked.txt'));
  await fs.writeFile(path.join(f.runtime,'python','python.exe'),'another python');
  await assert.rejects(assemble(f.options,deps),/python.exe differs/);await absent(C);  // E3
  await fs.writeFile(path.join(f.runtime,'python','python.exe'),'fake python');
  await fs.writeFile(path.join(f.runtime,'ffmpeg','ffprobe.exe'),'fake ffprobX');
  await assert.rejects(assemble(f.options,deps),/ffprobe.exe differs/);await absent(C);
  await fs.writeFile(path.join(f.runtime,'ffmpeg','ffprobe.exe'),'fake ffprobe');
  // Senua's 0.22.1 review, W10: a codec DLL that differs, or a file added, is refused like an executable.
  await fs.writeFile(path.join(f.runtime,'ffmpeg','avcodec.dll'),'another codec');
  await assert.rejects(assemble(f.options,deps),/files differ from the runtime tree/);await absent(C);
  await fs.writeFile(path.join(f.runtime,'ffmpeg','avcodec.dll'),'fake codec');
  await fs.writeFile(path.join(f.runtime,'python','extra.pyd'),'x');
  await assert.rejects(assemble(f.options,deps),/5 files, 4 pinned/);await absent(C);
  await fs.rm(path.join(f.runtime,'python','extra.pyd'));
  await fs.symlink(path.join(f.base,'checker'),path.join(f.W,'node_modules','linked'),'junction');
  await assert.rejects(assemble(f.options,deps),/Link refused/);await absent(C);
});


test('assembler refuses a different committed phase contract before creating context',async t=>{
 const f=await fixture(t),relative='scripts/qa-phase-contract.mjs',bytes=Buffer.from('// different clean snapshot contract\n');
 await fs.writeFile(path.join(f.W,relative),bytes);f.committed.set(relative,bytes);
 await assert.rejects(assemble(f.options,{node:f.node,git:f.git,...quiet}),/QA phase contract differs/);
 await absent(path.join(f.run,'context'));
});


test('missing or mislocated metadata runtimes refuse before Git and before context writes',async t=>{
 for(const key of ['git-root','powershell-root']){const f=await fixture(t);await assert.rejects(assemble({...f.options,[key]:undefined},{node:f.node,git:f.git,...quiet}),/absolute path/);assert.deepEqual(f.calls,[]);await absent(path.join(f.run,'context'));}
 for(const item of ['git','powershell']){const f=await fixture(t),file=item==='git'?path.join(f.gitRoot,'cmd','git.exe'):path.join(f.powershellRoot,'powershell.exe');await fs.rm(file);await assert.rejects(assemble(f.options,{node:f.node,git:f.git,...quiet}),/Metadata executable missing or linked/);assert.deepEqual(f.calls,[]);await absent(path.join(f.run,'context'));}
 const f=await fixture(t);await assert.rejects(assemble({...f.options,'powershell-root':f.gitRoot},{node:f.node,git:f.git,...quiet}),/PowerShell root must match/);assert.deepEqual(f.calls,[]);await absent(path.join(f.run,'context'));
 for(const which of ['git','powershell']){const f=await fixture(t),alias=path.join(f.base,'linked-'+which);await fs.symlink(which==='git'?f.gitRoot:f.systemRoot,alias,'junction');const options={...f.options,[which==='git'?'git-root':'powershell-root']:which==='git'?alias:path.join(alias,'System32','WindowsPowerShell','v1.0')};await assert.rejects(assemble(options,{node:f.node,git:f.git,...quiet}),/Metadata runtime directory missing or linked/);assert.deepEqual(f.calls,[]);await absent(path.join(f.run,'context'));}
});

test('Git and PowerShell whole-tree drift during metadata inspection refuses before context writes',async t=>{
 for(const [which,added] of [['git',false],['powershell',false],['git',true],['powershell',true]]){
  const f=await fixture(t),root=which==='git'?f.gitRoot:f.powershellRoot;let changed=false;
  const git=args=>{if(!changed){changed=true;const file=path.join(root,added?'unexpected.dll':which==='git'?'git-dependency.dll':'System.Management.Automation.dll');writeFileSync(file,'changed metadata input');}return f.git(args);};
  await assert.rejects(assemble(f.options,{node:f.node,git,...quiet}),/Metadata runtime changed during Git inspection/);await absent(path.join(f.run,'context'));assert.equal(changed,true);
 }
});

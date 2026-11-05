import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const root='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/0260-release-20261105/r3/publisher';
const release='C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r3';
const head='1b2f81a8f6d86995e937332e0c225837d05cbc20';
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const [expected]=process.argv.slice(2),planPath=root+'/plan.json';
if(process.argv.length!==3||!/^[a-f0-9]{64}$/.test(expected||'')||sha(planPath)!==expected)throw Error('Exact reviewed publisher plan SHA required');
const plan=JSON.parse(fs.readFileSync(planPath,'utf8'));
if(plan.schema!=='books-0260-publisher-plan-v1'||plan.source_head!==head||plan.source_root!==release||plan.version!=='0.26.0'||plan.deadlineMs!==600000)throw Error('Exact publisher source/plan required');
const env=plan.environment;
for(const key of ['USERPROFILE','APPDATA','LOCALAPPDATA'])if(env[key]!==process.env[key])throw Error('Current credential configuration root changed: '+key);
for(const key of Object.keys(env))if(/TOKEN|PASSWORD|SECRET|TRACE|DEBUG|GH_CONFIG_DIR|XDG_CONFIG_HOME/.test(key))throw Error('Credential/debug override forbidden in publisher plan');
if(env.HOME!==(process.env.HOME||process.env.USERPROFILE)||env.npm_config_userconfig!==root+'/empty-user-config.txt'||env.npm_config_globalconfig!==root+'/empty-global-config.txt'||env.npm_config_cache!==root+'/npm-cache'||env.TEMP!==root+'/temp'||env.TMP!==root+'/temp'||env.GCM_INTERACTIVE!=='0'||env.GH_PROMPT_DISABLED!=='1'||env.GIT_TERMINAL_PROMPT!=='0')throw Error('Reviewed private/configuration environment changed');
function verifyTree(tree){
 const actual=[];
 function walk(dir,prefix=''){
  const ds=fs.lstatSync(dir);if(!ds.isDirectory()||ds.isSymbolicLink())throw Error('Runtime directory linked or missing');
  for(const e of fs.readdirSync(dir,{withFileTypes:true})){
   if(e.isSymbolicLink())throw Error('Linked runtime member');const file=dir+'/'+e.name,rel=prefix+e.name;
   if(e.isDirectory())walk(file,rel+'/');else{const s=fs.lstatSync(file);if(!s.isFile())throw Error('Special runtime input');actual.push({path:rel,size:s.size,sha256:sha(file)});}
  }
 }
 walk(tree.root);actual.sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);
 if(JSON.stringify(actual)!==JSON.stringify(tree.files))throw Error('Actual runtime membership/hash changed: '+tree.root);
}
const git=args=>execFileSync('C:/Program Files/Git/cmd/git.exe',['-c','core.fsmonitor=false','-C',release,...args],{encoding:'utf8',windowsHide:true,timeout:30000,env:{...env,GIT_OPTIONAL_LOCKS:'0'}}).trim();
function verify(){
 if(sha(planPath)!==expected)throw Error('Publisher plan changed');
 for(const tree of plan.runtime_trees)verifyTree(tree);
 for(const pin of plan.pins){const s=fs.lstatSync(pin.path);if(!s.isFile()||s.isSymbolicLink()||s.size!==pin.size||sha(pin.path)!==pin.sha256)throw Error('Publisher input changed: '+pin.path);}
 for(const pin of plan.source_files)if(sha(release+'/'+pin.path)!==pin.sha256)throw Error('Tracked source changed: '+pin.path);
 const pkg=JSON.parse(fs.readFileSync(release+'/package.json','utf8'));
 if(pkg.version!=='0.26.0'||pkg.scripts.release!=='node scripts/release.mjs'||Object.hasOwn(pkg.scripts,'prerelease')||Object.hasOwn(pkg.scripts,'postrelease')||pkg.workspaces||fs.existsSync(release+'/.npmrc'))throw Error('Canonical npm release lifecycle changed');
 for(const file of ['empty-user-config.txt','empty-global-config.txt']){const s=fs.lstatSync(root+'/'+file);if(!s.isFile()||s.isSymbolicLink()||s.nlink!==1||s.size!==0)throw Error('Own npm config is not ordinary/empty');}
 if(git(['rev-parse','HEAD'])!==head||git(['status','--porcelain','--untracked-files=normal']))throw Error('Expected final clean publication checkout');
}
verify();
if(fs.existsSync(root+'/launch-started.json')||fs.existsSync(root+'/release-owned.json'))throw Error('One publisher invocation only; preserve prior output');
const {runOwned}=await import(pathToFileURL(plan.helper).href);
fs.writeFileSync(root+'/launch-started.json',JSON.stringify({started_at:new Date().toISOString(),plan_sha256:expected,source_head:head,one_use:true}),{flag:'wx'});
const result=await runOwned('C:/Program Files/nodejs/node.exe',['C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js','run','release'],{cwd:release,env,timeoutMs:600000,maxBytes:16*1024*1024,koffiRoot:plan.koffi_root});
fs.writeFileSync(root+'/release-owned.json',JSON.stringify(result,null,2),{flag:'wx'});
fs.writeFileSync(root+'/release-owned.log',(result.out||'')+(result.err||''),{flag:'wx'});
verify();
console.log(JSON.stringify({ok:result.ok,code:result.code,closed:result.closed,outputComplete:result.outputComplete,native:result.native,elapsedMs:result.elapsedMs}));
console.log((result.out||'')+(result.err||''));process.exitCode=result.ok?0:1;

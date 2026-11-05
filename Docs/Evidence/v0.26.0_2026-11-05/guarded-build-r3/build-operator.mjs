import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const root='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/0260-release-20261105/r3',release='C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r3',main='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger';
const [mode,planSha]=process.argv.slice(2);if(!['stage','pack'].includes(mode))throw Error('Exact stage/pack mode required');
const sha=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const env={SystemRoot:process.env.SystemRoot,WINDIR:process.env.WINDIR,PATH:'C:/Program Files/nodejs;C:/Windows/System32',TEMP:root+'/temp',TMP:root+'/temp',HOME:root+'/profile',USERPROFILE:root+'/profile',APPDATA:root+'/profile/Roaming',LOCALAPPDATA:root+'/profile/Local',PYTHONHOME:'',PYTHONPATH:'',NODE_OPTIONS:'',NODE_PATH:'',npm_config_userconfig:root+'/empty-user-config.txt',npm_config_globalconfig:root+'/empty-global-config.txt',npm_config_audit:'false',npm_config_fund:'false',npm_config_update_notifier:'false'};
const git=args=>execFileSync('C:/Program Files/Git/cmd/git.exe',['-c','core.fsmonitor=false','-C',release,...args],{encoding:'utf8',windowsHide:true,timeout:30000,env:{...env,GIT_OPTIONAL_LOCKS:'0'}}).trim();
if(git(['rev-parse','HEAD'])!=='3932155e9f3ceac00632d2d82a4e91315f7c832f'||git(['status','--porcelain']))throw Error('Expected final clean release source');
for(const leaf of ['temp','profile/Roaming','profile/Local'])fs.mkdirSync(root+'/'+leaf,{recursive:true});
for(const name of ['empty-user-config.txt','empty-global-config.txt']){
 const file=root+'/'+name;if(mode==='stage'&&!fs.existsSync(file))fs.writeFileSync(file,'',{flag:'wx'});
 const stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==1||stat.size!==0||sha(file)!=='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')throw Error('Expected own ordinary empty npm config: '+file);
}
function verifyTree(tree){
 const actual=[];function walk(dir,prefix=''){const stat=fs.lstatSync(dir);if(!stat.isDirectory()||stat.isSymbolicLink())throw Error('Runtime directory differs');for(const entry of fs.readdirSync(dir,{withFileTypes:true})){if(entry.isSymbolicLink())throw Error('Linked runtime input');const file=dir+'/'+entry.name,rel=prefix+entry.name;if(entry.isDirectory())walk(file,rel+'/');else{const s=fs.lstatSync(file);if(!s.isFile()||s.nlink!==1)throw Error('Nonordinary runtime input');actual.push({path:rel,size:s.size,sha256:sha(file)});}}}walk(tree.root);
 actual.sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);if(JSON.stringify(actual)!==JSON.stringify(tree.files))throw Error('Actual loaded runtime tree changed: '+tree.root);
}
if(mode==='pack'){
 if(!/^[a-f0-9]{64}$/.test(planSha||'')||sha(root+'/build-plan.json')!==planSha)throw Error('Exact reviewed build plan SHA required');
 const plan=JSON.parse(fs.readFileSync(root+'/build-plan.json','utf8'));
 verifyTree(plan.ownership);verifyTree(plan.npm_tree);
 for(const pin of plan.pins)if(sha(pin.path)!==pin.sha256)throw Error('Build plan input changed: '+pin.path);
 for(const pin of plan.source_files)if(sha(release+'/'+pin.path)!==pin.sha256)throw Error('Source bytes changed: '+pin.path);
 if(plan.source_head!=='3932155e9f3ceac00632d2d82a4e91315f7c832f'||plan.version!=='0.26.0')throw Error('Build source differs');
}
const {runOwned}=await import(pathToFileURL('C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts/bounded-check.mjs').href);
const args=mode==='stage'?[root+'/stage-inputs.mjs']:['C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js','run','pack'];
const result=await runOwned('C:/Program Files/nodejs/node.exe',args,{cwd:release,env,timeoutMs:600000,maxBytes:16*1024*1024,koffiRoot:main+'/build-cache/qa-ownership/node_modules/koffi'});
fs.writeFileSync(root+'/'+mode+'-owned.json',JSON.stringify(result,null,2),{flag:'wx'});fs.writeFileSync(root+'/'+mode+'-owned.log',(result.out||'')+(result.err||''),{flag:'wx'});
if(mode==='pack'){
 const plan=JSON.parse(fs.readFileSync(root+'/build-plan.json','utf8'));
 verifyTree(plan.ownership);verifyTree(plan.npm_tree);
 for(const pin of plan.pins)if(sha(pin.path)!==pin.sha256)throw Error('Build plan pin changed during pack: '+pin.path);
 for(const pin of plan.source_files)if(sha(release+'/'+pin.path)!==pin.sha256)throw Error('Source changed during pack: '+pin.path);
 if(git(['rev-parse','HEAD'])!==plan.source_head||git(['status','--porcelain']))throw Error('Release source changed during pack');
}
console.log(JSON.stringify({mode,ok:result.ok,code:result.code,closed:result.closed,outputComplete:result.outputComplete,native:result.native,elapsedMs:result.elapsedMs}));if(mode==='pack')console.log((result.out||'')+(result.err||''));process.exitCode=result.ok?0:1;

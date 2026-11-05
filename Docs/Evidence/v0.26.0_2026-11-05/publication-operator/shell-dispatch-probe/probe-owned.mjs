import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/0260-release-20261105/r3/shell-dispatch-probe';
const original='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/0260-release-20261105/r3/publisher/plan.json';
const hash=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(hash(original)!=='e160ed17c9bb7cf7200fa7c50c82e7566dafd62503658ceedf13911856ff6ccf')throw Error('Original plan changed');
const plan=JSON.parse(fs.readFileSync(original,'utf8')),node='C:/Program Files/nodejs/node.exe',npm='C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js';
for(const file of [node,npm]){const tree=plan.runtime_trees.find(t=>file.startsWith(t.root+'/'));const pin=tree.files.find(p=>tree.root+'/'+p.path===file);if(hash(file)!==pin.sha256)throw Error('Pinned tool changed');}
const source='C:/Program Files/nodejs/node_modules/npm/node_modules/@npmcli/promise-spawn/lib/index.js';
const {runOwned}=await import(pathToFileURL(plan.helper).href),records=[];
for(const [name,comspec] of [['forward','C:/Windows/System32/cmd.exe'],['native','C:\\Windows\\System32\\cmd.exe']]){
 const dir=root+'/'+name;if(fs.existsSync(dir))throw Error('Fresh harmless probe arm required');fs.mkdirSync(dir);
 for(const leaf of ['temp','cache'])fs.mkdirSync(dir+'/'+leaf);
 for(const leaf of ['user-config.txt','global-config.txt'])fs.writeFileSync(dir+'/'+leaf,'',{flag:'wx'});
 fs.writeFileSync(dir+'/package.json',JSON.stringify({name:'private-dispatch-proof',version:'1.0.0',private:true,scripts:{probe:'node marker.cjs'}}),{flag:'wx'});
 fs.writeFileSync(dir+'/marker.cjs',"require('node:fs').writeFileSync(__dirname+'/executed.txt','PRIVATE_PROBE_EXECUTED');console.log('PRIVATE_DISPATCH_PROBE_EXECUTED');\n",{flag:'wx'});
 const env={...plan.environment,ComSpec:comspec,TEMP:dir+'/temp',TMP:dir+'/temp',npm_config_cache:dir+'/cache',npm_config_userconfig:dir+'/user-config.txt',npm_config_globalconfig:dir+'/global-config.txt'};
 const result=await runOwned(node,[npm,'run','probe'],{cwd:dir,env,timeoutMs:600000,maxBytes:1048576,koffiRoot:plan.koffi_root});
 fs.writeFileSync(dir+'/owned.json',JSON.stringify(result,null,2),{flag:'wx'});fs.writeFileSync(dir+'/owned.log',(result.out||'')+(result.err||''),{flag:'wx'});
 const marker=fs.existsSync(dir+'/executed.txt'),executed=result.out.includes('PRIVATE_DISPATCH_PROBE_EXECUTED');
 if(!result.ok||!result.closed||!result.outputComplete||!result.native?.zero||marker!==(name==='native')||executed!==marker)throw Error('Harmless discriminator did not match expected branch');
 records.push({name,ComSpec:comspec,marker,executed,code:result.code,normal_native_zero:true,elapsedMs:result.elapsedMs,owned_sha256:hash(dir+'/owned.json'),environment_diff_from_original:Object.fromEntries(Object.keys(env).filter(k=>env[k]!==plan.environment[k]).map(k=>[k,{before:plan.environment[k],after:env[k]}]))});
}
const proof={schema:'private-npm-dispatch-proof-v1',scope:'Harmless private npm probe only; NO release script, network, app, Git or user data action',node_sha256:hash(node),npm_cli_sha256:hash(npm),promise_spawn_source_sha256:hash(source),source_branch:'@npmcli/promise-spawn/lib/index.js82 cmd regex accepts backslash separators only; false branch adds POSIX -c',records};
fs.writeFileSync(root+'/proof.json',JSON.stringify(proof,null,2),{flag:'wx'});console.log(JSON.stringify(proof));

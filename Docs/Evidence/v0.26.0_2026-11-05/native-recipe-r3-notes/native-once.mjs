// Reviewed operator only. No app/native adapter is constructed by prepare/accept.
// One fresh 0.26.0 PA-1 launch, after the exact full PASS; never automatic retry.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
const hash=b=>createHash('sha256').update(b).digest('hex');
const need=(ok,why)=>{if(!ok)throw Error(why);};
const BASE='C:/Antigravity Projects/n26';
const SOURCE='C:/Antigravity Projects/q28/context/source',CONTEXT='C:/Antigravity Projects/q28/context';
const RELEASE='C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r3';
const STUDIO='C:/Antigravity Projects/Studio Illuminati';
const HELPER=STUDIO+'/.claude/skills/qa-handoff/scripts/bounded-check.mjs';
const NODE='C:/Program Files/nodejs/node.exe',OWNERSHIP='C:/Antigravity Projects/q28/ownership';
const BINDING={"version":"0.26.0","source_head":"3932155e9f3ceac00632d2d82a4e91315f7c832f","product_digest":"6e9a3f3a785eb5fe243f032d6ccc30b9352518ef1efba1739aba57501a17b5c3","build_id":"82b4dac4-0aad-453a-a013-d3486cc431eb","artifact_manifest_sha256":"8d170ee68ad1e5cccca5be024cf23aaa0893c4b12b4c8ebdfb1dbd9a4086574f","runtime_manifest_sha256":"f41e06413dee3dc1fdb2261c695baa38c8a846a02e408c690ee6d9ad08000b2e","phase_contract_sha256":"63fbc25237be6b9a548a6cb5d0d83ba53b473b86a8d00d6b265beb5fa3f00e3f"};
const FIXTURE=BASE+'/pa1-'+BINDING.build_id,PLAN=BASE+'/plan.json';
const CODE={
 "scripts/qa-phase-contract.mjs": "63fbc25237be6b9a548a6cb5d0d83ba53b473b86a8d00d6b265beb5fa3f00e3f",
 "scripts/qa-real-shell-phase.mjs": "49a0a2fae1f29b0dd0631644be168fa321df4a4689a9cf59dbc076da5e6f32af",
 "tests/real-shell-update-support.mjs": "fd3f0c9c5d0af1bbf877b089781e718092b64c6488d483ba2c925c3326975c90",
 "tests/real-shell-update.test.mjs": "0a4a48db35c05214c1ac5e9cd9cb536fc73fd3989664685f0f376975e2ee4ee2"
};
const EXPECTED_CONTEXT='3181ef027e64c0af6ce8746dd0d5ee3d1df3d78a795ec03edb9c371512abd267';
const encode=v=>Buffer.from(JSON.stringify(v));
async function write(file,bytes){await fs.writeFile(file,bytes,{flag:'wx'});return {path:file,sha256:hash(bytes),size:bytes.length};}
async function pin(file,systemDll=false){const bytes=await fs.readFile(file),s=await fs.lstat(file,{bigint:true});need(s.isFile()&&!s.isSymbolicLink()&&(s.nlink===1n||(systemDll&&s.nlink>1n)),'Nonordinary/hardlinked pin: '+file);return {path:file.replaceAll('\\','/'),sha256:hash(bytes),size:bytes.length,identity:{dev:String(s.dev),ino:String(s.ino),nlink:Number(s.nlink)}};}
async function canonical(){
 for(const [name,sha]of Object.entries(CODE))need(hash(await fs.readFile(SOURCE+'/'+name))===sha,'Canonical source changed: '+name);
 const contract=await import(pathToFileURL(SOURCE+'/scripts/qa-phase-contract.mjs').href);
 const support=await import(pathToFileURL(SOURCE+'/tests/real-shell-update-support.mjs').href);
 return {contract,support};
}
async function readPlan(sha){
 need(/^[a-f0-9]{64}$/.test(sha||''),'Exact plan SHA required');const raw=await fs.readFile(PLAN);need(hash(raw)===sha,'Plan changed');
 const p=JSON.parse(raw);need(JSON.stringify(p.binding)===JSON.stringify(BINDING)&&p.fixture_root===FIXTURE&&p.evidence_root===BASE&&p.source_root===SOURCE&&p.koffi_root===OWNERSHIP+'/node_modules/koffi'&&!p.recovery,'Exact fresh candidate plan required');
 const {contract,support}=await canonical();support.validatePlan(p,JSON.parse(await support.readPin(p.authority)));
 need(p.operator.sha256===await selfHash()&&p.operator.path===fileURLToPath(import.meta.url).replaceAll('\\','/'),'Operator differs');
 await support.readPin(p.release_full_receipt);fullPass(await fs.readFile(p.release_full_receipt.path,'utf8'));
 return {p,contract,support};
}
function fullPass(text){
 const receipts=text.split(/\r?\n/).filter(line=>line.startsWith('Entry-check receipt v2:'));
 need(receipts.length===1,'One exact original full receipt required');const line=receipts[0];
 need(line.startsWith('Entry-check receipt v2: books-arranger v0.26.0 @ '+BINDING.source_head+' (dirty: N) ')&&/ — .*\bcheck pass,/.test(line)&&/; personal-folders clean(?: \((?:1 subfolder note|(?:[2-9]|[1-9]\d+) subfolder notes)\))?$/.test(line),'Exact clean full PASS required');
}
const selfHash=async()=>hash(await fs.readFile(fileURLToPath(import.meta.url)));
async function prepare(receiptPath,receiptSha){
 need(/^[a-f0-9]{64}$/.test(receiptSha||''),'Exact full receipt SHA required');const receipt=await pin(receiptPath);need(receipt.sha256===receiptSha,'Full receipt differs');fullPass(await fs.readFile(receiptPath,'utf8'));
 const {contract,support}=await canonical();const contextRaw=await fs.readFile(CONTEXT+'/context.json');need(hash(contextRaw)===EXPECTED_CONTEXT,'Full context changed');const c=JSON.parse(contextRaw);
 need(c.source.head===BINDING.source_head&&c.source.dirty==='N','Full context source differs');
 const manifest=await pin(RELEASE+'/dist/release-artifacts.json');need(manifest.sha256===BINDING.artifact_manifest_sha256,'Built artifact changed');const m=JSON.parse(await fs.readFile(manifest.path));
 need(m.build_id===BINDING.build_id&&m.product_digest===BINDING.product_digest&&m.source_head===BINDING.source_head&&hash(JSON.stringify(m.runtime))===BINDING.runtime_manifest_sha256&&m.payload?.verified===true&&m.payload.installer_equivalent===true,'Built candidate identity differs');
 const inputs=[manifest,await pin(RELEASE+'/build-cache/runtime-pointer.json'),await pin(HELPER),await pin(path.dirname(HELPER)+'/bounded-child.mjs'),await pin(NODE),await pin(fileURLToPath(import.meta.url)),receipt];
 need(inputs[1].sha256==='fe93797d34dece7d0bef2426f9e6bffa028ba78b0be5c7e418200c3ce041ca77','Runtime pointer changed');
 need(inputs[2].sha256==='89ecbd30698cae696ba52d677f31bfaa505c87227c22f85e0bb6a2103475fcbc'&&inputs[3].sha256==='240a6a96a32f08989439387d5d6ab75d17e1bcf243863d31d2ff7287f68d1e42'&&inputs[4].sha256==='14319838b3f355e0398c13569a90270bce4fc68f25189f58c59b03dadae0e6d5','Reviewed owner/Node changed');
 for(const name of ['kernel32.dll','advapi32.dll','ntdll.dll','user32.dll','iphlpapi.dll'])inputs.push(await pin('C:/Windows/System32/'+name,true));
 for(const name of Object.keys(CODE))inputs.push(await pin(SOURCE+'/'+name));
 inputs.push(await pin(CONTEXT+'/context.json'));
 const trees=[];
 for(const [root,manifestPath,sha]of [[SOURCE,CONTEXT+'/source-manifest.json',c.source.manifest.sha256],['C:/Program Files/nodejs',CONTEXT+'/runtime-node-installation.json','9baa25ddc8f3d43d5f7ac8f765f52e6525b12904706f3c94cf7e7bf2b09395ca'],[OWNERSHIP,CONTEXT+'/runtime-ownership.json','122eca8f1ad057bd86867f8e302c60fcaa5b6dba5ff4e660cfd860cf40769617']]){
  const ref=await pin(manifestPath);need(ref.sha256===sha,'Input inventory changed');inputs.push(ref);const listed=JSON.parse(await fs.readFile(manifestPath)).files,files={};
  for(const item of listed){need(typeof item.path==='string'&&!item.path.includes('..')&&!item.path.includes('\\')&&!item.path.includes(':')&&!path.isAbsolute(item.path),'Unsafe inventory member');const stat=await support.ordinary(root+'/'+item.path,{file:true});files[item.path]={size:stat.size,sha256:item.sha256};}
  trees.push({root,files});
 }
 const koffi={};for(const [name,ref]of Object.entries(trees[2].files))if(name.startsWith('node_modules/koffi/'))koffi[name.slice('node_modules/koffi/'.length)]=ref;
 need(Object.keys(koffi).length>0,'Koffi inventory absent');trees.push({root:OWNERSHIP+'/node_modules/koffi',files:koffi});
 await support.ordinary(path.dirname(BASE));await fs.mkdir(BASE); // Must be fresh; never adopt/remove existing output.
 const authority={"schema":"books-native-qa-authority-v1","binding":BINDING,"approved_by":"Sergei","decision_ref":"Current user message in this release chat, client date 2026-11-05; exact message sent time unavailable","decision_text":"Current user message, quoted verbatim: \"Add the four Universe options too, then have Sully release the next version with all these fixes. Don't stop until it's released unless there's a serious stopper.\" Jane and Senua interpret the existing canonical private PA-1 as necessary release workflow within that request: one hidden private copied app, invalid fake installer refusal, deletion of the exact newly created own HKCU tray numeric leaf, and ONE added 8-byte numeric history reference while preserving every preexisting UIOrderList byte. These enumerated registry effects are producer/reviewer scope interpretation, not words attributed to Sergei. No focus, installed app changes, live library or Z: access. No old 0.25 authority or proof is reused. approved_at records actual new preparation UTC, not the unavailable user-message sent time.","approved_at":new Date().toISOString(),"effects":{"hidden_private_app":true,"invalid_installer_attempt":true,"own_new_leaf_delete":true,"leave_numeric_history_reference":true,"ui_order_list_write":false}};
 const authorityRef=await write(BASE+'/authority.json',encode(authority));
 const p={schema:'books-real-shell-plan-v1',binding:BINDING,case:contract.NATIVE_CASE,deadlineMs:600000,phase_contract_sha256:BINDING.phase_contract_sha256,fixture_root:FIXTURE,evidence_root:BASE,source_root:SOURCE,koffi_root:OWNERSHIP+'/node_modules/koffi',authority:authorityRef,node:inputs[4],helper:inputs[2],inputs,trees,payload:{root:RELEASE+'/dist/'+m.unpacked,manifest},environment:{SystemRoot:'C:/Windows',WINDIR:'C:/Windows',PATH:'C:/Program Files/nodejs;C:/Windows/System32',TEMP:FIXTURE+'/temp',TMP:FIXTURE+'/temp',USERPROFILE:FIXTURE+'/home',APPDATA:FIXTURE+'/home/Roaming',LOCALAPPDATA:FIXTURE+'/home/Local'},expected_tray_types:{ExecutablePath:1,IconSnapshot:3,InitialTooltip:1,UID:4},operator:inputs[5],release_full_receipt:receipt};
 support.validatePlan(p,authority);const ref=await write(PLAN,encode(p));console.log(JSON.stringify({prepared:true,plan:ref,self_sha256:await selfHash(),binding:BINDING}));
}
async function run(sha){
 const {p,support}=await readPlan(sha);await support.verifyInputs(p); // Pure preflight before the one-use marker.
 const started=new Date().toISOString();await write(BASE+'/launch-started.json',encode({started_at:started,plan_sha256:sha,binding:BINDING,one_use:true}));
 const result=await new Promise(resolve=>execFile(NODE,[SOURCE+'/scripts/qa-real-shell-phase.mjs','--run',PLAN,sha],{cwd:SOURCE,env:p.environment,windowsHide:true,encoding:'buffer',timeout:600000,maxBuffer:32*1024*1024},(error,stdout,stderr)=>resolve({error,stdout,stderr})));
 const out=Buffer.from(result.stdout),err=Buffer.from(result.stderr);await write(BASE+'/outer-stdout.log',out);await write(BASE+'/outer-stderr.log',err);
 const optional=async name=>{try{return hash(await fs.readFile(BASE+'/'+name));}catch(e){if(e.code==='ENOENT')return null;throw e;}};
 const cb={callback_received:true,error:result.error?{message:result.error.message,code:result.error.code,signal:result.error.signal,killed:result.error.killed}:null,start_write_error:null,write_errors:[],plan_sha256:sha,binding_sha256:hash(encode(BINDING)),owned_sha256:await optional('owned.json'),controller_owned_sha256:await optional('controller-owned.json'),stdout_sha256:hash(out),stdout_bytes:out.length,stderr_sha256:hash(err),stderr_bytes:err.length,started_at:started,received_at:new Date().toISOString(),pid:process.pid};
 await write(BASE+'/callback.json',encode(cb));process.stdout.write(out);process.stderr.write(err);if(result.error)process.exitCode=1;
}
async function accept(sha){
 const {p,contract}=await readPlan(sha);const phase=await import(pathToFileURL(SOURCE+'/scripts/qa-real-shell-phase.mjs').href),raw={};
 for(const role of contract.NATIVE_ROLES)raw[role]=await fs.readFile(BASE+'/'+role.replaceAll('_','-')+(['stdout','stderr','controller_stdout','controller_stderr'].includes(role)?'.log':'.json'));
 const callback=JSON.parse(raw.callback);need((await fs.readFile(BASE+'/outer-stdout.log')).equals(raw.controller_stdout)&&(await fs.readFile(BASE+'/outer-stderr.log')).equals(raw.controller_stderr),'Actual callback streams differ from original controller');
 need(callback.plan_sha256===sha,'Actual callback plan differs');const summary=phase.evidenceSummary(BINDING,raw);contract.validateNativeEvidence(summary,raw,BINDING);
 await fs.mkdir(BASE+'/accepted');await fs.mkdir(BASE+'/accepted/BooksArranger_NativeQA_v0.26.0_Evidence');
 for(const role of contract.NATIVE_ROLES)await write(BASE+'/accepted/'+summary.records[role].path.replace(/^Docs\//,''),raw[role]);
 const ref=await write(BASE+'/accepted/BooksArranger_NativeQA_v0.26.0.json',Buffer.from(JSON.stringify(summary,null,2)+'\n'));
 console.log(JSON.stringify({accepted:true,summary:ref,binding:p.binding}));
}
const [mode,expectedSelf,...args]=process.argv.slice(2);
try{
 need(/^[a-f0-9]{64}$/.test(expectedSelf||'')&&expectedSelf===await selfHash(),'Reviewed exact operator SHA required');
 if(mode==='prepare'&&args.length===2)await prepare(...args);
 else if(mode==='run'&&args.length===1)await run(...args);
 else if(mode==='accept'&&args.length===1)await accept(...args);
 else throw Error('Use prepare <selfSHA> <original-full-receipt> <receiptSHA>, run/accept <selfSHA> <planSHA>');
}catch(error){console.error(error.stack||String(error));process.exitCode=1;}

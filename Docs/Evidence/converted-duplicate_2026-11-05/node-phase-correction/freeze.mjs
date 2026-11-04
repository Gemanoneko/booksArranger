import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const source='C:/Antigravity Projects/Worktrees/Books Arranger/frontend-fixtures-025-20261105';
const main='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger';
const destination=path.join(main,'Docs/Evidence/converted-duplicate_2026-11-05/node-phase-correction');
const baseline='0ec4971169a70d57a407ae1a9ef6bf96227724d4',name='tests/test_precheck_frontend.js';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const git=args=>{const result=spawnSync('git',['-C',source,...args],{windowsHide:true});if(result.status!==0)throw Error(result.stderr.toString());return result.stdout;};
if(git(['status','--short']).toString().trim()!=='M '+name)throw Error('Unexpected dirty checkout path');
git(['-c','core.whitespace=cr-at-eol','diff','--check','--',name]);
const raw=fs.readFileSync(path.join(source,name)),old=git(['show',baseline+':'+name]),patch=git(['diff',baseline,'--',name]);
fs.writeFileSync(path.join(root,'source.patch'),patch,{flag:'wx'});
const phase=JSON.parse(fs.readFileSync(path.join(root,'phase-result.json'))),owned=JSON.parse(fs.readFileSync(path.join(root,'complete-node-phase.json')));
if(!phase.ok||phase.syntaxRan!==11||phase.nodeEntriesRan!==18||phase.nodeCases!==242||phase.frontendScriptsRan!==39||phase.commandsRan!==51||!phase.sourceInputsUnchanged)throw Error('Incomplete Node phase');
if(!owned.ok||owned.code!==0||!owned.closed||!owned.outputComplete||!owned.native?.complete||!owned.native?.zero||owned.forced||owned.timedOut)throw Error('Incomplete owned closure');
fs.mkdirSync(destination);
const evidence=[];
for(const item of fs.readdirSync(root,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){
 if(!item.isFile())continue;const file=path.join(root,item.name),bytes=fs.readFileSync(file);fs.copyFileSync(file,path.join(destination,item.name),fs.constants.COPYFILE_EXCL);evidence.push({path:item.name,bytes:bytes.length,sha256:hash(bytes)});
}
const lf=bytes=>Buffer.from(bytes.toString().replaceAll('\r\n','\n'));
const summary={baseline,files:[{path:name,bytes:raw.length,sha256:hash(raw),lf_sha256:hash(lf(raw)),baseline_lf_sha256:hash(lf(old))}],patch_sha256:hash(patch),
 change:'One stale expected status string only: unsupported M4B feature refusal now expects the user-approved feature-specific label. No runtime or mock change; legacy singleMP3 replacement copy retained.',
 authority:'Committed Docs/BooksArranger_ConvertedDuplicate_UX_2026-11-04.md media addendum, table feature row and feature-only filter paragraph (lines78/83). Fixture stale(s5,{group:unsupported}) is a current unsupported-feature row after precheck; no invalid-container or failedMP3 proof is inferred.',
 results:{baseline:'Exact precheck old label failure reproduced in owned285.0311ms/nativezero.',corrected:'The unchanged precheck selector passed as one of all39 canonical frontend scripts.',complete_phase:{syntax:11,node_entries:18,node_cases:242,node_failed:0,node_skipped:0,node_cancelled:0,frontend_scripts:39,commands:51,owned_elapsed_ms:owned.elapsedMs,source_inputs_unchanged:true,normal_native_zero:true}},
 graph:'Literal syntax list and sorted test_*.js discovery taken from canonical scripts/check-desktop.mjs; fixed Node entry list imported from scripts/qa-phase-contract.mjs and validated by phaseAccounting. PA1_ENTRY explicitly excluded. All51commands executed even if an earlier command would fail; full canonical check/Python/native phase not invoked.',
 environment:'Private TEMP/profile/fixture paths, reviewed runOwned600000 helper, windowsHide children, pure Node/DOM doubles. No Electron/native shell/Explorer/live/Z access. Current checkout raw lock74c5e770... differs from LF pin01d87... by known checkout endings; no Node failure and no pin/graph edit.',
 evidence};
fs.writeFileSync(path.join(destination,'summary.json'),JSON.stringify(summary,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({destination,summary_sha256:hash(fs.readFileSync(path.join(destination,'summary.json'))),patch_sha256:hash(patch),file:summary.files[0],evidence_files:evidence.length+1}));

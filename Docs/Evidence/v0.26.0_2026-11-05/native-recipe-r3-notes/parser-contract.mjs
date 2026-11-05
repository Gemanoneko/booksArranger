// Synthetic pure unit inputs only. This neither creates a PA-1 plan/authority nor
// constructs an adapter, imports the operator as a CLI, or emits a QA PASS receipt.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const [operator,expected]=process.argv.slice(2),hash=b=>createHash('sha256').update(b).digest('hex');
const bytes=fs.readFileSync(operator);assert.equal(hash(bytes),expected);
const text=bytes.toString('utf8'),binding=JSON.parse(/const BINDING=(\{[^\n]+\});/.exec(text)[1]);
const contextPath='C:/Antigravity Projects/q28/context/context.json',contextBytes=fs.readFileSync(contextPath);
assert.equal(hash(contextBytes),'3181ef027e64c0af6ce8746dd0d5ee3d1df3d78a795ec03edb9c371512abd267');
const context=JSON.parse(contextBytes),checker='C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts';
for(const pin of context.tooling.files)assert.equal(hash(fs.readFileSync(checker+'/'+pin.path)),pin.sha256);
const {receipt}=await import(pathToFileURL(checker+'/entry-main.mjs').href);
const {personalFolderVerdict}=await import(pathToFileURL(checker+'/entry-identity.mjs').href);
const contractPath=context.source.root.replaceAll('\\','/')+'/scripts/qa-phase-contract.mjs';
assert.equal(hash(fs.readFileSync(contractPath)),binding.phase_contract_sha256);
const {normalOwned}=await import(pathToFileURL(contractPath).href);
const identity={sourceDigest:'1'.repeat(64),harnessDigest:'2'.repeat(64),runtimeDigest:'3'.repeat(64),toolingDigest:'4'.repeat(64)};
const results={'pre-qa':'n/a','post-build':'n/a','check-electron':'n/a',check:'pass','test:smoke':'n/a'};
const personal=(count=0)=>({clean:true,notes:Array.from({length:count},()=>({})),added:[],changed:[],removed:[],errors:[],allowed:[]});
const make=(p=personal(),overrides={})=>receipt({name:'books-arranger',version:overrides.version||binding.version},{source:{head:overrides.head||binding.source_head,dirty:overrides.dirty||'N'}},identity,{...results,...overrides.results},p);
const start=text.indexOf('function fullPass('),end=text.indexOf('const selfHash=',start);assert(start>=0&&end>start);
const box={BINDING:binding,need:(ok,why)=>{if(!ok)throw Error(why);}};vm.createContext(box);vm.runInContext(text.slice(start,end),box);
const cases=[];
function test(name,fn){try{fn();cases.push({name,pass:true});}catch(error){cases.push({name,pass:false,error:error.message});}}
for(const n of [0,1,2,10,21])test('canonical clean notes='+n,()=>{const p=personal(n);assert.equal(p.clean,true);assert.match(personalFolderVerdict(p),/^clean(?: \(\d+ subfolder notes?\))?$/);assert.doesNotThrow(()=>box.fullPass(make(p)));});
test('check fail refused',()=>assert.throws(()=>box.fullPass(make(personal(),{results:{check:'fail (owned check)'}}))));
test('listed change refused',()=>assert.throws(()=>box.fullPass(make({...personal(),clean:false,changed:[{}]}))));
test('NOT CHECKED refused',()=>assert.throws(()=>box.fullPass(make({notChecked:'Synthetic pure unit unavailable comparison'}))));
test('missing personal result refused',()=>assert.throws(()=>box.fullPass(make(null))));
test('wrong source refused',()=>assert.throws(()=>box.fullPass(make(personal(),{head:'0'.repeat(40)}))));
test('wrong version refused',()=>assert.throws(()=>box.fullPass(make(personal(),{version:'0.26.1'}))));
test('dirty source refused',()=>assert.throws(()=>box.fullPass(make(personal(),{dirty:'Y'}))));
test('multiple receipts refused',()=>assert.throws(()=>box.fullPass(make()+'\n'+make())));
test('missing receipt refused',()=>assert.throws(()=>box.fullPass('No receipt')));
for(const suffix of ['clean (0 subfolder notes)','clean (01 subfolder note)','clean (1 subfolder notes)','clean (2 subfolder note)','clean (1 new)','clean (2 subfolder notes) extra'])
 test('altered suffix refused: '+suffix,()=>assert.throws(()=>box.fullPass(make().replace(/personal-folders .*/,'personal-folders '+suffix))));
const contextGuard="need(hash(contextRaw)===EXPECTED_CONTEXT,'Full context changed');";
assert(text.includes(contextGuard));
const expectedContext=/const EXPECTED_CONTEXT='([a-f0-9]{64})';/.exec(text)[1];
test('actual context hash accepted by unchanged guard',()=>assert.doesNotThrow(()=>vm.runInNewContext(contextGuard,{need:box.need,hash,contextRaw:contextBytes,EXPECTED_CONTEXT:expectedContext})));
test('changed context hash refused by unchanged guard',()=>assert.throws(()=>vm.runInNewContext(contextGuard,{need:box.need,hash,contextRaw:Buffer.concat([contextBytes,Buffer.from('changed')]),EXPECTED_CONTEXT:expectedContext}),/Full context changed/));
test('failed native owner refused by unchanged pure contract',()=>assert.throws(()=>normalOwned({ok:false}),/normal owned result/));
// Exercise the actual unchanged plan binding guard with in-memory reads only.
// Wrong build is not a receipt field; it must refuse in readPlan before canonical
// input imports, authority/plan writes, an adapter, or any app/native construction.
const planStart=text.indexOf('async function readPlan('),planEnd=text.indexOf(' const {contract,support}=await canonical();',planStart),base='C:/Antigravity Projects/n26';
assert(planStart>=0&&planEnd>planStart);
for(const field of ['build_id','source_head']){
 const bad={schema:'books-real-shell-plan-v1',binding:{...binding,[field]:field==='build_id'?'00000000-0000-4000-8000-000000000000':'0'.repeat(40)},fixture_root:base+'/pa1-'+binding.build_id,evidence_root:base,source_root:context.source.root.replaceAll('\\','/'),koffi_root:'C:/Antigravity Projects/q28/ownership/node_modules/koffi'};
 const raw=Buffer.from(JSON.stringify(bad)),fake={BINDING:binding,BASE:base,FIXTURE:base+'/pa1-'+binding.build_id,PLAN:base+'/plan.json',SOURCE:context.source.root.replaceAll('\\','/'),OWNERSHIP:'C:/Antigravity Projects/q28/ownership',fs:{readFile:async()=>raw},hash,need:box.need,canonical:async()=>{throw Error('Binding guard was bypassed');}};
 // Compile the exact prefix through the binding guard, stopping before imports.
 // The later real module path uses import.meta and is outside this pure unit.
 vm.createContext(fake);vm.runInContext(text.slice(planStart,planEnd)+'\n}',fake);
 try{await assert.rejects(fake.readPlan(hash(raw)),/Exact fresh candidate plan required/);cases.push({name:'plan '+field+' mismatch refused before input imports',pass:true});}
 catch(error){cases.push({name:'plan '+field+' mismatch refused before input imports',pass:false,error:error.message});}
}
console.log(JSON.stringify({schema:'native-receipt-parser-unit-v1',scope:'SYNTHETIC PURE UNIT INPUTS ONLY; NOT ACTUAL QA RECEIPTS OR NATIVE PREPARATION',operator,operator_sha256:expected,tests:cases.length,passed:cases.filter(x=>x.pass).length,failed:cases.filter(x=>!x.pass),no_native_preparation:true}));
process.exitCode=cases.every(x=>x.pass)?0:1;

/** PURE fake controls only. Import never invokes fixture, FFI or a child. Written UNRUN. */
import assert from 'node:assert/strict';
import path from 'node:path';
import {namespaceFixture} from './native-fixture-controller.mjs';
const root='C:/fixture',container=path.win32.join(root,'namespace-case'),branch=path.win32.join(container,'branch'),leaf=path.win32.join(branch,'leaf');
const norm=p=>path.win32.resolve(p).toLowerCase();
function setup(options={}){
 const calls=[],records=[];let made=0,phaseClosed=false;
 const facts=(different=false)=>({volume64:'1',file_id128:(different?'2':'1').repeat(32),creation_ticks:different?'2':'1',attrs:16});
 const proof=[root,container,branch,leaf].map(p=>({path:p,facts:facts()}));if(options.missingProof)proof.pop();if(options.malformedProof)proof[1].facts.creation_ticks='0';
 const io={parents:new Map([[norm(root),{}]]),writeRecord(p,r){calls.push('diagnostic');records.push(r);if(options.captureFails)throw Error('capture failure');return {};}};
 if(options.cachedSubtree)io.parents.set(norm(container),{});
 const makeLeases=()=>{
  const phase=made++===0;
  if(phase)return {handles:[1,2,3,4],ancestry(){calls.push('phase-ancestry');},createDirectory(p,n){calls.push('create-'+n);},directoryProof(){return proof;},teardown(){calls.push('close-container-and-phase');if(options.phaseCloseFails)throw Error('phase close failure');this.handles=[];phaseClosed=true;}};
  return {handles:[5],ancestry(){calls.push('replacement-ancestry');if(options.openFails)throw Error('replacement open failure');},retain(p,d){assert.equal(norm(p),norm(branch));assert.equal(d,true);calls.push('replacement-retain');return 5;},directoryIdentity(){calls.push('replacement-facts');const f=facts(!options.sameIdentity);if(options.badReplacement)f.attrs=1024;return f;},teardown(){calls.push('replacement-close');if(options.replacementCloseFails)throw Error('replacement close failure');this.handles=[];}};
 };
 const fsOps={renameSync(p,q){assert.equal(norm(p),norm(branch));if(!phaseClosed){calls.push('held-rename');if(options.heldAllowed)return;const e=Error('held denied');e.code=options.badHeldError?'ENOENT':'EBUSY';throw e;}calls.push('unheld-rename');assert.equal(norm(q),norm(path.win32.join(container,'branch-original')));if(options.unheldBusy){const e=Error('unheld busy');e.code='EBUSY';throw e;}},mkdirSync(p){assert.equal(norm(p),norm(branch));assert.equal(phaseClosed,true);calls.push('replacement-mkdir');}};
 return {calls,records,io,run:()=>namespaceFixture({io,fixtureRoot:root,deadline:600000,makeLeases,fsOps})};
}
export function namespaceFixtureChecks(){let passed=0;
 const positive=setup(),result=positive.run();assert.equal(result.replaced_ancestor_refused,true);assert.equal(result.phase_checked_close,true);assert.equal(result.phase_handle_count,4);assert.deepEqual(positive.calls,['phase-ancestry','create-namespace-case','create-branch','create-leaf','held-rename','close-container-and-phase','unheld-rename','replacement-mkdir','replacement-ancestry','replacement-retain','replacement-facts','replacement-close']);assert.equal(positive.records.length,0);passed++;
 assert.deepEqual(result.proof.map(x=>norm(x.path)),[root,container,branch,leaf].map(norm));assert.equal(positive.io.parents.has(norm(container)),false);passed++;
 const controls=[['cachedSubtree','Long-lived IO acquired'],['phaseCloseFails','phase close failure'],['missingProof','Incomplete original namespace proof'],['malformedProof','Original creation-owned'],['badHeldError','held denied'],['heldAllowed','Held native directory allowed'],['unheldBusy','unheld busy'],['openFails','replacement open failure'],['sameIdentity','Replacement branch retained original'],['badReplacement','Original creation-owned'],['replacementCloseFails','replacement close failure']];
 for(const [option,message] of controls){const f=setup({[option]:true});assert.throws(f.run,new RegExp(message));assert.equal(f.records.length,1);assert.equal(f.records[0].authoritative,false);if(['cachedSubtree','phaseCloseFails','missingProof','malformedProof','badHeldError','heldAllowed'].includes(option))assert.equal(f.calls.includes('unheld-rename'),false);if(option==='unheldBusy')assert.equal(f.calls.includes('replacement-mkdir'),false);if(option==='openFails')assert.equal(f.calls.includes('replacement-facts'),false);passed++;}
 const logFail=setup({unheldBusy:true,captureFails:true});assert.throws(logFail.run,AggregateError);assert.equal(logFail.records.length,1);passed++;
 const huge=setup();assert.throws(()=>namespaceFixture({io:huge.io,fixtureRoot:'C:/'+('x'.repeat(250)),deadline:600000,makeLeases(){throw Error('must not acquire');},fsOps:{}}),/Namespace ordinary path bound/);assert.equal(huge.records.length,1);passed++;
 const busy=setup({unheldBusy:true});assert.throws(busy.run,/unheld busy/);assert.equal(busy.records[0].phase_teardown_returned,true);assert.equal(busy.records[0].stage,'unheld-rename');assert.equal(busy.records[0].error.code,'EBUSY');assert.equal(busy.records[0].original_proof.length,4);assert.equal(busy.calls.filter(x=>x==='unheld-rename').length,1);passed++;
 return {passed,native_execution:false,new_processes:0,authority:false};
}

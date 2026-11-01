// Pure test process: forbid native execution, network and account/credential access
// before importing any release implementation. Fixtures below are inert data only.
import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import childProcess from 'node:child_process';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import tls from 'node:tls';
import dns from 'node:dns';
import dgram from 'node:dgram';
import os from 'node:os';
import workers from 'node:worker_threads';
import {syncBuiltinESMExports} from 'node:module';
const nativeAttempts=[], restores=[];
function forbid(object,key,label=key){
 if(typeof object[key]!=='function')return;
 const original=object[key];object[key]=function(){nativeAttempts.push(label);throw Error('Forbidden native/network/credential API: '+label);};
 restores.push(()=>{object[key]=original;});
}
for(const key of ['spawn','spawnSync','exec','execSync','execFile','execFileSync','fork'])forbid(childProcess,key,'child_process.'+key);
for(const [object,keys,label] of [[http,['request','get','createServer'],'http'],[https,['request','get','createServer'],'https'],[net,['connect','createConnection','createServer'],'net'],[tls,['connect','createServer'],'tls'],[dgram,['createSocket'],'dgram'],[os,['userInfo'],'os']])for(const key of keys)forbid(object,key,label+'.'+key);
for(const key of Object.keys(dns))if(/^(lookup|resolve|reverse)/.test(key))forbid(dns,key,'dns.'+key);
for(const key of Object.keys(dns.promises))if(/^(lookup|resolve|reverse)/.test(key))forbid(dns.promises,key,'dns.promises.'+key);
forbid(childProcess.ChildProcess.prototype,'spawn','ChildProcess.spawn');
forbid(net.Socket.prototype,'connect','Socket.connect');
forbid(http.Agent.prototype,'createConnection','http.Agent.createConnection');
forbid(https.Agent.prototype,'createConnection','https.Agent.createConnection');
forbid(workers,'Worker','worker_threads.Worker');
for(const key of ['fetch','WebSocket','EventSource'])forbid(globalThis,key,'global.'+key);
forbid(process,'dlopen','process.dlopen');
syncBuiltinESMExports();
after(()=>{for(const restore of restores.reverse())restore();syncBuiltinESMExports();assert.deepEqual(nativeAttempts,[],'the suite must attempt zero native/network/credential calls');});
const { acceptanceIndex, packageContract, newer, reportPin, reportManifest, productTree, artifactContract, remoteArtifacts, releasesToPrune, requiresNativeQa, nativeEvidencePath, nativeEvidenceReportHash, nativeRecordReferences, validateNativeEvidence } = await import('../scripts/release-contract.mjs');
const {PA1_ASSERTIONS,NATIVE_CASE,NATIVE_ROLES,phaseAccounting,CANONICAL_NODE_ENTRIES,PA1_ENTRY}=await import('../scripts/qa-phase-contract.mjs');
const hex='a'.repeat(64), pin='b'.repeat(40), id='d9ee38b0-6d35-4a5e-8cc5-bba1c08a91f4';
const names=['Books-Arranger-Setup-0.16.0.exe','Books-Arranger-Setup-0.16.0.exe.blockmap','latest.yml'];
const manifest=()=>({schema:'books-desktop-artifacts-v1',version:'0.16.0',product_digest:hex,source_head:pin,build_id:id,unpacked:'builds/'+id+'/win-unpacked',payload:{backend_version:'0.16.0',shell_version:'0.16.0',verified:true,installer_equivalent:true},artifacts:names.map(name=>({path:'builds/'+id+'/'+name,size:123,sha256:hex}))});
test('version and package lock/publisher must be exact',()=>{
  assert.equal(newer('0.16.0','0.15.0'),true); assert.equal(newer('0.16.0','0.16.0'),false); assert.throws(()=>newer('00.16.0','0.15.0'));
  const pkg={version:'0.16.0',build:{directories:{output:'dist'},publish:{provider:'github',owner:'Gemanoneko',repo:'booksArranger',releaseType:'release'}}},lock={version:'0.16.0',packages:{'':{version:'0.16.0'}}};
  packageContract(pkg,lock); lock.packages[''].version='0.15.0'; assert.throws(()=>packageContract(pkg,lock));
});
test('report verdict/source/manifest are unambiguous, no approval inference',()=>{
 const qa='**Verdict:** GO\nRelease source commit: '+pin+'\nRelease artifact manifest SHA256: '+hex+'\n';
 assert.equal(reportPin(qa,'qa'),pin); assert.equal(reportManifest(qa),hex);
 assert.throws(()=>reportPin(qa+'**Verdict:** NO-GO\n','qa'));assert.throws(()=>reportPin(qa.replace('GO','NO-GO'),'qa'));
 assert.throws(()=>reportPin('**Verdict:** GO\n','qa'));assert.throws(()=>reportManifest(qa+'Release artifact manifest SHA256: '+hex+'\n'));
});
test('product digest permits final docs only and catches dependency/code/config drift',()=>{
 const entries=[{mode:'100644',object:pin,name:'desktop/main.js'},{mode:'100644',object:pin,name:'Docs/QA.md'}];
 const hash=productTree(entries);entries[1].object='c'.repeat(40);assert.equal(productTree(entries),hash);entries[0].object='c'.repeat(40);assert.notEqual(productTree(entries),hash);
});
test('artifact gate refuses traversal, duplicates, stale version or absent payload proof',()=>{
 const m=manifest(), expected={version:'0.16.0',productTree:hex};assert.equal(artifactContract(m,expected).length,3);
 for(const change of [m=>m.artifacts[0].path='../../victim.exe',m=>m.artifacts.push(m.artifacts[0]),m=>m.payload.backend_version='0.15.0',m=>m.payload.installer_equivalent=false,m=>m.product_digest='c'.repeat(64)]){const bad=manifest();change(bad);assert.throws(()=>artifactContract(bad,expected));}
});
test('remote receipt requires exact uploaded names/sizes/digests and stable tag',()=>{
 const m=manifest(),release={tag_name:'v0.16.0',draft:false,prerelease:false,assets:names.map(name=>({name,state:'uploaded',size:123,digest:'sha256:'+hex}))};remoteArtifacts(release,m,'v0.16.0',pin);
 release.assets[1].digest='sha256:'+'c'.repeat(64);assert.throws(()=>remoteArtifacts(release,m,'v0.16.0',pin));release.assets[1].digest='sha256:'+hex;release.draft=true;assert.throws(()=>remoteArtifacts(release,m,'v0.16.0',pin));
});
test('keep four is bounded and cannot prune the release just published',()=>{
 const rs=Array.from({length:6},(_,i)=>({id:i+1,tag_name:'v0.'+(20-i)+'.0',created_at:new Date(2026,9,13-i).toISOString()}));
 assert.deepEqual(releasesToPrune(rs,'v0.20.0').map(r=>r.id),[5,6]);assert.throws(()=>releasesToPrune(rs,'v0.15.0'));assert.throws(()=>releasesToPrune([...rs,rs[0]],'v0.20.0'));
});

test('acceptance index names exactly the dated reports for this version',()=>{
 const index={schema:'books-desktop-acceptance-v1',version:'0.16.0',qa:'Docs/BooksArranger_QA_v0.16.0_2026-10-13.md',review:'Docs/BooksArranger_CodeReview_v0.16.0_2026-10-13.md'};
 assert.equal(acceptanceIndex(index,'0.16.0').length,2);
 for(const change of [i=>i.qa='../QA.md',i=>i.qa=i.review,i=>i.extra=true,i=>i.version='0.15.0',i=>i.review=i.review.replace('0.16.0','0.15.0')]){const bad={...index};change(bad);assert.throws(()=>acceptanceIndex(bad,'0.16.0'));}
});

const encode=value=>Buffer.from(JSON.stringify(value));
const sha=value=>createHash('sha256').update(value).digest('hex');
function normalProof(out='') {return {ok:true,closed:true,outputComplete:true,code:0,signal:null,error:null,forced:false,timedOut:false,overflow:false,truncated:false,closureError:null,reason:null,native:{complete:true,zero:true,active:0,assigned:0,listed:0,unsignaled:0,retained:3,sampling:{queries:2,incompleteQueries:0}},out,err:'',ownership:'private-job'};}
function nativeBundle(candidate,mutations={}) {
 // These fabricated records never leave memory and never authorize native work.
 // The pre-import guards above make calling any real adapter an immediate failure.
 const expected=structuredClone(candidate),b=structuredClone(candidate),records={};
 const change=(role,value)=>{mutations[role]?.(value);return value;};
 const authority=change('authority',{schema:'books-native-qa-authority-v1',binding:structuredClone(b),approved_by:'Sergei',decision_ref:'unit-only-decision-20261101',decision_text:'Inert unit test data; never supplies actual native permission.',approved_at:'2026-11-01T00:00:00Z',effects:{hidden_private_app:true,invalid_installer_attempt:true,own_new_leaf_delete:true,leave_numeric_history_reference:true,ui_order_list_write:false}});
 records.authority=encode(authority);
 const fixtureRoot='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/release-tests/inert-pa1-'+b.build_id;
 records.plan=encode(change('plan',{schema:'books-real-shell-plan-v1',binding:structuredClone(b),case:structuredClone(NATIVE_CASE),deadlineMs:600000,expected_tray_types:{ExecutablePath:1,IsPromoted:4},phase_contract_sha256:b.phase_contract_sha256,fixture_root:fixtureRoot,evidence_root:fixtureRoot+'/evidence',source_root:fixtureRoot+'/source',koffi_root:fixtureRoot+'/owner/node_modules/koffi',node:{path:'C:/Program Files/nodejs/node.exe',sha256:'f'.repeat(64)},helper:{path:fixtureRoot+'/bounded-check.mjs',sha256:'f'.repeat(64)},authority:{path:fixtureRoot+'/authority.json',sha256:sha(records.authority),size:records.authority.length},trees:[{},{},{},{}],inputs:[{},{},{},{},{},{},{}],payload:{root:fixtureRoot+'/built'},environment:{}}));
 const functional=change('functional',{schema:'books-pa1-functional-v1',binding:structuredClone(b),case:structuredClone(NATIVE_CASE),assertions:[...PA1_ASSERTIONS],fixture_root:fixtureRoot,exe:fixtureRoot+'/app/Books Arranger.exe',downloadVerified:true,invalidInstallerRefused:true,oldEngineRecovered:true,shellStayedRunning:true,healthVersionMatched:true,closedByQuit:true,payloadUnchanged:true,endpointsOwned:true,noVisibleOwnWindow:true,intrusion:null});
 records.functional=encode(functional);
 let output='# BOOKS_PA1_FUNCTIONAL '+JSON.stringify(functional)+'\n# tests 1\n# pass 1\n# fail 0\n# skipped 0\n# cancelled 0\n';
 const owned=change('owned',{...normalProof(output),err:'inner-only diagnostic\n'});
 records.owned=encode(owned);records.stdout=Buffer.from(owned.out);records.stderr=Buffer.from(owned.err);
 records.postflight=encode(change('postflight',{schema:'books-native-postflight-v1',binding:structuredClone(b),unchanged:true,plan_sha256:sha(records.plan),owned_sha256:sha(records.owned)}));
 records.cleanup=encode(change('cleanup',{schema:'books-own-tray-cleanup-v1',binding:structuredClone(b),authority_sha256:sha(records.authority),owned_sha256:sha(records.owned),fixture_root:functional.fixture_root,exe:functional.exe,ownId:'42',exactNewLeaf:true,sameHandle:true,deleted:true,closed:true,absenceVerified:true,preexistingUnchanged:true,uiOrderListWritten:false,ownReferenceCount:1,ownReferenceBytes:8,uiOrderListSha256:'a'.repeat(64),partial:false,error:null}));
 const marker={schema:'books-pa1-controller-v1',plan_sha256:sha(records.plan),owned_sha256:sha(records.owned),cleanup_sha256:sha(records.cleanup),postflight_sha256:sha(records.postflight)};
 records.controller_owned=encode(change('controller_owned',{...normalProof('BOOKS_PA1_CONTROLLER '+JSON.stringify(marker)+'\n'),err:'controller-only diagnostic\n'}));
 records.controller_stdout=Buffer.from(JSON.parse(records.controller_owned).out);records.controller_stderr=Buffer.from(JSON.parse(records.controller_owned).err);
 records.callback=encode(change('callback',{callback_received:true,error:null,start_write_error:null,write_errors:[],plan_sha256:sha(records.plan),binding_sha256:sha(JSON.stringify(b)),owned_sha256:sha(records.owned),controller_owned_sha256:sha(records.controller_owned),stdout_sha256:sha(records.controller_stdout),stdout_bytes:records.controller_stdout.length,stderr_sha256:sha(records.controller_stderr),stderr_bytes:records.controller_stderr.length}));
 const summary={schema:'books-native-qa-v1',binding:b,case:structuredClone(NATIVE_CASE),records:Object.fromEntries(NATIVE_ROLES.map(role=>[role,{path:'Docs/BooksArranger_NativeQA_v'+b.version+'_Evidence/'+role.replaceAll('_','-')+(['stdout','stderr','controller_stdout','controller_stderr'].includes(role)?'.log':'.json'),sha256:sha(records[role]),size:records[role].length}]))};
 mutations.summary?.(summary);
 return {expected,summary,records};
}

function currentBinding(version='0.24.2'){return {version,source_head:pin,product_digest:hex,build_id:id,artifact_manifest_sha256:'c'.repeat(64),runtime_manifest_sha256:'d'.repeat(64),phase_contract_sha256:'e'.repeat(64)};}
test('native phase is mandatory from 0.24.2 through later major versions',()=>{
 for(const value of ['0.24.2','0.24.3','0.25.0','1.0.0','2.0.0'])assert.equal(requiresNativeQa(value),true,value);
 for(const value of ['0.16.0','0.24.1'])assert.equal(requiresNativeQa(value),false,value);
 for(const value of ['00.24.2','0.24.2-beta','v0.24.2','0.24'])assert.throws(()=>requiresNativeQa(value));
});
test('historical artifact readers remain readable but cannot accept a current version',()=>{
 artifactContract(manifest(),{version:'0.16.0',productTree:hex});
 assert.throws(()=>artifactContract(manifest(),{version:'0.24.2',productTree:hex}),/Artifact source\/version manifest mismatch/);
});
test('QA evidence line is exactly one hash and GO prose alone cannot replace it',()=>{
 const line='Native QA evidence SHA256: '+hex+'\n';assert.equal(nativeEvidenceReportHash(line),hex);
 for(const text of ['**Verdict:** GO\n',line+line,line.replace(hex,'short'),line.replace(hex,hex.toUpperCase()),line.replace(hex,hex+' trailing')])assert.throws(()=>nativeEvidenceReportHash(text));
});
test('complete in-memory evidence has exact original case and every raw role',()=>{
 const e=nativeBundle(currentBinding());assert.equal(validateNativeEvidence(e.summary,e.records,e.expected).passed,true);
 assert.equal(nativeRecordReferences(e.summary,'0.24.2').length,12);
 assert.equal(nativeEvidencePath('0.24.2'),'Docs/BooksArranger_NativeQA_v0.24.2.json');
});
test('each source version build product artifact runtime and phase binding is enforced',()=>{
 const changes={version:'0.24.3',source_head:'f'.repeat(40),product_digest:'f'.repeat(64),build_id:'e9ee38b0-6d35-4a5e-8cc5-bba1c08a91f4',artifact_manifest_sha256:'f'.repeat(64),runtime_manifest_sha256:'f'.repeat(64),phase_contract_sha256:'f'.repeat(64)};
 for(const [field,value] of Object.entries(changes)){const e=nativeBundle(currentBinding());e.summary.binding[field]=value;assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.expected),/different candidate/,field);}
});
test('authority and functional case cannot be replaced by copied or skipped proof',()=>{
 for(const mutate of [a=>a.approved_by='agent',a=>a.decision_ref='PENDING-approval',a=>a.effects.ui_order_list_write=true,a=>a.effects.own_new_leaf_delete=false]){const e=nativeBundle(currentBinding(),{authority:mutate});assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.expected));}
 for(const mutate of [f=>f.case.title='replacement case',f=>f.assertions.pop(),f=>f.assertions.reverse(),f=>f.assertions[1]=f.assertions[0],f=>f.oldEngineRecovered=false,f=>f.intrusion='visible own window']){const e=nativeBundle(currentBinding(),{functional:mutate});assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.expected));}
});
test('mandatory phase inventory cannot omit duplicate or relabel the native case',()=>{
 assert.equal(phaseAccounting().native.required,true);
 for(const list of [CANONICAL_NODE_ENTRIES.slice(1),[...CANONICAL_NODE_ENTRIES,PA1_ENTRY],[...CANONICAL_NODE_ENTRIES.slice(0,-1),CANONICAL_NODE_ENTRIES[0]]])assert.throws(()=>phaseAccounting(list));
 assert.throws(()=>phaseAccounting(CANONICAL_NODE_ENTRIES,[]));
});
test('every raw reference is required byte-bound and confined before file reads',()=>{
 for(const role of NATIVE_ROLES){const missing=nativeBundle(currentBinding());delete missing.records[role];assert.throws(()=>validateNativeEvidence(missing.summary,missing.records,missing.expected),role);const changed=nativeBundle(currentBinding());changed.records[role]=Buffer.concat([changed.records[role],Buffer.from(' ')]);assert.throws(()=>validateNativeEvidence(changed.summary,changed.records,changed.expected),role);}
 for(const mutate of [s=>s.records.plan.path='../plan.json',s=>s.records.plan.path='C:/outside.json',s=>s.records.plan.path=s.records.owned.path,s=>s.records.plan.path=s.records.plan.path.replace('0.24.2','0.24.1'),s=>s.records.plan.size=32*1024*1024+1,s=>s.records.plan.size=-1,s=>s.records.plan.sha256='bad']){const e=nativeBundle(currentBinding());mutate(e.summary);assert.throws(()=>nativeRecordReferences(e.summary,'0.24.2'));}
});
test('inner and controller ownership each require normal complete zero closure',()=>{
 const changes=[r=>r.ok=false,r=>r.closed=false,r=>r.code=1,r=>r.signal='SIGTERM',r=>r.error='failed',r=>r.outputComplete=false,r=>r.forced=true,r=>r.timedOut=true,r=>r.overflow=true,r=>r.truncated=true,r=>r.closureError='lost',r=>r.reason='closure refused',r=>r.native.zero=false,r=>r.native.complete=false,r=>r.native.assigned=1,r=>r.native.active=1,r=>r.native.listed=1,r=>r.native.unsignaled=1,r=>r.native.retained=0,r=>r.native.sampling.incompleteQueries=1,r=>r.native.sampling.queries=0,r=>r.ownership='unknown'];
 for(const role of ['owned','controller_owned'])for(const mutate of changes){const e=nativeBundle(currentBinding(),{[role]:mutate});assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.expected),role);}
});
test('execution totals and functional markers cannot be skipped duplicated or replaced',()=>{
 for(const mutate of [r=>r.out=r.out.replace('# skipped 0','# skipped 1'),r=>r.out=r.out.replace('# pass 1','# pass 0'),r=>r.out=r.out.replace('# tests 1','# tests 2'),r=>r.out=r.out.replace('# cancelled 0','# cancelled 1'),r=>r.out+=r.out.split('\n')[0]+'\n',r=>r.out=r.out.replace('BOOKS_PA1_FUNCTIONAL','BOOKS_OTHER_FUNCTIONAL')]){const e=nativeBundle(currentBinding(),{owned:mutate});assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.expected));}
});
test('callback postflight and own-leaf cleanup failures cannot become release evidence',()=>{
 const mutations={callback:[c=>c.callback_received=false,c=>c.error='failure',c=>c.start_write_error='failure',c=>c.write_errors.push('failure'),c=>c.plan_sha256='f'.repeat(64),c=>c.binding_sha256='f'.repeat(64),c=>c.stdout_bytes++,c=>c.controller_owned_sha256='f'.repeat(64)],postflight:[p=>p.unchanged=false,p=>p.plan_sha256='f'.repeat(64)],cleanup:[c=>c.deleted=false,c=>c.closed=false,c=>c.exactNewLeaf=false,c=>c.sameHandle=false,c=>c.absenceVerified=false,c=>c.preexistingUnchanged=false,c=>c.partial=true,c=>c.error='failure',c=>c.uiOrderListWritten=true,c=>c.ownReferenceCount=2,c=>c.ownReferenceBytes=16,c=>c.exe+='-other',c=>c.fixture_root+='-other',c=>c.ownId='unknown']};
 for(const [role,list] of Object.entries(mutations))for(const mutate of list){const e=nativeBundle(currentBinding(),{[role]:mutate});assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.expected),role);}
});

test('outer callback cannot authenticate inner TAP or diagnostic streams as controller output',()=>{
 const e=nativeBundle(currentBinding()),callback=JSON.parse(e.records.callback);
 for(const role of ['stdout','stderr']){assert.notDeepEqual(e.records[role],e.records['controller_'+role]);callback[role+'_sha256']=sha(e.records[role]);callback[role+'_bytes']=e.records[role].length;}
 e.records.callback=encode(callback);e.summary.records.callback.sha256=sha(e.records.callback);e.summary.records.callback.size=e.records.callback.length;
 assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.expected),/Outer callback must bind original controller streams/);
});

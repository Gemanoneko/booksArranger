// Pure only: native adapters are never constructed. Every injected mutation
// adapter records calls; unselected native operations throw.
import test,{after} from 'node:test';
import childProcess from 'node:child_process';
import net from 'node:net';
import http from 'node:http';
import https from 'node:https';
import Module,{syncBuiltinESMExports} from 'node:module';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {phaseAccounting,CANONICAL_NODE_ENTRIES,ORIGINAL_NODE_ENTRIES,PA1_ENTRY,PA1_ASSERTIONS,NATIVE_CASE,NATIVE_ROLES,hash,binding,validateAuthority,validateFunctional,normalOwned,validateNativeEvidence,nativeRecordReferences,requiresNativeQa} from '../scripts/qa-phase-contract.mjs';
let nativeAttempts=0;const restore=[];
const deny=()=>{nativeAttempts++;throw Error('Native adapter reached during pure contract tests');};
for(const [object,names] of [[childProcess,['spawn','spawnSync','exec','execSync','execFile','execFileSync','fork']],[net,['connect','createConnection','createServer']],[http,['request','get','createServer']],[https,['request','get','createServer']]])for(const name of names){const old=object[name];restore.push(()=>object[name]=old);object[name]=deny;}
for(const name of ['fetch','WebSocket']){const old=globalThis[name];restore.push(()=>globalThis[name]=old);globalThis[name]=deny;}
const originalRequire=Module.createRequire;restore.push(()=>Module.createRequire=originalRequire);Module.createRequire=(...args)=>{const require=originalRequire(...args);return spec=>{if(!String(spec).startsWith('node:'))return deny();return require(spec);};};syncBuiltinESMExports();
after(()=>{for(const undo of restore.reverse())undo();syncBuiltinESMExports();assert.equal(nativeAttempts,0,'No actual native/child/network operation');});
const {validatePlan,ownLeafDelta,cleanupOwnLeaf,nativeAdapters,membershipWitness,listenerOnlyRows,requiredWindowPid,sameFileTree,ordinary,readPin,treeFiles,verifyInputs,verifyRecovery,recoveryCacheChanges,privateEnginePort,freshFixture,createPrivateShellCommands,verifyCloseSession}=await import('./real-shell-update-support.mjs');
const {evidenceSummary,forwardControllerStreams}=await import('../scripts/qa-real-shell-phase.mjs');
const encoded=v=>Buffer.from(JSON.stringify(v));
function candidate(){return {version:'0.24.2',source_head:'a'.repeat(40),product_digest:'b'.repeat(64),build_id:'e3a1de11-1811-4ef5-bf5c-586a70b7db9e',artifact_manifest_sha256:'c'.repeat(64),runtime_manifest_sha256:'d'.repeat(64),phase_contract_sha256:'e'.repeat(64)};}
function authority(b=candidate()){return {schema:'books-native-qa-authority-v1',binding:b,approved_by:'Sergei',decision_ref:'unit-only-decision-20261101',decision_text:'Inert unit test data; never supplies actual native permission.',approved_at:'2026-11-01T00:00:00Z',effects:{hidden_private_app:true,invalid_installer_attempt:true,own_new_leaf_delete:true,leave_numeric_history_reference:true,ui_order_list_write:false}};}
function plan(b=candidate(),a=authority(b)){return {schema:'books-real-shell-plan-v1',binding:b,case:NATIVE_CASE,deadlineMs:600000,phase_contract_sha256:b.phase_contract_sha256,fixture_root:'C:/private/pa1-'+b.build_id,evidence_root:'C:/private',source_root:'C:/source',koffi_root:'C:/owner/node_modules/koffi',node:{path:'C:/Program Files/nodejs/node.exe',sha256:'f'.repeat(64)},helper:{path:'C:/studio/.claude/skills/qa-handoff/scripts/bounded-check.mjs',sha256:'f'.repeat(64)},authority:{path:'C:/private/authority.json',sha256:hash(encoded(a)),size:encoded(a).length},trees:[{},{},{},{}],inputs:[{},{},{},{},{},{},{}],payload:{root:'C:/built'},environment:{SystemRoot:'C:/Windows',WINDIR:'C:/Windows',PATH:'C:/Program Files/nodejs;C:/Windows/System32',TEMP:'C:/private/pa1-'+b.build_id+'/home/temp',TMP:'C:/private/pa1-'+b.build_id+'/home/temp',USERPROFILE:'C:/private/pa1-'+b.build_id+'/home',APPDATA:'C:/private/pa1-'+b.build_id+'/home/roaming',LOCALAPPDATA:'C:/private/pa1-'+b.build_id+'/home/local'},expected_tray_types:{ExecutablePath:1,IsPromoted:4}};}
function normal(out=''){return {ok:true,closed:true,outputComplete:true,code:0,signal:null,error:null,forced:false,timedOut:false,overflow:false,truncated:false,closureError:null,reason:null,native:{complete:true,zero:true,active:0,assigned:0,listed:0,unsignaled:0,retained:3,sampling:{queries:2,incompleteQueries:0}},out,err:'',ownership:'private-job'};}
function functional(b){return {schema:'books-pa1-functional-v1',binding:b,case:NATIVE_CASE,assertions:[...PA1_ASSERTIONS],fixture_root:'C:/private/pa1-'+b.build_id,exe:'C:/private/pa1-'+b.build_id+'/app/Books Arranger.exe',downloadVerified:true,invalidInstallerRefused:true,oldEngineRecovered:true,shellStayedRunning:true,healthVersionMatched:true,closedByQuit:true,payloadUnchanged:true,endpointsOwned:true,noVisibleOwnWindow:true,intrusion:null};}
function evidence(){
 const b=candidate(),a=authority(b),p=plan(b,a),f=functional(b),records={authority:encoded(a),plan:encoded(p),functional:encoded(f)};
 const out='# BOOKS_PA1_FUNCTIONAL '+JSON.stringify(f)+'\n# tests 1\n# pass 1\n# fail 0\n# skipped 0\n# cancelled 0\n';records.owned=encoded({...normal(out),err:'inner-only diagnostic\n'});records.stdout=Buffer.from(out);records.stderr=Buffer.from('inner-only diagnostic\n');
 records.postflight=encoded({schema:'books-native-postflight-v1',binding:b,unchanged:true,plan_sha256:hash(records.plan),owned_sha256:hash(records.owned)});
 records.cleanup=encoded({schema:'books-own-tray-cleanup-v1',binding:b,authority_sha256:hash(records.authority),owned_sha256:hash(records.owned),fixture_root:f.fixture_root,exe:f.exe,ownId:'42',exactNewLeaf:true,sameHandle:true,deleted:true,closed:true,absenceVerified:true,preexistingUnchanged:true,uiOrderListWritten:false,ownReferenceCount:1,ownReferenceBytes:8,uiOrderListSha256:'a'.repeat(64),partial:false,error:null});
 records.controller_owned=encoded({...normal('BOOKS_PA1_CONTROLLER '+JSON.stringify({schema:'books-pa1-controller-v1',plan_sha256:hash(records.plan),owned_sha256:hash(records.owned),cleanup_sha256:hash(records.cleanup),postflight_sha256:hash(records.postflight)})+'\n'),err:'controller-only diagnostic\n'});
 records.controller_stdout=Buffer.from(JSON.parse(records.controller_owned).out);records.controller_stderr=Buffer.from(JSON.parse(records.controller_owned).err);
 records.callback=encoded({callback_received:true,error:null,start_write_error:null,write_errors:[],plan_sha256:hash(records.plan),binding_sha256:hash(JSON.stringify(b)),owned_sha256:hash(records.owned),controller_owned_sha256:hash(records.controller_owned),stdout_sha256:hash(records.controller_stdout),stdout_bytes:records.controller_stdout.length,stderr_sha256:hash(records.controller_stderr),stderr_bytes:records.controller_stderr.length});
 return {b,records,summary:evidenceSummary(b,records)};
}
function leaf(exe){return {subkeys:0,values:{ExecutablePath:{type:1,hex:Buffer.from(exe+'\0','utf16le').toString('hex')},IsPromoted:{type:4,hex:'00000000'}}};}
function registryFixture(){const b=candidate(),a=authority(b),p=plan(b,a),exe=p.fixture_root+'/app/Books Arranger.exe',before={rootSchema:{},order:'',leaves:{}},order=Buffer.alloc(8);order.writeBigUInt64LE(42n);const current={rootSchema:{},order:order.toString('hex'),leaves:{'42':leaf(exe)}},calls=[];let state=structuredClone(current),held=null;
 const adapter={snapshot:async()=>{calls.push('snapshot');return structuredClone(state);},openExact:async id=>{calls.push('open:'+id);assert.equal(id,'42');return held={id};},readHandle:async h=>{calls.push('read');assert.equal(h,held);return structuredClone(state.leaves[h.id]);},deleteHandle:async h=>{calls.push('delete');assert.equal(h,held);delete state.leaves[h.id];},close:async h=>{calls.push('close');assert.equal(h,held);},writeOrder:()=>{throw Error('FORBIDDEN native write');}};
 return {p,a,before,current,exe,adapter,calls,get state(){return state;},set state(v){state=v;},run:()=>cleanupOwnLeaf({plan:p,authority:a,owned:normal(),before,adapter,deadline:Date.now()+5000})};}
test('all eighteen original identities occur exactly once across mandatory phases',()=>{const p=phaseAccounting();assert.equal(ORIGINAL_NODE_ENTRIES.length,18);assert.equal(p.canonical.node_entries.length,18);assert.equal(p.native.entry,PA1_ENTRY);assert.equal(p.native.required,true);assert.ok(!p.canonical.node_entries.includes(PA1_ENTRY));assert.equal(p.total_node_entries,19);});
test('missing, duplicated, renamed or pure-labelled native entries refuse',()=>{for(const rows of [CANONICAL_NODE_ENTRIES.slice(1),[...CANONICAL_NODE_ENTRIES,PA1_ENTRY],[...CANONICAL_NODE_ENTRIES.slice(0,-1),CANONICAL_NODE_ENTRIES[0]]])assert.throws(()=>phaseAccounting(rows));assert.throws(()=>phaseAccounting(CANONICAL_NODE_ENTRIES,[]));});
test('native evidence is mandatory for 0.24.2 and every later release',()=>{for(const v of ['0.24.2','0.24.3','0.25.0','1.0.0'])assert.equal(requiresNativeQa(v),true);assert.equal(requiresNativeQa('0.24.1'),false);assert.throws(()=>requiresNativeQa('00.24.2'));});
test('authority absent, stale or allowing shared-list writes refuses',()=>{const b=candidate();assert.throws(()=>validateAuthority(null,b));for(const alter of [a=>a.binding.build_id='a3a1de11-1811-4ef5-bf5c-586a70b7db9e',a=>a.decision_ref='PENDING-authority',a=>a.effects.ui_order_list_write=true,a=>a.effects.leave_numeric_history_reference=false,a=>a.approved_by='agent']){const a=authority(b);a.binding=structuredClone(b);alter(a);assert.throws(()=>validateAuthority(a,b));}});
test('each candidate binding field is checked',()=>{const expected=candidate();for(const k of Object.keys(expected)){const a=authority();a.binding[k]=k==='version'?'0.24.3':k==='build_id'?'f3a1de11-1811-4ef5-bf5c-586a70b7db9e':'f'.repeat(k==='source_head'?40:64);assert.throws(()=>validateAuthority(a,expected),k);}});
test('fixed plan rejects wrong selector, deadline, external fixture or authority bytes',()=>{for(const alter of [p=>p.case={...NATIVE_CASE,title:'replacement'},p=>p.deadlineMs=600001,p=>p.fixture_root='Z:/library',p=>p.authority.sha256='0'.repeat(64),p=>p.environment.NODE_OPTIONS='--require bad']){const a=authority(),p=plan(candidate(),a);alter(p);assert.throws(()=>validatePlan(p,a));}});
test('all eight original functional assertions and extra proof are mandatory',()=>{const b=candidate(),f=functional(b);assert.equal(PA1_ASSERTIONS.length,8);validateFunctional(f,b);for(const flag of ['downloadVerified','invalidInstallerRefused','oldEngineRecovered','shellStayedRunning','healthVersionMatched','closedByQuit','payloadUnchanged','endpointsOwned','noVisibleOwnWindow'])assert.throws(()=>validateFunctional({...f,[flag]:false},b));assert.throws(()=>validateFunctional({...f,assertions:f.assertions.slice(1)},b));});
test('original ownership rejects timeout, forced, unknown or incomplete closure',()=>{for(const alter of [r=>r.ok=false,r=>r.forced=true,r=>r.timedOut=true,r=>r.outputComplete=false,r=>r.native.zero=false,r=>r.native.complete=false,r=>r.native.sampling.incompleteQueries=r.native.sampling.queries,r=>r.native.active=1,r=>r.native.assigned=1,r=>r.native.listed=1,r=>r.native.unsignaled=1,r=>r.closureError='lost']){const r=normal();alter(r);assert.throws(()=>normalOwned(r));}});
test('normal final zero closure retains earlier incomplete sampling diagnostics',()=>{
 const r=normal();r.native.sampling={queries:3,incompleteQueries:1};const before=encoded(r);
 assert.equal(normalOwned(r),r);assert.deepEqual(encoded(r),before,'validation must not zero or rewrite the original diagnostic');
});
test('sampling counts require safe integers and at least one completed final observation',()=>{
 const bad=[undefined,null,-1,.5,'1',NaN,Infinity,Number.MAX_SAFE_INTEGER+1];
 for(const field of ['queries','incompleteQueries'])for(const value of [...bad,...(field==='queries'?[0]:[3,4])]){
  const r=normal();r.native.sampling={queries:3,incompleteQueries:1};if(value===undefined)delete r.native.sampling[field];else r.native.sampling[field]=value;
  assert.throws(()=>normalOwned(r),/Native observation incomplete/,field+'='+String(value));
 }
 for(const sampling of [undefined,null,{}]){const r=normal();r.native.sampling=sampling;assert.throws(()=>normalOwned(r),/Native observation incomplete/);}
});
test('strict raw evidence accepts internally consistent original inner and outer owner records',()=>{const e=evidence();assert.equal(validateNativeEvidence(e.summary,e.records,e.b).passed,true);assert.equal(NATIVE_ROLES.length,12);});
test('every missing or byte-changed raw evidence record refuses',()=>{for(const role of NATIVE_ROLES){const e=evidence();delete e.records[role];assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.b));const f=evidence();f.records[role]=Buffer.concat([f.records[role],Buffer.from(' ')]);assert.throws(()=>validateNativeEvidence(f.summary,f.records,f.b));}});
test('copied receipt for another candidate refuses even with valid hashes',()=>{const e=evidence(),b={...e.b,build_id:'f3a1de11-1811-4ef5-bf5c-586a70b7db9e'};assert.throws(()=>validateNativeEvidence(e.summary,e.records,b));});
test('unsafe, duplicate and oversized record references refuse before reads',()=>{for(const alter of [s=>s.records.authority.path='../foreign',s=>s.records.authority.path=s.records.plan.path,s=>s.records.authority.size=33*1024*1024]){const e=evidence();alter(e.summary);assert.throws(()=>nativeRecordReferences(e.summary,e.b.version));}});
test('valid exact own leaf deletion leaves only the explicitly counted eight bytes',async()=>{const f=registryFixture(),r=await f.run();assert.equal(r.deleted,true);assert.equal(r.partial,false);assert.equal(r.uiOrderListWritten,false);assert.equal(r.ownReferenceBytes,8);assert.deepEqual(f.calls,['snapshot','open:42','read','snapshot','delete','close','snapshot']);});
test('no cleanup adapter call occurs with missing normal app-owner proof',async()=>{const f=registryFixture();await assert.rejects(cleanupOwnLeaf({plan:f.p,authority:f.a,owned:{},before:f.before,adapter:f.adapter,deadline:Date.now()+5000}));assert.deepEqual(f.calls,[]);});
test('wrong executable, additional leaf, subkey and foreign list drift refuse before deletion',async()=>{for(const alter of [f=>f.state.leaves['42']=leaf('C:/foreign.exe'),f=>f.state.leaves['43']=leaf(f.exe),f=>f.state.leaves['42'].subkeys=1,f=>f.state.order='00'.repeat(16)]){const f=registryFixture();alter(f);await assert.rejects(f.run());assert.ok(!f.calls.includes('delete'));}});
test('a preexisting leaf is never adopted or deleted',async()=>{const f=registryFixture();f.before.leaves['42']=structuredClone(f.current.leaves['42']);await assert.rejects(f.run());assert.ok(!f.calls.includes('delete'));});
test('same-handle executable/extra-value drift refuses and closes the retained handle',async()=>{for(const alter of [v=>v.values.ExecutablePath=leaf('C:/other.exe').values.ExecutablePath,v=>v.values.extra={type:4,hex:'00000000'}]){const f=registryFixture();f.adapter.readHandle=async()=>{const v=structuredClone(f.current.leaves['42']);alter(v);return v;};await assert.rejects(f.run());assert.ok(!f.calls.includes('delete'));assert.equal(f.calls.at(-1),'close');}});
test('foreign drift after handle validation refuses without rollback or list write',async()=>{const f=registryFixture(),snap=f.adapter.snapshot;let n=0;f.adapter.snapshot=async()=>{const s=await snap();if(++n===2)s.rootSchema.foreign={type:4,hex:'00000001'};return s;};await assert.rejects(f.run());assert.ok(!f.calls.includes('delete'));});
test('post-delete drift reports partial outcome and never restores shared state',async()=>{const f=registryFixture(),del=f.adapter.deleteHandle;f.adapter.deleteHandle=async h=>{await del(h);f.state.rootSchema.concurrent={type:4,hex:'00000001'};};await assert.rejects(f.run(),e=>e.cleanup.partial===true&&e.cleanup.deleted===true&&e.cleanup.error.includes('Registry changed'));assert.equal(f.calls.filter(x=>x==='delete').length,1);});
test('deletion or close failure cannot become cleanup PASS',async()=>{for(const op of ['deleteHandle','close']){const f=registryFixture();f.adapter[op]=async()=>{throw Error('injected '+op);};await assert.rejects(f.run(),new RegExp('injected '+op));}});

test('native adapter stays default refused before its first loader call',()=>{assert.throws(()=>nativeAdapters(plan(),null));assert.equal(nativeAttempts,0);});

test('known HWND lookup returns its PID only after a successful thread result',()=>{let calls=0;assert.equal(requiredWindowPid((window,pid)=>{calls++;assert.equal(window,'own-window');pid[0]=42;return 99;},'own-window'),42);assert.equal(calls,1);});
test('failed or unknown HWND lookup refuses both enumeration and foreground identities',()=>{for(const [thread,pid] of [[0,42],[0,0],[99,0],[99,NaN],[-1,42],[99,0x100000000]])assert.throws(()=>requiredWindowPid((_,out)=>{out[0]=pid;return thread;},'window'),/Window PID lookup failed/);assert.throws(()=>requiredWindowPid(()=>{throw Error('query failure');},'window'),/query failure/);});
test('actual outer forwarding writes distinct controller bytes without inner TAP substitution',async()=>{const result={...normal('controller marker bytes\n'),err:'controller diagnostic bytes\n'},seen={stdout:[],stderr:[]};const streams=Object.fromEntries(Object.keys(seen).map(name=>[name,{write(bytes,done){seen[name].push(Buffer.from(bytes));done();}}]));await forwardControllerStreams(result,streams);assert.equal(Buffer.concat(seen.stdout).toString(),result.out);assert.equal(Buffer.concat(seen.stderr).toString(),result.err);assert.notEqual(result.out,'inner TAP bytes\n');});
test('outer forwarding refuses abnormal owner before writes and rejects write failure',async()=>{let writes=0;const stream={write(_,done){writes++;done();}};await assert.rejects(forwardControllerStreams({...normal(),forced:true},{stdout:stream,stderr:stream}),/Abnormal owned/);assert.equal(writes,0);await assert.rejects(forwardControllerStreams(normal('marker'),{stdout:{write(_,done){done(Error('sink failed'));}},stderr:stream}),/sink failed/);assert.equal(writes,0);});
test('callback hashes bound to inner TAP instead of controller bytes refuse despite coherent hashes',()=>{const e=evidence(),callback=JSON.parse(e.records.callback);for(const role of ['stdout','stderr']){callback[role+'_sha256']=hash(e.records[role]);callback[role+'_bytes']=e.records[role].length;}e.records.callback=encoded(callback);e.summary.records.callback.sha256=hash(e.records.callback);e.summary.records.callback.size=e.records.callback.length;assert.notDeepEqual(e.records.stdout,e.records.controller_stdout);assert.notDeepEqual(e.records.stderr,e.records.controller_stderr);assert.throws(()=>validateNativeEvidence(e.summary,e.records,e.b),/Outer callback must bind original controller streams/);});

// Tiny ordinary filesystem fixtures exercise the actual inventory verifier/copy.
// Fake Node/DLL bytes are inert; the suite's process/network/native guards stay installed.
async function fileInventoryFixture(t){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'books-pa1-inventory-'));
 t.after(async()=>{assert.equal(path.dirname(root),path.resolve(os.tmpdir()));assert.ok(path.basename(root).startsWith('books-pa1-inventory-'));await fs.rm(root,{recursive:true});});
 const write=async(rel,bytes)=>{const p=path.join(root,rel);await fs.mkdir(path.dirname(p),{recursive:true});await fs.writeFile(p,bytes);return p;};
 const source=path.join(root,'source'),nodeRoot=path.join(root,'node'),koffi=path.join(root,'owner','koffi'),payload=path.join(root,'payload');
 const files=[];
 for(const rel of ['scripts/qa-phase-contract.mjs','scripts/qa-real-shell-phase.mjs','tests/real-shell-update.test.mjs','tests/real-shell-update-support.mjs'])files.push(await write('source/'+rel,'inert source '+rel));
 files.push(await write('node/node.exe','inert Node fixture'),await write('owner/koffi/index.js','inert ownership fixture'),await write('helper/bounded-check.mjs','inert helper'),await write('helper/bounded-child.mjs','inert child'));
 await write('payload/Books Arranger.exe','not an executable');await write('payload/resources/backend/VERSION','0.24.2\n');
 const realStat=fs.lstat.bind(fs),realRead=fs.readFile.bind(fs),system=new Map(['kernel32.dll','advapi32.dll','ntdll.dll','user32.dll','iphlpapi.dll'].map(name=>['C:/Windows/System32/'+name,Buffer.from('inert '+name)]));
 const key=p=>String(p).replaceAll(String.fromCharCode(92),'/');
 t.mock.method(fs,'lstat',async(p,options)=>{const bytes=system.get(key(p));if(!bytes)return realStat(p,options);assert.deepEqual(options,{bigint:true});return {dev:1n,ino:2n,nlink:1n,size:BigInt(bytes.length),isFile:()=>true,isDirectory:()=>false,isSymbolicLink:()=>false};});
 t.mock.method(fs,'readFile',async(p,...args)=>system.has(key(p))?system.get(key(p)):realRead(p,...args));
 const pin=async p=>{const bytes=await fs.readFile(p),s=await fs.lstat(p,{bigint:true});return {path:p,size:bytes.length,sha256:hash(bytes),identity:{dev:String(s.dev),ino:String(s.ino),nlink:Number(s.nlink)}};};
 const inputs=await Promise.all([...files,...system.keys()].map(pin));
 const pythonFacts=tree=>Object.fromEntries(Object.entries(tree).reverse().map(([name,f])=>[name,{sha256:f.sha256,size:f.size}]));
 const trees=await Promise.all([source,nodeRoot,koffi].map(async root=>({root,files:pythonFacts(await treeFiles(root))})));
 const p={binding:candidate(),node:inputs.find(f=>f.path===path.join(nodeRoot,'node.exe')),helper:inputs.find(f=>f.path===path.join(root,'helper','bounded-check.mjs')),source_root:source,koffi_root:koffi,inputs,trees,payload:{root:payload},fixture_root:path.join(root,'pa1-'+candidate().build_id)};
 p.binding.phase_contract_sha256=inputs.find(f=>f.path===path.join(source,'scripts','qa-phase-contract.mjs')).sha256;
 const published=pythonFacts(await treeFiles(payload)),runtime={fixture:true};p.binding.runtime_manifest_sha256=hash(JSON.stringify(runtime));
 const publish=async inventory=>{const m={version:p.binding.version,source_head:p.binding.source_head,product_digest:p.binding.product_digest,build_id:p.binding.build_id,runtime,payload:{verified:true,installer_equivalent:true,files:inventory}};const file=await write('release-artifacts.json',JSON.stringify(m));p.payload.manifest=await pin(file);p.binding.artifact_manifest_sha256=p.payload.manifest.sha256;return m;};
 await publish(published);return {root,p,published,publish,payload};
}
test('published Python-shaped payload inventory verifies and copies without depending on JSON key order',async t=>{
 const f=await fileInventoryFixture(t),actual=await treeFiles(f.payload);
 assert.deepEqual(Object.keys(f.published['Books Arranger.exe']),['sha256','size']);assert.deepEqual(Object.keys(actual['Books Arranger.exe']),['size','sha256']);
 assert.notEqual(JSON.stringify(actual),JSON.stringify(f.published));assert.equal(sameFileTree(actual,f.published),true);
 const manifest=await verifyInputs(f.p),app=await freshFixture(f.p,manifest);
 assert.equal(sameFileTree(await treeFiles(app),manifest.payload.files),true,'same exact comparator is used by controller postflight');
 assert.deepEqual(await fs.readFile(path.join(app,'Books Arranger.exe')),await fs.readFile(path.join(f.payload,'Books Arranger.exe')));
});
test('actual payload verifier rejects changed bytes, members, keys and typed facts after manifest rebinding',async t=>{
 const f=await fileInventoryFixture(t),name='Books Arranger.exe';
 for(const alter of [v=>delete v[name],v=>v['unexpected.exe']={...v[name]},v=>v[name].size=String(v[name].size),v=>delete v[name].sha256,v=>v[name].extra=true,v=>v[name].sha256='0'.repeat(64),v=>v[name]=[v[name].size,v[name].sha256]]){
  const changed=structuredClone(f.published);alter(changed);await f.publish(changed);await assert.rejects(verifyInputs(f.p),/Built payload differs/);
 }
 await f.publish(f.published);const file=path.join(f.payload,name),bytes=await fs.readFile(file);bytes[0]^=1;await fs.writeFile(file,bytes);await assert.rejects(verifyInputs(f.p),/Built payload differs/);
});
test('readPin preserves adjacent inode identities above 2^53 and rejects the wrong one before reading bytes',async t=>{
 const file='C:/private/identity.bin',bytes=Buffer.from('private pin'),ino=9007199254740993n,other=ino-1n;let reads=0;
 assert.equal(Number(ino),Number(other),'regression needs an actual Number collision');
 t.mock.method(fs,'lstat',async(p,options)=>{assert.deepEqual(options,{bigint:true});const own=p===file;return {dev:9007199254740995n,ino,nlink:1n,size:BigInt(bytes.length),isFile:()=>own,isDirectory:()=>!own,isSymbolicLink:()=>false};});
 t.mock.method(fs,'readFile',async p=>{assert.equal(p,file);reads++;return bytes;});
 const ref={path:file,size:bytes.length,sha256:hash(bytes),identity:{dev:'9007199254740995',ino:String(ino),nlink:1}};
 const stat=await ordinary(file,{file:true});assert.equal(stat.ino,String(ino));assert.equal(stat.dev,ref.identity.dev);assert.equal(stat.size,bytes.length);assert.equal(stat.nlink,1);
 assert.deepEqual(await readPin(ref),bytes);assert.equal(reads,1);
 await assert.rejects(readPin({...ref,identity:{...ref.identity,ino:String(other)}}),/native identity differs/);assert.equal(reads,1);
 await assert.rejects(readPin({...ref,identity:{...ref.identity,dev:String(9007199254740994n)}}),/native identity differs/);assert.equal(reads,1);
});
test('bigint metadata retains hardlink, ancestor, safe-number and byte integrity refusals',async t=>{
 const file='C:/private/identity.bin',bytes=Buffer.from('private pin');let links=1n,size=BigInt(bytes.length),symlink=false,parentLink=false;
 t.mock.method(fs,'lstat',async(p,options)=>{assert.deepEqual(options,{bigint:true});const own=p===file;return {dev:1n,ino:2n,nlink:links,size,isFile:()=>own,isDirectory:()=>!own,isSymbolicLink:()=>own?symlink:parentLink};});
 t.mock.method(fs,'readFile',async p=>{assert.equal(p,file);return bytes;});
 const ref={path:file,size:bytes.length,sha256:hash(bytes),identity:{dev:'1',ino:'2',nlink:2}};
 links=2n;await assert.rejects(ordinary(file,{file:true}),/Hard-linked/);assert.deepEqual(await readPin(ref),bytes,'exact read-only hardlink pin remains supported');
 await assert.rejects(readPin({...ref,sha256:'0'.repeat(64)}),/Input bytes differ/);
 links=1n;size=BigInt(Number.MAX_SAFE_INTEGER)+1n;await assert.rejects(ordinary(file,{file:true}),/Unsafe numeric file metadata: size/);
 size=BigInt(bytes.length);links=BigInt(Number.MAX_SAFE_INTEGER)+1n;await assert.rejects(ordinary(file,{file:true,allowHardlinks:true}),/Unsafe numeric file metadata: nlink/);
 links=1n;symlink=true;await assert.rejects(ordinary(file,{file:true}),/Nonordinary path/);
 symlink=false;parentLink=true;await assert.rejects(ordinary(file,{file:true}),/Nonordinary ancestor/);
});

test('private shell commands route close then Quit only to the same hidden private executable and profile',async()=>{
 const calls=[],exe='C:/private/app/Books Arranger.exe',profile='C:/private/home/profile',env={TEMP:'C:/private/home/temp'};
 const fake=(file,args,options)=>{calls.push({file,args,options});const listeners={};queueMicrotask(()=>listeners.exit(0,null));return {once(name,fn){listeners[name]=fn;return this;}};};
 const fixture=createPrivateShellCommands({spawn:fake,exe,profile,env});assert.deepEqual(Object.keys(fixture),['closeWindow','quit']);assert.equal(Object.isFrozen(fixture),true);
 await fixture.closeWindow();await fixture.quit();
 assert.deepEqual(calls,[{file:exe,args:['--close-window','--shell-profile='+profile,'--start-hidden','--quiet-errors'],options:{env,windowsHide:true,stdio:'ignore'}},{file:exe,args:['--quit','--shell-profile='+profile,'--start-hidden','--quiet-errors'],options:{env,windowsHide:true,stdio:'ignore'}}]);
 for(const outcome of [{code:1,signal:null},{code:0,signal:'SIGTERM'},{error:Error('command spawn refused')}]){
  const failing=()=>{const listeners={};queueMicrotask(()=>outcome.error?listeners.error(outcome.error):listeners.exit(outcome.code,outcome.signal));return {once(name,fn){listeners[name]=fn;return this;}};};
  const f=createPrivateShellCommands({spawn:failing,exe,profile,env});await assert.rejects(f.closeWindow());await assert.rejects(f.quit());
 }
});
test('close-session proof requires the live primary, unchanged healthy engine and an observed hidden owned window',()=>{
 const proof={running:true,loaded:true,quit:'none',health:{pid:42,version:'0.24.2'},expectedPid:42,version:'0.24.2',windows:{checks:3,intrusion:null,hiddenOwnWindows:1}},before=encoded(proof);
 assert.deepEqual(verifyCloseSession(proof),{endpointsOwned:true,healthVersionMatched:true,noVisibleOwnWindow:true});assert.deepEqual(encoded(proof),before);
 for(const alter of [p=>p.running=false,p=>p.loaded=false,p=>p.quit='requested',p=>p.health.pid=43,p=>p.health.version='0.24.1',p=>p.health=null,p=>p.expectedPid=0,p=>p.windows.intrusion='visible own window',p=>p.windows.hiddenOwnWindows=0,p=>p.windows.hiddenOwnWindows=NaN,p=>p.windows=null]){
  const p=structuredClone(proof);alter(p);assert.throws(()=>verifyCloseSession(p));
 }
});

// The recovery fixtures remain inert bytes under the suite's process/network/native deny guards.
async function failedAttemptFixture(t,caches=false){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'books-pa1-recovery-'));t.after(()=>fs.rm(root,{recursive:true}));
 const prior=path.join(root,'first'),next=path.join(root,'second');await fs.mkdir(prior);await fs.mkdir(next);
 const b=candidate(),fixture=path.join(prior,'pa1-'+b.build_id),app=path.join(fixture,'app');await fs.mkdir(app,{recursive:true});await fs.writeFile(path.join(app,'Books Arranger.exe'),'inert original payload');
 if(caches)for(let n=0;n<93;n++){const cache=path.join(app,'resources/backend/__pycache__/module'+n+'.cpython-314.pyc');await fs.mkdir(path.dirname(cache),{recursive:true});await fs.writeFile(cache,'old cache '+n);await fs.writeFile(path.join(app,'resources/backend/module'+n+'.py'),'unchanged Python source '+n);}
 const pin=async file=>{const raw=await fs.readFile(file),s=await fs.lstat(file,{bigint:true});return{path:file,size:raw.length,sha256:hash(raw),identity:{dev:String(s.dev),ino:String(s.ino),nlink:Number(s.nlink)}};};
 const write=async(name,value)=>{const file=path.join(prior,name);await fs.writeFile(file,encoded(value));return pin(file);};
 const artifact={version:b.version,source_head:b.source_head,product_digest:b.product_digest,build_id:b.build_id,payload:{verified:true,installer_equivalent:true,files:await treeFiles(app)}};
 const artifactRef=await write('artifact.json',artifact);b.artifact_manifest_sha256=artifactRef.sha256;
 const a=authority(b),previous=plan(b,a);previous.evidence_root=prior;previous.fixture_root=fixture;previous.authority=await write('authority.json',a);
 previous.environment=Object.fromEntries(Object.entries(previous.environment).map(([k,v])=>[k,v.replace('C:/private/pa1-'+b.build_id,fixture)]));
 const previousRef=await write('plan.json',previous),owned={...normal(),ok:false,forced:true,timedOut:true,outputComplete:false,reason:'Total deadline reserved for owned cleanup'};
 const ownedRef=await write('controller-owned.json',owned),callback={callback_received:true,error:{code:1,killed:false},plan_sha256:previousRef.sha256,controller_owned_sha256:ownedRef.sha256};
 const callbackRef=await write('callback.json',callback),baseline={rootSchema:{},order:'',leaves:{}},baselineRef=await write('baseline.private.json',baseline);
 const nextBinding={...b,build_id:'f3a1de11-1811-4ef5-bf5c-586a70b7db9e'},nextAuthority=authority(nextBinding),p=plan(nextBinding,nextAuthority);
 p.fixture_root=fixture;p.evidence_root=next;p.environment=previous.environment;
 const nextAuthorityFile=path.join(next,'authority.json');await fs.writeFile(nextAuthorityFile,encoded(nextAuthority));p.authority=await pin(nextAuthorityFile);
 const s=await ordinary(fixture);p.recovery={schema:'books-pa1-one-failed-attempt-v1',attempt:2,cache_refresh:[],fixture_root:fixture,fixture_identity:{dev:s.dev,ino:s.ino,nlink:s.nlink},exe_identity:await ordinary(path.join(app,'Books Arranger.exe'),{file:true}),original_plan:previousRef,original_controller_owned:ownedRef,original_callback:callbackRef,original_baseline:baselineRef,original_artifact_manifest:artifactRef};
 const replaceOwned=async value=>{p.recovery.original_controller_owned=await write('controller-owned.json',value);callback.controller_owned_sha256=p.recovery.original_controller_owned.sha256;p.recovery.original_callback=await write('callback.json',callback);};
 return {p,nextAuthority,previous,owned,callback,artifact,baseline,app,write,replaceOwned};
}

test('one forced but fully closed attempt reuses only its exact unchanged app and original baseline',async t=>{
 const f=await failedAttemptFixture(t);validatePlan(f.p,f.nextAuthority);const prior=await verifyRecovery(f.p);
 assert.deepEqual(prior.baseline,f.baseline);assert.equal(prior.previous.fixture_root,f.p.fixture_root);
 assert.equal(await freshFixture(f.p,f.artifact),f.app);assert.equal((await fs.readFile(path.join(f.app,'Books Arranger.exe'))).toString(),'inert original payload');
 assert.throws(()=>normalOwned(f.owned),'the forced first attempt remains a failure');
});

test('recovery refuses unknown/live closure, forged callback, new fixture and chained attempts',async t=>{
 const f=await failedAttemptFixture(t);
 for(const alter of [o=>o.forced=false,o=>o.closed=false,o=>o.native.zero=false,o=>o.native.complete=false,o=>o.native.active=1,o=>o.native.unsignaled=1,o=>o.closureError='unknown']){
  const bad=structuredClone(f.owned);alter(bad);await f.replaceOwned(bad);await assert.rejects(verifyRecovery(f.p));
 }
 await f.replaceOwned(f.owned);const good=structuredClone(f.p);
 f.callback.plan_sha256='0'.repeat(64);f.p.recovery.original_callback=await f.write('callback.json',f.callback);await assert.rejects(verifyRecovery(f.p),/callback provenance/);
 f.p=good;f.callback.plan_sha256=good.recovery.original_plan.sha256;await f.replaceOwned(f.owned);
 f.p.recovery.fixture_identity.ino=String(BigInt(f.p.recovery.fixture_identity.ino)+1n);await assert.rejects(verifyRecovery(f.p),/fixture identity/);
 f.p.recovery.fixture_identity=good.recovery.fixture_identity;
 f.previous.recovery={};f.p.recovery.original_plan=await f.write('plan.json',f.previous);await assert.rejects(verifyRecovery(f.p),/Chained/);
});

test('recovery cannot adopt another release, escape its bound arena or change the original payload',async t=>{
 const f=await failedAttemptFixture(t);f.p.binding.version='0.24.3';await assert.rejects(verifyRecovery(f.p),/same release/);f.p.binding.version='0.24.2';
 for(const alter of [p=>p.recovery.attempt=6,p=>p.fixture_root='C:/foreign/pa1-'+p.binding.build_id,p=>p.recovery.original_plan.path='C:/foreign/plan.json',p=>p.recovery.extra=true]){const p=structuredClone(f.p);alter(p);assert.throws(()=>validatePlan(p,f.nextAuthority));}
 await fs.writeFile(path.join(f.app,'Books Arranger.exe'),'changed private payload');await assert.rejects(freshFixture(f.p,f.artifact));
});

test('exact 93 generated-cache refresh preserves EXE identity, Python sources and the entire new payload',async t=>{
 const f=await failedAttemptFixture(t,true),payload=path.join(path.dirname(f.p.evidence_root),'verified-new-payload');await fs.cp(f.app,payload,{recursive:true});
 for(let n=0;n<93;n++)await fs.writeFile(path.join(payload,'resources/backend/__pycache__/module'+n+'.cpython-314.pyc'),'new cache '+n);
 const files=await treeFiles(payload),old=f.artifact.payload.files;
 f.p.recovery.cache_refresh=Object.keys(files).sort().filter(name=>!sameFileTree(old[name],files[name])).map(name=>{const source=name.replace('__pycache__/','').replace('.cpython-314.pyc','.py');return{path:name,old_sha256:old[name].sha256,new_sha256:files[name].sha256,size:files[name].size,source_path:source,source_sha256:files[source].sha256};});
 f.p.payload.root=payload;const identity=await ordinary(path.join(f.app,'Books Arranger.exe'),{file:true});
 assert.equal(recoveryCacheChanges(f.p,old,files).length,93);
 for(const alter of [v=>delete v['resources/backend/module0.py'],v=>v['resources/backend/module0.py'].sha256='0'.repeat(64),v=>v['Books Arranger.exe'].sha256='0'.repeat(64),v=>v['resources/backend/__pycache__/module0.cpython-314.pyc'].size++,v=>v['resources/backend/__pycache__/module0.cpython-314.pyc']=old['resources/backend/__pycache__/module0.cpython-314.pyc']]){const bad=structuredClone(files);alter(bad);assert.throws(()=>recoveryCacheChanges(f.p,old,bad));}
 const wrong=structuredClone(f.p);wrong.recovery.cache_refresh[0].new_sha256='0'.repeat(64);assert.throws(()=>recoveryCacheChanges(wrong,old,files),/manifest-pinned/);
 await freshFixture(f.p,{payload:{files}});assert.deepEqual(await treeFiles(f.app),files);assert.deepEqual(await ordinary(path.join(f.app,'Books Arranger.exe'),{file:true}),identity);
});

async function knownThirdFixture(t){
 const f=await failedAttemptFixture(t),second=f.p,dir=second.evidence_root;
 const pin=async file=>{const b=await fs.readFile(file),s=await fs.lstat(file,{bigint:true});return{path:file,size:b.length,sha256:hash(b),identity:{dev:String(s.dev),ino:String(s.ino),nlink:Number(s.nlink)}};};
 const write=async(name,value)=>{const file=path.join(dir,name);await fs.writeFile(file,encoded(value));return pin(file);};
 const base={...f.artifact,build_id:second.binding.build_id};const manifest=await write('artifact.json',base);second.binding.artifact_manifest_sha256=manifest.sha256;second.payload.manifest=manifest;
 second.authority=await write('authority.json',authority(second.binding));const secondRef=await write('plan.json',second);
 const inner={...normal(),ok:false,code:1},controller=structuredClone(inner),owned=await write('owned.json',inner),controllerRef=await write('controller-owned.json',controller);
 const cb={callback_received:true,error:{code:1,killed:false},plan_sha256:secondRef.sha256,owned_sha256:owned.sha256,controller_owned_sha256:controllerRef.sha256};
 const callback=await write('callback.json',cb),quit=await write('quit-owned.json',normal()),refresh=await write('refresh.json',{original_manifest_sha256:second.recovery.original_artifact_manifest.sha256,current_manifest_sha256:manifest.sha256,exe_identity:second.recovery.exe_identity,changes:[],whole_payload_matches_current:true});
 const p=structuredClone(second);p.binding={...p.binding,build_id:'c3a1de11-1811-4ef5-bf5c-586a70b7db9e'};p.evidence_root=path.join(path.dirname(dir),'third');await fs.mkdir(p.evidence_root);
 const a=authority(p.binding),authorityFile=path.join(p.evidence_root,'authority.json');await fs.writeFile(authorityFile,encoded(a));p.authority=await pin(authorityFile);
 const record={application:'Books Arranger',version:'0.24.2',pid:42,instance:'c'.repeat(32),port:61169,url:'http://127.0.0.1:61169/'};
 const live=path.join(p.fixture_root,'home/data/web-instance.json');await fs.mkdir(path.dirname(live),{recursive:true});await fs.writeFile(live,encoded(record));
 p.recovery.attempt=3;p.recovery.second_failed_attempt={plan:secondRef,owned,controller_owned:controllerRef,callback,quit_owned:quit,payload_manifest:manifest,cache_refresh:refresh};
 p.recovery.engine_port=61169;p.recovery.engine_record=await write('engine-record-copy.json',record);p.recovery.engine_record_identity=(await pin(live)).identity;
 return {p,a,write,inner,controller,callback:cb,record,live,base};
}

test('known third attempt binds both real failure categories and selects only the original private engine port',async t=>{
 const f=await knownThirdFixture(t);validatePlan(f.p,f.a);const prior=await verifyRecovery(f.p);
 assert.equal(prior.baseManifestSha,f.p.recovery.second_failed_attempt.payload_manifest.sha256);assert.notEqual(prior.baseManifestSha,f.p.recovery.original_artifact_manifest.sha256);
 const calls=[];assert.equal(await privateEnginePort(f.p,async port=>{calls.push(port);return port;}),61169);assert.deepEqual(calls,[61169]);
 assert.throws(()=>normalOwned(f.inner),'second failure is never accepted as a successful native run');
});

test('known third attempt refuses unknown second closure, forged callback or an unbound payload refresh',async t=>{
 const f=await knownThirdFixture(t),original=structuredClone(f.p.recovery.second_failed_attempt);
 for(const alter of [v=>v.forced=true,v=>v.timedOut=true,v=>v.native.zero=false,v=>v.native.active=1,v=>v.outputComplete=false,v=>v.code=0]){
  const bad=structuredClone(f.controller);alter(bad);const ref=await f.write('controller-owned.json',bad);f.p.recovery.second_failed_attempt.controller_owned=ref;
  f.callback.controller_owned_sha256=ref.sha256;f.p.recovery.second_failed_attempt.callback=await f.write('callback.json',f.callback);await assert.rejects(verifyRecovery(f.p));
 }
 f.p.recovery.second_failed_attempt=original;
 f.p.recovery.second_failed_attempt.controller_owned=await f.write('controller-owned.json',f.controller);f.callback.controller_owned_sha256=f.p.recovery.second_failed_attempt.controller_owned.sha256;
 f.callback.plan_sha256='0'.repeat(64);f.p.recovery.second_failed_attempt.callback=await f.write('callback.json',f.callback);await assert.rejects(verifyRecovery(f.p),/callback provenance/);
 f.callback.plan_sha256=f.p.recovery.second_failed_attempt.plan.sha256;f.p.recovery.second_failed_attempt.callback=await f.write('callback.json',f.callback);
 f.p.recovery.second_failed_attempt.cache_refresh=await f.write('refresh.json',{whole_payload_matches_current:false});await assert.rejects(verifyRecovery(f.p),/cache refresh provenance/);
});

test('private port selection refuses a busy port, fallback, changed record or wrong saved URL before app launch',async t=>{
 const f=await knownThirdFixture(t);let calls=0;
 await assert.rejects(privateEnginePort(f.p,async port=>{calls++;assert.equal(port,61169);throw Error('EADDRINUSE');}),/EADDRINUSE/);assert.equal(calls,1);
 await assert.rejects(privateEnginePort(f.p,async()=>0),/no fallback/);
 await fs.writeFile(f.live,encoded({...f.record,port:61170}));calls=0;await assert.rejects(privateEnginePort(f.p,async()=>{calls++;return 61169;}));assert.equal(calls,0);
 f.p.recovery.engine_record=await f.write('wrong-record-copy.json',{...f.record,url:'http://127.0.0.1:61170/'});await assert.rejects(privateEnginePort(f.p,async()=>{calls++;return 61169;}),/Exact original private engine port record/);assert.equal(calls,0);
});

test('private Quit command has a finite wait without any PID kill or command fallback',async()=>{
 const calls=[],spawn=(file,args)=>{calls.push({file,args});return{once(){return this;}};};
 const fixture=createPrivateShellCommands({spawn,exe:'C:/private/app/Books Arranger.exe',profile:'C:/private/profile',env:{},timeoutMs:5});
 await assert.rejects(fixture.quit(),/timed out/);assert.equal(calls.length,1);assert.equal(calls[0].args[0],'--quit');
 assert.throws(()=>createPrivateShellCommands({spawn,exe:'C:/private/app/Books Arranger.exe',profile:'C:/private/profile',env:{},timeoutMs:60001}));
});

function tcpRows(rows){const b=Buffer.alloc(4+24*rows.length);b.writeUInt32LE(rows.length);rows.forEach((r,n)=>{const at=4+n*24;b.writeUInt32LE(r.state??0,at);Buffer.from(r.address||[127,0,0,1]).copy(b,at+4);b.writeUInt16BE(r.port??61169,at+8);b.writeUInt32LE(r.pid??42,at+20);});return b;}
test('exact SDK listener-only role keeps raw state diagnostics without mapping state zero to LISTEN',()=>{
 for(const state of [0,2]){const buffer=tcpRows([{state}]);assert.deepEqual(listenerOnlyRows(buffer,3,2,61169),[{pid:42,state,listenerTableClass:3}]);assert.equal(buffer.readUInt32LE(4),state);}
 for(const cls of [0,4,5])assert.throws(()=>listenerOnlyRows(tcpRows([{state:0}]),cls,2,61169),/listener-only query/);
 assert.throws(()=>listenerOnlyRows(tcpRows([{}]),3,23,61169),/IPv4/);
});
test('listener-role decoder rejects nonlistener contradictions, wildcard, unknown owner, duplicate and malformed rows',()=>{
 for(const state of [1,3,4,5,6,7,8,9,10,11,12,0xffffffff])assert.throws(()=>listenerOnlyRows(tcpRows([{state}]),3,2,61169),/non-listener/);
 for(const address of [[0,0,0,0],[192,168,1,2],[127,0,0,2]])assert.throws(()=>listenerOnlyRows(tcpRows([{address}]),3,2,61169),/loopback-only/);
 assert.throws(()=>listenerOnlyRows(tcpRows([{pid:0}]),3,2,61169),/PID/);assert.throws(()=>listenerOnlyRows(tcpRows([{},{}]),3,2,61169),/Ambiguous/);
 assert.throws(()=>listenerOnlyRows(Buffer.alloc(3),3,2,61169));const truncated=tcpRows([{}]);truncated.writeUInt32LE(2);assert.throws(()=>listenerOnlyRows(truncated,3,2,61169),/truncated/);
 assert.deepEqual(listenerOnlyRows(tcpRows([{port:61170}]),3,2,61169),[],'another port supplies no positive role evidence');
});

async function knownFourthFixture(t){
 const f=await knownThirdFixture(t),third=f.p,dir=third.evidence_root;
 const pin=async file=>{const b=await fs.readFile(file),s=await fs.lstat(file,{bigint:true});return{path:file,size:b.length,sha256:hash(b),identity:{dev:String(s.dev),ino:String(s.ino),nlink:Number(s.nlink)}};};
 const write=async(name,value)=>{const file=path.join(dir,name);await fs.writeFile(file,encoded(value));return pin(file);};
 const base={...f.base,build_id:third.binding.build_id},manifest=await write('artifact.json',base);third.binding.artifact_manifest_sha256=manifest.sha256;third.payload.manifest=manifest;third.authority=await write('authority.json',authority(third.binding));
 const planRef=await write('plan.json',third),inner={...normal(),ok:false,code:1},controller=structuredClone(inner),owned=await write('owned.json',inner),controllerRef=await write('controller-owned.json',controller);
 const callback={callback_received:true,error:{code:1,killed:false},plan_sha256:planRef.sha256,owned_sha256:owned.sha256,controller_owned_sha256:controllerRef.sha256},cb=await write('callback.json',callback);
 const refresh=await write('refresh.json',{original_manifest_sha256:third.recovery.original_artifact_manifest.sha256,base_manifest_sha256:third.recovery.second_failed_attempt.payload_manifest.sha256,current_manifest_sha256:manifest.sha256,exe_identity:third.recovery.exe_identity,changes:third.recovery.cache_refresh,whole_payload_matches_current:true});
 const p=structuredClone(third);p.binding={...p.binding,build_id:'d3a1de11-1811-4ef5-bf5c-586a70b7db9e'};p.evidence_root=path.join(path.dirname(dir),'fourth');await fs.mkdir(p.evidence_root);const a=authority(p.binding),file=path.join(p.evidence_root,'authority.json');await fs.writeFile(file,encoded(a));p.authority=await pin(file);
 p.recovery.attempt=4;p.recovery.engine_record_absent=true;p.recovery.third_failed_attempt={plan:planRef,callback:cb,owned,controller_owned:controllerRef,payload_manifest:manifest,cache_refresh:refresh};await fs.unlink(f.live);
 return {p,a,live:f.live,write,callback,controller,record:f.record};
}
test('known fourth attempt binds all three failures and the current base while requiring an absent live control record',async t=>{
 const f=await knownFourthFixture(t);validatePlan(f.p,f.a);const prior=await verifyRecovery(f.p);assert.equal(prior.baseManifestSha,f.p.recovery.third_failed_attempt.payload_manifest.sha256);
 const calls=[];assert.equal(await privateEnginePort(f.p,async port=>{calls.push(port);return port;}),61169);assert.deepEqual(calls,[61169]);
 await fs.writeFile(f.live,encoded(f.record));await assert.rejects(privateEnginePort(f.p,async()=>{throw Error('probe must not run');}),/unexpectedly exists/);
});
test('known fourth attempt refuses a relabelled history, unknown third closure and unrecorded next attempt',async t=>{
 const f=await knownFourthFixture(t),bad=structuredClone(f.p);bad.recovery.attempt=5;assert.throws(()=>validatePlan(bad,f.a));
 f.p.recovery.engine_record_absent=false;await assert.rejects(verifyRecovery(f.p),/cleanly removed control record/);f.p.recovery.engine_record_absent=true;
 const v=structuredClone(f.controller);v.native.zero=false;const ref=await f.write('controller-owned.json',v);f.p.recovery.third_failed_attempt.controller_owned=ref;f.callback.controller_owned_sha256=ref.sha256;f.p.recovery.third_failed_attempt.callback=await f.write('callback.json',f.callback);await assert.rejects(verifyRecovery(f.p),/normal closure/);
});

async function knownFifthFixture(t){
 const f=await knownFourthFixture(t),fourth=f.p,dir=fourth.evidence_root;
 const write=async(name,value)=>{const file=path.join(dir,name),b=encoded(value);await fs.writeFile(file,b);const s=await fs.lstat(file,{bigint:true});return {path:file,size:b.length,sha256:hash(b),identity:{dev:String(s.dev),ino:String(s.ino),nlink:Number(s.nlink)}};};
 const base=JSON.parse(await readPin(fourth.recovery.third_failed_attempt.payload_manifest));base.build_id=fourth.binding.build_id;const manifest=await write('artifact.json',base);fourth.binding.artifact_manifest_sha256=manifest.sha256;fourth.payload.manifest=manifest;fourth.authority=await write('authority.json',authority(fourth.binding));
 const planRef=await write('plan.json',fourth),inner={...normal(),ok:false,code:1},owned=await write('owned.json',inner),controller=structuredClone(inner),controllerRef=await write('controller-owned.json',controller);
 const callback={callback_received:true,error:{code:1,killed:false},plan_sha256:planRef.sha256,owned_sha256:owned.sha256,controller_owned_sha256:controllerRef.sha256},cb=await write('callback.json',callback);
 const refresh=await write('refresh.json',{original_manifest_sha256:fourth.recovery.original_artifact_manifest.sha256,base_manifest_sha256:fourth.recovery.third_failed_attempt.payload_manifest.sha256,current_manifest_sha256:manifest.sha256,exe_identity:fourth.recovery.exe_identity,changes:fourth.recovery.cache_refresh,whole_payload_matches_current:true});
 const p=structuredClone(fourth);p.binding={...p.binding,build_id:'f3a1de11-1811-4ef5-bf5c-586a70b7db9e'};p.evidence_root=path.join(path.dirname(dir),'fifth');await fs.mkdir(p.evidence_root);const a=authority(p.binding);const b=encoded(a),file=path.join(p.evidence_root,'authority.json');await fs.writeFile(file,b);const s=await fs.lstat(file,{bigint:true});p.authority={path:file,size:b.length,sha256:hash(b),identity:{dev:String(s.dev),ino:String(s.ino),nlink:Number(s.nlink)}};
 p.recovery.attempt=5;p.recovery.fourth_failed_attempt={plan:planRef,callback:cb,owned,controller_owned:controllerRef,payload_manifest:manifest,cache_refresh:refresh};return {...f,p,a,write,callback,controller};
}
test('known fifth attempt pins all four actual failure categories and current payload with absent control record',async t=>{
 const f=await knownFifthFixture(t);validatePlan(f.p,f.a);const prior=await verifyRecovery(f.p);assert.equal(prior.baseManifestSha,f.p.recovery.fourth_failed_attempt.payload_manifest.sha256);assert.equal(await privateEnginePort(f.p,async port=>port),61169);
 await fs.writeFile(f.live,encoded(f.record));await assert.rejects(privateEnginePort(f.p,async()=>{throw Error('must not probe');}),/unexpectedly exists/);
});
test('known fifth refuses missing fourth provenance, forced fourth closure and arbitrary sixth attempt',async t=>{
 const f=await knownFifthFixture(t),bad=structuredClone(f.p);delete bad.recovery.fourth_failed_attempt;assert.throws(()=>validatePlan(bad,f.a),/Exact failed-attempt/);bad.recovery=f.p.recovery;bad.recovery={...bad.recovery,attempt:6};assert.throws(()=>validatePlan(bad,f.a));
 const v=structuredClone(f.controller);v.forced=true;const ref=await f.write('controller-owned.json',v);f.p.recovery.fourth_failed_attempt.controller_owned=ref;f.callback.controller_owned_sha256=ref.sha256;f.p.recovery.fourth_failed_attempt.callback=await f.write('callback.json',f.callback);await assert.rejects(verifyRecovery(f.p),/normal closure/);
});
function witnessFixture(){const handle={},calls=[],buffer=Buffer.alloc(8+8192*8);buffer.writeUInt32LE(2,0);buffer.writeUInt32LE(2,4);buffer.writeBigUInt64LE(101n,8);buffer.writeBigUInt64LE(202n,16);const api={create:()=>{calls.push('create');return handle;},configure:(h,flags)=>{assert.equal(h,handle);assert.equal(flags,0);calls.push('configure');return true;},assignSelf:h=>{assert.equal(h,handle);calls.push('assign');return true;},flags:h=>{assert.equal(h,handle);return 0;},query:h=>{assert.equal(h,handle);calls.push('query-explicit');return buffer;},belongs:(p,h)=>{assert.equal(h,handle);return p==='owned';},close:h=>{assert.equal(h,handle);calls.push('close');return true;}};return {handle,calls,buffer,api};}
test('explicit query-only witness retains fixed handle, checks current worker and rejects foreign process',()=>{const f=witnessFixture(),w=membershipWitness(f.api,101);assert.deepEqual(f.calls.slice(0,3),['create','configure','assign']);assert.deepEqual(w.members(),[101,202]);assert.equal(w.contains('owned'),true);assert.equal(w.contains('foreign'),false);w.close();w.close();assert.equal(f.calls.filter(x=>x==='close').length,1);assert.throws(()=>w.members(),/closed/);});
test('witness rejects kill-on-close or breakaway flags, failed assignment, incomplete list and missing worker',()=>{for(const flags of [0x2000,0x800,0x1000]){const f=witnessFixture();f.api.flags=()=>flags;assert.throws(()=>membershipWitness(f.api,101),/no breakaway or kill/);assert.equal(f.calls.at(-1),'close');}const failed=witnessFixture();failed.api.assignSelf=()=>false;assert.throws(()=>membershipWitness(failed.api,101),/Cannot assign/);assert.equal(failed.calls.at(-1),'close');for(const mutate of [b=>b.writeUInt32LE(3,0),b=>b.writeBigUInt64LE(303n,8),b=>b.writeBigUInt64LE(101n,16)]){const f=witnessFixture();mutate(f.buffer);assert.throws(()=>membershipWitness(f.api,101));assert.equal(f.calls.at(-1),'close');}});

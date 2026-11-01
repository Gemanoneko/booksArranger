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
const {validatePlan,ownLeafDelta,cleanupOwnLeaf,nativeAdapters,requiredWindowPid,sameFileTree,ordinary,readPin,treeFiles,verifyInputs,freshFixture,createPrivateShellCommands,verifyCloseSession}=await import('./real-shell-update-support.mjs');
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

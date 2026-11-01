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
const {releaseFlow,gitEntries}=await import('../scripts/release-flow.mjs');
const {productTree}=await import('../scripts/release-contract.mjs');
const {PA1_ASSERTIONS,NATIVE_CASE,NATIVE_ROLES}=await import('../scripts/qa-phase-contract.mjs');
const {default:cleanup}=await import('../scripts/cleanup-releases.js');

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

const pin='b'.repeat(40),id='d9ee38b0-6d35-4a5e-8cc5-bba1c08a91f4',hex='a'.repeat(64),tag='v0.24.2';
const entry={mode:'100644',object:pin,name:'desktop/main.js'};
function fixture({version='0.24.2',mutations={}}={}) {
 const events=[],digest=productTree([entry]),releaseTag='v'+version;
 const names=['Books-Arranger-Setup-'+version+'.exe','Books-Arranger-Setup-'+version+'.exe.blockmap','latest.yml'];
 const manifest={schema:'books-desktop-artifacts-v1',version,product_digest:digest,source_head:pin,build_id:id,unpacked:'builds/'+id+'/win-unpacked',payload:{verified:true,installer_equivalent:true,shell_version:version,backend_version:version},runtime:{schema:'inert-unit-runtime-v1',python:'f'.repeat(64)},artifacts:names.map(name=>({path:'builds/'+id+'/'+name,size:123,sha256:hex}))};
 const raw=JSON.stringify(manifest),manifestHash=sha(raw),phaseRaw='// inert phase contract bytes, no native authority\n';
 const report=verdict=>'**Verdict:** '+verdict+'\nRelease source commit: '+pin+'\nRelease artifact manifest SHA256: '+manifestHash+'\n';
 const pkg={version,build:{directories:{output:'dist'},publish:{provider:'github',owner:'Gemanoneko',repo:'booksArranger',releaseType:'release'}}};
 const qaPath='Docs/BooksArranger_QA_v'+version+'_2026-10-13.md',reviewPath='Docs/BooksArranger_CodeReview_v'+version+'_2026-10-13.md';
 const files={'package.json':JSON.stringify(pkg),'package-lock.json':JSON.stringify({version,packages:{'':{version}}}),'dist/release-artifacts.json':raw,[qaPath]:report('GO'),[reviewPath]:report('RELEASE CLEAR'),'scripts/qa-phase-contract.mjs':phaseRaw};
 files['Docs/BooksArranger_ReleaseAcceptance_v'+version+'.json']=JSON.stringify({schema:'books-desktop-acceptance-v1',version,qa:qaPath,review:reviewPath});
 const expected={version,source_head:pin,product_digest:digest,build_id:id,artifact_manifest_sha256:manifestHash,runtime_manifest_sha256:sha(JSON.stringify(manifest.runtime)),phase_contract_sha256:sha(phaseRaw)};
 const bundle=nativeBundle(expected,mutations),summaryPath='Docs/BooksArranger_NativeQA_v'+version+'.json';
 const summaryRaw=JSON.stringify(bundle.summary);
 files[summaryPath]=summaryRaw;files[qaPath]+='Native QA evidence SHA256: '+sha(summaryRaw)+'\n';
 for(const role of NATIVE_ROLES)files[bundle.summary.records[role].path]=bundle.records[role];
 let published=false;
 const io={
  run:async(cmd,args,options)=>{events.push([cmd,...args]);if(cmd==='node-builder'){assert.equal(options.credential,true);published=true;return{stdout:''};}assert.equal(cmd,'git');assert.equal(options.credential,false);let out='';switch(args[0]){case'config':out='https://github.com/Gemanoneko/booksArranger.git';break;case'status':break;case'rev-parse':out=pin;break;case'ls-tree':out='100644 blob '+pin+'\tdesktop/main.js\0';break;case'tag':out='v0.15.0\n'+releaseTag;break;case'ls-remote':out=pin+'\trefs/tags/'+releaseTag+'^{}';break;case'merge-base':break;default:throw Error('unexpectedgit');}return{stdout:out};},
  read:async path=>{events.push(['read',path]);if(!(path in files))throw Error('missingfile: '+path);return files[path];},
  exists:async path=>path in files,
  prepare:async()=>events.push(['prepare']),
  verifyPayload:async()=>events.push(['verify']),
  hash:async path=>{events.push(['hash',path]);if(path in files){const bytes=Buffer.from(files[path]);return{sha256:sha(bytes),size:bytes.length};}if(manifest.artifacts.some(a=>'dist/'+a.path===path))return{sha256:hex,size:123};throw Error('missingfile: '+path);},
  authenticate:async()=>events.push(['auth']),
  api:async(method,path)=>{events.push([method,path]);return published?{tag_name:releaseTag,draft:false,prerelease:false,assets:names.map(name=>({name,size:123,state:'uploaded',digest:'sha256:'+hex}))}:null;},
  cleanup:async()=>events.push(['cleanup'])
 };
 return {io,files,events,bundle,summaryPath,qaPath,manifest,expected};
}
function fileSnapshot(files){return Object.fromEntries(Object.entries(files).map(([name,bytes])=>[name,Buffer.from(bytes).toString('hex')]));}
async function refusesBeforeEffects(f,pattern){
 const before=fileSnapshot(f.files);
 await assert.rejects(()=>releaseFlow(f.io),pattern);
 assert.equal(f.events.some(e=>['auth','node-builder','verify','prepare','cleanup','GET','POST','DELETE'].includes(e[0])),false,'invalid native proof must stop before credentials, publishing, payload verification or mutation');
 assert.deepEqual(fileSnapshot(f.files),before,'refused proof must leave every input byte unchanged');
 assert.deepEqual(nativeAttempts,[]);
}
test('publishes only accepted files then verifies remote before cleanup',async()=>{const f=fixture(),result=await releaseFlow(f.io);assert.equal(result.tag,tag);assert.equal(f.events.filter(e=>e[0]==='node-builder').length,1);assert.equal(f.events.some(e=>e[0]==='prepare'),false);assert.equal(f.events.at(-1)[0],'cleanup');});
test('missing candidate prepares and stops before credentials/publication',async()=>{const f=fixture();delete f.files['dist/release-artifacts.json'];await assert.rejects(()=>releaseFlow(f.io),/candidate prepared/);assert.equal(f.events.some(e=>e[0]==='auth'||e[0]==='node-builder'),false);});
test('changed candidate or NO-GO never authenticates or publishes',async()=>{for(const mode of ['hash','verdict']){const f=fixture();f.files['Docs/BooksArranger_QA_v0.24.2_2026-10-13.md']=f.files['Docs/BooksArranger_QA_v0.24.2_2026-10-13.md'].replace(mode==='hash'?/[a-f0-9]{64}/:'GO',mode==='hash'?'c'.repeat(64):'NO-GO');await assert.rejects(()=>releaseFlow(f.io));assert.equal(f.events.some(e=>e[0]==='auth'||e[0]==='node-builder'),false);}});
test('zero-exit builder is not success if remote asset hashes differ',async()=>{const f=fixture(),api=f.io.api;f.io.api=async(...args)=>{const r=await api(...args);if(r)r.assets[0].digest='sha256:'+'c'.repeat(64);return r;};await assert.rejects(()=>releaseFlow(f.io),/Remote asset mismatch/);assert.equal(f.events.some(e=>e[0]==='cleanup'),false);});
test('submodules/special Git entries are not silently excluded',()=>assert.throws(()=>gitEntries('160000 commit '+pin+'\tsubmodule\0')));
test('cleanup verifies identities and preserves current release',async()=>{
 let releases=Array.from({length:5},(_,i)=>({id:i+1,tag_name:'v0.'+(20-i)+'.0',created_at:new Date(2026,9,13-i).toISOString(),draft:false,prerelease:false}));const deletes=[];
 const api=async(method,path)=>{if(method==='DELETE'){deletes.push(path);if(path.endsWith('/releases/5'))releases=releases.filter(r=>r.id!==5);return null;}if(path.includes('?'))return releases;if(path.endsWith('/releases/5'))return releases.find(r=>r.id===5);throw Error('unexpected');};
 const receipt=await cleanup.cleanupReleases(api,'/repos/Gemanoneko/booksArranger','v0.20.0');assert.equal(receipt.remaining.length,4);assert.equal(deletes.length,2);assert.ok(!deletes.some(p=>p.includes('v0.20.0')));
});

test('valid current native bundle reaches original release assertions in gate order',async()=>{
 const f=fixture();await releaseFlow(f.io);
 const locate=name=>f.events.findIndex(e=>e[0]===name),lastEvidence=Math.max(...f.events.map((e,i)=>e[0]==='read'&&e[1].includes('_Evidence/')?i:-1));
 assert.ok(lastEvidence>=0&&lastEvidence<locate('verify'));
 assert.ok(locate('verify')<locate('auth')&&locate('auth')<locate('node-builder'));
 assert.deepEqual(nativeAttempts,[]);
});
test('missing native evidence blocks every current and future publish before credentials',async()=>{
 for(const version of ['0.24.2','0.24.3','0.25.0','1.0.0','2.0.0']){const f=fixture({version});delete f.files[f.summaryPath];await refusesBeforeEffects(f,/missingfile/);}
});
test('GO prose missing duplicate stale or invented native summary SHA is insufficient',async()=>{
 for(const change of [f=>f.files[f.qaPath]=f.files[f.qaPath].replace(/^Native QA evidence SHA256:.*\n/m,''),f=>f.files[f.qaPath]+=f.files[f.qaPath].match(/^Native QA evidence SHA256:.*$/m)[0]+'\n',f=>f.files[f.qaPath]=f.files[f.qaPath].replace(/(Native QA evidence SHA256: )([a-f0-9]{64})/,'$1'+'f'.repeat(64)),f=>f.files[f.summaryPath]+=' ']){const f=fixture();change(f);await refusesBeforeEffects(f,/native QA evidence hash|Native QA summary/i);}
});
test('candidate source version product build artifact runtime and phase mismatches refuse publish',async()=>{
 const changes={version:'0.24.3',source_head:'f'.repeat(40),product_digest:'f'.repeat(64),build_id:'e9ee38b0-6d35-4a5e-8cc5-bba1c08a91f4',artifact_manifest_sha256:'f'.repeat(64),runtime_manifest_sha256:'f'.repeat(64),phase_contract_sha256:'f'.repeat(64)};
 for(const [field,value] of Object.entries(changes)){const f=fixture({mutations:{summary:s=>s.binding[field]=value}});await refusesBeforeEffects(f,/different candidate/);}
});
test('each missing or changed raw native record stops before payload and credentials',async()=>{
 for(const role of NATIVE_ROLES){for(const mode of ['missing','tampered']){const f=fixture(),path=f.bundle.summary.records[role].path;if(mode==='missing')delete f.files[path];else f.files[path]=Buffer.concat([Buffer.from(f.files[path]),Buffer.from(' ')]);await refusesBeforeEffects(f,/missingfile|Native QA raw record differs/);}}
});
test('unsafe duplicate oversized and cross-version native references refuse before referenced reads',async()=>{
 for(const change of [s=>s.records.plan.path='../outside.json',s=>s.records.plan.path='C:/outside.json',s=>s.records.plan.path=s.records.owned.path,s=>s.records.plan.path=s.records.plan.path.replace('0.24.2','0.24.1'),s=>s.records.plan.size=32*1024*1024+1]){
  const f=fixture();change(f.bundle.summary);f.files[f.summaryPath]=JSON.stringify(f.bundle.summary);f.files[f.qaPath]=f.files[f.qaPath].replace(/(Native QA evidence SHA256: )([a-f0-9]{64})/,'$1'+sha(f.files[f.summaryPath]));
  await refusesBeforeEffects(f,/Unsafe\/duplicate native evidence path|Native record bounds/);
  assert.equal(f.events.some(e=>e[0]==='read'&&e[1].includes('_Evidence/')),false,'references are validated as a set before records are read');
 }
});
test('normal ownership callback postflight and cleanup failures all block publishing',async()=>{
 const cases=[['owned',r=>r.forced=true],['owned',r=>r.timedOut=true],['owned',r=>r.overflow=true],['owned',r=>r.truncated=true],['owned',r=>r.native.zero=false],['controller_owned',r=>r.outputComplete=false],['controller_owned',r=>r.native.assigned=1],['callback',r=>r.callback_received=false],['callback',r=>r.write_errors=['failure']],['callback',r=>r.start_write_error='failure'],['postflight',r=>r.unchanged=false],['cleanup',r=>r.deleted=false],['cleanup',r=>r.closed=false],['cleanup',r=>r.partial=true],['cleanup',r=>r.preexistingUnchanged=false],['cleanup',r=>r.uiOrderListWritten=true]];
 for(const [role,mutate] of cases){const f=fixture({mutations:{[role]:mutate}});await refusesBeforeEffects(f);}
});
test('skipped duplicate replacement or incomplete native case cannot publish despite coherent hashes',async()=>{
 const cases=[['functional',r=>r.assertions.pop()],['functional',r=>r.case.title='different test'],['functional',r=>r.oldEngineRecovered=false],['owned',r=>r.out=r.out.replace('# skipped 0','# skipped 1')],['owned',r=>r.out+=r.out.split('\n')[0]+'\n']];
 for(const [role,mutate] of cases){const f=fixture({mutations:{[role]:mutate}});await refusesBeforeEffects(f);}
});
test('authority is required for this candidate and cannot be inferred from GO',async()=>{
 for(const mutate of [a=>a.approved_by='agent',a=>a.decision_ref='PENDING',a=>a.effects.hidden_private_app=false,a=>a.effects.ui_order_list_write=true,a=>a.binding.build_id='e9ee38b0-6d35-4a5e-8cc5-bba1c08a91f4'])await refusesBeforeEffects(fixture({mutations:{authority:mutate}}));
});
test('historical artifacts or reports cannot replace current publish prerequisites',async()=>{
 for(const change of [f=>{const m=JSON.parse(f.files['dist/release-artifacts.json']);m.version='0.16.0';f.files['dist/release-artifacts.json']=JSON.stringify(m);},f=>{const path='Docs/BooksArranger_ReleaseAcceptance_v0.24.2.json';const a=JSON.parse(f.files[path]);a.version='0.16.0';f.files[path]=JSON.stringify(a);},f=>{f.files[f.qaPath]=f.files[f.qaPath].replace(/^Native QA evidence SHA256:.*\n/m,'');}]){const f=fixture();change(f);await refusesBeforeEffects(f);}
});
test('native summary size or hash races cannot authenticate',async()=>{
 for(const mode of ['oversize','read-drift']){const f=fixture(),hash=f.io.hash,read=f.io.read;f.io.hash=async path=>{const result=await hash(path);return path===f.summaryPath&&mode==='oversize'?{...result,size:128*1024+1}:result;};f.io.read=async path=>{const raw=await read(path);return path===f.summaryPath&&mode==='read-drift'?raw+' ':raw;};await refusesBeforeEffects(f,/Native QA summary/);}
});

test('coherently rehashed inner-stream callback binding refuses before credentials or publication',async()=>{
 const f=fixture(),e=f.bundle,callback=JSON.parse(e.records.callback);
 for(const role of ['stdout','stderr']){assert.notDeepEqual(e.records[role],e.records['controller_'+role]);callback[role+'_sha256']=sha(e.records[role]);callback[role+'_bytes']=e.records[role].length;}
 const bytes=encode(callback),ref=e.summary.records.callback;ref.sha256=sha(bytes);ref.size=bytes.length;f.files[ref.path]=bytes;
 f.files[f.summaryPath]=JSON.stringify(e.summary);f.files[f.qaPath]=f.files[f.qaPath].replace(/(Native QA evidence SHA256: )([a-f0-9]{64})/,'$1'+sha(f.files[f.summaryPath]));
 await refusesBeforeEffects(f,/Outer callback must bind original controller streams/);
});

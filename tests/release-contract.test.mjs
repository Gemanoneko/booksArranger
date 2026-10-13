import test from 'node:test';
import assert from 'node:assert/strict';
import { acceptanceIndex, packageContract, newer, reportPin, reportManifest, productTree, artifactContract, remoteArtifacts, releasesToPrune } from '../scripts/release-contract.mjs';
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

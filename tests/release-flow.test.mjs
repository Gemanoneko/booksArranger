import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { releaseFlow,gitEntries } from '../scripts/release-flow.mjs';
import { productTree } from '../scripts/release-contract.mjs';
import cleanup from '../scripts/cleanup-releases.js';
const pin='b'.repeat(40),id='d9ee38b0-6d35-4a5e-8cc5-bba1c08a91f4',hex='a'.repeat(64),tag='v0.16.0';
const entry={mode:'100644',object:pin,name:'desktop/main.js'};
function fixture() {
 const events=[],digest=productTree([entry]),names=['Books-Arranger-Setup-0.16.0.exe','Books-Arranger-Setup-0.16.0.exe.blockmap','latest.yml'];
 const manifest={schema:'books-desktop-artifacts-v1',version:'0.16.0',product_digest:digest,source_head:pin,build_id:id,unpacked:'builds/'+id+'/win-unpacked',payload:{verified:true,installer_equivalent:true,shell_version:'0.16.0',backend_version:'0.16.0'},artifacts:names.map(name=>({path:'builds/'+id+'/'+name,size:123,sha256:hex}))};
 const raw=JSON.stringify(manifest),hash=createHash('sha256').update(raw).digest('hex');
 const report=verdict=>'**Verdict:** '+verdict+'\nRelease source commit: '+pin+'\nRelease artifact manifest SHA256: '+hash+'\n';
 const pkg={version:'0.16.0',build:{directories:{output:'dist'},publish:{provider:'github',owner:'Gemanoneko',repo:'booksArranger',releaseType:'release'}}};
 const files={'package.json':JSON.stringify(pkg),'package-lock.json':JSON.stringify({version:pkg.version,packages:{'':{version:pkg.version}}}),'dist/release-artifacts.json':raw,'Docs/BooksArranger_QA_v0.16.0_2026-10-13.md':report('GO'),'Docs/BooksArranger_CodeReview_v0.16.0_2026-10-13.md':report('RELEASE CLEAR')};
 files['Docs/BooksArranger_ReleaseAcceptance_v0.16.0.json']=JSON.stringify({schema:'books-desktop-acceptance-v1',version:'0.16.0',qa:'Docs/BooksArranger_QA_v0.16.0_2026-10-13.md',review:'Docs/BooksArranger_CodeReview_v0.16.0_2026-10-13.md'});
 let published=false;
 const io={
  run:async(cmd,args)=>{events.push([cmd,...args]);if(cmd==='node-builder'){published=true;return{stdout:''};}let out='';switch(args[0]){case'config':out='https://github.com/Gemanoneko/booksArranger.git';break;case'status':break;case'rev-parse':out=pin;break;case'ls-tree':out='100644 blob '+pin+'\tdesktop/main.js\0';break;case'tag':out='v0.15.0\n'+tag;break;case'ls-remote':out=pin+'\trefs/tags/'+tag+'^{}';break;case'merge-base':break;default:throw Error('unexpectedgit');}return{stdout:out};},
  read:async path=>{if(!(path in files))throw Error('missingfile');return files[path];},exists:async p=>p in files,prepare:async()=>events.push(['prepare']),verifyPayload:async()=>events.push(['verify']),hash:async()=>({sha256:hex,size:123}),authenticate:async()=>events.push(['auth']),
  api:async(method,path)=>{events.push([method,path]);return published?{tag_name:tag,draft:false,prerelease:false,assets:names.map(name=>({name,size:123,state:'uploaded',digest:'sha256:'+hex}))}:null;},cleanup:async()=>events.push(['cleanup'])};
 return {io,files,events};
}
test('publishes only accepted files then verifies remote before cleanup',async()=>{const f=fixture(),result=await releaseFlow(f.io);assert.equal(result.tag,tag);assert.equal(f.events.filter(e=>e[0]==='node-builder').length,1);assert.equal(f.events.some(e=>e[0]==='prepare'),false);assert.equal(f.events.at(-1)[0],'cleanup');});
test('missing candidate prepares and stops before credentials/publication',async()=>{const f=fixture();delete f.files['dist/release-artifacts.json'];await assert.rejects(()=>releaseFlow(f.io),/candidate prepared/);assert.equal(f.events.some(e=>e[0]==='auth'||e[0]==='node-builder'),false);});
test('changed candidate or NO-GO never authenticates or publishes',async()=>{for(const mode of ['hash','verdict']){const f=fixture();f.files['Docs/BooksArranger_QA_v0.16.0_2026-10-13.md']=f.files['Docs/BooksArranger_QA_v0.16.0_2026-10-13.md'].replace(mode==='hash'?/[a-f0-9]{64}/:'GO',mode==='hash'?'c'.repeat(64):'NO-GO');await assert.rejects(()=>releaseFlow(f.io));assert.equal(f.events.some(e=>e[0]==='auth'||e[0]==='node-builder'),false);}});
test('zero-exit builder is not success if remote asset hashes differ',async()=>{const f=fixture(),api=f.io.api;f.io.api=async(...args)=>{const r=await api(...args);if(r)r.assets[0].digest='sha256:'+'c'.repeat(64);return r;};await assert.rejects(()=>releaseFlow(f.io),/Remote asset mismatch/);assert.equal(f.events.some(e=>e[0]==='cleanup'),false);});
test('submodules/special Git entries are not silently excluded',()=>assert.throws(()=>gitEntries('160000 commit '+pin+'\tsubmodule\0')));
test('cleanup verifies identities and preserves current release',async()=>{
 let releases=Array.from({length:5},(_,i)=>({id:i+1,tag_name:'v0.'+(20-i)+'.0',created_at:new Date(2026,9,13-i).toISOString(),draft:false,prerelease:false}));const deletes=[];
 const api=async(method,path)=>{if(method==='DELETE'){deletes.push(path);if(path.endsWith('/releases/5'))releases=releases.filter(r=>r.id!==5);return null;}if(path.includes('?'))return releases;if(path.endsWith('/releases/5'))return releases.find(r=>r.id===5);throw Error('unexpected');};
 const receipt=await cleanup.cleanupReleases(api,'/repos/Gemanoneko/booksArranger','v0.20.0');assert.equal(receipt.remaining.length,4);assert.equal(deletes.length,2);assert.ok(!deletes.some(p=>p.includes('v0.20.0')));
});

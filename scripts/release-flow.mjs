import { createHash } from 'node:crypto';
import { acceptanceIndex, artifactContract, newer, packageContract, productTree, remoteArtifacts, reportManifest, reportPin, requiresNativeQa, nativeEvidencePath, nativeEvidenceReportHash, nativeRecordReferences, validateNativeEvidence } from './release-contract.mjs';

import { consumeNativeCompatibility, frozen } from '../Docs/BooksArranger_Compatibility_0.24.2/compat-consumer.mjs';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export function gitEntries(output) {
  return output.split('\0').filter(Boolean).map(line=>{
    const m=/^(\d{6}) blob ([a-f0-9]{40})\t(.+)$/.exec(line);
    if(!m)throw new Error('Unexpected Git tree entry (submodule/special object refused)');
    return {mode:m[1],object:m[2],name:m[3]};
  });
}
// io owns native path/handle validation and the 600-second descendant job.
// No shell strings, injected env token, rebuild-after-QA or upload fallback.
export async function releaseFlow(io) {
  if(io.productRoot!==frozen.product_root)throw Error('One-off host must use the declared actual product worktree');
  const git = async args => (await io.run('git',args,{credential:false})).stdout.trim();
  if(await git(['status','--porcelain','--untracked-files=normal']))throw new Error('Release needs a clean checkout');
  const head=await git(['rev-parse','HEAD']);
  const pkg=JSON.parse(await io.read('package.json')), lock=JSON.parse(await io.read('package-lock.json'));
  const publish=packageContract(pkg,lock), tag='v'+pkg.version;
  const origin=await git(['config','--get','remote.origin.url']);
  const canonical=publish.owner+'/'+publish.repo;
  if(!['https://github.com/'+canonical+'.git','https://github.com/'+canonical,'git@github.com:'+canonical+'.git'].includes(origin))throw new Error('Origin differs from configured GitHub publisher');
  const entryList=async pin=>gitEntries((await io.run('git',['ls-tree','-rz','--full-tree',pin],{credential:false})).stdout);
  const digest=productTree(await entryList(head));
  const previous=(await git(['tag','--list','v*'])).split('\n').filter(t=>t&&t!==tag);
  for(const old of previous)if(!newer(pkg.version,old.slice(1)))throw new Error('Version is not newer than previous tags');
  // A missing candidate is prepared without publishing, then needs fresh acceptance.
  if(!await io.exists('dist/release-artifacts.json')) {
    await io.prepare();
    throw new Error('New installer candidate prepared. QA and review must accept its exact manifest before release.');
  }
  const raw=await io.read('dist/release-artifacts.json'), manifest=JSON.parse(raw), manifestHash=hash(raw);
  const files=artifactContract(manifest,{version:pkg.version,productTree:digest});
  if(productTree(await entryList(manifest.source_head))!==digest)throw new Error('Artifact source commit differs from release product');
  await io.run('git',['merge-base','--is-ancestor',manifest.source_head,head],{credential:false});
  const acceptance=acceptanceIndex(JSON.parse(await io.read('Docs/BooksArranger_ReleaseAcceptance_v'+pkg.version+'.json')),pkg.version);
  let qaText=null;
  for(const [kind,file] of acceptance) {
    const text=await io.read(file),pin=reportPin(text,kind);
    if(kind==='qa')qaText=text;
    await io.run('git',['merge-base','--is-ancestor',pin,head],{credential:false});
    if(productTree(await entryList(pin))!==digest || reportManifest(text)!==manifestHash)throw new Error(kind+' accepts a different source or installer');
  }
  if(requiresNativeQa(pkg.version)){
    // Mandatory real-shell phase. Canonical PASS or GO prose cannot substitute for
    // original candidate-bound normal owner/output/postflight/cleanup evidence.
    const evidencePath=nativeEvidencePath(pkg.version),facts=await io.hash(evidencePath);
    if(!Number.isSafeInteger(facts.size)||facts.size<=0||facts.size>128*1024||facts.sha256!==nativeEvidenceReportHash(qaText))throw Error('Native QA summary bytes are missing or unaccepted');
    const nativeRaw=await io.read(evidencePath);if(hash(nativeRaw)!==facts.sha256)throw Error('Native QA summary changed');
    const summary=JSON.parse(nativeRaw),records={};
    for(const [role,ref] of nativeRecordReferences(summary,pkg.version)){
      const actual=await io.hash(ref.path);if(actual.size!==ref.size||actual.sha256!==ref.sha256)throw Error('Native QA raw record differs: '+role);
      records[role]=await io.read(ref.path);
    }
    if(!manifest.runtime||typeof manifest.runtime!=='object')throw Error('Candidate runtime manifest missing');
    const phase=await io.hash('scripts/qa-phase-contract.mjs');
    const compatibility=await consumeNativeCompatibility(summary,records,{version:pkg.version,source_head:manifest.source_head,product_digest:digest,build_id:manifest.build_id,artifact_manifest_sha256:manifestHash,runtime_manifest_sha256:hash(JSON.stringify(manifest.runtime)),phase_contract_sha256:phase.sha256},{productRoot:io.productRoot});
    const receiptPath='Docs/BooksArranger_NativeQA_v0.24.2_Compatibility.json',receiptRaw=await io.read(receiptPath),receipt=JSON.parse(receiptRaw),accepted=[...qaText.matchAll(/^Native QA compatibility receipt SHA256:\s*([a-f0-9]{64})\s*$/gm)];
    if(accepted.length!==1||hash(receiptRaw)!==accepted[0][1])throw Error('Explicit compatibility receipt is missing or unaccepted');
    const withoutTime=({observed_at,...rest})=>rest;
    if(JSON.stringify(withoutTime(receipt))!==JSON.stringify(withoutTime(compatibility)))throw Error('Accepted compatibility interpretation differs from current exact check');
  }
  await io.verifyPayload(manifest); // Entire unpacked tree, NSIS equivalence receipt, source/raw JSON and runtimes.
  for(const artifact of manifest.artifacts) {
    const actual=await io.hash('dist/'+artifact.path);
    if(actual.sha256!==artifact.sha256 || actual.size!==artifact.size)throw new Error('Artifact changed: '+artifact.path);
  }
  // This acquisition strips GH_TOKEN/GITHUB_TOKEN first; no env credential fallback.
  if(io.compatibilityDryRun===true)return {dryRun:true,version:pkg.version,head,manifestHash,assets:files,deferred:['named tag exact local/remote HEAD','authentication','upload','remote asset verification','keep-four cleanup']};
  if(await git(['rev-parse',tag+'^{commit}'])!==head)throw new Error('Named release tag does not point to HEAD');
  const remote=await git(['ls-remote','--tags','origin','refs/tags/'+tag,'refs/tags/'+tag+'^{}']);
  const refs=remote.split('\n').filter(Boolean).map(line=>line.split(/\s+/));
  const resolved=refs.find(r=>r[1]==='refs/tags/'+tag+'^{}')||refs.find(r=>r[1]==='refs/tags/'+tag);
  if(resolved?.[0]!==head)throw new Error('Named tag has not been pushed to exact HEAD');
  await io.authenticate();
  const route='/repos/'+publish.owner+'/'+publish.repo;
  const existing=await io.api('GET',route+'/releases/tags/'+tag,{allow404:true});
  if(existing)throw new Error('Release already exists; preserve it and report, never overwrite');
  await io.run('node-builder',['publish','--files',...files.map(f=>'dist/'+f),'--version',pkg.version,'--policy','always'],{credential:true});
  // Builder 26's artifact publisher can return zero despite a failed upload.
  // Never infer success from its exit code or prune before remote hashes match.
  const release=await io.api('GET',route+'/releases/tags/'+tag);
  remoteArtifacts(release,manifest,tag,head);
  const finalRemote=await git(['ls-remote','--tags','origin','refs/tags/'+tag,'refs/tags/'+tag+'^{}']);
  const finalRefs=finalRemote.split('\n').filter(Boolean).map(line=>line.split(/\s+/));
  const finalResolved=finalRefs.find(r=>r[1]==='refs/tags/'+tag+'^{}')||finalRefs.find(r=>r[1]==='refs/tags/'+tag);
  if(finalResolved?.[0]!==head)throw new Error('Remote release tag changed during publication');
  if(await git(['rev-parse','HEAD'])!==head || await git(['status','--porcelain','--untracked-files=normal']))throw new Error('Release source changed during publication');
  if(hash(await io.read('dist/release-artifacts.json'))!==manifestHash)throw new Error('Release manifest changed during publication');
  // Exact assets remain held by native read leases until the last verification.
  for(const artifact of manifest.artifacts) {
    const actual=await io.hash('dist/'+artifact.path);
    if(actual.sha256!==artifact.sha256 || actual.size!==artifact.size)throw new Error('Published artifact changed locally');
  }
  let cleanupWarning=null;
  try { await io.cleanup(route,tag); } catch(error) { cleanupWarning=error.message; }
  return {version:pkg.version,head,tag,manifestHash,assets:files,cleanupWarning};
}

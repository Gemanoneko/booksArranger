import { createHash } from 'node:crypto';
import { acceptanceIndex, artifactContract, newer, packageContract, productTree, remoteArtifacts, reportManifest, reportPin } from './release-contract.mjs';

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
  if(await git(['rev-parse',tag+'^{commit}'])!==head)throw new Error('Named release tag does not point to HEAD');
  const previous=(await git(['tag','--list','v*'])).split('\n').filter(t=>t&&t!==tag);
  for(const old of previous)if(!newer(pkg.version,old.slice(1)))throw new Error('Version is not newer than previous tags');
  const remote=await git(['ls-remote','--tags','origin','refs/tags/'+tag,'refs/tags/'+tag+'^{}']);
  const refs=remote.split('\n').filter(Boolean).map(line=>line.split(/\s+/));
  const resolved=refs.find(r=>r[1]==='refs/tags/'+tag+'^{}')||refs.find(r=>r[1]==='refs/tags/'+tag);
  if(resolved?.[0]!==head)throw new Error('Named tag has not been pushed to exact HEAD');
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
  for(const [kind,file] of acceptance) {
    const text=await io.read(file),pin=reportPin(text,kind);
    await io.run('git',['merge-base','--is-ancestor',pin,head],{credential:false});
    if(productTree(await entryList(pin))!==digest || reportManifest(text)!==manifestHash)throw new Error(kind+' accepts a different source or installer');
  }
  await io.verifyPayload(manifest); // Entire unpacked tree, NSIS equivalence receipt, source/raw JSON and runtimes.
  for(const artifact of manifest.artifacts) {
    const actual=await io.hash('dist/'+artifact.path);
    if(actual.sha256!==artifact.sha256 || actual.size!==artifact.size)throw new Error('Artifact changed: '+artifact.path);
  }
  // This acquisition strips GH_TOKEN/GITHUB_TOKEN first; no env credential fallback.
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

// Pure validation shared by the local publisher and offline tests.
import { createHash } from 'node:crypto';
import path from 'node:path';
export const KEEP_RELEASES = 4;
export function version(value) {
  if (typeof value !== 'string' || !/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(value)) throw new Error('Expected canonical x.y.z version');
  return value.split('.').map(Number);
}
export function newer(a,b) { const aa=version(a),bb=version(b); for(let i=0;i<3;i++)if(aa[i]!==bb[i])return aa[i]>bb[i]; return false; }
export function packageContract(pkg, lock) {
  version(pkg.version);
  if(lock.version!==pkg.version || lock.packages?.['']?.version!==pkg.version) throw new Error('Package/lock version mismatch');
  const pub=pkg.build?.publish;
  if(!pub || Array.isArray(pub) || pub.provider!=='github' || !/^[A-Za-z0-9_.-]+$/.test(pub.owner||'') || !/^[A-Za-z0-9_.-]+$/.test(pub.repo||'') || pub.releaseType!=='release') throw new Error('Expected one stable GitHub publisher');
  if(pkg.build.directories?.output!=='dist')throw new Error('Release output must be dist');
  return pub;
}
export function productTree(entries) {
  // Git object identities bind every tracked product/config/test file; only final prose can change after acceptance.
  const selected=entries.filter(e=>!e.name.startsWith('Docs/') && e.name!=='CHANGELOG.md');
  selected.sort((a,b)=>a.name.localeCompare(b.name,'en'));
  return createHash('sha256').update(JSON.stringify(selected)).digest('hex');
}
export function reportPin(text, kind) {
  const wanted=kind==='qa'?'GO':'RELEASE CLEAR';
  const verdicts=[...text.matchAll(/^\*\*Verdict:\*\*\s*(.+?)\s*$/gm)];
  if(verdicts.length!==1 || verdicts[0][1]!==wanted)throw new Error(kind+' acceptance verdict missing or ambiguous');
  const pins=[...text.matchAll(/^Release source commit:\s*([a-f0-9]{40})\s*$/gm)];
  if(pins.length!==1)throw new Error(kind+' exact release source pin missing or ambiguous');
  return pins[0][1];
}
export function reportManifest(text) {
  const matches=[...text.matchAll(/^Release artifact manifest SHA256:\s*([a-f0-9]{64})\s*$/gm)];
  if(matches.length!==1)throw new Error('Exact accepted artifact manifest hash missing or ambiguous');
  return matches[0][1];
}
export function artifactContract(manifest, expected) {
  if(manifest.schema!=='books-desktop-artifacts-v1' || manifest.version!==expected.version || manifest.product_digest!==expected.productTree || !/^[a-f0-9]{40}$/.test(manifest.source_head||''))throw new Error('Artifact source/version manifest mismatch');
  if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(manifest.build_id||''))throw new Error('Invalid build identity');
  if(manifest.unpacked!=='builds/'+manifest.build_id+'/win-unpacked')throw new Error('Unpacked tree outside build identity');
  const exe='Books-Arranger-Setup-'+expected.version+'.exe';
  const names=[exe,exe+'.blockmap','latest.yml'];
  if(!Array.isArray(manifest.artifacts) || manifest.artifacts.length!==3)throw new Error('Expected exactly three release artifacts');
  for(const name of names) {
    const matches=manifest.artifacts.filter(a=>a.path==='builds/'+manifest.build_id+'/'+name);
    if(matches.length!==1 || !Number.isSafeInteger(matches[0].size) || matches[0].size<=0 || !/^[a-f0-9]{64}$/.test(matches[0].sha256||''))throw new Error('Invalid artifact '+name);
  }
  if(manifest.payload?.backend_version!==expected.version || manifest.payload?.shell_version!==expected.version || (manifest.payload?.verified!==true || manifest.payload?.installer_equivalent!==true))throw new Error('Packaged version/payload was not verified');
  return manifest.artifacts.map(a=>a.path);
}
export function remoteArtifacts(release, manifest, tag, head) {
  if(release.tag_name!==tag || release.draft || release.prerelease)throw new Error('Release is not the expected stable release');
  // target_commitish may be a branch; actual remote annotated tag resolution is checked independently.
  for(const file of manifest.artifacts) {
    const matches=(release.assets||[]).filter(a=>a.name===file.path.split('/').at(-1));
    if(matches.length!==1 || matches[0].state!=='uploaded' || matches[0].size!==file.size || matches[0].digest!=='sha256:'+file.sha256)throw new Error('Remote asset mismatch: '+file.path);
  }
  if((release.assets||[]).length!==3)throw new Error('Unexpected release assets');
}
export function releasesToPrune(releases, currentTag) {
  if(!Array.isArray(releases) || releases.some(r=>!Number.isSafeInteger(r.id)||r.id<=0 || !/^v\d+\.\d+\.\d+$/.test(r.tag_name||'') || !Number.isFinite(Date.parse(r.created_at))))throw new Error('Malformed release inventory');
  if(new Set(releases.map(r=>r.id)).size!==releases.length || new Set(releases.map(r=>r.tag_name)).size!==releases.length)throw new Error('Duplicate release inventory');
  const sorted=[...releases].sort((a,b)=>Date.parse(b.created_at)-Date.parse(a.created_at)||b.id-a.id);
  if(!sorted.slice(0,KEEP_RELEASES).some(r=>r.tag_name===currentTag))throw new Error('Current release is outside keep-four window; refusing prune');
  return sorted.slice(KEEP_RELEASES);
}

export function acceptanceIndex(index,expectedVersion) {
  if(index.schema!=='books-desktop-acceptance-v1'||index.version!==expectedVersion||Object.keys(index).sort().join(',')!=='qa,review,schema,version')throw new Error('Invalid release acceptance index');
  const escape=expectedVersion.replaceAll('.','\\.');
  for(const kind of ['qa','review']){
    const prefix=kind==='qa'?'QA':'CodeReview';
    if(typeof index[kind]!=='string'||!new RegExp('^Docs/BooksArranger_'+prefix+'_v'+escape+'_\\d{4}-\\d{2}-\\d{2}\\.md$').test(index[kind]))throw new Error('Unsafe acceptance report path');
  }
  return [['qa',index.qa],['review',index.review]];
}

export function leasedExecutable(proof,command) {
 const executable=command==='node-builder'?proof.node:proof.executables?.[command];
 if(!['git','gh','node-builder'].includes(command)||typeof executable!=='string'||!path.isAbsolute(executable))throw new Error('Exact native leased executable is missing');
 return executable;
}

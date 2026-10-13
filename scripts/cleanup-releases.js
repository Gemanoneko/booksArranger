#!/usr/bin/env node
// Final local release step. Authentication and native process ownership are
// supplied by release.mjs, never by an ambient GH_TOKEN or a second publish path.
const KEEP = 4;
async function cleanupReleases(api, route, currentTag) {
  if(!/^\/repos\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(route))throw new Error('Invalid repository route');
  const { releasesToPrune }=await import('./release-contract.mjs');
  const inventory=async()=>{
    const result=[];
    for(let page=1;page<=10;page++) {
      const batch=await api('GET',route+'/releases?per_page=100&page='+page);
      if(!Array.isArray(batch))throw new Error('Invalid release page');
      result.push(...batch);
      if(batch.length<100)return result;
    }
    throw new Error('Release inventory exceeds bounded 1000-release limit');
  };
  const before=await inventory(),remove=releasesToPrune(before,currentTag);
  for(const old of remove) {
    if(old.draft || old.prerelease)throw new Error('Refusing automatic deletion of draft/prerelease');
    // Re-read to refuse a substitution between inventory and destructive calls.
    const current=await api('GET',route+'/releases/'+old.id);
    if(current.id!==old.id || current.tag_name!==old.tag_name || current.created_at!==old.created_at || current.draft || current.prerelease)throw new Error('Release identity changed before prune');
    await api('DELETE',route+'/releases/'+old.id);
    await api('DELETE',route+'/git/refs/tags/'+encodeURIComponent(old.tag_name));
  }
  const after=await inventory();
  if(after.length>KEEP || !after.some(r=>r.tag_name===currentTag))throw new Error('Keep-four verification failed');
  return {removed:remove.map(r=>r.tag_name),remaining:after.map(r=>r.tag_name)};
}
module.exports={cleanupReleases};
if(require.main===module) {
  console.error('cleanup-releases: use npm run release; authenticated owned context is required.');
  process.exitCode=1;
}

/** Pure installation/rollback orchestration candidate. No production native backend is installed. */
export const PROTECTED_ROOT='C:/Program Files/BooksArranger-QA-v2';
export const ACL='O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;GRGX;;;BU)';
const hex=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
export function validateInstallPlan(plan){
 if(plan?.schema!=='books-qa-protected-install-v1'||plan.root!==PROTECTED_ROOT||plan.disabled!==true||plan.sddl!==ACL||!Array.isArray(plan.files)||!plan.files.length||plan.files.length>110||!hex(plan.original_global_sha256)||!hex(plan.candidate_global_sha256))throw Error('Unknown fixed disabled install plan');
 let bytes=0;const seen=new Set();for(const f of plan.files){if(!f||typeof f.relative!=='string'||!f.relative||f.relative.startsWith('/')||f.relative.includes('\\')||f.relative.includes(':')||f.relative.split('/').some(p=>!p||p==='.'||p==='..')||seen.has(f.relative.toLowerCase())||!hex(f.sha256)||!Number.isInteger(f.size)||f.size<0)throw Error('Unsafe install member');seen.add(f.relative.toLowerCase());bytes+=f.size;}
 if(bytes>8*1024*1024||!['books-qa-watchdog.exe','launch-books-qa.mjs','dispatch-books.mjs','operations.registry','bootstrap.manifest','dispatch-policy.json','original-bash-entry.json','original-global-hooks.json','candidate-global-hooks.json'].every(p=>seen.has(p)))throw Error('Incomplete fixed install closure');
 return {bytes,count:seen.size};
}
export async function installCandidate(plan,io){
 validateInstallPlan(plan);await io.requireExclusiveHumanPrivilegedBootstrap();await io.freezeExactSources(plan.files);await io.freezeOriginalGlobal(plan.original_global_sha256);await io.refuseExistingRoot(plan.root);
 const birth=await io.createAbsentDirectoryWithBirthAclUnderTrustedParent(plan.root,ACL);await io.verifyQuiescentPrivilegedCreationIdentity(birth);
 for(const file of plan.files){await io.checkDeadline();const created=await io.createNewRelative(birth,file.relative,ACL);await io.copyExactHeldSource(created,file);await io.flushAndReadback(created,file);await io.verifyProtectedOwnerDacl(created,ACL);}
 await io.requireExactManifest(birth,plan.files);await io.verifyProtectedAncestors(birth);await io.freezeExactSources(plan.files);
 // The candidate stays DISABLED. Global CAS is a SEPARATE, independently reviewed operation.
 return await io.writeCreateNewInstallProof(birth,{disabled:true,global_changed:false,root:plan.root,files:plan.files});
}
export async function deployCandidate(){throw Error('Automatic uncooperative global CAS is unavailable; only a separately reviewed explicit human host/pin update may proceed');}
export async function rollbackCandidate(){throw Error('Automatic global rollback is unavailable; require explicit human quiescent restoration of exact protected baseline bytes');}
export function requireProductionBackend(){throw Error('No approved automatic privileged bootstrap/global-CAS route; literal human creation-only recipe requires separate review and authorization');}

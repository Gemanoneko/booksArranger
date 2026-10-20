/** Revision2 review-only build contract. No accepted observable native owner is deployed. */
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export const LEGACY_NORESULT='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-review';
export const BUILD_PARENT='C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared';
export const CL='C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/VC/Tools/MSVC/14.50.35717/bin/Hostx64/x64/cl.exe';
const VC='C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/VC/Tools/MSVC/14.50.35717';
const SDK='C:/Program Files (x86)/Windows Kits/10';
const SDK_VERSION='10.0.26100.0';
const sha=s=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
export function validateBuildPlan(plan){
 if(plan?.schema!=='books-native-sealed-build-v2'||!sha(plan.source_sha256)||!sha(plan.recipe_sha256)||!sha(plan.toolchain_manifest_sha256)||!sha(plan.owner_admission_sha256)||!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(plan.invocation_id??'')||plan.deadline_ms!==600000)throw Error('Incomplete sealed native build plan');
 const arena=BUILD_PARENT+'/'+plan.source_sha256+'-'+plan.invocation_id;
 if(plan.arena!==arena||plan.owner_kind!=='reviewed-observable-native-owner-v1'||plan.reuse!==false)throw Error('Fresh digest-bound native arena required');
 if(arena.toLowerCase().startsWith(LEGACY_NORESULT.toLowerCase()))throw Error('Original NORESULT evidence is immutable');
 return {arena,source:arena+'/source/books-qa-watchdog.cpp',out:arena+'/out',tmp:arena+'/tmp',cache:arena+'/cache',evidence:arena+'/evidence'};
}
export function compilerInvocation(plan){
 const p=validateBuildPlan(plan);const args=['/nologo','/std:c++17','/EHsc','/MT','/W4','/WX','/O2','/guard:cf','/D_WIN32_WINNT=0x0A00','/I'+VC+'/include',...['ucrt','shared','um'].map(d=>'/I'+SDK+'/Include/'+SDK_VERSION+'/'+d),p.source,'/Fo'+p.out+'/books-qa-watchdog.obj','/Fe'+p.out+'/books-qa-watchdog.exe','/link','/INCREMENTAL:NO','/DYNAMICBASE','/NXCOMPAT','/HIGHENTROPYVA','/guard:cf','/LIBPATH:'+VC+'/lib/x64','/LIBPATH:'+SDK+'/Lib/'+SDK_VERSION+'/ucrt/x64','/LIBPATH:'+SDK+'/Lib/'+SDK_VERSION+'/um/x64'];
 return {file:CL,args,cwd:p.out,env:{SystemRoot:'C:\\Windows',WINDIR:'C:\\Windows',PATH:path.win32.dirname(CL)+';C:\\Windows\\System32',TEMP:p.tmp,TMP:p.tmp,APPDATA:p.cache+'/roaming',LOCALAPPDATA:p.cache+'/local',USERPROFILE:p.cache+'/profile',HOME:p.cache+'/profile'},deadline_ms:600000};
}
export async function prepareBuildCandidate(plan,io){
 const p=validateBuildPlan(plan);await io.requireIndependentlyReviewedObservableOwner(plan.owner_admission_sha256);const birth=await io.createExclusiveDigestArena(p.arena);await io.verifyNativeCreationIdentity(birth);await io.sealSourceRecipeToolchain(plan,birth);await io.createNewPrivateDirectories(birth,['source','out','tmp','cache','evidence']);await io.requireNoSharedWritableInputsOutputsCaches(plan,birth);await io.writeCreateNewStartupCreationProof(plan,birth);return {plan,paths:p,invocation:compilerInvocation(plan),execute_permitted:false};
}
export function requireBuildOwner(){throw Error('No supported reviewed durable observable native build owner; compilation refused. Original NORESULT arena must remain untouched.');}
if(typeof process!=='undefined'&&process.argv[1]&&path.win32.resolve(process.argv[1]).toLowerCase()===path.win32.resolve(fileURLToPath(import.meta.url)).toLowerCase()){requireBuildOwner();}

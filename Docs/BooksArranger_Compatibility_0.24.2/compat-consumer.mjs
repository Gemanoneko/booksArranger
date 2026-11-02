// One frozen 0.24.2 TAP-consumption exception. This is NOT an old-validator PASS.
// Original twelve records and product/phase identities are never rewritten.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const sha=b=>createHash('sha256').update(b).digest('hex');
const need=(ok,message)=>{if(!ok)throw Error(message);};
const metaRaw=fs.readFileSync(new URL('./metadata.json',import.meta.url));
need(sha(metaRaw)==='4533cb7824b76a7e295dc52b049733437962057abfb2747d8f836a9b87521102','Frozen compatibility metadata changed');
export const frozen=JSON.parse(metaRaw);
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function literalTapIdentity(functional,cleanup,plan){
 const exe=path.win32.join(frozen.fixture_root,'app','Books Arranger.exe');
 need(plan.fixture_root===frozen.fixture_root&&functional.fixture_root===plan.fixture_root&&cleanup.fixture_root===plan.fixture_root,'Compatibility fixture differs');
 need(exe===frozen.private_exe&&cleanup.exe===exe&&functional.exe===exe.replaceAll('\\','\\\\'),'Only the exact frozen TAP backslash spelling is compatible');
 need(cleanup.ownId===frozen.own_id&&/^\d+$/.test(cleanup.ownId),'Compatibility own leaf differs');
}
function currentExe(){
 const p=frozen.private_exe,s=fs.lstatSync(p,{bigint:true});need(s.isFile()&&!s.isSymbolicLink()&&s.nlink===1n,'Compatibility EXE is not ordinary');
 const identity={dev:String(s.dev),ino:String(s.ino),size:Number(s.size),nlink:Number(s.nlink)};need(same(identity,frozen.exe_identity),'Compatibility original EXE identity differs');
 const fd=fs.openSync(p,'r'),digest=createHash('sha256');try{const held=fs.fstatSync(fd,{bigint:true});need(held.dev===s.dev&&held.ino===s.ino&&held.size===s.size&&held.nlink===1n,'Compatibility EXE changed before retention');const b=Buffer.alloc(1024*1024);let n;while((n=fs.readSync(fd,b,0,b.length,null))>0)digest.update(b.subarray(0,n));const after=fs.fstatSync(fd,{bigint:true});need(after.dev===s.dev&&after.ino===s.ino&&after.size===s.size&&after.nlink===1n,'Compatibility retained EXE changed');}finally{fs.closeSync(fd);}
 need(digest.digest('hex')===frozen.exe_sha256,'Compatibility original EXE bytes differ');return identity;
}
export async function consumeNativeCompatibility(summary,records,expected,{productRoot=frozen.product_root}={}){
 need(path.resolve(productRoot)===path.resolve(frozen.product_root),'Compatibility must consume the declared nested product');
 need(same(expected,frozen.binding),'Compatibility is limited to the original f606/0f85/6704 binding');
 need(sha(fs.readFileSync(path.join(productRoot,'dist/release-artifacts.json')))===frozen.binding.artifact_manifest_sha256,'Compatibility product artifact differs');
 const contract=path.join(productRoot,'scripts/qa-phase-contract.mjs');need(sha(fs.readFileSync(contract))===frozen.binding.phase_contract_sha256,'Compatibility original phase contract differs');
 const original=await import(pathToFileURL(contract).href);let refusal=null;
 try{original.validateNativeEvidence(summary,records,expected);}catch(error){if(error.message!==frozen.strict_refusal)throw error;refusal=error.message;}
 need(refusal===frozen.strict_refusal,'The original validator did not produce the one known final refusal');
 need(Object.keys(records).sort().join('|')===Object.keys(frozen.raw).sort().join('|'),'Compatibility raw roles differ');
 for(const [role,pin]of Object.entries(frozen.raw)){const raw=Buffer.from(records[role]);need(raw.length===pin.size&&sha(raw)===pin.sha256,'Compatibility frozen raw record differs: '+role);}
 const decoded=Object.fromEntries(['functional','cleanup','plan'].map(role=>[role,JSON.parse(Buffer.from(records[role]).toString('utf8'))]));literalTapIdentity(decoded.functional,decoded.cleanup,decoded.plan);
 return {schema:'books-native-qa-0242-compatibility-v1',binding:expected,route:frozen.route,original_validator:{contract_sha256:frozen.binding.phase_contract_sha256,outcome:'REFUSED',reason:refusal},compatibility:{outcome:'PASS',rule:'exact frozen TAP backslash doubling only',raw_records_unchanged:true,current_exe_identity:currentExe(),raw_sha256:Object.fromEntries(Object.entries(frozen.raw).map(([role,p])=>[role,p.sha256]))},observed_at:new Date().toISOString()};
}

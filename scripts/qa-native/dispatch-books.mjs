/** New protected Books-only dispatch candidate. Existing fallback bytes are opaque and unchanged. */
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const BASE='C:/Program Files/BooksArranger-QA-v2';
const STUDIO='C:/Antigravity Projects/Studio Illuminati';
const NODE='C:/Program Files/nodejs/node.exe';
const hex=s=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
const same=(a,b)=>typeof a==='string'&&typeof b==='string'&&path.win32.resolve(a).toLowerCase()===path.win32.resolve(b).toLowerCase();
export function isBooksOperation(command){
 if(typeof command!=='string')return false;
 // Inspect executable position only. Search/read/echo arguments are data.
 const tokens=[];const pattern=/\s*(?:"([^"\r\n]*)"|'([^'\r\n]*)'|([^\s"']+))/gy;let m;
 while(tokens.length<3&&(m=pattern.exec(command))!==null)tokens.push(m[1]??m[2]??m[3]);
 if(tokens[0]==='&')tokens.shift();
 const normalized=s=>String(s??'').replaceAll('\\','/').toLowerCase();
 const executable=normalized(tokens[0]);
 const target=s=>/^(?:.*\/)?books-qa-watchdog(?:\.exe)?$/.test(s)||/(?:^|\/)qa-native\/launch-books-qa\.mjs$/.test(s)||s==='c:/program files/booksarranger-qa-v2/launch-books-qa.mjs';
 if(target(executable))return true;
 return /(?:^|\/)(?:node(?:\.exe)?|powershell(?:\.exe)?|pwsh(?:\.exe)?)$/.test(executable)&&target(normalized(tokens[1]));
}
export function booksCandidate(raw,originalOwned=false){
 if(originalOwned)return false;let input;try{input=JSON.parse(raw);}catch{return false;}
 const tool=input?.tool_input??{};return ['command','cmd'].some(key=>isBooksOperation(tool[key]));
}
export async function verifyBooksGuard(){
 throw Error('Protected Books native admission backend is not yet reviewed/installed; deny Books only');
}
export function classify(input,policy){
 const tool=input?.tool_input??{};const command=tool.command??tool.cmd;
 if(!['command','cmd'].some(key=>isBooksOperation(tool[key])))return {kind:'fallback'};
 if(!policy||policy.schema!=='books-qa-dispatch-policy-v1'||policy.enabled!==true||!hex(policy.registry_sha256))return {kind:'deny',reason:'Books protected registration is disabled'};
 const wanted="'C:/Program Files/BooksArranger-QA-v2/books-qa-watchdog.exe' --registry-sha "+policy.registry_sha256;
 if(command!==wanted||!same(tool.cwd??tool.workdir,STUDIO)||tool.command!==undefined&&tool.cmd!==undefined||tool.cwd!==undefined&&tool.workdir!==undefined)return {kind:'deny',reason:'Wrong exact Books command or cwd'};
 const allowed=new Set(['command','cmd','cwd','workdir','shell','timeout','yield_time_ms','max_output_tokens','login','tty']);
 if(Object.keys(tool).some(k=>!allowed.has(k))||tool.tty===true||tool.login!==false||tool.timeout!==undefined&&tool.timeout!==600000||!same(tool.shell,'C:/Program Files/Git/bin/bash.exe'))return {kind:'deny',reason:'Unknown Books launch envelope'};
 return {kind:'books'};
}
export function proposedHook(original,policySHA){
 if(!hex(policySHA)||!original?.hooks?.PreToolUse)throw Error('Exact original hook and policy pin required');
 const clone=structuredClone(original);const matches=clone.hooks.PreToolUse.flatMap((group,gi)=>(group.matcher==='Bash'?group.hooks:[]).map((hook,hi)=>({hook,gi,hi}))).filter(x=>typeof x.hook.commandWindows==='string');
 if(matches.length!==1)throw Error('Ambiguous global Bash Windows entry');
 return {candidate:clone,originalEntry:structuredClone(matches[0].hook),pointer:null,replacement_available:false,reason:'Original effective host/stdio/env/cwd/timing must remain unchanged. No replacement dispatcher is admitted.'};
}
async function main(){
 throw Error('Global entry replacement unavailable: no proved original-host equivalence; preserve existing hook unchanged');
}
if(typeof process!=='undefined'&&process.argv[1]&&same(process.argv[1],fileURLToPath(import.meta.url)))main().then(c=>{process.exitCode=c;}).catch(e=>{console.error('Books dispatch REFUSED: '+e.message);process.exitCode=2;});

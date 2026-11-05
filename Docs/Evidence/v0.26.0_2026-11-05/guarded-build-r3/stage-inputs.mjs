import fs from 'node:fs/promises';
import {createReadStream,constants} from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const main='C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger',release='C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r3';
const sha=async file=>{const hash=createHash('sha256');for await(const chunk of createReadStream(file))hash.update(chunk);return hash.digest('hex');};
const need=(ok,message)=>{if(!ok)throw Error(message);};
async function list(root){const result={};async function walk(dir,prefix=''){for(const entry of await fs.readdir(dir,{withFileTypes:true})){need(!entry.isSymbolicLink(),'Linked input refused: '+entry.name);const rel=prefix+entry.name,file=path.join(dir,entry.name);if(entry.isDirectory())await walk(file,rel+'/');else{need(entry.isFile(),'Special input refused');const s=await fs.lstat(file,{bigint:true});need(s.nlink===1n,'Hardlinked input refused: '+rel);result[rel]={size:Number(s.size),sha256:await sha(file)};}}}await walk(root);return Object.fromEntries(Object.entries(result).sort());}
async function copy(root,target,expected){need(!await fs.lstat(target).catch(()=>null),'Fresh target already exists: '+target);const before=await list(root);if(expected)need(JSON.stringify(before)===JSON.stringify(Object.fromEntries(Object.entries(expected).sort())),'Source seed differs from declared complete inventory');await fs.mkdir(target,{recursive:true});for(const [rel,ref] of Object.entries(before)){const to=path.join(target,rel);await fs.mkdir(path.dirname(to),{recursive:true});await fs.copyFile(path.join(root,rel),to,constants.COPYFILE_EXCL);need(await sha(to)===ref.sha256,'Copied input differs: '+rel);}need(JSON.stringify(await list(root))===JSON.stringify(before),'Input source changed during copy');need(JSON.stringify(await list(target))===JSON.stringify(before),'Input target changed during copy');return {source:root,target,files:Object.keys(before).length,bytes:Object.values(before).reduce((n,f)=>n+f.size,0),manifest:before};}
const config=JSON.parse(await fs.readFile(release+'/scripts/build-inputs.json','utf8'));
need(await sha(release+'/package-lock.json')===config.packageLockSha256,'Lock does not match final input pin');
const dependencies=await copy(main+'/node_modules',release+'/node_modules');
for(const [rel,ref]of Object.entries(config.productionFiles)){need(dependencies.manifest[rel.replace(/^node_modules\//,'')]?.sha256===ref.sha256,'Production package input differs: '+rel);}
const seed=await copy(main+'/'+config.seedDirectory,release+'/'+config.seedDirectory,config.files);
const runtimePins=JSON.parse(await fs.readFile(release+'/desktop/runtime-pins.json','utf8')),archives=[];
for(const [kind,pin]of Object.entries(runtimePins)){if(!pin.file||!pin.version)continue;const rel='build-cache/downloads/'+kind+'-'+pin.version+'/'+pin.file,from=main+'/'+rel,to=release+'/'+rel;if(!await fs.lstat(from).catch(()=>null))continue;need(await sha(from)===pin.sha256,'Cached runtime archive differs');await fs.mkdir(path.dirname(to),{recursive:true});await fs.copyFile(from,to,constants.COPYFILE_EXCL);need(await sha(to)===pin.sha256,'Runtime archive copy differs');archives.push({path:to,sha256:pin.sha256});}
console.log(JSON.stringify({dependencies,seed,archives,verified:true}));

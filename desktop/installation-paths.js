'use strict';
// Installation-owned bootstrap is outside Application and is found before the
// default Electron profile is opened. No bootstrap preserves legacy behavior.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const SCHEMA='books-arranger-installation-v1';
const PORTABLE_SCHEMA='books-arranger-installation-v2';
const ENV_KEYS=['BOOKS_STORAGE_RELOCATION_MANIFEST','BOOKS_STORAGE_RELOCATION_SHA256','BOOKS_WORK_TEMP'];
function inside(child,parent){const r=path.relative(parent,child);return r===''||!r.startsWith('..'+path.sep)&&r!=='..'&&!path.isAbsolute(r);}
function ordinary(file,{directory=false,bounded=16384}={}){
 const absolute=path.resolve(file);let current=absolute;
 while(true){const stat=fs.lstatSync(current);if(stat.isSymbolicLink())throw Error('Configured Books Arranger storage contains a junction or link: '+current);const parent=path.dirname(current);if(parent===current)break;current=parent;}
 const stat=fs.lstatSync(absolute);
 if(directory?!stat.isDirectory():!stat.isFile()||stat.size>bounded)throw Error('Configured Books Arranger storage has an unexpected type or size: '+absolute);
 const physical=fs.realpathSync.native(absolute);
 if(physical.startsWith('\\\\')||path.resolve(physical).toLowerCase()!==absolute.toLowerCase())throw Error('Configured Books Arranger storage is not its ordinary local location: '+absolute);
 return absolute;
}
function absolute(value,name){if(typeof value!=='string'||!value||!path.isAbsolute(value))throw Error('Installation '+name+' must name an absolute path.');return path.resolve(value);}
function relative(value,root,name){
 // Stored portable paths are members of the installation anchor, never paths
 // whose meaning depends on the current directory or the current drive.
 if(typeof value!=='string'||!value||path.isAbsolute(value)||path.win32.isAbsolute(value)||/[\x00-\x1f:]/.test(value))throw Error('Installation '+name+' must be a relative member of its storage folder.');
 const parts=value.split(/[\\/]/);
 if(parts.some(part=>!part||part==='.'||part==='..'||/[. ]$/.test(part)||/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part)))throw Error('Installation '+name+' contains an invalid relative member.');
 const result=path.resolve(root,...parts);
 if(!inside(result,root)||result===root)throw Error('Installation '+name+' escapes its storage folder.');
 // Some historical control selectors may no longer exist. Still reject a
 // junction in every existing ancestor without reopening their old location.
 let current=result;
 while(current!==root){
  try{if(fs.lstatSync(current).isSymbolicLink())throw Error('Configured Books Arranger storage contains a junction or link: '+current);}
  catch(error){if(error.code!=='ENOENT')throw error;}
  current=path.dirname(current);
 }
 return result;
}
function completedMigration(root,value){
 const intent=path.join(root,'Storage','portable-migration.json');
 try{fs.lstatSync(intent);}catch(error){if(error.code==='ENOENT')return;throw Error('Run the installer again to finish moving your data. Existing files have been kept.');}
 try{
  ordinary(intent,{bounded:64*1024*1024});
  const pending=JSON.parse(fs.readFileSync(intent,'utf8'));
  if(pending?.schema!=='books-portable-migration-intent-v1'||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(pending.migration_id)||pending.installation_id!==value.installation_id||value.schema!==PORTABLE_SCHEMA||pending.completion!==`Storage/migration-${pending.migration_id}.complete.json`)throw Error('Incomplete migration');
  const completed=ordinary(relative(pending.completion,root,'migration completion'),{bounded:64*1024*1024});
  const receipt=JSON.parse(fs.readFileSync(completed,'utf8'));
  if(receipt?.schema!=='books-portable-migration-complete-v1'||receipt.migration_id!==pending.migration_id||receipt.installation_id!==value.installation_id)throw Error('Incomplete migration');
  if(receipt.kind==='retained-runtime'){
   if(!/^[a-f0-9]{64}$/.test(receipt.binding_sha256)||receipt.binding_sha256!==value.storage_relocation?.sha256||'catalog_identity' in receipt)throw Error('Incomplete migration');
  }else if(receipt.kind==='legacy-catalog'){
   if(value.storage_relocation||'binding_sha256' in receipt||receipt.data_dir!==value.data_dir||receipt.data_dir!=='Data'||!Array.isArray(receipt.catalog_identity)||receipt.catalog_identity.length!==3||receipt.catalog_identity.some(n=>!Number.isInteger(n)||n<0||n>0xffffffff))throw Error('Incomplete migration');
  }else throw Error('Incomplete migration');
 }catch{throw Error('Run the installer again to finish moving your data. Existing files have been kept.');}
}
function load({argv=[],executable=process.execPath,packaged=true,requireConfiguration=false}={}){
 const selected=argv.filter(a=>a.startsWith('--installation-config='));
 if(selected.length>1)throw Error('Only one installation configuration may be selected.');
 const explicit=selected.length?selected[0].slice('--installation-config='.length):null;
 if(explicit!==null&&!path.isAbsolute(explicit))throw Error('Installation configuration must name an absolute path.');
 if(!explicit&&!packaged)return null;
 const filename=explicit||path.join(path.dirname(executable),'..','books-arranger-installation.json');
 try{fs.lstatSync(filename);}catch(error){
  if(error.code==='ENOENT'&&!explicit&&!requireConfiguration)return null;
  if(error.code==='ENOENT')throw Error('Required installation settings are missing at “'+filename+'”. Repair the installation before opening Books Arranger.');
  throw Error('Books Arranger cannot read the required installation settings at “'+filename+'”. Restore access or repair the installation before opening Books Arranger.');
 }
 let value;
 try{ordinary(filename);value=JSON.parse(fs.readFileSync(filename,'utf8'));}
 catch(error){
  if(['EACCES','EPERM','EIO','ENXIO'].includes(error.code))throw Error('Books Arranger cannot read the required installation settings at “'+filename+'”. Restore access or repair the installation before opening Books Arranger.');
  throw Error('The installation settings at “'+filename+'” are invalid. Repair the installation before opening Books Arranger.');
 }
 const required=['schema','installation_id','application_dir','data_dir','catalog_mode','profile_dir','temp_dir','downloads_dir','logs_dir','ownership_manifest'];
 if(!value||Array.isArray(value)||required.some(k=>!(k in value))||Object.keys(value).some(k=>!required.includes(k)&&!['storage_relocation','package_ownership','retained_package','retained_profile','ownership_provenance','control_provenance','maintenance_temp_dir','maintenance_temp_identity'].includes(k))||![SCHEMA,PORTABLE_SCHEMA].includes(value.schema)||!/^([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$/.test(value.installation_id)||!['existing','new'].includes(value.catalog_mode))throw Error('Unsupported Books Arranger installation configuration; retained unchanged.');
 const portable=value.schema===PORTABLE_SCHEMA,anchor=path.dirname(path.resolve(filename));
 // A half-published move must be caught before Electron opens any profile or
 // the engine touches a catalog. The ordinary installer resumes its journal.
 completedMigration(anchor,value);
 const selectedPath=(value,name)=>portable?relative(value,anchor,name):absolute(value,name);
 require('./pending-cleanup').assertNoPendingCleanup(value.installation_id);
 const app=ordinary(selectedPath(value.application_dir,'application folder'),{directory:true});
 if(app.toLowerCase()!==path.resolve(path.dirname(executable)).toLowerCase())throw Error('Installation configuration belongs to a different application folder.');
 if(inside(path.resolve(filename),app))throw Error('Retained installation configuration must be outside the application folder.');
 const result={...value,filename:path.resolve(filename),application_dir:app};
 for(const key of ['retained_package','retained_profile','ownership_provenance','control_provenance'])if(value[key]){
  const pin=value[key];
  if(!pin||Array.isArray(pin)||Object.keys(pin).sort().join(',')!=='manifest,sha256'||!/^[a-f0-9]{64}$/.test(pin.sha256))throw Error('Invalid retained package ownership selection.');
  // Historical retention metadata is a cleanup selector only. Normal runtime
  // must not reopen a retired C installation or depend on its later existence.
  result[key]=Object.freeze({manifest:selectedPath(pin.manifest,key+' receipt'),sha256:pin.sha256});
 }
 if(value.package_ownership){
  const pin=value.package_ownership;
  if(!pin||Array.isArray(pin)||Object.keys(pin).sort().join(',')!=='manifest,sha256'||!/^[a-f0-9]{64}$/.test(pin.sha256))throw Error('Invalid installation package ownership selection.');
  const manifest=ordinary(selectedPath(pin.manifest,'package ownership receipt'),{bounded:64*1024*1024});
  if(inside(manifest,app)||crypto.createHash('sha256').update(fs.readFileSync(manifest)).digest('hex')!==pin.sha256)throw Error('Installation package ownership receipt changed; retained unchanged.');
  // This pin is uninstall binary ownership only, never catalog/storage authority.
  result.package_ownership=Object.freeze({manifest,sha256:pin.sha256});
 }
 for(const key of ['profile_dir','temp_dir','downloads_dir','logs_dir']){
  try{result[key]=ordinary(selectedPath(value[key],key),{directory:true});}
  catch(error){throw Error('Configured Books Arranger '+key+' is unavailable: '+String(value[key])+'. No alternate storage was opened. '+error.message);}
  if(inside(result[key],app)||inside(app,result[key]))throw Error('Application and retained storage folders overlap: '+key);
 }
 const dirs=['profile_dir','temp_dir','downloads_dir','logs_dir'];
 for(let a=0;a<dirs.length;a++)for(let b=a+1;b<dirs.length;b++)if(inside(result[dirs[a]],result[dirs[b]])||inside(result[dirs[b]],result[dirs[a]]))throw Error('Configured Books Arranger storage folders overlap.');
 result.data_dir=selectedPath(value.data_dir,'catalog folder');
 if(portable)ordinary(result.data_dir,{directory:true});
 result.ownership_manifest=selectedPath(value.ownership_manifest,'ownership manifest');
 if(inside(result.data_dir,app)||inside(app,result.data_dir))throw Error('Application and catalog folders overlap.');
 for(const key of dirs)if(inside(result.data_dir,result[key])||inside(result[key],result.data_dir))throw Error('Catalog and installation-managed storage folders overlap.');
 if(('maintenance_temp_dir' in value)!==('maintenance_temp_identity' in value))throw Error('Installation maintenance settings are incomplete. Repair the installation.');
 if('maintenance_temp_dir' in value){
  const identity=value.maintenance_temp_identity;
  if(!Array.isArray(identity)||identity.length!==3||identity.some(n=>!Number.isInteger(n)||n<0||n>0xffffffff))throw Error('Installation maintenance identity is invalid. Repair the installation.');
  try{result.maintenance_temp_dir=ordinary(selectedPath(value.maintenance_temp_dir,'maintenance temporary folder'),{directory:true});}
  catch(error){throw Error('Configured Books Arranger maintenance storage is unavailable: '+String(value.maintenance_temp_dir)+'. No alternate storage was opened. '+error.message);}
  const managed=[app,result.data_dir,...dirs.map(key=>result[key])];
  if(managed.some(folder=>inside(folder,result.maintenance_temp_dir)||inside(result.maintenance_temp_dir,folder)))throw Error('Maintenance and retained storage folders overlap.');
  const controls=[result.filename,result.ownership_manifest,...['package_ownership','retained_package','retained_profile','ownership_provenance','control_provenance'].filter(key=>result[key]).map(key=>result[key].manifest)];
  if(controls.some(file=>inside(file,result.maintenance_temp_dir)))throw Error('Maintenance work overlaps retained installation records.');
  result.maintenance_temp_identity=Object.freeze([...identity]);
 }
 if(value.storage_relocation){
  const selection=value.storage_relocation;
  if(!selection||Array.isArray(selection)||Object.keys(selection).sort().join(',')!=='manifest,sha256'||!/^[a-f0-9]{64}$/.test(selection.sha256))throw Error('Explicit storage relocation requires its exact descriptor and SHA-256.');
  const manifest=ordinary(selectedPath(selection.manifest,'relocation descriptor'),{bounded:64*1024*1024});
  const raw=fs.readFileSync(manifest);
  if(crypto.createHash('sha256').update(raw).digest('hex')!==selection.sha256)throw Error('Selected storage relocation descriptor changed; no alternate storage was opened.');
  result.storage_relocation={manifest,sha256:selection.sha256};
  // This lexical choice grants no native authority. Python's strict byte-pinned
  // manifest/native activation validator remains mandatory before catalog I/O.
  const descriptor=JSON.parse(raw.toString('utf8'));
  if(portable){
   if(descriptor.schema!=='books-portable-runtime-v1'||relative(descriptor.data,anchor,'runtime catalog folder')!==result.data_dir)throw Error('Portable runtime binding does not select this installation catalog.');
   // Historical source paths are evidence only. The native admission helper
   // verifies this binding before I/O; the shell always uses the current Data.
  }else if(descriptor.schema!=='books-storage-relocation-v1'||!path.isAbsolute(descriptor.source_root)||!path.isAbsolute(descriptor.target_root)||!Array.isArray(descriptor.scopes))throw Error('Unsupported storage relocation descriptor.');
  else if(inside(result.data_dir,path.resolve(descriptor.target_root))){
   const relative=path.relative(path.resolve(descriptor.target_root),result.data_dir);
   if(!descriptor.scopes.some(scope=>typeof scope==='string'&&inside(relative,scope)))throw Error('Selected catalog is outside the explicitly relocated managed scope.');
   result.data_dir=path.join(descriptor.source_root,relative);
  }else if(!inside(result.data_dir,path.resolve(descriptor.source_root))||!descriptor.scopes.some(scope=>typeof scope==='string'&&inside(path.relative(descriptor.source_root,result.data_dir),scope)))throw Error('Selected catalog does not belong to this storage relocation.');
 }
 return Object.freeze(result);
}
function apply(app,installation,environment=process.env){
 if(!installation)return;
 app.setPath('userData',installation.profile_dir);
 app.setPath('sessionData',installation.profile_dir); // preserves migrated Local Storage/cookies in their original layout
 app.setPath('temp',installation.temp_dir);
 app.setPath('downloads',installation.downloads_dir);
 app.setAppLogsPath(installation.logs_dir);
 const crashes=path.join(installation.logs_dir,'CrashDumps');fs.mkdirSync(crashes,{recursive:true});app.setPath('crashDumps',crashes);
 environment.TEMP=environment.TMP=installation.temp_dir;
}
function profileSettings(value,installation){
 if(!value||Array.isArray(value)||typeof value.dataDir!=='string')throw Error('Desktop settings need a data folder; retained unchanged.');
 if(installation?.schema!==PORTABLE_SCHEMA){
  if(!path.isAbsolute(value.dataDir))throw Error('Desktop settings need an explicit absolute data folder; retained unchanged.');
  return value;
 }
 const anchor=path.dirname(installation.filename);
 const dataDir=relative(value.dataDir,anchor,'profile catalog folder');
 if(dataDir!==installation.data_dir)throw Error('Desktop settings do not match this installation catalog; retained unchanged.');
 const result={...value,dataDir};
 if(value.storage_relocation){
  const pin=value.storage_relocation;
  if(!pin||Array.isArray(pin)||Object.keys(pin).sort().join(',')!=='manifest,sha256'||!/^[a-f0-9]{64}$/.test(pin.sha256))throw Error('Desktop settings contain an invalid runtime binding; retained unchanged.');
  const manifest=relative(pin.manifest,anchor,'profile runtime binding');
  if(!installation.storage_relocation||manifest!==installation.storage_relocation.manifest||pin.sha256!==installation.storage_relocation.sha256)throw Error('Desktop settings do not match this installation runtime binding; retained unchanged.');
  result.storage_relocation={manifest,sha256:pin.sha256};
 }
 return result;
}
function childEnvironment(base,selection,workTemp=null){
 const result={...base};for(const key of ENV_KEYS)delete result[key];
 if(selection){result[ENV_KEYS[0]]=selection.manifest;result[ENV_KEYS[1]]=selection.sha256;}
 if(workTemp){result.BOOKS_WORK_TEMP=workTemp;result.TEMP=result.TMP=workTemp;}
 return result;
}
function configureUpdater(updater,installation){
 if(!installation)return;
 if(!updater.app||updater.downloadedUpdateHelper)throw Error('Updater storage must be configured before downloading.');
 // Pinned electron-updater 6.8.9 gets its cache from the AppAdapter before its
 // first helper is created. The adapter's remaining identity/config stays intact.
 Object.defineProperty(updater.app,'baseCachePath',{value:installation.downloads_dir,configurable:false});
}
module.exports={load,apply,profileSettings,childEnvironment,configureUpdater,ordinary,inside};

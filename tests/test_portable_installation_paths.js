'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const kit=require('../desktop/installation-paths');
const scratch=path.resolve(process.env.BOOKS_QA_FIXTURE_ROOT||path.join(__dirname,'..','scratch'));
fs.mkdirSync(scratch,{recursive:true});
const root=fs.mkdtempSync(path.join(scratch,'portable-paths-')),moved=root+'-moved';
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
let current=root;
try{
 for(const name of ['Application','Data','Profile','Temp','Downloads','Logs','MaintenanceTemp','Storage'])fs.mkdirSync(path.join(root,name));
 const runtime=Buffer.from(JSON.stringify({schema:'books-portable-runtime-v1',data:'Data'}));
 fs.writeFileSync(path.join(root,'Storage','runtime.json'),runtime);
 const packageReceipt=Buffer.from('package fixture');fs.writeFileSync(path.join(root,'Storage','package.json'),packageReceipt);
 const pin={manifest:'Storage/runtime.json',sha256:digest(runtime)};
 const value={schema:'books-arranger-installation-v2',installation_id:'869124b6-3d43-45d8-8123-2c2c7544806c',application_dir:'Application',data_dir:'Data',catalog_mode:'existing',profile_dir:'Profile',temp_dir:'Temp',downloads_dir:'Downloads',logs_dir:'Logs',ownership_manifest:'Storage/ownership.json',maintenance_temp_dir:'MaintenanceTemp',maintenance_temp_identity:[1,2,3],storage_relocation:pin,package_ownership:{manifest:'Storage/package.json',sha256:digest(packageReceipt)},retained_package:{manifest:'Storage/retained.json',sha256:'b'.repeat(64)}};
 const save=input=>fs.writeFileSync(path.join(current,'books-arranger-installation.json'),JSON.stringify(input));
 const load=()=>kit.load({executable:path.join(current,'Application','Books Arranger.exe'),packaged:true,requireConfiguration:true});
 save(value);
 let installed=load();
 assert.equal(installed.data_dir,path.join(root,'Data'),'portable shell never rewrites to the historical alias');
 assert.equal(installed.retained_package.manifest,path.join(root,'Storage','retained.json'),'historical selectors stay within the current anchor');
 const settings={dataDir:'Data',catalogMode:'existing',storage_relocation:pin,audiobook_sources:['Z:\\Library'],audiobook_output_root:'Y:\\Converted'};
 const resolved=kit.profileSettings(settings,installed);
 assert.equal(resolved.dataDir,installed.data_dir);
 assert.deepEqual(resolved.audiobook_sources,settings.audiobook_sources);
 assert.equal(resolved.audiobook_output_root,settings.audiobook_output_root);
 assert.equal(settings.dataDir,'Data','reading does not rewrite the stored relative selection');
 assert.throws(()=>kit.profileSettings({...settings,dataDir:'C:\\old-data'},installed),/relative member/);
 assert.throws(()=>kit.profileSettings({...settings,dataDir:'Other'},installed),/do not match/);
 assert.throws(()=>kit.profileSettings({...settings,storage_relocation:{...pin,sha256:'f'.repeat(64)}},installed),/do not match/);
 for(const member of ['../Data','..\\Data','C:\\Data','C:Data','/Data','Data/../Data','Data\\..\\Data','Data.','Data ','.','Data//x','NUL']){
  save({...value,data_dir:member});assert.throws(load,undefined,'unsafe relative member refused: '+member);
 }
 save({...value,retained_package:{manifest:'C:\\old-receipt.json',sha256:'b'.repeat(64)}});assert.throws(load,/relative member/);
 save({...value,storage_relocation:{...pin,sha256:'0'.repeat(64)}});assert.throws(load,/descriptor changed/);
 const incompatible=Buffer.from(JSON.stringify({schema:'books-storage-relocation-v1',source_root:'C:\\old',target_root:root,scopes:['Data']}));
 fs.writeFileSync(path.join(root,'Storage','runtime.json'),incompatible);
 save({...value,storage_relocation:{...pin,sha256:digest(incompatible)}});assert.throws(load,/Portable runtime binding/);
 fs.writeFileSync(path.join(root,'Storage','runtime.json'),runtime);
 save(value);
 // The whole owned installation moves without editing its bootstrap/profile.
 fs.renameSync(root,moved);current=moved;
 installed=load();
 assert.equal(installed.data_dir,path.join(moved,'Data'));
 assert.equal(installed.profile_dir,path.join(moved,'Profile'));
 assert.equal(installed.storage_relocation.manifest,path.join(moved,'Storage','runtime.json'));
 assert.equal(kit.profileSettings(settings,installed).dataDir,path.join(moved,'Data'));
 const migrationId='ea9dd376-b3c9-4bd7-a6f6-0126e4a1f26b';
 const completion=`Storage/migration-${migrationId}.complete.json`;
 const intent={schema:'books-portable-migration-intent-v1',migration_id:migrationId,installation_id:value.installation_id,completion};
 fs.writeFileSync(path.join(moved,'Storage','portable-migration.json'),JSON.stringify(intent));
 fs.renameSync(path.join(moved,'Profile'),path.join(moved,'Profile-retained'));
 assert.throws(load,/Run the installer again/,'pending move refuses before opening the unavailable profile');
 fs.renameSync(path.join(moved,'Profile-retained'),path.join(moved,'Profile'));
 const complete={schema:'books-portable-migration-complete-v1',kind:'retained-runtime',migration_id:migrationId,installation_id:value.installation_id,binding_sha256:pin.sha256};
 fs.writeFileSync(path.join(moved,...completion.split('/')),JSON.stringify({...complete,binding_sha256:'d'.repeat(64)}));
 assert.throws(load,/Run the installer again/,'a completion for another binding cannot authorize startup');
 fs.writeFileSync(path.join(moved,...completion.split('/')),JSON.stringify(complete));
 assert.equal(load().data_dir,path.join(moved,'Data'),'complete move uses the current anchor');
 const plainComplete={schema:complete.schema,kind:'legacy-catalog',migration_id:migrationId,installation_id:value.installation_id,data_dir:'Data',catalog_identity:[1,2,3]};
 fs.writeFileSync(path.join(moved,...completion.split('/')),JSON.stringify(plainComplete));
 assert.throws(load,/Run the installer again/,'plain completion cannot authorize a retained runtime binding');
 const plainValue={...value};delete plainValue.storage_relocation;save(plainValue);
 assert.equal(load().data_dir,path.join(moved,'Data'),'typed plain catalog completion has no relocation dependency');
 fs.writeFileSync(path.join(moved,...completion.split('/')),JSON.stringify({...plainComplete,binding_sha256:pin.sha256}));
 assert.throws(load,/Run the installer again/,'mixed completion kinds are refused');
 fs.writeFileSync(path.join(moved,...completion.split('/')),JSON.stringify(complete));save(value);
 const link=path.join(moved,'LinkedData');fs.symlinkSync(path.join(moved,'Data'),link,'junction');
 save({...value,data_dir:'LinkedData'});assert.throws(load,/junction or link/);
 console.log('portable installation paths: default discovery, relative relocation, unchanged external paths, pin mismatch and traversal/link refusals passed');
}finally{
 for(const owned of [root,moved]){
  assert.equal(path.dirname(owned),scratch);assert.ok(path.basename(owned).startsWith('portable-paths-'));
  if(fs.existsSync(owned))fs.rmSync(owned,{recursive:true});
 }
}

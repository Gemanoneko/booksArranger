import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const require=createRequire(import.meta.url),root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const source=fs.readFileSync(path.join(root,'desktop/main.js'),'utf8');
const kit=require('../desktop/installation-paths.js');
const selected={filename:path.join(root,'package.json'),application_dir:'I:\\Private Books Fixture\\Application',
  temp_dir:'I:\\Private Books Fixture\\Temp',maintenance_temp_dir:'I:\\Private Books Fixture\\MaintenanceTemp',storage_relocation:null};

function run(success,configuration=selected){
  const events=[],errors=[],environment={TEMP:'C:\\unselected',TMP:'C:\\unselected',
    BOOKS_WORK_TEMP:'C:\\unselected',BOOKS_STORAGE_RELOCATION_MANIFEST:'untrusted'};
  const app={isPackaged:true,exit:code=>events.push('exit:'+code),
    requestSingleInstanceLock:()=>assert.fail('uninstall launcher entered normal instance startup')};
  const fakeProcess={argv:['I:\\Private Books Fixture\\Application\\Books Arranger.exe','--run-uninstaller','--quiet-errors'],
    execPath:'I:\\Private Books Fixture\\Application\\Books Arranger.exe',pid:12345,env:environment,
    stderr:{write:message=>errors.push(message)}};
  const spawnSync=(executable,args,options)=>{
    events.push('spawn');assert.ok(executable.endsWith('resources\\python\\python.exe'));
    assert.deepEqual(Array.from(args.slice(0,2)),['-I','-B']);
    assert.equal(options.env.TEMP,selected.maintenance_temp_dir);assert.equal(options.env.TMP,selected.maintenance_temp_dir);
    assert.equal(options.env.BOOKS_WORK_TEMP,selected.maintenance_temp_dir);
    assert.equal(options.env.BOOKS_STORAGE_RELOCATION_MANIFEST,undefined);
    assert.equal(options.windowsHide,true);
    return {status:success?0:1,stdout:JSON.stringify(success?{started:true}:{started:false,error:'Selected uninstall could not start'})};
  };
  function load(name){
    if(name==='electron')return {app};
    if(name==='node:child_process')return {spawn:()=>assert.fail('normal backend spawned'),spawnSync};
    if(name==='./launch-options')return {refuseCapture(){}};
    if(name==='./installation-paths')return {load(){events.push('load');return configuration;},
      childEnvironment:kit.childEnvironment,apply(){assert.fail('uninstall launcher applied a profile');}};
    return require(name);
  }
  const entry=vm.runInNewContext('(function(require,module,exports,__dirname,__filename,process){'+source+'\n})',{},
    {filename:'desktop/main.js'});
  entry(load,{exports:{}},{},path.join(root,'desktop'),path.join(root,'desktop/main.js'),fakeProcess);
  return {events,errors};
}
assert.deepEqual(run(true).events,['load','spawn','exit:0']);
const refused=run(false);assert.deepEqual(refused.events,['load','spawn','exit:2']);
assert.match(refused.errors.join(''),/Selected uninstall could not start/);
const oldBootstrap=run(true,{...selected,maintenance_temp_dir:undefined});
assert.deepEqual(oldBootstrap.events,['load','exit:2']);
assert.match(oldBootstrap.errors.join(''),/maintenance settings are missing/);
console.log('uninstall launch contract: selected temp before spawn; no profile or single-instance startup; launch refusal remains closed');

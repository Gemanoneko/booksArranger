// This boundary exists only inside the owned, pinned builder process.
import fs from 'node:fs';
import path from 'node:path';
import cp from 'node:child_process';
import {createHash} from 'node:crypto';
import {syncBuiltinESMExports} from 'node:module';

const canonical = value => path.resolve(value).toLowerCase();
const equalArgs = (a,b) => JSON.stringify(a) === JSON.stringify(b);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export function fileFacts(file) {
  let current=path.resolve(file);
  while (true) {
    const stat=fs.lstatSync(current);
    if(stat.isSymbolicLink()) throw Error('Pack child reparse path refused');
    const parent=path.dirname(current); if(parent===current)break; current=parent;
  }
  const stat=fs.lstatSync(file);
  if(!stat.isFile()||stat.nlink!==1)throw Error('Pack child must be one ordinary file');
  const bytes=fs.readFileSync(file);
  return {size:bytes.length,sha256:hash(bytes)};
}

export function createChildPolicy(context,{now=()=>Date.now(),inspectFile=fileFacts,onChildEvent=()=>{}}={}) {
  let refusal=null;
  const launches=[];
  const authorized=new WeakMap();
  function deny(reason) { refusal ||= Error('Pack child refused: '+reason); throw refusal; }
  function check(ok,reason) {if(!ok)deny(reason);}
  function assertClean() {
    if(refusal)throw refusal;
    check(Number.isFinite(context.deadline)&&context.deadline>now(),'expired build lease');
  }
  function samePath(a,b) {return typeof a==='string'&&typeof b==='string'&&canonical(a)===canonical(b);}
  function pinned(file) {
    const key=Object.keys(context.executablePins||{}).find(p=>samePath(p,file));
    check(key,'unlisted executable/input '+file);
    let actual;try{actual=inspectFile(file);}catch(error){deny(error.message);}
    const expected=context.executablePins[key];
    check(actual.size===expected.size&&actual.sha256===expected.sha256,'input fingerprint changed '+file);
  }
  function environment(proposed) {
    const base={...context.baseEnv};
    if(proposed!==undefined) {
      check(proposed&&typeof proposed==='object'&&!Array.isArray(proposed),'invalid child environment');
      for(const [key,value] of Object.entries(proposed)) {
        const original=Object.keys(base).find(k=>k.toLowerCase()===key.toLowerCase());
        if(original!==undefined)check(value===base[original],'child environment override '+key);
        else if(key==='NSISDIR')check(samePath(value,path.dirname(path.dirname(context.nsis))),'NSISDIR escape');
        else if(key==='__COMPAT_LAYER')check(value==='RunAsInvoker','unexpected compatibility override');
        else deny('unlisted child environment '+key);
        base[key]=value;
      }
    }
    return base;
  }
  function prepare(file,args,options={},method='spawn') {
    assertClean();
    check(!context.iconOnly,'icon converter may not start child processes');
    check(method==='spawn'||method==='execFile','unsupported process API');
    check(typeof file==='string'&&path.isAbsolute(file)&&!file.includes('\0'),'absolute executable required');
    check(Array.isArray(args)&&args.every(x=>typeof x==='string'&&!/[\0\r\n]/.test(x)),'invalid literal argv');
    check(!args.some(x=>/^-encodedcommand$/i.test(x)),'EncodedCommand prohibited');
    check(options&&typeof options==='object'&&!Array.isArray(options),'invalid options');
    check(options.shell===undefined||options.shell===false,'shell prohibited');
    check(options.detached===undefined||options.detached===false,'detached process prohibited');
    check(options.windowsHide!==false,'visible child prohibited');
    check(options.windowsVerbatimArguments!==true,'verbatim shell arguments prohibited');
    let mapped=file, mappedArgs=[...args];
    const cwd=options.cwd||context.root;
    let kind;
    if(samePath(file,context.node)) {
      check(equalArgs(args,[context.npmCli,'prefix','-w']),'only npm workspace metadata is allowed');
      check(samePath(cwd,context.root)||samePath(cwd,context.appDir),'npm cwd escape');
      pinned(context.npmCli);kind='npm-prefix';
    } else if(samePath(file,context.seven)) {
      const archive=context.archivePath;
      check(typeof archive==='string'&&path.isAbsolute(archive)&&samePath(path.dirname(archive),context.output)&&/^books-arranger-\d+\.\d+\.\d+-x64\.nsis\.7z$/.test(path.basename(archive)),'missing or invalid bound archive path');
      check(equalArgs(args,['a','-bd','-mx=9','-md=1m','-mtc=off','-ms=off','-mtm=off','-mta=off',archive,'.']),'unexpected 7zip operation');
      check(samePath(cwd,path.join(context.output,'win-unpacked')),'7zip cwd escape');kind='nsis-archive';
    } else if(samePath(file,context.nsis)) {
      check(samePath(cwd,context.nsisTemplates),'makensis cwd escape');
      check(args.length>4&&equalArgs(args.slice(0,3),['-WX','-INPUTCHARSET','UTF8'])&&args.at(-1)==='-','makensis invocation shape');
      let outFile=false;
      const defines=new Set(['APP_ID','APP_GUID','UNINSTALL_APP_KEY','PRODUCT_NAME','PRODUCT_FILENAME','APP_FILENAME','APP_DESCRIPTION','VERSION','PROJECT_DIR','BUILD_RESOURCES_DIR','APP_PACKAGE_NAME','COMPANY_NAME','APP_PRODUCT_FILENAME','APP_INSTALLER_STORE_FILE','MUI_ICON','MUI_UNICON','APP_64','APP_64_NAME','APP_64_HASH','APP_64_UNPACKED_SIZE','HIDE_RUN_AFTER_FINISH','MUI_WELCOMEFINISHPAGE_BITMAP','MUI_UNWELCOMEFINISHPAGE_BITMAP','INSTALL_MODE_PER_ALL_USERS_REQUIRED','SHORTCUT_NAME','UNINSTALLER_ICON','UNINSTALL_DISPLAY_NAME','DO_NOT_CREATE_DESKTOP_SHORTCUT','ESTIMATED_SIZE','COMPRESS','COMPRESSION_METHOD','BUILD_UNINSTALLER','UNINSTALLER_OUT_FILE']);
      for(const arg of args.slice(3,-1)) {
        if(arg.startsWith('-D')) {
          // Pinned electron-builder emits this exact valueless mixed-case flag
          // for the reviewed directory chooser. No other mixed-case form wins.
          check(arg==='-DallowToChangeInstallationDirectory'||
            /^-D[A-Z_0-9]+(?:=[^\r\n\0]*)?$/.test(arg)&&defines.has(arg.slice(2).split('=')[0]),'unsafe/unlisted NSIS define');
        } else if(arg.startsWith('-XOutFile ')) {
          check(samePath(arg.slice(10).replace(/^"|"$/g,''),context.generator.image),'NSIS output escape');
          outFile=true;
        } else check(/^-X(?:VIProductVersion|VIAddVersionKey|Unicode|SetCompress|SetCompressor) /.test(arg),'unlisted NSIS compiler command');
      }
      check(outFile,'NSIS output not bound');kind='makensis';
    } else if(samePath(file,context.generator.image)) {
      check(args.length===0,'generator arguments prohibited');
      check(options.env?.__COMPAT_LAYER==='RunAsInvoker','generator compatibility contract');
      check(samePath(cwd,context.root),'generator cwd mismatch');
      // The bridge, not Node path inspection, retains and fingerprints the newly
      // generated image before CreateProcess under the existing owner Job.
      pinned(context.bootstrap);pinned(context.generator.script);
      mapped=context.bootstrap;
      mappedArgs=['-I','-B',context.generator.script,context.generator.requestPath,context.generator.requestSha256];
      check(/^[a-f0-9]{64}$/.test(context.generator.requestSha256||''),'generator request pin missing');
      kind='nsis-generator';
    } else deny('unlisted executable '+file);
    if(kind!=='nsis-generator')pinned(file);
    const remaining=Math.floor(context.deadline-now());
    check(remaining>0,'expired build lease');
    if(options.timeout!==undefined)check(Number.isFinite(options.timeout)&&options.timeout>0,'invalid child timeout');
    const prepared={file:mapped,args:mappedArgs,options:{...options,cwd,env:environment(options.env),shell:false,windowsHide:true,detached:false,timeout:Math.min(remaining,options.timeout??remaining),maxBuffer:Math.min(options.maxBuffer??16*1024*1024,16*1024*1024)}};
    launches.push({kind,file:mapped,args:mappedArgs,cwd,windowsHide:true});
    authorized.set(prepared,launches.length-1);
    onChildEvent('prepared',{index:launches.length-1,kind,file:mapped,cwd});
    return prepared;
  }
  function observe(prepared,child) {
    const index=authorized.get(prepared);
    onChildEvent('spawned',{index,pid:Number.isInteger(child.pid)?child.pid:null});
    child.once('error',error=>onChildEvent('error',{index,code:typeof error.code==='string'?error.code:'UNKNOWN'}));
    child.once('close',(code,signal)=>onChildEvent('closed',{index,code,signal}));
    return child;
  }
  function install(target=cp) {
    const originals={};
    for(const name of ['spawn','execFile','fork','exec','spawnSync','execFileSync','execSync']) originals[name]=target[name];
    target.spawn=function(file,args,options){const p=prepare(file,args,options,'spawn');try{return observe(p,originals.spawn.call(this,p.file,p.args,p.options));}catch(error){onChildEvent('error',{index:authorized.get(p),code:typeof error.code==='string'?error.code:'UNKNOWN'});throw error;}};
    target.execFile=function(file,args,options,callback){
      if(typeof options==='function'){callback=options;options={};}
      const p=prepare(file,args,options,'execFile');
      try{return observe(p,originals.execFile.call(this,p.file,p.args,p.options,callback));}catch(error){onChildEvent('error',{index:authorized.get(p),code:typeof error.code==='string'?error.code:'UNKNOWN'});throw error;}
    };
    for(const name of ['fork','exec','spawnSync','execFileSync','execSync'])target[name]=()=>deny('unsupported process API '+name);
    if(target===cp)syncBuiltinESMExports();
    return ()=>{Object.assign(target,originals);if(target===cp)syncBuiltinESMExports();};
  }
  function wrapBuilderUtilities(util) {
    const original=util.spawn;
    check(typeof original==='function','builder-util spawn export missing');
    util.spawn=function(command,args,options,...rest) {
      if(command==='npm') {
        check(equalArgs(args,['prefix','-w']),'unlisted npm command');
        pinned(context.npmCli);
        return original.call(this,context.node,[context.npmCli,...args],options,...rest);
      }
      return original.call(this,command,args,options,...rest);
    };
    return ()=>{util.spawn=original;};
  }
  function rejectNetwork() {deny('network access prohibited during pack');}
  return {prepare,install,wrapBuilderUtilities,assertClean,rejectNetwork,launches};
}

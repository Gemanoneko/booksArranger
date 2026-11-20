// The desktop check's C: guard (Sergei, 2026-11-19: nothing we run may write to C: again, except what cannot be written
// on I:). Before 0.30.0, fixture roots on C: (C:\BA-*, C:\BASF-*, about 20 GB) and test folders in the real user Temp
// (books-main-*, codex-books-2026-10-20) were left by our runs. The check now points every child's TEMP at its own scratch
// (scripts/check-desktop.mjs); this guard proves it: it lists a few C: places at the start and again at the end, and a new
// entry fails the run, named by its full path.
// Cheap by design: one directory listing per place, twice. It sees what is still there at the end, not an entry made and
// removed during the run. A place that cannot be listed (C:\Windows\Temp is closed to a normal account) is reported as not
// checked, never as passed.
// Inside folders that were already there (Senua 0.30.0 m5): every folder or file in those places whose NAME only Books
// Arranger uses (OWN below: Books Arranger, books-*, BA-*, BASF-*, codex-books-*) is walked too, to a bounded depth and
// entry count, and a new entry or a file whose size or time changed fails the run. That covers the app's own C: folders
// (%APPDATA%\Books Arranger, %LOCALAPPDATA%\books-arranger-updater, the installer's records in %LOCALAPPDATA%\Programs) and
// any folder a run of ours left. Other programs' folders (npm-cache, electron, Microsoft, ...) are still read only by name
// at the top: other programs write inside them all the time (another studio's npm wrote two logs into npm-cache\_logs within
// 15 minutes on 2026-11-19), so watching inside them would fail runs on their work. A write of ours inside one of them,
// or a change to an existing top-level file there, is not seen; nothing the check starts runs npm, electron-builder or pip.
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';

// What our runs may still write on C:, each because it cannot live on I:. Exact paths; nothing else is allowed.
// Empty since 0.30.0: nothing the desktop check starts needs C:. (Outside the check, the release's GitHub CLI login under
// %APPDATA%\GitHub CLI and Windows' own records are not written by these checks; see the Brief, 0.30.0.)
export const C_DRIVE_EXCEPTIONS=Object.freeze([]);

// Temporary names our tests and engine make (Python tempfile: prefix + 8 of [a-z0-9_]; Node mkdtemp: prefix + 6 of
// [A-Za-z0-9]). tests/test_c_drive_guard.js scans the sources for every prefix and fails if one is missing here.
// Python's default name (tmp + 8) is not here: any program's Python makes it (two empty ones from another program appeared
// in the real Temp within 6 minutes on 2026-11-19), so a new one is named in a note and never fails the run.
export const OUR_TEMP_PREFIXES=Object.freeze(['n-','sr','ds','do','bm','case-','.books-arranger-','audio-read-',
 'cleanup-','controls-','current-package-','durable-decisions-','git-alias-','installer-snapshot-','move-integration-source-',
 'move-integration-target-','mp3-staging-','multisource-','nas-dispose-','nas-removal-','owned-','package-retention-','progress-',
 'producer-core-','publication-native-','relocation-source-','relocation-target-','retention-','selected-temp-','uninstall-launch-',
 'zone-','installation-paths-','lock-pin-','portable-paths-','qa-entry-','c-drive-guard-']);
const escape=text=>text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const SHAPED=new RegExp('^(?:'+OUR_TEMP_PREFIXES.map(escape).join('|')+')(?:[a-z0-9_]{8}|[A-Za-z0-9]{6})','u');
// Names only Books Arranger uses, whatever follows: Books Arranger, books-*, ba-*/BA-*, BASF-*, codex-books-*. (SQLite's
// etilqs_* temporary files are not here: any program's SQLite makes them, and one from another program sat in the real
// Temp on 2026-11-19.)
const OWN=/^(?:books|ba[-_]|basf|codex-books|\.books-arranger)/i;
export function isOwnName(name){return OWN.test(name);}
export function isOurTempName(name){return OWN.test(name)||SHAPED.test(name);}
export function isPythonDefaultTempName(name){return /^tmp[a-z0-9_]{8}(?:$|\.)/.test(name);}
// How far the guard reads inside one folder of ours: the app's own C: folders hold about 200 entries.
export const INSIDE_LIMITS=Object.freeze({entries:5000,depth:8});

const key=p=>path.win32.normalize(p).replace(/[\\]+$/,'').toLowerCase();

// Inputs the checks only read. Any other BOOKS_* path names a place a test writes (C:\BASF-* came from such a root).
const READ_ONLY_INPUTS=new Set(['BOOKS_QA_RUNTIME_ROOT','BOOKS_MP3_REAL_FIXTURE','BOOKS_QA_TARGET_PYTHON','BOOKS_QA_TARGET_BACKEND']);
export function cDriveEnvRefusal(env,root,approved=fs.existsSync('I:/AI Projects')?'I:/AI Projects':'C:/Antigravity Projects'){
 function allowed(value){
  if(!/^[a-z]:[\\/]/i.test(value)||value.slice(3).split(/[\\/]/).some(part=>part==='..'||/[. ]$|[:*?"<>|]/.test(part)))return false;
  const dest=key(value);
  if(!dest.startsWith(key(approved)+'\\'))return false;
  for(let component=dest;component!==path.win32.dirname(component);component=path.win32.dirname(component)){
   try{
    if(fs.lstatSync(component).isSymbolicLink()||key(fs.realpathSync.native(component))!==component)return false;
   }catch(error){if(error.code!=='ENOENT')return false;}
  }
  return true;
 }
 const paths=[['checkout',root],['scratch',path.win32.join(root,'scratch')]];
 for(const [name,value] of Object.entries(env)){
  if(!value||!/^BOOKS_/i.test(name)||READ_ONLY_INPUTS.has(name.toUpperCase()))continue;
  if(/^(?:[a-z]:|[\\/])/i.test(value)||/(?:_ROOT|_FIXTURE_SOURCE|_FIXTURE_TARGET)$/i.test(name))paths.push([name,value]);
 }
 const refused=paths.filter(([,value])=>!allowed(value)).map(([name,value])=>name+'='+value);
 return refused.length?'Refusing to run the checks: '+refused.join(', ')+' requires a physical destination inside '+approved:null;
}

// The places checked by default, from the real profile (os.userInfo, never TEMP or USERPROFILE: the check redirects those).
export function cDrivePlaces({home=os.userInfo().homedir,systemDrive='C:',startTemp=[process.env.TEMP,process.env.TMP]}={}){
 const drive=systemDrive.replace(/[\\/:]+$/,'')+':',local=path.win32.join(home,'AppData','Local'),roaming=path.win32.join(home,'AppData','Roaming');
 const realTemp=path.win32.join(local,'Temp');
 const places=[
  {dir:drive+'\\',mode:'any',label:'the C: drive root'},
  {dir:realTemp,mode:'ours',label:'the real user Temp folder'},
  {dir:path.win32.join(drive+'\\','Windows','Temp'),mode:'ours',label:'the Windows Temp folder'},
  {dir:home,mode:'any',label:'the user profile folder'},
  {dir:local,mode:'any',label:'%LOCALAPPDATA%'},
  {dir:roaming,mode:'any',label:'%APPDATA%'},
  {dir:path.win32.join(drive+'\\','ProgramData'),mode:'any',label:'C:\\ProgramData'},
  {dir:path.win32.join(drive+'\\','Program Files'),mode:'any',label:'C:\\Program Files'},
  {dir:path.win32.join(drive+'\\','Program Files (x86)'),mode:'any',label:'C:\\Program Files (x86)'},
  {dir:path.win32.join(drive+'\\','Users'),mode:'any',label:'C:\\Users'},
  // The installer's records (books-arranger-installation.json and the others) and its old per-user install folder.
  {dir:path.win32.join(local,'Programs'),mode:'ours',label:'%LOCALAPPDATA%\\Programs'},
 ];
 // The Temp folder this check was started with, when it is another folder on C: (its children get the check's own).
 for(const temp of startTemp)if(temp&&path.win32.isAbsolute(temp)&&key(temp).startsWith(drive.toLowerCase())&&!places.some(p=>key(p.dir)===key(temp)))
  places.push({dir:path.win32.normalize(temp),mode:'ours',label:'the Temp folder this check was started with'});
 return places;
}

function list(dir){
 try{return {names:new Set(fs.readdirSync(dir)),absent:false,why:null};}
 catch(error){return error.code==='ENOENT'?{names:new Set(),absent:true,why:null}:{names:null,absent:false,why:error.code||error.message};}
}

// A file's size and time, 'dir' for a folder (its entries are compared instead), 'link' for a link (never followed).
function signature(file){
 try{const s=fs.lstatSync(file);return s.isSymbolicLink()?'link':s.isDirectory()?'dir':s.size+':'+s.mtimeMs;}
 catch(error){return error.code==='ENOENT'?null:'unreadable';}
}
// One folder or file of ours: every entry under it, at most limits.entries. A folder that cannot be read, or one at
// limits.depth, is closed: what is under it is not compared. Over the entry limit the folder is not compared at all.
function walk(root,limits){
 const items=new Map(),top=signature(root);let over=null,count=0;
 if(top===null)return null;
 items.set('',top);
 const stack=top==='dir'?[['',0]]:[];
 while(stack.length&&!over){
  const [relative,depth]=stack.pop();let names;
  try{names=fs.readdirSync(path.join(root,relative)).sort();}catch{items.set(relative,'unreadable');continue;}
  for(const name of names){
   if(++count>limits.entries){over='over '+limits.entries+' entries';break;}
   const inner=relative?path.join(relative,name):name,sig=signature(path.join(root,inner));
   if(sig==='dir'&&depth+1>=limits.depth)items.set(inner,'deep');
   else{items.set(inner,sig);if(sig==='dir')stack.push([inner,depth+1]);}
  }
 }
 return {items,over};
}
const isFile=sig=>typeof sig==='string'&&!['dir','link','unreadable','deep'].includes(sig);
const under=(relative,parents)=>parents.some(p=>p===''||relative.startsWith(p+path.sep));

export function startCDriveGuard({places=cDrivePlaces(),exceptions=C_DRIVE_EXCEPTIONS,limits=INSIDE_LIMITS}={}){
 const inside=listing=>listing.names?new Map([...listing.names].filter(isOwnName).map(name=>[name,walk(path.join(listing.dir,name),limits)])):new Map();
 const before=places.map(place=>{const listing={place,dir:place.dir,...list(place.dir)};return {...listing,inside:inside(listing)};});
 return {places,finish(){
  const violations=[],allowed=[],notChecked=[],notes=[],allow=new Map(exceptions.map(e=>[key(e.path),e]));
  const report=(p,place,kind)=>{const exception=allow.get(key(p));if(exception)allowed.push({path:p,reason:exception.reason});else violations.push({path:p,place,kind});};
  let read=0;
  for(const start of before){
   const {place}=start,end=list(place.dir);
   if(start.names===null||end.names===null){notChecked.push({dir:place.dir,why:start.why||end.why});continue;}
   // A place that was not there at the start and is now: the place itself is the new entry.
   if(start.absent&&!end.absent){report(place.dir,place,'new');continue;}
   for(const name of end.names){
    if(start.names.has(name))continue;
    if(place.mode==='any'||isOurTempName(name))report(path.join(place.dir,name),place,'new');
    else if(isPythonDefaultTempName(name))notes.push({path:path.join(place.dir,name),place});
   }
   // Inside each folder (or file) of ours that was there at the start and still is.
   for(const [name,first] of start.inside){
    const root=path.join(place.dir,name),last=end.names.has(name)?walk(root,limits):null;
    if(!first||!last)continue;  // gone: removing is not a write
    if(first.over||last.over){notChecked.push({dir:root,why:'partly checked: '+(first.over||last.over)});continue;}
    read+=last.items.size;
    const closed=[...first.items].filter(([,sig])=>sig==='unreadable'||sig==='deep').map(([relative])=>relative);
    for(const [relative,sig] of last.items){
     if(under(relative,closed))continue;
     const was=first.items.get(relative),file=relative?path.join(root,relative):root;
     if(was===undefined)report(file,place,'new');
     else if(isFile(sig)&&isFile(was)&&sig!==was)report(file,place,'changed');
    }
   }
  }
  const lines=[];
  for(const v of violations)lines.push('C: guard: '+(v.kind==='changed'?'CHANGED':'NEW')+' on C: during this run: '+v.path+' (in '+v.place.label+')');
  for(const n of notes)lines.push('C: guard: note: new in '+n.place.label+', not counted: '+n.path+' (Python\'s default temporary name; any program makes these)');
  for(const a of allowed)lines.push('C: guard: allowed C: exception present: '+a.path+' ('+a.reason+')');
  for(const n of notChecked)lines.push('C: guard: not checked: '+n.dir+' ('+n.why+')');
  if(!violations.length)lines.push('C: guard: nothing new on C: in '+(places.length-notChecked.filter(n=>places.some(p=>p.dir===n.dir)).length)+' checked places and '+read+' entries inside folders of ours');
  const error=violations.length?'Nothing a check runs may write to C: (Sergei, 2026-11-19). New or changed on C: during this run: '+violations.map(v=>v.path).join(', ')+
   '. If one is not from this run (another program), check its time and run again.':null;
  return {violations,allowed,notChecked,notes,lines,error};
 }};
}

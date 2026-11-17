'use strict';
// Sergei 2026-11-16: Browse… (Folder and Files) and Save As in Manual conversion open where they were last used, across
// restarts. The real renderer with the app's DOM, transport and localStorage doubles: no server, library, native dialog
// or filesystem. The shell's half (a remembered folder is opened only if it still exists) is desktop-folder-picker.test.mjs.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const folder='Z:\\Audiobooks\\Unsorted\\Ужасы и трэшатинка. Сборник рассказов\\Сборник 2';
const tracksIn=[folder+'\\01 Глава.mp3',folder+'\\02 Глава.mp3'];
const exportFile='Z:\\Audiobooks Sorted\\Сборники\\Сборник 2.m4b',exportFolder='Z:\\Audiobooks Sorted\\Сборники\\';
const KEY='books-picker-places-v1',stored=new Map();
let storageBroken=false;
context.localStorage={
  getItem:key=>{if(storageBroken)throw new Error('Storage unavailable');return stored.has(key)?stored.get(key):null;},
  setItem:(key,value)=>{if(storageBroken)throw new Error('Storage unavailable');stored.set(key,String(value));},
  removeItem:key=>{stored.delete(key);},
};
const requests=[];
let folderAnswer=null,filesAnswer=null,outputAnswer=null;
context.booksDesktop={
  chooseFolder:async request=>{requests.push(['folder',JSON.parse(JSON.stringify(request))]);return folderAnswer;},
  chooseAudioFiles:async request=>{requests.push(['files',JSON.parse(JSON.stringify(request))]);return filesAnswer;},
  chooseAudiobookOutput:async request=>{requests.push(['output',JSON.parse(JSON.stringify(request))]);return outputAnswer;},
};
const baseFetch=context.fetch;
const response=result=>({ok:true,status:200,json:async()=>result});
context.fetch=async(route,options)=>{
  if(!route.startsWith('/api/manual-conversion'))return baseFetch(route,options);
  const body=options.body?JSON.parse(options.body):null;
  if(route==='/api/manual-conversion')return response({drafts:[]});
  if(route.endsWith('/inspect')){
    const paths=body.kind==='folder'?tracksIn:body.paths;
    return response({source:body.kind==='folder'?body:{kind:'files'},tracks:paths.map(p=>({path:p,included:true})),suggestions:{title:'Сборник 2'},
      inspections:paths.map((_,i)=>'ab'[i%2].repeat(64)),match_source:'Matching embedded audio metadata'});
  }
  throw new Error('Unexpected manual route '+route);
};
const click=id=>get(id).handlers.click();
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function pickKind(kind){const radio=get('manual-source-'+kind);radio.checked=true;radio.handlers.change();}
const places=()=>JSON.parse(stored.get(KEY)||'{}');
const last=()=>requests.at(-1);

(async()=>{
  click('manual-conversion-tab');await flush();
  pickKind('folder');
  // First use: nothing is remembered, so the picker gets an empty hint and opens at the Windows default.
  assert.equal(get('manual-folder-browse').disabled,false,'Browse… is usable');
  folderAnswer=folder;
  await click('manual-folder-browse');await flush();
  assert.deepEqual(last(),['folder',{title:'Choose a source folder',defaultPath:'',buttonLabel:'Choose folder',remembered:''}]);
  assert.deepEqual(places(),{source:folder},'the chosen folder is remembered, Cyrillic exact');
  assert.equal(get('manual-folder-path').value,folder);

  // Files mode shares the source folder; the folder holding the chosen files becomes the remembered one.
  pickKind('files');
  filesAnswer=tracksIn;
  await click('manual-files-choose');await flush();
  assert.deepEqual(last(),['files',{remembered:folder}]);
  assert.deepEqual(places(),{source:folder+'\\'});

  // Save As: its own remembered folder, separate from the source. The first time none is remembered.
  outputAnswer=exportFile;
  await click('manual-output-choose');await flush();
  assert.equal(last()[0],'output');
  assert.equal(last()[1].remembered,'');
  assert.equal(last()[1].suggestedName,'Сборник 2.m4b');
  assert.equal(get('manual-output-path').textContent,exportFile);
  assert.deepEqual(places(),{source:folder+'\\',export:exportFolder});
  outputAnswer=null;
  await click('manual-output-choose');await flush();
  assert.equal(last()[1].remembered,exportFolder);
  assert.equal(last()[1].defaultPath,exportFile,'the draft keeps its own export path; the shell decides the start');
  assert.deepEqual(places(),{source:folder+'\\',export:exportFolder},'Cancel changes nothing');

  // A restart: what an earlier session stored is what the next pickers are given (read from storage, not memory).
  stored.set(KEY,JSON.stringify({source:'Y:\\Прошлый сеанс',export:'D:\\Готово'}));
  click('manual-new');await flush();
  pickKind('folder');
  folderAnswer=null;
  await click('manual-folder-browse');await flush();
  assert.deepEqual(last(),['folder',{title:'Choose a source folder',defaultPath:'',buttonLabel:'Choose folder',remembered:'Y:\\Прошлый сеанс'}]);
  pickKind('files');filesAnswer=null;
  await click('manual-files-choose');await flush();
  assert.deepEqual(last(),['files',{remembered:'Y:\\Прошлый сеанс'}]);
  assert.deepEqual(places(),{source:'Y:\\Прошлый сеанс',export:'D:\\Готово'},'Cancel keeps the remembered folders');

  // Damaged or unavailable storage never blocks a picker; the next pick writes a clean value again.
  stored.set(KEY,'not json');
  pickKind('folder');folderAnswer=folder;
  await click('manual-folder-browse');await flush();
  assert.equal(last()[1].remembered,'');
  assert.deepEqual(places(),{source:folder});
  storageBroken=true;
  pickKind('files');filesAnswer=tracksIn;const before=requests.length;
  await click('manual-files-choose');await flush();
  assert.equal(requests.length,before+1,'the picker still opens');
  assert.deepEqual(last(),['files',{remembered:''}]);
  storageBroken=false;
  assert.deepEqual(places(),{source:folder});
  // Futaba O-r2-3: Files mode pre-ticks Light novel for files from a Light Novels folder, as Folder mode does; files from
  // an ordinary folder are not ticked. O-r2-4: Save As then starts in Audiobooks Sorted\Light Novels, with Audiobooks
  // Sorted as the shell's fallback while Light Novels does not exist yet.
  run('state={...(state || {}),audiobook_output_root:"Z:\\\\Audiobooks Sorted",source_roots:["Z:\\\\Audiobooks"]}');
  const novel='Z:\\Audiobooks\\Light Novels\\Ayatsuji Yukito\\Иная';
  click('manual-new');await flush();
  pickKind('files');filesAnswer=tracksIn;
  await click('manual-files-choose');await flush();
  assert.equal(get('manual-meta-light_novel').checked,false,'positive control: an ordinary folder is not ticked');
  click('manual-new');await flush();
  pickKind('files');filesAnswer=[novel+'\\01.mp3',novel+'\\02.mp3'];
  await click('manual-files-choose');await flush();
  assert.equal(get('manual-meta-light_novel').checked,true,'files from Light Novels are ticked');
  assert.equal(get('manual-light-help').hidden,false,'with "Light novel from the folder name."');
  outputAnswer=null;
  await click('manual-output-choose');await flush();
  assert.equal(last()[0],'output');
  assert.equal(last()[1].defaultPath,'Z:\\Audiobooks Sorted\\Light Novels\\Сборник 2.m4b');
  assert.equal(last()[1].remembered,'Z:\\Audiobooks Sorted','the shell falls back to the library, never Windows\' own start');
  console.log('Picker memory renderer passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
new Function('require','__dirname',harness)(require,__dirname);

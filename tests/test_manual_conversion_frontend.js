'use strict';
// Real renderer with the app's DOM and transport doubles. No library, server, native windows or filesystem mutation.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const fixtureFolder='Z:\\Audiobooks\\Сборник 2';
const first=fixtureFolder+'\\02.mp3',second=fixtureFolder+'\\10.flac';
const destination='D:\\Finished\\Мой сборник.m4b';
const server=new Map(),saves=[],queuePosts=[],reopenPosts=[];
let saveFinish=null,delaySave=false,dropQueueReply=true,chosenOutput=null,chosenFiles=null,inspectionError='',inspected=[];
let suggestions={title:'Matched collection',author:'Matched author'};
const baseFetch=context.fetch;
const response=result=>({ok:true,status:200,json:async()=>result});
context.booksDesktop={
  chooseFolder:async()=>null,
  chooseAudioFiles:async()=>chosenFiles,
  chooseAudiobookOutput:async()=>chosenOutput,
};
for(const id of ['manual-folder-load','pause-jobs','resume-jobs'])get(id).click=()=>get(id).handlers.click?.();
context.fetch=async(route,options)=>{
  if(!route.startsWith('/api/manual-conversion'))return baseFetch(route,options);
  const body=options.body?JSON.parse(options.body):null;
  if(route==='/api/manual-conversion')return response({drafts:[...server.values()]});
  if(route.endsWith('/inspect')){
    inspected.push(body);
    if(inspectionError)return {ok:false,status:400,json:async()=>({error:inspectionError})};
    const source=body.kind==='folder'?body:{kind:'files'};
    const paths=body.kind==='folder'?[first,second]:body.paths;
    return response({source,tracks:paths.map(path=>({path,included:true})),suggestions,match_source:'Matching embedded audio metadata'});
  }
  if(route.endsWith('/discard')){server.delete(body.id);return response({discarded:true});}
  if(route.endsWith('/reopen')){
    reopenPosts.push(body);
    const {job_id,candidate_id,retry_allowed,reopen_allowed,reason,...previous}=server.get(body.id);
    server.set(body.id,{...previous,revision:body.revision+1,state:'draft'});
    throw new Error('Accepted reopen reply lost');
  }
  if(route.endsWith('/save')){
    saves.push(body);
    const draft={...body,revision:body.revision+1,state:'draft'};
    server.set(draft.id,draft);
    if(delaySave)return new Promise(resolve=>{saveFinish=()=>resolve(response({draft}));});
    return response({draft});
  }
  if(route.endsWith('/queue')){
    queuePosts.push(body);
    const draft={...body,revision:body.revision+1,state:'queued',job_id:'manual-job',candidate_id:body.id};
    server.set(draft.id,draft);
    if(dropQueueReply){dropQueueReply=false;throw new Error('Accepted reply lost');}
    return response({draft});
  }
  throw new Error('Unexpected manual route '+route);
};
const click=id=>get(id).handlers.click();
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function pickKind(kind){const radio=get('manual-source-'+kind);radio.checked=true;radio.handlers.change();}
function enter(id,value){const input=get(id);input.value=value;input.handlers.input();}

(async()=>{
  click('manual-conversion-tab');await flush();
  assert.equal(get('library-workspace').hidden,true);
  const tabs=[get('library-tab'),get('manual-conversion-tab')];
  tabs[1].handlers.keydown({key:'Home',preventDefault(){}});
  assert.equal(document.activeElement,tabs[0]);
  assert.equal(tabs[1].getAttribute('aria-selected'),'true');
  pickKind('folder');enter('manual-folder-path',fixtureFolder);
  await click('manual-folder-load');
  assert.deepEqual(inspected[0],{kind:'folder',path:fixtureFolder});
  assert.match(get('manual-match').textContent,/Matching embedded/);
  assert.equal(get('manual-meta-title').value,'Matched collection');
  const tracks=get('manual-track-list');
  assert.equal(tracks.children[0].children[0].textContent,'02.mp3');
  tracks.children[1].children[1].children[0].handlers.click();
  assert.equal(tracks.children[0].children[0].textContent,'10.flac');
  const firstCheckbox=tracks.children[1].children[1].children[2].children[0];
  firstCheckbox.checked=false;firstCheckbox.handlers.change();
  assert.match(get('manual-track-count').textContent,/1 included file/);

  enter('manual-meta-title','My collection');
  enter('manual-meta-author','');
  enter('manual-meta-series','Cycle');enter('manual-meta-number','2.5');enter('manual-meta-universe','World');
  chosenOutput=destination;
  await click('manual-output-choose');
  chosenOutput=null;
  await click('manual-output-choose');
  assert.equal(get('manual-output-path').textContent,destination,'cancel leaves previous output');
  delaySave=true;
  const saving=click('manual-save');
  enter('manual-meta-title','My newer title');
  saveFinish();await saving;await flush();
  assert.equal(get('manual-meta-title').value,'My newer title','a late save reply preserves newer edits');
  assert.match(get('manual-saved-reservation').textContent,/1 saved file is reserved/);
  assert.match(get('manual-editor-status').textContent,/Unsaved changes/);
  assert.deepEqual(saves[0].tracks,[{path:second,included:true},{path:first,included:false}]);
  assert.equal(saves[0].metadata.author,'','explicitly cleared match stays clear');
  assert.equal(saves[0].metadata.number,'2.5');
  assert.equal(saves[0].destination,destination);
  assert.deepEqual(saves[0].metadata_touched,['author','number','series','title','universe']);

  await click('manual-queue');await flush();
  assert.equal(queuePosts.length,1);
  assert.equal(queuePosts[0].metadata.title,'My newer title');
  assert.equal(queuePosts[0].revision,1);
  assert.equal(get('manual-draft-actions').hidden,true,'lost reply reconciles against accepted job');
  assert.match(get('manual-editor-status').textContent,/Queued|Waiting for audiobook jobs/);

  click('library-tab');
  assert.equal(get('library-workspace').hidden,false);
  click('manual-conversion-tab');await flush();
  assert.equal(get('manual-meta-title').value,'My newer title');
  click('manual-new');pickKind('files');
  chosenFiles=[first,second];await click('manual-files-choose');
  assert.deepEqual(inspected.at(-1),{kind:'files',paths:[first,second]});
  tracks.children[0].children[1].children[2].handlers.click();
  assert.equal(tracks.children[0].children[0].textContent,'10.flac');
  delaySave=false;
  enter('manual-meta-author','');
  await click('manual-save');await flush();
  get('manual-books').replaceChildren();
  const reopened=vm.createContext({...context});
  vm.runInContext(app,reopened);
  click('manual-conversion-tab');await flush();
  const savedButton=get('manual-books').children.map(row=>row.children[0]).find(button=>button.textContent==='Matched collection');
  assert(savedButton,'saved draft is offered after renderer restart');
  savedButton.handlers.click();
  assert.equal(get('manual-meta-title').value,'Matched collection');
  assert.equal(get('manual-meta-author').value,'');
  suggestions={title:'Second match',author:'A different suggested author'};
  const duplicate=fixtureFolder+'\\Other\\02.mp3';
  chosenFiles=[first,duplicate];await click('manual-files-choose');
  assert.equal(get('manual-meta-title').value,'Second match','an earlier suggested title can be replaced after restart');
  assert.equal(get('manual-meta-author').value,'','explicitly cleared author persists after restart and source replacement');
  assert.equal(tracks.children[0].children[2].children[1].getAttribute('aria-label'),'Move down: '+first);
  assert.equal(tracks.children[1].children[2].children[2].getAttribute('aria-label'),'Remove from this book: '+duplicate);
  suggestions={author:'Only a different suggested author'};
  await click('manual-files-choose');
  assert.equal(get('manual-meta-title').value,'','an obsolete suggested title is cleared');
  assert.equal(get('manual-match').textContent,'','the UI claims no match when all suggestions were declined');

  inspectionError='An audio file is unavailable.';
  await click('manual-files-choose');
  assert.equal(get('manual-queue').disabled,true);
  assert.equal(get('manual-save').disabled,true);
  assert.match(get('manual-source-status').textContent,/confirm the previously loaded files/);
  await click('manual-queue');
  assert.equal(queuePosts.length,1,'failed source selection cannot silently submit the old source');
  click('manual-source-reuse');
  assert.equal(get('manual-queue').disabled,false);
  assert.match(get('manual-source-status').textContent,/Using the previously loaded files/);

  click('manual-discard');assert.equal(get('manual-discard-question').hidden,false);
  await click('manual-discard-confirm');await flush();
  assert.equal(server.size,1,'only the queued draft remains');
  assert.match(get('manual-list-status').textContent,/available for automatic processing/);

  const failed={...server.get(queuePosts[0].id),state:'failed',reason:'An output already exists',retry_allowed:true,reopen_allowed:true};
  server.set(failed.id,failed);
  click('manual-conversion-tab');await flush();
  const failedButton=get('manual-books').children.map(row=>row.children[0]).find(button=>button.textContent===failed.metadata.title);
  failedButton.handlers.click();
  assert.equal(get('manual-job-retry').hidden,false);
  assert.equal(get('manual-job-reopen').hidden,false);
  get('manual-job-reopen').focus();
  await click('manual-job-reopen');await flush();
  assert.deepEqual(reopenPosts,[{id:failed.id,revision:failed.revision}]);
  assert.equal(get('manual-job-reopen').hidden,true);
  assert.equal(get('manual-draft-actions').hidden,false);
  assert.equal(get('manual-output-path').textContent,destination);
  assert.equal(get('manual-meta-title').value,'My newer title');
  assert.match(get('manual-saved-reservation').textContent,/1 saved file is reserved/);
  assert.match(get('manual-editor-status').textContent,/Draft reopened\. Use Save As/);
  assert.equal(document.activeElement,get('manual-output-choose'));
  chosenOutput='D:\\Finished\\Replacement.m4b';
  await click('manual-output-choose');
  assert.equal(get('manual-output-path').textContent,chosenOutput);
  console.log('Manual Conversion renderer passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
new Function('require','__dirname',harness)(require,__dirname);

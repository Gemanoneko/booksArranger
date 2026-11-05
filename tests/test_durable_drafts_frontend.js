'use strict';
// Deferred durable acknowledgments against the actual renderer and existing DOM
// behavior fixture. No server, native app or library is opened.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const replies=[],lookups=[],baseFetch=context.fetch;let mode='';
context.fetch=async(route,options)=>{
  const body=options?.body?JSON.parse(options.body):null;
  if(mode==='lookup'&&route==='/api/book-decisions/book'){const response=await baseFetch(route,options);return new Promise(resolve=>lookups.push(()=>resolve(response)));}
  if((mode==='tracks'&&route==='/api/candidate/tracks')||(mode==='choices'&&route==='/api/candidate/metadata-choices')||(mode==='review'&&route==='/api/candidate/review')||(mode==='file'&&route==='/api/review')||(mode==='approve'&&route==='/api/candidate/approve')){
    calls.push({route,options});return new Promise(resolve=>replies.push({body,resolve}));
  }
  return baseFetch(route,options);
};
const ok=value=>({ok:true,status:200,json:async()=>value});
const walk=element=>[element,...element.children.flatMap(walk)];
function fixture(id,extra={}){return blocked({id,path:id,review:{title:'Original title',author:'Original Author',canonical_author:'Original Author',narrator:'Original Reader'},creation:{status:'Held',can_create:false,reasons:[]},automatic:null,members:[{member_key:'one',path:'private/one.mp3'}],track_order:['one'],included:['one'],...extra});}
function paint(row){context.fixture=row;run('state='+JSON.stringify(backend)+';dirty=false;trackDirty=false;selectedPath=null;view="candidates";filters.candidates="all";rows=[fixture];totalRows=1;select(fixture,true);renderRows(true);controls()');}
function answer(row,result={}){const sent=replies.at(-1);sent.resolve(ok({row:{...row,revision:row.revision+1},...result}));}
function type(field,value){const control=get('review-form').elements.namedItem(field);control.value=value;get('review-form').handlers.input({target:control});}
(async()=>{
  // All three nontext confirmations stay editable; none may be cleared by the older save.
  for(const flag of ['source-coverage','playback-order','add-chapters']){
    const row=fixture('flags-'+flag);paint(row);await tick();
    get('source-coverage').checked=true;get('playback-order').checked=true;get('add-chapters').checked=false;
    mode='tracks';const save=get('save-tracks').handlers.click();await tick();
    const before=run('JSON.stringify(trackDraft)');get(flag).checked=!get(flag).checked;get(flag).handlers.change();
    const visible=get(flag).checked;assert.equal(run('JSON.stringify(trackDraft)'),before,'checkbox change does not alter the old order snapshot');
    answer(row);await save;await tick();assert.equal(get(flag).checked,visible,flag+': late ack preserves the new checkbox');assert.equal(run('trackDirty'),true,flag+': newer edit stays unsaved');assert.match(get('track-save-status').textContent,/Your newer edits are not saved yet/);
  }
  // A radio change does not increment editSeq, so compare the submitted answer set too.
  const question={id:'q',field:'narrator',label:'Reader',options:[{id:'provider',values:{narrator:'Provider Reader'},sources:[]}]};
  const choiceRow=fixture('choice-radio',{metadata_questions:{signature:'same-evidence',unresolved_count:1,questions:[question]}});
  paint(choiceRow);await tick();mode='choices';
  const radio=value=>walk(get('metadata-question-fields')).find(node=>node.type==='radio'&&node.value===value);
  radio('provider').checked=true;radio('provider').handlers.change();const seq=run('editSeq');
  const savingChoice=get('save-metadata-choices').handlers.click();await tick();
  radio('unresolved').checked=true;radio('unresolved').handlers.change();assert.equal(run('editSeq'),seq);
  answer(choiceRow);await savingChoice;await tick();
  assert.equal(run('metadataChoiceState.answers.q.mode'),'unresolved');assert.equal(run('metadataChoiceState.edited'),true);assert.match(get('metadata-question-status').textContent,/Your newer choices are not saved yet/);
  context.updated={...choiceRow,revision:choiceRow.revision+1,metadata_questions:{...choiceRow.metadata_questions,questions:[{...question,decision:{mode:'provider',option_id:'provider'}}]}};
  run('select(updated,false)');assert.equal(run('metadataChoiceState.answers.q.mode'),'unresolved','catalog poll retains the newer unsaved radio');
  // Proposal and cover buttons can change without a form input event.
  for(const selector of ['proposal','cover']){
    const row=fixture('metadata-'+selector,{matching:{state:'completed',proposals:[{id:'private-proposal',title:'Proposal title',authors:['New Proposal Author'],provider:'Fixture',public_url:'https://example.org/book'}]},cover_choices:[{id:'private-cover',source_label:'Fixture cover'}]});
    paint(row);await tick();type('narrator','Submitted Reader');mode='review';const save=run('saveMetadata()');await tick();const seq=run('editSeq');
    const button=walk(get(selector==='proposal'?'metadata-proposals':'cover-choices')).find(node=>node.textContent===(selector==='proposal'?'Use as proposal':'Use this cover'));assert.ok(button);
    button.handlers.click();assert.equal(run('editSeq'),seq,'selector does not synthesize a text edit');
    answer(row);await save;await tick();assert.equal(run('dirty'),true,selector+': newer selection stays unsaved');
    if(selector==='cover')assert.equal(run('coverId'),'private-cover');else assert.equal(get('review-form').elements.namedItem('canonical_author').value,'New Proposal Author');
  }
  // Same ID/path is not sufficient after the source generation changes during acceptance.
  const oldMetadata=fixture('source-metadata');paint(oldMetadata);await tick();type('narrator','Submitted old-source Reader');mode='review';const oldSave=run('saveMetadata()');await tick();
  context.changed={...oldMetadata,revision:oldMetadata.revision+1,fingerprint:'b'.repeat(64)};run('rows=[changed];select(changed,false)');answer(oldMetadata);await oldSave;
  assert.equal(run('selectedRow.fingerprint'),'b'.repeat(64),'old metadata response cannot roll back current source identity');assert.equal(run('dirty'),true);assert.equal(get('review-form').elements.namedItem('narrator').value,'Submitted old-source Reader');
  const oldFile=fixture('source-file',{kind:'audiobook',path:'private/file.m4b',revision:undefined,fingerprint:undefined,size:101,modified:'1762398765432109876'});paint(oldFile);await tick();type('narrator','Submitted file Reader');mode='file';const fileSave=run('saveMetadata()');await tick();
  context.changed={...oldFile,size:102,modified:'1762398765432109877'};run('rows=[changed];select(changed,false)');replies.at(-1).resolve(ok({saved:true}));await fileSave;
  assert.equal(run('selectedRow.modified'),'1762398765432109877');assert.equal(run('dirty'),true,'old file generation acknowledgement cannot clear a current draft');
  const oldLookup=fixture('file-lookup',{kind:'audiobook',path:'private/restored-file.m4b',revision:undefined,fingerprint:undefined,size:201,modified:'1762398765432109876'});paint(oldLookup);await tick();type('narrator','Accepted old-file Reader');mode='file';const acceptedFile=run('saveMetadata()');await tick();replies.at(-1).resolve(ok({queued:true}));await acceptedFile;await tick();
  mode='lookup';const pendingLookup=run('restoreDecisionPanel(selectedRow,selectedLibrary)');await tick();assert.equal(lookups.length,1);
  context.changed={...oldLookup,size:202,modified:'1762398765432109877',review:{...oldLookup.review,narrator:'Current-file Reader'}};run('dirty=false;rows=[changed];select(changed,false)');mode='';lookups[0]();await pendingLookup;await tick();
  assert.equal(get('review-form').elements.namedItem('narrator').value,'Current-file Reader','late file owner lookup cannot overlay a different size/mtime generation');
  const oldTracks=fixture('source-tracks');paint(oldTracks);await tick();get('source-coverage').checked=true;get('source-coverage').handlers.change();mode='tracks';const trackSave= get('save-tracks').handlers.click();await tick();
  context.changed={...oldTracks,revision:oldTracks.revision+1,fingerprint:'c'.repeat(64)};run('rows=[changed];select(changed,false)');answer(oldTracks);await trackSave;
  assert.equal(run('selectedRow.fingerprint'),'c'.repeat(64));assert.equal(run('trackDirty'),true,'old-source track ack cannot clear the draft or restore its row');
  const oldChoices=fixture('source-choices',{metadata_questions:{signature:'same-evidence',unresolved_count:1,questions:[question]}});paint(oldChoices);await tick();mode='choices';
  radio('provider').checked=true;radio('provider').handlers.change();const choiceSave=get('save-metadata-choices').handlers.click();await tick();
  context.changed={...oldChoices,revision:oldChoices.revision+1,fingerprint:'d'.repeat(64)};run('rows=[changed];select(changed,false)');answer(oldChoices);await choiceSave;
  assert.equal(run('selectedRow.fingerprint'),'d'.repeat(64));assert.equal(run('metadataChoiceState.fingerprint'),'d'.repeat(64),'choice ack remains bound to its submitted source');
  const ask={kind:'title_author',why:'author_missing',fields:{title:{proposal:'Original title'},author:{proposal:'Original Author'}},candidates:[],destination:{path:'private/book.m4b',taken:false}};
  // Even an applied/job-enqueued reply cannot discard a newer row draft.
  const approval=fixture('approval-newer',{ask});paint(approval);mode='approve';const savingApproval=run('askPress(askRows.get(fixture.id),"approve")');await tick();
  run('askDraft(fixture.id).title="Newer unsaved title"');answer(approval,{approved:true,job_id:'private-job'});await savingApproval;
  assert.equal(run('askDone.has(fixture.id)'),false);assert.equal(run('askDraft(fixture.id).title'),'Newer unsaved title');assert.match(run('askResults.get(fixture.id).text'),/Your newer edits are not saved yet/);
  // Reopen and press an unchanged accepted approval: reuse its durable receipt.
  const pending=fixture('approval-pending',{ask});paint(pending);const accepted=run('askPress(askRows.get(fixture.id),"approve")');await tick();replies.at(-1).resolve(ok({queued:true}));await accepted;
  const sent=calls.filter(call=>call.route==='/api/book-decisions').length;run('renderRows(true);controls()');await run('askPress(askRows.get(fixture.id),"approve")');
  assert.equal(calls.filter(call=>call.route==='/api/book-decisions').length,sent,'no new request ID/job for the same current effective approval');assert.equal(run('askDone.has(fixture.id)'),false);assert.equal(run('queueState.queued.length'),0);
  console.log('PASS durable newer drafts: all track flags, choice radio/poll, proposal/cover, applied approval, accepted approval reopen/reclick, changed metadata/file/track/choice source generations');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
new Function('require','__dirname',harness)(require,__dirname);

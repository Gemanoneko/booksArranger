// Actual frontend polling through controlled transport/HTTP responses; no browser window.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const nodes=new Map(),fields=new Map();
function make(id=''){
  let text='';return {id,value:id==='library'?'Audiobooks':'',hidden:false,children:[],dataset:{},handlers:{},writes:0,
    get textContent(){return text;},set textContent(value){text=value;this.writes++;},
    addEventListener(type,fn){this.handlers[type]=fn;},setAttribute(){},
    replaceChildren(){this.children=[];},append(child){this.children.push(child);},
    insertAdjacentElement(_where,child){nodes.set(child.id,child);}};
}
function node(id){if(!nodes.has(id))nodes.set(id,make(id));return nodes.get(id);}
for(const name of ['original_language','title','author','canonical_author','narrator','universe','series','number','genre','topic','multi_author','anthology'])fields.set(name,{value:'',checked:false,options:[{}],append(value){this.options.push(value);}});
node('review-form').elements={namedItem:name=>fields.get(name)};
const clean={path:'C:/fixture/book.mp3',kind:'audiobook',size:10,modified:'2000000000000000001',error:'',missing:0,metadata:{title:'Existing',tags:{}},preview:{reason:'Needs review',path:''},review:null};
const bad={...clean,path:'C:/fixture/bad.mp3',error:'Source metadata read failed',preview:{reason:'Source metadata read failed',path:'',confidence:'Read error'}};
const state={version:'0.2.0',root:'C:/fixture',genres:['Horror'],active_library:null,stopping:false,
  status:{state:'completed with errors',count:2,checked:2,reused:1,pending:0,errors:1,current:'Source metadata read failed'}};
let mode='network',resolveState=null,rejectState=null,calls=0,lastInventoryRoute='',servedRows=[clean,bad];
const response=(body,ok=true,status=200)=>({ok,status,json:async()=>body});
const context=vm.createContext({console,clean,bad,document:{
  getElementById:id=>['connection-notice','inventory-intro'].includes(id)?nodes.get(id)||null:node(id),
  querySelector:()=>({content:'fixture-token'}),querySelectorAll:()=>[],createElement:()=>make()},
  setTimeout:()=>0,clearTimeout(){},
  fetch:async route=>{
    calls++;
    if(route==='/api/shutdown')return response({stopping:true});
    if(mode==='network')throw new TypeError('Failed to fetch');
    if(route.startsWith('/api/state')){
      if(mode==='auth')return response({error:'Specific authentication error'},false,403);
      if(mode==='stale')return new Promise(resolve=>{resolveState=()=>resolve(response(state));});
      if(mode==='deferred-failure')return new Promise((_resolve,reject)=>{rejectState=()=>reject(new TypeError('Failed to fetch'));});
      return response(state);
    }
    if(route.startsWith('/api/inventory')){
      lastInventoryRoute=route;
      if(mode==='inventory-network')throw new TypeError('Failed to fetch');
      return response({rows:servedRows,total:servedRows.length});
    }
    throw new Error('Unexpected fixture route '+route);
  }});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8'),context);
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const poll=()=>vm.runInContext('poll()',context);
(async()=>{
  await flush();
  vm.runInContext("view='files';viewControls()",context);
  const notice=node('connection-notice');
  assert.equal(notice.hidden,false);
  assert.equal(notice.textContent,'Connection interrupted; automatic processing may still be running. Retrying…');
  assert.match(node('status').textContent,/Last received:/);
  const announcements=notice.writes;
  vm.runInContext("message('Preview metadata saved')",context);
  await poll();assert.equal(notice.writes,announcements,'repeated transport failure must not announce duplicate notice');
  mode='good';await poll();
  assert.equal(notice.hidden,true);assert.equal(notice.textContent,'');
  assert.equal(node('message').textContent,'Preview metadata saved','recovery must retain action feedback');
  assert.match(node('status').textContent,/Files cataloged 2.*Files checked this scan 2.*Metadata reused this scan 1.*Pending tasks 0.*Read failures this scan 1.*Files with read errors 1/);
  assert.equal(node('page').textContent,'Showing 1–2 of 2 files · All files');
  assert.match(node('inventory-intro').textContent,/Each row is a source file/,'new script must support old HTML without the new helper element');
  vm.runInContext('select(bad,true)',context);assert.match(node('notes').textContent,/Source metadata read failed/);
  vm.runInContext('select(clean,true)',context);fields.get('title').value='Unsaved canonical title';node('review-form').handlers.input();
  state.status.checked++;mode='inventory-network';await poll();
  assert.equal(notice.hidden,false,'state success followed by required inventory failure is not recovery');
  assert.equal(fields.get('title').value,'Unsaved canonical title');
  mode='stale';const pending=poll();await flush();node('library').value='Ebooks';resolveState();await pending;
  assert.equal(notice.hidden,false,'stale-library response must not clear the notice');
  node('library').value='Audiobooks';mode='good';await poll();
  assert.equal(notice.hidden,true);assert.equal(fields.get('title').value,'Unsaved canonical title');
  assert.equal(node('message').textContent,'Preview metadata saved');
  mode='deferred-failure';const oldLibrary=poll();await flush();
  node('library').value='Ebooks';mode='good';await vm.runInContext('refresh(true)',context);
  rejectState();await oldLibrary;
  assert.equal(notice.hidden,true,'old-library failure after new-library success must be ignored');
  node('library').value='Audiobooks';await vm.runInContext('refresh(true)',context);
  mode='deferred-failure';const oldSameLibrary=poll();await flush();
  mode='good';await vm.runInContext('refresh(true)',context);rejectState();await oldSameLibrary;
  assert.equal(notice.hidden,true,'older same-library failure after newer success must be ignored');
  mode='network';await poll();assert.equal(notice.hidden,false,'the latest current-library failure must still show the notice');
  mode='good';await poll();assert.equal(notice.hidden,true);
  mode='auth';await poll();
  assert.equal(notice.hidden,false,'Unverified HTTP status response retains the released unavailable-state notice');
  assert.match(node('status').textContent,/Last received:/);
  assert.equal(node('shutdown').disabled,true,'Unverified status must keep mutations disabled');
  assert.match(node('message').textContent,/Preview metadata saved.*Specific authentication error/s);
  mode='good';await poll();
  assert.match(node('message').textContent,/Specific authentication error/,'healthy transport must not erase real backend feedback');
  assert.match(node('status').textContent,/Files with read errors 1/);
  mode='good';node('search').value='Book query';await node('filter').handlers.change();await flush();
  assert.match(lastInventoryRoute,/search=Book%20query/);assert.match(lastInventoryRoute,/status=/);
  fields.get('title').value='Dirty retained draft';node('review-form').handlers.input();
  servedRows=[];await vm.runInContext('refresh(true)',context);
  assert.equal(fields.get('title').value,'Dirty retained draft');assert.equal(node('details').hidden,false,'Filtering a selected row out must preserve its details and draft');
  node('search').value='Should clear';node('filter').value='errors';await node('error-shortcut').handlers.click();await flush();
  assert.equal(node('search').value,'');assert.match(lastInventoryRoute,/status=errors/);assert.match(lastInventoryRoute,/offset=0/);
  await node('clear-filters').handlers.click();await flush();assert.match(lastInventoryRoute,/status=all/);
  // Restart notice requires a complete current-owner poll and actual paused/idle state.
  Object.assign(state,{version:'0.11.0',application:'Books Arranger',pid:12345,port:5210,instance:'a'.repeat(32),restart_context:true,automatic_processing:{state:'Paused',run_id:'saved'}});
  mode='inventory-network';await vm.runInContext('refresh(true)',context).catch(()=>{});
  assert.doesNotMatch(node('message').textContent,/Books Arranger restarted/,'partial refresh cannot acknowledge restart');
  mode='good';await vm.runInContext('refresh(true)',context);
  assert.equal(node('message').textContent,'Books Arranger restarted. Automatic processing is paused.');
  vm.runInContext("message('Current user feedback')",context);await poll();
  assert.equal(node('message').textContent,'Current user feedback','same replacement must not repeatedly overwrite feedback');
  state.instance='b'.repeat(32);state.automatic_processing={state:'Running',phase:'waiting',run_id:'saved'};
  await vm.runInContext('refresh(true)',context);assert.equal(node('message').textContent,'Current user feedback','authorized resume cannot claim paused');
  state.automatic_processing={state:'Paused',run_id:'saved'};await poll();
  assert.equal(node('message').textContent,'Current user feedback','later user pause cannot revive stale restart notice');
  state.instance='c'.repeat(32);state.automatic_processing={state:'Idle',run_id:null};
  await vm.runInContext('refresh(true)',context);assert.equal(node('message').textContent,'Books Arranger restarted.');
  mode='network';await poll();assert.equal(notice.hidden,false,'later connection failure shows the notice again');
  const beforeUnavailableShutdown=calls;
  assert.equal(node('shutdown').disabled,true,'Unavailable status prevents a shutdown action');
  await node('shutdown').handlers.click();
  assert.equal(calls,beforeUnavailableShutdown,'Even a synthetic disabled-button click must send no shutdown request');
  assert.equal(notice.hidden,false,'Blocked shutdown cannot claim a successful stop or reconnect');
  mode='good';await poll();assert.equal(notice.hidden,true,'A complete current-owner poll restores action availability before shutdown');
  await node('shutdown').handlers.click();
  assert.equal(notice.hidden,true);assert.match(node('status').textContent,/Server stopping/);
  const afterShutdown=calls;await poll();assert.equal(calls,afterShutdown,'intentional shutdown must not reconnect');
  console.log('PASS actual polling failure/recovery, repeated failure, partial refresh, stale library, review/read-error preservation, old HTML fallback, explicit file units, once-per-owner Paused/Idle acknowledgement with Running suppression, blocked unavailable shutdown and intentional shutdown');
})().catch(error=>{console.error(error);process.exitCode=1;});

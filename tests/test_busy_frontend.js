'use strict';
// Busy engine (0.22.1, backlog 7; Judy's spec, section 4): in the desktop window a missing answer means "busy", never
// "interrupted". After 3 s without an answer a notice says the app is busy (with the passes the last update named), the
// status line reads "Last update HH:MM:SS · ...", and from 2 min the notice counts minutes; a failed read sets no offline
// flag and buttons stay usable; a press keeps its pending face with the ladder (3 s, 1 min); a press with no answer ends
// with its "not confirmed" line; Delete's Deleting line takes the same sentences. Browser mode keeps the old words
// (test_connection.js). The real frontend on the Retry test's doubles, with window.booksDesktop present. No server.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
const desktop='vm.createContext({window:{booksDesktop:{}},document,';
if(!harness.includes('vm.createContext({document,'))throw Error('harness changed: the desktop window cannot be added');
harness=harness.replace('vm.createContext({document,',desktop);
harness+=String.raw`
const FOLDER='Z:\\Audiobooks\\Iron';
const missingRow=name=>({id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
  title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:['Иван Петров'],members:[{path:FOLDER+'\\01.m4b',missing:true},{path:FOLDER+'\\02.m4b',missing:true}],track_order:[],included:[],review:{},review_context:{},status:'Held',
  automatic:{state:'Held',reasons:['Files missing']},creation:{status:'Held',can_create:false,reasons:[]},source_directory_count:1,
  ask:{kind:'files_missing',also:null,why:'',reasons:['Files missing'],fields:{title:{proposal:'Iron Inferno',basis:'tag'},author:{proposal:'Иван Петров',basis:'tag'}},candidates:[],
    missing:{folders:[FOLDER],files:[FOLDER+'\\01.m4b',FOLDER+'\\02.m4b'],present:0,total:2},destination:{path:'x.m4b',absolute:'',taken:false,reason:''},delete:{kind:'files_missing',present:0}}});
let stateAnswer=null;const baseFetch=context.fetch;
context.fetch=async(route,options)=>{if(route.startsWith('/api/state') && stateAnswer)return stateAnswer();if(route.startsWith('/api/candidate/delete') && context.deleteAnswer)return context.deleteAnswer(route);return baseFetch(route,options);};
const ok=value=>({ok:true,status:200,json:async()=>value});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const shown=text=>assert.doesNotMatch(text,/Connection interrupted|Local server unavailable|Retrying…/);
(async()=>{
  assert.equal(run('desktopMode()'),true,'positive control: the desktop window');
  const passes=[{id:'identity',kind:'identity',total:506},{id:'series',kind:'series',total:12},{id:'scan',kind:'scan',step:'researching',total:40}];
  run('state='+JSON.stringify({...backend,activities:passes})+';loadingActive=false');
  const known=Date.now()-60000;run('receivedStatus.set("Audiobooks","Discovery: idle · Files cataloged 5");receivedAt.set("Audiobooks",'+known+')');
  const clock=run('wallClock('+known+')');assert.match(clock,/^\d\d:\d\d:\d\d$/);
  // 1. A status read with no answer: nothing for 3 s, then the notice with the named passes, Last update and Last confirmed.
  let answer;stateAnswer=()=>new Promise(resolve=>{answer=resolve;});
  const t0=Date.now(),reading=run('refresh()');
  run('pressTick('+(t0+2000)+')');assert.equal(get('connection-notice').textContent,'','under 3 s: nothing');
  run('pressTick('+(t0+4000)+')');
  assert.equal(get('connection-notice').hidden,false);
  assert.equal(get('connection-notice').textContent,'The app is busy with background work and answers slowly. This page refreshes by itself.\nBusy with: re-checking 506 finished books, updating series on 12 books, researching 40 books.');
  assert.equal(get('status').textContent,'Last update '+clock+' · Discovery: idle · Files cataloged 5');
  assert.match(get('jobs-status').textContent,/^Last confirmed — /);
  run('pressTick('+(t0+150000)+')');
  assert.equal(get('connection-notice').textContent,'No answer for 2 min: the app is busy with background work. Your files are not touched. If it goes on, quit from the tray and open Books Arranger again.');
  assert.equal(run('recoveryDisconnected'),false,'no offline flag for a slow answer');
  // The first answer clears it.
  answer(ok({...backend,activities:[]}));await reading;await tick();
  assert.equal(get('connection-notice').hidden,true);assert.equal(get('connection-notice').textContent,'');assert.doesNotMatch(get('jobs-status').textContent,/^Last confirmed/);
  // Without named passes there is no second line.
  stateAnswer=()=>new Promise(resolve=>{answer=resolve;});const again=run('refresh()'),t1=Date.now();run('pressTick('+(t1+5000)+')');
  assert.equal(get('connection-notice').textContent,'The app is busy with background work and answers slowly. This page refreshes by itself.');
  answer(ok(backend));await again;await tick();
  // 2. A failed read (a reset connection): no offline flag, no "Connection interrupted", buttons stay usable.
  stateAnswer=()=>{throw new TypeError('Failed to fetch');};
  try{await run('refresh()');}catch(error){run('refreshFailed(new TypeError("Failed to fetch"))');}
  assert.equal(run('recoveryDisconnected'),false);shown(get('connection-notice').textContent);shown(get('status').textContent);
  stateAnswer=null;
  // 3. The press ladder (4.3): the pending note, then one sentence more at 3 s and at 1 min; the face stays pending.
  const row=blocked();show(row);inventoryRows=[row];retryOverride=()=>new Promise(()=>{});
  run('retryJob()');const at=run('retryPending.at');
  run('pressTick('+(at+1000)+')');assert.equal(get('retry-note').textContent,'Checking this book…');
  run('pressTick('+(at+5000)+')');assert.equal(get('retry-note').textContent,'Checking this book… The app is busy with background work, so this takes longer.');
  assert.equal(get('retry-job').textContent,'Checking…');assert.equal(get('retry-job').getAttribute('aria-disabled'),'true','never back to Retry, never a second press');
  run('pressTick('+(at+70000)+')');assert.equal(get('retry-note').textContent,'Checking this book… Still waiting (1 min). The app is busy with background work.');
  assert.equal(run('PRESS_TIMEOUT'),600000,'the 15 s abort is gone');
  // While the press waits, a status answer does not end the notice (no flicker each poll) and keeps one status format.
  run('for(const key of [...inflight.keys()])inflight.set(key,Date.now()-5000);pressTick()');
  assert.match(get('connection-notice').textContent,/^The app is busy with background work/);
  await run('refresh()');run('clearConnectionNotice()');
  assert.equal(get('connection-notice').hidden,false,'still shown: the press still waits');assert.match(get('status').textContent,/^Last update \d\d:\d\d:\d\d · /);
  run('retryPending=null;busy=false;retryResult=null;inflight.clear();controls()');
  // 4. No answer at all: the "not confirmed" lines replace every "Connection interrupted…" (4.3).
  assert.equal(run('lostLine()'),"This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check this row in a moment.");
  assert.equal(run('lostLine("bulk")'),"The retry requests haven't been confirmed yet. They may still go through. Check the list in a moment.");
  assert.equal(run('lostLine("discard")'),"The review may not have been discarded. The app hasn't confirmed it. Check the book before trying again.");
  assert.equal(run('askErrorText({},"approve")'),"This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check this row in a moment.");
  run('view="candidates";filters.candidates="output_attention";attentionGroup="all";viewControls()');
  context.fixture=[missingRow('i')];run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');
  const tr=[...get('inventory').children].find(item=>item.dataset.path==='cand-i'),del=[...tr.children[5].children[0].children].find(b=>b.textContent==='Delete book');
  let release;context.deleteAnswer=route=>route.endsWith('/delete-preview')?ok({files:[],bytes:0,folders:[],stay:{items:0},refusal:null,kind:'files_missing',blocked:null}):new Promise((resolve,reject)=>{release=reject;});
  await del.handlers.click({stopPropagation(){}});await tick();
  // Section 5 (n = 0), the dialog Sergei saw.
  assert.equal(get('delete-dialog-files').textContent,'No files will be deleted from your disk.');assert.equal(get('delete-confirm').textContent,'Delete book');
  const deleting=get('delete-confirm').handlers.click({});await tick();
  const started=run('deleteDialog.at');run('pressTick('+(started+4000)+')');
  assert.equal(get('delete-dialog-status').textContent,'Removing this book... The app is busy with background work, so this takes longer.','4.4: Deleting takes the same sentences');
  release(new TypeError('Failed to fetch'));await deleting;
  assert.equal(get('delete-dialog-files').textContent,"The delete may not have finished. The app hasn't confirmed it. Check the list before trying again.");
  assert.doesNotMatch(get('delete-dialog-files').textContent,/Nothing was deleted/,'an unknown outcome never says nothing was deleted');
  await get('delete-close').handlers.click({});
  for(const id of ['connection-notice','status','retry-note','message','delete-dialog-files'])shown(get(id).textContent);
  assert.equal(run('recoveryDisconnected'),false,'still no offline flag after a lost press');
  console.log('PASS busy engine (desktop): the 3 s notice with its passes, Last update, the 2 min notice, no offline flag, the press ladder, the not-confirmed lines, Delete slowly');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_busy_frontend.js'),module);m.filename=path.join(__dirname,'test_busy_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

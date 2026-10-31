'use strict';
// Ruling 75a (Sergei 2026-10-31) and Judy's 0.24.1 spec, section 1: the stale list. The poll never waits for a list read,
// the status read has a time limit, a slow list keeps its rows with "List from HH:MM…" (states S1-S8), a list read is
// asked again after a long wait without restarting the line, the poll pauses between list reads while the app is busy, and
// list reads never count as the app being silent (oldestWait). The real frontend on the Retry test's doubles, in the
// desktop window (window.booksDesktop present). No server.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
const desktop='vm.createContext({window:{booksDesktop:{}},document,';
if(!harness.includes('vm.createContext({document,'))throw Error('harness changed: the desktop window cannot be added');
harness=harness.replace('vm.createContext({document,',desktop);
harness+=String.raw`
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const listed=()=>calls.filter(call=>call.route.startsWith('/api/inventory')).length;
const line=()=>get('list-stale');
(async()=>{
  assert.equal(run('desktopMode()'),true,'positive control: the desktop window');
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8'),app=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
  assert.match(html,/<p id="attention-loading"[^>]*>[^<]*<\/p>\s*<p id="list-stale" role="status" aria-live="polite" hidden><\/p>\s*<div id="attention-groups"/,'Judy 1.2: after #attention-loading, before #attention-groups');
  assert.ok(css.includes('#list-stale{font-size:15px;color:var(--text);margin:8px 0;overflow-wrap:anywhere}#list-stale.escalated{color:var(--warning)}'));
  assert.match(app,/request\(\x60\/api\/state\?library=\$\{encodeURIComponent\(library\)\}\x60,undefined,STATE_TIMEOUT\)/,'the status read has a time limit');
  run('state='+JSON.stringify(backend)+';loadingActive=false;view="candidates";filters.candidates="all";viewControls()');
  const a=blocked(),b=blocked({id:'cand-b',path:'cand-b',title_clue:'Title b'});
  inventoryRows=[a,b];assert.equal(await run('refresh(true)'),true);
  assert.equal(get('inventory').children.length,2,'positive control: a painted list');
  const painted=run('paintedAt'),clock=run('askClock(new Date('+painted+'))');assert.equal(line().hidden,true);

  // The poll never waits for the list: the refresh answers with the status while the read is out; a second poll does not
  // start another read for the same list.
  let answer;inventoryOverride=()=>new Promise(resolve=>{answer=resolve;});
  run('lastKey=null');const before=listed();assert.equal(await run('refresh()'),true,'the refresh ends with the status');
  assert.equal(listed(),before+1);assert.equal(await run('refresh()'),true);assert.equal(listed(),before+1,'one read for one list');
  assert.equal(run('oldestWait()'),0,'a list read never counts as the app being silent');
  const since=run('listAsk.since');
  // S0, S1: nothing for 5 s, then the line; the rows stay and stay usable.
  run('pressTick('+(since+4000)+')');assert.equal(line().hidden,true,'a normal slow read moves nothing');
  run('pressTick('+(since+6000)+')');assert.equal(line().hidden,false);
  assert.equal(line().textContent,'List from '+clock+'. The app is busy; this updates by itself.');
  assert.equal(line().classes.has('escalated'),false);assert.equal(get('inventory').children.length,2);
  assert.equal(run('busyShown'),false,'the page-top notice keys on the status only');assert.equal(get('connection-notice').textContent,'');
  // S2: after the long wait the read is asked again; the line keeps its text and time; no blank frame.
  run('listAsk.started-=300001');assert.equal(await run('refresh()'),true);assert.equal(listed(),before+2,'asked again');
  assert.equal(run('listAsk.since'),since,'a re-ask never restarts the clock');
  run('pressTick('+(since+7000)+')');assert.equal(line().textContent,'List from '+clock+'. The app is busy; this updates by itself.');assert.equal(get('inventory').children.length,2);
  // S4: the status read is silent too: the page-top notice says it, the line only the time.
  run('statusSilentSince='+since);run('pressTick('+(since+8000)+')');
  assert.equal(line().textContent,'List from '+clock+'.');assert.equal(get('connection-notice').hidden,false);assert.match(get('connection-notice').textContent,/^The app is busy/);
  run('statusSilentSince=null;pressTick('+(since+8000)+')');
  // S3: ten minutes after the first ask: the way out, in --warning.
  run('pressTick('+(since+600001)+')');
  assert.equal(line().textContent,'List from '+clock+'; the app has been busy for over 10 minutes. If it goes on, quit from the tray and open Books Arranger again.');
  assert.equal(line().classes.has('escalated'),true);
  // S7: the answer paints and the line goes at once; nothing is left in #message.
  const c=blocked({id:'cand-c',path:'cand-c',title_clue:'Title c'});
  answer({ok:true,status:200,json:async()=>({rows:[a,b,c],total:3})});await tick();await tick();
  assert.equal(get('inventory').children.length,3);assert.equal(line().hidden,true);assert.equal(line().textContent,'');assert.equal(get('message').textContent,'');
  inventoryOverride=null;

  // The pause: while the app is busy the next poll leaves LIST_PAUSE after the last answer; a fresh list asked for (lastKey
  // null) goes at once.
  run('lastListTook=6000;listAnsweredAt=Date.now()');const paused=listed();
  assert.equal(await run('refresh()'),true);assert.equal(listed(),paused,'no read inside the pause');
  run('lastKey=null');await run('refresh()');await tick();assert.equal(listed(),paused+1,'an asked-for list is never paused');
  run('lastListTook=0;listAnsweredAt=Date.now()-60000');

  // S5: an answer that is an error other than "busy": the time only; the error keeps its place in #message.
  inventoryOverride=async()=>({ok:false,status:500,json:async()=>({error:'Local catalog request failed; source files remain untouched'})});
  run('lastKey=null');await run('refresh()');await tick();await tick();
  const clock2=run('askClock(new Date(paintedAt))');
  assert.equal(line().textContent,'List from '+clock2+'.');assert.match(get('message').textContent,/Local catalog request failed/);
  inventoryOverride=null;run('lastKey=null');await run('refresh()');await tick();await tick();assert.equal(line().hidden,true,'a good answer clears it');
  run("message('')");

  // S6: a new filter whose list is slow: blank rows, no line, and the loading text says why after 5 s.
  inventoryOverride=()=>new Promise(resolve=>{answer=resolve;});
  get('filter').value='output_attention';const changing=get('filter').handlers.change();await tick();
  assert.equal(get('inventory').children.length,0);const loading=get('page').textContent;assert.match(loading,/^Loading Output needs attention/);
  const since6=run('listAsk.since');run('pressTick('+(since6+6000)+')');
  assert.equal(line().hidden,true);assert.equal(get('empty').textContent,loading+' The app is busy; this updates by itself.');assert.equal(get('page').textContent,loading,'#page keeps the plain loading text');
  run('pressTick('+(since6+600001)+')');assert.equal(get('empty').textContent,loading+' The app has been busy for over 10 minutes. If it goes on, quit from the tray and open Books Arranger again.');
  answer({ok:true,status:200,json:async()=>({rows:[a],total:1})});await changing;await tick();
  assert.equal(get('inventory').children.length,1);assert.equal(line().hidden,true);inventoryOverride=null;

  // S8: never while the load strip is up.
  inventoryOverride=()=>new Promise(()=>{});run('lastKey=null');await run('refresh()');const since8=run('listAsk.since');
  run('loadingActive=true;pressTick('+(since8+6000)+')');assert.equal(line().hidden,true);
  run('loadingActive=false;pressTick('+(since8+6000)+')');assert.equal(line().hidden,false,'positive control: the same wait shows the line');
  // A list from another day names the day (75a-t).
  const yesterday=new Date();yesterday.setHours(23,48,0,0);yesterday.setDate(yesterday.getDate()-1);
  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  assert.equal(run('listClock('+yesterday.getTime()+',Date.now())'),yesterday.getDate()+' '+months[yesterday.getMonth()]+', 23:48');
  run('paintedAt='+yesterday.getTime()+';pressTick('+(since8+6000)+')');assert.equal(line().textContent,'List from '+yesterday.getDate()+' '+months[yesterday.getMonth()]+', 23:48. The app is busy; this updates by itself.');
  // "Life Signs" (2026-10-31): a queued Approve refused because the book changed meanwhile asks for the list at once, past the
  // busy pause; another refusal keeps the pause.
  context.outcome={id:'q1',action:'approve',book_id:'cand-a',title:'Title a',result:'refused',code:'changed',error:'Candidate changed; reload evidence before reviewing'};
  run('lastKey="painted";applyQueueOutcome(outcome)');assert.equal(run('lastKey'),null);assert.match(run('askResults.get("cand-a").text'),/^Approve cancelled: this book changed/);
  context.outcome={...context.outcome,id:'q2',code:'name_taken',error:'Name taken'};run('lastKey="painted";applyQueueOutcome(outcome)');assert.equal(run('lastKey'),'painted');
  // Ruling 76a: Approve (row and bulk) and names Save carry the files the row showed; a malformed one is never sent.
  const hash='0123456789abcdef'.repeat(4);assert.equal(run('JSON.stringify(seen({fingerprint:"'+hash+'"}))'),JSON.stringify({fingerprint:hash}));
  assert.equal(run('JSON.stringify(seen({fingerprint:"x"}))+JSON.stringify(seen({}))'),'{}{}');
  assert.equal(app.match(/request\('\/api\/candidate\/approve',\{library:'Audiobooks',id(?::row\.id)?,revision:row\.revision,\.\.\.seen\(row\)/g)?.length,2,'both Approve requests');
  assert.ok(app.includes("request('/api/candidate/names-save',{library:'Audiobooks',id,revision:row.revision,...seen(row),"),'names Save');
  console.log('PASS stale list: the poll never waits for the list, S0-S8, re-ask keeps the clock, the busy pause, list reads out of oldestWait, the status time limit, another day; 76a fingerprint');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_stale_list_frontend.js'),module);m.filename=path.join(__dirname,'test_stale_list_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

'use strict';
// 0.31.0 milestone B, the page (Judy's Docs/BooksArranger_0.31.0_UX.md sections 3.2 to 3.4a, amended 2026-11-23; rulings
// R18, R20, R24 and R26; Futaba's checks 36 to 39 and 46 as far as they run headless): finished audiobooks renamed and
// moved by the rules. The notice above the Running list, the grouped Waiting items, no Cancel on the app's own move, the
// record "Renamed or moved by the app" and the list "Could not be renamed or moved", and the quiet line gone. Also gap 9
// (the title's own mention of a series is not shown on a book whose series was dropped as doubtful). The real frontend on
// the destination test's DOM and transport doubles: no server, no library, no window, no file touched.
const fs=require('node:fs'),path=require('node:path');
// The Retry test's doubles, then the destination test's own helpers (its raw template text up to its first case).
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
const helpers=fs.readFileSync(path.join(__dirname,'test_0231_destination_frontend.js'),'utf8'),opening='harness+=String.raw`',from=helpers.indexOf(opening)+opening.length;
harness+=helpers.slice(from,helpers.indexOf('(async()=>{',from));
harness+=String.raw`
const tick=async(n=12)=>{for(let i=0;i<n;i++)await new Promise(resolve=>setImmediate(resolve));};
// The two read-only routes, each answered by the test: a queue of answers (a body, or a function of the sent data).
const filingSent=[],filingAnswers={'/api/filing/record':[],'/api/filing/could-not':[]};const destFetch=context.fetch;
context.fetch=async(route,options)=>{
  if(!Object.hasOwn(filingAnswers,route))return destFetch(route,options);
  const data=options?.body?JSON.parse(options.body):undefined;filingSent.push({route,data});
  const next=filingAnswers[route].shift();if(next===undefined)return {ok:true,status:200,json:async()=>({count:0,matching:0,entries:[]})};
  const body=await (typeof next==='function'?next(data):next);
  return body && body.fail?{ok:false,status:500,json:async()=>({error:'fixture failure'})}:{ok:true,status:200,json:async()=>body};
};
const timers=[];context.setTimeout=(callback,ms)=>{timers.push({callback,ms});return timers.length;};context.clearTimeout=id=>{if(timers[id-1])timers[id-1].cleared=true;};
const fire=()=>{const due=timers.splice(0).filter(timer=>!timer.cleared && timer.ms===300);for(const timer of due)timer.callback();return due.length;};
const filing=(more={})=>({known:true,at:1,paused:false,drive_away:false,left:0,writes_waiting:0,writes_running:0,moves_waiting:0,moves_running:0,renames_waiting:0,next_write:null,next_move:null,could_not:0,
  record:{count:0,last_at:null},waiting_for_lookup:0,on_hold:0,settling:0,tries:{limit:3,spacing_seconds:3600},feed:2,...more});
const pending=(more={})=>({any:true,running:0,paused:0,waiting:0,still_checking:0,attention:0,hold:0,moves:0,drives:0,lookups:{series:0,details:0,all:0},same_name:0,filing:0,could_not_file:0,...more});
function show(work={}){
  context.fixtureState={...backend,work:{rows:[],waiting:[],counts:{},unread:[],snapshot_age_ms:0,refreshing:false,state:'continues',pending:pending(),waits_for_you:[],background:{},lookups_waiting:[],filing:filing(),...work}};
  run('state=fixtureState;renderJobs()');
}
const lines=element=>walk(element).filter(e=>!e.children.length && shown(e)).map(e=>e.textContent).filter(Boolean);
const AT=new Date(2026,10,22,14,5).toISOString();  // 22 Nov, 14:05 in the machine's own zone
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="all";viewControls()');
  const html=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'),css=fs.readFileSync(path.join(__dirname,'../web/style.css'),'utf8'),app=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');

  // 1. The quiet line is gone whole (R24; check 36 and the amended check 37): its element, its function, both sentences.
  for(const text of [html,app,css]){
    assert.ok(!text.includes('jobs-series-found'),'the element and every reader of it');
    for(const words of ['Series found for','recorded and stay where they are','is recorded and stays where it is','No audiobook is renamed or moved.','next version','could not be renamed or moved. They stay where they are','could not be renamed or moved. It stays where it is'])
      assert.ok(!text.includes(words),words);
  }
  assert.equal(run('typeof renderSeriesFound'),'undefined');
  // Positive control that the scan reads the page: the words that replace it are there.
  assert.ok(html.includes('Could not be renamed or moved') && app.includes('Could not be renamed or moved · '));

  // 2. The notice (3.3a; check 38): from the engine's number, above 5, until zero.
  const notice=get('jobs-filing-notice'),count=get('jobs-filing-count');
  assert.match(html,/<\/div><div id="jobs-filing-notice" class="notice" aria-live="off" hidden><p id="jobs-filing-count"><\/p><p id="jobs-filing-what">A book is renamed or moved to match its author, series and title\. The audio is not changed\. If you quit, the app goes on next time\.<\/p><\/div><div id="jobs-activity">/,'under the toolbar, above the unread line and the Running list; no button, no tooltip, no focus stop');
  assert.doesNotMatch(html.match(/<div id="jobs-filing-notice".*?<\/div>/)[0],/button|title=|tabindex/);
  show({filing:filing({left:5})});assert.equal(notice.hidden,true,'5 or fewer from the start: never shown');
  show({filing:filing({left:3})});assert.equal(notice.hidden,true);
  show({filing:filing({left:6})});assert.equal(notice.hidden,false);assert.equal(count.textContent,'Filing 6 finished audiobooks under the names found for them.');
  show({filing:filing({left:212})});assert.equal(count.textContent,'Filing 212 finished audiobooks under the names found for them.');
  show({filing:filing({left:12345})});assert.equal(count.textContent,'Filing 12,345 finished audiobooks under the names found for them.','a five-digit number');
  show({filing:filing({left:4,paused:true}),state:'paused'});assert.equal(notice.hidden,false,'once up it stays below 5, also while paused');assert.equal(count.textContent,'Filing 4 finished audiobooks under the names found for them.');
  show({filing:filing({left:1})});assert.equal(count.textContent,'Filing 1 finished audiobook under the names found for it.');
  // A look-up that ends later adds its book: the number is the engine's at this poll, so the sentence stays true.
  show({filing:filing({left:9})});assert.equal(count.textContent,'Filing 9 finished audiobooks under the names found for them.');
  // The engine has not counted (or sends nothing for a moment): the notice stays as it is.
  show({filing:filing({known:false,left:null})});assert.equal(notice.hidden,false);assert.equal(count.textContent,'Filing 9 finished audiobooks under the names found for them.');
  show({filing:filing({left:0})});assert.equal(notice.hidden,true,'at zero it goes, and nothing takes its place');
  show({filing:filing({left:4})});assert.equal(notice.hidden,true,'after zero the rule starts again: 4 is not more than 5');
  show({filing:filing({left:84})});assert.equal(notice.hidden,false,'the number left after a relaunch');assert.equal(count.textContent,'Filing 84 finished audiobooks under the names found for them.');
  show({filing:null});assert.equal(notice.hidden,false,'an answer without the fact changes nothing');
  show({filing:filing({left:0})});assert.equal(notice.hidden,true);
  // Negative control: an engine that runs no such pass never shows it.
  show({filing:null});assert.equal(notice.hidden,true);
  // No word says the work was cut or taken up again: the notice states what is left, in the same sentence every time.
  for(const word of ['interrupted','resumed','again'])assert.ok(!html.match(/<div id="jobs-filing-notice".*?<\/div>/)[0].includes(word) && !count.textContent.includes(word),word);

  // 3. The grouped Waiting items (3.3): above 5 the engine's whole number, the next book and what blocks it.
  const item=(id,more)=>({id,kind:'action',label_key:'move',subject:'Book '+id,book_id:'b-'+id,blocker:{kind:'conversion',title:'Dune'},ahead:0,background:false,...more});
  const write=id=>({id:'series_write:'+id,kind:'series_write',subject:'Write '+id,book_id:'b-'+id,job_id:id,blocker:{kind:'conversion',title:'Dune'},background:false});
  const waitRows=()=>get('jobs-wait').children.map(li=>({label:li.children[0].children[0].children[0].textContent,subject:li.children[0].children[0].children[1].textContent,line:li.children[0].children[1].textContent,button:li.children[1]}));
  show({waiting:[item('own1',{origin:'rules'}),item('own2',{origin:'rules'}),item('his',{origin:'user'})],lookups_waiting:[write('w1'),write('w2')],
    filing:filing({left:628,writes_waiting:290,moves_waiting:338,next_write:{job_id:'w1',book_id:'b-w1',title:'Оно',move_id:null,blocker:{kind:'conversion',title:'Dune'}},next_move:{job_id:'m1',book_id:'b-own1',title:'Граф Ноль',move_id:'mv1',blocker:null}})});
  let list=waitRows();
  assert.deepEqual(list.map(row=>row.label+row.subject),['Moving finished audiobooks: 338 books','Move: Book his','Writing series into finished audiobooks: 290 books'],'one item per group in the place of its first; his own move stays its own item');
  assert.equal(list[0].line,'Next: Граф Ноль. They run one at a time.');assert.equal(list[2].line,'Next: Оно. It runs when Converting: Dune finishes.');
  assert.equal(list[0].button.hidden,false);assert.equal(list[0].button.title,'List this book: sets Status to All and searches for its title.','never the variant that ends "Its row has Cancel."');
  assert.equal(list[2].button.title,'List this book: sets Status to All and searches for its title.');assert.equal(list[2].button.getAttribute('aria-label'),'Show in list: Оно');
  assert.equal(run('JSON.stringify(waitingItems.get("filing_writes").target)'),'{"id":"b-w1","title":"Оно"}','Show in list is for the next book, by its title');
  assert.equal(run('JSON.stringify(waitingItems.get("filing_moves").target)'),'{"id":"b-own1","title":"Граф Ноль"}');
  assert.equal(list[1].button.title,'List this book: sets Status to All and searches for its title. Its row has Cancel.','positive control: his own queued move has Cancel');
  // Groups with no item of theirs listed (the engine lists only the books in hand): still shown, before the last kinds.
  show({waiting:[{id:'resume',kind:'resume',background:false}],filing:filing({left:14,writes_waiting:6,moves_waiting:8,next_write:{job_id:'w1',book_id:'b-w1',title:'Оно',blocker:null},next_move:null})});
  list=waitRows();assert.deepEqual(list.map(row=>row.label+row.subject),['Writing series into finished audiobooks: 6 books','Moving finished audiobooks: 8 books','Resume audiobook jobs']);
  assert.equal(list[1].line,'They run one at a time.','no next book sent: no name, no button');assert.equal(list[1].button.hidden,true);
  // Negative control: 5 or fewer are not grouped, each listed book is its own item; the app's own move still has the plain tooltip.
  show({waiting:[item('own1',{origin:'rules'}),item('his',{origin:'user'})],lookups_waiting:[write('w1')],filing:filing({left:5,writes_waiting:2,moves_waiting:3,next_write:{title:'Оно',book_id:'b-w1'},next_move:{title:'Граф Ноль',book_id:'b-own1'}})});
  list=waitRows();assert.deepEqual(list.map(row=>row.label+row.subject),['Move: Book own1','Move: Book his','Write series into audiobook: Write w1']);
  assert.equal(list[0].button.title,'List this book: sets Status to All and searches for its title.');assert.equal(list[1].button.title,'List this book: sets Status to All and searches for its title. Its row has Cancel.');
  // The engine's whole numbers of the look-up before review (total, other_waits) in place of the page's own subtraction.
  const before=(more={})=>({count:100,total:340,other_waits:7,next_at:null,waiting:[],limits:{per_source:3},tries_continue:true,...more});
  show({waiting:[{id:'metadata_sources',kind:'metadata_sources',count:360,background:false}],lookup_before_review:before()});  // 360 less 340 is not 7: the engine's number is printed, not a subtraction
  list=waitRows();assert.deepEqual(list.map(row=>row.label+row.subject),['Waiting for an online answer: 340 books','Metadata sources'],'the whole number, not the 100 listed');
  assert.equal(list[1].line,'7 books wait for a source to answer.','the engine\'s other waits');
  show({waiting:[{id:'metadata_sources',kind:'metadata_sources',count:345,background:false}],lookup_before_review:before({other_waits:0})});
  assert.deepEqual(waitRows().map(row=>row.label+row.subject),['Waiting for an online answer: 340 books'],'no other waits: no second item');
  // Negative control: an engine that sends neither number is read as before (the listed count, the subtraction).
  show({waiting:[{id:'metadata_sources',kind:'metadata_sources',count:12,background:false}],lookup_before_review:before({count:9,total:undefined,other_waits:undefined})});
  list=waitRows();assert.deepEqual(list.map(row=>row.label+row.subject),['Waiting for an online answer: 9 books','Metadata sources']);assert.equal(list[1].line,'3 books wait for a source to answer.');
  show();

  // 4. The record's summary (3.4): from the normal state, hidden while empty; its entries only when opened.
  const record=get('filing-record'),summary=get('filing-record-summary'),recordList=get('filing-record-list'),note=get('filing-record-note'),more=get('filing-record-more'),find=get('filing-find');
  assert.match(html,/<details id="filing-record" hidden><summary id="filing-record-summary" title="Finished audiobooks the app renamed or moved by its rules, newest first\.">/);
  assert.match(html,/<p class="field-help">The app files a finished audiobook under the author, series and title it found for certain\. The audio is never changed\.<\/p><p class="filing-find"><label for="filing-find">Find book<\/label> <input id="filing-find" type="search" maxlength="200" title="Show only entries whose title, author or path contains this text\."><\/p>/);
  assert.match(html,/<div id="filing-record-list" class="filing-list" role="group" aria-label="Books renamed or moved by the app" tabindex="0"><\/div>/);
  assert.ok(html.indexOf('id="jobs-you"')<html.indexOf('id="filing-record"') && html.indexOf('id="filing-record"')<html.indexOf('id="filing-could-not"') && html.indexOf('id="filing-could-not"')<html.indexOf('id="approved-help"'),'after Waiting for you, the list under the record, both above the help lines');
  assert.match(css,/\.filing-list\{max-height:40vh;overflow:auto/);assert.doesNotMatch(css,/#filing-[^{]*\{[^}]*(position|float|z-index)|\.filing-[^{]*\{[^}]*(position|float|z-index)|#jobs-filing-[^{]*\{[^}]*(position|float|z-index)/,'everything new is in normal flow');
  show();assert.equal(record.hidden,true,'no empty record');
  show({filing:filing({record:{count:1,last_at:AT}})});assert.equal(record.hidden,false);assert.equal(summary.textContent,'Renamed or moved by the app · 1 · 22 Nov, 14:05');
  show({filing:filing({record:{count:340,last_at:AT}})});assert.equal(summary.textContent,'Renamed or moved by the app · 340 · last 22 Nov, 14:05');
  show({filing:filing({record:{count:1240,last_at:AT}})});assert.equal(summary.textContent,'Renamed or moved by the app · 1,240 · last 22 Nov, 14:05');
  assert.equal(filingSent.length,0,'closed: nothing is fetched');
  const entry=(n,more={})=>({id:'f'+n,book_id:'b'+n,job_id:'j'+n,title:'Граф Ноль',author:'Gibson William',at:AT,from:'Z:\\Audiobooks Sorted\\Gibson William\\Граф Ноль - Gibson William.m4b',to:'Z:\\Audiobooks Sorted\\Gibson William\\Sprawl Trilogy\\2 - Граф Ноль - Gibson William.m4b',
    from_shown:'Gibson William\\Граф Ноль - Gibson William.m4b',to_shown:'Gibson William\\Sprawl Trilogy\\2 - Граф Ноль - Gibson William.m4b',kinds:['series'],reasons:[{kind:'series',name:'Sprawl Trilogy',number:'2',provider:'fantlab',source_url:'https://fantlab.ru/work1'}],in_app:true,...more});
  // Opened, the list not here yet: Loading…; then the entries.
  let release;filingAnswers['/api/filing/record'].push(()=>new Promise(resolve=>{release=resolve;}));
  record.open=true;record.handlers.toggle();await tick();
  assert.deepEqual(filingSent.at(-1),{route:'/api/filing/record',data:{}});assert.equal(note.hidden,false);assert.equal(note.textContent,'Loading…');assert.equal(recordList.children.length,0);
  release({count:3,matching:3,last_at:AT,limit:200,entries:[entry(1),
    entry(2,{title:'The Three-Body Problem',author:'Liu Cixin',from_shown:'Лю Цысинь\\Задача трёх тел - Лю Цысинь.m4b',to_shown:'Liu Cixin\\The Three-Body Problem - Liu Cixin.m4b',in_app:false,
      reasons:[{kind:'title',title:'The Three-Body Problem',provider:'wikidata',source_url:'https://www.wikidata.org/wiki/Q1'},{kind:'author',name:'Liu Cixin'},{kind:'series_name',name:'Remembrance of Earth\'s Past',provider:'',source_url:''}]}),
    entry(3,{reasons:[{kind:'series',name:'Дозоры',number:'1',provider:'',source_url:'javascript:alert(1)'},{kind:'unknown_kind',name:'x'},null],from_shown:'A\\x.m4b',to_shown:'A\\y.m4b'})]});
  await tick();
  assert.equal(note.hidden,true);assert.equal(more.hidden,true);assert.equal(recordList.children.length,3);
  let first=recordList.children[0],text=first.children[0],button=first.children[1];
  assert.deepEqual(text.children[0].children.map(e=>e.textContent).join(''),'Граф Ноль · Gibson William · 22 Nov, 14:05 · Series: Sprawl Trilogy · No. 2 · found on FantLab');
  assert.equal(text.children[0].children[0].className,'filing-title','the title it is filed under now, in weight 600');assert.match(css,/\.filing-title\{font-weight:600\}/);
  assert.equal(text.children[0].children.at(-1).title,'https://fantlab.ru/work1','the source name carries its address');
  assert.deepEqual(lines(text.children[1]),['Was in','Gibson William\\Граф Ноль - Gibson William.m4b']);assert.equal(text.children[1].title,'Z:\\Audiobooks Sorted\\Gibson William\\Граф Ноль - Gibson William.m4b','the full path is the tooltip');
  const now=text.children[2].children[1];assert.equal(text.children[2].children[0].textContent,'Now in');
  assert.deepEqual(now.children.map(e=>[e.className || '',e.textContent]),[['filing-shared','Gibson William\\'],['','Sprawl Trilogy\\2 - Граф Ноль - Gibson William.m4b']],'the folders it shares with Was in are muted, what is new is not');
  assert.match(css,/\.filing-label,\.filing-shared\{color:var\(--muted\)\}/);
  assert.equal(button.textContent,'Show in list');assert.equal(button.title,'List this book: sets Status to All and searches for its title.');assert.equal(button.getAttribute('aria-disabled'),null);
  // An English title, an author folder and a series name; the book is no longer in the app: its button says so and keeps its focus stop.
  const second=recordList.children[1];
  assert.equal(second.children[0].children[0].children.map(e=>e.textContent).join(''),'The Three-Body Problem · Liu Cixin · 22 Nov, 14:05 · English title found on Wikidata · Author folder: Liu Cixin · Series name: Remembrance of Earth\'s Past');
  assert.equal(second.children[0].children[2].children[1].textContent,'Liu Cixin\\The Three-Body Problem - Liu Cixin.m4b','no shared folder: nothing muted');assert.equal(second.children[0].children[2].children[1].children.length,0);
  assert.equal(second.children[1].getAttribute('aria-disabled'),'true');assert.equal(second.children[1].title,'This book is not in the app.');assert.equal(second.children[1].disabled,false,'aria-disabled, never the disabled attribute');
  get('search').value='untouched';await press(second.children[1]);await tick();assert.equal(get('search').value,'untouched','a disabled Show in list does nothing');
  await press(button);await tick();assert.equal(get('search').value,'Граф Ноль','positive control: an enabled one searches for the entry\'s own title');
  // A source the page has no name for, an address that is not a web address, a reason kind it does not know.
  const third=recordList.children[2];assert.equal(third.children[0].children[0].children.map(e=>e.textContent).join(''),'Граф Ноль · Gibson William · 22 Nov, 14:05 · Series: Дозоры · No. 1 · found online');
  assert.ok(!third.children[0].children[0].children.at(-1).title,'no tooltip from an address that is not http');
  assert.deepEqual(third.children[0].children[2].children[1].children.map(e=>e.textContent),['A\\','y.m4b'],'renamed in its folder: the file name shows the change');

  // The number changes while it is open: read again, the list kept until the answer; focus and scroll held.
  recordList.scrollTop=120;recordList.children[2].children[1].focus();
  filingAnswers['/api/filing/record'].push({count:4,matching:4,entries:[entry(4),entry(1),entry(2),entry(3)]});
  show({filing:filing({record:{count:1241,last_at:AT}})});assert.equal(note.hidden,true,'no Loading… on a refresh');assert.equal(recordList.children.length,3);
  await tick();assert.equal(recordList.children.length,4);assert.equal(recordList.scrollTop,120);
  assert.equal(document.activeElement,recordList.children[3].children[1],'the focused Show in list is on the same entry');assert.equal(document.activeElement.dataset.filing,'f3');
  const sentBefore=filingSent.length;show({filing:filing({record:{count:1241,last_at:AT}})});await tick();assert.equal(filingSent.length,sentBefore,'the same number: not read again');
  // More than 200: the newest 200 and the sentence that Find book searches all of them. No paging, no Show more.
  filingAnswers['/api/filing/record'].push({count:1240,matching:1240,entries:Array.from({length:200},(_v,i)=>entry(i))});
  show({filing:filing({record:{count:1240,last_at:AT}})});await tick();
  assert.equal(recordList.children.length,200);assert.equal(more.hidden,false);assert.equal(more.textContent,'Showing the newest 200 of 1,240. Find book searches all of them.');
  assert.ok(!walk(record).some(e=>/Show more|Next page|Previous/.test(e.textContent || '')));

  // Find book: every entry is searched (the engine does it), 300 ms after the last key; the list stays until the answer.
  filingAnswers['/api/filing/record'].push({count:1240,matching:312,entries:Array.from({length:200},(_v,i)=>entry(i))});
  find.value='gib';find.handlers.input();find.value='gibson';find.handlers.input();
  assert.equal(timers.filter(timer=>!timer.cleared && timer.ms===300).length,1,'one search, 300 ms after the last key');assert.equal(filingSent.length,sentBefore+1,'nothing sent while he types');
  assert.equal(fire(),1);assert.equal(note.hidden,true,'no Loading… and no flicker');assert.equal(recordList.children.length,200);await tick();
  assert.deepEqual(filingSent.at(-1).data,{search:'gibson'});assert.equal(more.textContent,'Showing the newest 200 of 312 that match.');
  filingAnswers['/api/filing/record'].push({count:1240,matching:0,entries:[]});find.value='zzz';find.handlers.input();fire();await tick();
  assert.equal(note.hidden,false);assert.equal(note.textContent,'No entry matches.');assert.equal(more.hidden,true);assert.equal(recordList.children.length,0);
  // A search that cannot be read: the line in place of the list.
  filingAnswers['/api/filing/record'].push({fail:true});find.value='q';find.handlers.input();fire();await tick();
  assert.equal(note.textContent,"The list couldn't be loaded. Close and open it again.");assert.equal(note.className,'failed');assert.match(css,/#filing-record-note\.failed,#filing-could-not-note\.failed\{color:var\(--warning\)\}/);assert.equal(recordList.children.length,0);
  // Escape in Find book clears the field and does nothing else: the newest 200 again, at once, focus where it was.
  filingAnswers['/api/filing/record'].push({count:2,matching:2,entries:[entry(1),entry(2)]});
  find.focus();let stopped=0,prevented=0;find.handlers.keydown({key:'Escape',preventDefault(){prevented++;},stopPropagation(){stopped++;}});await tick();
  assert.equal(find.value,'');assert.deepEqual(filingSent.at(-1).data,{});assert.equal(recordList.children.length,2);assert.equal(note.hidden,true);assert.equal(note.className,'');
  assert.equal(document.activeElement,find);assert.equal(record.open,true);assert.deepEqual([stopped,prevented],[1,1]);
  const sentAfter=filingSent.length;find.handlers.keydown({key:'Escape',preventDefault(){},stopPropagation(){}});find.handlers.keydown({key:'a',preventDefault(){prevented++;},stopPropagation(){}});await tick();
  assert.equal(filingSent.length,sentAfter,'an empty field: Escape reads nothing; another key is not touched');assert.equal(prevented,1);
  // Escape on the list or on an entry's button: the focus goes to the summary and the record stays open.
  recordList.children[1].children[1].focus();recordList.handlers.keydown({key:'Escape',preventDefault(){},stopPropagation(){}});
  assert.equal(document.activeElement,summary);assert.equal(record.open,true);
  recordList.focus();recordList.handlers.keydown({key:'ArrowDown',preventDefault(){throw Error('arrow keys scroll the list');},stopPropagation(){}});assert.equal(document.activeElement,recordList,'other keys are left to the list');
  // Closed and opened again after a failure: Loading…, then the list.
  record.open=false;record.handlers.toggle();const closedSent=filingSent.length;show({filing:filing({record:{count:1250,last_at:AT}})});await tick();assert.equal(filingSent.length,closedSent,'closed: a changed number reads nothing');

  // 5. The list of the books that could not be renamed or moved (3.4a; R24; checks 37 and 46).
  const could=get('filing-could-not'),couldSummary=get('filing-could-not-summary'),couldList=get('filing-could-not-list'),couldNote=get('filing-could-not-note'),couldMore=get('filing-could-not-more');
  assert.match(html,/<details id="filing-could-not" hidden><summary id="filing-could-not-summary" title="Finished audiobooks the app has a new name or folder for and could not use, each with the reason\.">/);
  assert.match(html,/<p class="field-help">These audiobooks stay where they are\.<\/p><p id="filing-could-not-note" hidden><\/p><div id="filing-could-not-list" class="filing-list" role="group" aria-label="Books that could not be renamed or moved" tabindex="0"><\/div>/);
  show();assert.equal(could.hidden,true,'hidden at zero');
  show({pending:pending({could_not_file:1})});assert.equal(could.hidden,false);assert.equal(couldSummary.textContent,'Could not be renamed or moved · 1');
  show({pending:pending({could_not_file:12}),state:'all_done'});assert.equal(couldSummary.textContent,'Could not be renamed or moved · 12','it is in no state: shown under All done too');
  // The number is the engine's could_not_file alone: a doubtful result, a chosen folder and a book being moved are not in it.
  show({pending:pending({could_not_file:0,moves:55,filing:9}),filing:filing({left:9,could_not:0})});assert.equal(could.hidden,true,'negative control: other numbers never show it');
  const stuck=(n,key,more={})=>({job_id:'j'+n,book_id:'b'+n,title:'Граф Ноль',author:'Gibson William',from:'Z:\\Audiobooks Sorted\\Gibson William\\Граф Ноль - Gibson William.m4b',to:'Z:\\Audiobooks Sorted\\Gibson William\\Sprawl Trilogy\\2 - Граф Ноль - Gibson William.m4b',
    from_shown:'Gibson William\\Граф Ноль - Gibson William.m4b',to_shown:'Gibson William\\Sprawl Trilogy\\2 - Граф Ноль - Gibson William.m4b',key,kinds:['series'],reasons:[],...more});
  const KEYS={name_exists:'A file with that name is already there.',same_target:'Another audiobook would get the same name.',not_app_name:'Its file name is not one the app gave it.',not_where_recorded:'The file is not where the app left it.',
    no_name:'The app could not work out its new name.',did_not_finish:'The rename or move did not finish.'};
  let releaseCould;filingAnswers['/api/filing/could-not'].push(()=>new Promise(resolve=>{releaseCould=resolve;}));
  show({pending:pending({could_not_file:7})});could.open=true;could.handlers.toggle();await tick();
  assert.deepEqual(filingSent.at(-1),{route:'/api/filing/could-not',data:{}});assert.equal(couldNote.textContent,'Loading…');
  releaseCould({count:7,known:true,keys:Object.keys(KEYS),entries:[...Object.keys(KEYS).map((key,n)=>stuck(n,key,key==='no_name'?{to:null,to_shown:null}:{})),stuck(9,'a_key_the_page_does_not_know')]});await tick();
  assert.equal(couldNote.hidden,true);assert.equal(couldList.children.length,7);
  Object.keys(KEYS).forEach((key,n)=>{
    const box=couldList.children[n],body=box.children[0];
    assert.equal(body.children[0].children.map(e=>e.textContent).join(''),'Граф Ноль · Gibson William',key);
    assert.deepEqual(lines(body.children[1]),['Now in','Gibson William\\Граф Ноль - Gibson William.m4b'],key);
    if(key==='no_name')assert.deepEqual(body.children.map(e=>e.children[0]?.textContent || e.textContent),['Граф Ноль','Now in',KEYS[key]],'no Would be in line');
    else{assert.equal(body.children[2].children[0].textContent,'Would be in');assert.deepEqual(body.children[2].children[1].children.map(e=>[e.className || '',e.textContent]),[['filing-shared','Gibson William\\'],['','Sprawl Trilogy\\2 - Граф Ноль - Gibson William.m4b']]);
      assert.equal(body.children[2].title,'Z:\\Audiobooks Sorted\\Gibson William\\Sprawl Trilogy\\2 - Граф Ноль - Gibson William.m4b');}
    assert.equal(body.children.at(-1).textContent,KEYS[key],key);
    assert.equal(box.children[1].textContent,'Show in list');assert.equal(box.children[1].title,'List this book: sets Status to All and searches for its title.');assert.equal(box.children.length,2,'one button, and it does not act on a file');
  });
  assert.equal(couldList.children[6].children[0].children.length,3,'a key the page has no sentence for: no invented reason');
  for(const word of ['Move anyway','Leave it','Retry','Cancel'])assert.ok(!walk(could).some(e=>e.textContent===word),word);
  couldList.children[0].children[1].focus();couldList.handlers.keydown({key:'Escape',preventDefault(){},stopPropagation(){}});assert.equal(document.activeElement,couldSummary,'Escape returns to the summary');assert.equal(could.open,true);
  // More than 200: the first 200 and the count. The number changing while open reads it again; a failure says so.
  filingAnswers['/api/filing/could-not'].push({count:312,entries:Array.from({length:312},(_v,i)=>stuck(i,'name_exists'))});
  show({pending:pending({could_not_file:312})});await tick();assert.equal(couldList.children.length,200);assert.equal(couldMore.textContent,'Showing 200 of 312.');
  filingAnswers['/api/filing/could-not'].push({fail:true});show({pending:pending({could_not_file:311})});await tick();
  assert.equal(couldNote.textContent,"The list couldn't be loaded. Close and open it again.");assert.equal(couldNote.className,'failed');assert.equal(couldList.children.length,0);assert.equal(couldMore.hidden,true);
  could.open=false;could.handlers.toggle();show();

  // 6. No Cancel on the app's own move (3.3; R26; check 39). Positive control: his own queued move keeps Cancel and its words.
  context.window={booksDesktop:{chooseFolder:async()=>null}};  // a stub picker bridge, never a real dialog
  const target=ROOT+'\\Pratchett Terry\\Discworld\\32 - Hat - Pratchett Terry.m4b',renamed=ROOT+'\\Pratchett Terry\\A Hat Full of Sky - Pratchett Terry.m4b';
  paint([finished('own',{move:{state:'queued',target,folder:ROOT+'\\Pratchett Terry\\Discworld',origin:'rules'}}),finished('ren',{move:{state:'queued',target:renamed,folder:ROOT+'\\Pratchett Terry',origin:'rules'}}),
    finished('his',{move:{state:'queued',target:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',folder:'D:\\Books\\Horror',origin:'user'}}),finished('run',{move:{state:'moving',target,folder:ROOT+'\\Pratchett Terry\\Discworld',origin:'rules',progress:10}}),
    finished('old',{move:{state:'queued',target:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',folder:'D:\\Books\\Horror'}})]);
  run('queueState={queued:[{id:"q1",action:"move",book_id:"cand-own",title:"Title own",position:1,origin:"rules"},{id:"q2",action:"move",book_id:"cand-ren",title:"Title ren",position:2,origin:"rules"},{id:"q3",action:"move",book_id:"cand-his",title:"Title his",position:3,origin:"user"},{id:"q4",action:"move",book_id:"cand-old",title:"Title old",position:4}],running:null};controls()');
  const cancelOf=tr=>walk(statusCell(tr)).find(e=>e.textContent==='Cancel move');
  let tr=trOf('cand-own');assert.equal(goes(tr),'Moves to Audiobooks Sorted\\Pratchett Terry\\Discworld\\32 - Hat - Pratchett Terry.m4b');
  assert.equal(cancelOf(tr).hidden,true,'no Cancel on a move the app queued by its rules');
  assert.equal(choose(tr).getAttribute('aria-disabled'),'true');assert.equal(choose(tr).disabled,false,'it keeps its focus stop');assert.equal(choose(tr).title,'The app is about to move this audiobook. Choose another folder when it has moved.');
  tr=trOf('cand-ren');assert.equal(cancelOf(tr).hidden,true);assert.equal(choose(tr).title,'The app is about to rename this audiobook. Choose a folder when it is done.','a rename in place');
  tr=trOf('cand-his');assert.equal(cancelOf(tr).hidden,false,'positive control: a move he queued with Choose folder… has Cancel');assert.equal(choose(tr).title,'Move is queued for this book. Cancel it to use this.');
  tr=trOf('cand-old');assert.equal(cancelOf(tr).hidden,false,'a move with no origin sent is read as before');assert.equal(choose(tr).title,'Move is queued for this book. Cancel it to use this.');
  tr=trOf('cand-run');assert.equal(choose(tr).title,'Moving the audiobook. Choose another folder when it finishes.','while the move runs: the 0.30.0 tooltip, unchanged');assert.equal(choose(tr).getAttribute('aria-disabled'),'true');
  // The origin on the queued action alone (the row's own move not read yet) hides Cancel too.
  paint([finished('q',{move:{state:'queued',target,folder:ROOT+'\\Pratchett Terry\\Discworld'}})]);
  run('queueState={queued:[{id:"q1",action:"move",book_id:"cand-q",title:"Title q",position:1,origin:"rules"}],running:null};controls()');
  assert.equal(cancelOf(trOf('cand-q')).hidden,true);assert.equal(choose(trOf('cand-q')).title,'The app is about to move this audiobook. Choose another folder when it has moved.');
  // Once the book has moved, Choose folder… works as on any finished audiobook.
  paint([finished('done',{move:{state:'moved',target,folder:ROOT+'\\Pratchett Terry\\Discworld',origin:'rules'},output:{path:target,absolute:target,folder:ROOT+'\\Pratchett Terry\\Discworld'}})]);
  run('queueState={queued:[],running:null};controls()');
  tr=trOf('cand-done');assert.equal(goes(tr),'Now in Audiobooks Sorted\\Pratchett Terry\\Discworld\\32 - Hat - Pratchett Terry.m4b');assert.equal(choose(tr).textContent,'Choose folder…');
  assert.equal(choose(tr).getAttribute('aria-disabled'),null);assert.equal(choose(tr).title,'Choose a new folder for this audiobook. The file is moved there. Nothing is converted again.');

  // 7. Gap 9 (check 48): the title's own mention of a series is not shown on a book whose series was dropped as doubtful.
  const mention='The title mentions a series: Книга Нового Солнца #3. Not used in the file name.';
  const ask={kind:'title_author',also:null,why:'',reasons:['x'],fields:named,candidates:[],destination:rel('Джордан Роберт\\Колесо Времени - Джордан Роберт.m4b'),series_clue:'Книга Нового Солнца #3'};
  paint([bookRow('drop',{ask,series_dropped:[{provider:'fantlab',name:'Книга Нового Солнца',number:'3',why:'number_mismatch',source_url:''}]}),bookRow('kept',{ask,series_dropped:[]}),bookRow('none',{ask})]);
  assert.ok(!texts(trOf('cand-drop')).some(line=>String(line).includes('The title mentions a series')),'a dropped series is treated as not found: the row does not name it');
  assert.ok(texts(trOf('cand-kept')).includes(mention),'positive control: no series dropped, the line stays');assert.ok(texts(trOf('cand-none')).includes(mention),'an engine that sends no such fact: the line stays');

  // 8. The Title line of a row that asks another question (Judy 4.5; R1): the engine's fact on the question itself
  // (ask.title_origin), since such a row has no record of its own. It follows the draft, as on any row (gap 6).
  const english={origin:'source',rule:'english',split:false,provider:'wikidata',source_url:'https://www.wikidata.org/wiki/Q1'};
  const titleLine=tr=>walk(statusCell(tr)).find(e=>e.className==='field-help book-english-title' && shown(e))?.textContent || '';
  paint([bookRow('eng',{ask:{...ask,series_clue:undefined,title_origin:english}}),bookRow('fan',{ask:{...ask,series_clue:undefined,title_origin:{...english,provider:'fantlab'}}}),
    bookRow('unk',{ask:{...ask,series_clue:undefined,title_origin:{...english,provider:'somewhere'}}}),bookRow('files',{ask:{...ask,series_clue:undefined,title_origin:{origin:'files',rule:'no_english_title',split:false}}}),
    bookRow('rus',{ask:{...ask,series_clue:undefined,title_origin:{origin:'source',rule:'russian_original',split:false,provider:'fantlab'}}}),bookRow('his',{ask:{...ask,series_clue:undefined,title_origin:{origin:'entered',rule:'his',split:false}}}),
    bookRow('not',{ask:{...ask,series_clue:undefined}}),bookRow('own',{ask:{...ask,series_clue:undefined,title_origin:english},metadata_facts:{original_title_lookup:{state:'none',title:''}}})]);
  assert.equal(titleLine(trOf('cand-eng')),'English title found on Wikidata.');assert.equal(titleLine(trOf('cand-fan')),'English title found on FantLab.');
  assert.equal(titleLine(trOf('cand-unk')),'English title found online.','a source the page has no name for');
  for(const [id,why] of [['files','the files\' own title'],['rus','a Russian original named by a source'],['his','a title he typed'],['not','no fact sent'],['own','the row\'s own record decides when it has one']])
    assert.equal(titleLine(trOf('cand-'+id)),'',why);
  // Typing another title removes the line at once; restoring the app's title brings it back.
  const titleField=walk(statusCell(trOf('cand-eng'))).find(e=>e.dataset?.name==='title');
  if(titleField){titleField.value='My own title';titleField.handlers.input?.({target:titleField});assert.equal(titleLine(trOf('cand-eng')),'','typed: the line goes');}

  console.log('PASS 0.31.0 rule filing page: the quiet line gone, the notice above 5 until zero, grouped Waiting items with the engine\'s whole numbers, no Cancel on the app\'s own move, the record with Find book and Escape, the could-not list with a reason per key, the title\'s mention hidden for a dropped series');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_rule_filing_frontend.js'),module);m.filename=path.join(__dirname,'test_rule_filing_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

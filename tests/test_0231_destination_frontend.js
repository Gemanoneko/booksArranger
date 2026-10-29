'use strict';
// Judy's 0.23.1 Part B (Docs/BooksArranger_0.23.1_UX_2026-10-29.md sections 13-19; rulings 69, 70 and 71h-k; Futaba's checks
// 15-22 that run headless): the destination block on every row with a destination or a converted file, Choose folder…
// through a stub picker bridge (never a real dialog), the chosen folder's lines, Use computed folder and the finished-row
// confirmation, a move's states and failure copy, "Now in" on finished rows and "Open book folder". Real frontend on the
// Retry test's DOM/transport doubles. No server, no library, no window.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const ROOT='Z:\\Audiobooks Sorted',HAT=ROOT+'\\Pratchett Terry\\Hat - Pratchett Terry.m4b';
function bookRow(name,extra={}){
  return {id:'cand-'+name,path:'cand-'+name,kind:'candidate',library:'Audiobooks',revision:2,scope:'fixture scope',preview:{reason:'fixture',path:''},metadata:{tags:{},notes:[]},grouping:'Source clues',title_evidence:[],
    title_clue:'Title '+name,conflicts:[],coverage:'',companions:[],artists:['Artist '+name],members:[{path:'Z:\\Audiobooks\\'+name+'\\01.mp3'}],track_order:[],included:[],review:{},review_context:{},status:'Held',
    automatic:{state:'Held',reasons:['x']},creation:{status:'Held',can_create:false,reasons:[]},...extra};
}
const named={title:{proposal:'Колесо Времени',basis:'tag'},author:{proposal:'Джордан Роберт',basis:'tag'}};
function waiting(name,destination,extra={}){return bookRow(name,{ask:{kind:'title_author',also:null,why:'',reasons:['x'],fields:named,candidates:[],destination},...extra});}
const rel=p=>({path:p,absolute:ROOT+'\\'+p,taken:false,reason:''});
function finished(name,extra={}){return bookRow(name,{status:'Audiobook created',audiobook_ready:true,source_state:'present',output:{path:HAT,absolute:HAT,folder:ROOT+'\\Pratchett Terry'},
  creation:{status:'Audiobook created',can_create:false,reasons:[],job:{job_id:'job-'+name,state:'Audiobook created',reason:''}},automatic:null,...extra});}
const chosen={folder:'D:\\Books\\Horror',computed_folder:ROOT+'\\Без автора',computed_path:ROOT+'\\Без автора\\X.m4b',outside_sorted:true};
backend={...backend,audiobook_output_root:ROOT,audiobook_jobs:{...backend.audiobook_jobs,attention_counts:{},todo_still_checking:0}};
let destAnswer=null;const sent=[],opened=[];const baseFetch=context.fetch;
context.fetch=async(route,options)=>{
  const data=options?.body?JSON.parse(options.body):undefined;
  if(route==='/api/candidate/destination'){calls.push({route,options});sent.push(data);return destAnswer?destAnswer(data):{ok:true,status:200,json:async()=>({outcome:'unchanged'})};}
  if(route==='/api/open-folder'){calls.push({route,options});opened.push(data);return {ok:true,status:200,json:async()=>({opened:true})};}
  if(route==='/api/candidate/approve-preview'){calls.push({route,options});return {ok:true,status:200,json:async()=>({preview:{path:'x.m4b',taken:false}})};}
  return baseFetch(route,options);
};
const ok=body=>()=>({ok:true,status:200,json:async()=>body});
const trOf=id=>[...get('inventory').children].find(tr=>tr.dataset.path===id);
const statusCell=tr=>tr.children[4],buttonsOf=tr=>[...tr.children[5].children[0].children];
function walk(element,found=[]){for(const child of element.children || []){found.push(child);walk(child,found);}return found;}
const shown=element=>{for(let e=element;e;e=e.parentElement)if(e.hidden)return false;return true;};
const texts=element=>walk(element).filter(shown).map(e=>e.textContent).filter(Boolean);
const destBlock=tr=>walk(statusCell(tr)).find(e=>e.className==='goes-to-block');
const goes=tr=>{const line=destBlock(tr)?.children[0];return line && shown(line)?line.children.map(c=>c.textContent).join(' '):'';};
const byText=(tr,text)=>walk(tr).filter(e=>e.textContent===text && e.type==='button');
const choose=tr=>byText(statusCell(tr),'Choose folder…')[0] || walk(statusCell(tr)).find(e=>e.getAttribute?.('aria-label')?.startsWith('Choose folder: '));
const reset=tr=>walk(statusCell(tr)).find(e=>e.getAttribute?.('aria-label')?.startsWith('Use computed folder: '));
const stateLine=tr=>walk(statusCell(tr)).find(e=>e.className==='field-help attention-hint dest-state');
const chosenLine=tr=>walk(statusCell(tr)).find(e=>e.className==='field-help dest-chosen');
function paint(list){context.fixture=list;run('rows=fixture.map(row=>({...row}));totalRows=rows.length;renderRows(true);controls()');}
const press=async button=>{button.focus();return button.handlers.click({stopPropagation(){}});};
(async()=>{
  run('state='+JSON.stringify(backend)+';view="candidates";filters.candidates="all";viewControls()');
  // Check 15: Choose folder… lives in the destination block, never in the Actions column (six at most there); a row with
  // neither a destination nor a converted file has none.
  const kinds=[waiting('w',rel('Без автора\\X.m4b')),waiting('nd',{path:'',absolute:'',taken:false,reason:'Type a title first.'}),finished('f'),bookRow('pend',{preview:{path:ROOT+'\\A\\B.m4b',reason:''}}),
    bookRow('gone',{members:[{path:'Z:\\Audiobooks\\gone\\01.mp3',missing:true}],ask:{kind:'files_missing',also:null,why:'',reasons:['Files missing'],fields:{},candidates:[],missing:{folders:['Z:\\Audiobooks\\gone'],files:['Z:\\Audiobooks\\gone\\01.mp3'],present:0,total:1}}}),
    bookRow('stopped',{status:'Output needs attention',creation:{status:'Output needs attention',can_create:false,reasons:[],job:{job_id:'job-s',state:'Output needs attention',stage:'queued',reason:'x',retry:{allowed:true,reason:''},destination:rel('A\\S.m4b')}}})];
  paint(kinds);
  for(const row of kinds){const tr=trOf(row.id),actions=buttonsOf(tr).filter(b=>b.type==='button' && !b.hidden);
    assert.ok(actions.length<=6,row.id);assert.ok(!actions.some(b=>/Choose folder/.test(b.textContent)),'not in the Actions column: '+row.id);
    const count=walk(statusCell(tr)).filter(e=>e.type==='button' && e.getAttribute?.('aria-label')?.startsWith('Choose folder: ')).length;assert.equal(count,row.id==='cand-gone'?0:1,row.id);}
  assert.equal(goes(trOf('cand-w')),'Goes to Audiobooks Sorted\\Без автора\\X.m4b');
  assert.equal(goes(trOf('cand-nd')),'Goes to Not decided yet.','a folder can be chosen before the title is');
  assert.equal(goes(trOf('cand-f')),'Now in Audiobooks Sorted\\Pratchett Terry\\Hat - Pratchett Terry.m4b','check 20: the converted file, in Sorted');
  assert.equal(destBlock(trOf('cand-f')).children[0].title,HAT);
  assert.equal(goes(trOf('cand-pend')),'Goes to Audiobooks Sorted\\A\\B.m4b','the planner preview reads as every Goes to line');
  assert.equal(goes(trOf('cand-stopped')),'Goes to Audiobooks Sorted\\A\\S.m4b','a Stopped row: its job destination');
  // Check 16: no bridge (the browser launch): inert with its tooltip; the page never offers a path box.
  let tr=trOf('cand-w'),button=choose(tr);
  assert.equal(button.getAttribute('aria-disabled'),'true');assert.equal(button.title,'Choosing a folder works in the desktop app.');assert.equal(button.getAttribute('aria-label'),'Choose folder: Title w');
  await press(button);assert.equal(sent.length,0);
  assert.ok(!walk(destBlock(tr)).some(e=>e.tagName==='input' || e.type==='text'),'no text box for a path');
  // The stub bridge: title, confirm label and start folder; cancel changes nothing and focus returns.
  const picks=[];let pickAnswer=null,release=null;
  context.window={booksDesktop:{chooseFolder:async options=>{picks.push(options);if(pickAnswer==='hold')return new Promise(resolve=>{release=resolve;});return pickAnswer;}}};
  run('controls()');assert.equal(button.getAttribute('aria-disabled'),null);
  assert.equal(button.title,'Choose the folder this book is filed in. Your choice replaces the folder the app computed. The file goes straight into it.');
  await press(button);
  assert.deepEqual(JSON.parse(JSON.stringify(picks.at(-1))),{title:'Choose a folder for Колесо Времени',defaultPath:ROOT+'\\Без автора',buttonLabel:'Select folder'});
  assert.equal(sent.length,0,'cancel sends nothing');assert.equal(button.textContent,'Choose folder…');assert.equal(document.activeElement,button);
  pickAnswer='hold';const pending=press(button);
  assert.equal(button.textContent,'Choosing…');assert.equal(button.getAttribute('aria-disabled'),'true');assert.equal(button.title,'Waiting for the folder picker.');
  release(null);await pending;assert.equal(button.textContent,'Choose folder…');
  pickAnswer=null;await press(choose(trOf('cand-f')));assert.equal(picks.at(-1).buttonLabel,'Move here');
  assert.equal(choose(trOf('cand-f')).title,'Choose a new folder for this audiobook. The file is moved there. Nothing is converted again.');
  // Check 22: choosing on a waiting row saves the folder only: no Approve request, the status stays; Approve files it there.
  pickAnswer='D:\\Books\\Horror';
  destAnswer=ok({outcome:'saved',destination_override:chosen,preview:{path:'D:\\Books\\Horror\\X.m4b',absolute:'D:\\Books\\Horror\\X.m4b',taken:false}});
  const status=statusCell(tr).children[0].textContent;await press(button);
  assert.deepEqual(sent.at(-1),{library:'Audiobooks',id:'cand-w',revision:2,folder:'D:\\Books\\Horror'});
  assert.equal(calls.some(c=>c.route==='/api/candidate/approve'),false,'choosing never approves (ruling 71j)');assert.equal(statusCell(tr).children[0].textContent,status);
  assert.equal(stateLine(tr).textContent,'Folder saved. Approve converts the book and files it there.');
  assert.equal(goes(tr),'Goes to D:\\Books\\Horror\\X.m4b','the chosen folder in full plus the computed name');
  assert.equal(chosenLine(tr).textContent,'Folder chosen by you. The app would use Audiobooks Sorted\\Без автора\\');
  assert.equal(reset(tr).hidden,false);assert.equal(reset(tr).title,'Stop using your folder. The book goes to the folder the app computes.');
  assert.ok(!texts(tr).some(t=>/Originals stay/.test(t)),'ruling 71h: no "Originals stay" line');
  assert.equal(buttonsOf(tr)[0].title,'Approve with the values shown: convert if needed, rename, move to the folder you chose. Ctrl+Enter in a field does the same.');
  // A row without Approve: the saved line names the path.
  destAnswer=ok({outcome:'saved',destination_override:{...chosen,folder:'D:\\Books'},preview:{path:'D:\\Books\\B.m4b',absolute:'D:\\Books\\B.m4b'}});pickAnswer='D:\\Books';
  await press(choose(trOf('cand-pend')));assert.equal(stateLine(trOf('cand-pend')).textContent,'Folder saved. This book goes to D:\\Books\\B.m4b.');
  // Check 17: with a chosen folder painted from the engine; a name taken there; without one: neither line nor button.
  paint([waiting('c',{path:'D:\\Books\\Horror\\X.m4b',absolute:'D:\\Books\\Horror\\X.m4b',taken:false,reason:''},{destination_override:chosen}),
    waiting('t',{path:'D:\\Books\\Horror\\X.m4b',absolute:'D:\\Books\\Horror\\X.m4b',taken:true,reason:''},{destination_override:chosen}),waiting('plain',rel('A\\X.m4b'))]);
  assert.equal(goes(trOf('cand-c')),'Goes to D:\\Books\\Horror\\X.m4b');assert.equal(chosenLine(trOf('cand-c')).textContent,'Folder chosen by you. The app would use Audiobooks Sorted\\Без автора\\');
  assert.equal(goes(trOf('cand-t')),'Already there D:\\Books\\Horror\\X.m4b');assert.equal(buttonsOf(trOf('cand-t'))[0].getAttribute('aria-disabled'),'true');
  assert.equal(buttonsOf(trOf('cand-t'))[0].title,'That name is already in the folder you chose. Change the title, the author or the folder.');
  assert.equal(chosenLine(trOf('cand-plain')).hidden,true);assert.equal(reset(trOf('cand-plain')).hidden,true);
  // Check 18, not finished: one press clears it, no confirmation; focus to Choose folder… (the pressed button goes).
  destAnswer=ok({outcome:'cleared',destination_override:null,preview:{path:'Без автора\\X.m4b',absolute:ROOT+'\\Без автора\\X.m4b'}});
  tr=trOf('cand-c');await press(reset(tr));
  assert.equal(sent.at(-1).folder,null);assert.equal(stateLine(tr).textContent,'Folder reset. This book goes to Audiobooks Sorted\\Без автора\\X.m4b.');
  assert.equal(reset(tr).hidden,true);assert.equal(chosenLine(tr).hidden,true);assert.equal(document.activeElement,choose(tr));
  // Check 18, finished: the inline confirmation, focus on Keep it here, Esc keeps; Move book queues the move.
  paint([finished('back',{destination_override:{...chosen,computed_folder:ROOT+'\\Pratchett Terry',computed_path:HAT},output:{path:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',absolute:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',folder:'D:\\Books\\Horror'}})]);
  tr=trOf('cand-back');assert.equal(goes(tr),'Now in D:\\Books\\Horror\\Hat - Pratchett Terry.m4b');
  assert.equal(reset(tr).title,'Move the audiobook back to the folder the app computes. Nothing is converted again. You confirm first.');
  const before=sent.length;await press(reset(tr));
  const confirm=walk(statusCell(tr)).find(e=>e.className==='dest-confirm');assert.equal(confirm.hidden,false);
  assert.equal(walk(statusCell(tr)).find(e=>e.className==='row-actions dest-controls').hidden,true,'the two buttons give way, nothing overlays');
  assert.equal(confirm.children[0].textContent,'Move the audiobook back to Audiobooks Sorted\\Pratchett Terry\\Hat - Pratchett Terry.m4b? Nothing is converted again.');
  const keep=byText(confirm,'Keep it here')[0],move=byText(confirm,'Move book')[0];
  assert.equal(document.activeElement,keep);assert.equal(keep.getAttribute('aria-label'),'Keep it here: Title back');assert.equal(move.title,'Move the audiobook to the folder shown now. Nothing is converted again.');
  assert.equal(keep.title,'Leave the audiobook where it is and keep your folder.');
  keep.handlers.keydown({key:'Escape',stopPropagation(){},preventDefault(){}});assert.equal(confirm.hidden,true);assert.equal(sent.length,before,'Esc keeps: nothing sent');
  await press(reset(tr));destAnswer=ok({outcome:'move_queued',move:{state:'queued',target:HAT,folder:ROOT+'\\Pratchett Terry'}});
  await press(byText(walk(statusCell(tr)).find(e=>e.className==='dest-confirm'),'Move book')[0]);
  assert.equal(sent.at(-1).folder,null);assert.equal(goes(tr),'Moves to Audiobooks Sorted\\Pratchett Terry\\Hat - Pratchett Terry.m4b');
  assert.equal(stateLine(tr).textContent,'Move queued. It runs when the app is free.');assert.equal(choose(tr).textContent,'Queued');assert.equal(choose(tr).getAttribute('aria-disabled'),'true');
  assert.equal(calls.some(c=>c.route==='/api/candidate/approve'),false,'a move never converts or approves');
  // Check 19: each move state in order, the Cancel of a queued move, every failure cause; a failure leaves Now in unchanged.
  const moving={state:'moving',target:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',folder:'D:\\Books\\Horror',progress:41};
  paint([finished('mq',{move:{state:'queued',target:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',folder:'D:\\Books\\Horror'}}),finished('mm',{move:moving}),
    finished('md',{destination_override:chosen,move:{state:'moved',target:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',folder:'D:\\Books\\Horror'},output:{path:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',absolute:'D:\\Books\\Horror\\Hat - Pratchett Terry.m4b',folder:'D:\\Books\\Horror'}})]);
  run('queueState={queued:[{id:"q1",action:"move",book_id:"cand-mq",title:"Title mq",position:1}],running:null};controls()');
  tr=trOf('cand-mq');assert.equal(goes(tr),'Moves to D:\\Books\\Horror\\Hat - Pratchett Terry.m4b');assert.equal(choose(tr).title,'Move is queued for this book. Cancel it to use this.');
  const cancel=walk(statusCell(tr)).find(e=>e.textContent==='Cancel move');assert.ok(cancel && !cancel.hidden,'the queued-action Cancel');assert.equal(cancel.title,'Take this move out of the queue. Nothing was started.');
  tr=trOf('cand-mm');assert.equal(goes(tr),'Moving to D:\\Books\\Horror\\Hat - Pratchett Terry.m4b');assert.equal(choose(tr).textContent,'Moving…');
  assert.equal(choose(tr).title,'Moving the audiobook. Choose another folder when it finishes.');assert.equal(stateLine(tr).textContent,'Moving the audiobook… · 41%');
  assert.ok(!walk(statusCell(tr)).some(e=>e.textContent==='Cancel move' && !e.hidden),'no Cancel while moving');
  run('ladderClock=Date.now()+7000;updateDestinations();ladderClock=null');assert.match(stateLine(tr).textContent,/^Moving the audiobook… 0:0[67] · 41% The app is busy with background work, so this takes longer\.$/);
  tr=trOf('cand-md');assert.equal(goes(tr),'Now in D:\\Books\\Horror\\Hat - Pratchett Terry.m4b');assert.equal(stateLine(tr).textContent,'Moved. The audiobook is now in D:\\Books\\Horror.');
  assert.equal(choose(tr).textContent,'Choose folder…');assert.equal(reset(tr).hidden,false);
  const SENTENCES={target_exists:'A file named Hat.m4b is already in D:\\Books\\Horror. Nothing was moved.',unavailable:"D:\\Books\\Horror isn't available. Connect the drive or choose another folder. Nothing was moved.",
    not_writable:"The app can't write to D:\\Books\\Horror. Choose another folder. Nothing was moved.",no_space:"There isn't enough free space on that drive. Nothing was moved.",
    in_use:'The audiobook is open in another program. Close it and try again. Nothing was moved.',source_missing:"The audiobook isn't where the app expects it. Nothing was moved.",
    unsafe:"That folder holds this book's original files. Choose another folder.",partial:"Moved to D:\\Books\\Horror. The old file in Z:\\Audiobooks Sorted\\Pratchett Terry couldn't be removed. Delete it yourself.",
    changed:'This book changed. Review its details and try again.',other:'Move was not accepted. Nothing was moved.'};
  for(const [cause,sentence] of Object.entries(SENTENCES)){
    paint([finished('x',{move:{state:'failed',cause,target:'D:\\Books\\Horror\\Hat.m4b',folder:'D:\\Books\\Horror',name:'Hat.m4b',old_folder:ROOT+'\\Pratchett Terry'}})]);tr=trOf('cand-x');
    assert.equal(stateLine(tr).textContent,sentence,cause);assert.equal(stateLine(tr).getAttribute('role'),'alert');assert.equal(goes(tr),'Now in Audiobooks Sorted\\Pratchett Terry\\Hat - Pratchett Terry.m4b',cause);
    assert.equal(choose(tr).textContent,'Choose folder…');assert.equal(choose(tr).getAttribute('aria-disabled'),null,'available again: '+cause);
  }
  // Control: a refused request after the picker leaves no row claiming it moved.
  paint([waiting('r',rel('Без автора\\X.m4b'))]);tr=trOf('cand-r');pickAnswer='D:\\Books\\Horror';
  destAnswer=()=>({ok:false,status:409,json:async()=>({cause:'target_exists',error:'Already there'})});await press(choose(tr));
  assert.equal(stateLine(tr).textContent,'A file named X.m4b is already in D:\\Books\\Horror. Nothing was moved.');assert.ok(!texts(tr).some(t=>/^Moved\./.test(t)));
  assert.equal(goes(tr),'Goes to Audiobooks Sorted\\Без автора\\X.m4b','nothing changed');
  // A queued move that the engine refused when it ran: its sentence on the row, announced once, acknowledged.
  run('syncQueue({queued_actions:[],queue_running:null,queue_outcomes:[{id:"o-move",action:"move",book_id:"cand-r",result:"refused",cause:"no_space",title:"Title r"}]})');
  assert.equal(stateLine(tr).textContent,"There isn't enough free space on that drive. Nothing was moved.");assert.equal(get('queue-announce').textContent,"Title r: There isn't enough free space on that drive. Nothing was moved.");
  assert.ok(calls.some(c=>c.route==='/api/queue/ack' && JSON.parse(c.options.body).ids[0]==='o-move'),'acknowledged');
  // Check 21: "Open book folder" on a finished row whose originals are gone opens the converted file's folder.
  paint([finished('bg',{source_state:'gone'}),finished('bp'),bookRow('ng',{source_state:'gone'})]);
  const face=tr=>buttonsOf(tr).find(b=>/^Open (source|book) folder$/.test(b.textContent));
  tr=trOf('cand-bg');assert.equal(face(tr).textContent,'Open book folder');assert.equal(face(tr).title,'The original files are gone. Open the folder that holds the converted audiobook.');
  assert.equal(face(tr).getAttribute('aria-label'),'Open book folder: Title bg');assert.equal(walk(statusCell(tr)).find(e=>e.className==='goes-to source-line').hidden,true,'"Now in" replaces the In line');
  await face(tr).handlers.click({stopPropagation(){}});assert.deepEqual(opened.at(-1),{library:'Audiobooks',view:'candidates',id:'cand-bg',folder_kind:'output'});
  assert.equal(face(trOf('cand-bp')).textContent,'Open source folder','originals present');assert.equal(face(trOf('cand-ng')).textContent,'Open source folder','not finished');
  console.log('PASS 0.23.1 destination: the block on every row, Choose folder… with the stub picker, the chosen folder lines, reset and its confirmation, move states and every failure, Now in, Open book folder');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_0231_destination_frontend.js'),module);m.filename=path.join(__dirname,'test_0231_destination_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

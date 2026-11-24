'use strict';
// 0.31.0 ruling R27 (Sergei 2026-11-23), the page (Judy's Docs/BooksArranger_0.31.0_UX.md section 3.3, specced in the fourth
// round and built now that the engine sends the job): a finished audiobook whose English title or author's name is written
// into its file has the running row "Renaming finished audiobook: <book>", a Waiting item "Rename finished audiobook: <book>"
// with its blocker sentence, and above 5 one grouped item "Renaming finished audiobooks: N books" with the engine's whole
// number. The real renderJobs on the look-ups test's DOM doubles: no server, no library, no window, no file touched.
const fs=require('fs'),path=require('path');
const lookups=fs.readFileSync(path.join(__dirname,'test_lookups_frontend.js'),'utf8');
let harness=lookups.slice(0,lookups.indexOf('// 1. The running rows'));
harness+=String.raw`
const filing=(more={})=>({known:true,at:1,paused:false,drive_away:false,left:0,writes_waiting:0,writes_running:0,moves_waiting:0,moves_running:0,renames_waiting:0,renames_running:0,
  next_write:null,next_move:null,next_rename:null,could_not:0,record:{count:0,last_at:null},waiting_for_lookup:0,on_hold:0,settling:0,tries:{limit:3,spacing_seconds:3600},feed:2,...more});
const rename=(extra={})=>({id:'rename',kind:'rename',subject:'Тёмный лес',step:'updating',state:'running',started:NOW-60000,background:false,...extra});
const item=(id,extra={})=>({id:'rename_write:'+id,kind:'rename_write',subject:'Book '+id,book_id:'b-'+id,job_id:id,blocker:{kind:'conversion',title:'Dune'},background:false,...extra});
const page=work=>show({state:'working',pending:{lookups:{series:0,details:0,all:0},filing:1},filing:filing(),...work});

// 1. The running row (3.3): label and subject, the step, the step's own text as its tooltip, a sliding bar (no amount sent).
let row=parts(page({rows:[rename()]})[0]);
assert.equal(row.label+row.subject,'Renaming finished audiobook: Тёмный лес');
assert.equal(row.step,'Writing the new names into the file and renaming it. Audio unchanged.');
assert.equal(row.tip,row.step,'its step\'s tooltip is the step\'s own text');
assert.equal(row.bar.hasAttribute('value'),false,'a sliding bar unless the engine sends an amount');
assert.equal(row.detail,'');
// Negative control: the series row's writing step keeps its own words; the rename row is not a look-up (no look-up tooltip).
row=parts(page({rows:[{...rename(),id:'series',kind:'series',done:3,total:9,unit:'books'}]})[0]);
assert.equal(row.label,'Finding series for finished audiobooks: ');assert.equal(row.step,'Writing the series into the file and renaming it. Audio unchanged.');
assert.equal(run("isLookup({kind:'rename'})"),false);assert.equal(run("workLabel({kind:'rename'})"),'Renaming finished audiobook');

// 2. A rename that waits for a job (3.3): its item and the blocker sentence; Show in list with the plain tooltip.
page({lookups_waiting:[item('r1')],filing:filing({left:1,renames_waiting:1,next_rename:{job_id:'r1',book_id:'b-r1',title:'Book r1',blocker:{kind:'conversion',title:'Dune'}}})});
let list=waits();
assert.deepEqual(list.map(entry=>entry.line1),['Rename finished audiobook: Book r1']);
assert.equal(list[0].line2,'It runs when Converting: Dune finishes.');
assert.equal(list[0].button.hidden,false);assert.equal(list[0].button.title,'List this book: sets Status to All and searches for its title.','never the variant that ends "Its row has Cancel."');
assert.equal(run('JSON.stringify(waitingItems.get("rename_write:r1").target)'),'{"id":"b-r1","title":"Book r1"}');

// 3. More than 5 waiting (3.3): one grouped item with the engine's whole count (it lists at most 100), the next book and
// what blocks it, in the place of the first; 5 or fewer: one item each.
const many=['r1','r2','r3'].map(id=>item(id));
page({lookups_waiting:many,filing:filing({left:92,renames_waiting:92,next_rename:{job_id:'r1',book_id:'b-r1',title:'Тёмный лес',blocker:{kind:'conversion',title:'Dune'}}})});
list=waits();
assert.deepEqual(list.map(entry=>entry.line1),['Renaming finished audiobooks: 92 books'],'one item, the engine\'s whole number');
assert.equal(list[0].line2,'Next: Тёмный лес. It runs when Converting: Dune finishes.');
assert.equal(list[0].button.title,'List this book: sets Status to All and searches for its title.');
assert.equal(run('JSON.stringify(waitingItems.get("filing_renames").target)'),'{"id":"b-r1","title":"Тёмный лес"}','Show in list is for the next book, by its title');
page({lookups_waiting:[],filing:filing({left:8,renames_waiting:8,next_rename:{job_id:'r9',book_id:'b-r9',title:'Задача трёх тел',blocker:null}})});
list=waits();assert.deepEqual(list.map(entry=>entry.line1),['Renaming finished audiobooks: 8 books']);assert.equal(list[0].line2,'Next: Задача трёх тел. They run one at a time.');
// The three groups side by side keep their own words.
page({lookups_waiting:[],filing:filing({left:30,writes_waiting:6,renames_waiting:7,moves_waiting:17,next_write:{title:'A',book_id:'b-a'},next_rename:{title:'B',book_id:'b-b'},next_move:{title:'C',book_id:'b-c'}})});
assert.deepEqual(waits().map(entry=>entry.line1),['Writing series into finished audiobooks: 6 books','Renaming finished audiobooks: 7 books','Moving finished audiobooks: 17 books']);
// Negative controls: 5 or fewer are each their own item; an engine that sends no renames number groups nothing.
page({lookups_waiting:many,filing:filing({left:5,renames_waiting:5,next_rename:{title:'Book r1',book_id:'b-r1'}})});
assert.deepEqual(waits().map(entry=>entry.line1),['Rename finished audiobook: Book r1','Rename finished audiobook: Book r2','Rename finished audiobook: Book r3']);
page({lookups_waiting:many,filing:filing({left:9,renames_waiting:undefined})});
assert.deepEqual(waits().map(entry=>entry.line1).length,3);
page({lookups_waiting:[],filing:filing()});assert.deepEqual(waits(),[]);

// 4. Old words stay gone: the page no longer says the engine sends no rename of its own.
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
assert.ok(!source.includes('the engine sends no rename of its own'));
console.log('PASS 0.31.0 R27 page: the rename row with its step and tooltip, the rename item with its blocker, the grouped renames with the engine\'s number, the controls');
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_rename_write_frontend.js'),module);m.filename=path.join(__dirname,'test_rename_write_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

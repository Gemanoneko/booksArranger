'use strict';
// 0.31.3 (Judy's Docs/BooksArranger_LateWriteCleanup_UXSpec_2026-11-25.md; Sergei's rulings 2026-11-25): the books 0.31.2 left
// with their old file beside the updated one. During the clean-up one Running row "Removing old files" (section 2), a Waiting
// item while a library scan holds the books (3), and at its end two parts at the end of the status line for an hour (4).
// A kept book reads "The old file was not removed." in "Could not be renamed or moved" (4); an entry whose last try did not
// write the new names reads section 6's sentence. The real renderJobs on the look-ups test's DOM doubles: no server, no
// library, no window, no file touched. Each case has its control.
const fs=require('fs'),path=require('path');
const lookups=fs.readFileSync(path.join(__dirname,'test_lookups_frontend.js'),'utf8');
let harness=lookups.slice(0,lookups.indexOf('// 1. The running rows'));
harness+=String.raw`
const TIP='These books still have their old file beside the updated one. The app checks both files, then removes the old one.';
const late=(extra={})=>({id:'late_cleanup',kind:'late_cleanup',subject:'The Name of the Wind',step:'removing',done:42,total:115,unit:'books',kept:0,state:'running',started:NOW-60000,background:false,...extra});
const page=work=>show({state:'working',pending:{lookups:{series:0,details:0,all:0}},...work});

// 1. The row (2): label and the book in hand, the count, the step, the tooltip on the label, a determinate bar never at 100.
let row=parts(page({rows:[late()]})[0]);
assert.equal(row.label+row.subject,'Removing old files: The Name of the Wind');
assert.equal(row.detail,'42 of 115 books');
assert.equal(row.step,'Checking both files, then removing the old one.');
assert.equal(row.bar.value,Math.floor(42/115*100));
let label=get('jobs-rows').children[0].children[0].children[0].children[0];
assert.equal(label.title,TIP,'the tooltip is on the label');
assert.equal(run("workLabel({kind:'late_cleanup'})"),'Removing old files');assert.equal(run("isLookup({kind:'late_cleanup'})"),false,'main work, not a look-up');
// A kept book adds "· N kept"; none at 0 (the control); the count is never truncated or wrapped into the label.
assert.equal(parts(page({rows:[late({kept:1})]})[0]).detail,'42 of 115 books · 1 kept');
assert.equal(parts(page({rows:[late({kept:2,done:115,total:115})]})[0]).detail,'','at its last book the row is finishing (it leaves in the same update)');
assert.equal(parts(page({rows:[late({kept:3,done:1,total:1})]})[0]).bar.hasAttribute('value'),false);
assert.equal(parts(page({rows:[late({kept:2,done:7,total:12})]})[0]).detail,'7 of 12 books · 2 kept');
assert.equal(parts(page({rows:[late({kept:1200,done:1500,total:2000})]})[0]).detail,(1500).toLocaleString()+' of '+(2000).toLocaleString()+' books · '+(1200).toLocaleString()+' kept');
// Between two books: no subject, the row stays.
row=parts(page({rows:[late({subject:''})]})[0]);assert.equal(row.label+row.subject,'Removing old files');assert.equal(row.detail,'42 of 115 books');
// Control: another row's label has no tooltip.
page({rows:[{id:'series',kind:'series',subject:'Дюна',step:'updating',done:1,total:9,unit:'books',state:'running',started:NOW-60000,background:false}]});
assert.equal(get('jobs-rows').children[0].children[0].children[0].children[0].title,'','control: no other row has a label tooltip');
// The status line's first part is the row's own name (one running row).
page({rows:[late()]});assert.match(get('jobs-status-text').textContent,/^Removing old files: The Name of the Wind · /);

// 2. The time estimate (2, progress-rows spec 5): the book in hand changes with every book; the clean-up keeps its samples.
page({rows:[late({done:10,subject:'A'})]});
let view=run('activityRows.get("late_cleanup")');view.samples=[[NOW-20000,0.05],[NOW-10000,0.08]];
page({rows:[late({done:12,subject:'B'})]});
assert.equal(run('activityRows.get("late_cleanup").samples.length')>=2,true,'a new book keeps the run\'s samples');
const other=extra=>({id:'rename',kind:'rename',step:'updating',done:10,total:100,unit:'books',state:'running',started:NOW-60000,background:false,...extra});
page({rows:[other({subject:'A'})]});run('activityRows.get("rename").samples=[[Date.now()-20000,0.05],[Date.now()-10000,0.08]]');
page({rows:[other({subject:'B'})]});
assert.equal(run('activityRows.get("rename").samples.length')<=1,true,'control: a row whose subject is its job starts its samples again');

// 3. Waiting for a library scan (3): the books left, the row's tooltip, no Show in list.
page({rows:[],waiting:[{id:'late_cleanup',kind:'late_cleanup',count:73,blocker:{kind:'scan',cause:'scan'},background:false}]});
let list=waits();
assert.deepEqual(list.map(entry=>entry.line1),['Removing old files: 73 books']);
assert.equal(list[0].line2,'Waiting for the library scan to finish.');assert.equal(list[0].tip,TIP);assert.equal(list[0].button.hidden,true,'a count, not one book');
page({rows:[],waiting:[{id:'late_cleanup',kind:'late_cleanup',count:1,blocker:{kind:'scan',cause:'scan'},background:false}]});
assert.deepEqual(waits().map(entry=>entry.line1),['Removing old files: 1 book']);

// 4. The end (4): removed first, kept second, never merged, after "missing books removed"; byteText's size words; an hour.
const end=(late,removed)=>{context.fixture.late_cleanup=late;context.fixture.removed=removed;run('renderJobs()');return get('jobs-status-text').textContent;};
show({state:'all_done',pending:{lookups:{series:0,details:0,all:0}}});
const base=end(undefined,undefined);
assert.equal(end({removed:110,kept:5,freed_bytes:74*1024**3,last_age_ms:0}),base+' · 110 old files removed, 74 GB freed · 5 old files kept: a check failed');
assert.equal(end({removed:1,kept:1,freed_bytes:612367405,last_age_ms:1000}),base+' · 1 old file removed, 584 MB freed · 1 old file kept: a check failed','the singular forms; 1024-based');
assert.equal(end({removed:2,kept:0,freed_bytes:3.5*1024**3,last_age_ms:1000}),base+' · 2 old files removed, 3.5 GB freed','all removed: the removed part only');
assert.equal(end({removed:0,kept:115,freed_bytes:0,last_age_ms:1000}),base+' · 115 old files kept: a check failed','all kept: the kept part only');
assert.equal(end({removed:110,kept:5,freed_bytes:74*1024**3,last_age_ms:3599999}),base+' · 110 old files removed, 74 GB freed · 5 old files kept: a check failed');
assert.equal(end({removed:110,kept:5,freed_bytes:74*1024**3,last_age_ms:3600000}),base,'gone an hour after the last book settled');
assert.equal(end({removed:0,kept:0,freed_bytes:0,last_age_ms:null}),base,'nothing to clean: no part');
assert.equal(end({removed:3,kept:1,freed_bytes:1024**3,last_age_ms:0},{count:2,last_age_ms:0}),base+' · 2 missing books removed from the list, library files untouched · 3 old files removed, 1 GB freed · 1 old file kept: a check failed','after the missing books');
run('recoveryDisconnected=true');
assert.doesNotMatch(end({removed:3,kept:1,freed_bytes:1024**3,last_age_ms:0}),/old file/,'not while the line reads Last confirmed');
run('recoveryDisconnected=false');
assert.equal(run('byteSize(612367405)'),'584 MB');assert.equal(run('byteSize(5*1024**3+1024**3/2)'),'5.5 GB');assert.equal(run('byteSize(84181979136)'),'78 GB');

// 5. "Could not be renamed or moved" (4, 6): a kept book, and an entry whose last try did not write the new names.
assert.equal(run("couldNotReason({key:'old_file_kept'})"),'The old file was not removed.');
assert.equal(run("couldNotReason({key:'did_not_finish',cause:'tags_not_written'})"),'The names could not be written; the audiobook is unchanged.');
assert.equal(run("couldNotReason({key:'did_not_finish',cause:'other'})"),'The rename or move did not finish.','control: any other cause keeps its sentence');
assert.equal(run("couldNotReason({key:'not_app_name'})"),"Its file name is not one the app gave it.",'control: the other keys are as they were');
const entry=run("couldNotEntry({key:'old_file_kept',title:'Written in Bone',author:'Beckett Simon',from:'Z:\\\\A\\\\b.m4b',from_shown:'A\\\\b.m4b',job_id:'j',book_id:'b'})");
const texts=[];const walk=element=>{if(element.textContent)texts.push(element.textContent);for(const child of element.children || [])walk(child);};walk(entry);
assert.ok(texts.includes('The old file was not removed.'),texts.join(' | '));
console.log('PASS 0.31.3 late-write clean-up: the row, its kept count and tooltip, the time estimate, the Waiting item, the two end parts and their hour, the could-not lines');
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_late_cleanup_frontend.js'),module);m.filename=path.join(__dirname,'test_late_cleanup_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

'use strict';
// 0.30.0, Judy's spec section 10: the line under "Book metadata" printed row.scope, the internal grouping key (a path, \x1f,
// then Album and Artist tags read as Latin-1). Now two lines from the engine's scope_view: #source, where the files are
// (one folder, or the first and "N more folders" with every path in its title), and #source-basis, why they are one book.
// The key is never printed. Same vm harness as test_metadata_frontend.js: the real web/app.js, a stub document.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
class Element{
 constructor(id=''){this.id=id;this.value=id==='library'?'Audiobooks':'';this.children=[];this.handlers={};this.dataset={};this.options=[{}];this.textContent='';this.attrs={};this.title='';}
 addEventListener(type,fn){this.handlers[type]=fn;}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}
 append(...nodes){for(const n of nodes){this.children.push(n);n.parentElement=this;}}replaceChildren(...nodes){this.children=[];this.append(...nodes);}
 insertBefore(child){child.parentElement=this;if(!this.children.includes(child))this.children.push(child);}querySelector(){return this.header || (this.header=new Element());}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
const fields=new Map();for(const key of ['original_language','title','author','canonical_author','narrator','universe','series','number','genre','topic','multi_author','anthology'])fields.set(key,new Element());
get('review-form').elements={namedItem:key=>fields.get(key)};get('candidate-members').parentElement=new Element();
const document={getElementById:get,querySelector:()=>({content:'fixture-token'}),querySelectorAll:()=>[],createElement:tag=>new Element(tag)};
const context=vm.createContext({document,console,URL,location:{origin:'http://127.0.0.1:5211'},setTimeout:()=>0,clearTimeout(){},fetch:async()=>({ok:true,json:async()=>({})})});
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
vm.runInContext(source.replace(/viewControls\(\);poll\(\);\s*$/,''),context);
vm.runInContext('refresh=async()=>true',context);
const run=js=>vm.runInContext(js,context);

const folder='Z:\\Audiobooks\\Unsorted\\Линдквист - Впусти меня';
const raw='Âïóñòè ìåíÿ';  // «Впусти меня» in cp1251 read as Latin-1: what the key carried
const view=extra=>({kind:'album',album:'Впусти меня',artist:'Линдквист Йон Айвиде',track:null,track_total:null,basis:null,repaired:false,folders:[folder],title:null,author:null,...extra});
const candidate=extra=>({id:'book1',revision:4,fingerprint:'a'.repeat(64),path:'book1',kind:'candidate',library:'Audiobooks',scope:folder+'\x1fAlbum '+raw+'\x1fArtist x',
  grouping:'Leaf folder',coverage:'Folder scan complete',title_evidence:[],conflicts:[],metadata:{tags:{album:raw}},preview:{reason:'Review',path:''},
  review:{title:'Впусти меня',canonical_author:'Линдквист Йон Айвиде',author:'Линдквист',original_language:'Other'},title_clue:'Впусти меня',artists:[],companions:[],
  members:[{member_key:'one',path:folder+'\\01.mp3',filename:'01.mp3',metadata:{tags:{album:raw}},order:1,track_title:'01',duration:10}],included:['one'],track_order:['one'],
  matching:{state:'completed',proposals:[]},review_context:{metadata_actor:'assistant',source_coverage_confirmed:true,order_confirmed:true,track_actor:'assistant'},cover_choices:[],
  creation:{status:'Ready to create',can_create:true,destination:'Z:/Audiobooks/Author/Book.m4b',duration_seconds:10,reasons:[],device:'Apple Books sync not checked'},
  scope_view:view(extra)});
function lines(extra){context.row=candidate(extra);run('select(row,true)');return [get('source').textContent,get('source-basis').textContent];}

// Positive control: before 0.30.0 the line was the key, with its \x1f and the Latin-1 album.
let [where,why]=lines({});
assert.ok(!where.includes('\x1f') && !where.includes(raw),'the key is never printed: '+JSON.stringify(where));
assert.equal(where,folder);assert.equal(get('source').hidden,false);assert.equal(get('source').title,folder);
assert.equal(why,'Grouped by album «Впусти меня» and artist «Линдквист Йон Айвиде».');assert.equal(get('source-basis').hidden,false);

// Every kind (Judy's table), the album sentence, a missing artist left out, never "Unknown".
const said={
 album:[{},'Grouped by album «Впусти меня» and artist «Линдквист Йон Айвиде».'],
 albumNoArtist:[{artist:null},'Grouped by album «Впусти меня».'],
 single:[{kind:'single_file',track:2,track_total:5},'One audiobook file. Album «Впусти меня», track 2 of 5.'],
 singleNoTotal:[{kind:'single_file',track:2},'One audiobook file. Album «Впусти меня», track 2.'],
 singleNoAlbum:[{kind:'single_file',album:null},'One audiobook file.'],
 volume:[{kind:'volume',basis:'each file names its own work',track:2,track_total:5},
   'Kept as a separate book: each file names its own work. Album «Впусти меня», track 2 of 5. If these files are one book, select them and use Join into one book.'],
 volumeNoReason:[{kind:'volume',album:null},'Kept as a separate book. If these files are one book, select them and use Join into one book.'],
 split:[{kind:'split_book'},'Parts of one book, grouped by the file names.'],
 work:[{kind:'filename_work',author:'Автор',title:'Название'},'Grouped by the file names: «Автор» - «Название».'],
 numbered:[{kind:'numbered_set'},'Numbered files in one folder. The order comes from the file names.'],
 standalone:[{kind:'standalone'},'One file with no album or numbering.'],
 sameTitle:[{kind:'same_title',title:'Пастушья корона',artist:null},'Grouped by the title tag «Пастушья корона».'],
 folderAsk:[{kind:'folder',basis:'ask'},'One source folder that may hold more than one book: asked before anything is joined or split.'],
 folderOne:[{kind:'folder',basis:'one'},'One book: every audio file of its source folder.'],
 anthology:[{kind:'anthology'},'One anthology volume: its stories keep their source credits.'],
 other:[{kind:'other'},'Album «Впусти меня».'],
 otherBare:[{kind:'other',album:null},''],
};
for(const [name,[extra,text]] of Object.entries(said)){
 [,why]=lines(extra);assert.equal(why,text,name);assert.equal(get('source-basis').hidden,!text,name+': an empty line is hidden');
 assert.ok(!/Unknown|\x1f/.test(why),name);
}
// Repaired text says so, last; only where tag text is printed.
assert.equal(lines({repaired:true})[1],'Grouped by album «Впусти меня» and artist «Линдквист Йон Айвиде». The tag text was repaired from an old encoding.');
assert.equal(lines({kind:'volume',basis:'there are no chapters to compare',repaired:true})[1],
 'Kept as a separate book: there are no chapters to compare. Album «Впусти меня». If these files are one book, select them and use Join into one book. The tag text was repaired from an old encoding.');
assert.equal(lines({kind:'split_book',repaired:true})[1],'Parts of one book, grouped by the file names.','no tag text printed: no repair sentence');

// Several folders: the first, shortened, and how many more; every path in its title, one per line.
const cds=['Z:\\Audiobooks\\Unsorted\\Впусти меня\\CD1','Z:\\Audiobooks\\Unsorted\\Впусти меня\\CD2','Z:\\Audiobooks\\Unsorted\\Впусти меня\\CD3'];
[where]=lines({folders:cds});assert.equal(where,'Z:\\…\\CD1 and 2 more folders');assert.equal(get('source').title,cds.join('\n'));
[where]=lines({folders:cds.slice(0,2)});assert.equal(where,'Z:\\…\\CD1 and 1 more folder');
[where]=lines({folders:['\\\\nas\\books\\Впусти меня','\\\\nas\\books\\Другая']});assert.equal(where,'\\\\nas\\…\\Впусти меня and 1 more folder');
// No folder known: line 1 is hidden. No scope_view at all (an older engine): nothing is invented, the key still never shows.
[where]=lines({folders:[]});assert.equal(where,'');assert.equal(get('source').hidden,true);
context.row={...candidate({}),scope_view:undefined};run('select(row,true)');
assert.equal(get('source').textContent,'');assert.equal(get('source-basis').textContent,'');assert.equal(get('source-basis').hidden,true);

// A file row still shows its path; no basis line.
context.file={...candidate({}),kind:'audiobook',path:'C:\\fixture\\book.mp3',record_id:'a'.repeat(64),size:12,modified:'123'};run('select(file,true)');
assert.equal(get('source').textContent,'C:\\fixture\\book.mp3');assert.equal(get('source').hidden,false);assert.equal(get('source-basis').hidden,true);assert.equal(get('source').title,'');

// Nothing in app.js prints the key any more; the page has the field-help line.
assert.ok(!/row\.scope\b/.test(source),'no row.scope in app.js');
const page=fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8');
assert.match(page,/<p id="source" class="path"><\/p><p id="source-basis" class="field-help" hidden><\/p>/);
console.log('PASS the Book metadata lines: folders and the engine\'s reason, never the grouping key');

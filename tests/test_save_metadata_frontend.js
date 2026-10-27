'use strict';
// "Save preview metadata does nothing" (2026-10-26 diagnosis): the save succeeded and the page never said so. The press shows
// Saving… at once and keeps focus (aria-disabled); "Saved." lands with the answer even while focus is in the form; a press is
// never dropped (during a save the newest values are saved next; during another press it waits, ruling 35); edits typed
// while it saves stay unsaved; a book a background update moved on keeps Sergei's values and is saved on its new revision.
// The fake DOM of test_metadata_frontend.js. 0.22.3 (ruling 40): a book's names are not edited here, so the edits are the
// Reader / narrator field, and "Saved: {fields}." names what was saved (Judy 2.5).
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
class Element{
 constructor(id=''){this.id=id;this.value=id==='library'?'Audiobooks':'';this.children=[];this.handlers={};this.dataset={};this.options=[{}];this.textContent='';this.attrs={};}
 addEventListener(type,fn){this.handlers[type]=fn;}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}getAttribute(k){return this.attrs[k] ?? null;}
 append(...nodes){for(const n of nodes){this.children.push(n);n.parentElement=this;}}replaceChildren(...nodes){this.children=[];this.append(...nodes);}
 insertBefore(child){child.parentElement=this;if(!this.children.includes(child))this.children.push(child);}querySelector(){return this.header || (this.header=new Element());}
 contains(other){return other===this || this.children.some(child=>child.contains?.(other));}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
const fields=new Map();for(const key of ['original_language','title','author','canonical_author','narrator','universe','series','number','genre','topic','multi_author','anthology'])fields.set(key,new Element());
const form=get('review-form');form.elements={namedItem:key=>fields.get(key)};for(const field of fields.values())form.append(field);get('candidate-members').parentElement=new Element();
const document={getElementById:get,querySelector:()=>({content:'fixture-token'}),querySelectorAll:()=>[],createElement:tag=>new Element(tag),activeElement:null};
const answers=[];let requests=[],refreshes=0;
const context=vm.createContext({document,console,URL,location:{origin:'http://127.0.0.1:5211'},setTimeout:()=>0,clearTimeout(){},
  fetch:(route,options)=>{const body=options?.body?JSON.parse(options.body):null;requests.push({route,body});
    if(route==='/api/candidate/review'){return new Promise(resolve=>answers.push({body,resolve}));}
    return Promise.resolve({ok:true,json:async()=>({})});}});
let source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');source=source.replace(/viewControls\(\);poll\(\);\s*$/,'');vm.runInContext(source,context);
vm.runInContext('refresh=async()=>{refreshCount++;throw Error("list read failed")};var refreshCount=0',context);
const run=js=>vm.runInContext(js,context),tick=()=>new Promise(resolve=>setImmediate(resolve));
const row={id:'book1',revision:4,path:'book1',kind:'candidate',library:'Audiobooks',scope:'fixture',grouping:'Leaf folder',coverage:'',title_evidence:[],conflicts:[],metadata:{tags:{}},preview:{reason:'',path:''},
  review:{title:'Saved',canonical_author:'Author',author:'Author Folder',original_language:'Other'},title_clue:'Book One',artists:[],companions:[],members:[],included:[],track_order:[],matching:{state:'idle',proposals:[]},
  review_context:{metadata_actor:'assistant',manual_note:'Old note'},cover_choices:[],creation:{status:'Ready to create',can_create:false,destination:'',duration_seconds:1,reasons:[]}};
const answered=(revision,narrator)=>({ok:true,status:200,json:async()=>({saved:true,row:{...row,revision,review:{...row.review,narrator}}})});
const button=get('save-metadata'),note=()=>get('review-note').textContent;
function type(field,value){fields.get(field).value=value;form.handlers.input({target:fields.get(field)});}
function press(){return form.handlers.submit({preventDefault(){}});}
(async()=>{
  context.row=row;run('select(row,true)');
  // 1. Saving… at the press, keeping focus; "Saved." with the answer while focus stays in the form.
  document.activeElement=fields.get('narrator');type('narrator','Сейф №1');assert.equal(note(),'Unsaved local review.');
  const first=press();await tick();
  assert.equal(button.textContent,'Saving…');assert.equal(button.getAttribute('aria-disabled'),'true','inert, never disabled: focus stays');
  assert.equal(note(),'Saving…');assert.equal(answers.length,1);assert.equal(answers[0].body.review.narrator,'Сейф №1');
  assert.equal(answers[0].body.manual_note,'Old note','ruling 36: the stored note is kept, never typed');
  // 2. A press during the save is not dropped; an edit typed meanwhile stays unsaved.
  type('narrator','Сейф №2');press();await tick();assert.equal(answers.length,1,'one save at a time');
  answers[0].resolve(answered(5,'Сейф №1'));await tick();await tick();await tick();
  assert.equal(note(),'Saving…','the newest values are saved next');assert.equal(answers.length,2);
  assert.equal(answers[1].body.revision,5,'on the revision the first save made');assert.equal(answers[1].body.review.narrator,'Сейф №2');
  answers[1].resolve(answered(6,'Сейф №2'));await tick();await tick();
  assert.equal(note(),'Saved: Reader / narrator.');assert.equal(button.textContent,'Save preview metadata');assert.equal(button.getAttribute('aria-disabled'),null);
  assert.equal(run('dirty'),false);assert.ok(run('refreshCount')>=1,'the list reload follows');assert.equal(note(),'Saved: Reader / narrator.','a failed reload is not the save\'s failure');
  // 3. Typed while it saved, with no second press: those edits stay unsaved.
  type('narrator','Сейф №3');const third=press();await tick();type('narrator','Сейф №4');
  answers[2].resolve(answered(7,'Сейф №3'));await third;await tick();
  assert.equal(note(),'Unsaved local review.');assert.equal(run('dirty'),true);
  // 4. Candidate changed: his values are kept and saved again on the new revision, once.
  const fourth=press();await tick();assert.equal(answers[3].body.review.narrator,'Сейф №4');
  answers[3].resolve({ok:false,status:409,json:async()=>({error:'Candidate changed; reload evidence before reviewing',code:'changed',row:{...row,revision:9,review:{...row.review,narrator:'Researched'}}})});
  await tick();await tick();assert.equal(answers.length,5,'saved again');assert.equal(answers[4].body.revision,9);assert.equal(answers[4].body.review.narrator,'Сейф №4','his value, not the research\'s');
  answers[4].resolve(answered(10,'Сейф №4'));await fourth;await tick();assert.equal(note(),'Saved: Reader / narrator.');
  // 5. During another press of this page the save waits for it, then runs (ruling 35).
  type('narrator','Сейф №5');run('busy=true');press();await tick();
  assert.equal(answers.length,5,'waits');assert.equal(button.textContent,'Saving…');assert.equal(note(),'Saving after the current operation finishes…');
  run('busy=false;controls()');await tick();assert.equal(answers.length,6,'runs once the other press ends');assert.equal(answers[5].body.review.narrator,'Сейф №5');
  answers[5].resolve(answered(11,'Сейф №5'));await tick();await tick();assert.equal(note(),'Saved: Reader / narrator.');
  // 6. A refusal says so; nothing is silent.
  type('narrator','Сейф №6');const sixth=press();await tick();answers[6].resolve({ok:false,status:400,json:async()=>({error:'Invalid canonical metadata'})});await sixth;await tick();
  assert.equal(note(),'Not saved. Invalid canonical metadata. Nothing was changed.','0.22.3 (Judy 2.5): the reason beside the button, not at the page top');assert.equal(run('dirty'),true,'his values stay');
  // 7. Ruling 40 (Senua's 0.22.3 review, M3): a book's hidden name inputs are never what a Save sends. The request says the
  // names are the row's, and carries the saved draft's names, whatever stale text the hidden inputs hold.
  fields.get('title').value='Stale hidden title';fields.get('series').value='Old series';type('narrator','Сейф №7');const seventh=press();await tick();
  assert.equal(answers[7].body.names_row_only,true);assert.equal(answers[7].body.review.title,'Saved');assert.equal(answers[7].body.review.series,'');
  assert.equal(answers[7].body.review.narrator,'Сейф №7');answers[7].resolve(answered(12,'Сейф №7'));await seventh;await tick();
  console.log('PASS Save preview metadata: Saving… at the press, Saved. with the answer, no press dropped, typed edits kept unsaved, rebased on Candidate changed, waits for another press');
})().catch(error=>{console.error(error);process.exitCode=1;});

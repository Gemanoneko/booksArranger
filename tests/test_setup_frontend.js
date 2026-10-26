// The first-run form (desktop/setup.html): a folder the shell refuses shows the shell's own sentence, never Electron's IPC
// prefix (Futaba's 0.22.1 QA, m-10: "Error invoking remote method 'books:select': Error: Keep data outside source
// libraries and installation folders"). Judy 0.22.2 section 7: every control has its tooltip, and the busy and empty
// states use aria-disabled so focus stays. desktop/setup.js in a vm with a fake form; no window.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));

function form({setup,select}){
  const nodes={};
  const make=(id,extra={})=>nodes[id]=Object.assign({id,textContent:'',value:'',disabled:false,title:'',handlers:{},attributes:{},
    addEventListener(type,fn){this.handlers[type]=fn;},setAttribute(name,value){this.attributes[name]=String(value);},
    getAttribute(name){return name in this.attributes?this.attributes[name]:null;},removeAttribute(name){delete this.attributes[name];}},extra);
  for(const id of ['folder','accept','error','help','browse','cancel','existing-label','new-label'])make(id);
  const radios=[make('existing',{value:'existing',checked:true}),make('new',{value:'new',checked:false})];
  const document={querySelector(selector){if(selector==='[name=mode]:checked')return radios.find(r=>r.checked);return nodes[selector.replace(/^#/,'')];},
    querySelectorAll(){return radios;}};
  const api={setup,select,browse:async()=>'D:\\Books data',quit:async()=>{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','desktop','setup.js'),'utf8'),{window:{booksDesktop:api},document,String,console});
  return {nodes,radios};
}
const refused=sentence=>new Error(`Error invoking remote method 'books:select': Error: ${sentence}`);
const inert=node=>node.getAttribute('aria-disabled')==='true';

(async()=>{
  const sentence='Keep data outside source libraries and installation folders';
  let release;
  const {nodes,radios}=form({setup:async()=>({defaultFolder:''}),select:()=>new Promise((resolve,reject)=>{release=()=>reject(refused(sentence));})});
  await flush();
  // Tooltips (Judy 7).
  assert.equal(nodes['existing-label'].title,'Use a catalog you already have. Its files stay where they are.');
  assert.equal(nodes['new-label'].title,'Start an empty catalog in the folder below.');
  assert.equal(nodes.folder.title,'The folder that holds the catalog. Press Browse… to change it.');
  assert.equal(nodes.browse.title,'Choose the data folder.');
  assert.equal(nodes.cancel.title,'Close without choosing a folder. Books Arranger closes.');
  // No folder: inert with its tooltip, never the disabled attribute (focus stays).
  assert.equal(inert(nodes.accept),true);assert.equal(nodes.accept.disabled,false);
  assert.equal(nodes.accept.title,'Choose a data folder first.');
  await nodes.accept.handlers.click();assert.equal(release,undefined,'an inert press sends nothing');
  await nodes.browse.handlers.click();
  assert.equal(nodes.folder.value,'D:\\Books data');assert.equal(inert(nodes.accept),false);
  assert.equal(nodes.accept.title,'Check this folder and open its catalog.');
  radios[0].checked=false;radios[1].checked=true;radios[1].handlers.change();
  assert.equal(nodes.accept.textContent,'Create catalog');
  radios[1].checked=false;radios[0].checked=true;radios[0].handlers.change();
  await nodes.browse.handlers.click();
  const pressed=nodes.accept.handlers.click();
  assert.equal(inert(nodes.accept),true,'checking: inert');assert.equal(nodes.accept.title,'Checking the data folder…');
  release();await pressed;await flush();
  assert.equal(nodes.error.textContent,sentence,'the shell\'s sentence, without the IPC prefix');
  assert.equal(inert(nodes.accept),false,'the form can be used again');
  // New catalog: its own tooltip.
  radios[0].checked=false;radios[1].checked=true;radios[1].handlers.change();
  assert.equal(nodes.accept.title,'Choose a data folder first.','New catalog has its own folder, none chosen yet');
  await nodes.browse.handlers.click();
  assert.equal(nodes.accept.title,'Check this folder and create an empty catalog in it.');
  // The same for a refusal of the form's own setup call, and a plain error (no prefix) is shown as it is.
  const broken=form({setup:async()=>{throw new Error("Error invoking remote method 'books:setup': Error: Setup is unavailable");},select:async()=>({opened:true})});
  await flush();
  assert.equal(broken.nodes.error.textContent,'Setup is unavailable');
  const plain=form({setup:async()=>({defaultFolder:''}),select:async()=>{throw new Error('Choose an absolute data folder');}});
  await flush();await plain.nodes.browse.handlers.click();await plain.nodes.accept.handlers.click();await flush();
  assert.equal(plain.nodes.error.textContent,'Choose an absolute data folder');
  console.log('PASS setup form: a refusal shows the shell\'s sentence only; every control has its tooltip; busy and empty are aria-disabled');
})().catch(error=>{console.error(error);process.exitCode=1;});

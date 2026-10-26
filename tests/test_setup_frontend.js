// The first-run form (desktop/setup.html): a folder the shell refuses shows the shell's own sentence, never Electron's IPC
// prefix (Futaba's 0.22.1 QA, m-10: "Error invoking remote method 'books:select': Error: Keep data outside source
// libraries and installation folders"). desktop/setup.js in a vm with a fake form; no window.
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));

function form({setup,select}){
  const nodes={};
  const make=(id,extra={})=>nodes[id]=Object.assign({id,textContent:'',value:'',disabled:false,handlers:{},addEventListener(type,fn){this.handlers[type]=fn;}},extra);
  for(const id of ['folder','accept','error','help','browse','cancel'])make(id);
  const radios=[make('existing',{value:'existing',checked:true}),make('new',{value:'new',checked:false})];
  const document={querySelector(selector){if(selector==='[name=mode]:checked')return radios.find(r=>r.checked);return nodes[selector.replace(/^#/,'')];},
    querySelectorAll(){return radios;}};
  const api={setup,select,browse:async()=>'D:\\Books data',quit:async()=>{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','desktop','setup.js'),'utf8'),{window:{booksDesktop:api},document,String,console});
  return nodes;
}
const refused=sentence=>new Error(`Error invoking remote method 'books:select': Error: ${sentence}`);

(async()=>{
  const sentence='Keep data outside source libraries and installation folders';
  const nodes=form({setup:async()=>({defaultFolder:'C:\\Users\\me\\AppData\\Local\\Books Arranger\\data'}),select:async()=>{throw refused(sentence);}});
  await flush();
  await nodes.browse.handlers.click();
  assert.equal(nodes.folder.value,'D:\\Books data');assert.equal(nodes.accept.disabled,false);
  await nodes.accept.handlers.click();await flush();
  assert.equal(nodes.error.textContent,sentence,'the shell\'s sentence, without the IPC prefix');
  assert.equal(nodes.accept.disabled,false,'the form can be used again');
  // The same for a refusal of the form's own setup call, and a plain error (no prefix) is shown as it is.
  const broken=form({setup:async()=>{throw new Error("Error invoking remote method 'books:setup': Error: Setup is unavailable");},select:async()=>({opened:true})});
  await flush();
  assert.equal(broken.error.textContent,'Setup is unavailable');
  const plain=form({setup:async()=>({defaultFolder:''}),select:async()=>{throw new Error('Choose an absolute data folder');}});
  await flush();await plain.browse.handlers.click();await plain.accept.handlers.click();await flush();
  assert.equal(plain.error.textContent,'Choose an absolute data folder');
  console.log('PASS setup form: a refusal shows the shell\'s sentence only');
})().catch(error=>{console.error(error);process.exitCode=1;});

// Runs the actual frontend's edit/refresh/save path without opening a user window.
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const fields=new Map();
for(const name of ['original_language','title','author','series','number','genre','topic','multi_author']) fields.set(name,{value:'',checked:false});
const nodes=new Map();
function node(id){
  if(!nodes.has(id))nodes.set(id,{value:id==='library'?'Audiobooks':'',textContent:'',hidden:false,children:[],handlers:{},
    addEventListener(type,fn){this.handlers[type]=fn;},setAttribute(){},replaceChildren(){this.children=[];},append(value){this.children.push(value);}});
  return nodes.get(id);
}
node('review-form').elements={namedItem:name=>fields.get(name)};
const oldRow={path:'C:/fixture/book.mp3',root:'C:/fixture',kind:'audiobook',size:10,modified:'2000000000000000001',missing:0,error:'',
  metadata:{method:'fixture',tags:{}},preview:{path:'',reason:'review'},review:null};
const newRow={...oldRow,size:25,modified:'2000000000000000002',metadata:{method:'fixture',title:'Changed source',tags:{}}};
let posted=null;
const context=vm.createContext({console,document:{getElementById:node,querySelector:()=>({content:'fixture-token'})},
  setTimeout:()=>0,clearTimeout(){},oldRow,newRow,
  fetch:async(route,options)=>{
    if(route==='/api/review'){
      posted=JSON.parse(options.body);
      return {ok:false,status:400,json:async()=>({error:'Inventory file changed; reload evidence'})};
    }
    // Initial polling stays pending so the test controls the catalog refresh precisely.
    return new Promise(()=>{});
  }});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8'),context);
vm.runInContext('select(oldRow,true)',context);
fields.get('original_language').value='Other';
fields.get('title').value='Old canonical title';
fields.get('author').value='Old Author';
node('review-form').handlers.input();
vm.runInContext('select(newRow,false)',context);
assert.equal(fields.get('title').value,'Old canonical title','polling must preserve unsaved text');
(async()=>{
  await node('review-form').handlers.submit({preventDefault(){}});
  assert.equal(posted.modified,oldRow.modified,'save must retain the fingerprint reviewed by the user');
  assert.equal(posted.size,oldRow.size,'save must not adopt a newer source size from polling');
  assert.equal(posted.review.title,'Old canonical title');
  assert.match(node('message').textContent,/changed/);
  console.log('PASS browser unsaved-review fingerprint survives source refresh and stale save is surfaced');
})().catch(error=>{console.error(error);process.exitCode=1;});

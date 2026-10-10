'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
class Element{constructor(id=''){this.id=id;this.value=id==='library'?'Audiobooks':'';this.children=[];this.handlers={};this.dataset={};this.options=[{}];this.textContent='';this.attrs={};this.classList={toggle:(key,on)=>{this[key]=on;}};}addEventListener(k,f){this.handlers[k]=f;}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];if(k==='value')this.value=null;}append(...x){this.children.push(...x);}replaceChildren(...x){this.children=x;}querySelector(){return new Element();}}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element(id));return nodes.get(id);};
get('review-form').elements={namedItem:()=>new Element()};get('candidate-members').parentElement=new Element();
const document={getElementById:get,querySelector:()=>({content:'fixture'}),querySelectorAll:()=>[],createElement:tag=>new Element(tag)};
const context=vm.createContext({document,console,URL,location:{origin:'http://127.0.0.1:5210'},setTimeout:()=>0,clearTimeout(){},fetch:async()=>({ok:true,json:async()=>({})})});
let source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8').replace(/viewControls\(\);poll\(\);\s*$/,'');vm.runInContext(source,context);
function render(overrides){context.fixture={state:'Running',approved_total:2,converted_total:1,queued:0,failed:0,current_title:'Long book title',progress:{phase:'encoding',completed:25,total:100},...overrides};vm.runInContext('state={audiobook_jobs:fixture};renderJobs()',context);}
render({});assert.match(get('jobs-status').textContent,/1 converted out of 2 approved books/);assert.equal(get('jobs-progress').value,25);assert.equal(get('jobs-measure').textContent,' — 25%');assert.equal(get('jobs-measure').attrs['aria-live'],undefined);
render({progress:{phase:'encoding',completed:100,total:100}});assert.equal(get('jobs-progress').value,null);assert.equal(get('jobs-phase-label').textContent,'Finalizing conversion');
render({progress:{phase:'checking'}});assert.equal(get('jobs-progress').value,null);assert.equal(get('jobs-phase-label').textContent,'Verifying audiobook');
render({progress:{phase:'originals',completed:1,total:3}});assert.equal(get('jobs-measure').textContent,' — 1 of 3');assert.ok(get('jobs-progress').value<100);
render({progress:{phase:'originals',completed:3,total:3}});assert.equal(get('jobs-progress').value,null);assert.match(get('jobs-phase-label').textContent,/temporary/);
render({state:'Paused'});assert.equal(get('jobs-progress').value,25);assert.equal(get('jobs-progress')['progress-stopped'],true);assert.match(get('jobs-phase-label').textContent,/^Paused/);
render({state:'Needs attention',progress:{phase:'encoding',completed:25,total:100,reason:'Exact source changed'}});assert.match(get('jobs-phase-label').textContent,/Exact source changed/);assert.equal(get('jobs-progress').value,25);
render({approved_total:0,converted_total:0,current_title:'',progress:null});assert.match(get('jobs-status').textContent,/0 converted out of 0 approved books/);assert.equal(get('book-progress').hidden,true);assert.equal(get('jobs-idle').hidden,false);
render({approved_total:undefined});assert.match(get('jobs-status').textContent,/Approved book progress unavailable/);
render({folder_cleanup_notes:['Native protected stream namespace unsupported']});assert.match(get('jobs-help').textContent,/Empty source folders retained: safe automatic removal is unavailable on this drive/);assert.doesNotMatch(get('jobs-help').textContent,/Native protected/);
const options=vm.runInContext('filterOptions.candidates',context);const index=options.findIndex(x=>x[0]==='converted');assert.equal(options[index][1],'Converted');assert.equal(options[index-1][0],'created');assert.equal(options[index+1][0],'output_attention');
console.log('PASS progress counter, phase truthfulness, pause/error, idle and Converted option');

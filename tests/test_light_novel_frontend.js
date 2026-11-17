'use strict';
// 0.29.0 item 4 (Light novel, Judy's 0.29.0 UX section 4) on the real frontend, with the Retry test's DOM and transport
// doubles: the Edit names field, its Place lead and Entered line, the Remembered Yes/No, and the details panel's review.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
(async()=>{
  run('state='+JSON.stringify(backend));
  assert.equal(run('JSON.stringify(NAMES_FIELDS)'),JSON.stringify(['title','author','series','number','universe','collection','light_novel']));
  assert.equal(run('NAMES_LABELS.light_novel'),'Light novel');
  assert.equal(run('NAMES_TIPS.light_novel'),'File this book under Light Novels, then by author and series as usual. Use it for light novels.');
  // The Place line gains the lead; a plain book reads as before.
  assert.equal(run("placeText({universe:'',series:'Иная',number:'1',collection:false,light_novel:true})"),'Light novel · Series: Иная · No. 1');
  assert.equal(run("placeText({universe:'',series:'Иная',number:'1',collection:false})"),'Series: Иная · No. 1');
  assert.equal(run("enteredText(['series','light_novel'])"),'Entered by you: series, light novel.');
  assert.equal(run("enteredText(['collection'])"),'Entered by you: collection.');
  assert.equal(run("NAMES_BOOL.has('light_novel') && NAMES_BOOL.has('collection')"),true);
  console.log('PASS 0.29.0 Light novel on the page: Edit names field, Place lead, Entered line');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module');const m=new Module(path.join(__dirname,'test_light_novel_frontend.js'),module);m.filename=path.join(__dirname,'test_light_novel_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

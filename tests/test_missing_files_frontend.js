'use strict';
// Files gone from disk are not read errors (Judy's MissingFiles UX 2026-10-24, Sergei's ruling): the real frontend on the
// Retry test's DOM and transport doubles. A gone file reads "No longer found" in its row and "Not found in the last
// complete scan." in its details; its old error text is never on screen. No server, no library.
const fs=require('node:fs'),path=require('node:path');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{'));
harness+=String.raw`
const OLD='moov atom not found',GONE='Not found in the last complete scan.';
function fileRow(name,overrides){return {path:'C:/Library/'+name,kind:'audiobook',library:'Audiobooks',arrival:0,size:0,
  metadata:{title:name,author:'',tags:{},notes:['Metadata read failed; source file untouched'],method:''},review:null,error:'',missing:false,
  error_time:'2026-10-09T12:00:00+00:00',saved_snapshot:false,tag_preview:{},preview:{path:'',confidence:'Needs review',reason:'fixture'},...overrides};}
const present=fileRow('present.m4b',{error:OLD,preview:{path:'',confidence:'Read error',reason:OLD}});
const goneOld=fileRow('gone-old.m4b',{error:OLD,missing:true,preview:{path:'',confidence:'No longer found',reason:GONE}});
const goneClean=fileRow('gone-clean.m4b',{missing:true,preview:{path:'',confidence:'No longer found',reason:GONE}});
(async()=>{
  run('state='+JSON.stringify(backend)+';view="files";filters.files="all"');
  context.fixture=[present,goneOld,goneClean];run('rows=fixture.map(row=>({...row}));renderRows(true)');
  const trs=get('inventory').children;assert.equal(trs.length,3);
  const status=tr=>tr.children[4].textContent;
  assert.equal(status(trs[0]),'Read error · '+OLD,'positive control: a present unreadable file is still a read error');
  assert.equal(status(trs[1]),'No longer found','gone wins over the old error');
  assert.equal(status(trs[2]),'No longer found');

  // Details: the present file keeps its Read error section; the gone one shows the reason line only.
  show(present);
  assert.equal(get('read-error').hidden,false);assert.equal(get('read-error-message').textContent,OLD);
  assert.equal(get('read-error-action').textContent,'This audio file is empty. Replace it with a complete copy, then start scanning.');
  assert.match(get('notes').textContent,/moov atom not found/);
  show(goneOld);
  assert.equal(get('read-error').hidden,true);assert.equal(get('read-error-message').textContent,'');
  assert.equal(get('reason').textContent,GONE);assert.doesNotMatch(get('notes').textContent,/moov atom/);
  show(goneClean);
  assert.equal(get('read-error').hidden,true);assert.equal(get('reason').textContent,GONE);

  // A file that came back and still fails is present and unreadable again: a read error.
  const back={...goneOld,missing:false,preview:{path:'',confidence:'Read error',reason:OLD}};
  context.fixture=[back];run('rows=fixture.map(row=>({...row}));renderRows(true)');
  assert.equal(status(get('inventory').children[0]),'Read error · '+OLD);
  show(back);assert.equal(get('read-error').hidden,false);
  console.log('PASS gone files read "No longer found" in rows and details; no old error text; a returned unreadable file is a read error again');
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
const Module=require('node:module'),m=new Module(path.join(__dirname,'test_missing_files_frontend.js'),module);
m.filename=path.join(__dirname,'test_missing_files_frontend.js');m.paths=module.paths;m._compile(harness,m.filename);

'use strict';
// Entry for the owned private Python Handler fixture. Uses the actual renderer
// helper and host HTTP fetch; the DOM double supplies no durable responses.
const fs=require('node:fs'),path=require('node:path');
const config=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const base=new URL(config.baseURL);
if(base.protocol!=='http:' || base.hostname!=='127.0.0.1' || !base.port || !config.token)throw Error('An explicit private loopback fixture is required');
let harness=fs.readFileSync(path.join(__dirname,'test_retry_frontend.js'),'utf8');
harness=harness.slice(0,harness.indexOf('(async()=>{')).replace("content:'fixture-token'",'content:config.token');
harness+=String.raw`
const crypto=require('node:crypto'),wire=[];
context.crypto=crypto.webcrypto;
context.fetch=(route,options)=>{wire.push({route,body:options?.body?JSON.parse(options.body):null});return fetch(new URL(route,config.baseURL),options);};
const packed=v=>v===null||typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?'['+v.map(packed).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+packed(v[k])).join(',')+'}';
const hash=v=>crypto.createHash('sha256').update(packed(v)).digest('hex');
const effectList=(action,p)=>[...new Set(action==='names'?Object.keys(p.names).map(k=>'names.'+k):action==='approve'?['approval',...Object.keys(p.names||{}).map(k=>'names.'+k),...['title','author'].filter(k=>typeof p[k]==='string'&&p[k].trim()).map(k=>'names.'+k)]:[action])].sort();
(async()=>{
  context.fixture=config.row;context.payload=config.payload;context.action=config.action;context.library=config.library || 'Audiobooks';
  run('selectedLibrary=library');
  const result=config.action==='file_review'?await run('sendMetadata(fixture,payload.review)'):await run('bookDecision(fixture,action,payload,library)');
  assert.equal(result.durable,true);assert.equal(result.decision.schema,'books-durable-decision-v1');
  const sends=wire.filter(w=>w.route==='/api/book-decisions');assert.equal(sends.length,1,'one actual acceptance request');
  const body=sends[0].body;assert.equal(body.action,config.action);assert.deepEqual(body.payload,config.payload);
  const effects=effectList(body.action,body.payload),expected=hash({book_id:body.id,action:body.action,revision:body.revision,fingerprint:body.fingerprint,payload:body.payload,effects,predecessor:body.predecessor});
  assert.equal(result.decision.payload_sha256,expected);assert.equal(result.decision.request_id,body.request_id);
  context.requestID=body.request_id;const status=await run('request("/api/book-decisions/status",{request_id:requestID})');
  assert.equal(status.decision.request_id,body.request_id);assert.equal(status.decision.payload_sha256,expected);
  context.bookID=body.id;const current=await run('request("/api/book-decisions/book",{library,id:bookID})');
  assert.equal(current.head.source_fingerprint,body.fingerprint);assert.equal(current.head.request_id,body.request_id);
  if(['accepted','applying','needs_review'].includes(status.decision.state))for(const effect of effects)assert.equal(current.head.effects[effect],body.request_id);
  else {assert.equal(status.decision.state,'applied');assert.ok(status.decision.result,'applied acceptance retains its terminal saved receipt');for(const effect of effects)assert.notEqual(current.head.effects[effect],body.request_id,'fulfilled work has no unresolved owned effect');}
  console.log(JSON.stringify({pass:true,action:body.action,body,expected_sha256:expected,decision:result.decision,status:status.decision.state,head:current.head}));
})().catch(error=>{console.error(error);process.exitCode=1;});
`;
new Function('require','__dirname','config',harness)(require,__dirname,config);

'use strict';
// Compatibility transport for older DOM behavior fixtures. Their existing action
// handlers still control delays/refusals/results; a real durable envelope is now
// recorded and acknowledged. test_durable_decisions_frontend.js independently
// checks the production wire without this bridge.
const crypto=require('node:crypto');
const packed=value=>value===null||typeof value!=='object'?JSON.stringify(value):Array.isArray(value)?'['+value.map(packed).join(',')+']':'{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+packed(value[key])).join(',')+'}';
const hash=value=>crypto.createHash('sha256').update(packed(value)).digest('hex');
function effects(action,payload){return [...new Set(action==='names'?Object.keys(payload.names).map(k=>'names.'+k):action==='approve'?['approval',...Object.keys(payload.names||{}).map(k=>'names.'+k),...['title','author'].filter(k=>typeof payload[k]==='string'&&payload[k].trim()).map(k=>'names.'+k)]:[action])].sort();}
module.exports=function createDurableFixture(){
  const records=new Map(),heads=new Map();
  return async function durableFixture(route,options,fetch){
    const body=JSON.parse(options.body),ok=value=>({ok:true,status:200,json:async()=>value});
    if(route==='/api/book-decisions/book')return ok({head:heads.get(body.id)||null,decisions:[...records.values()].filter(d=>d.book_id===body.id && d.state!=='applied'),application:{state:'waiting',error:null}});
    if(route==='/api/book-decisions/status'){const decision=records.get(body.request_id);return decision?ok({decision,application:{state:'waiting',error:null}}):{ok:false,status:404,json:async()=>({code:'decision_not_found',error:'Unknown decision'})};}
    if(route!=='/api/book-decisions')throw Error('Unexpected durable fixture route '+route);
    if(records.has(body.request_id))return ok({decision:records.get(body.request_id),application:{state:'waiting',error:null}});
    const legacy={names:'/api/candidate/names-save',approve:'/api/candidate/approve',review:'/api/candidate/review',tracks:'/api/candidate/tracks',metadata_choices:'/api/candidate/metadata-choices',file_review:'/api/review'}[body.action];
    const data={library:body.library,id:body.id,revision:body.revision,...body.payload};
    if(body.action==='approve')for(const key of ['title','author','names','choice','path'])if(data[key]===null)delete data[key];
    if(body.action==='approve'&&!data.without_missing)delete data.without_missing;
    const answer=await fetch(legacy,{...options,body:JSON.stringify(data)});
    if(!answer.ok)return answer;
    const result=await answer.json(),owned=effects(body.action,body.payload);
    const decision={schema:'books-durable-decision-v1',request_id:body.request_id,book_id:body.id,action:body.action,state:result.queued?'accepted':'applied',sequence:records.size+1,observed_revision:body.revision,source_fingerprint:body.fingerprint,predecessor:body.predecessor,effects:owned,active_effects:owned,payload:body.payload,payload_sha256:hash({book_id:body.id,action:body.action,revision:body.revision,fingerprint:body.fingerprint,payload:body.payload,effects:owned,predecessor:body.predecessor}),result:result.queued?null:result};
    records.set(body.request_id,decision);const head={...(heads.get(body.id)?.effects||{})};for(const key of owned)head[key]=body.request_id;
    heads.set(body.id,{request_id:body.request_id,generation:decision.sequence,effects:head,source_fingerprint:body.fingerprint});
    return {ok:true,status:202,json:async()=>({decision,application:{state:'waiting',error:null}})};
  };
};

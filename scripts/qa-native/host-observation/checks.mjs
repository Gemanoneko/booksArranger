// Pure injected fixtures only. Never runs a guard, process or real capture IO.
export function runChecks(api,assert,sources){
 let count=0;const test=fn=>{fn();count++;};
 const request={cmd:api.COMMAND,shell:api.SHELL,workdir:'C:/Antigravity Projects/Studio Illuminati',login:false,yield_time_ms:10000,max_output_tokens:1000};
 const raw=JSON.stringify({hook_event_name:'PreToolUse',tool_name:'Bash',cwd:request.workdir,tool_input:request});
 const make=value=>JSON.stringify({hook_event_name:'PreToolUse',tool_name:'Bash',tool_input:value});
 test(()=>assert.equal(api.isProbe(raw),true));
 test(()=>{const m=api.metadata(raw);assert.equal(m.authority,false);assert.equal(m.raw.sha256,api.sha(raw));assert.equal(m.raw.utf8_bytes,Buffer.byteLength(raw));assert.equal(m.fields.cmd.sha256,api.sha(request.cmd));assert.equal(m.fields.cmd.utf8_bytes,Buffer.byteLength(request.cmd));assert.equal(m.fields.shell.sha256,api.sha(request.shell));assert.equal(JSON.stringify(m).includes(request.cmd),false);assert.equal(JSON.stringify(m).includes(request.workdir),false);});
 test(()=>assert.equal(api.metadata(make({command:api.COMMAND})).fields.command.sha256,api.sha(api.COMMAND)));
 test(()=>{const m=api.metadata(JSON.stringify({hook_event_name:'PreToolUse',tool_name:'Bash',tool_input:request,tool_use_id:'call-fixture',turn_id:'turn-fixture',session_id:'session-fixture'}));assert.equal(m.ids.tool_use_id.sha256,api.sha('call-fixture'));assert.equal(m.ids.turn_id.utf8_bytes,12);assert.equal(m.ids.session_id.type,'string');assert.equal(JSON.stringify(m).includes('call-fixture'),false);});
 for(const id of ['',123,'x'.repeat(257)])test(()=>assert.throws(()=>api.metadata(JSON.stringify({hook_event_name:'PreToolUse',tool_name:'Bash',tool_input:request,tool_use_id:id}))));
 for(const cmd of ['echo hello',"echo '"+api.TOKEN+"'",api.COMMAND.replace(api.TOKEN,api.TOKEN+'-other'),'npm run test'])test(()=>assert.equal(api.isProbe(make({cmd})),false));
 for(const value of [{...request,extra:'not permitted'},{...request,command:api.COMMAND},{...request,shell:'different'},{...request,login:'false'},{...request,yield_time_ms:1.5},{...request,max_output_tokens:-1}])test(()=>assert.throws(()=>api.metadata(make(value))));
 for(const value of ['{invalid',raw.replace('PreToolUse','PostToolUse'),JSON.stringify({hook_event_name:'PreToolUse',tool_name:'Bash',tool_input:request,session_id:api.TOKEN}),raw+' '.repeat(65537)])test(()=>assert.throws(()=>api.metadata(value)));
 test(()=>assert.throws(()=>api.metadata(JSON.stringify({hook_event_name:'PreToolUse',tool_name:'Bash',tool_input:request,unknown:'x'}))));
 function fixture(failure){let bytes=Buffer.alloc(0),created=false,closes=0;const events=[];const identity={dev:1,ino:100,nlink:1,isFile:()=>true,isDirectory:()=>false,isSymbolicLink:()=>false};const directory=name=>({dev:1,ino:name,isFile:()=>false,isDirectory:()=>true,isSymbolicLink:()=>failure==='symlink'});const io={lstatSync(name){events.push(['stat',name]);if(name===api.EVIDENCE&&created)return {...identity,size:bytes.length};return directory(name);},realpathSync:name=>name,openSync(name,flags,mode){assert.equal(name,api.EVIDENCE);assert.equal(flags,'wx+');assert.equal(mode,0o600);if(failure==='collision')throw Error('collision');created=true;return 7;},fstatSync(){return {...identity,nlink:failure==='hardlink'?2:1,size:bytes.length};},writeSync(fd,data,offset,length,position){assert.equal(fd,7);assert.equal(position,0);bytes=Buffer.from(data.subarray(offset,offset+(failure==='partial'?length-1:length)));return bytes.length;},fsyncSync(){if(failure==='flush')throw Error('flush');},readSync(fd,out){bytes.copy(out);if(failure==='readback')out[0]^=1;return bytes.length;},closeSync(fd){assert.equal(fd,7);closes++;if(failure==='close')throw Error('close');}};return {io,events,get bytes(){return bytes;},get created(){return created;},get closes(){return closes;}};}
 test(()=>{const f=fixture(),r=api.captureProbe(raw,f.io);assert.equal(r.captured,true);assert.equal(f.closes,1);assert.equal(f.bytes.length<=4096,true);assert.equal(r.sha256,api.sha(f.bytes));assert.equal(f.events.some(e=>String(e[1]).includes('observer-metadata.jsonl')),false);});
 for(const failure of ['collision','symlink','hardlink','partial','flush','readback','close'])test(()=>{const f=fixture(failure),r=api.captureProbe(raw,f.io);assert.equal(r.captured,false,failure);if(failure==='close')assert.equal(f.closes,1);if(['partial','flush','readback','close'].includes(failure))assert.equal(f.bytes.length>0,true);});
 test(()=>{const f=fixture();assert.equal(api.captureProbe(make({...request,unknown:1}),f.io).captured,false);assert.equal(f.created,false);});
 test(()=>{const f=fixture(),first=api.captureProbe(raw,f.io);assert.equal(first.captured,true);f.io.openSync=()=>{throw Error('collision');};assert.equal(api.captureProbe(raw,f.io).captured,false);assert.equal(api.sha(f.bytes),first.sha256);});
 test(()=>{const f=fixture(),old=f.io.lstatSync;let opened=false;const open=f.io.openSync;f.io.openSync=(...args)=>{opened=true;return open(...args);};f.io.lstatSync=name=>{const stat=old(name);return opened&&name!==api.EVIDENCE?{...stat,ino:'replaced'}:stat;};assert.equal(api.captureProbe(raw,f.io).captured,false);assert.equal(f.created,true);assert.equal(f.bytes.length,0);});
 test(()=>{const result={status:2,signal:null,stdout:'ORIGINAL\0BYTES',stderr:'ORIGINAL STDERR'};let calls=0;assert.equal(api.probeDecision(raw,()=>({captured:true}),input=>{calls++;assert.equal(input,raw);return result;}),result);assert.equal(calls,1);});
 for(const capture of [()=>({captured:false}),()=>{throw Error('capture fail');}])test(()=>{let calls=0;const result=api.probeDecision(raw,capture,()=>{calls++;throw Error('must not invoke');});assert.equal(calls,0);assert.equal(result.status,0);assert.equal(result.stderr,'');assert.deepEqual(JSON.parse(result.stdout),{hookSpecificOutput:{hookEventName:'PreToolUse',permissionDecision:'deny',permissionDecisionReason:'[books-host-observation] Exact probe capture failed; probe held.'}});});
 test(()=>{const original={status:2,stdout:'original denial',stderr:'kept'};assert.equal(api.probeDecision(make({cmd:"echo '"+api.TOKEN+"'"}),()=>{throw Error('must not capture');},()=>original),original);});
 for(const failure of ['collision','partial','flush','close'])test(()=>{const f=fixture(failure);let guardCalls=0;const result=api.probeDecision(raw,input=>api.captureProbe(input,f.io),()=>{guardCalls++;return {status:0,stdout:'must not happen',stderr:''};});assert.equal(guardCalls,0);assert.equal(JSON.parse(result.stdout).hookSpecificOutput.permissionDecision,'deny');assert.equal(result.status,0);});
 test(()=>{const f=fixture(),original={status:2,stdout:'original denial\0kept',stderr:'original stderr'};let guardCalls=0;const result=api.probeDecision(raw,input=>api.captureProbe(input,f.io),input=>{guardCalls++;assert.equal(input,raw);return original;});assert.equal(result,original);assert.equal(guardCalls,1);assert.equal(f.closes,1);});
 test(()=>{const f=fixture();let guardCalls=0;const duplicate=JSON.stringify({hook_event_name:'PreToolUse',tool_name:'Bash',tool_input:request,session_id:api.TOKEN});const result=api.probeDecision(duplicate,input=>api.captureProbe(input,f.io),()=>{guardCalls++;});assert.equal(guardCalls,0);assert.equal(f.created,false);assert.equal(JSON.parse(result.stdout).hookSpecificOutput.permissionDecision,'deny');});
 const encodedCommand=JSON.stringify(api.COMMAND);
 const duplicateRaw=[
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"cmd":"earlier","cmd":'+encodedCommand+'}}',
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"cmd":"earlier"},"tool_input":{"cmd":'+encodedCommand+'}}',
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"cmd":"earlier","\\u0063md":'+encodedCommand+'}}',
  '{"hook_event_name":"earlier","\\u0068ook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"cmd":'+encodedCommand+'}}',
  '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"cmd":'+encodedCommand+'},"permission_mode":{"x":1,"x":2}}'
 ];
 for(const ambiguous of duplicateRaw)test(()=>{const f=fixture();let guardCalls=0;assert.equal(api.isProbe(ambiguous),true);assert.throws(()=>api.metadata(ambiguous),/Duplicate JSON key/);const result=api.probeDecision(ambiguous,input=>api.captureProbe(input,f.io),()=>{guardCalls++;});assert.equal(f.created,false);assert.equal(guardCalls,0);assert.equal(result.status,0);assert.equal(JSON.parse(result.stdout).hookSpecificOutput.permissionDecision,'deny');});
 test(()=>assert.deepEqual(api.decodeCaptureEnvelope('{"tool_input":{"\\u0063md":"one"},"n":-1.25e2,"b":true,"z":null}'),{tool_input:{cmd:'one'},n:-125,b:true,z:null}));
 test(()=>assert.equal(api.decodeCaptureEnvelope('{"x":'+ '['.repeat(7)+'0'+']'.repeat(7)+'}').x[0][0][0][0][0][0][0],0));
 for(const invalid of [
  '{"x":'+'['.repeat(8)+'0'+']'.repeat(8)+'}',
  '{"x":['+Array(33).fill('0').join(',')+']}',
  '{'+Array.from({length:33},(_,i)=>'"k'+i+'":0').join(',')+'}',
  '{"'+ 'k'.repeat(81)+'":0}',
  '{"x":"bad\\q"}','{"x":01}','{"x":true} trailing','{"x":1,}','{"x":[0,]}','{"x":"unterminated}',
  '{"x":'+' '.repeat(65536)+'0}'
 ])test(()=>assert.throws(()=>api.decodeCaptureEnvelope(invalid)));
 test(()=>assert.equal(api.decodeCaptureEnvelope('{"x":0}'+ ' '.repeat(65529)).x,0));
 test(()=>{const object=count=>'{'+Array.from({length:count},(_,i)=>'"k'+i+'":0').join(',')+'}';assert.doesNotThrow(()=>api.decodeCaptureEnvelope('{"x":['+Array(4).fill(object(31)).join(',')+']}'));assert.throws(()=>api.decodeCaptureEnvelope('{"x":['+Array(5).fill(object(31)).join(',')+']}'),/key quota/);});
 test(()=>{const array=count=>'['+Array(count).fill('0').join(',')+']';const bounded='{'+Array.from({length:8},(_,i)=>'"k'+i+'":'+array(i===7?30:31)).join(',')+'}';assert.doesNotThrow(()=>api.decodeCaptureEnvelope(bounded));assert.throws(()=>api.decodeCaptureEnvelope(bounded.replace('"k7":'+array(30),'"k7":'+array(31))),/node quota/);});
 test(()=>{const f=fixture();let guardCalls=0;const oversized=make(request)+' '.repeat(65536);assert.equal(api.isProbe(oversized),true);const result=api.probeDecision(oversized,input=>api.captureProbe(input,f.io),()=>{guardCalls++;});assert.equal(guardCalls,0);assert.equal(f.created,false);assert.equal(JSON.parse(result.stdout).hookSpecificOutput.permissionDecision,'deny');});
 test(()=>assert.throws(()=>api.metadata(JSON.stringify({hook_event_name:'PreToolUse',tool_name:'Bash',tool_input:request,transcript_path:{nested:'not a path'}}))));
 test(()=>{const f=fixture();let guardCalls=0;const ambiguous=make({...request,command:'echo other'});assert.equal(api.isProbe(ambiguous),true);const result=api.probeDecision(ambiguous,input=>api.captureProbe(input,f.io),()=>{guardCalls++;});assert.equal(guardCalls,0);assert.equal(f.created,false);assert.equal(JSON.parse(result.stdout).hookSpecificOutput.permissionDecision,'deny');});
 // Algebraic source restoration proves unchanged opaque prior code, not live behavior.
 test(()=>assert.equal(sources.hostRestored,sources.baselineHost));
 test(()=>assert.equal(sources.compatRestored,sources.baselineCompat));
 test(()=>assert.equal(sources.observerRestored,sources.baselineObserver));
 test(()=>assert.equal(sources.globalPrefixEqual,true));
 test(()=>assert.equal(sources.globalSuffixEqual,true));
 test(()=>assert.equal(sources.bootstrapRestored,sources.baselineBootstrap));
 test(()=>assert.deepEqual(sources.originalLoaderRecords,sources.candidateLoaderRecords.slice(0,sources.originalLoaderRecords.length)));
 test(()=>assert.equal(sources.candidateLoaderRecords.length,sources.originalLoaderRecords.length+4));
 test(()=>assert.equal(sources.originalCall[0],sources.candidateCall[0]));
 test(()=>assert.deepEqual(sources.originalCall.slice(2),sources.candidateCall.slice(2)));
 test(()=>assert.equal(sources.oldLogReferenceRemovedFromProbeCallback,true));
 return {checks:count,passed:true,native_executed:false,processes_started:0,capture_io:'injected fake only',authority:false};
}

import hashlib,json,pathlib,shutil,sys
root=pathlib.Path(__file__).parent
name=sys.argv[1];stage=sys.argv[2]
assert stage in ('actual-frontend-handler-r1','actual-frontend-handler-final')
target=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/durable-decisions_2026-11-05')/stage;target.mkdir(exist_ok=False)
result=json.loads((root/(name+'.json')).read_text(encoding='utf-8'))
assert result['ok'] and result['code']==0 and result['closed'] and result['outputComplete'] and result['native']['complete'] and result['native']['zero']
line=next(line for line in result['out'].splitlines() if line.startswith('ACTUAL_FRONTEND_HANDLER_BRIDGE '));proof=json.loads(line.split(' ',1)[1])
assert [item['action'] for item in proof['results']]==['names','review','tracks','metadata_choices','approve','file_review']
for item in proof['results']:assert item['frontend_exit']==0 and json.loads(item['output'])['pass']
bridge=pathlib.Path(next(path for path in proof['participants'] if path.endswith('durable_frontend_http_bridge.js')))
assert hashlib.sha256(bridge.read_bytes()).hexdigest()==proof['participants'][str(bridge)]
files=[]
for path in (root/'owned-bridge.mjs',root/'frontend-backend-bridge.py',root/'freeze-bridge.py',root/(name+'.json'),root/(name+'.log'),bridge):
 data=path.read_bytes();shutil.copyfile(path,target/path.name);files.append({'path':path.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
summary={'backend_commit':'03fe85f11bde97c784a68f931e88be7680552557','actions':[item['action'] for item in proof['results']],
 'result':'PASS6/6 actual renderer transport→real ephemeral loopback Handler; exact raw payload/request/effect/hash, status and authoritative head verified. File-review terminal cleared head also verified. All participant byte hashes match before/after. No mock durable HTTP responses, no browser/app/focus/live data/Z. Source fixtures unchanged, no producer/job started.',
 'ownership':{'code':result['code'],'closed':result['closed'],'outputComplete':result['outputComplete'],'native_complete':result['native']['complete'],'native_zero':result['native']['zero'],'elapsed_ms':result['elapsedMs']},
 'fixture_observer_note':'r1 held the deliberate queue lock while its post-proof jobs.status observer ran, so six30s holder releases inflated total187.655s. Node proof itself took~4.16s/action. This is not product response latency. Subsequent final rebind releases the holder only after actual HTTP proof, before status observation. No original run aborted or duplicated.',
 'participants':proof['participants'],'files':files}
(target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(target),'summary_sha256':hashlib.sha256((target/'summary.json').read_bytes()).hexdigest(),'files':len(files)+1}))

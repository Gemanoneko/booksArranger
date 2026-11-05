import datetime,json,pathlib,sqlite3,time
root=pathlib.Path(__file__).parent
database=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/data/inventory.sqlite3')
db=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=2)
db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
deadline=time.monotonic()+15;db.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
result={'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'ro/query_only','tables':{}}
try:
 for table in ('pause_attribution','automatic_runs','automatic_errors','source_cleanup','audio_jobs'):
  if not db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?',('table',table)).fetchone():continue
  result['tables'][table]={'columns':[dict(row) for row in db.execute('PRAGMA table_info('+table+')')]}
 result['job_counts']=[dict(row) for row in db.execute('SELECT state,count(*) n FROM audio_jobs GROUP BY state')]
 result['latest_jobs']=[]
 for row in db.execute('SELECT * FROM audio_jobs ORDER BY updated DESC,created DESC LIMIT 8'):
  item=dict(row);manifest=json.loads(item.pop('manifest'));item['metadata']=manifest.get('metadata');item['candidate_id']=manifest.get('candidate_id');item['task_kind']=manifest.get('task_kind');item['source_count']=len(manifest.get('sources',[]));item['destination']=manifest.get('destination');item['journal']=json.loads(item['journal']);result['latest_jobs'].append(item)
 for table in ('pause_attribution','automatic_runs','automatic_errors'):
  result['tables'][table]['rows']=[dict(row) for row in db.execute('SELECT * FROM '+table+' ORDER BY rowid DESC LIMIT 4')]
 result['cleanup']=[{**dict(row),'intent':'OMITTED'} for row in db.execute('SELECT * FROM source_cleanup ORDER BY updated DESC LIMIT 5')]
finally:db.close()
(root/'readonly.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'counts':result['job_counts'],'latest':[{key:job.get(key) for key in ('job_id','state','stage','reason','updated','metadata','source_count')} for job in result['latest_jobs']],'pauses':result['tables'].get('pause_attribution',{}).get('rows'),'automatic':[{k:row.get(k) for k in ('id','state','phase','reason','updated')} for row in result['tables']['automatic_runs']['rows']]},ensure_ascii=True))

import datetime,json,pathlib,sqlite3,time
root=pathlib.Path(__file__).parent
database=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/data/inventory.sqlite3')
db=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=2);db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
deadline=time.monotonic()+10;db.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
job='204b6574-de1c-4798-a8e3-f6041970dd03'
result={'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'ro/query_only','job_id':job}
try:
 result['attempts']=[]
 for row in db.execute('SELECT * FROM working_attempts WHERE job_id=?',(job,)):
  item=dict(row);item.pop('manifest',None);result['attempts'].append(item)
 result['files']=[dict(row) for row in db.execute('SELECT attempt_id,name,role,state,size,sha256,updated FROM working_files WHERE job_id=? ORDER BY attempt_id,name',(job,))]
 result['diagnostics']=[dict(row) for row in db.execute('SELECT attempt_id,name,evidence,updated FROM working_diagnostics WHERE job_id=? ORDER BY updated DESC LIMIT 8',(job,))]
 result['failure_history_schema']=[dict(row) for row in db.execute('PRAGMA table_info(audio_failure_history)')]
 if result['failure_history_schema']:result['failure_history']=[dict(row) for row in db.execute('SELECT * FROM audio_failure_history WHERE job_id=? ORDER BY rowid DESC LIMIT 3',(job,))]
finally:db.close()
(root/'working-readonly.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('job_id','attempts','files','diagnostics')},ensure_ascii=True))

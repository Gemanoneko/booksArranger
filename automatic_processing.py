"""One explicitly started, checkpointed public-source Audiobooks pass.
Construction/reconnect/restart never starts inventory, approval or conversion.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid
from scanner import connect
from public_research import PublicClient,PublicResearch,ResearchWait
from source_identity import VERSION,source_gate


def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()

ERROR_LIMIT = 8192
RESEARCH_FAILURE = 'Metadata research failed'
MISSING_FAILURE_DETAILS = 'Failure details were not recorded.'
RETRY_HELP = 'Start automatic processing to retry this book and continue saved work.'

def failure_diagnostic(error,run_id,phase,candidate_id):
    """Keep code locations, never raw traceback lines, paths or arbitrary error text."""
    name=re.sub(r'[^A-Za-z0-9_]','_',type(error).__name__)[:80]
    raw=error.args[0] if error.args and isinstance(error.args[0],str) else ''
    message='Exception message redacted; inspect the recorded code location'
    # These structural built-in messages contain types/operations, not source values.
    structural=r"'(?:NoneType|dict|list|tuple|str|int|float|bool)' object (?:is not iterable|is not subscriptable|has no attribute '(?:get|items|values|keys|append|extend|split|strip)')"
    if type(error) in (TypeError,AttributeError) and re.fullmatch(structural,raw):message=raw
    elif isinstance(error,sqlite3.Error):
        code=getattr(error,'sqlite_errorname','')
        if isinstance(code,str) and re.fullmatch(r'SQLITE_[A-Z0-9_]{1,60}',code):message='Database error '+code
        else:message='Database operation failed; exception text redacted'
    elif isinstance(error,OSError) and type(error.errno) is int:message='Operating system error '+str(error.errno)
    frames=[];tb=error.__traceback__;base=Path(__file__).resolve().parent
    while tb is not None:
        code=tb.tb_frame.f_code
        try:
            file=Path(code.co_filename).resolve().relative_to(base).as_posix()
            if not re.fullmatch(r'[A-Za-z0-9_./-]{1,160}\.py',file):file='<external>'
        except (OSError,ValueError):file='<external>'
        frames.append({'file':file,'line':tb.tb_lineno,'function':re.sub(r'[^A-Za-z0-9_<>]','_',code.co_name)[:80]})
        frames=frames[-8:];tb=tb.tb_next
    result={'id':str(uuid.uuid4()),'run_id':run_id,'phase':phase,'candidate_id':candidate_id,'created_utc':stamp(),
            'exception_class':name,'message':message,'message_prefix_sha256':hashlib.sha256(raw[:4096].encode('utf-8',errors='replace')).hexdigest(),
            'message_truncated':len(raw)>4096,'stack':frames}
    if len(json.dumps(result,ensure_ascii=False).encode('utf-8'))>ERROR_LIMIT:raise ValueError('Failure diagnostic exceeds its bound')
    return result

def candidate_job_exists(db,identity):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audio_jobs'").fetchone():return False
    return bool(db.execute("SELECT 1 FROM audio_jobs WHERE json_extract(manifest,'$.candidate_id')=? LIMIT 1",(identity,)).fetchone())

def research_retry(run):
    if not run or run['state']!='Needs attention' or run['phase']!='research':return False
    try:
        pending=json.loads(run['checkpoint']).get('pending')
        return isinstance(pending,list) and bool(pending) and all(isinstance(value,str) and str(uuid.UUID(value))==value for value in pending)
    except (ValueError,TypeError,AttributeError):return False

class AutomaticProcessing:
    def __init__(self,merge,research=None,clock=time.time):
        self.merge=merge;self.inventory=merge.inventory;self.database=self.inventory.database
        self.research=research or PublicResearch(PublicClient(self.database))
        self.lock=threading.RLock();self.stop_event=threading.Event();self.thread=None;self.current=None;self.closed=False;self.volatile_failure=None;self.clock=clock;self.next_retry_at=None
        with connect(self.database) as db:
            __import__('groups').setup(db)
            db.execute('CREATE TABLE IF NOT EXISTS automatic_runs(id TEXT PRIMARY KEY,state TEXT,phase TEXT,checkpoint TEXT,reason TEXT,created TEXT,updated TEXT,restart_paused INTEGER DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS automatic_manual_drafts(id TEXT PRIMARY KEY,revision INTEGER,expires REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS automatic_candidates(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,state TEXT,result TEXT,retry_at REAL,attempted TEXT,matcher_version TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS automatic_errors(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,created TEXT NOT NULL,diagnostic TEXT NOT NULL)')
            prior=db.execute('SELECT * FROM automatic_runs ORDER BY created DESC LIMIT 1').fetchone()
            if prior and research_retry(dict(prior)):
                failed=json.loads(prior['checkpoint'])['pending'][0]
                failure_reason='Automatic processing error' if candidate_job_exists(db,failed) else RESEARCH_FAILURE
                db.execute("UPDATE automatic_candidates SET state='Needs attention',result=?,retry_at=NULL WHERE id=? AND state='Researching'",
                    (json.dumps({'reasons':[failure_reason,MISSING_FAILURE_DETAILS],'failure_run_id':prior['id']}),failed))
            db.execute("UPDATE automatic_runs SET state='Paused',reason='Paused after server restart — start to continue saved work',restart_paused=1 WHERE state IN ('Running','Stopping')")
            db.execute("UPDATE automatic_candidates SET state='Pending' WHERE state='Researching'")
    def _run_row(self):
        with connect(self.database) as db:
            r=db.execute('SELECT * FROM automatic_runs ORDER BY created DESC LIMIT 1').fetchone()
        return dict(r) if r else None
    def _update(self,id,**fields):
        fields['updated']=stamp()
        with connect(self.database) as db:db.execute('UPDATE automatic_runs SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',(*fields.values(),id))
    def _record(self,row,state,result=None,retry_at=None):
        with connect(self.database) as db:db.execute('INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',(row['id'],row['revision'],row['fingerprint'],state,json.dumps(result or {},ensure_ascii=False),retry_at,stamp(),VERSION))
    def candidate(self,row):
        with connect(self.database) as db:r=db.execute('SELECT * FROM automatic_candidates WHERE id=?',(row['id'],)).fetchone()
        if not r or r['revision']!=row['revision'] or r['fingerprint']!=row['fingerprint']:return None
        result=json.loads(r['result'])
        if self.volatile_failure and self.volatile_failure['diagnostic']['candidate_id']==row['id']:
            r=dict(r);r['state']='Needs attention';result=self.volatile_failure['candidate_result']
        return {'state':r['state'],'reasons':result.get('reasons',[]),'sources':result.get('sources',[]),'wait':result.get('wait'),'attempted_utc':r['attempted'],'retry_at':r['retry_at']}
    def _refresh_wait(self,row,previous):
        if not previous or previous['state']!='Waiting for source' or not previous.get('wait'):return previous
        revised=self.research.client.retry_wait(previous['wait'])
        if revised==previous['wait']:return previous
        with connect(self.database) as db:
            record=db.execute("SELECT result FROM automatic_candidates WHERE id=? AND revision=? AND fingerprint=? AND state='Waiting for source'",(row['id'],row['revision'],row['fingerprint'])).fetchone()
            if record:
                result=json.loads(record['result']);result['wait']=revised
                db.execute("UPDATE automatic_candidates SET result=?,retry_at=? WHERE id=? AND revision=? AND fingerprint=? AND state='Waiting for source'",(json.dumps(result,ensure_ascii=False),revised['retry_at'],row['id'],row['revision'],row['fingerprint']))
        return self.candidate(row)
    def status(self):
        run=self._run_row();counts={'researching':0,'waiting':0,'held':0}
        with connect(self.database) as db:
            for r in db.execute('SELECT a.state,count(*) n FROM automatic_candidates a JOIN book_groups g ON g.id=a.id AND g.revision=a.revision AND g.fingerprint=a.fingerprint WHERE g.superseded=0 GROUP BY a.state'):
                if r['state']=='Researching':counts['researching']+=r['n']
                elif r['state']=='Waiting for source':counts['waiting']+=r['n']
                elif r['state']=='Held':counts['held']+=r['n']
        state=run['state'] if run else 'Idle'
        with connect(self.database) as db:
            failure=db.execute('SELECT diagnostic FROM automatic_errors WHERE run_id=? ORDER BY created DESC LIMIT 1',(run['id'] if run else '',)).fetchone()
        diagnostic=json.loads(failure['diagnostic']) if failure else None
        if self.volatile_failure:
            state='Needs attention';diagnostic=self.volatile_failure['diagnostic'];counts['researching']=0
        active=state in ('Running','Stopping')
        armed=state=='Running' and self.next_retry_at is not None and not self.stop_event.is_set() and not self.closed
        return {'state':state,'phase':'waiting' if armed else run['phase'] if run else 'idle','run_id':run['id'] if run else None,'reason':self.volatile_failure['reason'] if self.volatile_failure else run['reason'] if run else '',
                'restart_paused':bool(run and run['restart_paused']),'failure':diagnostic,'failure_durable':bool(diagnostic and not self.volatile_failure),'retry_help':RETRY_HELP if research_retry(run) and not self.volatile_failure else '',
                'can_start':not self.closed and not active and not self.volatile_failure,'can_stop':active and state!='Stopping','research':counts,'current':dict(self.current) if self.current else None,
                'automatic_retry_enabled':armed,'next_retry_at':self.next_retry_at if armed else None}
    def start(self):
        with self.lock:
            if self.closed:raise ValueError('Automatic processing is closed')
            if self.volatile_failure:raise ValueError('Failure checkpoint could not be saved; automatic processing remains stopped')
            if self.thread and self.thread.is_alive():return self.status()
            self.merge._no_scan()
            jobs=self.merge.state()
            if jobs['state'] in ('Running','Pausing'):raise ValueError('Pause existing audiobook work before automatic discovery')
            run=self._run_row()
            if not run or run['state']=='Completed' or run['state']=='Needs attention' and not research_retry(run):
                id=str(uuid.uuid4());now=stamp();run={'id':id,'phase':'discovery','checkpoint':'{}'}
                with connect(self.database) as db:db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(id,'Running','discovery','{}','',now,now))
            else:self._update(run['id'],state='Running',reason='',restart_paused=0)
            self.stop_event.clear()
            self.thread=threading.Thread(target=self._work,args=(run['id'],),name='BooksArrangerAutomatic',daemon=False);self.thread.start()
        return self.status()
    def stop(self,force=False):
        with self.lock:
            run=self._run_row()
            if not force and (not run or run['state'] not in ('Running','Stopping')):return self.status()
            if run and run['state']=='Running':self._update(run['id'],state='Stopping',reason='Stopping automatic processing — saving pending work')
            self.stop_event.set();self.next_retry_at=None
        self.inventory.stop();self.merge.pause()
        return self.status()
    def close(self,timeout=30):
        self.closed=True;self.stop(force=True);thread=self.thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout)
            if thread.is_alive():raise TimeoutError('Automatic processing still closing at safe checkpoint')
    def _progress(self,title,source,stage):
        self.current={'title':title,'source':source,'stage':stage}
    def _idle_jobs(self):
        state=self.merge.state()
        return state['state'] not in ('Running','Pausing') and not state.get('queued',0) and not state.get('cleanup_active',False)
    def draft(self,id,revision,active):
        if type(active) is not bool:raise ValueError('Draft activity must be an explicit boolean')
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT revision FROM book_groups WHERE id=? AND root=? AND superseded=0',(id,self.inventory.roots['Audiobooks'])).fetchone()
            if not row or row['revision']!=revision:raise ValueError('Candidate changed; reload before editing')
            if active:db.execute('INSERT OR REPLACE INTO automatic_manual_drafts VALUES(?,?,?)',(id,revision,time.time()+300))
            else:db.execute('DELETE FROM automatic_manual_drafts WHERE id=?',(id,))
        return {'protected':active,'id':id,'revision':revision}
    def manual_draft(self,row):
        with connect(self.database) as db:
            draft=db.execute('SELECT * FROM automatic_manual_drafts WHERE id=? AND expires>?',(row['id'],time.time())).fetchone()
        if draft:return True
        return self._manual_draft(row)
    def _manual_draft(self,row):
        ctx=self.merge.reviews._context(row)
        return bool(row.get('review') and not (ctx.get('automatic_approval') or ctx.get('automatic_pending'))) or bool(ctx.get('manual_draft_active'))
    def _failure(self,id,error,phase,identity,row,research_failed):
        diagnostic=failure_diagnostic(error,id,phase,identity)
        reason='Automatic pass could not continue; saved source and job evidence preserved'
        title=re.sub(r'[\x00-\x1f\x7f]',' ',str(row.get('title_clue','')))[:120] if row else ''
        result={'reasons':[RESEARCH_FAILURE if research_failed else 'Automatic processing error','Failure details: '+diagnostic['exception_class']+': '+diagnostic['message']],'failure_run_id':id,'failure_id':diagnostic['id']}
        self.current=None
        self.next_retry_at=None
        self.volatile_failure={'diagnostic':diagnostic,'reason':reason,'candidate_result':result}
        try:
            with connect(self.database) as db:
                if research_failed and row and not candidate_job_exists(db,row['id']):
                    reason='An app error stopped automatic processing while researching '+title+'. Source files for this book were preserved.'
                db.execute('INSERT INTO automatic_errors VALUES(?,?,?,?)',(diagnostic['id'],id,diagnostic['created_utc'],json.dumps(diagnostic)))
                if row:
                    db.execute("UPDATE automatic_candidates SET state='Needs attention',result=?,retry_at=NULL WHERE id=? AND revision=? AND fingerprint=? AND state='Researching'",
                        (json.dumps(result),row['id'],row['revision'],row['fingerprint']))
                db.execute("UPDATE automatic_runs SET state='Needs attention',reason=?,updated=? WHERE id=?",(reason,stamp(),id))
            self.volatile_failure=None
        except (OSError,sqlite3.Error) as persistence_error:
            # No durable success claim and no retry when the checkpoint itself failed.
            diagnostic['persistence_error_class']=type(persistence_error).__name__[:80]
            self.volatile_failure['reason']='Retry progress could not be saved; Start is unavailable.'

    def _work(self,id):
        row=None;identity=None;phase='unknown';research_failed=False;checkpoint={}
        try:
            run=self._run_row();checkpoint=json.loads(run['checkpoint']);phase=run['phase']
            if phase=='discovery':
                # Existing queued jobs finish before a scan; never scan while encoding/cleanup runs.
                if self.merge.state().get('queued'):
                    self.merge.resume()
                    while not self._idle_jobs():
                        if self.stop_event.wait(.2):raise InterruptedError()
                saved=self.inventory.status('Audiobooks')
                self.inventory.launch('Audiobooks',resume=saved['state'] in ('stopped','offline','failed'))
                while self.inventory.worker and self.inventory.worker.is_alive():
                    if self.stop_event.wait(.2):self.inventory.stop();self.inventory.worker.join(20);raise InterruptedError()
                if self.inventory.status('Audiobooks')['state'] not in ('completed',):
                    raise ValueError('Discovery incomplete or has read errors; saved progress preserved')
                candidates=self.inventory.candidates('Audiobooks',limit=1000000)['rows']
                checkpoint={'pending':[r['id'] for r in candidates],'done':[]}
                self._update(id,phase='research',checkpoint=json.dumps(checkpoint));phase='research'
            else:
                # Resume saved queued work; the immutable queue already owns each manifest.
                if self.merge.state().get('queued'):self.merge.resume()
            checkpoint['pending']=list(dict.fromkeys(checkpoint.get('pending',[])+checkpoint.get('deferred',[])))
            checkpoint['done']=list(dict.fromkeys(checkpoint.get('done',[])))
            checkpoint['deferred']=[];deferred=checkpoint['deferred']
            while checkpoint.get('pending') or deferred:
                if self.stop_event.is_set():raise InterruptedError()
                if not checkpoint['pending']:
                    row=None;identity=None;self.current=None;phase='research'
                    # Let already admitted books and required cleanup drain before waiting.
                    while not self._idle_jobs():
                        if self.stop_event.wait(.2):raise InterruptedError()
                        if self.merge.state()['state']=='Paused':raise InterruptedError()
                    checkpoint['pending']=list(dict.fromkeys(deferred));deferred.clear()
                    with connect(self.database) as db:
                        times={r['id']:r['retry_at'] for r in db.execute("SELECT id,retry_at FROM automatic_candidates WHERE state='Waiting for source'")}
                    next_at=min(times.get(candidate) or self.clock() for candidate in checkpoint['pending'])
                    self._update(id,phase='research',checkpoint=json.dumps(checkpoint),reason='Waiting for metadata sources; saved research retries automatically.')
                    self.next_retry_at=next_at
                    try:
                        while next_at>self.clock():
                            if self.stop_event.wait(min(60,next_at-self.clock())):raise InterruptedError()
                        if self.stop_event.is_set():raise InterruptedError()
                    finally:self.next_retry_at=None
                    self._update(id,reason='')
                identity=checkpoint['pending'][0]
                try:row=self.merge.reviews._row('Audiobooks',identity)
                except ValueError:
                    checkpoint['pending'].pop(0);self._update(id,checkpoint=json.dumps(checkpoint));continue
                job=self.merge.candidate_status(identity)
                if job:
                    checkpoint['pending'].pop(0)
                    if identity not in checkpoint['done']:checkpoint['done'].append(identity)
                    self._update(id,checkpoint=json.dumps(checkpoint));continue
                previous=self._refresh_wait(row,self.candidate(row))
                if previous and previous['state'] in ('Held','Waiting for source') and previous.get('retry_at') and previous['retry_at']>self.clock():
                    # Deferred source opportunities stay owned by this authorized worker.
                    if previous['state']=='Waiting for source':deferred.append(identity)
                    checkpoint['pending'].pop(0);continue
                if self.manual_draft(row):
                    self._record(row,'Held',{'reasons':['Manual draft retained']});checkpoint['pending'].pop(0);self._update(id,checkpoint=json.dumps(checkpoint));continue
                self._update(id,checkpoint=json.dumps(checkpoint))
                self._record(row,'Researching');self._progress(row['title_clue'],'Public sources','Researching work identity')
                try:
                    research_failed=True
                    result=self.research.lookup(row,self.inventory.roots['Audiobooks'],self.stop_event,lambda source,stage:self._progress(row['title_clue'],source,stage))
                except ValueError:
                    # Unsupported input or malformed public evidence holds only this candidate.
                    result={'sources':[],'reasons':['Public research input or evidence exceeds supported limits']}
                research_failed=False
                if self.stop_event.is_set():raise InterruptedError()
                if result.get('reasons'):
                    wait=result.get('wait');state='Waiting for source' if wait else 'Held'
                    self._record(row,state,result,wait.get('retry_at') if wait else self.clock()+7*86400)
                    if wait:deferred.append(identity)
                else:
                    try:
                        fresh,job_id=self.merge.approve_automatic(row,result,self.stop_event,self.research.client)
                        self._record(fresh,'Queued',result);result['job_id']=job_id
                    except InterruptedError:raise
                    except ResearchWait as wait:
                        if self.stop_event.is_set():raise InterruptedError()
                        try:fresh=self.merge.reviews._row('Audiobooks',identity)
                        except ValueError:fresh=row
                        result['reasons']=['Cover source unavailable'];result['wait']={'source':wait.source,'reason':wait.reason,'retry_at':wait.retry_at,'kind':wait.kind,'scope':wait.scope}
                        self._record(fresh,'Waiting for source',result,wait.retry_at);deferred.append(identity)
                    except (ValueError,OSError) as error:
                        if self.stop_event.is_set():raise InterruptedError()
                        try:fresh=self.merge.reviews._row('Audiobooks',identity)
                        except ValueError:fresh=row
                        result['reasons']=[str(error)[:300] or 'Automatic source checks failed'];self._record(fresh,'Held',result,self.clock()+7*86400)
                checkpoint['pending'].pop(0)
                if identity not in checkpoint['done']:checkpoint['done'].append(identity)
                self._update(id,checkpoint=json.dumps(checkpoint))
            row=None;identity=None;phase='conversion';self.current=None;self._update(id,phase='conversion')
            while not self._idle_jobs():
                if self.stop_event.wait(.2):raise InterruptedError()
                if self.merge.state()['state']=='Paused':raise InterruptedError()
            if self.stop_event.is_set():raise InterruptedError()
            if self.merge.state().get('failed'):
                self._update(id,state='Needs attention',phase='conversion',reason='Some audiobook jobs need attention; verified outputs and pending work are preserved')
            else:self._update(id,state='Completed',phase='completed',reason='')
        except InterruptedError:
            self.current=None;self.next_retry_at=None
            # Report Paused only after both scan and owned converter/cleanup have stopped.
            self.inventory.stop();self.merge.pause()
            while self.inventory.worker and self.inventory.worker.is_alive():self.inventory.worker.join(.2)
            while self.merge.state()['state']=='Pausing':time.sleep(.2)
            with connect(self.database) as db:db.execute("UPDATE automatic_candidates SET state='Pending' WHERE state='Researching'")
            self._update(id,state='Paused',checkpoint=json.dumps(checkpoint),reason='Paused — pending work saved')
        except Exception as error:
            self._failure(id,error,phase,identity,row,research_failed)

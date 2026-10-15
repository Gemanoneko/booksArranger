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
from sqlite_retry import transaction
from public_research import PublicClient,PublicResearch,ResearchWait,RESEARCH_VERSION
from source_identity import VERSION,source_gate


def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()

ERROR_LIMIT = 8192
RESEARCH_FAILURE = 'Metadata research failed'
MISSING_FAILURE_DETAILS = 'Failure details were not recorded.'
RETRY_HELP = 'Start automatic processing to retry this book and continue saved work.'
# A locally identified book whose optional gap sources are cooling down waits only while
# the converter already has work, and at most this many queue drains; then it proceeds
# without the optional fields (Sergei decision 2026-10-12: gaps never block a book).
GAP_DEFER_LIMIT = 3
GAP_DEFER_REASON = 'Optional metadata sources cooling down; converter busy, book admitted when it is free'

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
        # Retry this idempotent checkpoint transaction only. Never replay the
        # enclosing research/admission/publication operation after a database error.
        worker=threading.current_thread() is self.thread
        cancel=worker and fields.get('state')!='Paused'
        # A worker can finish Paused after Stop reads Running. Never overwrite
        # that committed checkpoint using the caller's stale state snapshot.
        predicate=" AND state='Running'" if fields.get('state')=='Stopping' else ''
        transaction(self.database,lambda db:db.execute('UPDATE automatic_runs SET '+','.join(k+'=?' for k in fields)+' WHERE id=?'+predicate,(*fields.values(),id)),self.stop_event if cancel else None)
    def _record(self,row,state,result=None,retry_at=None):
        # Replay only this local candidate write. Each BEGIN IMMEDIATE retry
        # rereads committed history; never mutate a prior attempt's input/result.
        supplied=dict(result or {},research_version=RESEARCH_VERSION)
        def persist(db):
            recorded=dict(supplied)
            old=db.execute('SELECT revision,fingerprint,state,result FROM automatic_candidates WHERE id=?',(row['id'],)).fetchone()
            prior=json.loads(old['result']) if old else {}
            attempt=prior.get('research_attempt',0)
            history=prior.get('research_history',[])
            if old and (old['revision']!=row['revision'] or old['fingerprint']!=row['fingerprint']):
                history=history+[{'attempt':attempt,'at':stamp(),'state':old['state'],'revision':old['revision'],'fingerprint':old['fingerprint'],
                    'reasons':prior.get('reasons',[])[:8],'sources':[{'url':s.get('url'),'sha256':s.get('sha256'),'kind':s.get('kind')} for s in prior.get('sources',[])[:20]]}]
            if old and old['fingerprint']==row['fingerprint'] and 'source_refresh' not in recorded and prior.get('source_refresh'):
                recorded['source_refresh']=prior['source_refresh']
            if state in ('Held','Waiting for source','Queued'):
                attempt+=1
                history=history+[{'attempt':attempt,'at':stamp(),'state':state,'reasons':recorded.get('reasons',[])[:8],'sources':[{'url':s.get('url'),'sha256':s.get('sha256'),'kind':s.get('kind')} for s in recorded.get('sources',[])[:20]]}]
            recorded['research_attempt']=attempt;recorded['research_history']=history[-20:]
            db.execute('INSERT OR REPLACE INTO automatic_candidates VALUES(?,?,?,?,?,?,?,?)',(row['id'],row['revision'],row['fingerprint'],state,json.dumps(recorded,ensure_ascii=False),retry_at,stamp(),VERSION))
        worker=threading.current_thread() is self.thread
        transaction(self.database,persist,self.stop_event if worker else None)
    def _paused_checkpoint(self,id,checkpoint):
        encoded=json.dumps(checkpoint);updated=stamp()
        def persist(db):
            db.execute("UPDATE automatic_candidates SET state='Pending' WHERE state='Researching'")
            db.execute("UPDATE automatic_runs SET state='Paused',checkpoint=?,reason='Paused — pending work saved',updated=? WHERE id=?",(encoded,updated,id))
        # Stop is already set: finish this atomic save, never restart processing.
        transaction(self.database,persist)
    def candidate(self,row):
        with connect(self.database) as db:r=db.execute('SELECT * FROM automatic_candidates WHERE id=?',(row['id'],)).fetchone()
        if not r or r['revision']!=row['revision'] or r['fingerprint']!=row['fingerprint']:return None
        result=json.loads(r['result'])
        if self.volatile_failure and self.volatile_failure['diagnostic']['candidate_id']==row['id']:
            r=dict(r);r['state']='Needs attention';result=self.volatile_failure['candidate_result']
        return {'state':r['state'],'research_version':result.get('research_version'),'reasons':result.get('reasons',[]),'sources':result.get('sources',[]),'wait':result.get('wait'),'attempted_utc':r['attempted'],'retry_at':r['retry_at'],'research_attempt':result.get('research_attempt',0),'research_history':result.get('research_history',[]),'metadata_facts':result.get('metadata_facts'),'duplicate_review':result.get('duplicate_review'),'gap_deferrals':result.get('gap_deferrals',0)}
    def _refresh_wait(self,row,previous):
        if previous and previous['state']=='Held' and previous.get('research_version')!=RESEARCH_VERSION:return dict(previous,retry_at=None)
        if not previous or previous['state']!='Waiting for source' or not previous.get('wait'):return previous
        if previous.get('research_version')!=RESEARCH_VERSION:
            # New independent hosts get one opportunity; the old host ledger stays intact.
            return dict(previous,retry_at=None)
        revised=self.research.client.retry_wait(previous['wait'])
        if revised==previous['wait']:return previous
        with connect(self.database) as db:
            record=db.execute("SELECT result FROM automatic_candidates WHERE id=? AND revision=? AND fingerprint=? AND state='Waiting for source'",(row['id'],row['revision'],row['fingerprint'])).fetchone()
            if record:
                result=json.loads(record['result']);result['wait']=revised
                db.execute("UPDATE automatic_candidates SET result=?,retry_at=? WHERE id=? AND revision=? AND fingerprint=? AND state='Waiting for source'",(json.dumps(result,ensure_ascii=False),revised['retry_at'],row['id'],row['revision'],row['fingerprint']))
        return self.candidate(row)
    def _start_block_reason(self,state,*,jobs=None,scanning=None,server_closing=False):
        # This is a read-only snapshot, with no new lock acquisition. In
        # particular, never take merge/scanner locks while holding self.lock.
        if self.closed or server_closing:return 'The local server is stopping or stopped. Start is unavailable.'
        if self.volatile_failure:return 'Automatic processing cannot restart because its failure record could not be saved.'
        if state=='Stopping':return 'Automatic processing is stopping. Wait for it to finish stopping.'
        if state=='Running' or self.thread and self.thread.is_alive():return 'Automatic processing is already running.'
        if scanning is None:
            worker=getattr(self.inventory,'worker',None)
            scanning=bool(worker and worker.is_alive())
        if scanning:return 'Discovery is in progress. Wait for it to stop before starting automatic processing.'
        job_state=jobs.get('state') if isinstance(jobs,dict) else None
        if job_state=='Running':return 'Audiobook conversion is running. Pause audiobook jobs before starting automatic processing.'
        if job_state=='Pausing':return 'Audiobook jobs are pausing. Wait for them to pause before starting automatic processing.'
        if job_state not in ('Idle','Paused','Completed','Needs attention'):
            return 'Start availability is unknown. Waiting for the local server.'
        return ''
    def status(self,*,jobs=None,scanning=None,server_closing=False):
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
        block=self._start_block_reason(state,jobs=jobs,scanning=scanning,server_closing=server_closing)
        return {'state':state,'phase':'waiting' if armed else run['phase'] if run else 'idle','run_id':run['id'] if run else None,'reason':self.volatile_failure['reason'] if self.volatile_failure else run['reason'] if run else '',
                'restart_paused':bool(run and run['restart_paused']),'failure':diagnostic,'failure_durable':bool(diagnostic and not self.volatile_failure),'retry_help':RETRY_HELP if research_retry(run) and not self.volatile_failure else '',
                'can_start':not bool(block),'start_block_reason':block,'can_stop':active and state!='Stopping','research':counts,'current':dict(self.current) if self.current else None,
                'automatic_retry_enabled':armed,'next_retry_at':self.next_retry_at if armed else None}
    def start(self,*,server_closing=False):
        with self.lock:
            if server_closing:raise ValueError('The local server is stopping or stopped. Start is unavailable.')
            if self.closed:raise ValueError('Automatic processing is closed')
            if self.volatile_failure:raise ValueError('Failure checkpoint could not be saved; automatic processing remains stopped')
            if self.thread and self.thread.is_alive():return self.status()
            run=self._run_row()
            scanner=getattr(self.inventory,'worker',None)
            if scanner and scanner.is_alive():
                raise ValueError(self._start_block_reason(run['state'] if run else 'Idle',scanning=True,server_closing=server_closing))
            block=self._start_block_reason(run['state'] if run else 'Idle',jobs=self.merge.state(),server_closing=server_closing)
            if block:raise ValueError(block)
            self.merge._no_scan()  # Recheck discovery immediately before admission.
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
    def _add_current_candidates(self,checkpoint):
        """Regrouping (split books, v0.15.0) replaces candidates with new ids; a saved run adds
        every current candidate it has not seen, so new books are researched without a new
        discovery pass. Superseded ids are skipped where they come up (candidate no longer current)."""
        seen=set(checkpoint.get('pending',[]))|set(checkpoint.get('done',[]))|set(checkpoint.get('deferred',[]))
        listing=getattr(self.inventory,'candidates',None)
        page=listing('Audiobooks',limit=1000000) if callable(listing) else None
        # An inventory without a candidate listing (private test stubs) adds nothing.
        if not isinstance(page,dict) or not isinstance(page.get('rows'),list):return 0
        current=[r['id'] for r in page['rows']]
        added=[identity for identity in current if identity not in seen]
        checkpoint['pending']=list(checkpoint.get('pending',[]))+added
        return len(added)

    def _refresh_observed_sources(self,row,previous):
        """Only stale/unreadable, unprotected observed members are refreshed."""
        stale={'Source files changed','Source embedded identity or order evidence changed','Source changed — review required','Source files unavailable or unreadable'}
        needs=any(m.get('error') or m.get('missing') for m in row['members']) or bool(stale.intersection((previous or {}).get('reasons',[])))
        if not needs:return None
        adapter=getattr(self.inventory,'refresh_candidate_sources',None)
        if adapter is None:return {'state':'held','reason':'Observed source inventory refresh is unavailable'}
        receipt=adapter('Audiobooks',row['id'],row['revision'],stop=self.stop_event,force=True)
        if self.stop_event.is_set():raise InterruptedError()
        if receipt.get('state') not in ('held','unchanged','refreshed'):raise ValueError('Unsupported source refresh result')
        if receipt['state']=='held':return receipt
        old_paths=sorted(m['path'] for m in row['members'])
        if receipt.get('old_revision')!=row['revision'] or receipt.get('old_fingerprint')!=row['fingerprint'] or sorted(receipt.get('observed_paths',[]))!=old_paths:
            raise ValueError('Observed source refresh identity changed')
        try:fresh=self.merge.reviews._row('Audiobooks',row['id'])
        except ValueError:
            # Refresh can expose proven independent groups. Consider only the exact
            # refreshed observed paths; do not expand discovery or inherit approval.
            with connect(self.database) as db:
                marks=','.join('?' for _ in old_paths)
                groups=db.execute(f"SELECT DISTINCT g.* FROM book_groups g,json_each(g.evidence,'$.members') m WHERE g.root=? AND g.superseded=0 AND json_extract(m.value,'$.path') IN ({marks})",(self.inventory.roots['Audiobooks'],*old_paths)).fetchall()
            covered=[];replacements=[]
            for group in groups:
                members=json.loads(group['evidence'])['members'];paths=[m['path'] for m in members]
                if group['approved'] or group['review'] or any(p not in old_paths for p in paths):return {'state':'held','reason':'Refreshed source membership requires separate protected evidence'}
                covered.extend(paths);replacements.append(group['id'])
            if sorted(covered)!=old_paths or len(set(covered))!=len(covered):return {'state':'held','reason':'Refreshed source membership is incomplete or overlapping'}
            return receipt|{'replacement_ids':replacements}
        if sorted(m['path'] for m in fresh['members'])!=old_paths:return {'state':'held','reason':'Refreshed source membership changed'}
        return receipt|{'row':fresh}

    def _failure(self,id,error,phase,identity,row,research_failed):
        diagnostic=failure_diagnostic(error,id,phase,identity)
        reason='Automatic pass could not continue; saved source and job evidence preserved'
        title=re.sub(r'[\x00-\x1f\x7f]',' ',str(row.get('title_clue','')))[:120] if row else ''
        result={'reasons':[RESEARCH_FAILURE if research_failed else 'Automatic processing error','Failure details: '+diagnostic['exception_class']+': '+diagnostic['message']],'failure_run_id':id,'failure_id':diagnostic['id']}
        self.current=None
        self.next_retry_at=None
        self.volatile_failure={'diagnostic':diagnostic,'reason':reason,'candidate_result':result}
        try:
            def persist(db):
                nonlocal reason
                if research_failed and row and not candidate_job_exists(db,row['id']):
                    reason='An app error stopped automatic processing while researching '+title+'. Source files for this book were preserved.'
                db.execute('INSERT INTO automatic_errors VALUES(?,?,?,?)',(diagnostic['id'],id,diagnostic['created_utc'],json.dumps(diagnostic)))
                if row:
                    db.execute("UPDATE automatic_candidates SET state='Needs attention',result=?,retry_at=NULL WHERE id=? AND revision=? AND fingerprint=? AND state='Researching'",
                        (json.dumps(result),row['id'],row['revision'],row['fingerprint']))
                db.execute("UPDATE automatic_runs SET state='Needs attention',reason=?,updated=? WHERE id=?",(reason,stamp(),id))
            transaction(self.database,persist)
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
                if self.merge.state().get('queued') or self.merge.state().get('postprocessing_pending'):
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
                if self.merge.state().get('queued') or self.merge.state().get('postprocessing_pending'):self.merge.resume()
                if self._add_current_candidates(checkpoint):
                    self._update(id,phase='research',checkpoint=json.dumps(checkpoint));phase='research'
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
                    self._add_current_candidates(checkpoint)
                    with connect(self.database) as db:
                        times={r['id']:r['retry_at'] for r in db.execute("SELECT id,retry_at FROM automatic_candidates WHERE state IN ('Waiting for source','Held')")}
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
                    if job.get('state')=='Output needs attention':
                        decision=self.merge.retry_automatic_job(job['job_id'],self.clock())
                        if decision.get('retryable'):
                            self._record(row,'Held',{'reasons':['Saved audiobook I/O failure; prior attempt preserved'],'job_retry':decision},decision['retry_at']);deferred.append(identity)
                    elif job.get('state')=='Audiobook created':self._record(row,'Queued',{'reasons':[]})
                    checkpoint['pending'].pop(0)
                    if identity not in checkpoint['done']:checkpoint['done'].append(identity)
                    self._update(id,checkpoint=json.dumps(checkpoint));continue
                previous=self._refresh_wait(row,self.candidate(row))
                if previous and previous['state'] in ('Held','Waiting for source') and previous.get('retry_at') and previous['retry_at']>self.clock():
                    # Deferred source opportunities stay owned by this authorized worker.
                    deferred.append(identity)
                    checkpoint['pending'].pop(0);continue
                if self.manual_draft(row):
                    self._record(row,'Held',{'reasons':['Manual draft retained']},self.clock()+300);deferred.append(identity);checkpoint['pending'].pop(0);self._update(id,checkpoint=json.dumps(checkpoint));continue
                refreshed=self._refresh_observed_sources(row,previous)
                if refreshed:
                    compact={k:v for k,v in refreshed.items() if k not in ('row','replacement_ids')}
                    compact['at_utc']=stamp()
                    if refreshed['state']=='held':
                        self._record(row,'Held',{'reasons':[refreshed.get('reason') or 'Observed sources remain unavailable'],'source_refresh':compact},self.clock()+900)
                        deferred.append(identity);checkpoint['pending'].pop(0);self._update(id,checkpoint=json.dumps(checkpoint));continue
                    if 'replacement_ids' in refreshed:
                        self._record(row,'Held',{'reasons':['Refreshed observed sources split into independent candidates'],'source_refresh':compact},self.clock()+900)
                        checkpoint['pending'].extend(candidate for candidate in refreshed['replacement_ids'] if candidate not in checkpoint['pending'])
                        checkpoint['pending'].pop(0);self._update(id,checkpoint=json.dumps(checkpoint));continue
                    row=refreshed['row']
                    self._record(row,'Pending',{'reasons':[],'source_refresh':compact})
                    previous=self.candidate(row)
                self._update(id,checkpoint=json.dumps(checkpoint))
                self._record(row,'Researching');self._progress(row['title_clue'],'Public sources','Researching work identity')
                try:
                    research_failed=True
                    row['_research_attempt']=previous.get('research_attempt',0) if previous else 0
                    result=self.research.lookup(row,self.inventory.roots['Audiobooks'],self.stop_event,lambda source,stage:self._progress(row['title_clue'],source,stage))
                except ValueError:
                    # Unsupported input or malformed public evidence holds only this candidate.
                    result={'sources':[],'reasons':['Public research input or evidence exceeds supported limits']}
                research_failed=False
                if self.stop_event.is_set():raise InterruptedError()
                deferrals=(previous or {}).get('gap_deferrals',0)
                if not result.get('reasons') and result.get('gap_wait') and deferrals<GAP_DEFER_LIMIT and not self._idle_jobs():
                    # The converter has work, so waiting for an optional field costs no throughput.
                    # Eligible again on the next pass, which starts only once the queue drains.
                    self._record(row,'Waiting for source',dict(result,reasons=[GAP_DEFER_REASON],wait=None,gap_deferrals=deferrals+1),self.clock())
                    deferred.append(identity)
                elif result.get('reasons'):
                    wait=result.get('wait');state='Waiting for source' if wait else 'Held'
                    self._record(row,state,result,wait.get('retry_at') if wait else self.clock()+min(86400,900*2**min((previous or {}).get('research_attempt',0),7)))
                    deferred.append(identity)
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
                        result['reasons']=[str(error)[:300] or 'Automatic source checks failed'];self._record(fresh,'Held',result,self.clock()+min(86400,900*2**min((previous or {}).get('research_attempt',0),7)));deferred.append(identity)
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
            try:self._paused_checkpoint(id,checkpoint)
            except (OSError,sqlite3.Error) as error:self._failure(id,error,'pause',identity,row,False)
        except Exception as error:
            self._failure(id,error,phase,identity,row,research_failed)

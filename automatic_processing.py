"""One explicitly started, checkpointed public-source Audiobooks pass.
Construction/reconnect/restart never starts inventory, approval or conversion.
"""
import contextlib
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
# Start over / "Let the app handle it" (RefusedRetry follow-ups 3 and 4): a blocker that clears by itself leaves one
# pending start for the app, checked every PENDING_POLL seconds (Judy: within 15 s of the blocker clearing).
CLEARS = ('conversion', 'scan', 'stopping')
PENDING_POLL = 3.0

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
    # Defaults for an instance built without __init__ (private test stubs that run _work directly): no book was put
    # back, the run is not closing, no hook is set, no start is pending.
    _requeued=();_closing_run=False;on_started=None;server_closing=None;start_pending=None
    def __init__(self,merge,research=None,clock=time.time):
        self.merge=merge;self.inventory=merge.inventory;self.database=self.inventory.database
        self.research=research or PublicResearch(PublicClient(self.database))
        self.lock=threading.RLock();self.stop_event=threading.Event();self.thread=None;self.current=None;self.live_checkpoint=None;self.closed=False;self.volatile_failure=None;self.clock=clock;self.next_retry_at=None
        # Books put back on the running run by Start over or release (requeue), taken by the worker in click order;
        # _closing_run is set once the run has passed its last research step, so a later book waits for the next run.
        self._requeued=[];self._closing_run=False
        # One pending start for the app (O12), in memory only: a start nobody is watching never comes back after a restart.
        self.start_pending=None;self._pending_thread=None;self._pending_wake=threading.Event();self.on_change=None
        # The server's hook for every start (Start, Start over, release, a pending start): the pass scans Audiobooks.
        self.on_started=None
        # The server's closing flag (Quit, shutdown), read at the moment a start fires: a pending start has no request
        # to carry it, and a press admitted before Quit carries the value it read before Quit began.
        self.server_closing=None
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
    def index(self):
        """{id: {revision, fingerprint, state, duplicate_review}} for every recorded candidate, in one read.

        The book list's Held and Recording review filters use it instead of one query per candidate;
        a row still counts only when its revision and fingerprint match, exactly as candidate().
        """
        result={}
        with connect(self.database) as db:
            for r in db.execute('SELECT id,revision,fingerprint,state,result FROM automatic_candidates'):
                try:recorded=json.loads(r['result'] or '{}');duplicate=bool(recorded.get('duplicate_review'));reasons=[str(x) for x in recorded.get('reasons') or []][:8]
                except (TypeError,ValueError,AttributeError):duplicate=False;reasons=[]
                result[r['id']]={'revision':r['revision'],'fingerprint':r['fingerprint'],'state':r['state'],'duplicate_review':duplicate,'reasons':reasons}
        failure=self.volatile_failure
        if failure and failure['diagnostic'].get('candidate_id') in result:result[failure['diagnostic']['candidate_id']]['state']='Needs attention'
        return result
    def _candidate_root(self,row):
        if row.get('source_root'):return row['source_root']
        sources=self.inventory.source_roots('Audiobooks') if hasattr(self.inventory,'source_roots') else (self.inventory.roots['Audiobooks'],)
        if len(sources)==1:return sources[0]
        return self.inventory.source_root_for_path(row['members'][0]['path'])

    def candidate(self,row):
        with connect(self.database) as db:r=db.execute('SELECT * FROM automatic_candidates WHERE id=?',(row['id'],)).fetchone()
        if not r or r['revision']!=row['revision'] or r['fingerprint']!=row['fingerprint']:return None
        result=json.loads(r['result'])
        if self.volatile_failure and self.volatile_failure['diagnostic']['candidate_id']==row['id']:
            r=dict(r);r['state']='Needs attention';result=self.volatile_failure['candidate_result']
        return {'state':r['state'],'local_source_gate_version':result.get('local_source_gate_version'),'metadata_holds':result.get('metadata_holds',[]),'manual_metadata_sources':result.get('manual_metadata_sources',[]),'manual_metadata_conflicts':result.get('manual_metadata_conflicts',[]),'research_version':result.get('research_version'),'reasons':result.get('reasons',[]),'sources':result.get('sources',[]),'wait':result.get('wait'),'attempted_utc':r['attempted'],'retry_at':r['retry_at'],'research_attempt':result.get('research_attempt',0),'research_history':result.get('research_history',[]),'metadata_facts':result.get('metadata_facts'),'duplicate_review':result.get('duplicate_review'),'gap_deferrals':result.get('gap_deferrals',0)}
    def _refresh_wait(self,row,previous):
        from source_identity import LOCAL_SOURCE_GATE_VERSION
        if previous and previous['state']=='Held' and previous.get('reasons')==['Sources disagree on the title or author'] and (previous.get('metadata_facts') or {}).get('identity_basis')=='local_agreement' and previous.get('local_source_gate_version')!=LOCAL_SOURCE_GATE_VERSION:
            # Narrow policy invalidation only. The normal worker still respects editing leases,
            # saved drafts, source revalidation and all metadata/media admission gates.
            return dict(previous,retry_at=None)
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
        return self._start_block(state,jobs=jobs,scanning=scanning,server_closing=server_closing)[1]
    def _start_block(self,state,*,jobs=None,scanning=None,server_closing=False):
        """(kind, reason) of what stops Start now, or (None, ''). kind: 'closing', 'failure', 'stopping', 'running',
        'scan', 'conversion' or 'unknown'; 'conversion', 'scan' and 'stopping' clear by themselves (CLEARS)."""
        # This is a read-only snapshot, with no new lock acquisition. In
        # particular, never take merge/scanner locks while holding self.lock.
        if self.closed or server_closing or self._server_closing():return 'closing','The local server is stopping or stopped. Start is unavailable.'
        if self.volatile_failure:return 'failure','Automatic processing cannot restart because its failure record could not be saved.'
        if state=='Stopping':return 'stopping','Automatic processing is stopping. Wait for it to finish stopping.'
        if state=='Running' or self.thread and self.thread.is_alive():return 'running','Automatic processing is already running.'
        if scanning is None:
            worker=getattr(self.inventory,'worker',None)
            scanning=bool(worker and worker.is_alive())
        if scanning:return 'scan','Discovery is in progress. Wait for it to stop before starting automatic processing.'
        job_state=jobs.get('state') if isinstance(jobs,dict) else None
        if job_state=='Running':return 'conversion','Audiobook conversion is running. Pause audiobook jobs before starting automatic processing.'
        if job_state=='Pausing':return 'conversion','Audiobook jobs are pausing. Wait for them to pause before starting automatic processing.'
        if job_state not in ('Idle','Paused','Completed','Needs attention'):
            return 'unknown','Start availability is unknown. Waiting for the local server.'
        return None,''
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
        kind,block=self._start_block(state,jobs=jobs,scanning=scanning,server_closing=server_closing)
        pending=self.start_pending
        return {'start_block':{'kind':kind,'clears':kind in CLEARS} if kind and kind!='running' else None,
                'start_pending':{'kind':pending['kind']} if pending else None,'state':state,'phase':'waiting' if armed else run['phase'] if run else 'idle','run_id':run['id'] if run else None,'reason':self.volatile_failure['reason'] if self.volatile_failure else run['reason'] if run else '',
                'restart_paused':bool(run and run['restart_paused']),'failure':diagnostic,'failure_durable':bool(diagnostic and not self.volatile_failure),'retry_help':RETRY_HELP if research_retry(run) and not self.volatile_failure else '',
                'can_start':not bool(block),'start_block_reason':block,'can_stop':active and state!='Stopping','research':counts,'current':dict(self.current) if self.current else None,
                'automatic_retry_enabled':armed,'next_retry_at':self.next_retry_at if armed else None,'research_pass':self._research_pass(run,self.live_checkpoint)}
    @staticmethod
    def _research_pass(run,live=None):
        """Books visited of this research sweep; None outside research.

        The worker's live checkpoint is used while it runs: the saved one is written only at some
        steps, so it lagged (2777 of 4026 while the current book changed 31 times). A book counts once
        it has been visited, deferred or not; a sweep over deferred books starts its own count.
        Display only, read on every poll and by the restart fence: any unexpected shape gives None.
        """
        try:
            if not run or run['phase']!='research':return None
            checkpoint=live if isinstance(live,dict) else json.loads(run['checkpoint'] or '{}')
            if not isinstance(checkpoint,dict):return None
            ids=lambda key:{item for item in list(checkpoint.get(key) or []) if isinstance(item,str)} if isinstance(checkpoint.get(key) or [],list) else set()
            pending=ids('pending');total=len(ids('done')|pending|ids('deferred'))
            return {'completed':total-len(pending),'total':total} if total else None
        except Exception:return None
    def _server_closing(self):
        """Quit or shutdown has begun: the server is closing, or the converter drains for a desktop Quit. Read where a
        start fires, not only where a press enters: the pending start (O12) acts later for a press. Attribute reads
        only, no lock. A hook that fails reads as closing: no start is the safe answer."""
        if getattr(self.merge,'draining',False) is True:return True
        probe=self.server_closing
        if probe is None:return False
        try:return bool(probe())
        except Exception:return True
    def start(self,*,server_closing=False):
        with self.lock:
            # Checked under self.lock, which stop() also takes: a start can no longer slip in after Quit's stop.
            if server_closing or self._server_closing():raise ValueError('The local server is stopping or stopped. Start is unavailable.')
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
            self.stop_event.clear();self.start_pending=None;self._closing_run=False
            self.thread=threading.Thread(target=self._work,args=(run['id'],),name='BooksArrangerAutomatic',daemon=False);self.thread.start()
        started=self.on_started
        if started:
            try:started()
            except Exception:pass
        return self.status()
    def requeue(self,identity):
        """Start over / release: put a book back on the run's pending list. 'this_run' when the running or saved run will
        still visit it (the worker takes it next, ahead of the others), 'next_run' when the running run has already
        passed its last research step. A run that ended or never started visits every book after its scan."""
        with self.lock:
            if self.thread and self.thread.is_alive():
                if self._closing_run:return 'next_run'
                if identity not in self._requeued:self._requeued.append(identity)
                return 'this_run'
            run=self._run_row()
            if not run or run['phase']=='discovery' or not (run['state'] in ('Paused','Stopping') or research_retry(run)):return 'this_run'
            def put(db):
                current=db.execute('SELECT checkpoint FROM automatic_runs WHERE id=?',(run['id'],)).fetchone()
                try:checkpoint=json.loads(current['checkpoint'] or '{}') if current else {}
                except (TypeError,ValueError):checkpoint={}
                if not isinstance(checkpoint,dict):checkpoint={}
                self._requeue_into(checkpoint,[identity])
                db.execute('UPDATE automatic_runs SET checkpoint=? WHERE id=?',(json.dumps(checkpoint),run['id']))
            transaction(self.database,put)
            return 'this_run'
    @staticmethod
    def _requeue_into(checkpoint,ids):
        """ids go first on pending and leave done and deferred (deferred is changed in place: the worker holds it)."""
        checkpoint['pending']=list(ids)+[item for item in list(checkpoint.get('pending') or []) if item not in ids]
        checkpoint['done']=[item for item in list(checkpoint.get('done') or []) if item not in ids]
        deferred=checkpoint.get('deferred')
        if isinstance(deferred,list):deferred[:]=[item for item in deferred if item not in ids]
    def _requeue_guard(self):
        return self.__dict__.get('lock') or contextlib.nullcontext()
    def _take_requeued(self,checkpoint):
        """Worker: move books Start over or release put back since the last step to the front of pending."""
        if not self._requeued:return False
        with self._requeue_guard():
            taken=list(self._requeued);self._requeued.clear()
        if taken:self._requeue_into(checkpoint,taken)
        return bool(taken)
    def request_start(self,*,server_closing=False):
        """Start over / release (O9, O12): start automatic processing when it is not running. Never raises: a start a
        blocker refuses leaves one pending start when that blocker clears by itself, and is reported otherwise.
        {'action': 'running'|'started'|'continued'|'pending'|'blocked', 'pending_kind'?, 'reason'?}."""
        with self.lock:
            if self.thread and self.thread.is_alive():return {'action':'running'}
            run=self._run_row()
            continuing=bool(run and (run['state'] in ('Paused','Stopping') or research_retry(run)))
        try:self.start(server_closing=server_closing)
        except ValueError as error:
            kind,reason=self._current_block(server_closing=server_closing)
            if kind=='running':return {'action':'running'}
            if kind in CLEARS:
                self._set_pending(kind)
                return {'action':'pending','pending_kind':kind,'reason':reason}
            return {'action':'blocked','reason':reason or str(error)}
        return {'action':'continued' if continuing else 'started'}
    def _current_block(self,server_closing=False):
        run=self._run_row()
        snapshot=getattr(self.merge,'status_snapshot',None)
        try:jobs=snapshot() if callable(snapshot) else self.merge.state()
        except Exception:jobs=None
        return self._start_block(run['state'] if run else 'Idle',jobs=jobs,server_closing=server_closing)
    def _changed(self):
        notify=self.on_change
        if notify:
            try:notify()
            except Exception:pass
    def _set_pending(self,kind):
        with self.lock:
            self.start_pending={'kind':kind}
            if not (self._pending_thread and self._pending_thread.is_alive()):
                self._pending_wake.clear()
                self._pending_thread=threading.Thread(target=self._pending_loop,name='BooksArrangerPendingStart',daemon=True);self._pending_thread.start()
        self._changed()
    def cancel_start(self):
        """Cancel automatic start: the pending start ends; books keep waiting for a press."""
        with self.lock:self.start_pending=None
        self._pending_wake.set();self._changed()
        return self.status()
    def _pending_loop(self):
        """The pending start fires with exactly what the Start button does, and nothing else: no window, focus, sound
        or notification call exists on this path (the server has none). It keeps waiting through another blocker that
        clears; a blocker that cannot clear ends it."""
        while True:
            self._pending_wake.wait(PENDING_POLL);self._pending_wake.clear()
            with self.lock:
                pending=self.start_pending
                if not pending or self.closed:
                    self.start_pending=None;return
                if self.thread and self.thread.is_alive():
                    self.start_pending=None;self._changed();return
            kind,_=self._current_block()
            if kind is None:
                try:
                    with self.lock:
                        if self.start_pending is not pending:continue  # cancelled meanwhile
                        self.start()
                except ValueError:kind,_=self._current_block()
                else:
                    self._changed();return
            if kind=='running':
                with self.lock:self.start_pending=None
                self._changed();return
            with self.lock:
                if self.start_pending is not pending:continue
                if kind in CLEARS and kind==pending['kind']:continue
                self.start_pending={'kind':kind} if kind in CLEARS else None
            self._changed()
            if kind not in CLEARS:return
    def stop(self,force=False):
        """Stop, Quit (not forced) and the app's own safety stops (disk full, working-file hold: forced). Each also ends
        a pending start (O12): a start the app or Sergei has just stopped must never come back by itself. The rows and
        the notice then read as after Cancel automatic start (RefusedRetry follow-up 4, section 1.4)."""
        with self.lock:
            cancelled=self.start_pending is not None;self.start_pending=None
            run=self._run_row()
            active=force or bool(run and run['state'] in ('Running','Stopping'))
            if active:
                if run and run['state']=='Running':self._update(run['id'],state='Stopping',reason='Stopping automatic processing — saving pending work')
                self.stop_event.set();self.next_retry_at=None
        if cancelled:
            self._pending_wake.set();self._changed()
        if not active:return self.status()
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
            row=db.execute('SELECT revision FROM book_groups WHERE id=? AND root=? AND superseded=0',(id,self.inventory.source_root_for_candidate(id) if hasattr(self.inventory,'source_root_for_candidate') else self.inventory.roots['Audiobooks'])).fetchone()
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
                groups=db.execute(f"SELECT DISTINCT g.* FROM book_groups g,json_each(g.evidence,'$.members') m WHERE g.root=? AND g.superseded=0 AND json_extract(m.value,'$.path') IN ({marks})",(self._candidate_root(row),*old_paths)).fetchall()
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

    def _resume_queue(self):
        """Resume saved queued work for this run. A Quit or Pause that began meanwhile refuses that queue start
        (StartRefused 'closing' or 'stale'); for this worker that is a stop, so the run pauses with its work saved.
        Live 2026-10-23: a Start racing Quit recorded 'Books is closing' as an automatic-processing failure."""
        from audio_jobs import StartRefused
        try:self.merge.resume()
        except StartRefused as refused:
            if getattr(refused,'start_state',None) in ('closing','stale') or self.stop_event.is_set():raise InterruptedError() from refused
            raise

    def _work(self,id):
        row=None;identity=None;phase='unknown';research_failed=False;checkpoint={}
        try:
            run=self._run_row();checkpoint=json.loads(run['checkpoint']);phase=run['phase'];self.live_checkpoint=checkpoint
            if phase=='discovery':
                # Existing queued jobs finish before a scan; never scan while encoding/cleanup runs.
                if self.merge.state().get('queued') or self.merge.state().get('postprocessing_pending'):
                    self._resume_queue()
                    while not self._idle_jobs():
                        if self.stop_event.wait(.2):raise InterruptedError()
                saved=self.inventory.status('Audiobooks')
                self.inventory.launch('Audiobooks',resume=saved['state'] in ('stopped','offline','failed'))
                while self.inventory.worker and self.inventory.worker.is_alive():
                    if self.stop_event.wait(.2):self.inventory.stop();self.inventory.worker.join(20);raise InterruptedError()
                if self.inventory.status('Audiobooks')['state'] not in ('completed',):
                    raise ValueError('Discovery incomplete or has read errors; saved progress preserved')
                candidates=self.inventory.candidates('Audiobooks',limit=1000000)['rows']
                checkpoint={'pending':[r['id'] for r in candidates],'done':[]};self.live_checkpoint=checkpoint
                self._update(id,phase='research',checkpoint=json.dumps(checkpoint));phase='research'
            else:
                # Resume saved queued work; the immutable queue already owns each manifest.
                if self.merge.state().get('queued') or self.merge.state().get('postprocessing_pending'):self._resume_queue()
                if self._add_current_candidates(checkpoint):
                    self._update(id,phase='research',checkpoint=json.dumps(checkpoint));phase='research'
            checkpoint['pending']=list(dict.fromkeys(checkpoint.get('pending',[])+checkpoint.get('deferred',[])))
            checkpoint['done']=list(dict.fromkeys(checkpoint.get('done',[])))
            checkpoint['deferred']=[];deferred=checkpoint['deferred']
            while True:
              while self._take_requeued(checkpoint) or checkpoint.get('pending') or deferred:
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
                              if self._requeued:break  # Start over / release: that book is taken within a minute
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
                      import manual_metadata
                      with connect(self.inventory.database) as db:row['_manual_metadata_sources']=manual_metadata.records(db,row)
                      result=self.research.lookup(row,self._candidate_root(row),self.stop_event,lambda source,stage:self._progress(row['title_clue'],source,stage))
                  except ValueError:
                      # Unsupported input or malformed public evidence holds only this candidate.
                      result={'sources':[],'reasons':['Public research input or evidence exceeds supported limits']}
                  research_failed=False
                  if self.stop_event.is_set():raise InterruptedError()
                  # Human choices are scoped constraints; a matching researched draft
                  # may discharge only the exact manual/provider conflict hold.
                  # Other source/identity reasons and normal admission proofs remain.
                  if hasattr(getattr(self.merge,'reviews',None),'metadata_questions'):
                      import metadata_choices
                      question_row=dict(row,automatic=result)
                      questions=self.merge.reviews.metadata_questions(question_row,self.merge.reviews._context(row))
                      try:metadata_choices.admission(questions,result.get('review') or {})
                      except ValueError as error:
                          result['reasons']=list(dict.fromkeys(result.get('reasons',[])+[str(error)]))
                          result['metadata_holds']=list(result.get('metadata_holds',[]))+[{'cause':'metadata_choice_required','reason':str(error)}]
                      else:
                          if questions.get('questions'):
                              result['reasons']=[reason for reason in result.get('reasons',[]) if reason!='Saved manual metadata disagrees with researched identity']
                              result['metadata_holds']=[hold for hold in result.get('metadata_holds',[]) if hold.get('reason')!='Saved manual metadata disagrees with researched identity']
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
                  if self._requeued:break  # a book put back meanwhile is researched in this run
              if self.stop_event.is_set():raise InterruptedError()
              with self._requeue_guard():
                  if not self._requeued:self._closing_run=True
              if self._closing_run:break
              phase='research';self._update(id,phase='research',checkpoint=json.dumps(checkpoint))
            if self.merge.state().get('failed'):
                self._update(id,state='Needs attention',phase='conversion',reason='Some audiobook jobs need attention; verified outputs and pending work are preserved')
            else:self._update(id,state='Completed',phase='completed',reason='')
        except InterruptedError:
            self.current=None;self.next_retry_at=None;self.live_checkpoint=None
            if isinstance(checkpoint,dict) and checkpoint.get('pending') is not None:self._take_requeued(checkpoint)  # saved, so continuing reaches them
            # Report Paused only after both scan and owned converter/cleanup have stopped.
            self.inventory.stop();self.merge.pause()
            while self.inventory.worker and self.inventory.worker.is_alive():self.inventory.worker.join(.2)
            while self.merge.state()['state']=='Pausing':time.sleep(.2)
            try:self._paused_checkpoint(id,checkpoint)
            except (OSError,sqlite3.Error) as error:self._failure(id,error,'pause',identity,row,False)
        except Exception as error:
            self._failure(id,error,phase,identity,row,research_failed)

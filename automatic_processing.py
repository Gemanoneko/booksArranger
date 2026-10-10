"""One explicitly started, checkpointed public-source Audiobooks pass.
Construction/reconnect/restart never starts inventory, approval or conversion.
"""
import datetime as dt
import json
import threading
import time
import uuid
from scanner import connect
from public_research import PublicClient,PublicResearch,ResearchWait
from source_identity import VERSION,source_gate


def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()

class AutomaticProcessing:
    def __init__(self,merge,research=None):
        self.merge=merge;self.inventory=merge.inventory;self.database=self.inventory.database
        self.research=research or PublicResearch(PublicClient(self.database))
        self.lock=threading.RLock();self.stop_event=threading.Event();self.thread=None;self.current=None;self.closed=False
        with connect(self.database) as db:
            __import__('groups').setup(db)
            db.execute('CREATE TABLE IF NOT EXISTS automatic_runs(id TEXT PRIMARY KEY,state TEXT,phase TEXT,checkpoint TEXT,reason TEXT,created TEXT,updated TEXT,restart_paused INTEGER DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS automatic_manual_drafts(id TEXT PRIMARY KEY,revision INTEGER,expires REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS automatic_candidates(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,state TEXT,result TEXT,retry_at REAL,attempted TEXT,matcher_version TEXT)')
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
        return {'state':r['state'],'reasons':result.get('reasons',[]),'sources':result.get('sources',[]),'attempted_utc':r['attempted'],'retry_at':r['retry_at']}
    def status(self):
        run=self._run_row();counts={'researching':0,'waiting':0,'held':0}
        with connect(self.database) as db:
            for r in db.execute('SELECT a.state,count(*) n FROM automatic_candidates a JOIN book_groups g ON g.id=a.id AND g.revision=a.revision AND g.fingerprint=a.fingerprint WHERE g.superseded=0 GROUP BY a.state'):
                if r['state']=='Researching':counts['researching']+=r['n']
                elif r['state']=='Waiting for source':counts['waiting']+=r['n']
                elif r['state']=='Held':counts['held']+=r['n']
        state=run['state'] if run else 'Idle';active=state in ('Running','Stopping')
        return {'state':state,'phase':run['phase'] if run else 'idle','run_id':run['id'] if run else None,'reason':run['reason'] if run else '',
                'restart_paused':bool(run and run['restart_paused']),'can_start':not self.closed and not active,'can_stop':active and state!='Stopping','research':counts,'current':dict(self.current) if self.current else None}
    def start(self):
        with self.lock:
            if self.closed:raise ValueError('Automatic processing is closed')
            if self.thread and self.thread.is_alive():return self.status()
            self.merge._no_scan()
            jobs=self.merge.state()
            if jobs['state'] in ('Running','Pausing'):raise ValueError('Pause existing audiobook work before automatic discovery')
            run=self._run_row()
            if not run or run['state'] in ('Completed','Needs attention'):
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
            self.stop_event.set()
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
    def _work(self,id):
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
                self._update(id,phase='research',checkpoint=json.dumps(checkpoint))
            else:
                # Resume saved queued work; the immutable queue already owns each manifest.
                if self.merge.state().get('queued'):self.merge.resume()
            checkpoint['pending']=list(dict.fromkeys(checkpoint.get('pending',[])+checkpoint.get('deferred',[])))
            checkpoint['deferred']=[];deferred=checkpoint['deferred']
            while checkpoint.get('pending'):
                if self.stop_event.is_set():raise InterruptedError()
                identity=checkpoint['pending'][0]
                try:row=self.merge.reviews._row('Audiobooks',identity)
                except ValueError:
                    checkpoint['pending'].pop(0);self._update(id,checkpoint=json.dumps(checkpoint));continue
                job=self.merge.candidate_status(identity)
                if job:
                    checkpoint['pending'].pop(0);checkpoint.setdefault('done',[]).append(identity);self._update(id,checkpoint=json.dumps(checkpoint));continue
                previous=self.candidate(row)
                if previous and previous['state'] in ('Held','Waiting for source') and previous.get('retry_at') and previous['retry_at']>time.time():
                    # Save unavailable-source work for the next explicit Start.
                    if previous['state']=='Waiting for source':deferred.append(identity)
                    checkpoint['pending'].pop(0);self._update(id,checkpoint=json.dumps(checkpoint));continue
                if self.manual_draft(row):
                    self._record(row,'Held',{'reasons':['Manual draft retained']});checkpoint['pending'].pop(0);self._update(id,checkpoint=json.dumps(checkpoint));continue
                self._record(row,'Researching');self._progress(row['title_clue'],'Public sources','Researching work identity')
                try:
                    result=self.research.lookup(row,self.inventory.roots['Audiobooks'],self.stop_event,lambda source,stage:self._progress(row['title_clue'],source,stage))
                except ValueError:
                    # Unsupported input or malformed public evidence holds only this candidate.
                    result={'sources':[],'reasons':['Public research input or evidence exceeds supported limits']}
                if self.stop_event.is_set():raise InterruptedError()
                if result.get('reasons'):
                    wait=result.get('wait');state='Waiting for source' if wait else 'Held'
                    self._record(row,state,result,wait.get('retry_at') if wait else time.time()+7*86400)
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
                        result['reasons']=['Cover source unavailable'];result['wait']={'source':wait.source,'reason':wait.reason,'retry_at':wait.retry_at}
                        self._record(fresh,'Waiting for source',result,wait.retry_at);deferred.append(identity)
                    except (ValueError,OSError) as error:
                        if self.stop_event.is_set():raise InterruptedError()
                        try:fresh=self.merge.reviews._row('Audiobooks',identity)
                        except ValueError:fresh=row
                        result['reasons']=[str(error)[:300] or 'Automatic source checks failed'];self._record(fresh,'Held',result,time.time()+7*86400)
                checkpoint['pending'].pop(0);checkpoint.setdefault('done',[]).append(identity);self._update(id,checkpoint=json.dumps(checkpoint))
            self.current=None;self._update(id,phase='conversion')
            while not self._idle_jobs():
                if self.stop_event.wait(.2):raise InterruptedError()
                if self.merge.state()['state']=='Paused':raise InterruptedError()
            if self.stop_event.is_set():raise InterruptedError()
            if deferred:
                checkpoint['pending']=list(dict.fromkeys(deferred));checkpoint['deferred']=[]
                self._update(id,state='Paused',phase='research',checkpoint=json.dumps(checkpoint),reason='Waiting for public sources; Start retries saved work after cooldown')
            elif self.merge.state().get('failed'):
                self._update(id,state='Needs attention',phase='conversion',reason='Some audiobook jobs need attention; verified outputs and pending work are preserved')
            else:self._update(id,state='Completed',phase='completed',reason='')
        except InterruptedError:
            self.current=None
            # Report Paused only after both scan and owned converter/cleanup have stopped.
            self.inventory.stop();self.merge.pause()
            while self.inventory.worker and self.inventory.worker.is_alive():self.inventory.worker.join(.2)
            while self.merge.state()['state']=='Pausing':time.sleep(.2)
            with connect(self.database) as db:db.execute("UPDATE automatic_candidates SET state='Pending' WHERE state='Researching'")
            self._update(id,state='Paused',reason='Paused — pending work saved')
        except Exception:
            self.current=None;self._update(id,state='Needs attention',reason='Automatic pass could not continue; saved source and job evidence preserved')

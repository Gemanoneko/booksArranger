"""Application owner for durable book decisions; acceptance never starts audio."""
import json
import sqlite3
import threading
import contextlib

from durable_decisions import Decisions,DecisionChanged
from scanner import connect


class DecisionBusy(ValueError):
    code='busy'


class DecisionRuntime:
    def __init__(self,merge):
        self.merge=merge;self.store=Decisions(merge.inventory.database)
        self.stop=threading.Event();self.wake=threading.Event();self.thread=None
        self.lock=threading.Lock();self.failure=None
        self._prune_needed=True

    def accept_names(self,request_id,book,revision,fingerprint,names,predecessor=None):
        import entered_names
        entered_names.check(names)
        return self.accept(request_id,book,revision,fingerprint,'names',{'names':names},predecessor)

    def accept(self,request_id,book,revision,fingerprint,action,payload,predecessor=None,*,library='Audiobooks'):
        from decision_contract import effects,file_row,file_identity,file_fingerprint
        old=self.store.get(request_id)
        if old is not None:current={'revision':None,'fingerprint':None}
        elif action=='file_review':
            row=file_row(self.merge.inventory,library,payload['path'])
            if book!=file_identity(library,payload['path']) or revision!=0 or fingerprint!=file_fingerprint(library,payload['path'],payload['size'],payload['modified']):raise ValueError('Saved file review requires its exact shown catalog identity')
            current={'revision':0,'fingerprint':file_fingerprint(library,row['path'],row['size'],str(row['modified']))}
        else:
            with connect(self.store.database) as db:
                current=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=? AND superseded=0',(book,)).fetchone()
            if current is None:raise ValueError('This book is no longer in the current catalog')
        answer=self.store.accept(request_id=request_id,book_id=book,action=action,revision=revision,fingerprint=fingerprint,
                                 payload=payload,effects=effects(action,payload),predecessor=predecessor,
                                 current_revision=current['revision'],current_fingerprint=current['fingerprint'])
        self.wake.set()
        if not self.stop.is_set():
            try:self.start()
            except Exception as error:
                # Acceptance already committed: an application-owner failure
                # cannot turn this durable receipt into a refused Save.
                self.failure={'code':'decision_application_unavailable','message':'Saved decisions are retained; application could not start: '+(str(error) or type(error).__name__)[:1000],'transient':False}
        return answer

    @contextlib.contextmanager
    def admission(self):
        with contextlib.ExitStack() as stack:
            for lock in (self.merge.operation_lock,self.merge.reviews.lock,self.merge.inventory.group_lock):
                if not lock.acquire(blocking=False):raise DecisionBusy('Saved decision is waiting for the current book check')
                stack.callback(lock.release)
            yield

    def _apply(self,request,scope,row):
        from decision_effects import Effect
        action=request['action'];payload=request['payload'];revision=row['revision'];book=request['book_id']
        projection=action=='approve' and 'approval' not in request['active_effects']
        if action=='names' or projection:
            fields={key.split('.',1)[1] for key in request['active_effects'] if key.startswith('names.')}
            original=dict(payload.get('names') or {})
            if projection:
                for key in ('title','author'):
                    if payload.get(key) is not None and payload[key].strip():original[key]=payload[key]
            names={key:value for key,value in original.items() if key in fields}
            if not names:raise ValueError('Saved names no longer own an applicable field')
            return self.merge.names_save(book,revision,names,fingerprint=request['source_fingerprint'],decision=scope)
        with self.admission():
            if action=='approve':return self.merge.approve_book(book,revision,**payload,fingerprint=request['source_fingerprint'],decision=scope)
            effect=Effect(scope,action,actions=(action,),final=True)
            if action=='review':return self.merge.reviews.save('Audiobooks',book,revision,**payload,effect=effect)
            if action=='tracks':return self.merge.reviews.tracks('Audiobooks',book,revision,**payload,effect=effect)
            if action=='metadata_choices':return self.merge.reviews.choose_metadata('Audiobooks',book,revision,**payload,effect=effect)
            raise ValueError('Unsupported saved decision consumer')

    def _apply_file(self,request,scope):
        from decision_contract import file_identity,file_fingerprint
        from durable_decisions import packed
        payload=request['payload'];path=payload['path']
        labels=[library for library in self.merge.inventory.roots if file_identity(library,path)==request['book_id']]
        if len(labels)!=1:raise ValueError('Saved file review has no exact configured library binding')
        library=labels[0];inventory=self.merge.inventory
        roots=inventory.source_roots(library) if hasattr(inventory,'source_roots') else (inventory.roots[library],)
        with connect(self.store.database) as db:
            db.execute('BEGIN IMMEDIATE');saved,_=scope.check(db)
            if saved['action']!='file_review' or packed(json.loads(saved['payload']))!=packed(payload):raise DecisionChanged('Saved file metadata differs from its accepted decision')
            rows=[row for row in db.execute('SELECT * FROM files WHERE path=?',(path,)) if row['root'] in roots]
            if len(rows)!=1 or rows[0]['kind'] not in ('audiobook','ebook') or rows[0]['error'] or rows[0]['missing']:raise ValueError('The catalog file is unavailable; saved metadata is retained for review')
            row=rows[0]
            if file_fingerprint(library,path,row['size'],str(row['modified']))!=saved['source_fingerprint'] or row['size']!=payload['size'] or str(row['modified'])!=payload['modified']:
                raise DecisionChanged('Inventory file changed; review the retained metadata against the new source')
            review=payload['review']
            if row['kind']!='audiobook' and (review.get('anthology') or review.get('canonical_author') or review.get('narrator')):raise ValueError('Audiobook role and anthology fields do not apply to ebooks')
            result=db.execute('UPDATE files SET review=? WHERE root=? AND path=? AND size=? AND modified=?',(json.dumps(review,ensure_ascii=False),row['root'],path,row['size'],row['modified']))
            if result.rowcount!=1:raise DecisionChanged('Inventory file changed before saved metadata could commit')
            scope.commit_step(db,'file_review',{'payload':payload},{'outcome':'saved','candidate_id':request['book_id'],'candidate_revision':0},final=True,applied_revision=0)

    def status(self):
        return {'state':'needs_review' if self.failure and self.failure['transient'] is False else 'waiting' if self.failure else 'paused' if self.stop.is_set() else 'running' if self.thread and self.thread.is_alive() else 'idle',
                'error':dict(self.failure) if self.failure else None}

    def start(self):
        with self.lock:
            if self.stop.is_set():raise ValueError('Saved-decision application is closing')
            if self.thread and self.thread.is_alive():return
            self.thread=threading.Thread(target=self._work,name='BooksArrangerSavedDecisions',daemon=False)
            self.thread.start()

    def close(self):
        self.stop.set();self.wake.set()
        thread=self.thread
        if thread and thread is not threading.current_thread():
            thread.join(30)
            if thread.is_alive():raise TimeoutError('Saved-decision application has not reached its catalog checkpoint')

    def _work(self):
        while not self.stop.is_set():
            try:
                if self._prune_needed:
                    self.store.purge_fulfilled();self._prune_needed=False
                requests=self.store.pending()
                worked=self.run_once(requests)
            except Exception as error:
                transient=isinstance(error,sqlite3.OperationalError) and getattr(error,'sqlite_errorcode',0)&255==sqlite3.SQLITE_BUSY
                self.failure={'code':'decision_catalog_busy' if transient else 'decision_application_unavailable',
                              'message':('Saved decisions are retained while the catalog is busy' if transient else 'Saved decisions are retained; their application stopped: '+(str(error) or type(error).__name__)[:1000]),
                              'transient':bool(transient)}
                # Re-read durable pending state after a bounded wait. Completed
                # consumer receipts are excluded, so recovery never blindly
                # repeats the action that preceded a failed status/hold write.
                self.wake.wait(.5 if transient else 2);self.wake.clear();continue
            self.failure=None
            if not worked:self.wake.wait(.5);self.wake.clear()

    def run_once(self,requests=None):
        """One pass over ready requests; busy books do not head-block other books."""
        worked=False
        for request in self.store.pending() if requests is None else requests:
            if self.stop.is_set() or getattr(self.merge,'draining',False) or self.merge.__dict__.get('_closing'):break
            scope=self.store.application(request['request_id'],request['generation'])
            try:
                if request['action']=='file_review':
                    self._apply_file(request,scope);self._prune_needed=True;worked=True;continue
                with connect(self.store.database) as db:
                    db.execute('BEGIN');row=db.execute('SELECT id,revision,fingerprint FROM book_groups WHERE id=? AND superseded=0',(request['book_id'],)).fetchone()
                if row is None or row['fingerprint']!=request['source_fingerprint']:
                    self.store.hold(request['request_id'],request['generation'],'This book’s sources changed; review the saved names before applying them')
                    worked=True;continue
                with connect(self.store.database) as db:
                    db.execute('BEGIN');scope.check_current(db,dict(row))
                self._apply(request,scope,row)
                # This only purges payload after the consumer's atomic receipt is
                # already committed; receipt/tombstone reconciliation survives.
                self._prune_needed=True;worked=True
            except DecisionChanged as error:
                # A new head fenced the old in-flight read. Its retained cumulative
                # effects will be read afresh, never marked failed or overwritten.
                try:self.store.hold(request['request_id'],request['generation'],str(error))
                except DecisionChanged:pass
                continue
            except (ValueError,sqlite3.Error) as error:
                if (self.store.get(request['request_id']) or {}).get('state')=='applied':
                    self._prune_needed=True;worked=True;continue
                if getattr(error,'code',None)=='busy' or isinstance(error,sqlite3.OperationalError) and getattr(error,'sqlite_errorcode',0)&255==sqlite3.SQLITE_BUSY:
                    continue
                try:self.store.hold(request['request_id'],request['generation'],str(error) or type(error).__name__)
                except DecisionChanged:pass
                worked=True
            except Exception as error:
                # An unknown consumer failure is held, not generically retried.
                # If its final receipt committed, hold() refuses to undo it.
                if (self.store.get(request['request_id']) or {}).get('state')=='applied':
                    self._prune_needed=True;worked=True;continue
                try:self.store.hold(request['request_id'],request['generation'],'Saved-decision application needs review: '+(str(error) or type(error).__name__))
                except DecisionChanged:pass
                worked=True
        return worked

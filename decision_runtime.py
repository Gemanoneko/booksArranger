"""Application owner for durable book decisions; acceptance never starts audio."""
import json
import sqlite3
import threading

from durable_decisions import Decisions,DecisionChanged
from scanner import connect


class DecisionRuntime:
    def __init__(self,merge):
        self.merge=merge;self.store=Decisions(merge.inventory.database)
        self.stop=threading.Event();self.wake=threading.Event();self.thread=None
        self.lock=threading.Lock();self.failure=None

    def accept_names(self,request_id,book,revision,fingerprint,names,predecessor=None):
        import entered_names
        entered_names.check(names)
        with connect(self.store.database) as db:
            row=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=? AND superseded=0',(book,)).fetchone()
        if row is None:raise ValueError('This book is no longer in the current catalog')
        answer=self.store.accept(request_id=request_id,book_id=book,action='names',revision=revision,fingerprint=fingerprint,
                                 payload={'names':names},effects=['names.'+field for field in names],predecessor=predecessor,
                                 current_revision=row['revision'],current_fingerprint=row['fingerprint'])
        self.wake.set()
        if not self.stop.is_set():
            try:self.start()
            except Exception as error:
                # Acceptance already committed: an application-owner failure
                # cannot turn this durable receipt into a refused Save.
                self.failure={'code':'decision_application_unavailable','message':'Saved decisions are retained; application could not start: '+(str(error) or type(error).__name__)[:1000],'transient':False}
        return answer

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
            if request['action']!='names':continue  # Other consumers are integrated separately.
            scope=self.store.application(request['request_id'],request['generation'])
            try:
                with connect(self.store.database) as db:
                    row=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=? AND superseded=0',(request['book_id'],)).fetchone()
                if row is None or row['fingerprint']!=request['source_fingerprint']:
                    self.store.hold(request['request_id'],request['generation'],'This book’s sources changed; review the saved names before applying them')
                    worked=True;continue
                if row['revision']!=request['observed_revision']:
                    self.store.hold(request['request_id'],request['generation'],'This book’s revision changed; review the saved names before applying them')
                    worked=True;continue
                fields={key.split('.',1)[1] for key in request['active_effects'] if key.startswith('names.')}
                names={key:value for key,value in request['payload']['names'].items() if key in fields}
                if not names:raise ValueError('Saved names no longer own an applicable field')
                self.merge.names_save(request['book_id'],row['revision'],names,fingerprint=request['source_fingerprint'],decision=scope)
                # This only purges payload after the consumer's atomic receipt is
                # already committed; receipt/tombstone reconciliation survives.
                self.store.purge_fulfilled();worked=True
            except DecisionChanged:
                # A new head fenced the old in-flight read. Its retained cumulative
                # effects will be read afresh, never marked failed or overwritten.
                continue
            except (ValueError,sqlite3.Error) as error:
                if getattr(error,'code',None)=='busy' or isinstance(error,sqlite3.OperationalError) and getattr(error,'sqlite_errorcode',0)&255==sqlite3.SQLITE_BUSY:
                    continue
                try:self.store.hold(request['request_id'],request['generation'],str(error) or type(error).__name__)
                except DecisionChanged:pass
                worked=True
            except Exception as error:
                # An unknown consumer failure is held, not generically retried.
                # If its final receipt committed, hold() refuses to undo it.
                try:self.store.hold(request['request_id'],request['generation'],'Saved-decision application needs review: '+(str(error) or type(error).__name__))
                except DecisionChanged:pass
                worked=True
        return worked

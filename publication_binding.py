"""Effective publication locations with catalog generation leases.

Historical receipts remain immutable. Read views use observed WAL snapshots with fresh provenance checks. Destructive
callers retain their own generation writer transaction; no location is cached.
"""
import contextlib
import copy
import json
import sqlite3
import threading
import publication_locations as locations


class PublicationBindings:
    def __init__(self,database):
        self.database=database;self.lock=threading.RLock();self.local=threading.local()

    @staticmethod
    def _effective(original,envelope):
        record=copy.deepcopy(original)
        record.update(copy.deepcopy(envelope['effective_location']))
        return record

    @contextlib.contextmanager
    def protect(self,original,kind=None,job=None,repair_journal_sha256=None):
        # A view is not disposal authority. Supported relocation writers require
        # the same exclusive catalog owner held by the application. WAL snapshots
        # let unrelated metadata writers proceed during protected media reads.
        with self.lock:
            inherited=getattr(self.local,'db',None)
            db=inherited or sqlite3.connect(self.database,timeout=10);db.row_factory=sqlite3.Row
            owner=inherited is None
            try:
                if owner:
                    wal=db.execute('PRAGMA journal_mode').fetchone()[0].lower()=='wal'
                    db.execute('BEGIN' if wal else 'BEGIN IMMEDIATE')
                    self.local.db=db
                effective,envelope=self.lookup(db,original,kind,repair_journal_sha256=repair_journal_sha256)
                yield effective,envelope
                # Never check freshness through the retained snapshot: an illegal
                # external writer could otherwise commit unseen generation drift.
                with contextlib.closing(sqlite3.connect(self.database,timeout=10)) as fresh:
                    fresh.row_factory=sqlite3.Row
                    fresh.execute('BEGIN')
                    current_record,current=self.lookup(fresh,original,kind,repair_journal_sha256=repair_journal_sha256)
                    if current!=envelope or current_record!=effective:
                        raise ValueError('Publication generation changed during protection')
            finally:
                if owner:
                    self.local.db=None;db.rollback();db.close()

    def display(self,original,kind=None,repair_journal_sha256=None):
        """(effective record, envelope) for showing a book, from one read snapshot, reused while lookup_token() and the
        receipt are unchanged (0.22.1: the book list resolved each shown book's relocation twice through protect(), about
        5 s a page on the live catalog). No lease and no deletion authority: verification and every destructive caller
        keep protect()."""
        with contextlib.closing(sqlite3.connect(self.database,timeout=10)) as db:
            db.row_factory=sqlite3.Row;db.execute('BEGIN')
            key=(self.lookup_token(db),kind,repair_journal_sha256,locations._digest(original))
            with self.lock:
                cache=self.__dict__.setdefault('_display',{})
                if key in cache:return copy.deepcopy(cache[key])
            value=self.lookup(db,original,kind,repair_journal_sha256=repair_journal_sha256)
        with self.lock:
            if len(cache)>=4096:cache.clear()
            cache[key]=copy.deepcopy(value)
        return value

    def current(self,original,kind=None,job=None,repair_journal_sha256=None):
        with self.protect(original,kind,job,repair_journal_sha256=repair_journal_sha256) as (record,envelope):
            return record,envelope

    def guard(self,db,original,envelope,kind=None,require_transaction=False,repair_journal_sha256=None):
        """Revalidate the generation in the caller's destructive write transaction."""
        if require_transaction and not db.in_transaction:raise ValueError('Publication guard requires a retained write transaction')
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='output_relocations'").fetchone()
        if kind is None:
            kinds=[r[0] for r in db.execute("SELECT DISTINCT publication_kind FROM output_relocations WHERE job_id=? AND publication_kind IN ('base','replacement')",(original['job_id'],))] if exists else []
            if len(kinds)>1:raise ValueError('Publication binding is ambiguous')
            kind=kinds[0] if kinds else 'base'
        bound=exists and db.execute('SELECT 1 FROM output_relocations WHERE job_id=? AND publication_kind=?',(original['job_id'],kind)).fetchone()
        if not bound:return envelope is None
        if envelope is None:return False
        durable=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(original['job_id'],)).fetchone()
        if durable is None:return False
        current=locations.resolve(db,dict(durable),kind,original)
        if kind in {'Chapters','Chaptersv2'} and json.loads(current['relocation']['accepted_routing_json']).get('repair_journal_sha256')!=repair_journal_sha256:return False
        return current['generation']==envelope['generation'] and current['effective_location']==envelope['effective_location']

    @staticmethod
    def lookup_token(db):
        """What a display lookup depends on beyond the job's own receipt, read in the caller's snapshot: the relocation
        rows (a transition writes a new generation), the append-only migration events and the completed series backfills
        (a retagged book's lineage). Equal tokens and an equal receipt give an equal lookup() answer (0.22.1: the status
        computation reuses each job's answer instead of resolving about 500 relocations every time, 19 s on the live
        catalog). Display only, like lookup().

        Cheap by construction (it runs once per shown book): every relocation insert and generation change appends a
        migration event in the same savepoint (publication_locations; the events table refuses UPDATE and DELETE), so the
        newest event id stands for both tables; only primary keys and the done rows' ids are read, never the JSON."""
        have={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('output_relocations','migration_events','series_backfill')")}
        token=[]
        if 'output_relocations' in have:token.append(db.execute('SELECT max(rowid) FROM output_relocations').fetchone()[0])
        if 'migration_events' in have:token.append(db.execute('SELECT max(event_id) FROM migration_events').fetchone()[0])
        if 'series_backfill' in have:token.append(tuple(db.execute("SELECT count(*),group_concat(job_id) FROM (SELECT job_id FROM series_backfill WHERE state='done' ORDER BY job_id)").fetchone()))
        return (tuple(sorted(have)),*token)

    def lookup(self,db,original,kind=None,repair_journal_sha256=None):
        """Display-only location lookup in the caller's coherent SQL snapshot.

        This does not grant deletion authority or current native verification.
        """
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='output_relocations'").fetchone()
        if kind is None:
            kinds=[r[0] for r in db.execute("SELECT DISTINCT publication_kind FROM output_relocations WHERE job_id=? AND publication_kind IN ('base','replacement')",(original['job_id'],))] if exists else []
            if len(kinds)>1:raise ValueError('Publication binding is ambiguous')
            kind=kinds[0] if kinds else 'base'
        bound=exists and db.execute('SELECT 1 FROM output_relocations WHERE job_id=? AND publication_kind=?',(original['job_id'],kind)).fetchone()
        if not bound:return copy.deepcopy(original),None
        durable=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(original['job_id'],)).fetchone()
        if durable is None:raise ValueError('Publication history unavailable')
        envelope=locations.resolve(db,dict(durable),kind,original)
        if kind in {'Chapters','Chaptersv2'}:
            accepted=json.loads(envelope['relocation']['accepted_routing_json'])
            if not repair_journal_sha256 or accepted.get('repair_journal_sha256')!=repair_journal_sha256:raise ValueError('Fresh authorized repair journal differs from relocation provenance')
        return self._effective(original,envelope),envelope

    @contextlib.contextmanager
    def protect_parent(self,job_id,proof):
        if not isinstance(proof,dict) or proof.get('schema')!='books-repair-parent-location-v1':raise ValueError('Invalid relocated repair parent proof')
        with contextlib.closing(sqlite3.connect(self.database,timeout=10)) as db:
            db.row_factory=sqlite3.Row;row=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()
            if row is None:raise ValueError('Repair parent history unavailable')
            original=json.loads(row['output'])
        with self.protect(original) as (effective,envelope):
            if envelope is None or proof.get('immutable_receipt_sha256')!=locations._digest(original) or proof.get('generation')!=envelope['generation'] or proof.get('effective_location')!=envelope['effective_location']:
                raise ValueError('Relocated repair parent generation changed')
            yield effective,envelope

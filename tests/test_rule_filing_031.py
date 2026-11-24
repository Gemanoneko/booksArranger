"""0.31.0 milestone B (Sergei 2026-11-22, rulings R18, R19, R24, R26): finished audiobooks are renamed and moved by the rules
with no approval step, and with a record (rule_filing.py).

Every move here is the app's real verified move (book_move) on real files in a private folder under the test's TEMP, from a
real catalog; the list is the real sorting_moves.plan(), the ledgers are the real series_backfill and gap_fill. The engine
is a stand-in that queues a move as the action queue does and runs it when the test says. One class writes a series into a
real audiobook made by ffmpeg and follows it to its series folder. No network, no real library.

Each behaviour has its control: the same case with the rule taken out gives another result (named in the test)."""
import contextlib
import copy
import hashlib
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import action_queue
import author_rules
import background_work
import book_delete
import book_move
import publication_locations as p
import rule_filing
import series_backfill
import sorting_moves
from gap_fill import GapFill
from metadata import propose
from native_io import DirectoryBoundary
from publication_binding import PublicationBindings
from scanner import connect
from series_backfill import SeriesBackfill

JOBS = ('CREATE TABLE IF NOT EXISTS audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL,'
        ' stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)')
ROWLING, FILED = 'Роулинг Джоан', 'Rowling J. K'  # Sergei's rule of 2026-10-24 files the first under the second


class Crash(RuntimeError):
    """The app ends here (a fault at a journal boundary of the move)."""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Engine:
    """What RuleFiling asks of the engine, on the shelf's catalog and folder: the real list, the real ledgers, and the real
    move, queued (as the action queue holds it) and run when the test says."""
    draining = False

    def __init__(self, shelf):
        self.shelf = shelf
        self.inventory = SimpleNamespace(database=shelf.db, output_root=str(shelf.sorted), worker=None)
        self.stage_root = shelf.base / 'cache' / 'audio-staging'
        self.jobs = SimpleNamespace(_thread=None, status=lambda: {'jobs': []})
        self.cleanup = SimpleNamespace(thread=None, current=None)
        self.paused, self.retained, self.queue, self.crash_at = False, frozenset(), [], None
        self.same_volume = book_move.default_same_volume
        self.series_backfill = SeriesBackfill(self, research=None, stage=shelf.base / 'proof')
        self.gap_fill = GapFill(self)
        self.rule_filing = rule_filing.RuleFiling(self, clock=lambda: shelf.now)

    def sorting_moves(self):
        with connect(self.shelf.db) as db:
            return sorting_moves.plan(db, str(self.shelf.sorted), author_rules.load(self.shelf.db), retained=self.retained)

    def filing_paused(self):
        return self.paused

    def cancel_move(self, move_id):
        with connect(self.shelf.db) as db:
            return book_move.cancel(db, move_id)

    def resolve(self, job_id, kind):
        with connect(self.shelf.db) as db:
            record = json.loads(db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()[0])
        return PublicationBindings(self.shelf.db).current(record, kind)[0]

    def fault(self, stage):
        if stage == self.crash_at:
            raise Crash(stage)

    def mover(self):
        shelf = self.shelf
        return book_move.Mover(lambda: connect(shelf.db), self.resolve, sources=lambda: (str(shelf.library),), output_root=str(shelf.sorted),
                               same_volume=lambda a, b: self.same_volume(a, b), fault=self.fault, remove_folder=book_delete._remove_folder,
                               protected_roots=lambda: (str(shelf.library), str(shelf.sorted)))

    def _sorting_move(self, job_id, target, origin='user', override_id=None):
        with connect(self.shelf.db) as db:
            candidate = db.execute("SELECT json_extract(manifest,'$.candidate_id') FROM audio_jobs WHERE job_id=?", (job_id,)).fetchone()[0]
        start = book_move.location(self.resolve(job_id, 'base'))
        with connect(self.shelf.db) as db:
            move = book_move.plan(db, job_id=job_id, kind='base', candidate_id=candidate, start=start, folder=os.path.dirname(target),
                                  root=str(self.shelf.sorted), name=os.path.basename(target), origin=origin, override_id=override_id)
        if move is None:
            return {'state': 'unchanged', 'move': {}}
        self.queue.append(move['move_id'])
        return {'state': 'move_queued', 'move': book_move.view(move)}

    def run_queue(self):
        done = []
        while self.queue:
            done.append(self.mover().run(self.queue.pop(0)))
            self.rule_filing.notify()
        return done

    def quit(self):
        """Quit: a queued move is taken back as the app closes (ActionQueue.drop); nothing else is kept in memory."""
        for move_id in self.queue:
            self.cancel_move(move_id)
        self.queue = []


class Shelf(unittest.TestCase):
    """A private Audiobooks Sorted folder with real files, named as the app names them, and the catalog of those books."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='filing-'))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.sorted, self.library = self.base / 'Sorted', self.base / 'lib'
        for folder in (self.sorted, self.library, self.base / 'data'):
            folder.mkdir(parents=True)
        self.db = str(self.base / 'data' / 'c.sqlite3')
        self.now = 1_800_000_000.0
        self.count = 0
        with connect(self.db) as db:
            db.execute(JOBS)
            db.execute('CREATE TABLE storage_cleanup_jobs(job_id TEXT PRIMARY KEY,output_hash TEXT,state TEXT,reason TEXT,updated TEXT)')
            db.execute('CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,review TEXT,superseded INTEGER NOT NULL DEFAULT 0)')
            author_rules.seed(db)
        self.engine = Engine(self)
        self.filing = self.engine.rule_filing

    def book(self, author, title, series='', number='', language='Unknown', looked_up=True, payload=None):
        """One finished book in Sorted: a real file at the app's own name for it, its job and its completed cleanup. Its
        series look-up has ended with no series (looked_up) unless the book has one."""
        self.count += 1
        review = {'title': title, 'author': author, 'canonical_author': author, 'series': series, 'number': number, 'original_language': language,
                  'organization_policy': 'books-hierarchy-v2', 'anthology': False, 'multi_author': False}
        facts = {'policy_version': 'standing-17-v1', 'authors': [author], 'series_state': 'verified' if series else 'omitted_unknown'}
        path = Path(propose('', str(self.sorted), 'audiobook', {}, review, automatic_facts=copy.deepcopy(facts))['path'])
        path.parent.mkdir(parents=True, exist_ok=True)
        data = payload if payload is not None else (b'audiobook %03d ' % self.count) * 256
        path.write_bytes(data)
        with DirectoryBoundary(self.sorted, path.parent) as boundary:
            parents = [list(i) for i in boundary.identities]
        job_id, candidate = 'job-%03d' % self.count, 'book-%03d' % self.count
        output = {'job_id': job_id, 'root': str(self.sorted), 'final_path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
                  'parent_identity': parents, 'validation': {'passed': True}}
        manifest = {'job_id': job_id, 'candidate_id': candidate, 'candidate_revision': 1, 'root': str(self.library), 'output_root': str(self.sorted),
                    'sources': [{'path': str(self.library / ('%03d.mp3' % self.count))}], 'metadata': review, 'metadata_facts': facts}
        with connect(self.db) as db:
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (job_id, p._packed(manifest), p._digest(manifest), 'completed', 'completed', None, p._packed({'publication_intent': output}),
                        p._packed(output), '', '2026-11-%02dT00:00:%02d' % (1 + self.count // 60 % 28, self.count % 60), 'now'))
            db.execute("INSERT INTO storage_cleanup_jobs VALUES(?,?,'completed','','')", (job_id, output['sha256']))
            db.execute('INSERT INTO book_groups(id,revision,review) VALUES(?,?,?)', (candidate, 1, json.dumps(review, ensure_ascii=False)))
            if looked_up and not series:
                db.execute("INSERT INTO series_backfill VALUES(?,'none','',?,'now')", (job_id, json.dumps({'lookup_policy': series_backfill.LOOKUP_POLICY})))
        return job_id

    def path(self, job_id):
        """Where the catalog says the book is now (its receipt and its moves)."""
        return Path(self.engine.resolve(job_id, 'base')['final_path'])

    def english_title(self, job_id, title, source='https://www.wikidata.org/wiki/Q1', language='en'):
        """The detail look-up recorded the work's English title (gap_fill, state 'found')."""
        found = {'catalog': {'language': language, 'english_title': title, 'original_title': title, 'source_url': source}}
        with connect(self.db) as db:
            db.execute("INSERT OR REPLACE INTO gap_fill VALUES(?,?,'found','',?,'now')", (job_id, 'c', json.dumps({'found': found})))

    def held_series(self, job_id, series, number, url='https://fantlab.ru/work100', provider='fantlab', judged=True):
        """The series look-up found a series and holds the book (its series folder is another folder). 0.31.0's look-up
        judged it certain and records so (series_proof's number_from; Senua's 0.31.0 review, M3). judged=False: a series
        0.30.x found and held, in the record's shape on a copy of the live catalog (no judgment, an empty series_proof)."""
        record = {'series': series, 'number': number, 'provider': provider, 'source_url': url, 'research_receipts': [],
                  'series_proof': {'number_from': 'source'} if judged else {}}
        with connect(self.db) as db:
            db.execute("INSERT OR REPLACE INTO series_backfill VALUES(?,'held',?,?,'now')", (job_id, series_backfill.MOVE_WAITS, json.dumps(record, ensure_ascii=False)))

    def moves(self, where='1=1'):
        with connect(self.db) as db:
            if not book_move.have(db):
                return []
            return [dict(row) for row in db.execute('SELECT job_id,state,origin,override_id,target_path FROM book_moves WHERE %s ORDER BY created_utc,rowid' % where)]

    def filings(self, state=None):
        with connect(self.db) as db:
            return [dict(row) for row in db.execute('SELECT * FROM rule_filings' + (' WHERE state=?' if state else '') + ' ORDER BY created_utc,rowid', (state,) if state else ())]

    def settle(self, engine=None, limit=60):
        """Passes and queue runs until nothing is left: the last pass's numbers."""
        engine = engine or self.engine
        for _ in range(limit):
            value = engine.rule_filing.tick()
            if not engine.queue and not value['left']:
                return value
            engine.run_queue()
        self.fail('the rules did not come to an end')

    def restart(self):
        """A new run of the app on the same catalog and folder: move recovery first (MergeService._start_move_recovery)."""
        self.engine = Engine(self)
        self.filing = self.engine.rule_filing
        self.engine.mover().recover()
        return self.engine


class AppliedByTheRulesTests(Shelf):
    """B1: a certain change is made with no approval, once, to the one final place all rules give together."""

    def test_an_english_title_and_the_authors_folder_move_the_book_once_to_its_final_place(self):
        job = self.book(ROWLING, 'Гарри Поттер и тайная комната')
        self.english_title(job, 'Harry Potter and the Chamber of Secrets')
        old, before = self.path(job), sha(self.path(job))
        final = self.sorted / FILED / ('Harry Potter and the Chamber of Secrets - %s.m4b' % FILED)
        value = self.filing.tick()
        self.assertEqual((value['left'], value['moves_waiting'], value['writes_waiting'], value['renames_waiting']), (1, 1, 0, 0))
        self.assertEqual([(m['state'], m['origin'], m['target_path']) for m in self.moves()], [('queued', 'rules', str(final))],
                         'one move to the final name and folder, marked as the app\'s own (B6)')
        self.assertTrue(old.exists(), 'queued only: nothing moved yet')
        self.assertEqual(self.settle()['left'], 0)
        self.assertEqual(self.path(job), final)
        self.assertEqual(sha(final), before, 'the very same bytes')
        self.assertFalse(old.exists())
        self.assertFalse(old.parent.exists(), 'the folder it left was empty and is gone (ruling 71k)')
        self.assertEqual(len(self.moves()), 1, 'never one move per rule: both changes in one move')
        # Nothing more at any later pass: the book is where the rules file it.
        for _ in range(3):
            self.assertEqual(self.filing.tick()['left'], 0)
        self.assertEqual(len(self.moves()), 1)
        self.assertEqual(self.engine.sorting_moves()['items'], [])

    def test_control_without_the_title_rule_the_same_book_goes_to_another_name(self):
        job = self.book(ROWLING, 'Гарри Поттер и тайная комната')
        self.english_title(job, 'Harry Potter and the Chamber of Secrets')
        with mock.patch.object(sorting_moves, 'recorded_titles', lambda db: {}):
            self.settle()
        self.assertEqual(self.path(job).name, 'Гарри Поттер и тайная комната - %s.m4b' % FILED)

    def test_a_book_that_is_where_the_rules_file_it_is_never_touched(self):
        job = self.book('Хилл Джо', 'Страна Рождества')
        before = (self.path(job), sha(self.path(job)))
        value = self.settle()
        self.assertEqual((value['left'], value['could_not'], self.moves(), self.filings()), (0, 0, [], []))
        self.assertEqual((self.path(job), sha(self.path(job))), before)

    def test_a_doubtful_series_does_nothing_and_says_nothing(self):
        # The title's own number is 2; the series kept for it says 5: doubtful by the one rule (series_certainty, R18).
        job = self.book('Желязны Роджер', 'Хроники Амбера. Книга 2')
        self.held_series(job, 'Хроники Амбера', '5')
        before = (self.path(job), sha(self.path(job)))
        value = self.settle()
        self.assertEqual((value['left'], value['could_not'], value['waiting_for_lookup']), (0, 0, 0))
        self.assertEqual((self.moves(), self.filings(), self.filing.could_not()['entries']), ([], [], []))
        found = self.engine.sorting_moves()
        self.assertEqual((found['items'], found['refused']), ([], []), 'in no list at all')
        self.assertEqual(self.engine.series_backfill.entry(job)['state'], 'held', 'never approved')
        self.assertEqual((self.path(job), sha(self.path(job))), before)
        # Control: were the same record certain, the book would be listed to move.
        with mock.patch.object(sorting_moves, 'certain', lambda found, manifest: True):
            self.assertEqual([i['job_id'] for i in self.engine.sorting_moves()['items']], [job])

    def test_the_series_number_the_title_agrees_with_is_certain(self):
        job = self.book('Желязны Роджер', 'Хроники Амбера. Книга 2')
        self.held_series(job, 'Хроники Амбера', '2')
        self.assertEqual([(i['job_id'], i['items']) for i in self.engine.sorting_moves()['items']], [(job, ['series'])])

    def test_a_series_found_before_0_31_is_neither_written_nor_moved_until_it_is_looked_up_again(self):
        # Senua's 0.31.0 review, M3 (R18): 0.30.x held 55 live books with a series its adapters let through (Goodreads kept
        # the first of several series, FantLab had no universe check). Its stored fields pass the rule (the case above),
        # which proves nothing: the book is looked up again first, and until then the rules neither write nor move it.
        job = self.book('Желязны Роджер', 'Хроники Амбера. Книга 2')
        self.held_series(job, 'Хроники Амбера', '2', judged=False)
        before = (self.path(job), sha(self.path(job)))
        value = self.settle()
        self.assertEqual((value['left'], value['could_not']), (0, 0), 'without its old series it has no listed change at all')
        self.assertEqual((self.moves(), self.filings()), ([], []))
        self.assertEqual(self.engine.series_backfill.entry(job)['state'], 'held', 'never approved, never written')
        self.assertEqual(self.engine.sorting_moves()['items'], [], 'its old series is in no list')
        self.assertIn(job, self.engine.series_backfill.unsettled())
        self.assertEqual((self.path(job), sha(self.path(job))), before)
        # Control: the same series, judged by 0.31.0's look-up, is filed by the rules.
        self.held_series(job, 'Хроники Амбера', '2')
        self.assertEqual([(i['job_id'], i['items']) for i in self.engine.sorting_moves()['items']], [(job, ['series'])])
        self.assertNotIn(job, self.engine.series_backfill.unsettled())

    def test_a_book_waits_for_its_look_ups_to_end_so_it_moves_once(self):
        # R19: its series look-up has not ended; a series found later must not move it a second time.
        job = self.book(ROWLING, 'Waiting', looked_up=False)
        value = self.filing.tick()
        self.assertEqual((value['left'], value['waiting_for_lookup'], value['could_not'], self.moves()), (0, 1, 0, []))
        with connect(self.db) as db:  # the look-up ends with no series
            db.execute("INSERT INTO series_backfill VALUES(?,'none','',?,'now')", (job, json.dumps({'lookup_policy': series_backfill.LOOKUP_POLICY})))
        self.settle()
        self.assertEqual(self.path(job), self.sorted / FILED / ('Waiting - %s.m4b' % FILED))

    def test_a_book_whose_detail_look_up_has_not_ended_waits_too(self):
        job = self.book(ROWLING, 'Неизвестно')
        with connect(self.db) as db:
            row = db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (job,)).fetchone()
            manifest = json.loads(row[0])
            manifest['metadata_facts']['gap_search'] = {'background': ['original_title'], 'ask': {'title': 'Неизвестно', 'author': ROWLING}}
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?', (p._packed(manifest), p._digest(manifest), job))
        self.assertEqual(self.engine.gap_fill.unsettled(), {job})
        self.assertEqual((self.filing.tick()['waiting_for_lookup'], self.moves()), (1, []))
        with connect(self.db) as db:
            db.execute("INSERT INTO gap_fill VALUES(?,?,'none','','{}','now')", (job, 'c'))
        self.assertEqual(self.engine.gap_fill.unsettled(), set())
        self.settle()
        self.assertEqual(self.path(job).parent.name, FILED)

    def test_the_series_look_up_names_the_books_it_has_not_settled(self):
        waiting = self.book('Хилл Джо', 'Не найдено', looked_up=False)
        between = self.book('Хилл Джо', 'Между попытками', looked_up=False)
        again = self.book('Хилл Джо', 'Ещё раз', looked_up=False)
        approved = self.book('Хилл Джо', 'Одобрено', looked_up=False)
        self.book('Хилл Джо', 'Без серии')
        self.book('Хилл Джо', 'В серии', series='Серия', number='1')
        with connect(self.db) as db:
            db.execute("INSERT INTO series_backfill VALUES(?,'deferred','later','{\"next_attempt\": 9999999999}','now')", (between,))
            db.execute("INSERT INTO series_backfill VALUES(?,'held',?,'{}','now')", (again, series_backfill.REVIEW_REASON + ': x'))
            db.execute("INSERT INTO series_backfill VALUES(?,'deferred','waits','{\"move_approved\": true}','now')", (approved,))
        self.assertEqual(self.engine.series_backfill.unsettled(), {waiting, between, again}, 'an approved write that waits is work, not a look-up')


class SafetyTests(Shelf):
    """B2: never over a file, never under something else's hands, never a second copy; a refusal is listed with its reason."""

    def test_a_file_already_at_the_new_name_is_refused_listed_and_never_overwritten(self):
        job = self.book(ROWLING, 'Taken')
        stranger = self.sorted / FILED / ('Taken - %s.m4b' % FILED)
        stranger.parent.mkdir()
        stranger.write_bytes(b'another file')
        old, before = self.path(job), sha(self.path(job))
        value = self.settle()
        self.assertEqual((value['left'], value['could_not'], self.moves(), self.filings()), (0, 1, [], []))
        entry = self.filing.could_not()['entries'][0]
        self.assertEqual((entry['job_id'], entry['key'], entry['from_shown'], entry['to_shown']),
                         (job, 'name_exists', '%s\\Taken - %s.m4b' % (ROWLING, ROWLING), '%s\\Taken - %s.m4b' % (FILED, FILED)))
        self.assertEqual((stranger.read_bytes(), sha(old)), (b'another file', before))
        # F12: once the file in the way is gone the rules file the book by themselves, at the next pass.
        stranger.unlink()
        value = self.settle()
        self.assertEqual((value['could_not'], self.path(job), sha(stranger)), (0, stranger, before))

    def test_a_file_that_appears_after_the_move_was_queued_is_never_overwritten_either(self):
        job = self.book(ROWLING, 'Late')
        target = self.sorted / FILED / ('Late - %s.m4b' % FILED)
        old, before = self.path(job), sha(self.path(job))
        self.filing.tick()
        target.parent.mkdir()
        target.write_bytes(b'arrived meanwhile')
        done = self.engine.run_queue()
        self.assertEqual([(m['state'], m['cause']) for m in done], [('failed', 'target_exists')])
        self.assertEqual((target.read_bytes(), sha(old), self.path(job)), (b'arrived meanwhile', before, old))
        value = self.filing.tick()
        self.assertEqual([(f['state'], f['cause']) for f in self.filings()], [('failed', 'target_exists')])
        self.assertEqual((value['left'], value['could_not'], self.filing.could_not()['entries'][0]['key']), (0, 1, 'name_exists'))
        self.assertEqual(len(self.moves()), 1, 'not queued again while the file is in the way')

    def test_two_books_for_one_name_are_both_left_and_listed(self):
        first = self.book(ROWLING, 'Twin')
        second = self.book('Джоан Роулинг', 'Twin')
        value = self.settle()
        self.assertEqual((value['left'], value['could_not'], self.moves()), (0, 2, []))
        self.assertEqual({entry['job_id']: entry['key'] for entry in self.filing.could_not()['entries']}, {first: 'same_target', second: 'same_target'})

    def test_a_file_that_is_not_where_the_catalog_says_or_not_under_the_apps_name_is_listed_and_left(self):
        gone = self.book(ROWLING, 'Gone')
        self.path(gone).unlink()
        renamed = self.book(ROWLING, 'Renamed')
        with connect(self.db) as db:  # he renamed it himself: the catalog follows the file, the name is not the app's
            output = json.loads(db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (renamed,)).fetchone()[0])
            mine = Path(output['final_path']).with_name('My own name.m4b')
            Path(output['final_path']).rename(mine)
            db.execute('UPDATE audio_jobs SET output=? WHERE job_id=?', (p._packed(dict(output, final_path=str(mine))), renamed))
        value = self.settle()
        self.assertEqual((value['left'], self.moves()), (0, []))
        self.assertEqual({entry['job_id']: entry['key'] for entry in self.filing.could_not()['entries']}, {gone: 'not_where_recorded', renamed: 'not_app_name'})
        self.assertTrue(mine.exists())

    def test_a_book_something_else_still_works_on_is_skipped_until_that_has_ended(self):
        cleaning = self.book(ROWLING, 'Cleaning')
        held = self.book(ROWLING, 'Held')
        copies = self.book(ROWLING, 'Copies')
        ready = self.book(ROWLING, 'Ready')
        with connect(self.db) as db:
            db.execute("UPDATE storage_cleanup_jobs SET state='pending' WHERE job_id=?", (cleaning,))
            db.execute('CREATE TABLE source_cleanup(id TEXT PRIMARY KEY,job_id TEXT,state TEXT)')
            db.execute("INSERT INTO source_cleanup VALUES('c1',?,'needs_attention')", (held,))
            db.execute('CREATE TABLE recovery_retention(job_id TEXT PRIMARY KEY,state TEXT)')
            db.execute("INSERT INTO recovery_retention VALUES(?,'retained')", (copies,))
        value = self.settle()
        self.assertEqual((value['left'], value['settling'], value['on_hold'], value['could_not']), (0, 2, 1, 0), 'skipped, and in no list: nothing is wrong with them')
        self.assertEqual([m['job_id'] for m in self.moves()], [ready])
        for job in (cleaning, held, copies):
            self.assertEqual(self.path(job).parent.name, ROWLING)
        with connect(self.db) as db:  # each ends: the rules take the books up by themselves
            db.execute("UPDATE storage_cleanup_jobs SET state='completed'")
            db.execute("UPDATE source_cleanup SET state='completed'")
            db.execute("UPDATE recovery_retention SET state='deleted'")
        self.settle()
        self.assertEqual({self.path(job).parent.name for job in (cleaning, held, copies, ready)}, {FILED})

    def test_a_book_that_converts_again_is_not_listed(self):
        job = self.book(ROWLING, 'Again')
        with connect(self.db) as db:  # a newer job of the same book waits to convert
            row = db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (job,)).fetchone()
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)', ('job-newer', row['manifest'], row['manifest_hash'], 'pending', 'queued', None, '{}', None, '', '2027-01-01T00:00:00', 'now'))
        value = self.settle()
        self.assertEqual((value['left'], value['could_not'], self.moves()), (0, 0, []))
        self.assertEqual(self.path(job).parent.name, ROWLING)
        with connect(self.db) as db:  # control: without the newer job the same book is filed
            db.execute("DELETE FROM audio_jobs WHERE job_id='job-newer'")
        self.settle()
        self.assertEqual(self.path(job).parent.name, FILED)

    def test_a_retained_job_is_left_as_published_in_retained_runtime_mode(self):
        retained = self.book(ROWLING, 'Retained')
        other = self.book(ROWLING, 'Other')
        self.engine.retained = frozenset({retained})
        value = self.settle()
        self.assertEqual((value['left'], value['could_not']), (0, 0))
        self.assertEqual([m['job_id'] for m in self.moves()], [other])
        self.assertEqual((self.path(retained).parent.name, self.path(other).parent.name), (ROWLING, FILED))
        refused = {i['job_id']: i['refused_key'] for i in self.engine.sorting_moves()['refused']}
        self.assertEqual(refused, {retained: 'data_move'})
        self.engine.retained = frozenset()  # control: outside that mode the same book is filed
        self.settle()
        self.assertEqual(self.path(retained).parent.name, FILED)

    def test_a_move_cut_after_the_rename_is_finished_at_the_next_start_with_the_file_intact(self):
        job = self.book(ROWLING, 'Cut')
        old, before = self.path(job), sha(self.path(job))
        final = self.sorted / FILED / ('Cut - %s.m4b' % FILED)
        self.filing.tick()
        self.engine.crash_at = 'renamed'  # the file is renamed; the app ends before the catalog says so
        with self.assertRaises(Crash):
            self.engine.run_queue()
        self.assertEqual((old.exists(), final.exists(), self.moves()[0]['state']), (False, True, 'rename_intent'))
        # Before recovery has run, a pass queues nothing for the book (its move is still in the journal).
        fresh = Engine(self)
        self.assertEqual((fresh.rule_filing.tick()['moves_running'], fresh.queue, len(self.moves())), (1, [], 1))
        engine = self.restart()
        value = self.settle(engine)
        self.assertEqual((value['left'], value['record']['count']), (0, 1))
        self.assertEqual((self.path(job), sha(final), old.exists()), (final, before, False))
        self.assertEqual([(m['state'], m['origin']) for m in self.moves()], [('complete', 'rules')], 'finished, not done a second time')
        self.assertEqual([f['state'] for f in self.filings()], ['done'])

    def test_a_copy_cut_before_it_was_placed_leaves_the_book_where_it_was_and_is_tried_again(self):
        job = self.book(ROWLING, 'Copied')
        old, before = self.path(job), sha(self.path(job))
        final = self.sorted / FILED / ('Copied - %s.m4b' % FILED)
        self.engine.same_volume = lambda a, b: False  # as to another volume: copy, verify, publish, then remove the old file
        self.filing.tick()
        self.engine.crash_at = 'copied'
        with self.assertRaises(Crash):
            self.engine.run_queue()
        engine = self.restart()
        self.assertEqual((old.exists(), sha(old), final.exists(), [x.name for x in final.parent.iterdir()]), (True, before, False, []), 'the temporary is gone, the book untouched')
        value = engine.rule_filing.tick()
        self.assertEqual(([f['state'] for f in self.filings()], value['left'], value['could_not']), (['failed'], 0, 1))
        entry = engine.rule_filing.could_not()['entries'][0]
        self.assertEqual((entry['key'], entry['tries'], entry['retries']), (rule_filing.DID_NOT_FINISH, 1, True))
        self.assertEqual(len(self.moves()), 1, 'not tried again at once')
        self.now += rule_filing.SPACING + 1
        engine.same_volume = lambda a, b: False
        value = self.settle(engine)
        self.assertEqual((value['could_not'], self.path(job), sha(final), old.exists()), (0, final, before, False))

    def test_a_drive_that_does_not_answer_plans_nothing_and_lists_nothing(self):
        jobs = [self.book(ROWLING, 'Away %d' % n) for n in range(3)]
        away = self.base / 'Unplugged'
        self.sorted.rename(away)  # the drive is gone: no file of the library can be seen
        try:
            value = self.filing.tick()
            self.assertEqual((value, self.moves(), self.filings(), self.filing.could_not()['entries']), (None, [], [], []),
                             'never "not where the catalog says" for a whole library that is only away')
            self.assertEqual(self.filing.summary()['left'], 0, 'a pass never started reports nothing; a started one is not known yet')
        finally:
            away.rename(self.sorted)
        self.assertEqual(self.settle()['record']['count'], 3, 'back again: the same pass files them')
        # Control: with the root check taken out, the same outage lists every book as not where the catalog says.
        self.book(ROWLING, 'Away later')
        self.sorted.rename(away)
        try:
            with mock.patch.object(rule_filing.RuleFiling, '_answers', staticmethod(lambda root: True)):
                self.assertEqual(self.filing.tick()['could_not'], 1)
        finally:
            away.rename(self.sorted)
        self.assertEqual(self.settle()['could_not'], 0)

    def test_a_move_that_waits_for_a_restart_holds_no_place_and_a_passing_refusal_is_no_try(self):
        first = self.book(ROWLING, 'A cut move')  # the list is in path order: this one is put in hand first
        others = [self.book(ROWLING, 'Other %d' % n) for n in range(3)]
        self.filing.tick()
        self.engine.crash_at = 'renamed'
        with self.assertRaises(Crash):
            self.engine.run_queue()  # the first move is cut and stays in the journal; nothing runs it in this session
        self.engine.crash_at = None
        self.engine._move_running = lambda move_id: False
        value = self.filing.tick()
        self.assertEqual((value['moves_running'], len(self.engine.queue)), (1, rule_filing.FEED), 'two more are in hand beside the one that waits')
        self.engine.run_queue()
        refuse = mock.Mock(side_effect=ValueError('Move was not accepted. Nothing was moved.'))
        with mock.patch.object(self.engine, '_sorting_move', refuse):
            for _ in range(rule_filing.REFUSALS + 2):
                value = self.filing.tick()
        self.assertEqual((value['left'], value['could_not'], self.filings('failed')), (2, 0, []), 'asked again at each pass, never recorded as failed')
        self.filing.tick()
        self.engine.run_queue()
        self.assertEqual(self.filing.tick()['left'], 1, 'only the one that waits for the restart')
        self.assertEqual({self.path(job).parent.name for job in others}, {FILED})
        self.assertEqual(self.path(first).parent.name, ROWLING, 'the cut move is the next start\'s to finish (the catalog still names the old place)')

    def test_a_change_that_cannot_finish_is_tried_three_times_then_left_and_listed(self):
        job = self.book(ROWLING, 'Changed')
        old = self.path(job)
        old.write_bytes(bytes(reversed(old.read_bytes())))  # other bytes than the receipt's: the move refuses it every time
        changed = sha(old)
        for attempt in range(1, rule_filing.TRIES + 3):
            self.filing.tick()
            self.engine.run_queue()
            self.filing.tick()
            self.now += rule_filing.SPACING + 1
        self.assertEqual([m['state'] for m in self.moves()], ['failed'] * rule_filing.TRIES, 'tries never pile up')
        entry = self.filing.could_not()['entries'][0]
        self.assertEqual((entry['key'], entry['tries'], entry['retries'], self.filing.summary()['left']), (rule_filing.DID_NOT_FINISH, rule_filing.TRIES, False, 0))
        self.assertEqual((self.path(job), sha(old)), (old, changed), 'never moved, never altered')


class PacingTests(Shelf):
    """B3: a few books in hand at a time, a Pause holds them, a Quit loses nothing and repeats nothing."""

    def test_only_a_few_books_are_in_hand_and_the_counts_are_whole(self):
        jobs = [self.book(ROWLING, 'Book %02d' % n) for n in range(9)]
        value = self.filing.tick()
        self.assertEqual((len(self.engine.queue), value['left'], value['moves_waiting'], value['moves_running']), (rule_filing.FEED, 9, 9, 0))
        self.assertEqual(value['next_move']['job_id'], jobs[0])
        left = [value['left']]
        while self.engine.queue:
            self.engine.run_queue()
            value = self.filing.tick()
            left.append(value['left'])
            self.assertLessEqual(len(self.engine.queue), rule_filing.FEED)
        self.assertEqual(left, [9, 7, 5, 3, 1, 0], 'the number only goes down')
        self.assertEqual(value['record']['count'], 9)

    def test_a_pause_at_launch_moves_nothing_and_resume_goes_on(self):
        jobs = [self.book(ROWLING, 'Paused %d' % n) for n in range(3)]
        self.engine.paused = True
        for _ in range(3):
            value = self.filing.tick()
        self.assertEqual((value['paused'], value['left'], self.engine.queue, self.moves(), self.filings()), (True, 3, [], [], []))
        self.assertEqual({self.path(job).parent.name for job in jobs}, {ROWLING})
        self.engine.paused = False  # control: the same pass with no Pause files them
        self.settle()
        self.assertEqual({self.path(job).parent.name for job in jobs}, {FILED})

    def test_the_apps_own_queued_move_is_held_by_a_pause_and_a_move_he_queued_is_not(self):
        paused = [True]
        merge = SimpleNamespace(_jobs_pause_saved=lambda: paused[0], cleanup=None, operation_lock=None)
        server = SimpleNamespace(merge=merge, loading=None, closing=False, inventory=None, scan_active=lambda: False)
        queue = action_queue.ActionQueue(server, store=None)
        own = {'id': 'a', 'action': 'move', 'book_id': 'b1', 'title': 'T', 'args': {'move_id': 'm1', 'origin': 'rules'}}
        his = {'id': 'b', 'action': 'move', 'book_id': 'b2', 'title': 'T', 'args': {'move_id': 'm2', 'origin': 'user'}}
        with mock.patch.object(book_delete, 'processing', lambda merge, book: False):
            self.assertEqual((queue.item_blocker(own), queue.item_blocker(his)), ('paused', None))
            paused[0] = False
            self.assertEqual(queue.item_blocker(own), None)
        self.assertEqual((queue._shown(own)['origin'], queue._shown(his)['origin']), ('rules', 'user'), 'the page shows no Cancel for the first')
        self.assertTrue(action_queue.held_by_pause(own))
        self.assertFalse(action_queue.held_by_pause(his))

    def test_a_quit_with_300_left_queues_the_rest_once_after_the_restart(self):
        jobs = [self.book(ROWLING, 'Volume %03d' % n, payload=b'%03d' % n) for n in range(300)]
        with mock.patch.object(rule_filing, 'FEED', 40):
            value = self.filing.tick()
            self.assertEqual((value['left'], len(self.engine.queue)), (300, 40))
            self.engine.run_queue()
            value = self.filing.tick()  # 40 are done; the next 40 are queued and the app is quit before one of them runs
            self.assertEqual((value['left'], value['record']['count'], len(self.engine.queue)), (260, 40, 40))
            self.engine.quit()
            engine = self.restart()
            value = engine.rule_filing.tick()
            self.assertEqual((value['left'], value['record']['count'], len(engine.queue)), (260, 40, 40), 'the rest is derived again from the rules, with nothing pressed')
            self.assertEqual(self.settle(engine)['record']['count'], 300)
        done = {}
        for move in self.moves("state='complete'"):
            done[move['job_id']] = done.get(move['job_id'], 0) + 1
        self.assertEqual((len(done), set(done.values())), (300, {1}), 'every book moved, and each exactly once')
        self.assertEqual(len(self.moves("state='cancelled'")), 40, 'the 40 the Quit took back; each was queued again once')
        self.assertEqual(len(self.moves()), 340)
        self.assertEqual({self.path(job).parent.name for job in jobs}, {FILED})
        self.assertEqual((len(self.filings('done')), len(self.filings('open')), len(self.filings('failed'))), (300, 0, 0), 'one record entry per book')


class HisChoiceTests(Shelf):
    """B6 (R26): a folder he chooses after the app moved a book is kept; the rules never move it back."""

    def test_choose_folder_after_the_move_is_kept_for_good(self):
        job = self.book(ROWLING, 'Mine')
        self.settle()
        moved = self.path(job)
        mine = self.sorted / 'My shelf'
        mine.mkdir()
        self.engine._sorting_move(job, str(mine / moved.name), origin='user', override_id='override-1')  # Choose folder…: his choice, his move
        self.engine.run_queue()
        self.assertEqual(self.path(job), mine / moved.name)
        for _ in range(3):
            value = self.filing.tick()
        self.assertEqual((value['left'], value['could_not'], self.engine.queue), (0, 0, []), 'not moved back, and not listed: his decision')
        self.assertEqual(self.path(job), mine / moved.name)
        self.assertEqual({i['job_id']: i['refused_key'] for i in self.engine.sorting_moves()['refused']}, {job: 'chosen_folder'})
        self.assertEqual([(m['origin'], m['state']) for m in self.moves()], [('rules', 'complete'), ('user', 'complete')])
        self.assertEqual(self.filing.record()['count'], 1, 'his own move is not in the record of the app\'s')

    def test_control_a_move_with_no_folder_of_his_is_still_filed_by_the_rules(self):
        # The same move without his chosen folder (as Use computed folder makes it): the rules take the book up again.
        job = self.book(ROWLING, 'Mine')
        self.settle()
        moved = self.path(job)
        other = self.sorted / 'Elsewhere'
        other.mkdir()
        self.engine._sorting_move(job, str(other / moved.name), origin='user')
        self.engine.run_queue()
        self.settle()
        self.assertEqual(self.path(job), moved)

    def test_a_rule_that_changes_later_moves_a_book_the_rules_filed_before(self):
        # B8's way in: a learned author rule is corrected on evidence; the finished books follow, from where they are.
        job = self.book('Cixin Liu', 'The Dark Forest', language='Other')
        self.assertEqual(self.settle()['record']['count'], 0, 'no evidence of the order: the folder stays as it is (R23)')
        self.assertEqual(self.path(job).parent.name, 'Cixin Liu')
        with connect(self.db) as db:
            author_rules.append(db, 'same_as', 'Cixin Liu', target='Liu Cixin', actor='assistant', source='https://www.wikidata.org/wiki/Q607588')
        self.assertEqual(self.settle()['record']['count'], 1)
        self.assertEqual(self.path(job), self.sorted / 'Liu Cixin' / 'The Dark Forest - Liu Cixin.m4b')
        with connect(self.db) as db:  # and a later rule moves it on, once more, from where the rules put it
            author_rules.append(db, 'same_as', 'Cixin Liu', target='Liu Cixin (author)', actor='user')
        self.assertEqual(self.settle()['record']['count'], 2)
        self.assertEqual(self.path(job).parent.name, 'Liu Cixin (author)')


class AuthorOrderTests(Shelf):
    """B8 (R23): a Latin author name whose order the app cannot tell stays as filed, and is put in order only on evidence
    the catalog already holds; the finished books then follow. No request is made for it."""

    def detail(self, job_id, author_latin, language, credit, source='https://www.wikidata.org/wiki/Q607588'):
        found = {'catalog': {'language': language, 'author_latin': author_latin, 'source_url': source}}  # no title in it: the name only
        with connect(self.db) as db:
            db.execute("INSERT OR REPLACE INTO gap_fill VALUES(?,?,'found','',?,'2026-11-23T00:00:00Z')", (job_id, 'c', json.dumps({'found': found, 'ask': {'title': 'x', 'author': credit}})))

    def learned(self, credit, target):
        with connect(self.db) as db:
            author_rules.append(db, 'same_as', credit, target=target, actor='assistant', source='https://fantlab.ru/work1')

    def test_a_rule_learned_by_the_old_guess_is_corrected_on_recorded_evidence_and_the_books_follow(self):
        self.learned('Лю Цысинь', 'Cixin Liu')
        job = self.book('Cixin Liu', 'The Dark Forest', language='Other')
        self.detail(job, 'Liu Cixin', 'zh', 'Лю Цысинь')
        self.assertEqual([(e['name'], e['ordered'], e['credit']) for e in rule_filing.author_orders(self.db)], [('Cixin Liu', 'Liu Cixin', 'Лю Цысинь')])
        self.settle()
        self.assertEqual(self.path(job), self.sorted / 'Liu Cixin' / 'The Dark Forest - Liu Cixin.m4b')
        self.assertEqual(author_rules.load(self.db).same_as('Лю Цысинь'), 'Liu Cixin', 'the next book of his is filed there too')
        self.assertEqual(rule_filing.author_orders(self.db), [], 'settled: nothing is written a second time')
        with connect(self.db) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM author_rules WHERE actor='assistant'").fetchone()[0], 2)
        self.assertEqual(self.filing.record()['entries'][0]['reasons'], [{'kind': 'author', 'name': 'Liu Cixin'}])

    def test_the_learned_rules_own_credit_is_evidence_enough(self):
        # «Лю Цысинь» is written surname first, so "Liu" is the surname: no record of any book is needed for it.
        self.learned('Лю Цысинь', 'Cixin Liu')
        job = self.book('Cixin Liu', 'The Dark Forest', language='Other')
        self.assertEqual([(e['name'], e['ordered']) for e in rule_filing.author_orders(self.db)], [('Cixin Liu', 'Liu Cixin')])
        self.settle()
        self.assertEqual(self.path(job).parent.name, 'Liu Cixin')

    def test_with_no_evidence_the_folder_stays_and_nothing_is_written(self):
        # A name the files give in Latin letters only, with no rule and no record: nothing shows its order.
        job = self.book('Cixin Liu', 'The Dark Forest', language='Other')
        other = self.book('Хилл Джо', 'Страна Рождества')
        self.detail(other, 'Joe Hill', 'en', 'Хилл Джо')  # a record of another author says nothing of this one
        value = self.settle()
        self.assertEqual((rule_filing.author_orders(self.db), value['record']['count'], value['could_not']), ([], 0, 0), 'it stays, and nothing says so (R23)')
        self.assertEqual(self.path(job).parent.name, 'Cixin Liu')
        with connect(self.db) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM author_rules WHERE actor='assistant'").fetchone()[0], 0)

    def test_an_unruled_name_is_put_in_order_by_the_credit_in_the_files(self):
        job = self.book('Lev Grossman', 'The Magicians', language='Other')
        self.detail(job, 'Lev Grossman', 'en', 'Гроссман Лев')
        import canonical_names
        self.assertEqual(canonical_names.latin_order('Lev Grossman')[1], canonical_names.ORDER_UNKNOWN, 'the premise: the name alone does not show its order')
        self.settle()
        self.assertEqual(self.path(job).parent.name, 'Grossman Lev')
        self.assertEqual(author_rules.load(self.db).same_as('Lev Grossman'), 'Grossman Lev', 'kept as a learned rule, so the author\'s other books follow')

    def test_two_records_that_disagree_decide_nothing(self):
        self.learned('Лю Цысинь', 'Cixin Liu')
        first = self.book('Cixin Liu', 'One', language='Other')
        second = self.book('Cixin Liu', 'Two', language='Other')
        self.detail(first, 'Liu Cixin', 'zh', 'Лю Цысинь')
        self.detail(second, 'Cixin Liu', 'zh', 'Лю Цысинь')  # a source that writes it the other way round
        self.assertEqual(rule_filing.author_orders(self.db), [])

    def test_a_name_he_ruled_himself_is_never_reordered(self):
        with connect(self.db) as db:
            author_rules.append(db, 'same_as', 'Лю Цысинь', target='Cixin Liu', actor='user')
        job = self.book('Cixin Liu', 'The Dark Forest', language='Other')
        self.detail(job, 'Liu Cixin', 'zh', 'Лю Цысинь')
        self.settle()
        self.assertEqual((rule_filing.author_orders(self.db), self.path(job).parent.name), ([], 'Cixin Liu'))


class RecordTests(Shelf):
    """B4 and B5: what was renamed or moved, why, from which source; and the list of what could not be."""

    def test_an_entry_says_where_from_where_to_when_and_why_with_the_source(self):
        job = self.book(ROWLING, 'Гарри Поттер и тайная комната')
        self.english_title(job, 'Harry Potter and the Chamber of Secrets', source='https://www.wikidata.org/wiki/Q47209')
        start = self.path(job)
        self.settle()
        found = self.filing.record()
        self.assertEqual((found['count'], found['matching'], len(found['entries'])), (1, 1, 1))
        entry = found['entries'][0]
        self.assertEqual((entry['book_id'], entry['job_id'], entry['title'], entry['author'], entry['in_app']), ('book-001', job, 'Harry Potter and the Chamber of Secrets', FILED, True))
        self.assertEqual((entry['from'], entry['to']), (str(start), str(self.path(job))))
        self.assertEqual((entry['from_shown'], entry['to_shown']), ('%s\\Гарри Поттер и тайная комната - %s.m4b' % (ROWLING, ROWLING),
                                                                   '%s\\Harry Potter and the Chamber of Secrets - %s.m4b' % (FILED, FILED)))
        self.assertEqual(entry['kinds'], ['title', 'author'])
        self.assertEqual(entry['reasons'], [{'kind': 'title', 'title': 'Harry Potter and the Chamber of Secrets', 'provider': 'wikidata', 'source_url': 'https://www.wikidata.org/wiki/Q47209'},
                                            {'kind': 'author', 'name': FILED}])
        self.assertEqual((entry['at'], found['last_at']), (self.filings('done')[0]['done_utc'], entry['at']))
        with connect(self.db) as db:  # the book is deleted from the app later: the entry stays and says so
            db.execute('UPDATE book_groups SET superseded=1')
        self.assertFalse(self.filing.record()['entries'][0]['in_app'])

    def test_the_record_is_newest_first_capped_and_its_search_reads_every_entry(self):
        for n in range(12):
            self.book(ROWLING, 'Том %02d' % n)
        self.book('Джоан Роулинг', 'Особая Книга')
        self.settle()
        with connect(self.db) as db:
            self.assertEqual(rule_filing.totals(db)[0], 13)
            capped = rule_filing.record(db, str(self.sorted), limit=5)
            self.assertEqual((capped['count'], capped['matching'], len(capped['entries'])), (13, 13, 5))
            times = [entry['at'] for entry in rule_filing.record(db, str(self.sorted))['entries']]
            self.assertEqual(times, sorted(times, reverse=True))
            found = rule_filing.record(db, str(self.sorted), search='особая книга', limit=5)
            self.assertEqual((found['count'], found['matching'], [e['title'] for e in found['entries']]), (13, 1, ['Особая Книга']), 'beyond the newest five, case aside')
            self.assertEqual(rule_filing.record(db, str(self.sorted), search='джоан роулинг')['matching'], 1, 'the path it was in')
            self.assertEqual(rule_filing.record(db, str(self.sorted), search='no such text')['matching'], 0)

    def test_nothing_is_recorded_for_a_change_that_did_not_happen(self):
        job = self.book(ROWLING, 'Taken')
        stranger = self.sorted / FILED / ('Taken - %s.m4b' % FILED)
        stranger.parent.mkdir()
        stranger.write_bytes(b'x')
        self.settle()
        self.assertEqual((self.filing.record()['count'], self.filing.summary()['record']), (0, {'count': 0, 'last_at': None}))


class SeriesWriteThenMoveTests(unittest.TestCase):
    """B1 end to end on a real audiobook (ffmpeg): a certain series found is written into the file by the series look-up's own
    write (retag, proofs, no-replace rename, catalog) and the app's verified move then takes the book, once, to the one
    final place: the English series folder under the English title. Both doors are opened only through the list."""

    def setUp(self):
        import test_series_backfill as base
        from test_sorting_030 import cycle
        short = Path(__file__).resolve().parents[1] / 'scratch' / 's'  # a short folder: the book goes one folder deeper
        short.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=short, prefix='')
        self.addCleanup(temp.cleanup)
        original = base.Library.__init__.__globals__['propose']

        def v2(path, root, kind, metadata, review=None, automatic_facts=None):  # the Library's book as books-hierarchy-v2 files it
            return original(path, root, kind, metadata, dict(review or {}, organization_policy='books-hierarchy-v2'), automatic_facts)
        with mock.patch.object(base, 'propose', v2):
            self.lib = lib = base.Library(Path(temp.name), separate_sorted=True)
        with connect(lib.db) as db:
            manifest = json.loads(db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (lib.job_id,)).fetchone()[0])
            manifest['metadata'].update(organization_policy='books-hierarchy-v2', original_language='Unknown')
            manifest['metadata_facts'] = {'policy_version': 'standing-17-v1', 'authors': [lib.review['author']], 'series_state': 'omitted_unknown'}
            text, digest = series_backfill.encoded(manifest)
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?', (text, digest, lib.job_id))
            db.execute('CREATE TABLE public_research_cache(url TEXT PRIMARY KEY, raw TEXT, sha256 TEXT, fetched REAL)')
            cycle(db, 777, 'Нормальное аномальное', 'Normal Abnormal', 'en')  # FantLab: the cycle of a work written in English
            db.execute('ALTER TABLE book_groups ADD COLUMN superseded INTEGER NOT NULL DEFAULT 0')
        self.queue = []
        self.merge = merge = lib.merge()
        merge.inventory.output_root = str(lib.root)
        merge.draining = False
        merge._sorting_move = self.queue_move
        merge.cancel_move = lambda move_id: None
        self.research = SimpleNamespace(_series_goodreads=lambda *a: None, _series_wikidata=lambda *a: None, _series_publisher=lambda *a: None, _series_litres=lambda *a: None,
                                        _series_fantlab=lambda *a: {'provider': 'fantlab', 'name': 'Нормальное аномальное', 'number': '10', 'number_from': 'counted',
                                                                    'source_url': 'https://fantlab.ru/work777'})
        merge.series_backfill = self.backfill = SeriesBackfill(merge, research=self.research, stage=lib.base / 'proof-stage')
        merge.gap_fill = GapFill(merge)
        with connect(lib.db) as db:  # the detail look-up recorded the work's English title
            found = {'catalog': {'language': 'en', 'english_title': 'White Nights Ghosts', 'original_title': 'White Nights Ghosts', 'source_url': 'https://fantlab.ru/work778'}}
            db.execute("INSERT INTO gap_fill VALUES(?,?,'found','',?,'now')", (lib.job_id, lib.candidate, json.dumps({'found': found})))
        merge.rule_filing = self.filing = rule_filing.RuleFiling(merge)
        self.final = lib.root / lib.review['author'] / 'Normal Abnormal' / ('Normal Abnormal - 10 - White Nights Ghosts - %s.m4b' % lib.review['author'])

    def resolve(self, job_id, kind):
        with connect(self.lib.db) as db:
            record = json.loads(db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (job_id,)).fetchone()[0])
        return PublicationBindings(str(self.lib.db)).current(record, kind)[0]

    def queue_move(self, job_id, target, origin='user'):
        lib = self.lib
        start = book_move.location(self.resolve(job_id, 'base'))
        with connect(lib.db) as db:
            move = book_move.plan(db, job_id=job_id, kind='base', candidate_id=lib.candidate, start=start, folder=os.path.dirname(target), root=str(lib.root),
                                  name=os.path.basename(target), origin=origin)
        self.queue.append(move['move_id'])
        return {'state': 'move_queued', 'move': book_move.view(move)}

    def run_queue(self):
        lib = self.lib
        mover = book_move.Mover(lambda: connect(lib.db), self.resolve, sources=lambda: (str(lib.source_root),), output_root=str(lib.root),
                                remove_folder=book_delete._remove_folder, protected_roots=lambda: (str(lib.root), str(lib.source_root)))
        return [mover.run(self.queue.pop(0)) for _ in list(self.queue)]

    def moves(self):
        with connect(self.lib.db) as db:
            return [tuple(row) for row in db.execute('SELECT state,origin,target_path FROM book_moves ORDER BY created_utc,rowid')] if book_move.have(db) else []

    def test_the_series_is_written_and_the_book_moves_once_to_its_english_named_place(self):
        from quicktime_chapters import media_unchanged
        lib, backfill = self.lib, self.backfill
        keep = lib.base / 'original-copy.m4b'
        shutil.copyfile(lib.path, keep)
        # The look-up finds the series and, as before milestone B, writes nothing by itself: the book is held.
        backfill.run_pass()
        self.assertEqual(lib.state(backfill), ('held', series_backfill.MOVE_WAITS))
        self.assertEqual((sha(lib.path), self.filing.summary()['left']), (lib.original, 0))
        # The rules' pass approves it through the list, bound to the list's own final path.
        value = self.filing.tick()
        self.assertEqual((value['left'], value['writes_waiting'], value['moves_waiting']), (1, 1, 0))
        entry = backfill.entry(lib.job_id)
        self.assertEqual((entry['state'], entry['record']['approved_by'], entry['record']['approved_target'], entry['record']['approved_found']['name']),
                         ('pending', 'rules', str(self.final), 'Normal Abnormal'))
        self.assertEqual(sha(lib.path), lib.original, 'approved, not yet written')
        backfill.run_pass()  # the write: retag, proofs, rename in its own folder, catalog; then its move is asked for
        entry = backfill.entry(lib.job_id)
        self.assertEqual((entry['state'], entry['reason']), ('done', ''))
        placed = Path(entry['record']['new_path'])
        self.assertEqual((placed.parent, placed.exists(), lib.path.exists()), (lib.path.parent, True, False))
        self.assertEqual(self.moves(), [('queued', 'rules', str(self.final))], 'the move after the write is the app\'s own too (no Cancel, R26)')
        value = self.filing.tick()
        self.assertEqual((value['left'], value['writes_waiting'], value['moves_waiting']), (1, 0, 1), 'one book, counted once until both are done')
        self.run_queue()
        value = self.filing.tick()
        self.assertEqual((value['left'], value['record']['count'], value['could_not']), (0, 1, 0))
        self.assertTrue(self.final.exists())
        self.assertFalse(placed.exists())
        self.assertEqual(self.resolve(lib.job_id, 'base')['final_path'], str(self.final), 'the catalog follows')
        self.assertEqual(self.moves(), [('complete', 'rules', str(self.final))], 'moved once')
        media_unchanged(keep, self.final, threading.Event())  # every media byte and sample table as in the file before
        found = self.filing.record()['entries'][0]
        self.assertEqual((found['from'], found['to'], found['title'], found['kinds']), (str(lib.path), str(self.final), 'White Nights Ghosts', ['series', 'title']),
                         'one entry, from where it was to where it ended; the in-between name is not in it')
        self.assertEqual(found['reasons'], [{'kind': 'series', 'name': 'Normal Abnormal', 'number': '10', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work777'},
                                            {'kind': 'title', 'title': 'White Nights Ghosts', 'provider': 'fantlab', 'source_url': 'https://fantlab.ru/work778'}])
        # And nothing more, at any later pass.
        backfill.run_pass()
        self.assertEqual((self.filing.tick()['left'], len(self.moves()), self.queue), (0, 1, []))

    def test_a_pause_holds_the_approved_write(self):
        lib, backfill = self.lib, self.backfill
        backfill.run_pass()
        self.filing.tick()
        import pause_state
        with connect(lib.db) as db:
            pause_state.record(db, 'jobs', 'user', 'Audiobook jobs paused')
        backfill.run_pass()
        self.assertEqual((sha(lib.path), backfill.entry(lib.job_id)['state'], self.moves()), (lib.original, 'deferred', []), 'approved, and held by his Pause')
        self.assertEqual(backfill.summary()['write_waiting'], 1, 'a write that waits, never a look-up between tries')
        value = self.filing.tick()
        self.assertEqual((value['paused'], value['left'], value['writes_waiting']), (True, 1, 1))
        with connect(lib.db) as db:
            pause_state.clear(db, 'jobs')
        self.now = backfill.clock() + 120
        backfill.clock = lambda: self.now
        backfill.run_pass()
        self.assertEqual(backfill.entry(lib.job_id)['state'], 'done')

    def test_control_the_look_up_alone_still_writes_nothing(self):
        # The guard is not flipped: without the rules' pass the found series stays held, at every pass.
        self.assertEqual(series_backfill.WRITE_WITHOUT_APPROVAL, 'hold')
        for _ in range(3):
            self.backfill.run_pass()
        self.assertEqual((self.lib.state(self.backfill), sha(self.lib.path), self.moves()), (('held', series_backfill.MOVE_WAITS), self.lib.original, []))


class WorkViewTests(unittest.TestCase):
    """B7: a rename or move of a finished book is main work; the counts are whole; nothing guesses 'all done'."""

    def state(self, filing, rows=(), jobs=None):
        pending, state, reasons = background_work.finished_state(list(rows), [], jobs or {}, {}, {}, [], filing)
        return state, pending, reasons

    def test_books_left_to_file_are_main_work_never_background_only_or_all_done(self):
        self.assertEqual(self.state(None)[0], 'all_done', 'an engine without the pass')
        self.assertEqual(self.state({'known': True, 'left': 0, 'could_not': 0})[0], 'all_done')
        state, pending, reasons = self.state({'known': True, 'left': 212, 'could_not': 0})
        self.assertEqual((state, pending['filing'], pending['any']), ('continues', 212, True))
        moving = {'kind': 'move', 'state': 'running', 'step': None}
        self.assertEqual(self.state({'known': True, 'left': 212, 'could_not': 0}, rows=[moving])[0], 'working')
        self.assertEqual(self.state({'known': True, 'left': 212, 'could_not': 0}, jobs={'state': 'Paused'})[0], 'paused')

    def test_the_pass_that_has_not_counted_yet_is_not_all_done(self):
        state, pending, _ = self.state({'known': False, 'left': None, 'could_not': None})
        self.assertEqual((state, pending['filing'], pending['could_not_file']), ('unknown', None, 0))

    def test_books_that_could_not_be_moved_hold_nothing_back(self):
        state, pending, reasons = self.state({'known': True, 'left': 0, 'could_not': 12})
        self.assertEqual((state, pending['could_not_file'], pending['any'], reasons), ('all_done', 12, False, []))

    def test_the_view_carries_the_whole_counts_and_the_first_books_blockers(self):
        summary = {'known': True, 'left': 5, 'paused': False, 'writes_waiting': 2, 'moves_waiting': 3, 'renames_waiting': 0, 'could_not': 1,
                   'next_write': {'job_id': 'j1', 'book_id': 'b1', 'title': 'One', 'move_id': None},
                   'next_move': {'job_id': 'j2', 'book_id': 'b2', 'title': 'Two', 'move_id': 'm2'}}
        merge = SimpleNamespace(rule_filing=SimpleNamespace(summary=lambda: dict(summary)))
        queue = {'queue_running': None, 'queued_actions': [{'id': 'q1', 'action': 'move', 'book_id': 'b2', 'title': 'Two', 'position': 1, 'origin': 'rules',
                                                           'blocker': {'kind': 'book', 'cause': 'book', 'title': None, 'book_id': None, 'count': None}}]}
        work = background_work.view(SimpleNamespace(merge=merge, active_library=''), {}, {}, queue, False, None)
        filing = work['filing']
        self.assertEqual((filing['left'], filing['writes_waiting'], filing['moves_waiting'], filing['renames_waiting']), (5, 2, 3, 0))
        self.assertEqual(filing['next_write']['blocker']['kind'], 'jobs', 'a series write waits for the queue, as its Waiting item says')
        self.assertEqual(filing['next_move']['blocker']['kind'], 'book', 'the queued move\'s own blocker')
        self.assertEqual((work['state'], work['pending']['filing'], work['pending']['could_not_file']), ('continues', 5, 1))
        self.assertEqual([item['origin'] for item in work['waiting'] if item['kind'] == 'action'], ['rules'], 'the app\'s own move: no Cancel')
        paused = background_work.view(SimpleNamespace(merge=SimpleNamespace(rule_filing=SimpleNamespace(summary=lambda: dict(summary, paused=True))), active_library=''),
                                      {'state': 'Paused'}, {}, {}, False, None)
        self.assertEqual((paused['state'], paused['filing']['next_write']['blocker']['cause'], paused['filing']['next_move']['blocker']['cause']), ('paused', 'queue_paused', 'queue_paused'))

    def test_before_its_first_pass_a_started_pass_is_not_known_and_one_never_started_reports_nothing_left(self):
        shelf = Shelf('setUp')
        shelf.setUp()
        self.addCleanup(shelf.doCleanups)
        self.assertEqual((shelf.filing.summary()['known'], shelf.filing.summary()['left']), (True, 0))
        shelf.filing.thread = SimpleNamespace(is_alive=lambda: True)  # started, its first pass still to come
        self.assertEqual((shelf.filing.summary()['known'], shelf.filing.summary()['left']), (False, None))
        shelf.filing.thread = None
        shelf.filing.tick()
        self.assertEqual((shelf.filing.summary()['known'], shelf.filing.summary()['left']), (True, 0))


class PageFactTests(unittest.TestCase):
    """Small facts the 0.31.0 page asked for beside milestone B (additive; the page words them)."""

    def test_the_books_that_wait_for_something_else_than_an_online_answer_are_counted_apart(self):
        server = SimpleNamespace(merge=SimpleNamespace(), active_library='')
        work = background_work.view(server, {}, {'state': 'Running', 'research': {'waiting': 7}}, {}, False, None)
        before = work['lookup_before_review']
        self.assertEqual((before['total'], before['other_waits'], before['count']), (0, 7, 0), 'the Metadata sources number without the online waits')
        unknown = background_work.view(server, {}, {'state': 'Running', 'research': {}}, {}, False, None)['lookup_before_review']
        self.assertIsNone(unknown['other_waits'], 'not known is never a number')

    def test_the_wait_reason_names_the_english_title_and_a_kept_result_is_still_understood(self):
        import public_research
        self.assertIn('English title', public_research.LOOKUP_WAIT_REASON)
        self.assertNotIn('original title', public_research.LOOKUP_WAIT_REASON)
        self.assertIn('original title', public_research.LOOKUP_WAIT_REASON_BEFORE, 'the wording kept results carry, dropped with the current one')

    def test_a_book_stopped_by_a_withdrawn_hold_is_read_once_more(self):
        import public_research
        held = {'state': 'Held', 'reasons': ['Series and standalone evidence conflicts']}
        credits = {'state': 'Held', 'reasons': ['Series membership has conflicting author credits. Confirm this book in Edit names.']}
        self.assertTrue(public_research.needs_local_recheck(held))
        self.assertTrue(public_research.needs_local_recheck(credits))
        self.assertFalse(public_research.needs_local_recheck(dict(held, local_recheck=public_research.LOCAL_RECHECK)), 'once')
        self.assertFalse(public_research.needs_local_recheck({'state': 'Held', 'reasons': ['Sources disagree on the title or author']}), 'a question that still stands is not re-read for this')


class JournalColumnTests(unittest.TestCase):
    """The one schema change: book_moves.origin. Added to a table made before 0.31.0, and that version still runs on it."""
    OLD = ('CREATE TABLE book_moves(move_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, kind TEXT NOT NULL, candidate_id TEXT NOT NULL,'
           ' generation INTEGER NOT NULL, state TEXT NOT NULL, strategy TEXT, target_folder TEXT NOT NULL, target_root TEXT NOT NULL,'
           ' target_path TEXT NOT NULL, from_json TEXT NOT NULL, final_json TEXT, temp_path TEXT, cause TEXT, detail TEXT, progress INTEGER,'
           ' override_id TEXT, created_utc TEXT NOT NULL, updated_utc TEXT NOT NULL, UNIQUE(job_id,kind,generation))')
    OLD_INSERT = ('INSERT INTO book_moves(move_id,job_id,kind,candidate_id,generation,state,strategy,target_folder,target_root,target_path,from_json,final_json,temp_path,cause,detail,progress,override_id,created_utc,updated_utc)'
                  " VALUES(?,?,'base','c',?,'complete',NULL,'f','r','t','{}','{\"final_path\": \"t\"}',NULL,NULL,NULL,NULL,NULL,'now','now')")

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='filing-'))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.db = str(self.base / 'c.sqlite3')

    def test_the_column_is_added_once_and_a_move_made_before_it_reads_as_before(self):
        with connect(self.db) as db:
            db.execute(self.OLD)
            db.execute(self.OLD_INSERT, ('old-move', 'job-1', 1))
            self.assertTrue(book_move.migrate(db))
            self.assertFalse(book_move.migrate(db), 'once')
            book_move.setup(db)
            move = book_move.load(db, 'old-move')
            self.assertEqual((move['state'], move['origin'], book_move.view(move)['origin']), ('complete', None, None))
            self.assertEqual(sorting_moves._last_move(db, 'job-1'), ('t', True))
            # Rollback: the statement a version before 0.31.0 writes a move with still runs on the migrated table.
            db.execute(self.OLD_INSERT, ('after-rollback', 'job-2', 1))
            self.assertEqual(book_move.load(db, 'after-rollback')['origin'], None)

    def test_a_new_catalog_gets_the_column_and_a_move_keeps_who_made_it(self):
        start = {'root': 'r', 'final_path': 'r\\a\\b.m4b', 'sha256': '0' * 64, 'size': 1, 'parent_identity': []}
        with connect(self.db) as db:
            own = book_move.plan(db, job_id='j1', kind='base', candidate_id='c1', start=start, folder='r\\x', root='r', origin='rules')
            his = book_move.plan(db, job_id='j2', kind='base', candidate_id='c2', start=start, folder='r\\y', root='r', origin='user', override_id='o1')
            plain = book_move.plan(db, job_id='j3', kind='base', candidate_id='c3', start=start, folder='r\\z', root='r')
            self.assertEqual([book_move.view(move)['origin'] for move in (own, his, plain)], ['rules', 'user', None])
            with self.assertRaises(ValueError):
                book_move.plan(db, job_id='j4', kind='base', candidate_id='c4', start=start, folder='r\\w', root='r', origin='someone')
            self.assertEqual(sorting_moves._last_move(db, 'j2'), ('', False), 'a folder he chose: never planned on')

    def test_the_record_table_is_made_once_and_holds_one_entry_in_hand_per_book(self):
        import sqlite3
        with connect(self.db) as db:
            rule_filing.setup(db)
            rule_filing.setup(db)
            insert = ("INSERT INTO rule_filings(filing_id,job_id,candidate_id,state,step,from_path,to_path,kinds,reasons,title,author,created_utc,updated_utc)"
                      " VALUES(?,'job-1','c','open','','a','b','[]','[]','t','a','now','now')")
            db.execute(insert, ('f1',))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(insert, ('f2',))


if __name__ == '__main__':
    unittest.main()

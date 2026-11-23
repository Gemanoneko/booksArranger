"""0.31.0 ruling R27 (Sergei 2026-11-23): when the rules give a finished audiobook an English title or put its author's name in
order, the change is written inside the file's tags and into the app's list, not only into its file name and folder
(name_write.py; the series write carries the names when a book needs both, series_backfill). The rules' pass that
approves these writes (one pass per book, the guards, the pacing) has its own module, test_rule_filing_names_031.

Real audiobooks made by ffmpeg (test_series_backfill's Library) in a private folder under the worker's scratch, a real
catalog, the real list (sorting_moves.plan through MergeService.sorting_target), the real proofs and the real verified
move. An interrupted write is a real kill: a child process of this module ends itself with os._exit between two steps,
and a new run takes the book up from what is on disk and in the catalog. No network, no real library.

Each behaviour has its control: the same case without the rule gives another result (named in the test)."""
import contextlib
import copy
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
if not shutil.which('ffmpeg'):
    os.environ['PATH'] = str(ROOT / 'build-cache' / 'runtime' / 'ffmpeg') + os.pathsep + os.environ.get('PATH', '')

import author_rules  # noqa: E402
import book_delete  # noqa: E402
import book_move  # noqa: E402
import groups  # noqa: E402
import name_write  # noqa: E402
import publication_locations as p  # noqa: E402
import quicktime_chapters  # noqa: E402
import rule_filing  # noqa: E402
import series_backfill  # noqa: E402
import sorting_moves  # noqa: E402
from gap_fill import GapFill  # noqa: E402
from name_write import NameWrite  # noqa: E402
from native_io import VerifiedFile  # noqa: E402
from publication_binding import PublicationBindings  # noqa: E402
from scanner import connect  # noqa: E402
from series_backfill import SeriesBackfill, encoded  # noqa: E402

ENGLISH = 'White Nights Ghosts'
ORDERED = 'Obukhova Lena'
SHORT = ROOT / 'scratch' / 'nw'  # inside the worker's scratch: the only place the QA disposition owner removes files


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def media_hash(path):
    """SHA-256 of every media atom's bytes (mdat), read from the file's own top-level layout."""
    top, _index, _moves = quicktime_chapters._layout(Path(path))
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for kind, at, length in top:
            if kind == b'mdat':
                stream.seek(at)
                digest.update(stream.read(length))
    return digest.hexdigest()


def probe(path):
    from audio_pipeline import probe as run
    stage = Path(tempfile.mkdtemp(dir=SHORT, prefix=''))
    try:
        return run(Path(path), stage, threading.Event())
    finally:
        shutil.rmtree(stage, True)


def tags(raw):
    return {key.lower(): str(value) for key, value in raw.get('format', {}).get('tags', {}).items()}


class Book:
    """One real finished audiobook in a private Audiobooks Sorted (books-hierarchy-v2), its catalog, an English title the
    detail look-up recorded, its series look-up ended without a series, and the engine pieces the rules' pass asks for."""

    def __init__(self, test, english=ENGLISH, author_rule=None, facts=True, folder=None):
        import test_series_backfill as base
        SHORT.mkdir(parents=True, exist_ok=True)
        if folder is None:
            temp = tempfile.TemporaryDirectory(dir=SHORT, prefix='')
            test.addCleanup(temp.cleanup)
            folder = temp.name
        original = base.Library.__init__.__globals__['propose']

        def v2(path, root, kind, metadata, review=None, automatic_facts=None):
            return original(path, root, kind, metadata, dict(review or {}, organization_policy='books-hierarchy-v2'), automatic_facts)
        with mock.patch.object(base, 'propose', v2):
            self.lib = lib = base.Library(Path(folder), separate_sorted=True)
        self.title, self.author = base.TITLE, base.AUTHOR
        with connect(lib.db) as db:
            manifest = json.loads(db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?', (lib.job_id,)).fetchone()[0])
            manifest['metadata'].update(organization_policy='books-hierarchy-v2', original_language='Unknown')
            if facts:
                manifest['metadata_facts'] = {'policy_version': 'standing-17-v1', 'authors': [lib.review['author']], 'series_state': 'omitted_unknown',
                                              'title_basis': 'source_russian', 'author_folder_basis': 'surname_first'}
            text, digest = encoded(manifest)
            output = json.loads(db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (lib.job_id,)).fetchone()[0])
            output['validation']['passed'] = True  # as the conversion's checks record it
            # As every published book has it: its publication intent is the receipt it was published with.
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=?,output=?,journal=? WHERE job_id=?',
                       (text, digest, json.dumps(output), json.dumps({'publication_intent': output}), lib.job_id))
            db.execute('ALTER TABLE book_groups ADD COLUMN superseded INTEGER NOT NULL DEFAULT 0')
            author_rules.setup(db)
            if author_rule:
                author_rules.append(db, 'same_as', lib.review['author'], target=author_rule, actor='user', source='test')
        self.queue = []
        self.merge = merge = lib.merge()
        merge.inventory.output_root = str(lib.root)
        merge.draining = False
        merge._sorting_move = self.queue_move
        merge.cancel_move = lambda move_id: None
        merge.series_backfill = SeriesBackfill(merge, research=None, stage=lib.base / 'proof-stage')
        merge.gap_fill = GapFill(merge)
        merge.name_write = self.writer = NameWrite(merge, stage=lib.base / 'names-stage')
        merge.rule_filing = self.filing = rule_filing.RuleFiling(merge)
        with connect(lib.db) as db:
            db.execute("INSERT INTO series_backfill VALUES(?,'none','',?,'now')", (lib.job_id, json.dumps({'lookup_policy': series_backfill.LOOKUP_POLICY})))
            if english:
                found = {'catalog': {'language': 'en', 'english_title': english, 'original_title': english, 'source_url': 'https://www.wikidata.org/wiki/Q42'}}
                db.execute("INSERT INTO gap_fill VALUES(?,?,'found','',?,'now')", (lib.job_id, lib.candidate, json.dumps({'found': found})))
        self.original = lib.original
        self.path = lib.path

    def queue_move(self, job_id, target, origin='user'):
        lib = self.lib
        start = book_move.location(self.resolve())
        with connect(lib.db) as db:
            move = book_move.plan(db, job_id=job_id, kind='base', candidate_id=lib.candidate, start=start, folder=os.path.dirname(target), root=str(lib.root),
                                  name=os.path.basename(target), origin=origin)
        self.queue.append(move['move_id'])
        return {'state': 'move_queued', 'move': book_move.view(move)}

    def run_queue(self):
        lib = self.lib
        mover = book_move.Mover(lambda: connect(lib.db), lambda job_id, kind: self.resolve(), sources=lambda: (str(lib.source_root),), output_root=str(lib.root),
                                remove_folder=book_delete._remove_folder, protected_roots=lambda: (str(lib.root), str(lib.source_root)))
        return [mover.run(self.queue.pop(0)) for _ in list(self.queue)]

    def resolve(self):
        with connect(self.lib.db) as db:
            record = json.loads(db.execute('SELECT output FROM audio_jobs WHERE job_id=?', (self.lib.job_id,)).fetchone()[0])
        return PublicationBindings(str(self.lib.db)).current(record, 'base')[0]

    def row(self):
        with connect(self.lib.db) as db:
            return dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (self.lib.job_id,)).fetchone())

    def output(self):
        return json.loads(self.row()['output'])

    def manifest(self):
        return json.loads(self.row()['manifest'])

    def target(self):
        return self.merge.sorting_target(self.lib.job_id)

    def plan_item(self):
        answer = self.merge.sorting_moves()
        return next((item for item in answer['items'] if item['job_id'] == self.lib.job_id), None)

    def approve(self, names=None, by='rules'):
        item = self.plan_item()
        self.writer.approve(self.lib.job_id, names or item['names'], item['to'], by=by, reasons=item.get('reasons'))
        return item

    def state(self):
        entry = self.writer.entry(self.lib.job_id)
        return (entry['state'], entry['reason']) if entry else None

    def temps(self):
        return sorted(item.name for item in self.path.parent.iterdir() if item.name.startswith(name_write.TEMP_PREFIX))

    def files(self):
        return sorted(str(item.relative_to(self.lib.root)) for item in self.lib.root.rglob('*') if item.is_file())


class Unchanged:
    def assert_unchanged(self, book):
        self.assertEqual(sha(book.path), book.original, 'the published file is untouched')
        self.assertEqual(book.temps(), [], 'no temporary file is left')
        output = book.output()
        self.assertEqual((output['final_path'], output['sha256']), (str(book.path), book.original), 'the catalog still names the file as it is')
        self.assertEqual(book.manifest()['metadata']['title'], book.title)


class NameWriteTests(Unchanged, unittest.TestCase):
    """Item 1: the English title written into the file (title, album, sort title), read back, and recorded in one catalog
    transaction; every other byte of the audio and every other tag as before."""

    def test_the_english_title_goes_into_the_tags_the_catalog_and_the_list_and_the_audio_is_byte_identical(self):
        book = Book(self)
        before = probe(book.path)
        media_before = media_hash(book.path)
        keep = book.lib.base / 'original-copy.m4b'
        shutil.copyfile(book.path, keep)
        item = book.plan_item()
        self.assertEqual((item['names'], item['items']), ({'title': ENGLISH}, ['title']), 'the list names what changes in the file')
        book.approve()
        self.assertEqual(sha(book.path), book.original, 'approved, not yet written')
        book.writer.run_pass()
        self.assertEqual(book.state(), ('done', ''))
        new = Path(book.writer.entry(book.lib.job_id)['record']['new_path'])
        self.assertEqual((new.parent, new.name), (book.path.parent, '%s - %s.m4b' % (ENGLISH, book.author)), 'renamed in its own folder to the name the list gives')
        self.assertEqual((book.path.exists(), new.exists(), book.temps()), (False, True, []), 'no copy is kept, no temporary left')
        # The audio: every media byte the same (the hash of the media atoms), the sample tables and the decoded packets too.
        self.assertEqual(media_hash(new), media_before, 'the media atoms are byte-identical')
        quicktime_chapters.media_unchanged(keep, new, threading.Event())
        from audio_pipeline import audio_packet_hash
        stage = Path(tempfile.mkdtemp(dir=SHORT, prefix=''))
        self.addCleanup(shutil.rmtree, stage, True)
        self.assertEqual(audio_packet_hash(keep, stage, threading.Event(), 2.0), audio_packet_hash(new, stage, threading.Event(), 2.0))
        # The tags: the new title as a book converted under it carries it; everything else read back as before.
        after = probe(new)
        old, now = tags(before), tags(after)
        self.assertEqual((now['title'], now['album'], now.get('sort_name')), (ENGLISH, ENGLISH, None))
        self.assertEqual((old['title'], old['album']), (book.title, book.title), 'control: the old file had the Russian title')
        self.assertEqual({k: v for k, v in old.items() if k not in ('title', 'album', 'sort_name')}, {k: v for k, v in now.items() if k not in ('title', 'album', 'sort_name')},
                         'artist, album artist, media type, encoder and every other tag survive')
        self.assertEqual(before['chapters'], after['chapters'], 'the chapters survive')
        streams = lambda raw: [(s.get('codec_type'), s.get('codec_name'), s.get('disposition', {}).get('attached_pic'), s.get('duration_ts')) for s in raw['streams']]
        self.assertEqual(streams(before), streams(after), 'the audio stream and the cover survive')
        self.assertEqual([s for s in streams(after) if s[2] == 1][0][0], 'video', 'the cover is there')
        # The catalog, in one transaction: the receipt, the manifest and its hash, the owned output, the verified identity.
        row, output, manifest = book.row(), book.output(), book.manifest()
        self.assertEqual((output['final_path'], output['sha256'], output['size']), (str(new), sha(new), new.stat().st_size))
        self.assertEqual(row['manifest_hash'], hashlib.sha256(row['manifest'].encode()).hexdigest())
        self.assertEqual((manifest['metadata']['title'], manifest['destination']), (ENGLISH, str(new)))
        self.assertEqual((output['validation']['tags']['title'], output['validation']['tags'].get('album')), (ENGLISH, ENGLISH), 'the read-back record follows')
        self.assertTrue(book.merge._identity_current(output), 'routine check: the identity recorded for the new file')
        self.assertTrue(book.merge._output_valid(output), 'full check: the recorded bytes')
        with connect(book.lib.db) as db:
            self.assertEqual([tuple(r) for r in db.execute("SELECT path,sha256 FROM owned_artifacts WHERE kind='output'")], [(str(new), output['sha256'])])
            self.assertEqual(db.execute("SELECT count(*) FROM owned_artifacts WHERE kind='temporary'").fetchone()[0], 0)
            review = json.loads(db.execute('SELECT review FROM book_groups').fetchone()[0])
            context = json.loads(db.execute('SELECT data FROM candidate_context').fetchone()[0])
            journal = json.loads(row['journal'])
        # The list and the details panel: the stored review the list shows, and the facts it reads (4.5's English title).
        self.assertEqual((review['title'], review['author']), (ENGLISH, book.author))
        facts = manifest['metadata_facts']
        self.assertEqual((facts['title_source']['rule'], facts['title_source']['provider'], facts['original_title_lookup']['state'], facts['original_title_lookup']['title'], facts['title_basis']),
                         ('english', 'wikidata', 'found', ENGLISH, 'published_english'))
        self.assertEqual(context['metadata_evidence'][-1]['field'], 'title')
        from merge_service import MergeService
        self.assertEqual(MergeService.title_origin({'metadata_facts': facts}), {'origin': 'source', 'rule': 'english', 'split': False, 'provider': 'wikidata',
                                                                               'source_url': 'https://www.wikidata.org/wiki/Q42'}, 'the row says the English title came from Wikidata')
        # The publication record: the new receipt is the book's publication intent, the one it replaced is kept.
        self.assertEqual(p._digest(journal['publication_intent']), p._digest(output))
        self.assertEqual(journal['publication_intent_before_names']['final_path'], str(book.path))
        self.assertEqual(book.resolve()['final_path'], str(new), 'every reader of the catalog finds the book at its new path')
        # Nothing more at a later pass; the list has nothing left for this book.
        book.writer.run_pass()
        self.assertEqual((sha(new), book.plan_item()), (output['sha256'], None))

    def test_the_author_credit_in_order_goes_into_the_artist_tags_and_the_book_then_moves_once(self):
        book = Book(self, english=None, author_rule=ORDERED)
        before = probe(book.path)
        item = book.plan_item()
        self.assertEqual((item['names'], item['items']), ({'author': ORDERED, 'canonical_author': ORDERED}, ['author']))
        final = book.lib.root / ORDERED / ('%s - %s.m4b' % (book.title, ORDERED))
        self.assertEqual(item['to'], str(final))
        book.approve()
        book.writer.run_pass()
        entry = book.writer.entry(book.lib.job_id)
        self.assertEqual((entry['state'], entry['record']['follow_up']['state']), ('done', 'move_queued'), 'written in its own folder, then the move to its author folder')
        placed = Path(entry['record']['new_path'])
        self.assertEqual((placed.parent, placed.name), (book.path.parent, final.name))
        now = tags(probe(placed))
        self.assertEqual((now['artist'], now['album_artist'], now['title']), (ORDERED, ORDERED, book.title))
        self.assertEqual(tags(before)['artist'], book.author, 'control: the old file had the credit as the source wrote it')
        manifest = book.manifest()
        self.assertEqual((manifest['metadata']['author'], manifest['metadata']['canonical_author'], manifest['metadata_facts']['authors']), (ORDERED, ORDERED, [ORDERED]))
        book.run_queue()
        self.assertEqual((final.exists(), placed.exists()), (True, False))
        self.assertEqual(book.resolve()['final_path'], str(final), 'the catalog follows the move')
        self.assertEqual(book.plan_item(), None, 'moved once: nothing left')

    def test_control_without_the_switch_the_list_writes_nothing_and_the_move_renames_the_file_only(self):
        book = Book(self)
        with mock.patch.object(name_write, 'WRITE_NAMES', 'off'):
            item = book.plan_item()
            self.assertNotIn('names', item, 'switched off: the 0.31.0 milestone B list, exactly')
        self.assertEqual(book.plan_item()['names'], {'title': ENGLISH}, 'positive control: on, the same book has its names to write')

    def test_an_authors_folder_name_alone_is_the_moves_not_a_write(self):
        self.assertEqual(name_write.needed({'title': 'A', 'author': 'B', 'canonical_author': 'C'}, {'title': 'A', 'author': 'D', 'canonical_author': 'C'}), {})
        self.assertEqual(name_write.needed({'title': 'A', 'author': 'B', 'canonical_author': 'B'}, {'title': 'A', 'author': 'D', 'canonical_author': 'D'}),
                         {'author': 'D', 'canonical_author': 'D'}, 'control: the credit in the tags changes too')


class FailureTests(Unchanged, unittest.TestCase):
    """A failed write leaves the book as it was, and says why."""

    def test_a_tag_that_does_not_read_back_leaves_the_book_as_it_was_with_a_reason_key(self):
        book = Book(self)
        book.approve()
        with mock.patch.object(name_write, 'check', side_effect=series_backfill.Held('The new names did not read back: title')):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('held', 'The new names did not read back: title'))
        self.assert_unchanged(book)
        self.assertEqual(sorting_moves.reason_key(book.state()[1], sorting_moves.NOT_MOVED_KEYS), 'tags_not_written')

    def test_the_real_read_back_refuses_a_write_that_did_not_change_the_title(self):
        book = Book(self)
        book.approve()
        real = name_write.tags
        with mock.patch.object(name_write, 'tags', lambda was, now: {name_write.series_backfill.ALBUM: real(was, now)[series_backfill.ALBUM]}):
            book.writer.run_pass()  # the album is written, the title item is not: the proof must catch it
        self.assertEqual(book.state(), ('held', 'The new names did not read back: title'))
        self.assert_unchanged(book)

    def test_a_file_already_at_the_new_name_is_never_overwritten(self):
        book = Book(self)
        item = book.plan_item()
        stranger = book.path.parent / os.path.basename(item['to'])
        stranger.write_bytes(b'another book')
        book.writer.approve(book.lib.job_id, item['names'], item['to'], by='rules', reasons=item.get('reasons'))
        book.writer.run_pass()
        self.assertEqual(book.state()[0], 'held')
        self.assertIn('already exists', book.state()[1])
        self.assertEqual(stranger.read_bytes(), b'another book', 'the other file is untouched')
        self.assert_unchanged(book)
        self.assertEqual(sorting_moves.reason_key(book.state()[1], sorting_moves.NOT_MOVED_KEYS), 'name_exists')

    def test_a_move_begun_during_the_write_keeps_the_catalog_and_both_copies(self):
        book = Book(self)
        book.approve()
        with mock.patch.object(NameWrite, 'catalog', side_effect=sqlite3.OperationalError('database is locked')):
            book.writer.run_pass()
        self.assertEqual(book.state()[0], 'renamed', 'a busy catalog waits: renamed, not yet recorded')
        new = Path(book.writer.entry(book.lib.job_id)['record']['new_path'])
        with connect(book.lib.db) as db:  # Choose folder… on the book: its move starts from the receipt as it is
            move = book_move.plan(db, job_id=book.lib.job_id, kind='base', candidate_id=book.lib.candidate, start=book_move.location(book.resolve()),
                                  folder=str(book.lib.root / 'Mine'), root=str(book.lib.root), origin='user', override_id='his')
            db.execute("UPDATE book_moves SET state='rename_intent' WHERE move_id=?", (move['move_id'],))
        book.writer.clock = lambda: 2_000_000_000.0
        book.writer.run_pass()
        state, reason = book.state()
        self.assertEqual(state, 'held')
        self.assertIn('moved meanwhile', reason)
        output = book.output()
        self.assertEqual((output['final_path'], sha(book.path), book.manifest()['metadata']['title']), (str(book.path), book.original, book.title), 'the receipt the move starts from')
        self.assertEqual(sha(new), book.writer.entry(book.lib.job_id)['record']['new_sha256'], 'the proven copy is kept, never half written')
        with connect(book.lib.db) as db:
            db.execute("UPDATE book_moves SET state='cancelled' WHERE move_id=?", (move['move_id'],))
        control = Book(self)
        control.approve()
        with mock.patch.object(NameWrite, 'catalog', side_effect=sqlite3.OperationalError('database is locked')):
            control.writer.run_pass()
        with connect(control.lib.db) as db:  # control: a move only queued has not begun; the write is recorded
            book_move.plan(db, job_id=control.lib.job_id, kind='base', candidate_id=control.lib.candidate, start=book_move.location(control.resolve()),
                           folder=str(control.lib.root / 'Mine'), root=str(control.lib.root), origin='user', override_id='his')
        control.writer.clock = lambda: 2_000_000_000.0
        control.writer.run_pass()
        self.assertEqual(control.state(), ('done', ''))

    def test_the_write_touches_only_the_books_own_file_and_its_own_temporary_in_its_folder(self):
        book = Book(self)
        neighbour = book.path.parent / 'Another book - Someone.m4b'
        neighbour.write_bytes(b'neighbour')
        before = set(book.files())
        seen = []
        real = quicktime_chapters.retag

        def watch(source, destination, stop, items):
            seen.append((Path(source), Path(destination)))
            return real(source, destination, stop, items)
        book.approve()
        with mock.patch.object(quicktime_chapters, 'retag', watch):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('done', ''))
        new = book.writer.entry(book.lib.job_id)['record']['new_path']
        self.assertEqual(seen, [(book.path, book.path.parent / (name_write.TEMP_PREFIX + book.lib.job_id + '.m4b'))], 'read from the book, written next to it')
        self.assertEqual(set(book.files()) ^ before, {str(book.path.relative_to(book.lib.root)), str(Path(new).relative_to(book.lib.root))}, 'only the book\'s own name changed')
        self.assertEqual(neighbour.read_bytes(), b'neighbour')


KILL_POINTS = ('retag', 'written', 'renamed', 'cataloged', 'disposed')


def _engine(spec):
    """The engine a run of the app builds for the shelf (the child's and the restart's): Library.merge on the saved paths."""
    import test_series_backfill as base
    shelf = SimpleNamespace(db=Path(spec['db']), root=Path(spec['root']), source_root=Path(spec['source_root']), stage_root=Path(spec['stage_root']))
    merge = base.Library.merge(shelf)
    merge.inventory.output_root = spec['root']
    merge.draining = False
    merge._sorting_move = lambda job_id, target, origin='user': {'state': 'later', 'move': {}}
    merge.series_backfill = SeriesBackfill(merge, research=None, stage=Path(spec['base']) / 'proof-stage')
    merge.name_write = NameWrite(merge, stage=Path(spec['base']) / 'names-stage')
    return merge


def child(spec_path, point):
    """A run of the app that is killed at one point of the write (os._exit: no cleanup, no finally)."""
    spec = json.loads(Path(spec_path).read_text(encoding='utf-8'))
    merge = _engine(spec)
    writer = merge.name_write
    old = spec['old']
    if point == 'retag':
        def retag(source, destination, stop, items):
            Path(destination).write_bytes(Path(source).read_bytes()[:4096])  # half a file, then the process dies
            os._exit(9)
        quicktime_chapters.retag = retag
    elif point in ('written', 'renamed'):
        real = NameWrite._set

        def _set(self, job_id, state, reason='', record=None):
            real(self, job_id, state, reason, record)
            if state == point:
                os._exit(9)
        NameWrite._set = _set
    elif point == 'cataloged':
        real = NameWrite.catalog

        def catalog(self, job_id, record):
            real(self, job_id, record)
            os._exit(9)
        NameWrite.catalog = catalog
    elif point == 'disposed':
        real = VerifiedFile.dispose

        def dispose(handle, **kwargs):
            result = real(handle, **kwargs)
            if os.path.normcase(str(handle.path)) == os.path.normcase(old):
                os._exit(9)
            return result
        VerifiedFile.dispose = dispose
    from runtime_disposition_owners import support_dispositions
    with support_dispositions(ROOT / 'scratch', [ROOT / 'scratch']):
        writer.run_pass()
    os._exit(0)


class KillTests(unittest.TestCase):
    """An interrupted write (the process killed between each pair of steps) recovers to the old file or to the finished new
    one, never to a half-written book file, and the catalog matches the file in both outcomes."""

    def kill(self, point):
        book = Book(self)
        item = book.approve()
        spec = book.lib.base / 'shelf.json'
        spec.write_text(json.dumps({'db': str(book.lib.db), 'root': str(book.lib.root), 'source_root': str(book.lib.source_root), 'stage_root': str(book.lib.stage_root),
                                    'base': str(book.lib.base), 'old': str(book.path)}), encoding='utf-8')
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        done = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--child', str(spec), point], cwd=str(ROOT), capture_output=True, text=True,
                              timeout=300, creationflags=flags)
        self.assertEqual(done.returncode, 9, 'killed at ' + point + ': ' + done.stderr[-2000:])
        return book, item

    def assert_consistent(self, book):
        """The catalog names a file that is there with exactly the bytes it records; no book file is half written."""
        output = book.output()
        self.assertTrue(Path(output['final_path']).exists())
        self.assertEqual(sha(output['final_path']), output['sha256'], 'the catalog matches the file')
        record = book.writer.entry(book.lib.job_id)['record']
        new = Path(record.get('new_path') or '')
        if record.get('new_path') and new.exists():
            self.assertEqual(sha(new), record['new_sha256'], 'a file at the new name is only ever the proven one')
        if book.path.exists():
            self.assertEqual(sha(book.path), book.original, 'the old file is only ever the original')

    def finish(self, book):
        merge = _engine({'db': str(book.lib.db), 'root': str(book.lib.root), 'source_root': str(book.lib.source_root), 'stage_root': str(book.lib.stage_root),
                         'base': str(book.lib.base)})
        merge.name_write.run_pass()  # the next run of the app
        merge.name_write.run_pass()  # a book set back to pending by the recovery is written now
        entry = merge.name_write.entry(book.lib.job_id)
        self.assertEqual((entry['state'], entry['reason']), ('done', ''))
        new = Path(entry['record']['new_path'])
        self.assertEqual((book.path.exists(), new.exists(), book.temps()), (False, True, []))
        self.assertEqual(tags(probe(new))['title'], ENGLISH)
        self.assert_consistent(book)
        self.assertEqual(book.output()['final_path'], str(new))
        with connect(book.lib.db) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM owned_artifacts WHERE kind='temporary'").fetchone()[0], 0)

    def test_killed_while_the_new_file_is_written(self):
        book, _ = self.kill('retag')
        self.assertEqual(book.state()[0], 'writing')
        self.assertEqual(book.output()['final_path'], str(book.path), 'the catalog names the old file')
        self.assertEqual(len(book.temps()), 1, 'only the app\'s own owned temporary is half written')
        self.assert_consistent(book)
        self.finish(book)

    def test_killed_after_the_proofs_before_the_rename(self):
        book, _ = self.kill('written')
        self.assertEqual(book.state()[0], 'written')
        self.assertEqual(book.output()['final_path'], str(book.path))
        self.assert_consistent(book)
        self.finish(book)

    def test_killed_after_the_rename_before_the_catalog(self):
        book, _ = self.kill('renamed')
        self.assertEqual(book.state()[0], 'renamed')
        self.assertEqual(book.output()['final_path'], str(book.path), 'old file and old record: still valid')
        self.assertTrue(book.merge._output_valid(book.output()))
        self.assert_consistent(book)
        self.finish(book)

    def test_killed_after_the_catalog_before_the_old_file_goes(self):
        book, _ = self.kill('cataloged')
        self.assertEqual(book.state()[0], 'cataloged')
        record = book.writer.entry(book.lib.job_id)['record']
        self.assertEqual(book.output()['final_path'], record['new_path'], 'the new file and the new record')
        self.assertEqual(book.manifest()['metadata']['title'], ENGLISH, 'the names in the same transaction')
        self.assert_consistent(book)
        self.finish(book)

    def test_killed_after_the_old_file_went_before_done(self):
        book, _ = self.kill('disposed')
        self.assertFalse(book.path.exists())
        self.assert_consistent(book)
        self.finish(book)


class RefusalTests(Unchanged, unittest.TestCase):
    """The same refusals the series write has, and the approval only the rules give."""

    def test_only_the_rules_approve_and_only_names_the_list_gives(self):
        book = Book(self)
        item = book.plan_item()
        for by in (None, 'user', 'Sergei'):
            with self.assertRaises(ValueError):
                book.writer.approve(book.lib.job_id, item['names'], item['to'], by=by)
        with self.assertRaises(ValueError):
            book.writer.approve(book.lib.job_id, {}, item['to'], by='rules')
        self.assertIsNone(book.state(), 'nothing recorded')
        book.writer.run_pass()
        self.assert_unchanged(book)
        # An entry made by hand without the rules' approval is never written.
        book.writer._set(book.lib.job_id, 'pending', '', {'kind': 'names', 'approved_names': item['names'], 'approved_target': item['to']})
        book.writer.run_pass()
        self.assertEqual(book.state(), ('held', name_write.NOT_BY_RULES))
        self.assert_unchanged(book)
        # The series write carries names for the rules only, too.
        with connect(book.lib.db) as db:
            db.execute("UPDATE series_backfill SET state='held',reason=?,record=? WHERE job_id=?", (series_backfill.MOVE_WAITS, json.dumps({'series': 'S', 'number': '1'}), book.lib.job_id))
        with self.assertRaises(ValueError):
            book.merge.series_backfill.approve(book.lib.job_id, {'name': 'S', 'number': '1'}, item['to'], names={'title': ENGLISH})

    def test_a_book_that_changed_since_approval_or_whose_place_changed_is_left(self):
        book = Book(self)
        book.approve()
        with connect(book.lib.db) as db:
            manifest = book.manifest()
            manifest['comments'] = 'changed'
            text, digest = encoded(manifest)
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?', (text, digest, book.lib.job_id))
        book.writer.run_pass()
        self.assertEqual(book.state(), ('held', name_write.BOOK_CHANGED))
        self.assertEqual(sha(book.path), book.original)
        other = Book(self)
        item = other.plan_item()
        other.writer.approve(other.lib.job_id, item['names'], item['to'] + '.elsewhere.m4b', by='rules')
        other.writer.run_pass()
        self.assertEqual(other.state(), ('held', name_write.PLACE_CHANGED))
        self.assert_unchanged(other)

    def test_a_retained_job_a_newer_job_and_unfinished_cleanups_are_never_written(self):
        book = Book(self)
        book.approve()
        with mock.patch('storage_relocation_native.retained_job', lambda database, job_id: True):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('held', name_write.RETAINED))
        self.assert_unchanged(book)
        # A newer job for the same book.
        book = Book(self)
        book.approve()
        with connect(book.lib.db) as db:
            row = book.row()
            manifest = json.loads(row['manifest'])
            manifest['job_id'] = 'newer'
            db.execute("INSERT INTO audio_jobs VALUES('newer',?,?,'pending','queued',NULL,'{}',NULL,'','2026-12-01T00:00:00','now')", encoded(manifest))
        book.writer.run_pass()
        self.assertEqual(book.state(), ('held', name_write.NEWER))
        self.assert_unchanged(book)
        # Cleanup still to run (waits), and a cleanup on hold (blocked): never tried, nothing read.
        for state, expected in (('running', 'deferred'), ('needs_attention', 'blocked')):
            book = Book(self)
            book.approve()
            with connect(book.lib.db) as db:
                db.execute('UPDATE storage_cleanup_jobs SET state=? WHERE job_id=?', (state, book.lib.job_id))
            with mock.patch.object(quicktime_chapters, 'retag', side_effect=AssertionError('nothing may be read')):
                book.writer.run_pass()
            self.assertEqual(book.state()[0], expected, state)
            self.assert_unchanged(book)
            with connect(book.lib.db) as db:
                db.execute("UPDATE storage_cleanup_jobs SET state='completed' WHERE job_id=?", (book.lib.job_id,))
            book.writer.clock = lambda: 2_000_000_000.0
            book.writer.run_pass()
            self.assertEqual(book.state(), ('done', ''), 'control: once it has ended the book is written')

    def test_a_drive_that_does_not_answer_and_a_pause_hold_the_job_without_a_try(self):
        book = Book(self)
        book.approve()
        with mock.patch.object(NameWrite, '_answers', staticmethod(lambda root: False)), \
                mock.patch.object(quicktime_chapters, 'retag', side_effect=AssertionError('nothing may be read')):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('deferred', name_write.DRIVE_AWAY))
        self.assert_unchanged(book)
        import pause_state
        with connect(book.lib.db) as db:
            pause_state.record(db, 'jobs', 'user', 'Audiobook jobs paused')
        book.writer.clock = lambda: 2_000_000_000.0
        with mock.patch.object(quicktime_chapters, 'retag', side_effect=AssertionError('nothing may be read')):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('deferred', 'Audiobook jobs are paused'))
        self.assert_unchanged(book)
        self.assertEqual(book.writer.summary()['waiting'], 1)
        with connect(book.lib.db) as db:
            pause_state.clear(db, 'jobs')
        book.writer.clock = lambda: 2_100_000_000.0
        book.writer.run_pass()
        self.assertEqual(book.state(), ('done', ''), 'control: resumed, it is written')

    def test_one_writer_per_file(self):
        book = Book(self)
        item = book.plan_item()
        with connect(book.lib.db) as db:
            db.execute("UPDATE series_backfill SET state='pending',record=? WHERE job_id=?", (json.dumps({'move_approved': True}), book.lib.job_id))
        with self.assertRaises(ValueError):
            book.writer.approve(book.lib.job_id, item['names'], item['to'], by='rules')
        with connect(book.lib.db) as db:
            db.execute("UPDATE series_backfill SET state='none',record=? WHERE job_id=?", (json.dumps({'lookup_policy': series_backfill.LOOKUP_POLICY}), book.lib.job_id))
        book.writer.approve(book.lib.job_id, item['names'], item['to'], by='rules')
        self.assertTrue(book.merge.series_backfill._names_in_hand(book.lib.job_id), 'and the series write sees the write of names in hand')


class ListTests(unittest.TestCase):
    """Item 4: after the write the list, the details and the search show the English title and the corrected author; the
    files' Russian title stays findable."""

    def test_the_search_finds_the_english_title_and_still_the_russian_one(self):
        book = Book(self)
        with connect(book.lib.db) as db:
            stored = json.loads(db.execute('SELECT review FROM book_groups').fetchone()[0])
        row = {'title_clue': book.title, 'scope': str(book.lib.source_root / book.author / book.title), 'members': [{'path': str(book.lib.source_root / book.author / book.title / '01.mp3')}],
               'review': stored}
        self.assertNotIn(ENGLISH.casefold(), groups.searched(row).casefold(), 'control: before the write the English title is nowhere')
        book.approve()
        book.writer.run_pass()
        with connect(book.lib.db) as db:
            row['review'] = json.loads(db.execute('SELECT review FROM book_groups').fetchone()[0])
        text = groups.searched(row).casefold()
        self.assertIn(ENGLISH.casefold(), text, 'Show in list searches for the title the book has now')
        self.assertIn(book.title.casefold(), text, 'the files\' Russian title: the title clue and the source paths')
        self.assertEqual(row['review']['title'], ENGLISH, 'the list\'s title cell')


class RollbackTests(unittest.TestCase):
    """A rollback to 0.30.1 ignores the new ledger (name_writes): a renamed book reads as an ordinary publication at its new
    path (the publication record every reader checks, publication_locations._job: the one an output migration plans from
    and a relocated book is resolved through)."""

    def publication(self, book):
        with connect(book.lib.db) as db:
            row = dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?', (book.lib.job_id,)).fetchone())
            return p._job(db, row, 'base', p._receipt(row['output']))

    def test_a_renamed_book_is_an_ordinary_publication_without_the_new_ledger(self):
        book = Book(self)
        book.approve()
        book.writer.run_pass()
        new = book.writer.entry(book.lib.job_id)['record']['new_path']
        with connect(book.lib.db) as db:
            db.execute('DROP TABLE name_writes')
        _job, manifest, journal, lineage = self.publication(book)
        self.assertIsNone(lineage, 'no lineage to explain: the receipt is its own publication intent')
        self.assertEqual((journal['publication_intent']['final_path'], manifest['metadata']['title']), (new, ENGLISH))
        self.assertEqual(book.resolve()['final_path'], new)

    def test_control_without_the_intent_the_changed_receipt_is_refused(self):
        book = Book(self)
        book.approve()
        with mock.patch.object(name_write, 'journal_named', lambda text, receipt: text):
            book.writer.run_pass()
        self.assertEqual(book.state(), ('done', ''))
        with self.assertRaises(p.PublicationRefused):
            self.publication(book)  # what any version would read without the intent: a receipt no record explains


if __name__ == '__main__':
    if sys.argv[1:2] == ['--child']:
        child(sys.argv[2], sys.argv[3])
    unittest.main()

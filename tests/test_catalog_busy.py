"""0.22.2: a busy catalog never stops an automatic run (the 7th SQLITE_BUSY stop since 10-11, diagnosed read-only on the
live crash: OperationalError at public_research._expire, from a cache-only read inside _gap_fill, while a regroup of both
roots held the write lock for 10.3-10.5 s).

T1 a cache-only read finishes while another connection holds BEGIN IMMEDIATE (it used to run expiry DELETEs on every read);
T2 research's local lookup finishes under that lock; T3 a busy error during book A's research puts A in "Waiting for
source" for about a minute and book B still runs; T4 another writer gets the write lock within 1 s while the groups are
being rebuilt, and the rebuilt groups are the same as the in-transaction rebuild's. Private catalogs; no network."""
import contextlib, json, shutil, sqlite3, tempfile, threading, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import groups
import public_research
from public_research import PublicClient, PublicResearch
from scan_wait import close_scan, finish_scan, finish_thread
from scanner import Inventory, connect

AREA = Path(__file__).resolve().parents[1] / 'scratch' / 'catalog-busy-tests'
AREA.mkdir(parents=True, exist_ok=True)


def quick(database, timeout=10):
    """The app's connect with a 0.2 s busy wait, so a write that has to wait shows at once (the live wait was 10 s)."""
    return connect(database, timeout=0.2)


@contextlib.contextmanager
def held(database):
    """Another connection holds the catalog's write lock (as a regroup did) until the block ends."""
    other = sqlite3.connect(database, timeout=1)
    other.execute('BEGIN IMMEDIATE')
    try:
        yield
    finally:
        other.rollback(); other.close()


class CacheReadTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        self.database = Path(temp.name) / 'catalog.sqlite3'

    def test_t1_a_cache_only_read_finishes_while_another_connection_holds_the_write_lock(self):
        client = PublicClient(self.database, fetch=lambda url, *_: b'{"cached": true}')
        url = 'https://api.fantlab.ru/search-works?q=fixture'
        client.read(url, None, {'remaining': 1})
        with held(self.database), patch.object(public_research, 'connect', quick):
            started = time.monotonic()
            self.assertEqual(client.read(url, None, {'remaining': 0}), b'{"cached": true}')
            self.assertLess(time.monotonic() - started, 1.0)
            # Positive control: a read that needs a request reserves it under the write lock: a short wait, no error.
            with self.assertRaises(public_research.ResearchWait) as wait:
                client.read('https://api.fantlab.ru/search-works?q=other', None, {'remaining': 1})
            self.assertEqual(wait.exception.reason, public_research.CATALOG_BUSY_REASON)

    def test_expired_answers_are_still_never_returned_and_are_removed_with_the_next_answer(self):
        now = [1000000.0]
        client = PublicClient(self.database, fetch=lambda url, *_: b'{"n": 1}', clock=lambda: now[0])
        client.read('https://api.fantlab.ru/old', None, {'remaining': 1})
        now[0] += 8 * 86400
        with self.assertRaises(public_research.ResearchWait):
            client.read('https://api.fantlab.ru/old', None, {'remaining': 0})  # expired: a cache-only read finds nothing
        client.read('https://api.fantlab.ru/new', None, {'remaining': 1})
        with connect(self.database) as db:
            urls = [r[0] for r in db.execute('SELECT url FROM public_research_cache ORDER BY url')]
        self.assertEqual(urls, ['https://api.fantlab.ru/new'], 'the expired answer was removed with the new one')


class LocalLookupTests(unittest.TestCase):
    def test_t2_research_finishes_its_local_lookup_while_another_connection_holds_the_write_lock(self):
        from test_folder_structure import Base, ROOT, file_row
        base = Base('run'); base.addCleanup = self.addCleanup
        row = next(iter(base.catalog([file_row('Стивен Кинг\\Мизери.m4b', title='Мизери', artist='Стивен Кинг', album='Мизери')]).values()))
        research = PublicResearch(PublicClient(base.research.client.database, fetch=lambda *_: (_ for _ in ()).throw(AssertionError('no request'))), leads=[])
        with held(research.client.database), patch.object(public_research, 'connect', quick):
            started = time.monotonic()
            result = research.lookup(dict(row, _manual_metadata_sources=[]), ROOT, threading.Event())
            self.assertLess(time.monotonic() - started, 5.0)
        self.assertIn('local_agreement', result, 'the lookup finished')


class RunTests(unittest.TestCase):
    def setUp(self):
        from merge_service import MergeService
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        roots = {name: str(base / name) for name in ('Audiobooks', 'Podcasts', 'Ebooks')}
        for path in roots.values():
            Path(path).mkdir()
        (base / 'sorted').mkdir()
        for name in ('John Writer - A Book.mp3', 'Jane Author - B Book.mp3'):
            (Path(roots['Audiobooks']) / name).write_bytes(b'fixture only')
        self.inventory = Inventory(base / 'catalog.sqlite3', roots, self.read, output_root=str(base / 'sorted'))
        self.merge = MergeService(self.inventory, base / 'cache')
        self.addCleanup(self.close)

    def close(self):
        automatic = self.merge.__dict__.get('automatic')
        if automatic is not None:
            automatic.close()
        close_scan(self.inventory)
        self.merge.close()

    @staticmethod
    def read(path, kind, stop):
        title = Path(path).stem.split(' - ')[1]
        return {'title': title, 'artist': 'Writer', 'tags': {'title': title, 'artist': 'Writer', 'album': title, 'track': '1'}, 'probe': {'format': {'duration': '1'}}}

    def test_t3_a_busy_catalog_during_one_books_research_defers_that_book_and_the_run_goes_on(self):
        from automatic_processing import AutomaticProcessing
        calls = []
        def lookup(row, root, stop, progress=None):
            calls.append(row['title_clue'])
            if 'A Book' in row['title_clue']:
                raise sqlite3.OperationalError('database is locked')
            return {'reasons': ['Book identity uncertain'], 'sources': []}
        research = SimpleNamespace(client=SimpleNamespace(retry_wait=lambda wait: dict(wait)), lookup=lookup)
        automatic = AutomaticProcessing(self.merge, research)
        self.merge.automatic = automatic
        started = time.time()
        automatic.start()
        end = time.monotonic() + 60
        while time.monotonic() < end and len(calls) < 2 and automatic.thread.is_alive():
            time.sleep(0.1)
        time.sleep(0.5)  # B's outcome is recorded; the run now waits for A's minute
        self.assertTrue(automatic.thread.is_alive(), 'the run is still going (it waits for A), not stopped by the busy error')
        automatic.stop(); finish_thread(automatic.thread, 'the automatic run')
        self.assertEqual(sorted(c.split()[-2] for c in calls[:2]) if len(calls) >= 2 else calls, ['A', 'B'], 'book B was researched after A failed')
        with connect(self.inventory.database) as db:
            states = {json.loads(r['result']).get('reasons', [''])[0] if r['result'] else '': (r['state'], r['retry_at']) for r in db.execute('SELECT state,result,retry_at FROM automatic_candidates')}
        state, retry = states[public_research.CATALOG_BUSY_REASON]
        self.assertEqual(state, 'Waiting for source')
        self.assertAlmostEqual(retry, started + public_research.CATALOG_BUSY_WAIT, delta=30)
        with connect(self.inventory.database) as db:
            failures = db.execute("SELECT count(*) FROM automatic_runs WHERE state='Needs attention'").fetchone()[0]
        self.assertEqual(failures, 0, 'the run did not stop with the busy error')


class RegroupTests(unittest.TestCase):
    BOOKS = 3000

    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        roots = {name: str(self.base / name) for name in ('Audiobooks', 'Podcasts', 'Ebooks')}
        for path in roots.values():
            Path(path).mkdir()
        self.root = roots['Audiobooks']
        self.inventory = Inventory(self.base / 'catalog.sqlite3', roots, lambda *_: {})
        self.inventory.candidates('Audiobooks', limit=1)  # the group tables and their triggers
        metadata = lambda n: json.dumps({'title': 'Книга %d' % n, 'artist': 'Автор %d' % n, 'tags': {'title': 'Книга %d' % n, 'artist': 'Иван Автор%d' % n, 'album': 'Книга %d' % n},
                                         'probe': {'format': {'duration': '60'}}}, ensure_ascii=False)
        with connect(self.inventory.database) as db:
            db.executemany("INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata,error,missing,review) VALUES(?,?,1000,1000,1,'audiobook',0,?,'',0,'')",
                           [(self.root, str(Path(self.root) / ('Автор %04d' % n) / ('Книга %d.m4b' % n)), metadata(n)) for n in range(self.BOOKS)])

    def test_t4_another_writer_gets_the_lock_within_1_s_while_the_groups_are_rebuilt_and_they_are_the_same(self):
        reference = self.base / 'reference.sqlite3'
        shutil.copy2(self.inventory.database, reference)
        building = threading.Event()
        real = groups.build
        def slow_build(*args, **kwargs):
            building.set(); time.sleep(1.5)  # the live build took 10 s; 1.5 s is enough to try a write meanwhile
            return real(*args, **kwargs)
        with patch.object(groups, 'build', slow_build):
            page = threading.Thread(target=lambda: self.inventory.candidates('Audiobooks', limit=10), daemon=True)
            page.start(); self.addCleanup(finish_thread, page, 'the list read')
            self.assertTrue(building.wait(20), 'positive control: the groups are being rebuilt')
            time.sleep(0.2)
            other = sqlite3.connect(self.inventory.database, timeout=1)
            try:
                started = time.monotonic()
                other.execute('BEGIN IMMEDIATE')  # fails after 1 s while the rebuild holds the write lock
                waited = time.monotonic() - started
                other.rollback()
            finally:
                other.close()
            self.assertLess(waited, 1.0)
            finish_thread(page, 'the list read')
        with connect(reference) as db:  # the reference: the same catalog rebuilt the old way, inside one transaction
            db.execute('BEGIN IMMEDIATE'); groups.sync(db, self.root)
        def stored(database):
            with connect(database) as db:
                return sorted((r['scope'], r['fingerprint'], r['superseded']) for r in db.execute('SELECT scope,fingerprint,superseded FROM book_groups WHERE root=?', (self.root,)))
        self.assertEqual(len(stored(self.inventory.database)), self.BOOKS)
        self.assertEqual(stored(self.inventory.database), stored(reference), 'the same groups as the in-transaction rebuild')


if __name__ == '__main__':
    unittest.main()

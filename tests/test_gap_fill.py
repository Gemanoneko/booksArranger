"""0.22.1, backlog item 8 (Sergei, 2026-10-25): approval does not wait for optional online lookups.

The book is approved on its local identity at once (test_local_identity.GapSearchTests); the optional fields are filled
later by the background gap fill (gap_fill.GapFill); series backfill and the gap fill each use their own share of a
site's hourly bound (public_research lanes), so neither starves research or the other; and the client no longer holds
its lock while a request waits for its site or downloads. Private fixture answers; no network."""
import json, sqlite3, tempfile, threading, time, unittest, urllib.error, urllib.parse, uuid
from pathlib import Path
from types import SimpleNamespace

import gap_fill
import public_research
from gap_fill import GapFill
from public_research import PublicClient, PublicResearch, ResearchWait
from scanner import connect
from series_backfill import SeriesBackfill
from test_local_identity import AREA
from test_series_research import Sources, book_page, search_page
from test_approve_as_is import ApproveFixture


class Catalog(Sources):
    """The series fixture's answers plus a FantLab work with an English original."""
    def __init__(self):
        super().__init__()
        self.fantlab = [{'work_id': 42, 'name': 'Sandstorm', 'rusname': 'Око Бога', 'all_autor_name': 'James Rollins', 'all_autor_rusname': 'Джеймс Роллинс'}]
        self.extended['/work/42/extended'] = {'work_id': 42, 'work_name': 'Око Бога', 'work_name_orig': 'The Eye of God', 'lang_code': 'en',
                                              'work_type_name': 'Роман', 'authors': [{'type': 'autor', 'name': 'Джеймс Роллинс', 'name_orig': 'James Rollins'}]}


def manifest(candidate, gaps=('original_title',), title='Око Бога', author='Джеймс Роллинс'):
    return {'candidate_id': candidate, 'metadata': {'title': title, 'canonical_author': 'Rollins James', 'series': ''},
            'metadata_facts': {'gap_search': {'gaps': list(gaps), 'unfilled': list(gaps), 'closed_sources': [], 'from_cache': True,
                                              'background': list(gaps), 'ask': {'title': title, 'author': author, 'partial': False}}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(self.temp.cleanup); self.base = Path(self.temp.name)
        self.now = [100000.0]; self.database = self.base / 'catalog.sqlite3'
        self.sources = Catalog(); self.client = PublicClient(self.database, fetch=self.sources.fetch, clock=lambda: self.now[0])
        with connect(self.database) as db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,manifest_hash TEXT,state TEXT,stage TEXT,attempt_id TEXT,journal TEXT,output TEXT,reason TEXT,created TEXT,updated TEXT)')
        merge = SimpleNamespace(inventory=SimpleNamespace(database=str(self.database)), stage_root=str(self.base / 'stage'))
        self.research = PublicResearch(self.client, leads=[])
        self.fill = GapFill(merge, research=self.research, clock=lambda: self.now[0])

    def job(self, value, state='completed', created='2026-10-25T10:00:00Z'):
        job_id = str(uuid.uuid4())
        with connect(self.database) as db:
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)', (job_id, json.dumps(value, ensure_ascii=False), '', state, state, None, '{}', None, '', created, created))
        return job_id

    def lanes(self):
        with connect(self.database) as db:
            return [tuple(r) for r in db.execute('SELECT host,lane FROM public_research_lanes ORDER BY at')]


class GapFillTests(Base):
    def test_the_pass_records_what_a_source_confirms_in_its_own_lane_and_changes_no_book(self):
        job_id = self.job(manifest('book-1'))
        with connect(self.database) as db: before = db.execute('SELECT * FROM audio_jobs').fetchall()
        self.fill.run_pass()
        entry = self.fill.entry(job_id)
        self.assertEqual(entry['state'], 'found', entry)
        found = entry['record']['found']['catalog']
        self.assertEqual((found['original_title'], found['language'], found['source_url']), ('The Eye of God', 'en', 'https://fantlab.ru/work42'))
        self.assertTrue(entry['record']['receipts'], 'with the fetched receipts')
        self.assertEqual({lane for _, lane in self.lanes()}, {'gap'}, 'reserved in the gap lane')
        with connect(self.database) as db: self.assertEqual(db.execute('SELECT * FROM audio_jobs').fetchall(), before, 'the book itself is not changed')
        asked = len(self.sources.calls); self.fill.run_pass()
        self.assertEqual(len(self.sources.calls), asked, 'a recorded book is not asked again')

    def test_a_closed_source_defers_the_book_until_it_reopens(self):
        self.sources.closed = {'api.fantlab.ru', 'www.wikidata.org'}
        job_id = self.job(manifest('book-1'))
        self.fill.run_pass()
        entry = self.fill.entry(job_id)
        self.assertEqual(entry['state'], 'deferred', entry); retry = entry['record']['next_attempt']
        self.assertGreater(retry, self.now[0]); self.assertEqual(self.fill.candidates(), [], 'not before the source reopens')
        self.assertLessEqual(self.fill._next_wait(), max(gap_fill.MIN_WAIT, retry - self.now[0]))
        self.sources.closed = set(); self.now[0] = retry + 1
        self.fill.run_pass()
        self.assertEqual(self.fill.entry(job_id)['state'], 'found')

    def test_only_books_approved_with_background_gaps_and_only_their_newest_job(self):
        self.job({'candidate_id': 'old-book', 'metadata': {}, 'metadata_facts': {'gap_search': {'gaps': ['original_title'], 'unfilled': ['original_title']}}})
        self.job({'candidate_id': 'series-only', 'metadata': {}, 'metadata_facts': {'gap_search': {'background': [], 'ask': None}}})
        self.job(manifest('book-1'), state='needs attention', created='2026-10-25T09:00:00Z')
        newest = self.job(manifest('book-1'), created='2026-10-25T11:00:00Z')
        self.assertEqual([job_id for job_id, _ in self.fill.candidates()], [newest])

    def test_no_answer_is_recorded_as_none_and_never_asked_again(self):
        self.sources.fantlab = []
        job_id = self.job(manifest('book-1'))
        self.fill.run_pass(); self.assertEqual(self.fill.entry(job_id)['state'], 'none')
        self.assertEqual(self.fill.candidates(), [])

class ServiceTests(ApproveFixture):
    def test_the_app_starts_the_pass_with_series_backfill_on_the_automatic_research_and_stops_it_on_close(self):
        import contextlib
        self.start()
        fill = self.service.gap_fill
        self.assertIs(fill.research, self.service.automatic.research, 'the automatic pass\'s client, cache and site ledger')
        self.assertIsNone(fill.thread, 'not started by construction')
        self.service.start_retention(contextlib.nullcontext)
        self.assertTrue(fill.thread.is_alive() and self.service.series_backfill.thread.is_alive())
        self.service.close()
        self.assertFalse(fill.thread.is_alive(), 'Quit stops it')


class LaneTests(Base):
    def read(self, url, lane):
        return self.client.read(url, None, {'remaining': 5, 'lane': lane})

    def test_a_background_lane_uses_at_most_its_share_and_research_keeps_the_rest(self):
        share = int(public_research.APP_HOST_REQUESTS * public_research.BACKGROUND_SHARE)
        with connect(self.database) as db:
            db.executemany('INSERT INTO public_research_lanes VALUES(?,?,?)', [('api.fantlab.ru', self.now[0] - 3000 + n, 'gap') for n in range(share)])
        with self.assertRaises(ResearchWait) as raised:
            self.read('https://api.fantlab.ru/search-works?q=1', 'gap')
        self.assertEqual((raised.exception.kind, raised.exception.scope), ('app_limit', 'lane'))
        self.assertEqual(raised.exception.retry_at, self.now[0] - 3000 + public_research.APP_HOST_WINDOW, 'when its oldest request leaves the hour')
        self.assertTrue(self.read('https://api.fantlab.ru/search-works?q=2', 'series'), 'the other background pass keeps its own share')
        self.now[0] += 2
        self.assertTrue(self.read('https://api.fantlab.ru/search-works?q=3', 'research'), 'research keeps the rest of the bound')
        with self.assertRaises(ValueError): self.read('https://api.fantlab.ru/search-works?q=4', 'other')

    def test_the_wikimedia_family_counts_as_one_site_for_a_lane(self):
        share = int(100 * public_research.BACKGROUND_SHARE)
        with connect(self.database) as db:
            db.executemany('INSERT INTO public_research_lanes VALUES(?,?,?)', [('en.wikipedia.org' if n % 2 else 'www.wikidata.org', self.now[0] - 3000 + n, 'series') for n in range(share)])
        with self.assertRaises(ResearchWait) as raised:
            self.read('https://ru.wikipedia.org/w/api.php?q=1', 'series')
        self.assertEqual(raised.exception.scope, 'lane')

    def test_series_backfill_reserves_in_the_series_lane(self):
        self.sources.goodreads_search = search_page(('42', 'Око Бога (Отряд Сигма, #8)', ['James Rollins']))
        self.sources.goodreads_books['42'] = book_page('42', 'Око Бога', ['James Rollins'], 'Отряд Сигма', '8')
        merge = SimpleNamespace(inventory=SimpleNamespace(database=str(self.database)), stage_root=str(self.base / 'stage'))
        backfill = SeriesBackfill(merge, research=self.research, clock=lambda: self.now[0])
        found = backfill.lookup({'metadata': {'title': 'Око Бога', 'canonical_author': 'Rollins James'}})
        self.assertEqual((found['name'], found['number']), ('Отряд Сигма', '8'))
        self.assertEqual({lane for _, lane in self.lanes()}, {'series'})


class ClientLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AREA); self.addCleanup(self.temp.cleanup)
        self.release, self.fetching, self.started = threading.Event(), threading.Event(), []

    def fetch(self, url, *_):
        self.started.append((url, time.monotonic()))
        if 'slow' in url:
            self.fetching.set(); self.release.wait(10)
        return b'{"ok": true}'

    def test_a_cached_answer_never_waits_behind_another_threads_request(self):
        client = PublicClient(Path(self.temp.name) / 'c.sqlite3', fetch=self.fetch)
        client.read('https://api.fantlab.ru/cached', None, {'remaining': 1})
        self.addCleanup(self.release.set)
        slow = threading.Thread(target=lambda: client.read('https://www.goodreads.com/slow', None, {'remaining': 1, 'lane': 'series'}), daemon=True)
        slow.start(); self.assertTrue(self.fetching.wait(5))
        began = time.monotonic(); client.read('https://api.fantlab.ru/cached', None, {'remaining': 0})
        self.assertLess(time.monotonic() - began, 0.5, 'the cached read waited for the background download')
        self.release.set(); slow.join(10)

    def test_requests_to_one_site_stay_spaced_from_two_threads(self):
        client = PublicClient(Path(self.temp.name) / 'c.sqlite3', fetch=self.fetch)
        threads = [threading.Thread(target=lambda n=n: client.read('https://api.fantlab.ru/q%d' % n, None, {'remaining': 1, 'lane': lane}), daemon=True)
                   for n, lane in enumerate(('research', 'gap'))]
        for thread in threads: thread.start()
        for thread in threads: thread.join(10)
        times = sorted(at for _, at in self.started)
        self.assertEqual(len(times), 2); self.assertGreaterEqual(times[1] - times[0], public_research.host_policy('api.fantlab.ru')[1] - 0.05)


if __name__ == '__main__':
    unittest.main()

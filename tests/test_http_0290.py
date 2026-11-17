"""0.29.0, PA-1 (Futaba's pattern alert, accepted): each new page-to-server field and hook of this version through the REAL
server. A BrowserServer and its Handler answer over loopback HTTP with the page's token; behind them is a real MergeService
over a private fixture catalog with real private audio (FFmpeg) and offline research. No mock merge, no library, no
network, no window.

- Light novel through every save and approve route the page uses: Edit names Save (names-save and the durable names
  decision), Approve with an open editor (approve-preview, approve and the durable approve decision), the details panel's
  metadata save (candidate review and the durable review decision) and the Manual Conversion window's save.
- The scan-end hook: a finished scan runs the check pass; a book whose files Sergei deleted leaves Needs attention and stays
  off after the next scan, listed once in Details.

The entry tests before this file mocked the page-to-server hop, so B-1 (light_novel refused), M-1 (500 on the details
panel) and M-2 (no pass after a scan) passed them."""
import http.client
import json
import os
import shutil
import threading
import time
import unittest
import urllib.parse
import uuid
from pathlib import Path
from unittest.mock import patch

import entered_names
import web_server
from test_approve_as_is import ApproveFixture, tone


@unittest.skipUnless(os.name == 'nt' and shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Windows and FFmpeg required')
class RealServerTests(ApproveFixture):
    def serve(self):
        """Scan the private library, then answer through a real server whose engine is the fixture's MergeService."""
        rows = self.start()
        service = self.service
        service.start_retention = lambda admission: None  # no idle housekeeping thread in a short test
        service.start_published_check = lambda: None

        def factory(inventory, cache, progress=None):
            return service
        self.server = web_server.BrowserServer(('127.0.0.1', 0), self.inv, factory)
        self.assertNotEqual(self.server.server_port, 5210, 'never Sergei\'s app port')
        threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .05}, daemon=True).start()
        self.addCleanup(self.stop_server)
        return rows

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, route, body=None, method='POST'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=60)
        headers = {'X-Books-Token': self.server.token, 'Host': f'127.0.0.1:{self.server.server_port}'}
        raw = None
        if body is not None:
            raw = json.dumps(body, ensure_ascii=False).encode('utf-8')
            headers.update({'Content-Type': 'application/json', 'Content-Length': str(len(raw))})
        connection.request(method, route, body=raw, headers=headers)
        response = connection.getresponse()
        value = json.loads(response.read().decode('utf-8') or 'null')
        connection.close()
        return response.status, value

    def row(self, title):
        return next(r for r in self.service.reviews.page()['rows'] if title in (r.get('title_clue') or '') or any(title in m['path'] for m in r['members']))

    def identity(self, row):
        return {'library': 'Audiobooks', 'id': row['id'], 'revision': row['revision']}

    def decision(self, row, action, payload):
        """The page's own Save and Approve path (bookDecision): one durable request, then its application."""
        request_id = str(uuid.uuid4())
        status, answer = self.call('/api/book-decisions', dict(self.identity(row), fingerprint=row['fingerprint'], request_id=request_id, action=action, payload=payload))
        self.assertEqual(status, 202, answer)
        deadline = time.monotonic() + 60
        while True:
            status, answer = self.call('/api/book-decisions/status', {'request_id': request_id})
            if status == 200 and answer['decision']['state'] not in ('accepted', 'applying'):
                return answer['decision']
            if time.monotonic() > deadline:
                self.fail('the decision was not applied within 60 s: %r' % (answer,))
            time.sleep(.1)

    def light_novel_book(self):
        tone(self.audio / 'Light Novels' / 'Ayatsuji Yukito' / 'Иная' / '01.mp3', self.cover, album='Иная', artist='Ayatsuji Yukito', title='Глава 1')

    # ----------------------------------------------------------------------------------------------- light_novel routes
    def test_edit_names_save_carries_light_novel_b_1(self):
        self.light_novel_book()
        self.serve()
        row = self.row('Иная')
        names = {'title': 'Иная', 'author': 'Ayatsuji Yukito', 'series': '', 'number': '', 'universe': '', 'collection': False, 'light_novel': False}
        status, answer = self.call('/api/candidate/names-save', dict(self.identity(row), names=names))
        self.assertEqual(status, 200, answer)
        self.assertIs(entered_names.book_values(self.inv.database, row).get('light_novel'), False, 'his untick is saved')
        # The page's Save: the durable names decision. Ticked again, the box matches the folder: his No is taken back
        # (a "files" entry, no correction) and the book files under Light Novels again.
        row = self.row('Иная')
        decision = self.decision(row, 'names', {'names': {'light_novel': True}})
        self.assertEqual(decision['state'], 'applied', decision)
        self.assertNotIn('light_novel', entered_names.book_values(self.inv.database, row))
        row = self.row('Иная')
        status, answer = self.call('/api/candidate/approve-preview', dict(self.identity(row), names={}))
        self.assertEqual((status, Path(answer['preview']['path']).parts[0]), (200, 'Light Novels'), answer)

    def test_edit_names_pre_ticks_a_ranobe_book_whose_author_is_unresolved_m_6(self):
        # Futaba M-6: the editor read "proposal: false" for «Книга Ранобэ» (Author unclear) although its folder pre-ticks,
        # so an untouched Save would have stored an explicit No over the folder.
        tone(self.audio / 'Ранобэ' / 'Книга Ранобэ' / '01.mp3', self.cover, album='Книга Ранобэ', title='Глава 1', artist='Лев Толстой', album_artist='Антон Чехов')
        tone(self.audio / 'Обычные' / 'Книга Без' / '01.mp3', self.cover, album='Книга Без', title='Глава 1', artist='Лев Толстой', album_artist='Антон Чехов')
        self.serve()
        row = self.row('Книга Ранобэ')
        self.assertEqual(self.research(row)['ask']['kind'], 'author_unclear', 'positive control: two people credited, the author is unresolved')
        status, answer = self.call('/api/candidate/names', self.identity(row))
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer['editor']['fields']['light_novel'], {'proposal': True, 'basis': 'folder_name'})
        self.assertIs(answer['editor']['place'].get('light_novel'), True, 'the Place line leads with Light novel')
        # The case 50ce63c got wrong: a research result with no review yet (an author whose spelling is still asked: the
        # Goes to line has no path) previews a place without Light novel, and the editor took its No over the folder's
        # pre-tick. Futaba's exact catalog state was not rebuilt here; the preview such a result gives is.
        no_review = {'path': '', 'absolute': '', 'taken': False, 'title': 'Книга Ранобэ', 'author': '', 'collection': False,
                     'reason': "Enter the author's English name, then approve.", 'place': {'universe': '', 'series': '', 'number': '', 'collection': False}}
        with patch.object(self.service, 'approval_preview', return_value=no_review):
            status, answer = self.call('/api/candidate/names', self.identity(row))
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer['editor']['fields']['light_novel'], {'proposal': True, 'basis': 'folder_name'}, 'the folder pre-tick stays')
        self.assertIs(answer['editor']['place'].get('light_novel'), True)
        with patch.object(self.service, 'approval_preview', return_value=dict(no_review, place=dict(no_review['place'], collection=True))):
            status, answer = self.call('/api/candidate/names', self.identity(row))
        self.assertEqual(answer['editor']['fields']['light_novel']['proposal'], False, 'a collection is never pre-ticked a light novel (one or the other)')
        plain = self.row('Книга Без')
        status, answer = self.call('/api/candidate/names', self.identity(plain))
        self.assertEqual(answer['editor']['fields']['light_novel'], {'proposal': False, 'basis': ''}, 'positive control: no such folder')

    def test_approve_with_an_open_editor_carries_light_novel_b_1(self):
        self.light_novel_book()
        tone(self.audio / 'Light Novels' / 'Ayatsuji Yukito' / 'Другая' / '01.mp3', self.cover, album='Другая', artist='Ayatsuji Yukito', title='Глава 1')
        self.serve()
        row = self.row('Иная')
        editor = {'series': '', 'number': '', 'universe': '', 'collection': False}
        status, answer = self.call('/api/candidate/approve-preview', dict(self.identity(row), names=dict(editor, light_novel=True)))
        self.assertEqual(status, 200, answer)
        self.assertEqual(Path(answer['preview']['path']).parts[0], 'Light Novels')
        status, answer = self.call('/api/candidate/approve-preview', dict(self.identity(row), names=dict(editor, light_novel=False)))
        self.assertEqual(status, 200, answer)
        self.assertNotEqual(Path(answer['preview']['path']).parts[0], 'Light Novels', 'the box undoes the folder pre-tick')
        status, answer = self.call('/api/candidate/approve', dict(self.identity(row), names=dict(editor, light_novel=False)))
        self.assertEqual(status, 200, answer)
        job = next(j for j in self.service.jobs.status()['jobs'] if j['job_id'] == answer['job_id'])
        self.assertNotIn('Light Novels', Path(job['manifest']['destination']).parts)
        # The page's Approve: the durable approve decision, on the second book.
        other = self.row('Другая')
        decision = self.decision(other, 'approve', {'names': dict(editor, light_novel=True)})
        self.assertEqual(decision['state'], 'applied', decision)
        job = next(j for j in self.service.jobs.status()['jobs'] if j['manifest']['candidate_id'] == other['id'])
        self.assertIn('Light Novels', Path(job['manifest']['destination']).parts)

    def test_details_panel_metadata_save_carries_light_novel_m_1(self):
        self.light_novel_book()
        self.serve()
        row = self.row('Иная')
        review = {'title': 'Иная', 'author': 'Ayatsuji Yukito', 'canonical_author': 'Ayatsuji Yukito', 'original_language': 'Other', 'series': '', 'number': '',
                  'genre': '', 'topic': 'Школа', 'multi_author': False, 'anthology': False, 'narrator': '', 'universe': '', 'light_novel': True}
        status, answer = self.call('/api/candidate/review', dict(self.identity(row), review=review, approve=False))
        self.assertEqual(status, 200, answer)
        saved = self.service.reviews._row('Audiobooks', row['id'])['review']
        self.assertEqual((saved['light_novel'], saved['topic']), (True, 'Школа'))
        status, answer = self.call('/api/candidate/review', dict(self.identity(self.row('Иная')), review=dict(review, light_novel=False, anthology=True), approve=False))
        self.assertEqual(status, 200, answer)
        self.assertNotIn('light_novel', self.service.reviews._row('Audiobooks', row['id'])['review'], 'the key exists only when True')
        status, answer = self.call('/api/candidate/review', dict(self.identity(self.row('Иная')), review=dict(review, anthology=True), approve=False))
        self.assertEqual((status, answer['error']), (400, 'A book is a light novel or a short-story collection, not both. Untick one of them.'))
        # The page's panel Save: the durable review decision.
        decision = self.decision(self.row('Иная'), 'review', {'review': dict(review, topic='Мистика'), 'approve': False})
        self.assertEqual(decision['state'], 'applied', decision)
        saved = self.service.reviews._row('Audiobooks', row['id'])['review']
        self.assertEqual((saved['light_novel'], saved['topic']), (True, 'Мистика'))

    def test_manual_conversion_save_carries_light_novel(self):
        self.serve()
        import tempfile
        import test_automatic_processing as automatic_fixtures
        external = tempfile.TemporaryDirectory(dir=automatic_fixtures.AREA)  # outside the app's data folder, as the window asks
        self.addCleanup(external.cleanup)
        folder = Path(external.name) / 'Light Novels' / 'Ручная'
        tone(folder / '01.mp3', self.cover, album='Ручная', artist='Автор')
        status, inspection = self.call('/api/manual-conversion/inspect', {'kind': 'folder', 'path': str(folder)})
        self.assertEqual(status, 200, inspection)
        metadata = {'title': 'Ручная', 'author': 'Автор', 'series': '', 'number': '', 'universe': '', 'collection': '', 'anthology': False, 'light_novel': True}
        request = {'id': str(uuid.uuid4()), 'revision': 0, 'source': inspection['source'], 'tracks': inspection['tracks'], 'inspections': inspection['inspections'],
                   'metadata': metadata, 'metadata_touched': ['light_novel'], 'destination': ''}
        status, answer = self.call('/api/manual-conversion/save', request)
        self.assertEqual(status, 200, answer)
        self.assertIs(answer['draft']['metadata']['light_novel'], True)
        status, listed = self.call('/api/manual-conversion', method='GET')
        self.assertEqual(status, 200, listed)
        drafts = listed if isinstance(listed, list) else listed.get('drafts') or listed.get('items') or []
        self.assertIs(next(d for d in drafts if d['id'] == request['id'])['metadata']['light_novel'], True, 'kept with the draft')
        status, answer = self.call('/api/manual-conversion/save', dict(request, revision=answer['draft']['revision'], metadata=dict(metadata, light_novel=False)))
        self.assertEqual(status, 200, answer)
        self.assertIs(answer['draft']['metadata']['light_novel'], False, 'his untick is his value')

    # ------------------------------------------------------------------------------------------------ the scan-end hook
    def attention(self):
        status, state = self.call(f'/api/state?library=Audiobooks', method='GET')
        self.assertEqual(status, 200)
        counts = state['audiobook_jobs']['attention_counts']
        return {key: value for key, value in counts.items() if key != 'all' and value}, state

    def settle(self):
        """The scan has ended and the pass it asked for (thread books-source-check, started from the scan's own thread
        before it ends) has ended too."""
        deadline = time.monotonic() + 90
        while True:
            worker = self.inv.worker
            busy = worker is not None and worker.is_alive() or any(t.name == 'books-source-check' and t.is_alive() for t in threading.enumerate())
            if not busy:
                return
            if time.monotonic() > deadline:
                self.fail('the scan or its check pass did not end within 90 s')
            time.sleep(.05)

    def test_a_finished_scan_runs_the_check_pass_and_a_gone_book_leaves_needs_attention_m_2_m_3(self):
        gone = [tone(self.audio / 'Unsorted' / 'Утро снайпера' / ('%02d.mp3' % n), self.cover, album='Утро снайпера', title='Глава %d' % n, track='%d/2' % n) for n in (1, 2)]
        self.serve()
        row = self.row('Утро снайпера')
        self.service.automatic._record(row, 'Held', dict(self.research(row), reasons=['fixture hold']))  # researched: a question
        counts, state = self.attention()
        self.assertEqual(counts, {'title_author': 1}, 'positive control: listed in Needs attention')
        self.assertIsNone(state.get('source_check'), 'no pass has run yet in this server')
        for path in gone:
            path.unlink()
        for scan in (1, 2):
            status, answer = self.call('/api/scan/start', {'library': 'Audiobooks'})
            self.assertIn(status, (200, 202), answer)
            self.settle()
            counts, state = self.attention()
            check = state.get('source_check')
            self.assertIsNotNone(check, 'scan %d: the check pass ran after the scan' % scan)
            self.assertEqual(counts, {}, 'scan %d: the gone book left Needs attention' % scan)
            self.assertEqual((check['removed'], [item['title'] for item in check['removed_list']]), (1, ['Утро снайпера']), 'scan %d: listed once in Details' % scan)
        self.assertEqual(self.service.needs_you(), {})
        # Senua D-m3: the scan's pass records when it checked the root, so a drive-return pass waiting to be tried again
        # knows the root is done.
        import source_presence
        self.assertIn(source_presence._key(str(self.audio)), self.service.__dict__.get('_source_checked_at', {}))

    def scan(self):
        status, answer = self.call('/api/scan/start', {'library': 'Audiobooks'})
        self.assertIn(status, (200, 202), answer)
        self.settle()

    def test_a_book_whose_files_come_back_unchanged_is_listed_again_d_m1(self):
        # Senua D-M1 (probe P5): the folder goes away and comes back with the same bytes and times (a Recycle Bin restore,
        # a folder moved back, a short drive drop): the real scanner hashes it to the fingerprint the pass recorded, so only
        # the pass testing the paths again can list it again. Both ways: no scan while it was away, and a scan meanwhile.
        [tone(self.audio / 'Unsorted' / 'Утро снайпера' / ('%02d.mp3' % n), self.cover, album='Утро снайпера', title='Глава %d' % n, track='%d/2' % n) for n in (1, 2)]
        self.serve()
        row = self.row('Утро снайпера')
        self.service.automatic._record(row, 'Held', dict(self.research(row), reasons=['fixture hold']))
        self.assertEqual(self.attention()[0], {'title_author': 1}, 'positive control: listed in Needs attention')
        folder, away = self.audio / 'Unsorted' / 'Утро снайпера', self.base / 'away'
        # 1. Away, the pass runs with no scan (a launch while the drive was briefly gone); back; the next scan's pass.
        os.rename(folder, away)
        self.assertEqual([item['id'] for item in self.service.check_sources()['removed']], [row['id']])
        self.assertEqual(self.attention()[0], {}, 'off the list while the files are away')
        os.rename(away, folder)
        self.scan()
        self.assertEqual(self.row('Утро снайпера')['fingerprint'], row['fingerprint'], 'the scan sees the very same files')
        self.assertEqual(self.attention()[0], {'title_author': 1}, 'listed again after the files came back unchanged')
        # 2. Away across a scan (its files marked missing), back, the next scan's pass.
        os.rename(folder, away)
        self.scan()
        self.assertEqual(self.attention()[0], {}, 'the scan and its pass take it off')
        os.rename(away, folder)
        self.scan()
        # The two scans moved its revision, so automatic processing researches it again first: not hidden, still checking.
        self.assertEqual(self.service.todo_coverage(), {'listed': 0, 'still_checking': 1, 'removed': 0, 'with_job': 0})
        again = self.row('Утро снайпера')
        self.assertEqual(again['fingerprint'], row['fingerprint'])
        self.service.automatic._record(again, 'Held', dict(self.research(again), reasons=['fixture hold']))
        self.assertEqual(self.attention()[0], {'title_author': 1}, 'listed again once the files are back')
        _counts, state = self.attention()
        self.assertEqual(state['source_check']['removed'], 0, 'a book listed again is not counted as removed')


    def listing(self, status, search=''):
        query = urllib.parse.urlencode({'library': 'Audiobooks', 'view': 'candidates', 'status': status, 'search': search})
        status_code, page = self.call('/api/inventory?' + query, method='GET')
        self.assertEqual(status_code, 200, page)
        return sorted(row['title_clue'] for row in page['rows']), page['total']

    def test_a_gone_book_leaves_all_candidates_and_the_count_a_converted_one_stays_m_5(self):
        # Futaba M-5 (Sergei: yes): a book whose source is gone leaves All candidates and the "N book candidates found"
        # count too, list-only. A converted book (its sources removed by the app's own cleanup) stays everywhere.
        gone = [tone(self.audio / 'Unsorted' / 'Утро снайпера' / ('%02d.mp3' % n), self.cover, album='Утро снайпера', title='Глава %d' % n, track='%d/2' % n) for n in (1, 2)]
        done = tone(self.audio / 'Unsorted' / 'Тайна дома' / '01.mp3', self.cover, album='Тайна дома', title='Глава 1')
        self.serve()
        book = self.row('Тайна дома')
        self.service.approve_book(book['id'], book['revision'], author='Чехов Антон')
        self.start_and_wait()
        self.assertFalse(done.exists(), 'positive control: the app removed the converted book\'s sources')
        self.assertEqual(self.listing('converted')[0], ['Тайна дома'])
        before = self.listing('all')
        self.assertEqual(before, (['Тайна дома', 'Утро снайпера'], 2), 'positive control: both listed')
        self.assertEqual(self.attention()[1]['audiobook_jobs']['candidate_total'], 2)
        for path in gone:
            path.unlink()
        self.scan()
        self.assertEqual(self.attention()[1]['source_check']['removed'], 1)
        self.assertEqual(self.listing('all'), (['Тайна дома'], 1), 'the gone book left All candidates; the converted one stayed')
        self.assertEqual(self.listing('converted')[0], ['Тайна дома'], 'the converted list is untouched')
        jobs = self.attention()[1]['audiobook_jobs']
        self.assertEqual((jobs['candidate_total'], jobs['not_approved_total']), (1, 0), 'the count leaves it out too')
        self.assertEqual(self.listing('all', 'Утро'), ([], 0), 'nor found by a search in All candidates')


if __name__ == '__main__':
    unittest.main()

"""0.30.0 QA follow-ups (Futaba's findings on 5dbba45) on Join and part sets:
- D1: an always-queued press (Join, Approve) that nothing blocks names no blocker; it named the queue's own 'operation',
  then the action itself ("runs when Join … finishes").
- D2: part sets read the repaired tag text (cp1251 stored as Latin-1 in only some parts split one book 2+3).
- D3: Cancel retry with a malformed job id is a bad request (400), never a refusal (409).
- C2: the real «Darwin's Blade» shape (albums "… Blade 1" / "… Blade 2", no track numbers, chapters that continue) is one
  book ordered by the album part numbers: no "Mixed recordings in this group", no "Playback order uncertain".
Synthetic tags; tiny private audio (FFmpeg) for C2 and the real server for D3. No network, no library."""
import shutil, subprocess, threading, unittest, uuid
from pathlib import Path
from unittest import mock

import groups
import test_approve_as_is
from action_queue import ActionQueue
from test_action_queue import Server as StubServer
from test_split_books import row as catalog_row


def part(path, title, chapters, album, artist, track=None, total=None, seconds=1):
    """A private .m4b part; track None leaves the track tag out (the Darwin's Blade files carry none)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    args = [shutil.which('ffmpeg'), '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=%d' % seconds]
    meta = path.with_suffix('.txt')
    meta.write_text(';FFMETADATA1\n' + ''.join('[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n' % c for c in chapters), encoding='utf-8')
    args += ['-f', 'ffmetadata', '-i', str(meta), '-map', '0:a', '-map_chapters', '1', '-c:a', 'aac', '-b:a', '64k', '-ar', '44100', '-ac', '1',
             '-metadata', 'album=' + album, '-metadata', 'artist=' + artist, '-metadata', 'title=' + title]
    if track is not None:
        args += ['-metadata', 'track=%d/%d' % (track, total) if total else 'track=%d' % track]
    subprocess.run(args + [str(path)], check=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    meta.unlink()
    return path


def mojibake(text):
    """cp1251 bytes read as Latin-1: what an old tagger left in some of Sergei's files."""
    return text.encode('cp1251').decode('latin-1')


class QueueBlockerTests(unittest.TestCase):
    """D1: the answer and the queue's view name no blocker for an always-queued press nothing blocks."""
    def queue(self):
        queue = ActionQueue(StubServer(), poll=.02, store=False)
        queue._start = lambda: None  # no worker: the press stays queued, as it is for an instant before it runs
        queue.explainer = lambda kind, item: {'kind': kind, 'cause': 'action', 'title': item.get('title')}
        self.addCleanup(queue.close)
        return queue

    def test_nothing_blocks_it_so_it_names_no_blocker(self):
        queue = self.queue()
        answer = queue.enqueue('approve', str(uuid.uuid4()), 'Впусти меня', {'revision': 1})
        self.assertTrue(answer['queued'])
        self.assertIsNone(answer['blocker'], answer)
        self.assertIsNone(queue.view()['queued_actions'][0]['blocker'])
        behind = queue.enqueue('approve', str(uuid.uuid4()), 'Другая книга', {'revision': 1})
        self.assertEqual(behind['blocker']['kind'], 'operation', 'positive control: one behind it waits for the press ahead')

    def test_explain_queue_keeps_no_blocker(self):
        import background_work
        view = {'queued_actions': [{'id': 'a', 'action': 'join', 'book_id': 'b', 'title': 'T', 'blocker': None},
                                   {'id': 'c', 'action': 'approve', 'book_id': 'd', 'title': 'U', 'blocker': {'kind': 'scan'}}], 'queue_running': None}
        background_work.explain_queue(view, {})
        self.assertIsNone(view['queued_actions'][0]['blocker'])
        self.assertEqual(view['queued_actions'][1]['blocker']['cause'], 'scan', 'positive control: a real blocker keeps its cause')


class RepairedTagTests(unittest.TestCase):
    """D2: groups._part_sets compares the repaired tag text."""
    def rows(self, broken=()):
        album, artist = 'Впусти меня', 'Йон Айвиде Линдквист'
        return [catalog_row('Lindqvist/Впусти меня/Впусти меня %d.m4b' % n, {'album': mojibake(album) if n in broken else album,
                'artist': mojibake(artist) if n in broken else artist, 'title': 'Впусти меня %d' % n, 'track': '%d/5' % n}) for n in range(1, 6)]

    def test_parts_mis_encoded_in_only_some_files_are_one_set(self):
        clean = groups.build(self.rows())
        self.assertEqual([len(g['members']) for g in clean.values()], [5], 'positive control: one set when every tag reads the same')
        built = groups.build(self.rows(broken=(2, 4)))
        self.assertEqual([len(g['members']) for g in built.values()], [5], [len(g['members']) for g in built.values()])
        self.assertTrue(next(iter(built.values())).get('part_set'))

    def test_the_grouping_version_moves_so_every_root_regroups_once(self):
        self.assertIn('m4b-parts-v5', groups.GROUP_VERSION)  # v5: the C2 delta (a catalog grouped by v4 regroups once more)


class AlbumPartNumberTests(unittest.TestCase):
    """C2 at grouping: the album part numbers order an item-7 set; recordings that differ stay apart."""
    def test_the_album_part_numbers_order_the_set_whatever_the_file_names(self):
        rows = [catalog_row("Simmons/Darwin's Blade %s.m4b" % name, {'album': "Dale Stewart 04 - Darwin's Blade %d" % n, 'artist': 'Dan Simmons',
                'title': "Darwin's Blade %s" % name}) for name, n in (('A', 2), ('B', 1))]
        built = groups.build(rows)
        self.assertEqual(len(built), 1, list(built))
        group = next(iter(built.values()))
        self.assertEqual([Path(m['path']).name for m in group['members']], ["Darwin's Blade B.m4b", "Darwin's Blade A.m4b"])
        self.assertEqual(group['part_set']['order_basis'], groups.ALBUM_PART_BASIS)

    def test_recordings_that_differ_never_form_the_set(self):
        rows = [catalog_row("Simmons/Darwin's Blade %d.m4b" % n, dict({'album': "Darwin's Blade %d" % n, 'artist': 'Dan Simmons', 'title': "Darwin's Blade %d" % n},
                **({'narrator': reader} if reader else {}))) for n, reader in ((1, 'Чтец Один'), (2, 'Чтец Два'))]
        self.assertEqual(len(groups.build(rows)), 2, 'different readers: two books, never one set')


class DarwinsBladeTests(test_approve_as_is.ApproveFixture):
    """C2 through research: the source gate takes the order from the album part numbers and the albums as one recording."""
    def make(self, numbers=(1, 2)):
        folder = self.audio / 'Simmons Dan' / 'Dale Stewart'
        for n in numbers:
            part(folder / ("Dale Stewart 04 - Darwin's Blade %d.m4b" % n), "Dale Stewart 04 - Darwin's Blade %d" % n,
                 [(0, 500, 'Глава %d' % (2 * n - 1)), (500, 1000, 'Глава %d' % (2 * n))], album="Dale Stewart 04 - Darwin's Blade %d" % n, artist='Dan Simmons')
        rows = self.start()
        self.assertEqual([len(r['members']) for r in rows], [len(numbers)], 'item 7: one set')
        return rows[0]

    def test_c2_the_real_shape_is_one_book_with_no_hold(self):
        row = self.make()
        self.assertEqual(row['part_set']['order_basis'], groups.ALBUM_PART_BASIS)
        result = self.research(row)
        self.assertEqual((result['part_set']['decision'], result['reasons']), ('join', []), result.get('reasons'))

    def test_c2_a_missing_part_still_holds_the_order(self):
        row = self.make((1, 3))
        reasons = self.research(row)['reasons']
        self.assertIn('Playback order uncertain', reasons, 'a gap in the part numbers is still a question')
        self.assertNotIn('Mixed recordings in this group', reasons)


class AutomaticRunTests(test_approve_as_is.ApproveFixture):
    """C2 delta (Futaba on 03041ee): the grouping still carried "Different book album/title clues may indicate mixed works"
    for a set joined by its album part numbers, so the real automatic run held «Darwin's Blade» with no job while a
    same-album control converted. Now the conflict goes for such a set; the negatives still hold or stay apart."""
    def make(self, folder, album, numbers=(1, 2), artists=None):
        for n in numbers:
            part(self.audio / 'Simmons Dan' / folder / ('%s %d.m4b' % (album, n)), '%s %d' % (album, n),
                 [(0, 500, 'Глава %d' % (2 * n - 1)), (500, 1000, 'Глава %d' % (2 * n))],
                 album='%s %d' % (album, n), artist=(artists or {}).get(n, 'Dan Simmons'))

    def run_automatic(self, settle=60):
        """Start automatic processing; once it has finished (or after settle seconds: a held book keeps a run waiting for its
        next try), stop it and let the conversion queue finish."""
        import time
        automatic = self.service.automatic
        automatic.start()
        running = lambda: (automatic.thread and automatic.thread.is_alive()) or automatic.status()['state'] in ('Running', 'Stopping')
        limit = time.monotonic() + settle
        while running() and time.monotonic() < limit:
            time.sleep(.1)
        if running():
            automatic.stop()
            limit = time.monotonic() + 60
            while running():
                self.assertLess(time.monotonic(), limit, 'automatic processing did not stop')
                time.sleep(.1)
        self.wait()

    def jobs_for(self, folder):
        return [j for j in self.service.jobs.status()['jobs'] if any(Path(s['path']).parent.name == folder for s in j['manifest']['sources'])]

    def test_the_real_automatic_run_converts_darwins_blade_like_a_same_album_set(self):
        self.make('Dale Stewart', "Dale Stewart 04 - Darwin's Blade")
        for n in (1, 2):  # the control: one album on both parts, the track tags order it (converted before the fix too)
            part(self.audio / 'Simmons Dan' / 'Control' / ('Контроль %d.m4b' % n), 'Контроль %d' % n, [(0, 500, 'Глава %d' % (2 * n - 1)), (500, 1000, 'Глава %d' % (2 * n))],
                 album='Контроль', artist='Dan Simmons', track=n, total=2)
        rows = self.start()
        self.assertEqual(sorted(len(r['members']) for r in rows), [2, 2])
        darwin = next(r for r in rows if 'Dale Stewart' in r['members'][0]['path'])
        self.assertNotIn('Different book album/title clues may indicate mixed works', darwin['conflicts'])
        self.assertEqual(darwin['title_clue'], "Dale Stewart 04 - Darwin's Blade")
        self.run_automatic()
        control = self.jobs_for('Control')
        self.assertEqual([j['state'] for j in control], ['completed'], 'positive control: the same-album set converts')
        jobs = self.jobs_for('Dale Stewart')
        self.assertEqual([j['state'] for j in jobs], ['completed'], [r.get('reasons') for r in [self.service.automatic.candidate(darwin) or {}]])
        self.assertEqual([c['title'] for c in jobs[0]['output']['validation']['chapters']], ['Глава 1', 'Глава 2', 'Глава 3', 'Глава 4'])

    def test_a_gap_or_different_artists_never_convert(self):
        self.make('Gap', "Blade", numbers=(1, 3))
        self.make('Artists', "Edge", artists={1: 'Dan Simmons', 2: 'Stephen King'})
        rows = self.start()
        self.assertEqual(sorted(len(r['members']) for r in rows), [1, 1, 2], 'different artists: two books; the gap: one set')
        self.run_automatic()
        self.assertEqual(self.jobs_for('Gap'), [], 'a gap in the part numbers still holds the set')
        gap = next(r for r in rows if 'Gap' in r['members'][0]['path'])
        self.assertIn('Playback order uncertain', (self.service.automatic.candidate(gap) or {}).get('reasons') or [])


class ProtectedPartSetTests(unittest.TestCase):
    """C2 delta, the second cause the real run showed: once a part set was approved and queued (protected), a regroup rebuilt
    it by the per-file rule, which orders its parts differently, so it read "Recording grouping needs stronger evidence", its
    revision moved and the queued job stopped at "Source changed - review required". It keeps its stored group while its
    files are the same."""
    def rows(self, numbers=(1, 2), size=1000):
        return [catalog_row("Simmons/Dale Stewart 04 - Darwin's Blade %d.m4b" % n, {'album': "Dale Stewart 04 - Darwin's Blade %d" % n, 'artist': 'Dan Simmons',
                'title': "Dale Stewart 04 - Darwin's Blade %d" % n}, size=size if n == 2 else 1000) for n in numbers]

    def test_a_protected_part_set_keeps_its_group_while_its_files_are_the_same(self):
        rows = self.rows()
        scope, group = next(iter(groups.build(rows).items()))
        self.assertTrue(group['part_set'])
        again = groups.build(rows, protected={scope: group})
        self.assertIs(again[scope], group, 'the stored group, unchanged')
        changed = groups.build(self.rows(size=2000), protected={scope: group})
        self.assertTrue(changed[scope].get('source_partition_uncertain'), 'positive control: a changed file still asks')


class AlbumPartNegativeTests(unittest.TestCase):
    """C2 delta negatives at grouping: mixed audio profiles and "Metro 2033"/"Metro 2034" stay apart."""
    def test_mixed_audio_profiles_stay_apart(self):
        from test_split_books import AAC
        rows = [catalog_row("Simmons/Blade %d.m4b" % n, {'album': "Blade %d" % n, 'artist': 'Dan Simmons', 'title': "Blade %d" % n},
                            profile=AAC if n == 1 else ('aac', '22050', 2)) for n in (1, 2)]
        self.assertEqual(len(groups.build(rows)), 2)

    def test_metro_2033_and_2034_stay_apart(self):
        rows = [catalog_row("Glukhovsky/Metro %d.m4b" % n, {'album': "Metro %d" % n, 'artist': 'Dmitry Glukhovsky', 'title': "Metro %d" % n}) for n in (2033, 2034)]
        built = groups.build(rows)
        self.assertEqual(len(built), 2, list(built))
        self.assertFalse(any((g.get('part_set') or {}).get('album_parts') for g in built.values()))


class RetryCancelTests(test_approve_as_is.ApproveFixture):
    """D3 through the real server."""
    def test_a_malformed_job_id_is_a_bad_request(self):
        import web_server
        from test_http_0290 import RealServerTests
        self.start()
        self.service.start_retention = lambda admission: None
        self.service.start_published_check = lambda: None
        self.server = web_server.BrowserServer(('127.0.0.1', 0), self.inv, lambda inventory, cache, progress=None: self.service)
        self.assertNotEqual(self.server.server_port, 5210, "never Sergei's app port")
        threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .05}, daemon=True).start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close()))
        call = lambda body: RealServerTests.call(self, '/api/audiobook/retry-cancel', body)
        book = {'library': 'Audiobooks', 'id': str(uuid.uuid4()), 'revision': 1}
        status, answer = call(dict(book, job_id='not-a-job'))
        self.assertEqual(status, 400, answer)
        status, answer = call(dict(book, job_id=str(uuid.uuid4())))
        self.assertEqual(status, 409, 'positive control: a well-formed id for a book that is not there is a refusal')


def setUpModule():
    global _no_original_title_wait
    from original_title_fixture import no_wait
    _no_original_title_wait = no_wait()


def tearDownModule():
    _no_original_title_wait.stop()


if __name__ == '__main__':
    unittest.main()

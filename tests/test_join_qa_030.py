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
        self.assertIn('m4b-parts-v4', groups.GROUP_VERSION)


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

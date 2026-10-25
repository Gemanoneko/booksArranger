"""Book list speed (Sergei 2026-10-24, ruling 18: "fix it next"). Measured with the 200-book method, the page waited for
Inventory.group_lock twice, behind every automatic approval that holds it for seconds (cover extraction, the track
review, the job): in Inventory.candidates(), which held it for the whole read even when the stored groups are current,
and in its own converted-set computation once the status poll's set was 5 s old. Private fixtures; no network."""
import threading, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import test_approve_as_is
import test_quiet_status
from merge_service import MergeService
from scanner import Inventory, connect
from scan_wait import finish_scan
from test_approve_as_is import tone


class ConvertedSetTests(test_quiet_status.Base):
    def service(self):
        s = MergeService.__new__(MergeService)
        s.inventory = SimpleNamespace(database=str(self.db), worker=None)
        # A run is going: nothing is quiet, so only the age of the status poll's set decides.
        s.jobs = SimpleNamespace(_thread=SimpleNamespace(is_alive=lambda: True), _check_progress=None, _resuming=False)
        s.cleanup = SimpleNamespace(thread=None, current=None); s._post_current = None; s.draining = False
        s.progress_books = Mock(return_value={'converted_ids': {'fresh'}})
        return s

    def test_the_list_uses_the_status_polls_set_instead_of_computing_its_own(self):
        s = self.service()
        s._converted_cache = (time.monotonic() - 12, {'polled'}, None)
        self.assertEqual(s.converted_ids(), {'polled'}, 'a 12 s old set from the status poll is used as is')
        s.progress_books.assert_not_called()
        s._converted_cache = (time.monotonic() - 31, {'polled'}, None)
        self.assertEqual(s.converted_ids(), {'fresh'}, 'positive control: a set no status poll refreshed for 30 s is computed again')
        s.progress_books.reset_mock(); s.__dict__.pop('_converted_cache')
        self.assertEqual(s.converted_ids(), {'fresh'}, 'no set yet: computed'); s.progress_books.assert_called_once()

    def test_the_list_uses_the_status_polls_cleanup_statuses_instead_of_one_read_per_book(self):
        # Profiled on the 79-book catalog: once the poll's statuses were 5 s old the page read every shown job's cleanup
        # status itself, about 3 s of a 6.3 s page with nothing else running.
        s = self.service(); s.cleanup = SimpleNamespace(thread=None, current=None, status=Mock(return_value={'state': 'fresh'}))
        s._cleanup_kept = (time.monotonic() - 12, None, {'j': {'state': 'polled'}})
        self.assertEqual(s.cleanup_statuses(['j']), {'j': {'state': 'polled'}}); s.cleanup.status.assert_not_called()
        s._cleanup_kept = (time.monotonic() - 31, None, {'j': {'state': 'polled'}})
        self.assertEqual(s.cleanup_statuses(['j']), {'j': {'state': 'fresh'}}, 'positive control: 30 s without a status poll')


class CandidatesTests(test_approve_as_is.ApproveFixture):
    def test_a_page_of_current_groups_never_waits_for_an_approval_holding_the_group_lock(self):
        tone(self.audio / 'Unsorted' / 'Ясно' / 'Ясно.mp3', self.cover, album='Ясно', artist='Иван Петров')
        roots = {'Audiobooks': str(self.audio), 'Podcasts': str(self.base / 'podcasts'), 'Ebooks': str(self.base / 'ebooks')}
        inventory = Inventory(self.base / 'catalog.sqlite3', roots, output_root=str(self.sorted))
        inventory.launch('Audiobooks'); finish_scan(inventory)
        self.assertEqual(inventory.candidates('Audiobooks')['total'], 1)  # the first page stores the groups
        held, release = threading.Event(), threading.Event()

        def approval():
            with inventory.group_lock:
                held.set(); release.wait(30)
        holder = threading.Thread(target=approval, daemon=True); holder.start(); self.assertTrue(held.wait(5))
        self.addCleanup(release.set)
        pages = []
        reader = threading.Thread(target=lambda: pages.append(inventory.candidates('Audiobooks')), daemon=True); reader.start(); reader.join(5)
        self.assertFalse(reader.is_alive(), 'the page waited for group_lock')
        self.assertEqual(pages[0]['total'], 1)
        # Positive control: groups that must be rebuilt (the catalog changed) are written under the lock, as before.
        with connect(inventory.database) as db:
            db.execute('UPDATE book_catalog_revision SET revision=revision+1 WHERE id=1')
        rebuild = threading.Thread(target=lambda: pages.append(inventory.candidates('Audiobooks')), daemon=True); rebuild.start(); rebuild.join(1)
        self.assertTrue(rebuild.is_alive(), 'a rebuild waits for the lock')
        release.set(); rebuild.join(15); holder.join(5)
        self.assertFalse(rebuild.is_alive()); self.assertEqual(pages[1]['total'], 1)


if __name__ == '__main__':
    unittest.main()

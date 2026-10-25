"""Opened-handle fingerprint regressions; all byte writes target private fixtures."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import scanner
from scan_wait import finish_scan

SCRATCH = Path(__file__).resolve().parents[1] / 'scratch' / 'fresh-stat-fixtures'
SCRATCH.mkdir(parents=True, exist_ok=True)


class FreshStatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.path = self.base / 'audio' / 'book.mp3'
        self.path.parent.mkdir()
        self.path.write_bytes(b'private fixture')
        self.roots = {'Audiobooks': str(self.path.parent), 'Podcasts': str(self.base/'podcasts'), 'Ebooks': str(self.base/'ebooks')}
        self.calls = []
        def reader(path, kind, stop):
            self.calls.append(path)
            return {'title': 'Book', 'method': 'fixture'}
        self.inventory = scanner.Inventory(self.base/'catalog.sqlite3', self.roots, reader)
        self.root = self.roots['Audiobooks']
        with scanner.connect(self.inventory.database) as connection:
            connection.execute("INSERT INTO jobs(root,label,generation,state) VALUES(?,?,1,'scanning')",(self.root,'Audiobooks'))

    def read_file(self, generation=1):
        with scanner.connect(self.inventory.database) as connection:
            self.inventory._file(connection,'Audiobooks',self.root,generation,str(self.path))

    def row(self):
        return self.inventory.rows('Audiobooks')[0]

    def test_wrong_path_stat_cannot_disrupt_healthy_cache(self):
        self.read_file()
        self.inventory.save_review(self.root,str(self.path),{'title':'Reviewed'})
        other = self.base/'other.mp3'
        other.write_bytes(b'unrelated size')
        wrong = os.stat(other)
        with patch.object(scanner.os, 'stat', return_value=wrong):
            self.read_file(2)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.row()['review']['title'],'Reviewed')
        self.assertEqual(self.row()['seen'],2)
        self.assertEqual(self.inventory.status('Audiobooks')['reused'],1)

    def test_real_change_before_read_invalidates_review(self):
        self.read_file()
        self.inventory.save_review(self.root,str(self.path),{'title':'Reviewed'})
        self.path.write_bytes(b'new private content much larger')
        self.read_file(2)
        self.assertEqual(len(self.calls),2)
        self.assertIsNone(self.row()['review'])

    def test_actual_mutation_during_read_stays_blocked(self):
        def changing(*args):
            self.path.write_bytes(b'private changing fixture much larger')
            return {'title':'Unaccepted'}
        self.inventory.reader=changing
        with self.assertRaisesRegex(OSError,'File changed during read'):
            self.read_file()

    def test_identity_drift_blocks_equal_size_and_nanoseconds(self):
        actual=scanner.fresh_stat(self.path)
        replacement=SimpleNamespace(st_size=actual.st_size, st_mtime_ns=actual.st_mtime_ns,
                                    st_dev=actual.st_dev, st_ino=actual.st_ino+1)
        with patch.object(scanner,'fresh_stat',side_effect=[actual,replacement]):
            with self.assertRaisesRegex(OSError,'identity='):
                self.read_file()

    def test_cache_identity_drift_is_also_blocked(self):
        self.read_file()
        actual=scanner.fresh_stat(self.path)
        replacement=SimpleNamespace(st_size=actual.st_size, st_mtime_ns=actual.st_mtime_ns,
                                    st_dev=actual.st_dev+1, st_ino=actual.st_ino)
        with patch.object(scanner,'fresh_stat',side_effect=[actual,replacement]):
            with self.assertRaises(OSError):
                self.read_file(2)
        self.assertEqual(len(self.calls),1)

    def test_replaced_fixture_invalidates_review_through_scan_error_path(self):
        self.read_file()
        self.inventory.save_review(self.root,str(self.path),{'title':'Reviewed'})
        prior=scanner.fresh_stat(self.path)
        replacement=self.base/'replacement.mp3'
        replacement.write_bytes(self.path.read_bytes())
        os.utime(replacement,ns=(prior.st_atime_ns,prior.st_mtime_ns))
        with scanner.connect(self.inventory.database) as connection:
            connection.execute("UPDATE files SET error='Retry required' WHERE path=?",(str(self.path),))
        def replacing(*args):
            os.replace(replacement,self.path)
            return {'title':'Unaccepted replacement'}
        self.inventory.reader=replacing
        self.inventory.launch('Audiobooks')
        finish_scan(self.inventory)
        row=self.row()
        self.assertIsNone(row['review'])
        self.assertIn('identity=',row['error'])
        self.assertEqual(self.inventory.status('Audiobooks')['state'],'completed with errors')

    def test_exact_integer_nanoseconds_preserved(self):
        requested=1639041738263598500
        os.utime(self.path,ns=(requested,requested))
        actual=scanner.fresh_stat(self.path)
        self.read_file()
        self.assertIsInstance(actual.st_mtime_ns,int)
        self.assertEqual(self.row()['modified'],actual.st_mtime_ns)
        # NTFS may round to 100ns; never convert through floating-point seconds.
        self.assertEqual(actual.st_mtime_ns,requested)

    def test_error_entries_retry_metadata(self):
        self.read_file()
        with scanner.connect(self.inventory.database) as connection:
            connection.execute("UPDATE files SET error='Prior read failure' WHERE path=?",(str(self.path),))
        self.read_file(2)
        self.assertEqual(len(self.calls),2)
        self.assertEqual(self.row()['error'],'')


if __name__=='__main__':
    unittest.main()

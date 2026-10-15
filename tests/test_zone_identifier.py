"""Actual NTFS stream/handle fixtures; only private copied product scratch."""
import base64,contextlib,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import zone_identifier as zone
from native_io import BoundaryError,DirectoryBoundary,VerifiedFile
from scanner import connect

MARKER=b'[ZoneTransfer]\r\nZoneId=3\r\nHostUrl=https://example.invalid/book\r\n'

class ZoneIdentifierTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='zone-',dir=Path(__file__).resolve().parents[1]/'scratch');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'source-קнига.m4b';self.path.write_bytes(b'original audio bytes'*1024)
        self.sha=hashlib.sha256(self.path.read_bytes()).hexdigest();self.receipts=[]
        with VerifiedFile(self.path) as held:self.identity=held.facts()['identity']
    def marker(self,raw=MARKER):
        with open(str(self.path)+':Zone.Identifier','wb') as stream:stream.write(raw)
    def validate(self,held):
        self.assertEqual(held.facts()['identity'],self.identity);self.assertEqual(held.sha256(),self.sha)
        with self.assertRaises(PermissionError):self.path.write_bytes(b'changed')
    def remove(self,persist=None):
        with DirectoryBoundary(self.root,self.path.parent):return zone.remove_marker(self.path,self.validate,persist or self.receipts.append)
    def test_exact_known_marker_removed_audio_and_native_identity_unchanged(self):
        self.marker();self.assertTrue(self.remove());self.assertEqual(self.path.read_bytes(),b'original audio bytes'*1024)
        self.assertEqual(zone.streams(self.path),[('::$DATA',self.path.stat().st_size)])
        self.assertEqual(base64.b64decode(self.receipts[0]['marker_bytes_base64']),MARKER)
        with VerifiedFile(self.path) as held:self.assertEqual(held.facts()['identity'],self.identity)
        self.assertFalse(self.remove());self.assertEqual(len(self.receipts),1)
    def test_unknown_stream_preserves_both_marker_and_unknown_bytes(self):
        self.marker()
        with open(str(self.path)+':Unresolved','wb') as stream:stream.write(b'unique evidence')
        with self.assertRaisesRegex(BoundaryError,'Additional'):self.remove()
        with open(str(self.path)+':Unresolved','rb') as stream:self.assertEqual(stream.read(),b'unique evidence')
        with open(str(self.path)+':Zone.Identifier','rb') as stream:self.assertEqual(stream.read(),MARKER)
        self.assertEqual(self.receipts,[])
    def test_malformed_or_oversized_marker_preserved(self):
        for raw in (b'not a download marker',b'[ZoneTransfer]\nZoneId=3\nUnknown=secret',b'x'*8193):
            with self.subTest(size=len(raw)):
                self.marker(raw)
                with self.assertRaises(BoundaryError):self.remove()
                with open(str(self.path)+':Zone.Identifier','rb') as stream:self.assertEqual(stream.read(),raw)
        self.assertEqual(self.receipts,[])
    def test_marker_intent_failure_never_disposes_stream(self):
        self.marker()
        def failed(receipt):raise OSError('durable intent failed')
        with self.assertRaisesRegex(OSError,'intent'):self.remove(failed)
        with open(str(self.path)+':Zone.Identifier','rb') as stream:self.assertEqual(stream.read(),MARKER)
    def test_unknown_arrival_after_intent_preserves_every_stream(self):
        self.marker()
        def arriving(receipt):
            self.receipts.append(receipt)
            with open(str(self.path)+':Unresolved','wb') as stream:stream.write(b'late evidence')
        with self.assertRaisesRegex(BoundaryError,'changed'):self.remove(arriving)
        with open(str(self.path)+':Unresolved','rb') as stream:self.assertEqual(stream.read(),b'late evidence')
        with open(str(self.path)+':Zone.Identifier','rb') as stream:self.assertEqual(stream.read(),MARKER)
    def test_changed_original_refuses_marker_removal(self):
        self.marker()
        # CREATE_ALWAYS may discard named streams. Mutate the same existing
        # base file in place, retaining the marker whose validation we test.
        with open(self.path,'r+b') as stream:stream.write(b'changed original');stream.flush()
        self.assertIn(zone.MARKER,{name for name,size in zone.streams(self.path)})
        with self.assertRaises(AssertionError):self.remove()
        with open(str(self.path)+':Zone.Identifier','rb') as stream:self.assertEqual(stream.read(),MARKER)
    def test_hardlinked_base_and_marker_preserved(self):
        self.marker();os.link(self.path,self.root/'alias.m4b')
        with self.assertRaisesRegex(BoundaryError,'unique'):self.remove()
        with open(str(self.path)+':Zone.Identifier','rb') as stream:self.assertEqual(stream.read(),MARKER)
        self.assertEqual(self.receipts,[])

class ZoneCleanupIntegrationTests(unittest.TestCase):
    def setUp(self):
        import test_storage_cleanup as fixtures
        self.fixture=fixtures.RetentionTests('test_success_discards_staging_preserves_originals_and_output');self.fixture.setUp()
    def tearDown(self):self.fixture.tearDown()
    def reviewed_marker(self,source):
        # The marker belongs to a download made BEFORE approval. Adding it to
        # this already frozen fixture can itself change the base timestamp.
        with VerifiedFile(source) as held:before=held.facts()
        with open(str(source)+':Zone.Identifier','wb') as stream:stream.write(MARKER)
        with VerifiedFile(source) as held:after=held.facts()
        print('ZONE_FIXTURE_FACTS '+json.dumps({'before':before,'after_marker_creation':after}),flush=True)
        os.utime(source,ns=(source.stat().st_atime_ns,before['modified']))
        with VerifiedFile(source) as held:self.assertEqual(held.facts(),before)
    def test_original_cleanup_keeps_durable_marker_intent_and_exact_recovery(self):
        f=self.fixture;source=Path(f.sources[0]['path'])
        self.reviewed_marker(source)
        f.retire()
        with connect(f.db) as db:
            row=db.execute('SELECT receipt FROM source_zone_marker_intents WHERE cleanup_id=?',(f.cleanup_id,)).fetchone()
        self.assertEqual(base64.b64decode(json.loads(row[0])['marker_bytes_base64']),MARKER)
        backup=f.source.root/f.cleanup_id/'00000.mp3'
        self.assertEqual(hashlib.sha256(backup.read_bytes()).hexdigest(),f.sources[0]['sha256']);self.assertFalse(source.exists())
        from recovery_retention import RecoveryRetention
        retention=RecoveryRetention(f.storage)
        self.assertEqual(retention.status(f.job_id)['state'],'retained')
        self.assertEqual(retention.status(f.job_id)['count'],2)
    def test_unknown_original_stream_blocks_cleanup_without_discard(self):
        f=self.fixture;source=Path(f.sources[0]['path'])
        with open(str(source)+':Unresolved','wb') as stream:stream.write(b'preserve me')
        with self.assertRaisesRegex(BoundaryError,'Additional'):f.retire()
        self.assertTrue(source.is_file())
        with open(str(source)+':Unresolved','rb') as stream:self.assertEqual(stream.read(),b'preserve me')
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),f.sources[0]['sha256'])
    def test_normal_cleanup_resume_rechecks_previously_stream_held_book(self):
        f=self.fixture;source=Path(f.sources[0]['path'])
        self.reviewed_marker(source)
        cleanup=f.source.enroll(f.full,{})
        f.source._set(cleanup,'needs_attention','Additional filesystem streams require review; original retained')
        f.source._work(follow_audio=False)
        self.assertEqual(f.source.status(f.job_id)['state'],'completed');self.assertFalse(source.exists())
    def test_late_pre_disposition_stream_check_preserves_unknown(self):
        f=self.fixture;source=Path(f.sources[0]['path']);import source_cleanup
        original=source_cleanup.single_stream;arrived=[]
        def check(path):
            if str(path)==str(source) and len(arrived)==1:
                with open(str(source)+':Unresolved','wb') as stream:stream.write(b'late evidence')
                arrived.append(2)
            elif str(path)==str(source):arrived.append(1)
            return original(path)
        with patch.object(source_cleanup,'single_stream',side_effect=check):
            with self.assertRaises((BoundaryError,PermissionError)):f.retire()
        self.assertTrue(source.exists());self.assertTrue((f.source.root/f.cleanup_id/'00000.mp3').is_file())

if __name__=='__main__':unittest.main()

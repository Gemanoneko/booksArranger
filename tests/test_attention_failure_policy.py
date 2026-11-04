"""Private deterministic regression contracts; no media/process execution."""
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audio_jobs import AudioJobs, _failure_details
from audio_pipeline import _copy_presentation, copied_audio_evidence, PacketTimingHash, ValidationError


class FailureClassificationTests(unittest.TestCase):
    def sqlite_error(self, code):
        error = sqlite3.OperationalError('database is locked')
        error.sqlite_errorcode = code
        error.sqlite_errorname = 'TEST_TYPED_CODE'
        return error

    def test_typed_busy_locked_and_extended_codes(self):
        for code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED,
                     sqlite3.SQLITE_BUSY | (2 << 8), sqlite3.SQLITE_LOCKED | (1 << 8)):
            with self.subTest(code=code):
                record = _failure_details(self.sqlite_error(code), 'checking sources', 10)
                self.assertIs(record['retryable'], True)
                self.assertEqual(record['sqlite_errorcode'], code)
                self.assertEqual((record['stage'], record['at']), ('checking sources', 10))

    def test_unknown_and_permanent_codes_stay_held(self):
        for code in (None, True, '5', -1, -251, -250, sqlite3.SQLITE_IOERR, sqlite3.SQLITE_CORRUPT,
                     sqlite3.SQLITE_NOTADB, sqlite3.SQLITE_FULL, sqlite3.SQLITE_READONLY):
            with self.subTest(code=code):
                self.assertIs(_failure_details(self.sqlite_error(code), 'checking')['retryable'], False)
        self.assertIs(_failure_details(sqlite3.OperationalError('database is locked'), 'checking')['retryable'], False)
        self.assertIs(_failure_details(RuntimeError('database is locked'), 'checking')['retryable'], False)
        self.assertIs(_failure_details(InterruptedError('paused'), 'checking')['retryable'], False)

    def test_existing_io_policy_remains(self):
        self.assertIs(_failure_details(OSError('temporary I/O'), 'creating')['retryable'], True)
        self.assertIs(_failure_details(TimeoutError('temporary timeout'), 'creating')['retryable'], True)


class RetryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.queue = AudioJobs.__new__(AudioJobs)
        self.queue.database = str(Path(self.temp.name) / 'private.sqlite3')
        self.queue._lock = threading.RLock()
        self.queue._closed = False
        self.queue._thread = None
        self.queue.revision_guard = MagicMock(return_value=True)
        with self.queue._db() as db:
            db.execute('CREATE TABLE audio_jobs(job_id TEXT PRIMARY KEY,manifest TEXT,state TEXT,stage TEXT,attempt_id TEXT,journal TEXT,output TEXT,reason TEXT,updated TEXT,created TEXT DEFAULT 0)')
        self.journal = {'attempt_id':'prior-attempt', 'history':[{'stage':'checking sources'}],
                        'failure':{'retryable':True,'at':10,'sqlite_errorcode':5}}
        self.save()

    def save(self, output=None):
        with self.queue._db() as db:
            db.execute('INSERT OR REPLACE INTO audio_jobs(job_id,manifest,state,stage,attempt_id,journal,output,reason,updated) VALUES(?,?,?,?,?,?,?,?,?)',
                       ('private-job',json.dumps({'job_id':'private-job'}),'needs attention','checking sources',
                        'prior-attempt',json.dumps(self.journal),output,'saved failure','prior-time'))

    def row(self):
        return self.queue._rows()[0]

    def test_legacy_false_and_publication_are_never_reinterpreted(self):
        self.journal['failure']['retryable'] = False
        self.save()
        self.assertIs(self.queue.retry_failed('private-job', 4000)['retryable'], False)
        self.assertEqual(self.row()['state'], 'needs attention')
        self.queue.revision_guard.assert_not_called()
        self.journal['failure']['retryable'] = True
        self.journal['publication_intent'] = {'immutable':'publication'}
        self.save()
        self.assertIs(self.queue.retry_failed('private-job', 4000)['retryable'], False)
        self.journal.pop('publication_intent')
        self.save(output='{"immutable":"output"}')
        self.assertIs(self.queue.retry_failed('private-job', 4000)['retryable'], False)

    def test_due_time_worker_and_revision_gates_preserve_attempt(self):
        old = self.row()
        self.assertIs(self.queue.retry_failed('private-job', 20)['requeued'], False)
        self.queue._thread = MagicMock()
        self.queue._thread.is_alive.return_value = True
        self.assertIs(self.queue.retry_failed('private-job', 4000)['requeued'], False)
        self.queue._thread = None
        self.queue.revision_guard.return_value = False
        self.assertIs(self.queue.retry_failed('private-job', 4000)['retryable'], False)
        self.assertEqual(self.row(), old)

    def test_retry_archives_exact_prior_journal_and_does_not_duplicate(self):
        old = self.row()
        self.assertIs(self.queue.retry_failed('private-job', 4000)['requeued'], True)
        row = self.row()
        self.assertEqual((row['attempt_id'], row['journal']), (old['attempt_id'], old['journal']))
        self.assertEqual(row['state'], 'pending')
        with self.queue._db() as db:
            history = [tuple(row) for row in db.execute('SELECT job_id,attempt_id,record FROM audio_failure_history')]
        self.assertEqual(history, [('private-job','prior-attempt',old['journal'])])
        self.assertIs(self.queue.retry_failed('private-job', 5000)['retryable'], False)

    def test_history_failure_does_not_requeue(self):
        old = self.row()
        original = self.queue._db
        failed = MagicMock()
        failed.__enter__.side_effect = sqlite3.OperationalError('history write unavailable')
        with patch.object(self.queue, '_db', side_effect=[original(), failed]):
            with self.assertRaises(sqlite3.OperationalError):
                self.queue.retry_failed('private-job', 4000)
        self.assertEqual(self.row(), old)


class RationalPresentationTests(unittest.TestCase):
    def stream(self, **changes):
        return dict({'sample_rate':'44100','time_base':'1/22050','start_pts':0,'duration_ts':22050}, **changes)

    def movie(self, **changes):
        return dict({'start_time':'0.000000','duration':'1.000000'}, **changes)

    def test_he_aac_and_equivalent_positive_rational_clocks(self):
        expected = {'audio_start_sample':0,'audio_end_sample':44100,
                    'movie_start_sample':0,'movie_end_sample':44100}
        self.assertEqual(_copy_presentation(self.stream(),self.movie()), expected)
        self.assertEqual(_copy_presentation(self.stream(time_base='2/44100'),self.movie()), expected)
        self.assertEqual(_copy_presentation(self.stream(time_base='1/44100',duration_ts=44100),self.movie()), expected)

    def test_observed_he_aac_bounds_are_exact(self):
        result = _copy_presentation(self.stream(duration_ts=547903288),
                                    self.movie(duration='24848.221678'))
        self.assertEqual(result['audio_end_sample'], 1095806576)

    def test_malformed_or_fractional_ticks_stay_held(self):
        for changes in ({'time_base':'1/0'},{'time_base':'0/44100'},{'time_base':'-1/44100'},
                        {'time_base':'x/y'},{'time_base':None},{'time_base':'1/44101','duration_ts':1},
                        {'duration_ts':0},{'duration_ts':-1},{'duration_ts':1.5},
                        {'duration_ts':True},{'sample_rate':False},{'sample_rate':'NaN'}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValidationError):
                    _copy_presentation(self.stream(**changes),self.movie())
        for movie in ({},{'start_time':'0','duration':'NaN'},
                      {'start_time':'0','duration':'inf'},{'start_time':'0','duration':'-1'}):
            with self.subTest(movie=movie):
                with self.assertRaises(ValidationError):_copy_presentation(self.stream(),movie)

    def test_offsets_and_duration_drift_still_require_preservation(self):
        for stream,movie in ((self.stream(start_pts=1),self.movie()),
                             (self.stream(),self.movie(start_time='0.000001')),
                             (self.stream(),self.movie(duration='1.01'))):
            with self.assertRaisesRegex(ValidationError, 'preservation plan'):
                _copy_presentation(stream,movie)

    def test_packet_timing_and_trim_differences_remain_distinct(self):
        def proof(raw):
            result = PacketTimingHash()
            result.feed(raw)
            return result.result()
        base = b'pts=0|dts=0|duration=1024|skip_samples=0|discard_padding=0\n'
        for changed in (b'pts=0|dts=-1|duration=1024\n',
                        b'pts=0|dts=0|duration=1023\n',
                        b'pts=0|dts=0|duration=1024|skip_samples=1\n',
                        b'pts=0|dts=0|duration=1024|discard_padding=1\n'):
            self.assertNotEqual(proof(base),proof(changed))

    def test_copy_evidence_retains_raw_decoder_clock(self):
        stream = self.stream(codec_name='aac',profile='HE-AAC',channels=2,
                             channel_layout='stereo',extradata_hash='SHA256:private')
        def fake_run(argv, stage, stop, timeout, **kwargs):
            if kwargs.get('telemetry') is not None:
                kwargs['telemetry'].feed(b'pts=0|dts=0|duration=1024\n')
                return b''
            return json.dumps({'streams':[stream],'format':self.movie()}).encode()
        with patch('audio_pipeline.run_owned',side_effect=fake_run),patch('audio_pipeline.shutil.which',return_value='private-ffprobe'):
            evidence = copied_audio_evidence(Path('private.m4b'),Path('.'),threading.Event(),1)
        self.assertEqual(evidence['decoder_configuration']['time_base'], '1/22050')
        self.assertEqual(evidence['decoder_configuration']['profile'], 'HE-AAC')
        self.assertEqual(evidence['relative_packet_timing']['packet_count'],1)


class SourceRemedyTests(unittest.TestCase):
    def test_real_worker_persists_twelfth_of_57_source_and_exposes_bound_remedy(self):
        import copy,uuid
        from audio_pipeline import SourceDecodeError
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            sources=[{'path':str(base/(str(i).zfill(2)+'.mp3')),'sha256':'a'*64,'fingerprint':{'size':1,'modified':1}} for i in range(1,58)]
            manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'sources':sources,'metadata':{'title':'Whole book'},'destination':str(base/'whole.m4b'),'profile':'fixture','evidence':{},'cover':{}}
            frozen=copy.deepcopy(manifest)
            def runner(actual,stop,checkpoint):
                checkpoint('checking sources',{})
                cause=ValidationError('Controlled native Header missing');cause.tag_repair_checked=True
                raise SourceDecodeError(actual['sources'][11]['path'],11,len(actual['sources']),cause)
            queue=AudioJobs(base/'catalog.sqlite3',runner,lambda value:True,lambda record:False)
            try:
                queue.enqueue(manifest);queue.resume();queue._thread.join(5);self.assertFalse(queue._thread.is_alive())
                row=queue._rows('SELECT * FROM audio_jobs WHERE job_id=?',(manifest['job_id'],))[0]
                self.assertEqual(json.loads(row['manifest']),frozen);self.assertIsNone(row['output']);self.assertEqual(row['state'],'needs attention')
                journal=json.loads(row['journal']);failure=journal['failure'];self.assertEqual(failure['stage'],'checking sources');self.assertNotIn('publication_intent',journal)
                self.assertEqual(failure['source_diagnostic']['source_index'],11);self.assertEqual(failure['source_diagnostic']['source_count'],57);self.assertTrue(failure['tag_repair_checked'])
                summary=queue.attention_summary(job_ids=[manifest['job_id']],retry=False)[manifest['job_id']]
                self.assertEqual(summary['remedy']['path'],sources[11]['path']);self.assertEqual(summary['media_failure']['filename'],'12.mp3')
                self.assertEqual(summary['media_failure']['code'],'source_decode_failed');self.assertNotIn('retry',summary)
            finally:queue.close()

    def test_typed_multisource_decode_is_bound_to_exact_frozen_member(self):
        import copy
        from audio_jobs import _failure_details,source_remedy,media_failure,tag_repair_retry
        from audio_pipeline import SourceDecodeError,ValidationError
        sources=[{'path':'Z:/private/'+str(i).zfill(2)+'.mp3','sha256':'a'*64} for i in range(1,58)]
        manifest={'sources':sources};cause=ValidationError('Header missing');cause.tag_repair_checked=True
        error=SourceDecodeError(sources[11]['path'],11,57,cause);failure=_failure_details(error,'checking sources')
        self.assertTrue(failure['tag_repair_checked']);self.assertEqual(failure['source_diagnostic'],error.to_dict())
        row={'reason':str(error),'state':'needs attention','output':None,'manifest_hash':__import__('hashlib').sha256(json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()};journal={'failure':failure}
        remedy=source_remedy(row,journal,manifest);self.assertEqual((remedy['path'],remedy['source_index'],remedy['source_count']),(sources[11]['path'],11,57))
        media=media_failure(row,journal,manifest,'other',remedy);self.assertEqual((media['code'],media['filename']),('source_decode_failed','12.mp3'))
        for patch in ({'source_index':True},{'source_index':57},{'source_count':56},{'source_path':sources[0]['path']},{'schema':'untrusted'},{'detail':None}):
            changed=copy.deepcopy(journal);changed['failure']['source_diagnostic'].update(patch)
            self.assertIsNone(source_remedy(row,changed,manifest))
        for stage in ('checking output','publishing','creating'):
            changed=copy.deepcopy(journal);changed['failure']['stage']=stage;self.assertIsNone(source_remedy(row,changed,manifest))
        self.assertIsNone(source_remedy(row,dict(journal,publication_intent={}),manifest))
        self.assertIsNone(source_remedy(dict(row,output='{}'),journal,manifest))
        self.assertIsNone(source_remedy(dict(row,manifest_hash='0'*64),journal,manifest))
        raw=dict(row,manifest=__import__('json').dumps(manifest),journal=__import__('json').dumps(journal));self.assertFalse(tag_repair_retry(raw))

    def test_invalid_m4b_is_distinct_from_unsupported_chapter_image(self):
        from audio_jobs import media_failure
        manifest={'sources':[{'path':'Z:/private/source.m4b'}]};journal={'failure':{'exception_class':'ValidationError','stage':'checking sources'}}
        invalid=media_failure({'reason':'Full audio decode failed: corrupt input packet'},journal,manifest,'unsupported')
        feature=media_failure({'reason':'M4B preservation requires review: Unsupported chapter image sample entry'},journal,manifest,'unsupported')
        self.assertEqual(invalid['code'],'invalid_m4b_source');self.assertEqual(feature['code'],'m4b_feature_unsupported')
        self.assertIsNone(media_failure({'reason':'Unknown failure'},journal,manifest,'other'))
        self.assertIsNone(media_failure({'reason':'M4B preservation requires review: Unsupported chapter image sample entry'},journal,manifest,'checking'))

    def test_exact_single_source_decode_failure_exposes_retained_path(self):
        from audio_jobs import source_remedy
        row={'reason':'Full audio decode failed: Header missing'}
        journal={'failure':{'exception_class':'ValidationError','stage':'checking sources'}}
        manifest={'sources':[{'path':'Z:/Audio/Железная.mp3','sha256':'a'*64}]}
        self.assertEqual(source_remedy(row,journal,manifest),{'kind':'replace_source','cause':'source_decode_failed','path':'Z:/Audio/Железная.mp3','sha256':'a'*64,'original_retained':True})
        for changed in ({'sources':manifest['sources']*2},{'sources':[{'path':'Z:/Audio/book.m4b'}]}):self.assertIsNone(source_remedy(row,journal,changed))
        self.assertIsNone(source_remedy(row,{'failure':{'exception_class':'ValidationError','stage':'checking output'}},manifest))
        self.assertIsNone(source_remedy({'reason':'Other decode failure'},journal,manifest))


if __name__ == '__main__':
    unittest.main()

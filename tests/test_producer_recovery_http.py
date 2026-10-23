"""Actual handler boundary; mocked service, no sockets/catalog or recovery claims."""
import copy
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock,patch
import test_merge_http as fixture

AREA=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'producer-http'


class ProducerRecoveryHTTP(unittest.TestCase):
    handler=fixture.MergeHTTPTests.handler
    call=fixture.MergeHTTPTests.call

    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True)
        def retained(*args,**kwargs):
            kwargs['dir']=AREA
            return SimpleNamespace(name=tempfile.mkdtemp(*args,**kwargs),cleanup=lambda:None)
        with patch.object(fixture.tempfile,'TemporaryDirectory',side_effect=retained):fixture.MergeHTTPTests.setUp(self)
        self.route='/api/audiobook/prepare-recovery';self.job=str(uuid.uuid4())
        self.capability={'schema':'books-producer-recovery-capability-v1','state':'waiting_restart','cause':'restart_unverified','can_prepare':False,'can_retry':False,'checkpoint_id':str(uuid.uuid4()),'reason':'Restart verification needed','retained_files':True}
        self.answer={'job_id':self.job,'producer_recovery':self.capability,'queued':False,'outputs_changed':False}
        self.merge.prepare_producer_recovery=Mock(return_value=copy.deepcopy(self.answer))

    def test_exact_job_only_token_origin_and_shutdown_admission(self):
        body={'job_id':self.job}
        self.assertEqual(self.call(self.route,body,token=False)[0],403)
        h=self.handler(self.route,body);h.headers['Origin']='https://foreign.invalid';h.do_POST();self.assertEqual(h.result[0],403)
        for bad in ({},{'job_id':'../escape'},dict(body,actor='user'),dict(body,origin_fact=True),dict(body,evidence='provider assertion'),dict(body,library='Audiobooks')):
            self.assertEqual(self.call(self.route,bad)[0],400)
        self.merge.prepare_producer_recovery.assert_not_called()
        self.server.closing=True;self.assertEqual(self.call(self.route,body)[0],409)

    def test_success_forwards_authoritative_checkpoint_without_queue_or_restart(self):
        body={'job_id':self.job}
        for _ in range(2):
            status,answer,_=self.call(self.route,body);self.assertEqual(status,200);self.assertEqual(answer,self.answer)
        self.assertEqual(self.merge.prepare_producer_recovery.call_count,2)
        self.merge.prepare_producer_recovery.assert_called_with(self.job)
        self.jobs.resume.assert_not_called();self.merge.create.assert_not_called();self.merge.queue.assert_not_called()
        self.assertEqual(self.server.merge_admissions,0)

    def test_backend_unsupported_or_save_failure_never_reports_prepared(self):
        self.merge.prepare_producer_recovery.side_effect=ValueError('Historical origin is not proved; all files are retained')
        self.assertEqual(self.call(self.route,{'job_id':self.job})[0],400)
        self.merge.prepare_producer_recovery.side_effect=OSError('Private simulated save failure')
        status,answer,_=self.call(self.route,{'job_id':self.job});self.assertEqual(status,500);self.assertNotIn('producer_recovery',answer)


class ConfirmConvertHTTP(unittest.TestCase):
    """0.21.1 Confirm and convert: exact shape, the statements forwarded as sent, Retry-style typed refusals."""
    handler=fixture.MergeHTTPTests.handler
    call=fixture.MergeHTTPTests.call
    setUp=ProducerRecoveryHTTP.setUp
    def test_shape_forwarding_and_refusals(self):
        from audio_jobs import RetryRefused
        route='/api/audiobook/confirm-convert';statements=['The interrupted conversion ran on this PC.','Since then, Windows and these files were not moved, copied, cloned or restored from a backup.']
        body={'library':'Audiobooks','id':fixture.ID,'revision':3,'job_id':self.job,'statements':statements}
        self.merge.confirm_origin_and_convert=Mock(return_value={'job_id':self.job,'accepted':True,'queued_next':True,'origin_recorded':True})
        self.assertEqual(self.call(route,body,token=False)[0],403)
        for bad in ({k:v for k,v in body.items() if k!='statements'},dict(body,statements=statements[:1]),dict(body,statements='both'),dict(body,statements=[1,2]),dict(body,actor='user')):
            self.assertEqual(self.call(route,bad)[0],400)
        self.merge.confirm_origin_and_convert.assert_not_called()
        status,answer,_=self.call(route,body);self.assertEqual((status,answer['queued_next']),(202,True))
        self.merge.confirm_origin_and_convert.assert_called_once_with('Audiobooks',fixture.ID,3,self.job,statements)
        self.merge.confirm_origin_and_convert.side_effect=RetryRefused('This book changed. Review its details and try again.','book_changed')
        status,answer,_=self.call(route,body);self.assertEqual((status,answer['cause']),(409,'book_changed'))
        self.server.scan_active=lambda:True;status,answer,_=self.call(route,body);self.assertEqual((status,answer['error']),(409,'Scanning is running. Convert when it stops.'))


if __name__=='__main__':unittest.main()

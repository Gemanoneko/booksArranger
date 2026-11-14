import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from storage_admission_progress import Admission, report, _active


class AdmissionProgressTests(unittest.TestCase):
    def test_real_progress_and_heartbeat_are_distinct(self):
        clock=[0.0];events=[]
        with Admission(events.append,clock=lambda:clock[0]) as admission:
            clock[0]=16;report('retained',1,8134)
            self.assertEqual(events[-1]['done'],1)
            clock[0]=21;report()
            self.assertEqual(events[-1]['progress_age_ms'],5000)
            clock[0]=22;report(byte_count=4096)
            self.assertEqual(events[-1]['progress_age_ms'],0)
            clock[0]=23;report('database',0)
            self.assertIsNone(events[-1]['total'])
            admission.complete()
        self.assertEqual(events[-1]['state'],'complete')

    def test_deadline_refuses_before_success(self):
        clock=[0.0];events=[]
        with self.assertRaises(TimeoutError):
            with Admission(events.append,clock=lambda:clock[0]) as admission:
                clock[0]=597
                admission.complete()
        self.assertEqual(events[-1]['state'],'failed')
        self.assertIsNone(_active.get())

    def test_eof_at_checkpoint_and_final_barrier_refuses(self):
        for checkpoint in (lambda a:report(),lambda a:a.complete()):
            closed=[False];events=[]
            with self.assertRaisesRegex(RuntimeError,'app closed'):
                with Admission(events.append,cancelled=lambda:closed[0]) as admission:
                    closed[0]=True;checkpoint(admission)
            self.assertEqual(events[-1]['state'],'failed')

    def test_eof_during_complete_event_cannot_admit(self):
        closed=[False];events=[]
        def emit(value):
            events.append(value)
            if value['state']=='complete':closed[0]=True
        with self.assertRaises(RuntimeError):
            with Admission(emit,cancelled=lambda:closed[0]) as admission:admission.complete()
        self.assertEqual(events[-1]['state'],'failed')

    def test_failed_telemetry_resets_context(self):
        def fail(value):raise OSError('closed telemetry')
        with self.assertRaises(OSError):
            with Admission(fail):pass
        self.assertIsNone(_active.get())
        with self.assertRaises(OSError):
            with Admission(lambda value:None) as admission:
                admission.emit=fail
                raise ValueError('refused')
        self.assertIsNone(_active.get())

    def test_pipe_eof_before_control_attachment_is_not_lost(self):
        from desktop_backend import ShellLifetime
        read,write=os.pipe();calls=[]
        lifetime=ShellLifetime()
        try:
            with patch('desktop_backend.sys.stdin',SimpleNamespace(fileno=lambda:read)):
                lifetime.start()
            os.close(write);write=None
            self.assertTrue(lifetime.lost.wait(2))
            with self.assertRaises(RuntimeError):lifetime.check()
            lifetime.attach(SimpleNamespace(stop_now=lambda reason:calls.append(reason)))
            self.assertIn('shell_pipe_closed',calls)
        finally:
            os.close(read)
            if write is not None:os.close(write)


if __name__=='__main__':unittest.main()

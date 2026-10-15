import ctypes
import os
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock,patch
from desktop_backend import _process_running
from native_io import OwnedProcessJob

class OwnerLifetimeTests(unittest.TestCase):
    def test_actual_live_process_is_not_retired(self):
        self.assertTrue(_process_running(os.getpid()))

    def test_actual_ended_owned_child_does_not_need_image_query(self):
        child=subprocess.Popen([sys.executable,'-I','-B','-c','pass'],creationflags=0x08000000|4)
        child._books_suspended=True
        try:
            with OwnedProcessJob(child):
                child.wait(timeout=10)
                self.assertEqual(child.returncode,0)
                self.assertFalse(_process_running(child.pid))
        finally:
            if child.poll() is None:child.terminate();child.wait(timeout=5)

    def test_unknown_wait_refuses_and_closes_handle(self):
        kernel=types.SimpleNamespace(OpenProcess=Mock(return_value=123),WaitForSingleObject=Mock(return_value=0xffffffff),CloseHandle=Mock(return_value=True))
        with patch.object(ctypes,'WinDLL',return_value=kernel):
            with self.assertRaisesRegex(RuntimeError,'ownership record preserved'):_process_running(42)
        kernel.CloseHandle.assert_called_once_with(123)

    def test_unknown_open_error_is_not_proof_of_exit(self):
        kernel=types.SimpleNamespace(OpenProcess=Mock(return_value=0),WaitForSingleObject=Mock(),CloseHandle=Mock())
        with patch.object(ctypes,'WinDLL',return_value=kernel),patch.object(ctypes,'get_last_error',return_value=5):
            self.assertTrue(_process_running(42))
        kernel.WaitForSingleObject.assert_not_called()

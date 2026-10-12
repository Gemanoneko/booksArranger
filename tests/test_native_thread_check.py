import concurrent.futures, ctypes, hashlib, json, os, sys, tempfile, threading, types, unittest, uuid, wave
from pathlib import Path
from unittest.mock import patch, Mock
import native_io
from audio_pipeline import run_owned, snapshot_manifest, create_private, digest, fingerprint, ValidationError
from audio_jobs import AudioJobs

AREA=Path(__file__).resolve().parents[2]

class SnapshotGate:
    def __init__(self, function, barrier):
        object.__setattr__(self,'function',function);object.__setattr__(self,'barrier',barrier)
    def __getattr__(self,name):return getattr(self.function,name)
    def __setattr__(self,name,value):setattr(self.function,name,value)
    def __call__(self,*args):
        self.barrier.wait(10)
        return self.function(*args)

def concurrent_enumeration(module):
    # Both callers bind their ABI before entering the actual native enumeration.
    # A native DWORD PID cannot equal -1: no foreign thread can be opened.
    barrier=threading.Barrier(2);kernel=module.kernel
    proxy=types.SimpleNamespace(**{name:getattr(kernel,name) for name in
        ('Thread32First','Thread32Next','OpenThread','ResumeThread','GetProcessIdOfThread','CloseHandle')})
    proxy.CreateToolhelp32Snapshot=SnapshotGate(kernel.CreateToolhelp32Snapshot,barrier)
    proxy.OpenThread=Mock(side_effect=AssertionError('Foreign thread open refused'))
    proxy.ResumeThread=Mock(side_effect=AssertionError('Foreign thread resume refused'))
    def attempt():
        try:module.resume_owned_primary(-1)
        except Exception as error:return error
        raise AssertionError('Impossible PID unexpectedly resumed')
    with patch.object(module,'kernel',proxy),concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(attempt) for _ in range(2)]
        errors=[task.result(15) for task in tasks]
    proxy.OpenThread.assert_not_called();proxy.ResumeThread.assert_not_called()
    return errors

class NativeThreadChecks(unittest.TestCase):
    def test_baseline_race_reproduces_exact_native_ctypes_error(self):
        path=AREA/'baseline_native_io.py';module=types.ModuleType('baseline_native_thread')
        module.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
        errors=concurrent_enumeration(module)
        matches=[e for e in errors if isinstance(e,ctypes.ArgumentError)]
        self.assertEqual(len(matches),1,[str(e) for e in errors])
        self.assertIn('expected LP_ThreadEntry instance instead of pointer to ThreadEntry',str(matches[0]))

    def test_candidate_concurrent_actual_native_enumeration_keeps_abi_identity(self):
        errors=concurrent_enumeration(native_io)
        self.assertTrue(all(isinstance(e,native_io.BoundaryError) for e in errors),[str(e) for e in errors])
        self.assertTrue(all('exactly one suspended primary thread' in str(e) for e in errors))

    def test_windows_threadentry_layout_and_native_signatures(self):
        self.assertEqual(ctypes.sizeof(native_io.ThreadEntry),28)
        self.assertEqual([getattr(native_io.ThreadEntry,n).offset for n,_ in native_io.ThreadEntry._fields_],list(range(0,28,4)))
        for name in ('Thread32First','Thread32Next'):
            self.assertIs(getattr(native_io.kernel,name).argtypes[1]._type_,native_io.ThreadEntry)
            self.assertIs(getattr(native_io.kernel,name).restype,ctypes.wintypes.BOOL)

    def test_no_matching_owned_thread_refuses_without_resume(self):
        with patch.object(native_io.kernel,'ResumeThread') as resume, patch.object(native_io.kernel,'OpenThread') as opened:
            with self.assertRaises(native_io.BoundaryError):native_io.resume_owned_primary(-1)
            opened.assert_not_called();resume.assert_not_called()

    def test_two_owned_private_children_finish_and_drain(self):
        with tempfile.TemporaryDirectory(dir=AREA) as folder:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                tasks=[pool.submit(run_owned,[sys.executable,'-I','-B','-c','print("private-owned")'],Path(folder),threading.Event(),20) for _ in range(2)]
                self.assertEqual([t.result(25).strip() for t in tasks],[b'private-owned']*2)

    def test_private_audio_admission_source_check_advances_without_publication(self):
        with tempfile.TemporaryDirectory(dir=AREA) as folder:
            root=Path(folder);source=root/'source.wav';cover=root/'cover.png'
            with wave.open(str(source),'wb') as audio:
                audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(44100);audio.writeframes(b'\0\0'*4410)
            cover.write_bytes(b'private invalid cover deliberately stops before creation')
            before={p.name:digest(p) for p in (source,cover)}
            item={'path':str(source),**fingerprint(source),'sha256':digest(source),'metadata':{'tags':{}}}
            item['fingerprint']={'size':item['size'],'modified':item['modified']}
            manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,
                'root':str(root),'destination':str(root/'never-published.m4b'),'profile':'private prepublication fixture',
                'sources':[item],'cover':{'path':str(cover),'sha256':digest(cover)},'metadata':{},'evidence':{}}
            calls=[]
            def runner(m,stop,checkpoint):
                def progress(*args):checkpoint('checking sources',{})
                with patch('audio_pipeline.probe',wraps=__import__('audio_pipeline').probe) as probe:
                    try:return create_private(m,root/'stage',stop,progress)
                    finally:calls.extend(probe.call_args_list)
            queue=AudioJobs(root/'private.sqlite3',runner,lambda m:True,lambda r:False)
            queue.enqueue(manifest);queue._work();queue.close()
            row=queue._rows()[0];journal=json.loads(row['journal'])
            self.assertEqual(row['state'],'needs attention')
            self.assertIn('Select one usable JPEG or PNG cover',row['reason'])
            self.assertEqual(len(calls),1) # Real ffprobe and source PCM decode completed first.
            self.assertIsNone(row['output']);self.assertNotIn('publication_intent',journal)
            self.assertFalse(Path(manifest['destination']).exists())
            self.assertEqual({p.name:digest(p) for p in (source,cover)},before)

if __name__=='__main__':unittest.main()

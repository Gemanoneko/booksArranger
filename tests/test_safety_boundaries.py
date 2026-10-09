import ctypes,json,os,subprocess,sys,tempfile,threading,time,unittest,uuid
from pathlib import Path
from scanner import Inventory
from review_backend import CandidateReviewService
from native_io import BoundaryError,DirectoryBoundary,publish_no_replace,kernel
from audio_pipeline import run_owned,Paused,digest

AREA=Path(__file__).resolve().parents[1]/'scratch'/'safety-tests';AREA.mkdir(parents=True,exist_ok=True)

class Boundaries(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.base=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_cache_junction_is_rejected_before_write(self):
        target=self.base/'redirect';target.mkdir();link=self.base/'covers'
        result=subprocess.run(['cmd','/d','/c','mklink','/J',str(link),str(target)],capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8','replace'))
        try:
            inv=Inventory(self.base/'catalog.sqlite3',{'Audiobooks':str(self.base/'audio'),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')})
            with self.assertRaises(BoundaryError):CandidateReviewService(inv,link)
            self.assertFalse(list(target.iterdir()))
        finally:os.rmdir(link)

    def test_modified_destination_temp_cannot_be_published(self):
        source=self.base/'owned.partial';source.write_bytes(b'checked output')
        expected=digest(source);source.write_bytes(b'changed output')
        final=self.base/'Book.m4b'
        with DirectoryBoundary(self.base,self.base) as boundary:
            with self.assertRaises(BoundaryError):publish_no_replace(source,final,boundary,expected,len(b'checked output'))
        self.assertFalse(final.exists());self.assertTrue(source.exists())

    def test_directory_guard_rejects_ancestor_rename(self):
        owned=self.base/'owned';moved=self.base/'moved'
        with DirectoryBoundary(self.base,owned,create=True) as boundary:
            self.assertFalse(kernel.MoveFileExW(str(owned),str(moved),0))
            self.assertEqual(ctypes.get_last_error(),32)
            boundary.revalidate();self.assertTrue(owned.exists());self.assertFalse(moved.exists())

    def test_directory_guard_denies_reparse_write_handle(self):
        owned=self.base/'owned'
        with DirectoryBoundary(self.base,owned,create=True):
            handle=kernel.CreateFileW(str(owned),0x40000000,3,None,3,0x02000000|0x00200000,None)
            if handle!=ctypes.c_void_p(-1).value:
                kernel.CloseHandle(handle);self.fail('External reparse write handle was allowed')
            self.assertEqual(ctypes.get_last_error(),32)

    def test_handle_rename_is_exclusive_and_preserves_collision(self):
        source=self.base/'owned.partial';source.write_bytes(b'checked output');final=self.base/'Book.m4b';final.write_bytes(b'existing')
        with DirectoryBoundary(self.base,self.base) as boundary:
            with self.assertRaises(FileExistsError):publish_no_replace(source,final,boundary,digest(source),source.stat().st_size)
        self.assertEqual(final.read_bytes(),b'existing');self.assertEqual(source.read_bytes(),b'checked output')

    def test_suspended_job_cancels_its_early_descendant(self):
        script=self.base/'owned_child.py';pidfile=self.base/'descendant.pid'
        script.write_text('import subprocess,sys,time,os\nfrom pathlib import Path\nprint("Started",os.getpid(),flush=True)\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"])\nPath(sys.argv[1]).write_text(str(p.pid))\nprint("Descendant",p.pid,flush=True)\ntime.sleep(30)\n',encoding='utf-8')
        stop=threading.Event()
        def request_stop():
            deadline=time.monotonic()+20
            while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.01)
            stop.set()
        thread=threading.Thread(target=request_stop);thread.start()
        with self.assertRaises(Paused):run_owned([sys.executable,str(script),str(pidfile)],self.base,stop,25)
        thread.join(21);self.assertTrue(pidfile.exists())
        pid=int(pidfile.read_text());kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
        handle=kernel.OpenProcess(0x100000,False,pid)
        if handle:
            try:
                kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
                self.assertEqual(kernel.WaitForSingleObject(handle,0),0,'Owned descendant remained running')
            finally:kernel.CloseHandle(handle)

if __name__=='__main__':unittest.main()

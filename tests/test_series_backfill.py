"""v0.16.12 series backfill: the in-place tag rewrite and its proofs, the rename, a name collision, a failed move,
restarts at every step, and a catalog that still verifies afterwards. Real audiobook files made by ffmpeg
(movie atom last, as most published books are, and first); private catalog tables; no library, no network."""
import hashlib,json,os,shutil,sqlite3,subprocess,tempfile,threading,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
if not shutil.which('ffmpeg'):os.environ['PATH']=str(ROOT/'build-cache'/'runtime'/'ffmpeg')+os.pathsep+os.environ.get('PATH','')
import series_backfill
from series_backfill import SeriesBackfill,encoded
from quicktime_chapters import retag,media_unchanged,ChapterFormatError,_layout
from encoding_policy import AUTOMATIC_PROFILE
from merge_service import MergeService,file_identity
from metadata import propose
from scanner import connect

AREA=ROOT/'scratch'/'series-backfill-tests';AREA.mkdir(parents=True,exist_ok=True)
TITLE,AUTHOR='Призраки белых ночей','Обухова Лена'

def make_book(path,faststart=False):
    """A small published-style audiobook: AAC audio, one attached cover, two chapters, title/artist tags."""
    folder=path.parent;cover=folder/'cover.png';chapters=folder/'chapters.txt'
    subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-y','-f','lavfi','-i','color=c=red:s=32x32:d=1','-frames:v','1',str(cover)],check=True)
    chapters.write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=1000\ntitle=One\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=1000\nEND=2000\ntitle=Two\n',encoding='utf-8')
    subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-y','-f','lavfi','-i','sine=frequency=440:duration=2','-i',str(cover),'-f','ffmetadata','-i',str(chapters),
        '-map','0:a','-map','1:v','-map_chapters','2','-c:a','aac','-b:a','64k','-c:v','copy','-disposition:v:0','attached_pic',
        '-metadata','title='+TITLE,'-metadata','artist='+AUTHOR,'-metadata','album='+TITLE,'-metadata','album_artist='+AUTHOR,'-metadata','media_type=2',
        *(['-movflags','+faststart'] if faststart else []),'-f','mp4',str(path)],check=True)
    cover.unlink();chapters.unlink()

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class Library:
    """One published book in a private library and the catalog rows that describe it."""
    def __init__(self,base,faststart=False):
        self.base=base;self.root=base/'library';self.db=base/'catalog.sqlite3';self.stage_root=base/'merge-cache'/'audio-staging';self.stage_root.mkdir(parents=True)
        self.review={'title':TITLE,'canonical_author':AUTHOR,'author':AUTHOR,'original_language':'Russian','series':'','number':'','genre':'','topic':'','narrator':'','multi_author':False,'anthology':False}
        self.path=Path(propose('',str(self.root),'audiobook',{},self.review)['path']);self.path.parent.mkdir(parents=True)
        make_book(self.path,faststart)
        self.job_id=str(uuid.uuid4());self.candidate=str(uuid.uuid4())
        with connect(self.db) as db:
            db.executescript('''CREATE TABLE audio_jobs (job_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_hash TEXT NOT NULL, state TEXT NOT NULL, stage TEXT NOT NULL, attempt_id TEXT, journal TEXT NOT NULL, output TEXT, reason TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE owned_artifacts(path TEXT PRIMARY KEY,job_id TEXT,kind TEXT,sha256 TEXT,size INTEGER);
                CREATE TABLE verified_outputs(path TEXT NOT NULL,sha256 TEXT NOT NULL,job_id TEXT NOT NULL,identity TEXT NOT NULL,verified TEXT NOT NULL,PRIMARY KEY(path,sha256));
                CREATE TABLE storage_cleanup_jobs(job_id TEXT PRIMARY KEY,output_hash TEXT,state TEXT,reason TEXT,updated TEXT);
                CREATE TABLE book_groups(id TEXT PRIMARY KEY,revision INTEGER,review TEXT);
                CREATE TABLE candidate_context(id TEXT PRIMARY KEY,revision INTEGER,data TEXT);''')
            from native_io import DirectoryBoundary
            with DirectoryBoundary(self.root,self.path.parent) as boundary:ancestry=[list(i) for i in boundary.identities]
            size=self.path.stat().st_size;digest=sha(self.path)
            manifest={'job_id':self.job_id,'candidate_id':self.candidate,'candidate_revision':2,'root':str(self.root),'destination':str(self.path),'metadata':dict(self.review),'sources':[],'cover':{}}
            self.output={'job_id':self.job_id,'root':str(self.root),'final_path':str(self.path),'size':size,'sha256':digest,'parent_identity':ancestry,
                         'validation':{'profile':AUTOMATIC_PROFILE,'duration':2.0,'sha256':digest,'size':size,'tags':{'title':TITLE,'artist':AUTHOR}}}
            text,manifest_hash=encoded(manifest)
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',(self.job_id,text,manifest_hash,'completed','completed',None,'{}',json.dumps(self.output),'','2026-10-18T00:00:00','2026-10-18T00:00:00'))
            db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',(str(self.path),self.job_id,'output',digest,size))
            db.execute('INSERT INTO verified_outputs VALUES(?,?,?,?,?)',(os.path.normcase(str(self.path)),digest,self.job_id,json.dumps(file_identity(self.path)),'2026-10-18T00:00:00Z'))
            db.execute("INSERT INTO storage_cleanup_jobs VALUES(?,?,'completed','','')",(self.job_id,digest))
            db.execute('INSERT INTO book_groups VALUES(?,?,?)',(self.candidate,2,json.dumps(self.review,ensure_ascii=False)))
            db.execute('INSERT INTO candidate_context VALUES(?,?,?)',(self.candidate,2,json.dumps({'metadata_facts':{'series_state':'omitted_unknown'},'metadata_evidence':[]})))
        self.original=sha(self.path)
        self.target=Path(propose('',str(self.root),'audiobook',{},dict(self.review,series='Нормальное аномальное',number='10'))['path'])

    def merge(self):
        s=MergeService.__new__(MergeService)
        s.inventory=SimpleNamespace(database=str(self.db),worker=None,roots={'Audiobooks':str(self.root)})
        s.jobs=SimpleNamespace(_thread=None,status=lambda:{'jobs':[]});s.cleanup=SimpleNamespace(thread=None,current=None)
        s.stage_root=self.stage_root;s._validated_outputs={};s.invalidate_status=Mock()
        return s

    def backfill(self,merge=None,found=('Нормальное аномальное','10')):
        research=SimpleNamespace(_series_goodreads=lambda *a:{'provider':'goodreads','name':found[0],'number':found[1],'source_url':'https://www.goodreads.com/book/show/55108791'} if found else None,
                                 _series_fantlab=lambda *a:None)
        return SeriesBackfill(merge or self.merge(),research=research,stage=self.base/'proof-stage')

    def row(self):
        with connect(self.db) as db:return dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(self.job_id,)).fetchone())
    def state(self,backfill):entry=backfill.entry(self.job_id);return (entry['state'],entry['reason']) if entry else None
    def temps(self):return sorted(p.name for p in self.path.parent.iterdir() if p.name.startswith(series_backfill.TEMP_PREFIX))


class RewriteProofTests(unittest.TestCase):
    def test_both_layouts_keep_every_media_byte_and_only_the_series_tags_change(self):
        for faststart in (False,True):
            with self.subTest(faststart=faststart),tempfile.TemporaryDirectory(dir=AREA) as folder:
                folder=Path(folder);old=folder/'book.m4b';make_book(old,faststart);new=folder/'.retagged.m4b'
                kinds=[k for k,_,_ in _layout(old)[0]];self.assertEqual(kinds.index(b'moov')<kinds.index(b'mdat'),faststart)
                review=dict(title=TITLE,series='Серия',number='3')
                receipt=retag(old,new,threading.Event(),series_backfill.series_tags(review))
                self.assertEqual(receipt['input_sha256'],sha(old));self.assertEqual(receipt['media_moved'],faststart);self.assertGreater(receipt['metadata_growth'],0)
                if faststart:self.assertGreater(receipt['chunk_offsets'],0)
                media_unchanged(old,new,threading.Event())
                # Positive controls: one changed media byte, or one changed sample-table byte, fails the proof.
                top,index,_=_layout(new);mdat=next((at,length) for kind,at,length in top if kind==b'mdat')
                for offset in (mdat[0]+mdat[1]-5,):
                    damaged=folder/'.damaged.m4b';data=bytearray(new.read_bytes());data[offset]^=1;damaged.write_bytes(bytes(data))
                    with self.assertRaises(ChapterFormatError):media_unchanged(old,damaged,threading.Event())
                    damaged.unlink()
                data=bytearray(new.read_bytes());at=data.find(b'stsz');data[at+16]^=1;damaged=folder/'.damaged.m4b';damaged.write_bytes(bytes(data))
                with self.assertRaises(ChapterFormatError):media_unchanged(old,damaged,threading.Event())
                with self.assertRaises(FileExistsError):retag(old,new,threading.Event(),series_backfill.series_tags(review))
                self.assertEqual(sha(old),receipt['input_sha256'],'the published file is only read')

    def test_unsupported_layouts_are_refused(self):
        with tempfile.TemporaryDirectory(dir=AREA) as folder:
            folder=Path(folder);old=folder/'book.m4b';make_book(old)
            raw=old.read_bytes();moov=raw.find(b'moov')-4;size=int.from_bytes(raw[moov:moov+4],'big')
            twice=folder/'twice.m4b';twice.write_bytes(raw+raw[moov:moov+size])  # two movie atoms
            with self.assertRaises(ChapterFormatError):retag(twice,folder/'.x.m4b',threading.Event(),series_backfill.series_tags(dict(title=TITLE,series='S',number='1')))


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.lib=Library(Path(self.temp.name))

    def assert_unchanged(self,backfill):
        lib=self.lib
        self.assertEqual(sha(lib.path),lib.original,'the published file is untouched');self.assertFalse(lib.target.exists());self.assertEqual(lib.temps(),[])
        self.assertEqual(json.loads(lib.row()['output'])['final_path'],str(lib.path),'the catalog is unchanged')

    def test_series_written_renamed_recorded_and_still_verified(self):
        lib=self.lib;backfill=lib.backfill();backfill.run_pass()
        self.assertEqual(lib.state(backfill),('done',''))
        self.assertFalse(lib.path.exists(),'no copy is kept');self.assertTrue(lib.target.exists());self.assertEqual(lib.temps(),[])
        self.assertEqual(lib.target.name,'Нормальное аномальное - 10 - Призраки белых ночей - Обухова Лена.m4b')
        row=lib.row();output=json.loads(row['output']);manifest=json.loads(row['manifest'])
        self.assertEqual((output['final_path'],output['sha256'],output['size']),(str(lib.target),sha(lib.target),lib.target.stat().st_size))
        self.assertEqual(row['manifest_hash'],hashlib.sha256(row['manifest'].encode()).hexdigest(),'the frozen manifest and its hash agree')
        self.assertEqual((manifest['metadata']['series'],manifest['metadata']['number'],manifest['destination']),('Нормальное аномальное','10',str(lib.target)))
        self.assertEqual(manifest['destination'],propose('',manifest['root'],'audiobook',{},manifest['metadata'])['path'],'named as a newly converted book')
        # The catalog still verifies: the routine identity check and the full byte check both pass, without re-hashing loops.
        merge=lib.merge()
        self.assertTrue(merge._identity_current(output),'routine check: identity recorded for the new file')
        self.assertTrue(merge._output_valid(output),'full check: the recorded bytes')
        with connect(lib.db) as db:
            self.assertEqual([tuple(r) for r in db.execute("SELECT path,sha256,size FROM owned_artifacts WHERE kind='output'")],[(str(lib.target),output['sha256'],output['size'])])
            self.assertEqual(db.execute("SELECT count(*) FROM owned_artifacts WHERE kind='temporary'").fetchone()[0],0)
            review=json.loads(db.execute('SELECT review FROM book_groups').fetchone()[0]);context=json.loads(db.execute('SELECT data FROM candidate_context').fetchone()[0])
        self.assertEqual((review['series'],review['number']),('Нормальное аномальное','10'))
        self.assertEqual(context['metadata_facts']['series_state'],'verified');self.assertEqual(context['metadata_facts']['series_source']['provider'],'goodreads')
        self.assertEqual({e['field'] for e in context['metadata_evidence']},{'series','number'})
        merge.invalidate_status.assert_not_called()  # the backfill's own merge stub is a different object
        # A second pass changes nothing.
        backfill.run_pass();self.assertTrue(lib.target.exists());self.assertEqual(json.loads(lib.row()['output'])['sha256'],output['sha256'])

    def test_a_name_collision_leaves_the_book_as_it_is(self):
        lib=self.lib;lib.target.write_bytes(b'someone else');backfill=lib.backfill();backfill.run_pass()
        state,reason=lib.state(backfill);self.assertEqual(state,'held');self.assertIn('already exists',reason)
        self.assertEqual(lib.target.read_bytes(),b'someone else');self.assertEqual(sha(lib.path),lib.original);self.assertEqual(lib.temps(),[])
        self.assertEqual(json.loads(lib.row()['output'])['final_path'],str(lib.path))

    def test_a_failed_move_leaves_the_book_as_it_is(self):
        lib=self.lib;backfill=lib.backfill()
        with patch.object(series_backfill.os,'rename',side_effect=PermissionError(13,'Access is denied')):backfill.run_pass()
        state,reason=lib.state(backfill);self.assertEqual(state,'held');self.assertIn('could not be renamed',reason)
        self.assert_unchanged(backfill)

    def test_a_failed_proof_or_a_changed_file_leaves_the_book_as_it_is(self):
        lib=self.lib;backfill=lib.backfill()
        with patch.object(series_backfill.SeriesBackfill,'check_tags',side_effect=series_backfill.Held('Series tags did not read back: album')):backfill.run_pass()
        self.assertEqual(lib.state(backfill),('held','Series tags did not read back: album'));self.assert_unchanged(backfill)
        lib2=Library(Path(self.temp.name)/'second');data=bytearray(lib2.path.read_bytes());data[-1]^=1;lib2.path.write_bytes(bytes(data))  # not what was verified
        backfill=lib2.backfill();backfill.run_pass()
        state,reason=lib2.state(backfill);self.assertEqual(state,'held');self.assertIn('changed since it was verified',reason);self.assertEqual(lib2.temps(),[])

    def test_no_series_and_not_now(self):
        lib=self.lib
        backfill=lib.backfill(found=None);backfill.run_pass();self.assertEqual(lib.state(backfill)[0],'none');self.assert_unchanged(backfill)
        lib2=Library(Path(self.temp.name)/'second');merge=lib2.merge();merge.jobs._thread=SimpleNamespace(is_alive=lambda:True)
        backfill=lib2.backfill(merge);backfill.run_pass()
        self.assertIsNone(lib2.state(backfill),'file changes wait while a book converts; nothing is recorded');self.assertEqual(sha(lib2.path),lib2.original);self.assertEqual(lib2.temps(),[])
        merge.jobs._thread=None;backfill.run_pass();self.assertEqual(lib2.state(backfill)[0],'done','and run once the queue is idle')

    def test_restarts_at_every_step_finish_or_leave_it_unchanged(self):
        lib=self.lib
        # Stopped while writing: the unproven file goes, the book is tried again.
        backfill=lib.backfill()
        def stop_writing(*args,**kwargs):
            Path(args[1]).write_bytes(b'partial');raise InterruptedError('closing')
        with patch.object(series_backfill.SeriesBackfill,'_write',lambda self,job_id,manifest,output,old,temp,review,record:stop_writing(old,temp)):backfill.run_pass()
        self.assertEqual(lib.state(backfill)[0],'pending');self.assert_unchanged(backfill)
        # Stopped after the proof (the new file written and proven, not yet renamed): a new run finishes it.
        backfill=lib.backfill()
        with patch.object(series_backfill.SeriesBackfill,'resume',lambda self,job_id:None):backfill.run_pass()
        self.assertEqual(lib.state(backfill)[0],'written');self.assertEqual(len(lib.temps()),1);self.assertEqual(sha(lib.path),lib.original)
        restarted=lib.backfill();restarted.run_pass()
        self.assertEqual(lib.state(restarted)[0],'done');self.assertTrue(lib.target.exists());self.assertFalse(lib.path.exists());self.assertEqual(lib.temps(),[])

    def test_restart_after_the_rename_records_it_and_removes_the_former_file(self):
        lib=self.lib;backfill=lib.backfill()
        with patch.object(series_backfill.SeriesBackfill,'catalog',side_effect=sqlite3.OperationalError('database is locked')):backfill.run_pass()
        self.assertEqual(lib.state(backfill)[0],'renamed','a busy catalog waits: the book keeps its renamed state')
        self.assertTrue(lib.target.exists() and lib.path.exists());self.assertEqual(json.loads(lib.row()['output'])['final_path'],str(lib.path),'still the former record, still valid')
        self.assertTrue(lib.merge()._output_valid(json.loads(lib.row()['output'])))
        restarted=lib.backfill();restarted.run_pass()
        self.assertEqual(lib.state(restarted)[0],'done');self.assertFalse(lib.path.exists())
        self.assertTrue(lib.merge()._output_valid(json.loads(lib.row()['output'])))
        # A catalog refusal (the book changed meanwhile) puts the library back as it was: the new file goes.
        lib2=Library(Path(self.temp.name)/'second');backfill=lib2.backfill()
        with patch.object(series_backfill.SeriesBackfill,'catalog',side_effect=series_backfill.Held('The book changed meanwhile')):backfill.run_pass()
        state,reason=lib2.state(backfill);self.assertEqual(state,'held');self.assertIn('The book changed meanwhile',reason);self.assert_unchanged_lib(lib2)

    def assert_unchanged_lib(self,lib):
        self.assertEqual(sha(lib.path),lib.original);self.assertFalse(lib.target.exists());self.assertEqual(lib.temps(),[])

    def test_a_scan_never_catalogs_the_new_file_while_it_is_written(self):
        lib=self.lib;backfill=lib.backfill();seen=[]
        real=series_backfill.SeriesBackfill._write
        def watch(self,job_id,manifest,output,old,temp,review,record):
            with connect(lib.db) as db:seen.append(tuple(db.execute("SELECT kind FROM owned_artifacts WHERE path=?",(str(temp),)).fetchone()))
            return real(self,job_id,manifest,output,old,temp,review,record)
        with patch.object(series_backfill.SeriesBackfill,'_write',watch):backfill.run_pass()
        self.assertEqual(seen,[('temporary',)],'app-owned while it exists, so a library scan skips it')

    def test_progress_row_values(self):
        lib=self.lib;backfill=lib.backfill();seen=[]
        real=series_backfill.SeriesBackfill.apply
        def watch(self,job_id,found):seen.append(self.status());return real(self,job_id,found)
        with patch.object(series_backfill.SeriesBackfill,'apply',watch):backfill.run_pass()
        self.assertEqual(seen,[{'title':TITLE,'done':0,'total':1,'step':'updating'}]);self.assertIsNone(backfill.status())
        from web_server import activities
        rows=activities({'series_update':{'title':TITLE,'done':3,'total':38,'step':'updating'}},None,None,None,{},now_ms=1)
        self.assertEqual([(r['kind'],r['subject'],r['done'],r['total'],r['unit']) for r in rows],[('series',TITLE,3,38,'books')])

if __name__=='__main__':unittest.main()

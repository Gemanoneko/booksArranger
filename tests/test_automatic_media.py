"""Confident automatic approval through real private MP3/M4B verification and 24h recovery."""
import json,shutil,struct,subprocess,tempfile,threading,time,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from contextlib import contextmanager
from metadata import propose
from scanner import Inventory
from merge_service import MergeService
from public_research import PublicClient,PublicResearch
from test_automatic_processing import fixture_payload,AREA


def artwork():
    width,height=96,144
    raw=b''.join(b'\0'+bytes(v for x in range(width) for v in ((x*7+y)%256,(x+y*3)%256,(x*5+y*11)%256)) for y in range(height))
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')

class AutomaticMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.base=Path(self.temp.name);self.audio=self.base/'audio';self.audio.mkdir();self.cover=artwork();self.cover_path=self.base/'art.png';self.cover_path.write_bytes(self.cover)
        self.sources=[]
        for index in (1,2):
            source=self.audio/(str(index).zfill(2)+'.mp3')
            subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.4','-i',str(self.cover_path),'-map','0:a','-map','1:v','-c:a','libmp3lame','-b:a','128k','-ar','44100','-ac','1','-c:v','png','-id3v2_version','3','-metadata','album=A Book','-metadata','title=Chapter '+str(index),'-metadata','artist=John Writer','-metadata','track='+str(index)+'/2','-disposition:v','attached_pic',str(source)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.sources.append(source)
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots);self.inv.launch('Audiobooks');self.inv.worker.join(10);self.service=MergeService(self.inv,self.base/'cache')
        def fetch(url,*_):
            if '/search-works?' in url:return json.dumps([{'work_id':42,'name':'A Book','rusname':'Книга','all_autor_name':'John Writer','all_autor_rusname':'Джон Писатель'}]).encode()
            if '/work/42/extended' in url:return json.dumps(fixture_payload()).encode()
            if 'duckduckgo.com' in url:return b'<a class="result__a" href="https://ast.ru/book/example/">A Book</a>'
            if 'ast.ru' in url:return b'<p>John Writer. A Book</p>'
            if 'fantlab.ru/images/cover.jpg' in url:return self.cover
            raise AssertionError('Unexpected fixture public URL')
        self.client=PublicClient(self.inv.database,fetch=fetch)
    def tearDown(self):self.service.close();self.temp.cleanup()
    def result(self):
        row=self.service.reviews.page()['rows'][0];result=PublicResearch(self.client).lookup(row,str(self.audio));self.assertEqual(result['reasons'],[],result);return row,result
    def wait(self):
        limit=time.monotonic()+30
        while self.service.state()['state'] in ('Running','Pausing') or self.service.state().get('queued') or self.service.state().get('cleanup_active'):
            if time.monotonic()>limit:self.fail('Private automatic media job exceeded30s')
            time.sleep(.05)
    def test_confident_no_manual_form_to_verified_chapters_retained_recovery(self):
        row,result=self.result();fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['job_id'],job_id);self.assertEqual(job['state'],'completed',job)
        self.assertEqual(len(job['manifest']['chapters']),2);self.assertEqual(job['manifest']['cleanup_policy']['recovery_retention_hours'],24)
        self.assertTrue(all(not p.exists() for p in self.sources));self.assertTrue(Path(job['output']['final_path']).is_file())
        cleanup=self.service.cleanup.status(job_id);self.assertEqual(cleanup['state'],'completed');self.assertEqual(cleanup['recovery']['state'],'retained')
        status=self.service.state();self.assertEqual((status['converted_total'],status['approved_total']),(1,1));self.assertEqual(self.service.reviews.page(status='converted')['total'],1)
        self.assertTrue(self.service.reviews._context(fresh)['automatic_approval']);self.assertFalse(self.service.reviews._context(fresh).get('automatic_pending'))
        self.assertTrue(self.service._output_valid(job['output']))
        self.assertFalse(any(p.suffix in ('.stdout','.stderr') for p in self.service.reviews.cache.iterdir()))
    def test_independent_catalog_to_actual_verified_publication_and_ready_without_manual_step(self):
        from test_public_work_identity import FallbackFixture,cap_fantlab
        fixture=FallbackFixture(self.cover);client=PublicClient(self.inv.database,fetch=fixture.fetch);cap_fantlab(self.inv.database,time.time())
        row=self.service.reviews.page()['rows'][0];result=PublicResearch(client,leads=[]).lookup(row,str(self.audio))
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['work']['id'],'wikidata:Q100')
        fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),client);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        self.assertTrue(job['output']['validation']['passed']);self.assertTrue(Path(job['output']['final_path']).is_file())
        self.assertEqual(self.service.cleanup.status(job_id)['recovery']['state'],'retained')
        ready=self.service.reviews.page(status='converted');self.assertEqual(ready['total'],1);self.assertTrue(ready['rows'][0]['audiobook_ready'])
        self.assertTrue(self.service.inspect('Audiobooks','candidates',fresh['id'])['inspector']['audiobook_ready'])
        self.assertTrue(all(not source.exists() for source in self.sources));self.assertEqual(self.service.state()['converted_total'],1)

    def test_custom_source_cover_is_allowed_and_stop_preserves_sources(self):
        row,result=self.result();result['work']['cover_url']='https://evil.example/cover.jpg'
        stop=threading.Event();stop.set()
        with self.assertRaises(InterruptedError):self.service.approve_automatic(row,result,stop,self.client)
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertEqual(self.service.state()['approved_total'],0);self.assertTrue(all(p.exists() for p in self.sources))
        with patch.object(self.client,'read',wraps=self.client.read) as remote:
            fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
            remote.assert_not_called()
        self.assertEqual(result['metadata_facts']['cover']['kind'],'embedded')
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'completed')
        self.assertEqual(self.service.reviews.page(status='converted')['total'],1)

    def test_destination_collision_does_not_leave_approval_or_queue(self):
        row,result=self.result();proposal=propose(row['members'][0]['path'],str(self.audio),'audiobook',row['members'][0]['metadata'],result['review'])
        target=Path(proposal['path']);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'PREEXISTING DESTINATION PRESERVE')
        original_save=self.service.reviews.save
        def saved(*args,**kwargs):
            value=original_save(*args,**kwargs);self.assertFalse(value['metadata_approved']);self.assertEqual(self.service.state()['approved_total'],0);return value
        with patch.object(self.service.reviews,'save',saved),self.assertRaises(ValueError):self.service.approve_automatic(row,result,threading.Event(),self.client)
        self.assertEqual(self.service.state()['approved_total'],0);self.assertEqual(self.service.jobs.status()['jobs'],[])
        self.assertEqual(target.read_bytes(),b'PREEXISTING DESTINATION PRESERVE');self.assertTrue(all(p.exists() for p in self.sources))
        latest=self.service.reviews._row('Audiobooks',row['id']);context=self.service.reviews._context(latest);self.assertFalse(context.get('automatic_approval'))
        context['metadata_approved']=True;self.service.reviews._write(latest,context,bump=False) # Simulated pre-queue crash checkpoint.
        self.assertEqual(self.service.reviews.page(status='approved')['total'],0);self.assertEqual(self.service.reviews.page(status='ready')['total'],0);self.assertEqual(self.service.state()['approved_total'],0)
    def test_queue_insert_failure_rolls_back_final_approval(self):
        row,result=self.result();original=self.service.jobs._db
        class FailInsert:
            def __init__(self,db):self.db=db
            def execute(self,sql,*args):
                if sql.startswith('INSERT INTO audio_jobs'):raise __import__('sqlite3').OperationalError('Private fixture insertion failure')
                return self.db.execute(sql,*args)
        @contextmanager
        def fail_db():
            with original() as db:yield FailInsert(db)
        with patch.object(self.service.jobs,'_db',fail_db),self.assertRaises(__import__('sqlite3').OperationalError):self.service.approve_automatic(row,result,threading.Event(),self.client)
        self.assertEqual(self.service.state()['approved_total'],0);self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))
    def test_current_held_source_tags_revalidated_before_admission(self):
        row,result=self.result();from audio_pipeline import probe as original
        def changed(*args):
            raw=original(*args);raw['format']['tags']['track']='2/99';return raw
        with patch('audio_pipeline.probe',changed),self.assertRaisesRegex(ValueError,'embedded identity or order evidence changed'):self.service.approve_automatic(row,result,threading.Event(),self.client)
        self.assertEqual(self.service.state()['approved_total'],0);self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))
    def test_cover_stop_never_starts_second_track_extraction(self):
        row,result=self.result();stop=threading.Event();calls=[];from audio_pipeline import run_owned as original
        def inspected(args,*rest):
            value=original(args,*rest)
            if any(str(path) in args for path in self.sources):calls.append(args);stop.set()
            return value
        with patch('review_backend.run_owned',inspected),self.assertRaises(InterruptedError):self.service.reviews.covers('Audiobooks',row['id'],row['revision'],all_embedded=True,stop=stop)
        self.assertEqual(len(calls),1);self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))

    def test_last_track_interruption_is_not_swallowed(self):
        row,result=self.result();stop=threading.Event();from audio_pipeline import run_owned as original
        def last(args,*rest):
            if str(self.sources[-1]) in args:stop.set();raise InterruptedError('Private last-track pause')
            return original(args,*rest)
        with patch('review_backend.run_owned',last),self.assertRaises(InterruptedError):self.service.reviews.covers('Audiobooks',row['id'],row['revision'],all_embedded=True,stop=stop)
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))


    def test_unexpected_research_error_displays_nonactive_status_without_media_changes(self):
        from types import SimpleNamespace
        import hashlib
        before={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in self.sources}
        auto=self.service.automatic
        auto.research=SimpleNamespace(client=self.client,lookup=lambda *_:(_ for _ in ()).throw(RuntimeError('PRIVATE_UNEXPECTED_ERROR')))
        auto.start();auto.thread.join(5);self.assertFalse(auto.thread.is_alive())
        self.assertEqual(auto.status()['state'],'Needs attention');self.assertEqual(auto.status()['research']['researching'],0)
        row=self.service.reviews.page()['rows'][0]
        self.assertEqual(row['status'],'Needs attention — metadata research failed');self.assertFalse(row['metadata_approved']);self.assertFalse(row['creation']['can_create'])
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertEqual(self.service.state()['approved_total'],0)
        self.assertEqual(before,{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in self.sources})

if __name__=='__main__':unittest.main()

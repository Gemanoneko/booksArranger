"""Confident automatic approval through real private MP3/M4B verification and 24h recovery."""
import json,shutil,struct,subprocess,tempfile,threading,time,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from contextlib import contextmanager
from metadata import propose
from scanner import Inventory
from scan_wait import finish_scan
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
        # v0.22.0: these fixtures are identified from their tags alone (Sergei 2026-10-24, title + author is enough); the
        # cases build their results through the Internet identity path, so they pin local identity off.
        # Restored by tearDown too: test_working_lifecycle and test_standing_admission borrow setUp()/tearDown() without
        # the cleanups (tests/research_switch.py).
        import research_switch
        research_switch.pin(self,False)
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.base=Path(self.temp.name);self.audio=self.base/'audio';self.audio.mkdir();self.cover=artwork();self.cover_path=self.base/'art.png';self.cover_path.write_bytes(self.cover)
        self.sources=[]
        for index in (1,2):
            source=self.audio/(str(index).zfill(2)+'.mp3')
            subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.4','-i',str(self.cover_path),'-map','0:a','-map','1:v','-c:a','libmp3lame','-b:a','128k','-ar','44100','-ac','1','-c:v','png','-id3v2_version','3','-metadata','album=A Book','-metadata','title=Chapter '+str(index),'-metadata','artist=John Writer','-metadata','track='+str(index)+'/2','-disposition:v','attached_pic',str(source)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.sources.append(source)
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots);self.inv.launch('Audiobooks');finish_scan(self.inv);self.service=MergeService(self.inv,self.base/'cache')
        def fetch(url,*_):
            if '/search-works?' in url:return json.dumps([{'work_id':42,'name':'A Book','rusname':'Книга','all_autor_name':'John Writer','all_autor_rusname':'Джон Писатель'}]).encode()
            if '/work/42/extended' in url:return json.dumps(fixture_payload()).encode()
            if 'duckduckgo.com' in url:return b'<a class="result__a" href="https://ast.ru/book/example/">A Book</a>'
            if 'ast.ru' in url:return b'<p>John Writer. A Book</p>'
            if 'fantlab.ru/images/cover.jpg' in url:return self.cover
            raise AssertionError('Unexpected fixture public URL')
        self.client=PublicClient(self.inv.database,fetch=fetch)
    def tearDown(self):
        import research_switch
        research_switch.restore_pin(self);self.service.close();self.temp.cleanup()
    def result(self):
        row=self.service.reviews.page()['rows'][0];result=PublicResearch(self.client).lookup(row,str(self.audio));self.assertEqual(result['reasons'],[],result);return row,result
    def wait(self):
        # Ruling 72e (2026-10-29): 30 s became 90 s. The 0.24.0 entry checks ran suites 2.2-3 times slower than alone under
        # machine load and stopped this wait at 30 s (r1 and r3); it returns as soon as the job and cleanup end.
        limit=time.monotonic()+90
        while True:
            state=self.service.state()  # One snapshot; separate polls can cross cleanup enrollment.
            audio_worker=self.service.jobs._thread;cleanup_worker=self.service.cleanup.thread
            active=bool((audio_worker and audio_worker.is_alive()) or (cleanup_worker and cleanup_worker.is_alive()))
            if not (active or state['state'] in ('Running','Pausing') or state.get('queued') or state.get('cleanup_active')):return
            if time.monotonic()>limit:self.fail('Private automatic media job exceeded 90 s')
            time.sleep(.05)
    def test_confident_no_manual_form_to_verified_chapters_retained_recovery(self):
        row,result=self.result();fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['job_id'],job_id);self.assertEqual(job['state'],'completed',job)
        self.assertEqual(len(job['manifest']['chapters']),2);self.assertEqual(job['manifest']['cleanup_policy']['recovery_retention_hours'],24)
        self.assertTrue(all(not p.exists() for p in self.sources));self.assertTrue(Path(job['output']['final_path']).is_file())
        cleanup=self.service.cleanup.status(job_id);self.assertEqual(cleanup['state'],'completed');self.assertEqual(cleanup['recovery']['state'],'deleted','v0.16.8: deleted once the output is verified')
        status=self.service.state();self.assertEqual((status['converted_total'],status['approved_total']),(1,1));self.assertEqual(self.service.reviews.page(status='converted')['total'],1)
        self.assertTrue(self.service.reviews._context(fresh)['automatic_approval']);self.assertFalse(self.service.reviews._context(fresh).get('automatic_pending'))
        self.assertTrue(self.service._output_valid(job['output']))
        self.assertFalse(any(p.suffix in ('.stdout','.stderr') for p in self.service.reviews.cache.iterdir()))

    def test_identical_extra_source_uses_existing_publication_without_conversion(self):
        """Real automatic admission, real first codec run, native child cleanup."""
        import hashlib
        from scanner import connect
        originals=[source.read_bytes() for source in self.sources]
        row,result=self.result();_,parent_id=self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
        parent=next(job for job in self.service.jobs.status()['jobs'] if job['job_id']==parent_id)
        with connect(self.inv.database) as db:before=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent_id,)).fetchone())
        final=Path(parent['output']['final_path']);output_bytes=final.read_bytes()
        extra=self.audio/'Extra e\u0301';extra.mkdir()
        duplicate=[]
        for index,data in enumerate(originals,1):
            path=extra/(str(index).zfill(2)+'.mp3');path.write_bytes(data);duplicate.append(path)
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        rows=self.service.reviews.page()['rows'];current=next(row for row in rows if any(m['path']==str(duplicate[0]) for m in row['members']))
        research=PublicResearch(self.client).lookup(current,str(self.audio));self.assertEqual(research['reasons'],[])
        with patch.object(self.service,'_run_media',side_effect=AssertionError('Duplicate must never convert or publish')):
            _,child_id=self.service.approve_automatic(current,research,threading.Event(),self.client);self.wait()
        child=next(job for job in self.service.jobs.status()['jobs'] if job['job_id']==child_id)
        self.assertEqual(child['state'],'completed',child)
        self.assertEqual(child['manifest']['task_kind'],'duplicate_source_cleanup')
        self.assertEqual(child['output']['schema'],'books-duplicate-verification-v1')
        self.assertNotIn('publication_intent',json.loads(self.service.jobs._rows('SELECT journal FROM audio_jobs WHERE job_id=?',(child_id,))[0]['journal']))
        cleanup=self.service.cleanup.status(child_id);self.assertEqual(cleanup['state'],'completed',cleanup)
        self.assertEqual(cleanup['removed'],2);self.assertTrue(all(not source.exists() for source in duplicate))
        self.assertEqual(final.read_bytes(),output_bytes);self.assertEqual(hashlib.sha256(output_bytes).hexdigest(),parent['output']['sha256'])
        with connect(self.inv.database) as db:
            self.assertEqual(dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent_id,)).fetchone()),before)
            self.assertFalse(db.execute("SELECT 1 FROM owned_artifacts WHERE job_id=? AND kind='output'",(child_id,)).fetchone())
        self.assertEqual(self.service.state()['converted_total'],1)

    def test_single_m4b_unicode_duplicate_of_inplace_parent_has_its_own_recovery(self):
        import copy,hashlib
        from native_io import VerifiedFile,BoundaryError
        from scanner import connect
        for source in self.sources:source.unlink()
        original_folder=self.audio/'Original';original_folder.mkdir()
        old=original_folder/'Неисповедимыи\u0306 путь 2.m4b'
        subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=1.5','-i',str(self.cover_path),'-map','0:a','-map','1:v','-c:a','aac','-b:a','64k','-ar','44100','-ac','1','-c:v','png','-disposition:v','attached_pic','-metadata','title=A Book','-metadata','album=A Book','-metadata','artist=John Writer',str(old)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        original=old.read_bytes();old_identity=old.stat().st_ino
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        row=next(row for row in self.service.reviews.page()['rows'] if any(m['path']==str(old) for m in row['members']))
        result=PublicResearch(self.client).lookup(row,str(self.audio));self.assertEqual(result['reasons'],[])
        _,parent_id=self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
        parent=next(job for job in self.service.jobs.status()['jobs'] if job['job_id']==parent_id)
        self.assertEqual(parent['output']['validation'].get('publication_mode'),'in_place')
        self.assertFalse(old.exists());self.assertEqual(self.service.cleanup.status(parent_id)['state'],'completed')
        with connect(self.inv.database) as db:before=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent_id,)).fetchone())
        final=Path(parent['output']['final_path']);finished=final.read_bytes()
        extra=original_folder/'Неисповедимый путь 2.m4b';extra.write_bytes(original)
        self.assertNotEqual(extra.stat().st_ino,old_identity)
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        current=next(row for row in self.service.reviews.page()['rows'] if any(m['path']==str(extra) for m in row['members']))
        research=PublicResearch(self.client).lookup(current,str(self.audio));self.assertEqual(research['reasons'],[])
        with patch.object(self.service,'_run_media',side_effect=AssertionError('No second producer')),patch.object(self.service.jobs,'after_completed',None):
            _,child_id=self.service.approve_automatic(current,research,threading.Event(),self.client);self.wait()
        child=next(job for job in self.service.jobs.status()['jobs'] if job['job_id']==child_id);self.assertEqual(child['state'],'completed',child)
        cleanup_id=self.service.enroll_cleanup(child_id)['cleanup_id']
        # Known changed output refuses before any extra-source disposition.
        final.write_bytes(b'changed finished output')
        with self.assertRaisesRegex(BoundaryError,'changed or unavailable'):self.service.cleanup.run(cleanup_id)
        self.assertEqual(extra.read_bytes(),original)
        final.write_bytes(finished)
        # Same path/size/time but changed source bytes also refuse.
        stat=extra.stat();extra.write_bytes(b'x'*len(original));__import__('os').utime(extra,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        with self.assertRaisesRegex(BoundaryError,'Original bytes differ'):self.service.cleanup.run(cleanup_id)
        self.assertTrue(extra.exists());extra.write_bytes(original);__import__('os').utime(extra,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        # Cancel keeps the source and its verified child recovery; Resume uses it.
        self.service.cleanup.stop.set();self.service.cleanup.run(cleanup_id);self.service.cleanup.stop.clear()
        self.assertTrue(extra.exists());self.assertEqual(self.service.cleanup.status(child_id)['removed'],0)
        with connect(self.inv.database) as db:
            member=dict(db.execute('SELECT * FROM cleanup_members WHERE cleanup_id=?',(cleanup_id,)).fetchone())
            self.assertEqual(member['state'],'backup_verified');self.assertTrue(member['backup_facts'])
            intent=json.loads(db.execute('SELECT intent FROM source_cleanup WHERE id=?',(cleanup_id,)).fetchone()[0])
            self.assertEqual(intent['cleanup_mode'],'duplicate_backup_removal')
        self.assertEqual(Path(member['backup']).read_bytes(),original)
        self.service.cleanup.run(cleanup_id);self.assertFalse(extra.exists())
        self.assertEqual(self.service.cleanup.status(child_id)['removed'],1)
        self.assertEqual(final.read_bytes(),finished)
        self.service.cleanup.restore(cleanup_id);self.assertEqual(extra.read_bytes(),original)
        self.assertEqual(self.service.cleanup.status(child_id)['state'],'needs_attention')
        self.assertEqual(final.read_bytes(),finished)
        with connect(self.inv.database) as db:self.assertEqual(dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent_id,)).fetchone()),before)
        self.assertTrue(self.service._output_valid(parent['output']))
        self.assertEqual(self.service.state()['converted_total'],1)

    def test_normal_start_readmits_old_png_chapter_refusal_with_current_proof(self):
        import hashlib,m4b_preservation
        from scanner import connect
        from test_m4b_preservation import unpack,relocate,png_image,add_chapter_graph
        from audio_pipeline import run_owned
        for source in self.sources:source.unlink()
        full=self.base/'png-full.m4b';stop=threading.Event()
        run_owned([shutil.which('ffmpeg'),'-v','error','-xerror','-nostdin','-n','-f','lavfi','-i','sine=frequency=997:sample_rate=44100:duration=0.5','-ac','2','-c:a','aac','-b:a','64000','-movflags','+faststart','-metadata','title=A Book','-metadata','album=A Book','-metadata','artist=John Writer',str(full)],self.base,stop,30)
        top=unpack(full.read_bytes());gap=sum(b.size for kind,b in top.items() if kind not in (b'ftyp',b'moov',b'mdat'))
        base=top[b'ftyp'].raw+relocate(top[b'moov'].raw,-gap)+top[b'mdat'].raw
        folder=self.audio/'PNG';folder.mkdir();source=folder/'book.m4b'
        source.write_bytes(add_chapter_graph(base,image_kind=b'png ',image_samples=(png_image(),png_image())).replace(b'chapter',b'\0\5First',1))
        before=source.read_bytes()
        # This normal Start owns one PNG book; the MP3 setup catalog must not
        # leave unrelated missing-file candidates waiting for metadata.
        self.service.close();roots=dict(self.inv.roots);fetch=self.client.fetch
        self.inv=Inventory(self.base/'png-catalog.sqlite3',roots);self.inv.launch('Audiobooks');finish_scan(self.inv)
        self.service=MergeService(self.inv,self.base/'png-cache');self.client=PublicClient(self.inv.database,fetch=fetch)
        row=next(row for row in self.service.reviews.page()['rows'] if any(m['path']==str(source) for m in row['members']))
        research=PublicResearch(self.client).lookup(row,str(self.audio));self.assertEqual(research['reasons'],[])
        real=m4b_preservation.sample_description
        def old_image_rule(payload,handler):
            if handler==b'vide':raise m4b_preservation.Refused('Unsupported chapter image sample entry')
            return real(payload,handler)
        with patch.object(m4b_preservation,'sample_description',side_effect=old_image_rule):
            _,parent_id=self.service.approve_automatic(row,research,stop,self.client);self.wait()
        with connect(self.inv.database) as db:parent=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent_id,)).fetchone())
        self.assertEqual(parent['state'],'needs attention');self.assertEqual(parent['reason'],'M4B preservation requires review: Unsupported chapter image sample entry')
        self.assertIsNone(parent['output']);self.assertEqual(source.read_bytes(),before)
        self.service.automatic.research=PublicResearch(self.client)
        self.service.automatic.start();self.service.automatic.thread.join(90);self.assertFalse(self.service.automatic.thread.is_alive(),'Private normal Start did not finish')
        self.wait();jobs=self.service.jobs.status()['jobs'];children=[job for job in jobs if (job['manifest'].get('m4b_repair') or {}).get('parent_job_id')==parent_id]
        self.assertEqual(len(children),1,jobs);child=children[0];self.assertEqual(child['state'],'completed',child)
        self.assertTrue(child['output']['validation']['passed']);self.assertTrue(Path(child['output']['final_path']).exists())
        with connect(self.inv.database) as db:self.assertEqual(dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(parent_id,)).fetchone()),parent)
        image_tracks=[track for track in child['manifest']['m4b_repair']['source_profile']['tracks'] if track['handler']=='vide']
        self.assertEqual([track['codec'] for track in image_tracks],['png '])
    def test_independent_catalog_to_actual_verified_publication_and_ready_without_manual_step(self):
        from test_public_work_identity import FallbackFixture,cap_fantlab
        fixture=FallbackFixture(self.cover);client=PublicClient(self.inv.database,fetch=fixture.fetch);cap_fantlab(self.inv.database,time.time())
        row=self.service.reviews.page()['rows'][0];result=PublicResearch(client,leads=[]).lookup(row,str(self.audio))
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['work']['id'],'wikidata:Q100')
        fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),client);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        self.assertTrue(job['output']['validation']['passed']);self.assertTrue(Path(job['output']['final_path']).is_file())
        self.assertEqual(self.service.cleanup.status(job_id)['recovery']['state'],'deleted')  # v0.16.8: no 24 h retention
        ready=self.service.reviews.page(status='converted');self.assertEqual(ready['total'],1);self.assertTrue(ready['rows'][0]['audiobook_ready'])
        self.assertTrue(self.service.inspect('Audiobooks','candidates',fresh['id'])['inspector']['audiobook_ready'])
        self.assertTrue(all(not source.exists() for source in self.sources));self.assertEqual(self.service.state()['converted_total'],1)

    def test_approval_and_conversion_read_no_converted_set(self):
        # Live 2026-10-24 and Senua 0.21.2 F31: every enrich inside an automatic approval, and each of the converter's
        # revision guards (build_manifest -> enrich), recomputed the catalog's converted set (progress_books: every job,
        # cleanup and publication record, 10-25 s on the live catalog) under group_lock, which the status poll and the
        # book list wait on. 0.21.1 read it 7 times per approval, 0.21.2 once, and the converter 4 times per book; nothing
        # in either uses the audiobook_ready flag it feeds. Counted per thread: state() passes its own inputs and is not
        # an enrich read.
        row,result=self.result();calls=[];original=self.service.progress_books;approver=threading.current_thread()
        def counted(*args,**kwargs):
            if not args and not kwargs:calls.append('approval' if threading.current_thread() is approver else threading.current_thread().name)
            return original(*args,**kwargs)
        with patch.object(self.service,'progress_books',side_effect=counted):
            fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),self.client)
            self.assertFalse('audiobook_ready' in fresh,'the approval leaves the flag unset')
            self.assertFalse(getattr(self.service.reviews.page_local,'ready_skip',False),'the scope ends with the approval')
            self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual((job['job_id'],job['state']),(job_id,'completed'),job)
        self.assertEqual(calls.count('approval'),0,'no converted-set read in the approval')
        self.assertEqual(calls.count('BooksArrangerAudioJobs'),0,'no converted-set read in the conversion (its revision guards)')
        self.assertEqual(calls,[],'nothing else read it during the approval and conversion either')
        # Outside an approval each enrich still reads the current set, and the page and inspector still show Ready.
        with patch.object(self.service,'progress_books',side_effect=counted):
            first=self.service.reviews.enrich(self.service.reviews._row('Audiobooks',fresh['id']))
            second=self.service.reviews.enrich(self.service.reviews._row('Audiobooks',fresh['id']))
        self.assertEqual(calls,['approval','approval'],'one read per enrich outside an approval (this thread)')
        self.assertTrue(first['audiobook_ready'] and second['audiobook_ready'])
        self.assertTrue(self.service.reviews.page(status='converted')['rows'][0]['audiobook_ready'])
        self.assertTrue(self.service.inspect('Audiobooks','candidates',fresh['id'])['inspector']['audiobook_ready'])
        # build_manifest skips the read on any thread; a nested scope keeps the outer setting.
        calls.clear()
        with patch.object(self.service,'progress_books',side_effect=counted):
            unready=self.service.reviews.enrich(self.service.reviews._row('Audiobooks',fresh['id']),ready=False)
            with self.service.reviews.without_ready():
                with self.service.reviews.without_ready():pass
                self.assertTrue(self.service.reviews.page_local.ready_skip,'a nested scope keeps the outer setting')
                self.assertFalse('audiobook_ready' in self.service.reviews.enrich(self.service.reviews._row('Audiobooks',fresh['id'])))
        self.assertFalse('audiobook_ready' in unready);self.assertEqual(calls,[])
        self.assertFalse(self.service.reviews.page_local.ready_skip)

    def test_custom_source_cover_is_allowed_and_stop_preserves_sources(self):
        row,result=self.result();result['work']['cover_url']='https://evil.example/cover.jpg'
        stop=threading.Event();stop.set()
        with self.assertRaises(InterruptedError):self.service.approve_automatic(row,result,stop,self.client)
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertEqual(self.service.state()['approved_total'],0);self.assertTrue(all(p.exists() for p in self.sources))
        with patch.object(self.client,'read',wraps=self.client.read) as remote:
            fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
            remote.assert_not_called()
        job=next(item for item in self.service.jobs.status()['jobs'] if item['job_id']==job_id)
        self.assertEqual(job['manifest']['metadata_facts']['cover']['kind'],'embedded')
        self.assertEqual(job['state'],'completed')
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
            def __getattr__(self,name):return getattr(self.db,name)
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


# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

if __name__=='__main__':unittest.main()

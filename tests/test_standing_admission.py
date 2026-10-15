"""Standing-rule admission uses only private audio/catalog/queue fixtures."""
import json,shutil,subprocess,threading,time,unittest,uuid
from pathlib import Path
from unittest.mock import Mock,patch
import test_automatic_media as fixtures
from collection_identity import parse_contents,bind_collection
from test_collection_identity import PAGE,TITLE,WORKS
from standing_metadata import build_policy
from audio_jobs import AudioJobs
from scanner import connect
from public_research import PublicClient,PublicResearch

class StandingAdmissionTests(unittest.TestCase):
    def setUp(self):
        # Long immutable QA capsule paths must not consume the path budget of
        # the genuine collection title/author fixture. Keep it private/local.
        area=Path(__file__).resolve().parents[1]/'scratch'/'sa';area.mkdir(parents=True,exist_ok=True)
        self.f=fixtures.AutomaticMediaTests('test_confident_no_manual_form_to_verified_chapters_retained_recovery')
        with patch.object(fixtures,'AREA',area):self.f.setUp()
    def tearDown(self):self.f.tearDown()
    def replace_sources(self):
        for source in self.f.sources:source.unlink()
    def rescan(self):
        self.f.inv.launch('Audiobooks');self.f.inv.worker.join(10)
        return self.f.service.reviews.page()['rows']
    def test_existing_m4b_arranges_ready_preserving_chapters_and_24h_recovery(self):
        self.replace_sources();base=self.f.base/'base.m4b';source=self.f.audio/'existing.m4b';chapter=self.f.base/'source-chapters.txt'
        subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=1','-ar','44100','-ac','1','-c:a','aac',str(base)],check=True,timeout=30,creationflags=0x08000000)
        chapter.write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=500\ntitle=First\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=500\nEND=1000\ntitle=Second\n',encoding='utf8')
        subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-i',str(base),'-f','ffmetadata','-i',str(chapter),'-map','0:a:0','-map_chapters','1','-c:a','copy','-metadata','album=A Book','-metadata','title=A Book','-metadata','artist=John Writer',str(source)],check=True,timeout=30,creationflags=0x08000000)
        rows=self.rescan();row=next(r for r in rows if r['members'][0]['path']==str(source))
        result=PublicResearch(self.f.client).lookup(row,str(self.f.audio));self.assertEqual(result['reasons'],[],result)
        fresh,job_id=self.f.service.approve_automatic(row,result,threading.Event(),self.f.client);self.f.wait()
        job=next(j for j in self.f.service.jobs.status()['jobs'] if j['job_id']==job_id)
        self.assertEqual(job['state'],'completed',job);self.assertEqual(job['output']['validation']['encoding']['mode'],'copy')
        self.assertEqual([c['title'] for c in job['manifest']['source_chapters']],['First','Second']);self.assertGreater(job['output']['validation']['native_pcm_evidence']['sample_count'],0)
        self.assertFalse(source.exists());self.assertEqual(self.f.service.cleanup.status(job_id)['recovery']['state'],'retained')
        self.assertEqual(self.f.service.reviews.page(status='converted')['total'],1);self.assertTrue(self.f.service.inspect('Audiobooks','candidates',fresh['id'])['inspector']['audiobook_ready'])
    def test_fan_constituents_to_real_ready_and_unknown_staging_content_preserved(self):
        self.replace_sources();sources=[]
        for index,title in enumerate(('First Tale','Second Tale'),1):
            source=self.f.audio/(f'{index:02d} '+title+'.mp3');sources.append(source)
            subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.4','-c:a','libmp3lame','-b:a','128k','-ar','44100','-ac','1','-metadata','album='+TITLE,'-metadata','title='+title,'-metadata','artist=Narrator Person','-metadata','track='+str(index)+'/2','-metadata','language=ru',str(source)],check=True,timeout=30,creationflags=0x08000000)
        row=next(r for r in self.rescan() if r['title_clue']==TITLE);records,_=parse_contents(PAGE,TITLE);collection,authors=bind_collection(row,TITLE,records,WORKS)
        work={'id':'fantlab:900','titles':[TITLE],'original_title':TITLE,'author_aliases':authors,'original_language':'','policy_version':'standing-17-v1','collection':collection,'collection_records':records,'collection_work_facts':WORKS,'cover_url':''}
        review,facts,reasons=build_policy(row,work,TITLE,authors,collection=collection);facts['work_ids']=[c['work_id'] for c in collection['components']]
        result={'work':work,'review':review,'metadata_facts':facts,'reasons':reasons,'sources':[{'kind':'collection_manifest','verified_identity':True,'url':'https://fantlab.ru/edition900'}],
            'evidence':[{'field':field,'cited_value':value,'source_url':'https://fantlab.ru/edition900','retrieved_utc':'2026-10-11T00:00:00Z','reviewer_actor':'assistant','reviewer_identity':'Private constituent fixture','basis':'Explicit fetched ordered fan contents and independent original-work author relations; all local sources mapped.'} for field,value in {'title':TITLE,'authors':'; '.join(authors)}.items()]}
        fresh,job_id=self.f.service.approve_automatic(row,result,threading.Event(),self.f.client);self.f.wait()
        job=next(j for j in self.f.service.jobs.status()['jobs'] if j['job_id']==job_id);self.assertEqual(job['state'],'completed',job)
        self.assertEqual(job['manifest']['metadata_facts']['collection']['component_count'],2);self.assertEqual(result['metadata_facts']['cover']['kind'],'neutral')
        self.assertTrue(all(not s.exists() for s in sources));self.assertEqual(self.f.service.cleanup.status(job_id)['recovery']['state'],'retained')
        ready=self.f.service.reviews.page(status='converted');self.assertEqual(ready['total'],1);self.assertTrue(ready['rows'][0]['audiobook_ready'])
    def test_unknown_staging_audio_is_never_admitted_by_wav_extension(self):
        row,result=self.f.result();original=self.f.service.storage_cleanup.run;unknown=[]
        def insert_unknown(job_id,*args,**kwargs):
            job=next(j for j in self.f.service.jobs.status()['jobs'] if j['job_id']==job_id)
            path=self.f.service.stage_root/job_id/job['output']['validation']['staging_artifacts']['attempt_id']/'normalized99999.wav';path.write_bytes(b'Unknown producer bytes');unknown.append(path)
            return original(job_id,*args,**kwargs)
        with patch.object(self.f.service.storage_cleanup,'run',side_effect=insert_unknown):
            self.f.service.approve_automatic(row,result,threading.Event(),self.f.client);self.f.wait()
        self.assertTrue(unknown);self.assertTrue(unknown[0].is_file());self.assertEqual(self.f.service.state()['converted_total'],0)
        self.assertTrue(any(r['state']!='completed' for r in self.f.service.storage_cleanup.status()))

class FailedJobRetryTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'scratch'/'source-fallback-2026-10-11');self.addCleanup(self.temp.cleanup)
        self.guard=Mock(return_value=True);self.jobs=AudioJobs(Path(self.temp.name)/'queue.sqlite',Mock(),self.guard,Mock(return_value=True));self.addCleanup(self.jobs.close)
        self.job_id=str(uuid.uuid4());self.manifest={'job_id':self.job_id,'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'sources':[{'path':'fixture.mp3','sha256':'a'*64,'fingerprint':{}}],'metadata':{},'destination':'fixture.m4b','profile':'fixture','evidence':{},'cover':{}}
        self.jobs.enqueue(self.manifest);self.journal={'history':[],'failure':{'at':100,'retryable':True,'exception_class':'OSError'}}
        self.jobs._update(self.job_id,state='needs attention',attempt_id='prior-attempt',journal=json.dumps(self.journal))
    def test_classified_io_failure_has_backoff_and_archived_attempt(self):
        result=self.jobs.retry_failed(self.job_id,200);self.assertTrue(result['retryable']);self.assertFalse(result['requeued']);self.guard.assert_not_called()
        result=self.jobs.retry_failed(self.job_id,3700);self.assertTrue(result['requeued']);self.guard.assert_called_once_with(self.manifest)
        self.assertEqual(self.jobs.status()['jobs'][0]['state'],'pending')
        with connect(self.jobs.database) as db:self.assertEqual(json.loads(db.execute('SELECT record FROM audio_failure_history').fetchone()[0]),self.journal)
    def test_publication_or_unclassified_failure_cannot_be_replayed(self):
        for modification in ({'publication_intent':{'final_path':'preserve'}},{'failure':{'at':100,'retryable':False,'exception_class':'ValueError'}}):
            with self.subTest(modification=modification):
                self.jobs._update(self.job_id,journal=json.dumps(self.journal|modification))
                self.assertFalse(self.jobs.retry_failed(self.job_id,3700)['retryable']);self.assertEqual(self.jobs.status()['jobs'][0]['state'],'needs attention')
        self.guard.assert_not_called()
    def test_changed_frozen_source_review_never_requeues_failed_job(self):
        self.guard.return_value=False;self.assertFalse(self.jobs.retry_failed(self.job_id,3700)['retryable']);self.assertEqual(self.jobs.status()['jobs'][0]['state'],'needs attention')

if __name__=='__main__':unittest.main()

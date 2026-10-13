"""Local-agreement identity through the unchanged private admission, media verification,
publication, source retirement and 24-hour recovery. Private audio fixtures only."""
import json,shutil,subprocess,tempfile,threading,time,unittest,urllib.error
from pathlib import Path
from scanner import Inventory
from merge_service import MergeService
from public_research import PublicClient,PublicResearch
from test_automatic_media import artwork
import test_automatic_processing as automatic_fixtures

class LocalAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=automatic_fixtures.AREA);self.base=Path(self.temp.name);self.audio=self.base/'audio'
        folder=self.audio/'Rollins James'/'Око Бога';folder.mkdir(parents=True);art=self.base/'art.png';art.write_bytes(artwork());self.sources=[]
        for index in (1,2):
            source=folder/('%02d.mp3'%index)
            subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.4','-i',str(art),'-map','0:a','-map','1:v','-c:a','libmp3lame','-b:a','128k','-ar','44100','-ac','1','-c:v','png','-id3v2_version','3',
                '-metadata','album=Око Бога','-metadata','title=Глава '+str(index),'-metadata','artist=Джеймс Роллинс','-metadata','track=%d/2'%index,'-disposition:v','attached_pic',str(source)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.sources.append(source)
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots);self.inv.launch('Audiobooks');self.inv.worker.join(10);self.service=MergeService(self.inv,self.base/'cache')
        self.calls=[]
        def offline(url,*_):
            # Every public source is closed: identity must not depend on the Internet.
            self.calls.append(url);raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        self.client=PublicClient(self.inv.database,fetch=offline)
    def tearDown(self):self.service.close();self.temp.cleanup()
    def wait(self):
        limit=time.monotonic()+30
        while self.service.state()['state'] in ('Running','Pausing') or self.service.state().get('queued') or self.service.state().get('cleanup_active'):
            if time.monotonic()>limit:self.fail('Private local-agreement job exceeded 30s')
            time.sleep(.05)
    def research(self):
        row=self.service.reviews.page()['rows'][0];result=PublicResearch(self.client,leads=[]).lookup(row,str(self.audio))
        self.assertEqual(result['reasons'],[],result);return row,result
    def test_local_agreement_reaches_verified_ready_with_sources_retired_and_recovery_retained(self):
        row,result=self.research()
        self.assertTrue(all('fantlab' in u or 'wikidata' in u for u in self.calls),self.calls)
        fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['job_id'],job_id);self.assertEqual(job['state'],'completed',job)
        self.assertTrue(job['output']['validation']['passed']);self.assertTrue(Path(job['output']['final_path']).is_file())
        # Ruling 3: an English spelling exists locally (folder "Rollins James"), surname first.
        self.assertEqual(Path(job['output']['final_path']).name,'Око Бога - Rollins James.m4b')
        self.assertTrue(all(not p.exists() for p in self.sources));self.assertEqual(self.service.cleanup.status(job_id)['recovery']['state'],'retained')
        facts=job['manifest']['metadata_facts'];self.assertEqual(facts['identity_basis'],'local_agreement');self.assertEqual(facts['local_agreement']['author']['state'],'yellow')
        local=[e for e in job['manifest']['evidence']['metadata_fields'] if e['source_url']=='']
        self.assertEqual({e['field'] for e in local},{'title','authors'});self.assertTrue(all(e['verification']=='local agreement' for e in local))
        context=self.service.reviews._context(fresh);self.assertTrue(context['automatic_approval']);self.assertFalse(context.get('automatic_pending'))
        self.assertEqual(self.service.reviews.page(status='converted')['total'],1)
    def test_changed_local_sources_after_research_are_refused_and_preserved(self):
        row,result=self.research()
        result['metadata_facts']['local_agreement']['author']['value']='Клайв Касслер'
        with self.assertRaises(ValueError) as raised:self.service.approve_automatic(row,result,threading.Event(),self.client)
        self.assertIn('Local identity evidence changed',str(raised.exception))
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))
    def test_local_evidence_is_refused_outside_local_agreement(self):
        row,result=self.research()
        result['metadata_facts'].pop('identity_basis')
        with self.assertRaises(ValueError):self.service.approve_automatic(row,result,threading.Event(),self.client)
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))

if __name__=='__main__':unittest.main()

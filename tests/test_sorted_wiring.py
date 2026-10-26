"""Senua 0.21.3 F6: the production output-folder wiring end to end, with no fixture standing in for it.

Every other conversion-then-cleanup module replaces MergeService.output_policy (tests/sorted_fixture.py). Here an
Inventory is built with its own separate Sorted folder, exactly as the installed app is, and a book goes through
identity, admission, conversion, publication and source removal under the real MergeService.output_policy and
CleanupJobs rule (Sergei's rulings 2 and 1a). Private audio fixtures only; no network, no library access."""
import shutil,subprocess,tempfile,threading,time,unittest,urllib.error
from pathlib import Path
from scanner import Inventory
from scan_wait import finish_scan
from merge_service import MergeService
from public_research import PublicClient,PublicResearch
from test_automatic_media import artwork
import test_automatic_processing as automatic_fixtures


class ProductionSortedWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=automatic_fixtures.AREA);self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.audio=self.base/'audio';self.sorted=self.base/'Audiobooks Sorted';self.sorted.mkdir()
        folder=self.audio/'Rollins James'/'Око Бога';folder.mkdir(parents=True);art=self.base/'art.png';art.write_bytes(artwork());self.sources=[]
        for index in (1,2):
            source=folder/('%02d.mp3'%index)
            subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.4','-i',str(art),'-map','0:a','-map','1:v','-c:a','libmp3lame','-b:a','128k','-ar','44100','-ac','1','-c:v','png','-id3v2_version','3',
                '-metadata','album=Око Бога','-metadata','title=Глава '+str(index),'-metadata','artist=Джеймс Роллинс','-metadata','track=%d/2'%index,'-disposition:v','attached_pic',str(source)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.sources.append(source)
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots,output_root=str(self.sorted));self.inv.launch('Audiobooks');finish_scan(self.inv)
        self.service=MergeService(self.inv,self.base/'cache');self.addCleanup(self.service.close)
        def offline(url,*_):raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        self.client=PublicClient(self.inv.database,fetch=offline)

    def wait(self):
        limit=time.monotonic()+60
        while self.service.state()['state'] in ('Running','Pausing') or self.service.state().get('queued') or self.service.state().get('cleanup_active'):
            if time.monotonic()>limit:self.fail('Private wiring job exceeded 60 s')
            time.sleep(.05)

    def test_book_is_published_in_sorted_and_only_then_its_sources_are_removed(self):
        self.assertEqual(self.service.output_policy(),(str(self.sorted),tuple(self.inv.all_source_roots())),'the production policy, not a fixture')
        row=self.service.reviews.page()['rows'][0];result=PublicResearch(self.client,leads=[]).lookup(row,str(self.audio))
        self.assertEqual(result['reasons'],[],result)
        fresh,job_id=self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        final=Path(job['output']['final_path'])
        self.assertTrue(final.is_file());self.assertTrue(final.is_relative_to(self.sorted),final)
        cleanup=self.service.cleanup.status(job_id);self.assertEqual(cleanup['state'],'completed',cleanup);self.assertEqual(cleanup['removed'],2)
        self.assertTrue(all(not p.exists() for p in self.sources))



def setUpModule():
    # Ruling 29 (0.22.2) has its own tests; these fixtures predate it (tests/original_title_fixture.py): Russian titles by
    # authors credited in Cyrillic with a foreign first name, used to test other rules.
    global _no_original_title_wait
    from original_title_fixture import no_wait
    _no_original_title_wait = no_wait()


def tearDownModule():
    _no_original_title_wait.stop()


if __name__=='__main__':unittest.main()

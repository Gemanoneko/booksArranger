"""Sergei as a source and "Approve as is" (rulings 6a, 6b, 10, 11, 11a; 2026-10-24).

Real private audio fixtures through identity, Approve, conversion, publication and source removal, with a separate
Sorted folder and the production output policy. No network, no library access."""
import json,shutil,subprocess,tempfile,threading,time,unittest,urllib.error
from pathlib import Path
from scanner import Inventory,connect
from merge_service import MergeService
from public_research import PublicClient,PublicResearch
from test_automatic_media import artwork
import manual_metadata
import test_automatic_processing as automatic_fixtures


def tone(path,cover,**tags):
    path.parent.mkdir(parents=True,exist_ok=True)
    metadata=[]
    for key,value in tags.items():metadata+=['-metadata',key+'='+value]
    subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=0.4','-i',str(cover),'-map','0:a','-map','1:v','-c:a','libmp3lame','-b:a','128k','-ar','44100','-ac','1','-c:v','png','-id3v2_version','3']
                   +metadata+['-disposition:v','attached_pic',str(path)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return path


class ApproveAsIsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=automatic_fixtures.AREA);self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.audio=self.base/'audio';self.audio.mkdir();self.sorted=self.base/'Audiobooks Sorted';self.sorted.mkdir()
        self.cover=self.base/'art.png';self.cover.write_bytes(artwork())

    def start(self):
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots,output_root=str(self.sorted));self.inv.launch('Audiobooks');self.inv.worker.join(10)
        self.service=MergeService(self.inv,self.base/'cache');self.addCleanup(self.service.close)
        def offline(url,*_):raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        self.service.automatic.research=PublicResearch(PublicClient(self.inv.database,fetch=offline),leads=[])
        return self.service.reviews.page()['rows']

    def wait(self):
        limit=time.monotonic()+60
        while self.service.state()['state'] in ('Running','Pausing') or self.service.state().get('queued') or self.service.state().get('cleanup_active'):
            if time.monotonic()>limit:self.fail('Private Approve job exceeded 60 s')
            time.sleep(.05)

    def research(self,row):
        return self.service.automatic.research.lookup(dict(row,_manual_metadata_sources=[]),str(self.audio),threading.Event())

    def test_no_author_anywhere_approved_as_is_goes_to_bez_avtora_and_the_preview_path_is_the_one_used(self):
        sources=[tone(self.audio/'Unsorted'/'Утро снайпера'/('%02d.mp3'%n),self.cover,album='Утро снайпера',title='Глава %d'%n,track='%d/2'%n) for n in (1,2)]
        row=self.start()[0]
        self.assertEqual(self.research(row)['ask']['kind'],'title_author','positive control: the files name no author')
        preview=self.service.approval_preview(row['id'],row['revision'])
        self.assertEqual(preview['path'],str(Path('Без автора')/'Утро снайпера.m4b'));self.assertFalse(preview['taken'])
        approved=self.service.approve_book(row['id'],row['revision']);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['job_id'],approved['job_id']);self.assertEqual(job['state'],'completed',job)
        final=Path(job['output']['final_path']);self.assertEqual(final,self.sorted/'Без автора'/'Утро снайпера.m4b');self.assertTrue(final.is_file())
        self.assertEqual(job['manifest']['evidence']['metadata_actor'],'user','recorded as Sergei\'s approval')
        self.assertIn('Approved by you',job['manifest']['evidence']['manual_note'])
        cleanup=self.service.cleanup.status(job['job_id']);self.assertEqual(cleanup['state'],'completed',cleanup)
        self.assertTrue(all(not p.exists() for p in sources),'removed only after the verified result is in Sorted')

    def test_typed_title_and_author_are_used_and_saved_as_entered_by_you(self):
        tone(self.audio/'Unsorted'/'Тайна'/'Тайна.mp3',self.cover,title='Тайна',artist='Лев Толстой',album_artist='Антон Чехов')
        row=self.start()[0]
        self.assertEqual(self.research(row)['ask']['kind'],'author_unclear','positive control: two people credited')
        preview=self.service.approval_preview(row['id'],row['revision'],title='Тайна дома',author='Антон Чехов')
        approved=self.service.approve_book(row['id'],row['revision'],title='Тайна дома',author='Антон Чехов');self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        self.assertEqual(Path(job['output']['final_path']),Path(preview['absolute']))
        self.assertEqual((job['manifest']['metadata']['title'],job['manifest']['metadata']['canonical_author']),('Тайна дома','Чехов Антон'))
        with connect(self.inv.database) as db:entered=manual_metadata.records(db,approved['row'])
        self.assertEqual(entered[-1]['values'],{'title':'Тайна дома','canonical_author':'Антон Чехов'});self.assertEqual(entered[-1]['provider'],'Entered by you')

    def test_approve_overrides_an_order_hold_and_a_taken_name_is_never_overwritten(self):
        for n,name in ((1,'Пролог'),(2,'Финал')):tone(self.audio/'Unsorted'/'Брат мой'/(name+'.mp3'),self.cover,album='Брат мой',artist='Иван Петров')
        row=self.start()[0]
        self.assertIn('Playback order uncertain',self.research(row)['reasons'],'positive control: no track numbers')
        preview=self.service.approval_preview(row['id'],row['revision'])
        taken=Path(preview['absolute']);taken.parent.mkdir(parents=True);taken.write_bytes(b'PREEXISTING')
        self.assertTrue(self.service.approval_preview(row['id'],row['revision'])['taken'])
        with self.assertRaisesRegex(ValueError,'already exists'):self.service.approve_book(row['id'],row['revision'])
        self.assertEqual(taken.read_bytes(),b'PREEXISTING');self.assertEqual(self.service.jobs.status()['jobs'],[])
        taken.unlink();fresh=self.service.reviews.page()['rows'][0]
        self.service.approve_book(fresh['id'],fresh['revision']);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)

    def test_convert_whats_there_leaves_out_the_missing_file(self):
        sources=[tone(self.audio/'Unsorted'/'Новая плоть'/('%02d.mp3'%n),self.cover,album='Новая плоть',title='Рассказ %d'%n,artist='Иван Петров',track='%d/3'%n) for n in (1,2,3)]
        self.start();sources[2].unlink()
        self.inv.launch('Audiobooks');self.inv.worker.join(10)
        row=self.service.reviews.page()['rows'][0];self.assertTrue(any(m.get('missing') for m in row['members']),'positive control: a member is gone')
        with self.assertRaisesRegex(ValueError,'unavailable'):self.service.approve_book(row['id'],row['revision'])
        self.service.approve_book(row['id'],row['revision'],without_missing=True);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        self.assertEqual([Path(s['path']).name for s in job['manifest']['sources']],['01.mp3','02.mp3'])

    def test_saved_values_are_the_identity_without_any_other_source(self):
        tone(self.audio/'Unsorted'/'Неизвестная запись'/'Запись1.mp3',self.cover)
        row=self.start()[0]
        self.assertTrue(self.research(row)['reasons'],'positive control: the files settle nothing')
        with connect(self.inv.database) as db:manual_metadata.append(db,manual_metadata.capture(row,{'title':'Тайная запись','canonical_author':'Robert Brooks'},''))
        with connect(self.inv.database) as db:sources=manual_metadata.records(db,row)
        result=self.service.automatic.research.lookup(dict(row,_manual_metadata_sources=sources),str(self.audio),threading.Event())
        self.assertEqual(result['reasons'],[],result.get('reasons'))
        self.assertEqual((result['review']['title'],result['review']['canonical_author']),('Тайная запись','Brooks Robert'))
        self.assertEqual(result['local_agreement']['author']['state'],'entered')

    def test_a_changed_source_after_the_preview_is_refused_and_nothing_moves(self):
        source=tone(self.audio/'Unsorted'/'Тайна'/'Тайна.mp3',self.cover,album='Тайна',artist='Иван Петров')
        row=self.start()[0]
        with open(source,'ab') as stream:stream.write(b'changed')
        with self.assertRaises(ValueError):self.service.approve_book(row['id'],row['revision'])
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(source.exists())


if __name__=='__main__':unittest.main()

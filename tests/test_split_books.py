"""v0.15.0 split-book grouping and spelling fixes, with real library names as fixtures.
Private fixtures only: no network, no live catalog, no library access."""
import contextlib,json,shutil,sqlite3,subprocess,tempfile,threading,time,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
import groups
import split_books
from local_identity import (agreement,canonical_author,catalog_index,confirmed_spellings,middle_initial_same,slip_same,
                            KNOWN_AGREEMENT_VERSIONS,AGREEMENT_VERSION)
from source_identity import source_gate
import test_automatic_processing as automatic_fixtures
from test_local_identity import catalogue,Catalog
AREA=automatic_fixtures.AREA
ROOT='Z:\\Audiobooks'
AAC=('aac','44100',1)

def row(relative,tags,profile=AAC,duration=600.0,size=1000,root=ROOT):
    """One catalog row as the scanner stores it (tags plus the ffprobe stream profile)."""
    path=root+'\\'+relative.replace('/','\\')
    codec,rate,channels=profile
    metadata={'title':tags.get('album',''),'artist':tags.get('artist',''),'tags':tags,
              'probe':{'format':{'duration':str(duration)},'streams':[{'codec_type':'audio','codec_name':codec,'sample_rate':rate,'channels':channels}]}}
    return {'root':root,'path':path,'kind':'audiobook','size':size,'modified':10,'metadata':json.dumps(metadata,ensure_ascii=False),'error':'','missing':0}

def split_scopes(built):
    return {scope:group for scope,group in built.items() if group.get('split_book')}

def rendered(group,fingerprint='private-fixture'):
    for m in group['members']:m['metadata'].pop('probe',None)
    return dict(group,fingerprint=fingerprint)

def dan_brown(count=12,folder='Dan Brown/Robert Langdon series/3 The Lost Symbol',skip=()):
    return [row('%s/Dan Brown - The Lost Symbol - %02d - unknown title.m4b'%(folder,n),{'artist':'Dan Brown','album':'The Lost Symbol','track':str(n)})
            for n in range(1,count+1) if n not in skip]

def local_work(group,title,author):
    return {'titles':[title],'author_aliases':[author],'identity_basis':'local_agreement','policy_version':'standing-17-v1'}


class GroupingTests(unittest.TestCase):
    """Files that provably form one book become one candidate; the order is proven."""
    def test_dan_brown_chapter_files_become_one_ordered_book(self):
        built=groups.build(dan_brown())
        self.assertEqual(len(built),1,list(built))
        group=next(iter(built.values()))
        self.assertIn('\x1fSplit book ',group['scope']);self.assertEqual(group['split_book']['parts'],12)
        self.assertEqual(group['split_book']['order_basis'],'embedded track numbers');self.assertEqual(group['split_book']['book_name'],'Dan Brown - The Lost Symbol')
        self.assertEqual([m['track'] for m in group['members']],list(range(1,13)));self.assertEqual([m['order'] for m in group['members']],list(range(1,13)))
        self.assertEqual(group['conflicts'],[]);self.assertFalse(group.get('source_partition_uncertain'))
        # Local identity on the whole book: the shared file name supports title and author; no sibling is outside it.
        local=agreement(rendered(group),ROOT,[])
        self.assertTrue(local['accepted'],local['conflicts']);self.assertEqual(local['fields']['title']['value'],'The Lost Symbol')
        self.assertEqual(local['fields']['author']['value'],'Dan Brown')
        self.assertEqual(source_gate(rendered(group),local_work(group,'The Lost Symbol','Dan Brown')),[])
    def test_deception_point_chapter_titles_are_chapters(self):
        names=['Вступление']+['Глава %d'%n for n in range(1,6)]
        files=[row('Dan Brown/Deception Point/Дэн Браун - Точка обмана - %02d - %s.m4b'%(n,name),{'title':name,'artist':'Дэн Браун','album':'Точка обмана','track':str(n)})
               for n,name in enumerate(names,1)]
        group=next(iter(groups.build(files).values()))
        self.assertTrue(group.get('split_book'));self.assertEqual(len(group['members']),6)
    def test_part_sets_beside_each_other_in_an_author_folder(self):
        files=[]
        for title in ('Чужак','Куджо'):
            for n in (1,2):files.append(row('Stephen King/%s %d.m4b'%(title,n),{'album':title,'artist':'Стивен Кинг','title':'%s %d'%(title,n),'track':'%d/2'%n}))
        found=split_scopes(groups.build(files))
        self.assertEqual(sorted(len(g['members']) for g in found.values()),[2,2])
        self.assertEqual(sorted(g['title_clue'] for g in found.values()),['Куджо','Чужак'])
        for group in found.values():
            local=agreement(rendered(group),ROOT,[])
            self.assertTrue(local['accepted'],local['conflicts']);self.assertEqual(local['fields']['author']['state'],'yellow')
    def test_cd_folders_one_file_each(self):
        files=[row('Ночь триффидов/CD%d/Ночь триффидов.m4b'%n,{'album':'Ночь триффидов','artist':'Саймон Кларк'}) for n in (1,2)]
        group=next(iter(groups.build(files).values()))
        self.assertTrue(group.get('split_book'),group['scope']);self.assertEqual(group['split_book']['order_basis'],'one file per disc or part folder')
        self.assertEqual([(m['disc'],m['track']) for m in group['members']],[(1,1),(2,1)])
        self.assertEqual(source_gate(rendered(group),local_work(group,'Ночь триффидов','Саймон Кларк')),[])
    def test_cd_folders_with_tracks_per_disc(self):
        files=[row('Book/CD%d/%02d.m4b'%(d,t),{'album':'Хроники Амбера','artist':'Роджер Желязны','track':'%d/2'%t}) for d in (1,2) for t in (1,2)]
        group=next(iter(groups.build(files).values()))
        self.assertTrue(group.get('split_book'));self.assertEqual([(m['disc'],m['track']) for m in group['members']],[(1,1),(1,2),(2,1),(2,2)])
    def test_part_numbers_in_names_without_track_tags(self):
        files=[row('Joe Hill/1412. Странная погода (Дмитрий Рыбин)/Странная погода %d.m4b'%n,{'album':'Странная погода','artist':'Джо Хилл','title':'Странная погода %d'%n}) for n in (1,2)]
        group=next(iter(groups.build(files).values()))
        self.assertEqual(group['split_book']['order_basis'],'part numbers in the file names')
        self.assertEqual(source_gate(rendered(group),local_work(group,'Странная погода','Джо Хилл')),[])
    def test_roman_part_numbers(self):
        files=[row('Dan Simmons/Гиперион/0%d Часть %s.m4b'%(n,r),{'album':'Гиперион','artist':'Дэн Симмонс','title':'Часть '+r,'track':'%d/2'%n}) for n,r in ((1,'I'),(2,'II'))]
        self.assertTrue(next(iter(groups.build(files).values())).get('split_book'))
    def test_untouched_candidates_keep_their_scopes(self):
        files=[row('Stephen King/Мизери.m4b',{'album':'Мизери','artist':'Стивен Кинг'}),
               row('Author/Book/01.mp3',{'album':'Book','artist':'A B','track':'1/2'},('mp3','44100',1)),
               row('Author/Book/02.mp3',{'album':'Book','artist':'A B','track':'2/2'},('mp3','44100',1))]
        built=groups.build(files)
        self.assertFalse(split_scopes(built));self.assertEqual(len(built),2)
        self.assertTrue(any(s.endswith('\x1fSingle audiobook file') for s in built))


class HoldTests(unittest.TestCase):
    """Gaps, duplicates, mixed recordings or narrators, volumes and own titles hold: the files stay separate."""
    def held(self,files,reason):
        built=groups.build(files)
        self.assertFalse(split_scopes(built),list(built));self.assertEqual(len(built),len(files))
        members=[groups.member(r) for r in files]
        _,holds=split_books.plan(members)
        self.assertTrue(any(reason in r for h in holds for r in h['reasons']),holds)
    def test_gap(self):
        self.held(dan_brown(6,skip=(4,)),'gap in part numbers')
    def test_missing_first_part(self):
        self.held(dan_brown(6,skip=(1,)),'numbering does not start at 1')
    def test_duplicate_part(self):
        files=[row('Stephen King/Чужак %s.m4b'%name,{'album':'Чужак','artist':'Стивен Кинг','title':'Чужак '+name[0],'track':'%s/2'%name[0]}) for name in ('1','1 (копия)','2')]
        self.held(files,'duplicate part numbers')
    def test_declared_total_differs(self):
        files=[row('Robert R. McCammon/Жизнь мальчишки %d.m4b'%n,{'album':'Жизнь мальчишки','artist':'Роберт Маккаммон','track':'%d/3'%n}) for n in (1,2)]
        self.held(files,'a part says 3 parts, 2 found')
    def test_mixed_narrators(self):
        files=[row('Stephen King/Оно %d.m4b'%n,{'album':'Оно','artist':'Стивен Кинг','track':'%d/2'%n,'comment':'Читает '+reader})
               for n,reader in ((1,'Игорь Князев'),(2,'Олег Булдаков'))]
        self.held(files,'mixed narrators named in comments')
        files=[row('Stephen King/Оно %d.m4b'%n,{'album':'Оно','artist':'Стивен Кинг','track':'%d/2'%n,'composer':reader})
               for n,reader in ((1,'Игорь Князев'),(2,'Олег Булдаков'))]
        self.held(files,'mixed composer tags')
    def test_mixed_authors(self):
        files=[row('Калейдоскоп 4/%s-Рассказ.mp3'%a,{'album':'Калейдоскоп 4','artist':a,'track':str(n)},('mp3','44100',1)) for n,a in enumerate(('Виктор Глебов','Юрий Молчан'),1)]
        built=groups.build(files)
        self.assertFalse(split_scopes(built))
    def test_mixed_recordings(self):
        files=[row('Stephen King/Чужак %d.m4b'%n,{'album':'Чужак','artist':'Стивен Кинг','track':'%d/2'%n},('aac',rate,1)) for n,rate in ((1,'44100'),(2,'22050'))]
        self.held(files,'mixed recordings')
    def test_series_volumes(self):
        files=[row('Light Novels/Toradora!/Торадора! Том %d.m4b'%n,{'album':'Торадора!','artist':'Ююко Такэмия','title':'Торадора! Том %d'%n,'track':'%d/3'%n}) for n in (1,2,3)]
        self.held(files,'a volume or book number')
    def test_separate_works_in_one_album(self):
        titles=['Повелитель Хаоса','Элрик из Мелнибонэ','Скиталец по морям Судьбы']
        files=[row('Michael John Moorcock/Elric/%02d. %s.m4b'%(n,t),{'album':'Сага об Элрике','artist':'Майкл Муркок','title':'%02d. %s'%(n,t),'track':'%d/3'%n}) for n,t in enumerate(titles,1)]
        self.held(files,'a part has its own title')
    def test_tag_and_name_orders_disagree(self):
        files=[row('Stephen King/Чужак %d.m4b'%n,{'album':'Чужак','artist':'Стивен Кинг','track':'%d/2'%(3-n)}) for n in (1,2)]
        self.held(files,'order the parts differently')
    def test_protected_sibling_with_same_title_holds(self):
        files=[row('Stephen King/Чужак %d.m4b'%n,{'album':'Чужак','artist':'Стивен Кинг','track':'%d/3'%n}) for n in (1,2,3)]
        first=groups.member(files[0])
        protected=groups.build(files[:1])
        built=groups.build(files,protected)
        self.assertFalse(split_scopes(built))
        _,holds=split_books.plan([groups.member(r) for r in files[1:]],[first])
        self.assertTrue(any('separate candidates or protected' in r for h in holds for r in h['reasons']),holds)

class ProtectedSplitTests(unittest.TestCase):
    def test_reviewed_split_book_is_stable_and_fails_closed_when_parts_change(self):
        files=dan_brown(4)
        group=next(iter(groups.build(files).values()))
        protected={group['scope']:json.loads(json.dumps(group,ensure_ascii=False))}
        again=groups.build(files,protected)
        self.assertEqual(again[group['scope']],protected[group['scope']])
        changed=[dict(f) for f in files];tags=json.loads(changed[2]['metadata']);tags['tags']['track']='7';changed[2]['metadata']=json.dumps(tags)
        held=groups.build(changed,protected)[group['scope']]
        self.assertTrue(held['source_partition_uncertain']);self.assertTrue(any('no longer prove one book' in c for c in held['conflicts']))
        self.assertEqual(len(held['members']),4)

class SplitGateTests(unittest.TestCase):
    def test_gate_rederives_positions(self):
        group=rendered(next(iter(groups.build(dan_brown(4)).values())))
        work=local_work(group,'The Lost Symbol','Dan Brown')
        self.assertEqual(source_gate(group,work),[])
        tampered=json.loads(json.dumps(group));tampered['members'][0]['track'],tampered['members'][1]['track']=2,1
        self.assertIn('Playback order uncertain',source_gate(tampered,work))
        broken=json.loads(json.dumps(group));broken['members'][3]['metadata']['tags']['track']='9'
        self.assertIn('Source membership uncertain',source_gate(broken,work))


def make_part(path,title,track,chapters=False):
    ffmpeg=shutil.which('ffmpeg')
    args=[ffmpeg,'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=1']
    if chapters:
        meta=path.with_suffix('.txt');meta.write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=500\ntitle=A\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=500\nEND=1000\ntitle=B\n',encoding='utf-8')
        args+=['-f','ffmetadata','-i',str(meta),'-map','0:a','-map_chapters','1']
    args+=['-c:a','aac','-ar','44100','-ac','1','-metadata','album=Чужак','-metadata','artist=Стивен Кинг','-metadata','title='+title,'-metadata','track=%d/2'%track,str(path)]
    subprocess.run(args,check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if chapters:path.with_suffix('.txt').unlink()

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg required')
class SplitAdmissionTests(unittest.TestCase):
    """Two M4B parts through the unchanged admission, v4 media policy, publication and retirement."""
    def build(self,chapters=False):
        from scanner import Inventory
        from merge_service import MergeService
        from public_research import PublicClient
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.base=Path(self.temp.name);self.audio=self.base/'audio'
        folder=self.audio/'Stephen King';folder.mkdir(parents=True);self.sources=[]
        for n in (1,2):
            source=folder/('Чужак %d.m4b'%n);make_part(source,'Чужак %d'%n,n,chapters);self.sources.append(source)
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots);self.inv.launch('Audiobooks');self.inv.worker.join(10);self.service=MergeService(self.inv,self.base/'cache')
        self.addCleanup(self.temp.cleanup);self.addCleanup(self.service.close)
        def offline(url,*_):raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        self.client=PublicClient(self.inv.database,fetch=offline)
        rows=self.service.reviews.page()['rows']
        self.assertEqual(len(rows),1,[r['scope'] for r in rows]);self.row=rows[0];self.assertTrue(self.row.get('split_book'))
        from public_research import PublicResearch
        self.result=PublicResearch(self.client,leads=[]).lookup(self.row,str(self.audio))
        self.assertEqual(self.result['reasons'],[],self.result)
    def wait(self):
        limit=time.monotonic()+60
        while self.service.state()['state'] in ('Running','Pausing') or self.service.state().get('queued') or self.service.state().get('cleanup_active'):
            if time.monotonic()>limit:self.fail('Private split-book job exceeded 60s')
            time.sleep(.05)
    def test_two_m4b_parts_become_one_verified_m4b(self):
        self.build()
        fresh,job_id=self.service.approve_automatic(self.row,self.result,threading.Event(),self.client);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        output=job['output'];self.assertTrue(output['validation']['passed']);final=Path(output['final_path'])
        self.assertTrue(final.is_file());self.assertEqual(final.suffix,'.m4b');self.assertEqual(final.name,'Чужак - King Stephen.m4b')
        self.assertEqual(output['validation']['encoding']['mode'],'normalize');self.assertEqual(len(output['validation']['chapters']),2)
        self.assertEqual(len(job['manifest']['sources']),2)
        self.assertTrue(all(not p.exists() for p in self.sources));self.assertEqual(self.service.cleanup.status(job_id)['recovery']['state'],'retained')
    def test_parts_with_their_own_chapters_are_held(self):
        self.build(chapters=True)
        with self.assertRaises(ValueError) as raised:self.service.approve_automatic(self.row,self.result,threading.Event(),self.client)
        self.assertIn('carry their own chapters',str(raised.exception))
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))
    def test_parts_whose_audio_profiles_differ_at_admission_are_held(self):
        self.build()
        import audio_pipeline
        real=audio_pipeline.probe
        def probe(path,stage,stop):
            raw=real(path,stage,stop)
            if str(path).endswith('2.m4b'):
                for stream in raw.get('streams',[]):
                    if stream.get('codec_type')=='audio':stream['sample_rate']='22050'
            return raw
        with patch.object(audio_pipeline,'probe',probe),self.assertRaises(ValueError) as raised:
            self.service.approve_automatic(self.row,self.result,threading.Event(),self.client)
        self.assertIn('audio profiles differ',str(raised.exception))
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg required')
class JoinedM4BMediaTests(unittest.TestCase):
    """The v4 normalizer joins M4B parts; a part with its own chapter plan is refused on its snapshot."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def manifest(self,paths):
        import uuid
        from audio_pipeline import digest,fingerprint
        from encoding_policy import AUTOMATIC_PROFILE,freeze_automatic_policy
        from test_automatic_media import artwork
        cover=self.root/'cover.png';cover.write_bytes(artwork())
        sources=[{'path':str(path),**fingerprint(path),'sha256':digest(path),'metadata':{'tags':{}}} for path in paths]
        return {'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'root':str(self.root),
            'destination':str(self.root/'final.m4b'),'profile':AUTOMATIC_PROFILE,'encoding_policy':freeze_automatic_policy(sources),
            'sources':sources,'cover':{'path':str(cover),'sha256':digest(cover)},'comments':'','chapters':['Часть 1','Часть 2'],
            'metadata':{'title':'Чужак','canonical_author':'King Stephen'}}
    def test_parts_join_with_one_chapter_each(self):
        from audio_pipeline import create_private,digest
        paths=[self.root/('Чужак %d.m4b'%n) for n in (1,2)]
        for n,path in enumerate(paths,1):make_part(path,'Чужак %d'%n,n)
        before=[digest(p) for p in paths]
        output,proof=create_private(self.manifest(paths),self.root/'stage',threading.Event())
        self.assertEqual(proof['encoding']['mode'],'normalize');self.assertEqual([c['title'] for c in proof['chapters']],['Часть 1','Часть 2'])
        self.assertAlmostEqual(proof['expected_duration'],proof['decoded_duration'],delta=.2);self.assertEqual(before,[digest(p) for p in paths])
    def test_part_with_own_chapters_is_refused(self):
        from audio_pipeline import create_private,ValidationError
        paths=[self.root/('Чужак %d.m4b'%n) for n in (1,2)]
        make_part(paths[0],'Чужак 1',1);make_part(paths[1],'Чужак 2',2,chapters=True)
        with self.assertRaises(ValidationError) as raised:create_private(self.manifest(paths),self.root/'stage',threading.Event())
        self.assertIn('carry their own chapters',str(raised.exception))


class SpellingTests(unittest.TestCase):
    """One author, one folder: a fetched catalog spelling wins over a majority typo."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
    def database(self,spellings,evidence=()):
        path=self.base/('catalog-%d.sqlite3'%len(list(self.base.iterdir())))
        with contextlib.closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE files(root TEXT, path TEXT, kind TEXT, metadata TEXT, missing INTEGER DEFAULT 0, PRIMARY KEY(root,path))")
            db.execute('CREATE TABLE automatic_candidates(id TEXT PRIMARY KEY,revision INTEGER,fingerprint TEXT,state TEXT,result TEXT,retry_at REAL,attempted TEXT,matcher_version TEXT)')
            for spelling,count in spellings:
                for index in range(count):
                    db.execute("INSERT INTO files VALUES(?,?,'audiobook',?,0)",(ROOT,ROOT+'\\Shelf\\%s %02d\\01.mp3'%(spelling,index),json.dumps({'tags':{'artist':spelling,'album':'Книга %d'%index}})))
            for n,(value,url,facts) in enumerate(evidence):
                result={'metadata_facts':{'authors':[value]} if facts else None,'evidence':[{'field':'authors','cited_value':value,'source_url':url}]}
                db.execute("INSERT INTO automatic_candidates VALUES(?,1,'f','Waiting for source',?,NULL,?,'v')",('c%d'%n,json.dumps(result),'2026-10-13T00:00:%02d'%n))
            db.commit()
        return path
    PRATCHETT=(('Terry Pratchet',20),('Terry Pratchett',5),('Терри Пратчетт',11))
    def test_confirmed_spelling_wins_over_majority_typo(self):
        url='https://openlibrary.org/works/OL453749W'
        index=catalog_index(self.database(self.PRATCHETT,[('Terry Pratchett',url,True)]),ROOT)
        self.assertEqual(index['confirmed'],{'Terry Pratchett':[url]})
        for agreed in ('Терри Пратчетт','Terry Pratchet','Pratchett Terry'):
            with self.subTest(agreed=agreed):
                name,record=canonical_author(agreed,[agreed],index,'')
                self.assertEqual(name,'Pratchett Terry');self.assertEqual(record['confirmed_by'],[url]);self.assertIn('confirmed by fetched catalog evidence',record['why'])
    def test_without_confirmation_behaviour_is_unchanged(self):
        index=catalog_index(self.database(self.PRATCHETT),ROOT)
        self.assertEqual(index['confirmed'],{})
        name,record=canonical_author('Терри Пратчетт',['Терри Пратчетт'],index,'')
        self.assertEqual(name,'Pratchet Terry');self.assertNotIn('confirmed_by',record)
        # Zahn: no fetched evidence anywhere, the majority spelling stays (known limit).
        index=catalog_index(self.database((('Thimoty Zahn',2),('Timothy Zahn',1),('Тимоти Зан',1))),ROOT)
        self.assertEqual(canonical_author('Тимоти Зан',['Тимоти Зан'],index,'')[0],'Zahn Thimoty')
    def test_unusable_evidence_is_ignored(self):
        evidence=[('Terry Pratchett','',True),('Terry Pratchett','http://openlibrary.org/x',True),('Terry Pratchett','https://openlibrary.org/y',False),
                  ('Сборник','https://fantlab.ru/work1',True),('Neil Gaiman & Terry Pratchett','https://fantlab.ru/work2',True)]
        self.assertEqual(confirmed_spellings(self.database(self.PRATCHETT,evidence)),{})
    def test_script_follows_ruling_3_not_the_confirmation(self):
        index=catalog_index(self.database((('Сергей Лукьяненко',4),('Лукьяненко Сергей',1)),[('Sergei Lukyanenko','https://openlibrary.org/a',True)]),ROOT)
        self.assertEqual(canonical_author('Сергей Лукьяненко',['Сергей Лукьяненко'],index,'ru')[0],'Лукьяненко Сергей')
        self.assertEqual(canonical_author('Сергей Лукьяненко',['Сергей Лукьяненко'],index,'')[0],'Лукьяненко Сергей')
    def test_dick_one_folder_without_reopening_r2_2(self):
        index=catalog_index(self.database((('Philip K. Dick',1),('Дик Филип Киндред',1),('Филип Дик',2))),ROOT)
        self.assertEqual(canonical_author('Дик Филип Киндред',['Дик Филип Киндред'],index,'')[0],'Dick Philip K.')
        self.assertEqual(canonical_author('Philip K. Dick',['Philip K. Dick'],index,'')[0],'Dick Philip K.')
        self.assertTrue(middle_initial_same('Philip K. Dick','Дик Филип Киндред'))
        # R2-2: an initial never stands for a first name; conflicting middle names never merge.
        self.assertFalse(middle_initial_same('Толстой А.Н.','Толстой Алексей Николаевич'))
        self.assertFalse(middle_initial_same('Стругацкий А.','Стругацкий Борис'))
        self.assertFalse(middle_initial_same('Sawyer J.','Robert J. Sawyer'))
        self.assertFalse(middle_initial_same('Philip K. Dick','Дик Филип Киндред',['Philip M. Dick']))
        self.assertFalse(middle_initial_same('Philip K. Dick','Дик Филип Киндред',['Philip Kevin Dick']))
        index=catalog_index(self.database((('Philip K. Dick',1),('Дик Филип Киндред',1),('Philip M. Dick',1))),ROOT)
        self.assertEqual(canonical_author('Дик Филип Киндред',['Дик Филип Киндред'],index,'')[0],'Дик Филип Киндред')
    def test_slip_is_narrow(self):
        self.assertTrue(slip_same('Terry Pratchet','Terry Pratchett'));self.assertTrue(slip_same('Pratchett Terry','Terry Pratchet'))
        self.assertFalse(slip_same('John Smith','John Smyth'))
        self.assertFalse(slip_same('Thimoty Zahn','Timothy Zahn'))
        self.assertFalse(slip_same('Terry Pratchet','Terri Pratchett'))
        self.assertFalse(slip_same('Pratchet','Pratchett'))


class BuldakovRulingTests(unittest.TestCase):
    """Ruling 1 names Булдаков: under a collection folder his plain credit is the narrator's."""
    TAGS={'album':'Тёмные Аллеи в Кино','title':'Тёмные Аллеи в Кино','artist':'Олег Булдаков'}
    def local(self,relative,readers=('Олег Булдаков',),tags=None):
        member={'path':ROOT+'\\'+relative.replace('/','\\'),'filename':Path(relative).name,'metadata':{'tags':tags or self.TAGS}}
        return agreement({'members':[member]},ROOT,[],frozenset(readers))
    def test_filed_under_collections_with_narrator_only(self):
        local=self.local('Сборники/Тёмные Аллеи/Олег Булдаков - Тёмные Аллеи в Кино.m4b')
        self.assertFalse(local['accepted']);self.assertTrue(local['route'],local['conflicts'])
        self.assertEqual(local['route']['narrators'],['Олег Булдаков']);self.assertEqual(local['route']['credit'],'Разные авторы')
    def test_not_without_reader_credit_or_outside_collections(self):
        self.assertIsNone(self.local('Сборники/Тёмные Аллеи/Олег Булдаков - Тёмные Аллеи в Кино.m4b',readers=())['route'])
        self.assertIsNone(self.local('Булдаков Олег/Олег Булдаков - Тёмные Аллеи в Кино.m4b')['route'])
        # R3-1 unchanged: a folder that names the reader holds.
        self.assertIsNone(self.local('Сборники/Олег Булдаков - Тёмные Аллеи/Тёмные Аллеи в Кино.m4b')['route'])
        # Only readers Sergei named: another reader with a plain credit stays a research hold.
        tags=dict(self.TAGS,artist='Роман Волков')
        self.assertIsNone(self.local('Сборники/Тёмные Аллеи/Роман Волков - Тёмные Аллеи в Кино.m4b',('Роман Волков',),tags)['route'])
    def test_a_real_author_beside_him_is_never_dropped(self):
        tags=dict(self.TAGS,album_artist='Стивен Кинг')
        local=self.local('Сборники/Тёмные Аллеи/Олег Булдаков - Тёмные Аллеи в Кино.m4b',tags=tags)
        self.assertIsNone(local['route'])


class SiblingYearTests(unittest.TestCase):
    def sibling(self,name,album):
        return {'path':ROOT+'\\Глуховской Дмитрий\\'+name,'filename':name,'tags':{'album':album}}
    def test_year_numbers_are_titles_not_parts(self):
        member={'path':ROOT+'\\Глуховской Дмитрий\\Метро 2033.m4b','filename':'Метро 2033.m4b','metadata':{'tags':{'album':'Метро 2033','artist':'Дмитрий Глуховский'}}}
        local=agreement({'members':[member]},ROOT,[self.sibling('Метро 2034.m4b','Метро 2034')],frozenset())
        self.assertFalse(any('beside it' in c['detail'] for c in local['conflicts']),local['conflicts'])
        member={'path':ROOT+'\\Stephen King\\Чужак 2.m4b','filename':'Чужак 2.m4b','metadata':{'tags':{'album':'Чужак 2','artist':'Стивен Кинг'}}}
        local=agreement({'members':[member]},ROOT,[self.sibling('Чужак 1.m4b','Чужак 1')],frozenset())
        self.assertTrue(any('beside it' in c['detail'] for c in local['conflicts']),local['conflicts'])


class VersionAndCheckpointTests(unittest.TestCase):
    def test_earlier_agreement_records_keep_validating(self):
        self.assertIn('local-agree-v3',KNOWN_AGREEMENT_VERSIONS);self.assertEqual(AGREEMENT_VERSION,'local-agree-v4')
        from public_research import PublicClient,PublicResearch
        from test_local_identity import candidate,SERGEI
        from standing_metadata import validate_policy
        temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(temp.cleanup);base=Path(temp.name)
        catalog=Catalog();catalog.closed={'api.fantlab.ru','www.wikidata.org'}
        client=PublicClient(base/'catalog.sqlite3',fetch=catalog.fetch)
        fixture=catalogue(client.database,base,candidate(base,SERGEI))
        result=PublicResearch(client,leads=[]).lookup(fixture,str(base))
        self.assertEqual(result['reasons'],[],result)
        facts=json.loads(json.dumps(result['metadata_facts']))
        for version in ('local-agree-v3','local-agree-v4'):
            facts['local_agreement']['version']=version;validate_policy(fixture,result['review'],facts)
        facts['local_agreement']['version']='local-agree-v2'
        with self.assertRaises(ValueError):validate_policy(fixture,result['review'],facts)
    def test_resumed_run_adds_new_candidates(self):
        from automatic_processing import AutomaticProcessing
        class Inventory:
            def candidates(self,label,limit):return {'rows':[{'id':i} for i in ('old-done','old-pending','new-split')]}
        fake=type('Fake',(),{'inventory':Inventory()})()
        checkpoint={'pending':['old-pending'],'done':['old-done'],'deferred':['old-deferred']}
        self.assertEqual(AutomaticProcessing._add_current_candidates(fake,checkpoint),1)
        self.assertEqual(checkpoint['pending'],['old-pending','new-split'])
        self.assertEqual(AutomaticProcessing._add_current_candidates(fake,checkpoint),0)

if __name__=='__main__':unittest.main()

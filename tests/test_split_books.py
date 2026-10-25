"""v0.15.0 split-book grouping and spelling fixes, with real library names as fixtures.
Private fixtures only: no network, no live catalog, no library access."""
import contextlib,json,shutil,sqlite3,subprocess,tempfile,threading,time,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
import groups
import split_books
from local_identity import (agreement,canonical_author,catalog_index,confirmed_spellings,middle_initial_same,slip_same,
                            KNOWN_AGREEMENT_VERSIONS,AGREEMENT_VERSION)
from scan_wait import finish_scan
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
        self.assertFalse(split_scopes(built),list(built))
        # Rulings 19/19a (2026-10-24): a whole-.m4b set may be one part-set candidate, whose chapters decide in research.
        self.assertTrue(all(len(g['members'])==1 or g.get('part_set') for g in built.values()),list(built))
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
        self.held(files,'differ from the track numbers')
    def test_protected_sibling_with_same_title_holds(self):
        files=[row('Stephen King/Чужак %d.m4b'%n,{'album':'Чужак','artist':'Стивен Кинг','track':'%d/3'%n}) for n in (1,2,3)]
        first=groups.member(files[0])
        protected=groups.build(files[:1])
        built=groups.build(files,protected)
        self.assertFalse(split_scopes(built))
        _,holds=split_books.plan([groups.member(r) for r in files[1:]],[first])
        self.assertTrue(any('separate candidates or protected' in r for h in holds for r in h['reasons']),holds)

class ReviewFindingTests(unittest.TestCase):
    """Senua's (C1, M1, M2, M6, M7) and Futaba's (F1) cases on 3346da1: separate works never join."""
    def assert_not_grouped(self,files):
        built=groups.build(files)
        self.assertFalse(split_scopes(built),list(built))
        # Rulings 19/19a (2026-10-24): never joined on its own; a whole-.m4b set may be one part set its chapters decide.
        self.assertTrue(all(len(g['members'])==1 or g.get('part_set') for g in built.values()),list(built))
    def test_c1_a_title_on_one_part_only_still_holds_hunger_games(self):
        # Live tags: album "The Hungar games", tracks 1/3..3/3, a title on book 2 only; names "The Hunger Games 1..3".
        files=[row('Suzanne Collins/Suzanne Collins/The Hunger Games %d.m4b'%n,dict({'album':'The Hungar games','artist':'Suzanne Collins','track':'%d/3'%n},**({'title':'Book 2 Cathing Fire'} if n==2 else {})))
               for n in (1,2,3)]
        self.assert_not_grouped(files)
    def test_c1_tim_miller_with_one_title_missing_holds(self):
        files=[row('Tim Miller/Тёмный экзорцист %d.m4b'%n,dict({'album':'Тёмный экзорцист','artist':'Тим Миллер','track':'%d/2'%n},**({'title':'Тёмный экзорцист Том I'} if n==1 else {})))
               for n in (1,2)]
        self.assert_not_grouped(files)
    def test_m1_albums_differing_only_in_brackets_hold(self):
        files=[row('Suzanne Collins/The Hunger Games %d.m4b'%n,{'album':'The Hunger Games (Book %d)'%n,'artist':'Suzanne Collins','track':'%d/3'%n}) for n in (1,2,3)]
        self.assert_not_grouped(files)
        files=[row('Стругацкие/Пикник на обочине %d.m4b'%n,{'album':'Пикник на обочине (%s)'%r,'artist':'Аркадий и Борис Стругацкие','track':'%d/2'%n}) for n,r in ((1,'Кузнецов'),(2,'Козий'))]
        self.assert_not_grouped(files)
    def test_m2_episode_cd_track_with_a_name_is_a_separate_work(self):
        for names in (['Эпизод 1. Скрытая угроза','Эпизод 2. Атака клонов'],['CD1 Хоббит','CD2 Властелин колец'],['Track 1 - Хоббит','Track 2 - Сильмариллион']):
            with self.subTest(names=names):
                files=[row('Shelf/%s.m4b'%name,{'album':'Собрание','artist':'Джон Толкин','track':'%d/2'%n}) for n,name in enumerate(names,1)]
                self.assert_not_grouped(files)
        files=[row('Shelf/Часть %d. %s.m4b'%(n,name),{'album':'Оно','artist':'Стивен Кинг','track':'%d/2'%n}) for n,name in ((1,'Тень прошлого'),(2,'Июнь 1958 года'))]
        self.assertTrue(split_scopes(groups.build(files)))
    def test_f1_numbers_that_are_part_of_titles_never_number_parts(self):
        cases=[('Метро 2033','Метро 2034','Метро'),('Fallout 3','Fallout 4','Fallout'),('Фантастика 2021','Фантастика 2022','Фантастика')]
        for first,second,album in cases:
            with self.subTest(album=album):
                files=[row('Shelf/%s.m4b'%name,{'album':album,'artist':'Дмитрий Глуховский','track':str(n)}) for n,name in ((1,first),(2,second))]
                self.assert_not_grouped(files)
        files=[row('Shelf/Area %d.m4b'%n,{'title':'Area %d'%n,'artist':'Matthew Reilly','track':str(t)}) for t,n in ((1,51),(2,52))]
        self.assert_not_grouped(files)
        # The same shape with real part numbers stays one book (positive control).
        files=[row('Shelf/Метро 2033 %d.m4b'%n,{'album':'Метро 2033','artist':'Дмитрий Глуховский','track':'%d/2'%n}) for n in (1,2)]
        self.assertTrue(split_scopes(groups.build(files)))
    def test_f1_end_to_end_metro_pair_is_not_approvable(self):
        from public_research import PublicClient,PublicResearch
        from test_local_identity import candidate
        temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(temp.cleanup);base=Path(temp.name)
        catalog=Catalog();catalog.closed={'api.fantlab.ru','www.wikidata.org','openlibrary.org','www.googleapis.com','itunes.apple.com'}
        client=PublicClient(base/'catalog.sqlite3',fetch=catalog.fetch)
        files=[('Глуховский Дмитрий/Метро 2033.m4b',{'album':'Метро','artist':'Дмитрий Глуховский','track':'1'}),
               ('Глуховский Дмитрий/Метро 2034.m4b',{'album':'Метро','artist':'Дмитрий Глуховский','track':'2'})]
        rows=[]
        for relative,tags in files:
            path=base/relative;metadata={'tags':tags,'probe':{'format':{'duration':'600'},'streams':[{'codec_type':'audio','codec_name':'aac','sample_rate':'44100','channels':1}]}}
            rows.append({'root':str(base),'path':str(path),'kind':'audiobook','size':10,'modified':10,'metadata':json.dumps(metadata,ensure_ascii=False),'error':'','missing':0})
        built=groups.build(rows)
        self.assertFalse(split_scopes(built))  # one part set at most (rulings 19/19a): research holds it, never joins it
        for group in built.values():
            fixture=catalogue(client.database,base,dict(group,fingerprint='private-fixture'))
            for other in built.values():catalogue(client.database,base,dict(other,fingerprint='private-fixture'))
            result=PublicResearch(client,leads=[]).lookup(rendered(json.loads(json.dumps(fixture))),str(base))
            self.assertTrue(result['reasons'],result.get('review'))
    def test_m6_zero_padded_part_numbers_are_parts(self):
        def single(name,album):
            return {'path':ROOT+'\\Дорога\\'+name,'filename':name,'metadata':{'tags':{'album':album,'artist':'Кормак Маккарти'}}}
        local=agreement({'members':[single('Дорога 0001.m4b','Дорога 0001')]},ROOT,[{'path':ROOT+'\\Дорога\\Дорога 0002.m4b','filename':'Дорога 0002.m4b','tags':{'album':'Дорога 0002'}}],frozenset())
        self.assertTrue(any('beside it' in c['detail'] for c in local['conflicts']),local['conflicts'])
    def test_m7_scope_collision_fails_closed(self):
        files=[row('Dan Simmons/Террор %d.m4b'%n,{'album':'Террор','artist':'Дэн Симмонс','track':'%d/2'%n}) for n in (1,2)]
        group=next(iter(groups.build(files).values()));protected={group['scope']:json.loads(json.dumps(group,ensure_ascii=False))}
        # The reviewed parts are retagged (another book key) and new files with the old title appear.
        retagged=[row('Dan Simmons/Террор %d.m4b'%n,{'album':'Террор. Новая редакция','artist':'Дэн Симмонс','track':'%d/2'%n}) for n in (1,2)]
        arrivals=[row('Dan Simmons/Террор новое %d.m4b'%n,{'album':'Террор','artist':'Дэн Симмонс','track':'%d/2'%n}) for n in (1,2)]
        built=groups.build(retagged+arrivals,protected)
        self.assertEqual(sorted(m['path'] for m in built[group['scope']]['members']),sorted(r['path'] for r in retagged))
        self.assertEqual(sum(len(g['members']) for g in built.values()),4)


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


def make_part(path,title,track,chapters=False,album='Чужак',artist='Стивен Кинг',total=2):
    ffmpeg=shutil.which('ffmpeg')
    args=[ffmpeg,'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=1']
    if chapters:
        meta=path.with_suffix('.txt');meta.write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=500\ntitle=A\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=500\nEND=1000\ntitle=B\n',encoding='utf-8')
        args+=['-f','ffmetadata','-i',str(meta),'-map','0:a','-map_chapters','1']
    args+=['-c:a','aac','-ar','44100','-ac','1','-metadata','album='+album,'-metadata','artist='+artist,'-metadata','title='+title,'-metadata','track='+('%d/%d'%(track,total) if total else str(track)),str(path)]
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
        self.inv=Inventory(self.base/'catalog.sqlite3',roots);self.inv.launch('Audiobooks');finish_scan(self.inv);self.service=MergeService(self.inv,self.base/'cache')
        self.addCleanup(self.temp.cleanup);self.addCleanup(self.service.close)
        def offline(url,*_):raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        self.client=PublicClient(self.inv.database,fetch=offline)
        rows=self.service.reviews.page()['rows']
        self.assertEqual(len(rows),1,[r['scope'] for r in rows]);self.row=rows[0];self.assertTrue(self.row.get('split_book'))
        from public_research import PublicResearch
        self.result=PublicResearch(self.client,leads=[]).lookup(self.row,str(self.audio))
        if not chapters:self.assertEqual(self.result['reasons'],[],self.result)
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
        self.assertTrue(all(not p.exists() for p in self.sources));self.assertEqual(self.service.cleanup.status(job_id)['recovery']['state'],'deleted')  # v0.16.8: deleted once verified
    def test_parts_with_their_own_chapters_are_held(self):
        self.build(chapters=True)
        # Rulings 19/19a (2026-10-24): the set's chapters decide. Chapters "A", "B" in each bare-numbered part settle
        # nothing: "Part of a bigger book", with the proposed order and Approve as one book; never joined on its own.
        self.assertEqual((self.result['part_set']['decision'],self.result['part_set']['basis']),('ask','unclear'))
        self.assertIn('One part of a bigger book',self.result['reasons'])
        with self.assertRaises(ValueError):self.service.approve_automatic(self.row,self.result,threading.Event(),self.client)
        # Admission refuses joining own chapters without that decision (an identity-only result), and re-files nothing.
        from public_research import PublicResearch
        bare=PublicResearch(self.client,leads=[])._lookup(self.row,str(self.audio))
        self.assertEqual(bare['reasons'],[],bare.get('reasons'))
        with self.assertRaises(ValueError) as raised:self.service.approve_automatic(self.row,bare,threading.Event(),self.client)
        self.assertIn('carry their own chapters',str(raised.exception))
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))
        self.assertEqual([len(r['members']) for r in self.service.reviews.page()['rows']],[2],'one candidate: nothing re-filed')
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


IMAJICA=[('1. Пятый Доминион. Главы 1-20','Книга 1. Пятый Доминион. Главы 1-20'),('2. Пятый Доминион. Главы 21-36','Книга 1. Пятый Доминион. Главы 21-36'),
         ('3. Примирение. Главы 37-48','Книга 2. Примирение. Главы 37-48'),('4. Примирение. Главы 49-62','Книга 2. Примирение. Главы 49-62')]
IMAJICA_FOLDER='Clive Barker/1290. Имаджика (Светлана Смелова)'

def part_rows(folder,album,artist,parts,total=None):
    total=total or len(parts)
    return [row('%s/%s.m4b'%(folder,stem),{'album':album,'artist':artist,'title':title,'composer':'Светлана Смелова','track':'%d/%d'%(n,total)},duration=36000.0)
            for n,stem,title in parts]

def siblings_of(rows,index):
    out=[]
    for i,r in enumerate(rows):
        if i!=index:
            tags={k.casefold():str(v) for k,v in json.loads(r['metadata'])['tags'].items()}
            out.append({'path':r['path'],'filename':Path(r['path']).name,'tags':tags})
    return out

def candidate_of(built,path):
    return rendered(next(g for g in built.values() if g['members'][0]['path']==path))


class PartBookTests(unittest.TestCase):
    """Sergei 2026-10-13: M4B parts with their own chapters are never joined; each part is its own book."""
    def test_imajica_parts_are_separate_books_named_from_evidence(self):
        rows=part_rows(IMAJICA_FOLDER,'Имаджика','Клайв Баркер',[(n,s,t) for n,(s,t) in enumerate(IMAJICA,1)])
        self.assertEqual([len(g['members']) for g in groups.build(rows).values()],[4],'one part set until its chapters are read (ruling 19)')
        built=groups.build(rows,volumes=frozenset(r['path'] for r in rows))  # recorded as separate volumes
        self.assertEqual(len(built),4);self.assertFalse(split_scopes(built))
        titles=[]
        for index,r in enumerate(rows):
            group=candidate_of(built,r['path'])
            local=agreement(group,ROOT,siblings_of(rows,index),frozenset())
            self.assertTrue(local['accepted'],local['conflicts'])
            self.assertEqual(local['part_book'],{'parts':4,'position':index+1,'set_title':'Имаджика','members':sorted(r['path'] for r in rows),'requires_own_chapters':True})
            self.assertEqual(local['series'],{'name':'Имаджика','number':str(index+1)})
            titles.append(local['fields']['title']['value'])
            work={'titles':[local['fields']['title']['value'],'Имаджика'],'author_aliases':['Клайв Баркер'],'identity_basis':'local_agreement','policy_version':'standing-17-v1','part_book':True}
            self.assertEqual(source_gate(group,work),[])
            # Positive control: without the part-book mark the set total "N/4" holds a single file.
            self.assertIn('Source membership uncertain',source_gate(group,dict(work,part_book=False)))
        self.assertEqual(titles,['Пятый Доминион. Главы 1-20','Пятый Доминион. Главы 21-36','Примирение. Главы 37-48','Примирение. Главы 49-62'])
    def test_no_parent_work_holds_the_whole_set(self):
        # Senua R2-C1: a part never goes out without its parent work. The folder does not repeat
        # the album "Сага об Элрике", so no part has a series and the whole set is held.
        parts=[(1,'01. Повелитель Хаоса','01. Повелитель Хаоса'),(2,'02. Элрик из Мелнибонэ','02. Элрик из Мелнибонэ')]
        rows=part_rows('Michael John Moorcock/Elric of Melniboné','Сага об Элрике','Майкл Муркок',parts)
        for index in (0,1):
            local=agreement(candidate_of(groups.build(rows,volumes=frozenset(r['path'] for r in rows)),rows[index]['path']),ROOT,siblings_of(rows,index),frozenset())
            self.assertFalse(local['accepted']);self.assertIn('parent work',local['fields']['title']['how'])
    def test_part_without_a_title_of_its_own_stays_held(self):
        parts=[(n,'Торадора! Том %d'%n,'Торадора! Том %d'%n) for n in (1,2,3)]
        rows=part_rows('Light Novels/Yuyuko Takemiya/Toradora!','Торадора!','Ююко Такэмия',parts)
        local=agreement(candidate_of(groups.build(rows,volumes=frozenset(r['path'] for r in rows)),rows[0]['path']),ROOT,siblings_of(rows,0),frozenset())
        self.assertFalse(local['accepted']);self.assertTrue(local['part_book'])
        self.assertIn('no title of its own',local['fields']['title']['how'])
    def test_incoherent_set_is_not_a_part_book(self):
        parts=[(n,s,t) for n,(s,t) in enumerate(IMAJICA,1) if n!=3]
        rows=part_rows(IMAJICA_FOLDER,'Имаджика','Клайв Баркер',parts,total=4)
        local=agreement(candidate_of(groups.build(rows),rows[0]['path']),ROOT,siblings_of(rows,0),frozenset())
        self.assertIsNone(local['part_book']);self.assertFalse(local['accepted'])
        self.assertTrue(any('beside it' in c['detail'] for c in local['conflicts']),local['conflicts'])
    def test_known_volumes_get_their_own_candidates(self):
        # Rulings 19/19a (2026-10-24): own chapters no longer split a set (its chapters decide); recorded volumes do.
        files=[row('Stephen King/Чужак %d.m4b'%n,{'album':'Чужак','artist':'Стивен Кинг','title':'Чужак %d'%n,'track':'%d/2'%n}) for n in (1,2)]
        self.assertTrue(split_scopes(groups.build(files)))
        self.assertTrue(split_scopes(groups.build(files,chaptered=frozenset(f['path'] for f in files))),'own chapters keep the set')
        built=groups.build(files,volumes=frozenset(f['path'] for f in files))
        self.assertFalse(split_scopes(built));self.assertEqual(len(built),2)
        self.assertTrue(all(s.endswith('\x1fVolume of a series') for s in built))
        _,holds=split_books.plan([groups.member(f) for f in files],(),frozenset([files[0]['path']]))
        self.assertTrue(any('own chapters' in r for h in holds for r in h['reasons']),holds)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg required')
class PartBookAdmissionTests(unittest.TestCase):
    """An Imajica-like folder: each chaptered part becomes its own verified M4B with its chapters kept."""
    def build(self,chapters=True):
        from scanner import Inventory
        from merge_service import MergeService
        from public_research import PublicClient
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.base=Path(self.temp.name);self.audio=self.base/'audio'
        folder=self.audio/'Clive Barker'/'1290. Имаджика (Светлана Смелова)';folder.mkdir(parents=True);self.sources=[]
        for n,(stem,title) in enumerate((('1. Пятый Доминион','Книга 1. Пятый Доминион'),('2. Примирение','Книга 2. Примирение')),1):
            own=chapters[n-1] if isinstance(chapters,tuple) else chapters
            source=folder/(stem+'.m4b');make_part(source,title,n,own,album='Имаджика',artist='Клайв Баркер');self.sources.append(source)
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots);self.inv.launch('Audiobooks');finish_scan(self.inv);self.service=MergeService(self.inv,self.base/'cache')
        self.addCleanup(self.temp.cleanup);self.addCleanup(self.service.close)
        def offline(url,*_):raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        self.client=PublicClient(self.inv.database,fetch=offline)
        # Rulings 19/19a (2026-10-24): the set is one candidate until its chapters are read; these parts are recorded as
        # separate volumes (as research records a volume set), so each is its own part book.
        rows=self.service.reviews.page()['rows'];self.assertEqual([len(r['members']) for r in rows],[2])
        from scanner import connect
        with connect(self.inv.database) as db:groups.record_volumes(db,str(self.audio),rows[0]['members'],'fixture: separate volumes')
    def research(self,source):
        from public_research import PublicResearch
        rows=self.service.reviews.page()['rows']
        self.assertEqual(len(rows),2,[r['scope'] for r in rows]);self.assertFalse(any(r.get('split_book') for r in rows))
        row=next(r for r in rows if r['members'][0]['path']==str(source))
        return row,PublicResearch(self.client,leads=[]).lookup(row,str(self.audio))
    def wait(self):
        limit=time.monotonic()+60
        while self.service.state()['state'] in ('Running','Pausing') or self.service.state().get('queued') or self.service.state().get('cleanup_active'):
            if time.monotonic()>limit:self.fail('Private part-book job exceeded 60s')
            time.sleep(.05)
    def test_each_chaptered_part_becomes_its_own_m4b_nothing_joined(self):
        self.build()
        names=[]
        for source in self.sources:
            row,result=self.research(source)
            self.assertEqual(result['reasons'],[],result);self.assertTrue(result['local_agreement']['part_book'])
            self.service.approve_automatic(row,result,threading.Event(),self.client);self.wait()
        jobs=self.service.jobs.status()['jobs'];self.assertEqual(len(jobs),2)
        for job in jobs:
            self.assertEqual(job['state'],'completed',job);self.assertEqual(len(job['manifest']['sources']),1)
            validation=job['output']['validation'];self.assertEqual(validation['encoding']['mode'],'copy')
            self.assertEqual([c['title'] for c in validation['preserved_source_chapters']],['A','B'])
            names.append(Path(job['output']['final_path']).name)
        self.assertEqual(sorted(names),['Имаджика - 1 - Пятый Доминион - Barker Clive.m4b','Имаджика - 2 - Примирение - Barker Clive.m4b'])
        self.assertTrue(all(not p.exists() for p in self.sources))
    def test_a_set_with_one_part_lacking_chapters_is_held_whole(self):
        # Senua R2-C1: part 1 has its own chapters, part 2 does not: nothing is published piecemeal.
        self.build(chapters=(True,False))
        row,result=self.research(self.sources[0])
        self.assertEqual(result['reasons'],[],result)
        with self.assertRaises(ValueError) as raised:self.service.approve_automatic(row,result,threading.Event(),self.client)
        self.assertIn('whole set is held',str(raised.exception))
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))
    def test_part_without_its_own_chapters_stays_held(self):
        self.build(chapters=False)
        row,result=self.research(self.sources[0])
        self.assertEqual(result['reasons'],[],result)
        with self.assertRaises(ValueError) as raised:self.service.approve_automatic(row,result,threading.Event(),self.client)
        self.assertIn('without its own chapters',str(raised.exception))
        self.assertEqual(self.service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in self.sources))


ONO=[('Часть 1. ТЕНЬ ПРОШЛОГО.','Часть 1. ТЕНЬ ПРОШЛОГО.',1),('Часть 2. ИЮНЬ 1958 ГОДА. 1','Часть 2. ИЮНЬ 1958 ГОДА. 1',2),('Часть 2 ИЮНЬ 1958 ГОДА. 2','Часть 2. ИЮНЬ 1958 ГОДА. 2',3),
     ('Часть 3. ВЗРОСЛЫЕ.','Часть 3. ВЗРОСЛЫЕ.',4),('Часть 4. ИЮЛЬ 1958 ГОДА. 1','Часть 4. ИЮЛЬ 1958 ГОДА. 1',5),('Часть 4. ИЮЛЬ 1958 ГОДА. 2','Часть 4. ИЮЛЬ 1958 ГОДА. 2',6),
     ('Часть 5. РИТУАЛ ЧУДЬ.','Часть 5. РИТУАЛ ЧУДЬ.',7)]
MERZOST=[('Часть 1. Альпинисты','Часть 1. Альпинисты',1),('Часть 2. Гора','Часть 2. Гора',2),('Часть 3. Мерзость','Часть 3. Мерзость',3)]


class PartBookRound2Tests(unittest.TestCase):
    """Senua round 2 (b756301): every part keeps its parent work, a set is never filed piecemeal,
    and only whole .m4b parts are re-filed or become part books (live tags of Оно and Мерзость)."""
    def chaptered_set(self,folder,album,artist,parts):
        files=[row('%s/%s.m4b'%(folder,stem),{'album':album,'artist':artist,'album_artist':artist,'title':title,'track':'%d/%d'%(n,len(parts))},duration=36000.0) for stem,title,n in parts]
        return files,groups.build(files,chaptered=frozenset(f['path'] for f in files))
    # Ruling 19a (Sergei 2026-10-24) replaces "each chaptered part is its own book" (2026-10-13) for parts that each carry an
    # explicit part marker ("Часть 2"): they are one book, joined keeping every part's chapters (tests/test_m4b_join.py).
    def test_r2_c1_ono_explicitly_marked_parts_are_one_book(self):
        files,built=self.chaptered_set('Stephen King/Оно','Оно','Кинг Стивен',ONO)
        self.assertEqual(len(built),1);group=next(iter(built.values()))
        self.assertTrue(group['split_book']);self.assertEqual([m['path'] for m in group['members']],[f['path'] for f in files],'in part order')
        local=agreement(rendered(group),ROOT,[],frozenset())
        self.assertTrue(local['accepted'],local['conflicts']);self.assertEqual(local['fields']['title']['value'],'Оно')
    def test_r2_c1_merzost_explicitly_marked_parts_are_one_book(self):
        files,built=self.chaptered_set('Dan Simmons/Мерзость','Мерзость','Симмонс Дэн',MERZOST)
        self.assertEqual([len(g['members']) for g in built.values()],[3]);self.assertTrue(next(iter(built.values()))['split_book'])
    def test_r2_m1_m4a_is_never_a_part_book(self):
        rows=[row('%s/%s.m4a'%(IMAJICA_FOLDER,s),{'album':'Имаджика','artist':'Клайв Баркер','title':t,'track':'%d/4'%n}) for n,(s,t) in enumerate(IMAJICA,1)]
        for index,f in enumerate(rows):
            group=rendered(dict(groups.build([f])[next(iter(groups.build([f])))]))
            local=agreement(group,ROOT,siblings_of(rows,index),frozenset())
            self.assertIsNone(local['part_book']);self.assertFalse(local['accepted'])
    def test_r2_m1_m4a_group_never_loses_a_member(self):
        rows=[row('Stephen King/Чужак/%02d.m4a'%n,{'album':'Чужак','artist':'Стивен Кинг','track':str(n)}) for n in (1,2,3)]
        built=groups.build(rows,chaptered=frozenset([rows[2]['path']]))
        self.assertEqual(len(built),1);self.assertEqual(len(next(iter(built.values()))['members']),3)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg required')
class M4AGroupAdmissionTests(unittest.TestCase):
    """Senua R2-M1: a multi-file .m4a group with a chaptered file is held together, never re-filed."""
    def test_chaptered_m4a_file_keeps_its_group_whole(self):
        from scanner import Inventory
        from merge_service import MergeService
        from public_research import PublicClient,PublicResearch
        temp=tempfile.TemporaryDirectory(dir=AREA);base=Path(temp.name);audio=base/'audio'
        folder=audio/'Stephen King'/'Чужак';folder.mkdir(parents=True);sources=[]
        for n in (1,2,3):
            source=folder/('%02d.m4a'%n);make_part(source,'Глава %d'%n,n,n==3,total=0);sources.append(source)
        roots={'Audiobooks':str(audio),'Podcasts':str(base/'podcasts'),'Ebooks':str(base/'ebooks')}
        inv=Inventory(base/'catalog.sqlite3',roots);inv.launch('Audiobooks');finish_scan(inv);service=MergeService(inv,base/'cache')
        self.addCleanup(temp.cleanup);self.addCleanup(service.close)
        def offline(url,*_):raise urllib.error.HTTPError(url,503,'private fixture',{},None)
        client=PublicClient(inv.database,fetch=offline)
        rows=service.reviews.page()['rows'];self.assertEqual([len(r['members']) for r in rows],[3])
        result=PublicResearch(client,leads=[]).lookup(rows[0],str(audio))
        self.assertEqual(result['reasons'],[],result)
        with self.assertRaises(ValueError) as raised:service.approve_automatic(rows[0],result,threading.Event(),client)
        self.assertIn('joining them would drop those chapters',str(raised.exception))
        with contextlib.closing(sqlite3.connect(inv.database)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM part_chapters').fetchone()[0],0)
        self.assertEqual([len(r['members']) for r in service.reviews.page()['rows']],[3])
        self.assertEqual(service.jobs.status()['jobs'],[]);self.assertTrue(all(p.exists() for p in sources))


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
            for n,item in enumerate(evidence):
                value,url,facts=item[:3];state=item[3] if len(item)>3 else 'Queued';seen=item[4] if len(item)>4 else ()
                result={'metadata_facts':{'authors':[value]} if facts else None,'evidence':[{'field':'authors','cited_value':value,'source_url':url}],
                        'local_clues':[{'kind':'embedded','field':'artist','value':v} for v in seen]}
                db.execute("INSERT INTO automatic_candidates VALUES(?,1,'f',?,?,NULL,?,'v')",('c%d'%n,state,json.dumps(result),'2026-10-13T00:00:%02d'%n))
            db.commit()
        return path
    PRATCHETT=(('Terry Pratchet',20),('Terry Pratchett',5),('Терри Пратчетт',11))
    def test_confirmed_spelling_wins_over_majority_typo(self):
        url='https://openlibrary.org/works/OL453749W'
        index=catalog_index(self.database(self.PRATCHETT,[('Terry Pratchett',url,True,'Queued',['Terry Pratchet'])]),ROOT)
        self.assertEqual(index['confirmed'],{'Terry Pratchett':{'urls':[url],'seen':['terry pratchet']}})
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
    def test_unverified_research_never_confirms(self):
        # Senua M5: the live Pratchett confirmations came from research still waiting with "Author and
        # work not independently verified"; such records never confirm a spelling.
        url='https://openlibrary.org/works/OL453749W'
        for state in ('Waiting for source','Held','Researching'):
            with self.subTest(state=state):
                index=catalog_index(self.database(self.PRATCHETT,[('Terry Pratchett',url,True,state,['Terry Pratchet'])]),ROOT)
                self.assertEqual(index['confirmed'],{});self.assertEqual(canonical_author('Терри Пратчетт',['Терри Пратчетт'],index,'')[0],'Pratchet Terry')
    def test_slip_needs_the_confirming_record_to_have_seen_it(self):
        url='https://openlibrary.org/works/OL453749W'
        index=catalog_index(self.database(self.PRATCHETT,[('Terry Pratchett',url,True,'Queued',['Terry Pratchett'])]),ROOT)
        # Same person by the name rules: adopted. A one-letter slip the record never saw: not adopted.
        self.assertEqual(canonical_author('Терри Пратчетт',['Терри Пратчетт'],index,'')[0],'Pratchett Terry')
        self.assertEqual(canonical_author('Terry Pratchet',['Terry Pratchet'],index,'')[0],'Pratchet Terry')
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
        self.assertFalse(middle_initial_same('M. Mary Smith','Margaret Mary Smith'))
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


# 0.21.3: this module's admission fixtures publish inside their own library; see sorted_fixture (Sergei's
# deletion rule). Without it the two conversion-then-cleanup cases kept their sources and failed.
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()

if __name__=='__main__':unittest.main()

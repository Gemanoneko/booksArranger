"""Edit names (Sergei 2026-10-26; Judy 0.22.2 section 1): every book row's title, author, series, number, universe and
collection can be corrected; the correction is Sergei's ("Entered by you") and lasting; a name fix reaches the books that
read the same text under the same author or folder, never another author's; Save never converts, moves or queues; a job
planned under other names never starts. The «Пртоколы SCP» books are the worked example.

Store tests use a private catalog file; the engine tests use real private audio through the production policy, with a
separate Sorted folder and offline research. No network, no library access."""
import hashlib,json,tempfile,threading,time,unittest,uuid
from pathlib import Path

import entered_names
from scanner import connect,Inventory
from scan_wait import finish_scan
from test_approve_as_is import ApproveFixture,tone
import test_automatic_processing as automatic_fixtures


def book(*paths,clue='',tags=None):
    return {'id':str(uuid.uuid4()),'title_clue':clue,'members':[{'path':p,'metadata':{'tags':dict(tags or {})}} for p in paths]}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=automatic_fixtures.AREA);self.addCleanup(self.temp.cleanup)
        self.db=str(Path(self.temp.name)/'catalog.sqlite3')
        with connect(self.db) as db:db.execute('CREATE TABLE IF NOT EXISTS probe(x)')
        self.safe=[book('Z:\\SCP\\Пртоколы SCP. Сейф №%d.m4b'%n,clue='Пртоколы SCP. Сейф №%d'%n) for n in (1,2,3)]
        self.other=book('Z:\\Иван Петров\\Пртоколы SCP. Сейф №1.m4b',clue='Пртоколы SCP. Сейф №1')
        self.scope=entered_names.scope_of(self.safe[0],'Разные авторы',collection=True)
    def read(self,n):return {'title':'Пртоколы SCP. Сейф №%d'%n,'author':'Разные авторы','series':'','number':'','universe':'','collection':True}

    def test_a_one_word_respelling_reaches_the_folders_books_and_never_another_author(self):
        entries=entered_names.plan(self.safe[0],{'title':'Протоколы SCP. Сейф №1'},self.read(1),self.scope)
        self.assertIn(('fix','title','Протоколы','Пртоколы',self.scope,''),entries,'remembered as the word')
        others=[(self.safe[n-1],self.read(n),self.scope) for n in (2,3)]+[(self.other,self.read(1),entered_names.scope_of(self.other,'Иван Петров'))]
        self.assertEqual([r['id'] for r in entered_names.reach(entries,others)],[self.safe[1]['id'],self.safe[2]['id']],'Applies to 3 books; the control is not reached')
        entered_names.save(self.db,self.safe[0],entries)
        self.assertEqual(entered_names.effective(self.db,self.safe[2],self.read(3),self.scope)['title']['value'],'Протоколы SCP. Сейф №3')
        self.assertEqual(entered_names.effective(self.db,self.other,self.read(1),entered_names.scope_of(self.other,'Иван Петров')),{},'a title is never fixed across authors')

    def test_newest_wins_and_forget_takes_the_whole_press_back(self):
        entered_names.save(self.db,self.safe[0],entered_names.plan(self.safe[0],{'title':'Протоколы SCP. Сейф №1'},self.read(1),self.scope))
        now=entered_names.effective(self.db,self.safe[0],self.read(1),self.scope)
        entered_names.save(self.db,self.safe[0],entered_names.plan(self.safe[0],{'title':'Сейф №1'},self.read(1),self.scope,now))
        now=entered_names.effective(self.db,self.safe[0],self.read(1),self.scope)
        self.assertEqual(now['title']['value'],'Сейф №1','the newer entry wins')
        self.assertEqual(entered_names.effective(self.db,self.safe[1],self.read(2),self.scope)['title']['value'],'Протоколы SCP. Сейф №2','the first press\'s word fix still reaches the others')
        remembered=entered_names.remembered(self.db,self.safe[0],self.read(1),self.scope)
        self.assertEqual([(r['field'],r['from'],r['to']) for r in remembered],[('title','Пртоколы SCP. Сейф №1','Сейф №1')])
        taken=entered_names.forget(self.db,remembered[0]['id'])
        self.assertEqual(len(taken),2,'the book\'s value and the fix saved with it')
        self.assertEqual(entered_names.effective(self.db,self.safe[0],self.read(1),self.scope)['title']['value'],'Протоколы SCP. Сейф №1','the earlier press is in force again')
        self.assertEqual(entered_names.forget(self.db,remembered[0]['id']),[],'already taken back')

    def test_a_value_set_back_to_what_the_files_say_takes_its_entry_back(self):
        entered_names.save(self.db,self.safe[0],entered_names.plan(self.safe[0],{'series':'Протоколы SCP','number':'1'},self.read(1),self.scope))
        now=entered_names.effective(self.db,self.safe[0],self.read(1),self.scope)
        self.assertEqual(entered_names.entered(entered_names.book_values(self.db,self.safe[0])),['series','number'])
        entries=entered_names.plan(self.safe[0],{'series':'','number':''},self.read(1),self.scope,now)
        # M2 (Senua 0.22.2): a 'files' entry per field (no correction), never a forget of the newest entry only.
        self.assertEqual([(e[0],e[1],e[4]) for e in entries],[('book','series',entered_names.FILES),('book','number',entered_names.FILES)])
        entered_names.save(self.db,self.safe[0],entries)
        self.assertEqual(entered_names.book_values(self.db,self.safe[0]),{},'nothing stays "Entered by you"')
        self.assertEqual(entered_names.effective(self.db,self.safe[0],self.read(1),self.scope),{},'the files\' values are in force')
        self.assertEqual(entered_names.plan(self.safe[0],{'series':'','title':'Пртоколы SCP. Сейф №1'},self.read(1),self.scope),[],'unchanged values write nothing')

    def test_m2_typing_the_files_own_title_after_two_corrections_brings_no_older_one_back(self):
        # Senua's 0.22.2 review, M2: titles "A", then "B", then the files' own "Orig" left "A" in force.
        books=[book('Z:\\Иван Петров\\%s\\Orig.m4b'%folder,clue='Orig') for folder in ('one','two')]
        scope=entered_names.scope_of(books[0],'Петров Иван')
        read={'title':'Orig','author':'Петров Иван','series':'','number':'','universe':'','collection':False}
        def press(title):
            now=entered_names.effective(self.db,books[0],read,scope)
            entries=entered_names.plan(books[0],{'title':title},read,scope,now)
            entered_names.save(self.db,books[0],entries)
            return entries
        press('A');press('B')
        self.assertEqual(entered_names.effective(self.db,books[0],read,scope)['title']['value'],'B','positive control: the newer correction wins')
        press('Orig')
        self.assertNotIn('title',entered_names.effective(self.db,books[0],read,scope),'no correction for this book: neither A nor B')
        self.assertEqual(entered_names.book_values(self.db,books[0]),{},'nothing "Entered by you"')
        self.assertEqual(entered_names.remembered(self.db,books[0],read,scope),[],'nothing listed to Forget')
        self.assertEqual(entered_names.effective(self.db,books[1],read,scope)['title']['value'],'B','press B\'s fix still reaches the other book (Forget takes it back there)')
        press('C')
        self.assertEqual(entered_names.effective(self.db,books[0],read,scope)['title']['value'],'C','a new correction is in force again')
        entered_names.forget(self.db,entered_names.remembered(self.db,books[0],read,scope)[0]['id'])
        self.assertNotIn('title',entered_names.effective(self.db,books[0],read,scope),'Forget of C goes back to no correction, not to A or B')

    def test_m1_a_whole_value_fix_reaches_only_the_same_text_with_the_same_digits(self):
        # Senua's 0.22.2 review, M1: the comparison dropped digits, so correcting King's "01" also renamed «1408», and
        # "Книга 1" also "Книга 12".
        def case(author,folder,title):
            row=book('Z:\\%s\\%s\\%s.m4b'%(author,folder,title),clue=title)
            return row,{'title':title,'author':author,'series':'','number':'','universe':'','collection':False}
        for author,source,fixed,others,reached in (('King Stephen','01','Misery',['1408','11.22.63'],['01']),
                                                     ('Петров Иван','Книга 1','Первая книга',['Книга 12','Книга 2','Книга'],['книга  1'])):
            with self.subTest(source=source):
                first,read=case(author,'a',source)
                scope=entered_names.scope_of(first,author)
                entries=entered_names.plan(first,{'title':fixed},read,scope)
                self.assertIn(('fix','title',fixed,source,scope,''),entries,'a whole-value fix')
                rows=[case(author,'b%d'%n,title) for n,title in enumerate(others+reached)]
                near=[(row,read,scope) for row,read in rows]
                reach=entered_names.reach(entries,near)
                self.assertEqual([r['title_clue'] for r in reach],reached,'"Applies to %d books": the same text only'%(1+len(reached)))
                entered_names.save(self.db,first,entries)
                for (row,read) in rows:
                    value=entered_names.effective(self.db,row,read,scope).get('title',{}).get('value')
                    self.assertEqual(value,fixed if read['title'] in reached else None,read['title'])
        # Two fixes of two numbers under one author are two fixes (they shared one slot when the digits were dropped).
        king=entered_names.scope_of(book('Z:\\King Stephen\\x.m4b'),'King Stephen')
        room,read=case('King Stephen','c','1408')
        entered_names.save(self.db,room,entered_names.plan(room,{'title':'1408 (Комната)'},read,king))
        other,read01=case('King Stephen','d','01')
        self.assertEqual(entered_names.effective(self.db,other,read01,king)['title']['value'],'Misery','the "01" fix is still in force')
        # A word fix never changes a number.
        self.assertIsNone(entered_names._word_fix('Том1 Начало','Том2 Начало'))
        self.assertEqual(entered_names._word_fix('Пртоколы SCP','Протоколы SCP'),('Пртоколы','Протоколы'),'control')

    def test_series_and_number_go_together_and_a_title_is_needed(self):
        for values,sentence in (({'series':'Протоколы SCP'},'Type the number in the series, or clear the series.'),({'number':'1'},'Type the series name, or clear the number.'),
                                ({'series':'Протоколы SCP','number':''},'Type the number in the series, or clear the series.'),({'title':'  '},'Type a title first.')):
            with self.assertRaises(ValueError) as refused:entered_names.check(values)
            self.assertEqual(str(refused.exception),sentence)
        entered_names.check({'series':'Протоколы SCP','number':'1','collection':True})
        with self.assertRaises(ValueError):entered_names.check({'collection':'yes'})

    def test_the_names_stamp_follows_saves_and_forgets_and_is_none_without_entries(self):
        self.assertEqual(entered_names.digest_for(self.db,self.safe[1]),entered_names.NONE)
        entered_names.save(self.db,self.safe[0],entered_names.plan(self.safe[0],{'title':'Протоколы SCP. Сейф №1'},self.read(1),self.scope))
        first=entered_names.digest_for(self.db,self.safe[1])
        self.assertNotEqual(first,entered_names.NONE,'the fix may reach Сейф №2 (its title holds the old word)')
        self.assertEqual(entered_names.digest_for(self.db,book('Z:\\Elsewhere\\Другая книга.m4b',clue='Другая книга')),entered_names.NONE,'a book the fix cannot reach')
        remembered=entered_names.remembered(self.db,self.safe[0],self.read(1),self.scope)
        entered_names.forget(self.db,remembered[0]['id'])
        self.assertEqual(entered_names.digest_for(self.db,self.safe[1]),entered_names.NONE)
        with connect(self.db) as db:
            with self.assertRaises(Exception):db.execute('DELETE FROM names_entries')
            with self.assertRaises(Exception):db.execute("UPDATE names_entries SET value='x'")


class QueueClaimTests(unittest.TestCase):
    """AudioJobs' claim check (Judy 1.4: after a Save no job starts under the old names)."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=automatic_fixtures.AREA);self.addCleanup(self.temp.cleanup)
    def queue(self,seen):
        from audio_jobs import AudioJobs
        def runner(job,stop,checkpoint):
            seen.append(job['job_id'])
            record={'job_id':job['job_id'],'final_path':'fixture.m4b','owned_temp':'fixture.partial','sha256':'b'*64,'size':1,'validation':{'passed':True}}
            checkpoint('publishing',record);return record
        return AudioJobs(Path(self.temp.name)/'db.sqlite3',runner,lambda m:True,lambda r:True)
    @staticmethod
    def manifest():
        from encoding_policy import PROFILE
        return {'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'sources':[{'sha256':'a'*64,'fingerprint':{}}],'metadata':{},
                'destination':'fixture','profile':PROFILE,'evidence':{},'cover':{}}
    def finish(self,queue):
        queue.resume();limit=time.monotonic()+10
        while queue._thread and queue._thread.is_alive():
            if time.monotonic()>limit:self.fail('queue did not finish')
            time.sleep(.02)

    def test_a_job_planned_under_other_names_never_starts_and_is_replanned(self):
        seen=[];queue=self.queue(seen);stale,fresh=self.manifest(),self.manifest()
        queue.enqueue(stale);queue.enqueue(fresh)
        replanned=[]
        def replan(row):
            replanned.append(row['job_id'])
            with queue._db() as db:db.execute("UPDATE audio_jobs SET state='needs attention',reason='set aside' WHERE job_id=?",(row['job_id'],))
        queue.names_stamp=lambda:(1,'');queue.names_stale=lambda row:row['job_id']==stale['job_id'];queue.names_replan=replan
        self.finish(queue)
        self.assertEqual(seen,[fresh['job_id']],'the stale job never reached the runner');self.assertEqual(replanned,[stale['job_id']])

    def test_without_the_hooks_every_job_runs_as_before(self):
        seen=[];queue=self.queue(seen);first,second=self.manifest(),self.manifest()
        queue.enqueue(first);queue.enqueue(second);self.finish(queue)
        self.assertEqual(seen,[first['job_id'],second['job_id']])

    def test_a_save_between_the_check_and_the_claim_is_seen(self):
        seen=[];queue=self.queue(seen);job=self.manifest();queue.enqueue(job)
        stamp={'n':0};checks=[]
        def stale(row):
            checks.append(stamp['n'])
            if len(checks)==1:stamp['n']+=1  # a Save lands while the first check reads: the claim must check again
            return stamp['n']>=1 and len(checks)>1
        queue.names_stamp=lambda:stamp['n'];queue.names_stale=stale
        queue.names_replan=lambda row:queue._update(row['job_id'],state='needs attention',reason='set aside')
        self.finish(queue)
        self.assertEqual(seen,[],'checked again under the lock, found stale, never started');self.assertEqual(len(checks),2)

    def test_a_replan_that_fails_stops_the_job_with_its_line_and_nothing_runs(self):
        seen=[];queue=self.queue(seen);job=self.manifest();queue.enqueue(job)
        def broken(row):raise RuntimeError('catalog busy')
        queue.names_stamp=lambda:(1,'');queue.names_stale=lambda row:True;queue.names_replan=broken
        self.finish(queue)
        row=queue.status()['jobs'][0]
        self.assertEqual(seen,[]);self.assertEqual((row['state'],row['reason']),('needs attention',queue.NAMES_CHANGED))

    def test_the_claim_is_held_for_the_attempt_and_released_after(self):
        seen=[];held=[]
        queue=self.queue(seen);job=self.manifest();queue.enqueue(job)
        queue.names_stamp=lambda:(0,'');queue.names_stale=lambda row:False
        queue.before_attempt=lambda row:held.append(queue.claimed(row['job_id']))
        self.finish(queue)
        self.assertEqual(held,[True],'a Save during the attempt sees the claim (refused: converting)');self.assertFalse(queue.claimed(job['job_id']))


class EditNamesTests(ApproveFixture):
    """The «Пртоколы SCP» books: three in one folder, credited "Сборник" (a collection), and a control book by another
    author with the same misspelled title."""
    def scp(self):
        for n in (1,2,3):
            tone(self.audio/'SCP'/('Пртоколы SCP. Сейф №%d.mp3'%n),self.cover,title='Пртоколы SCP. Сейф №%d'%n,album='Пртоколы SCP. Сейф №%d'%n,artist='Сборник')
        tone(self.audio/'Иван Петров'/'Пртоколы SCP. Сейф №1.mp3',self.cover,title='Пртоколы SCP. Сейф №1',album='Пртоколы SCP. Сейф №1',artist='Иван Петров')
        rows=self.start()
        self.rows={('control' if 'Иван Петров' in r['members'][0]['path'] else r['members'][0]['path'][-5]):r for r in rows}
        return self.rows
    def row(self,key):
        current=self.service.reviews.page()['rows']
        found=[r for r in current if ('control' if 'Иван Петров' in r['members'][0]['path'] else r['members'][0]['path'][-5])==key]
        return found[0]
    def preview(self,key,**kw):
        row=self.row(key);return self.service.approval_preview(row['id'],row['revision'],**kw)
    def digest(self,paths):
        return {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}

    def test_the_editor_reads_what_the_files_say_with_the_place_and_no_job(self):
        self.scp();row=self.row('1')
        editor=self.service.names_editor(row['id'],row['revision'])
        fields={name:value['proposal'] for name,value in editor['fields'].items()}
        self.assertEqual(fields,{'title':'Пртоколы SCP. Сейф №1','author':'Разные авторы','series':'','number':'','universe':'','collection':True})
        self.assertEqual((editor['job'],editor['remembered'],editor['entered'],editor['applies']),('none',[],[],1))
        self.assertEqual(editor['destination']['path'],str(Path('Сборники')/'Пртоколы SCP. Сейф №1 - Разные авторы.m4b'),'positive control: filed as a collection today')
        self.assertEqual(editor['place'],{'universe':'','series':'','number':'','collection':True})

    def test_applies_to_counts_the_folders_books_and_a_save_fixes_them_but_never_the_other_authors(self):
        self.scp()
        self.assertEqual(self.preview('1',title='Протоколы SCP. Сейф №1',names={})['applies'],3,'Applies to 3 books.')
        row=self.row('1')
        saved=self.service.names_save(row['id'],row['revision'],{'title':'Протоколы SCP. Сейф №1'})
        self.assertEqual((saved['outcome'],saved['applies'],saved['entered']),('saved',3,['title']))
        self.assertEqual(self.preview('2')['title'],'Протоколы SCP. Сейф №2','the fix reached the folder\'s other books')
        self.assertEqual(self.preview('3')['path'],str(Path('Сборники')/'Протоколы SCP. Сейф №3 - Разные авторы.m4b'))
        self.assertEqual(self.preview('control')['title'],'Пртоколы SCP. Сейф №1','a title is never fixed across authors')

    def test_m1_applies_to_counts_only_the_books_with_the_same_digits(self):
        # Senua's 0.22.2 review, M1, through the engine's own count (the editor's "Applies to n books"): «Рассказ 12» holds
        # the text «Рассказ 1» (so the catalog prefilter keeps it) and the same letters, but it is another book.
        for folder,title in (('Рассказ 1','Рассказ 1'),('Рассказ 12','Рассказ 12'),('Рассказ 1 (другое издание)','Рассказ 1')):
            tone(self.audio/'Глуховский Дмитрий'/folder/(title+'.mp3'),self.cover,title=title,album=title,artist='Дмитрий Глуховский')
        rows=self.start()
        titles=lambda:{r['members'][0]['path'].split('\\')[-2]:self.service.approval_preview(r['id'],r['revision'])['title'] for r in self.service.reviews.page()['rows']}
        self.assertEqual(titles(),{'Рассказ 1':'Рассказ 1','Рассказ 1 (другое издание)':'Рассказ 1','Рассказ 12':'Рассказ 12'},'positive control: the titles read')
        first=next(r for r in rows if r['members'][0]['path'].endswith('Рассказ 1\\Рассказ 1.mp3'))
        preview=self.service.approval_preview(first['id'],first['revision'],title='Первый рассказ',names={})
        self.assertEqual(preview['applies'],2,'this book and the other edition of the same title, never «Рассказ 12»')
        saved=self.service.names_save(first['id'],first['revision'],{'title':'Первый рассказ'})
        self.assertEqual(saved['applies'],2)
        self.assertEqual(titles(),{'Рассказ 1':'Первый рассказ','Рассказ 1 (другое издание)':'Первый рассказ','Рассказ 12':'Рассказ 12'})

    def test_save_records_and_never_converts_moves_or_queues(self):
        self.scp();row=self.row('1');sources=[m['path'] for r in self.rows.values() for m in r['members']];before=self.digest(sources)
        self.service.names_save(row['id'],row['revision'],{'title':'Сейф №1','series':'Протоколы SCP','number':'1'})
        time.sleep(.3)
        self.assertEqual(self.service.jobs.status()['jobs'],[],'no job');self.assertEqual(self.digest(sources),before,'sources unchanged')
        self.assertEqual([p for p in self.sorted.rglob('*') if p.is_file()],[],'nothing in Sorted')

    def test_a_collection_in_its_series_files_under_the_series_folder_and_the_row_carries_place_and_entered(self):
        self.scp();row=self.row('1')
        self.service.automatic._record(row,'Held',dict(self.research(row),reasons=['fixture hold']))  # researched: a collection
        self.service.names_save(row['id'],row['revision'],{'title':'Сейф №1','series':'Протоколы SCP','number':'1'})
        self.assertEqual(self.preview('1')['path'],str(Path('Сборники')/'Протоколы SCP'/'Протоколы SCP - 1 - Сейф №1 - Разные авторы.m4b'))
        listed=self.row('1')
        self.assertEqual(listed['place'],{'universe':'','series':'Протоколы SCP','number':'1','collection':True})
        self.assertEqual(listed['entered'],['title','series','number'])
        editor=self.service.names_editor(listed['id'],listed['revision'])
        self.assertIn('Протоколы SCP',editor['series'],'the pick-list offers the series once saved')
        self.assertEqual(self.row('2')['entered'],[],'the other books carry no entry of their own')

    def test_the_names_survive_a_new_scan_and_forget_restores_them(self):
        self.scp();row=self.row('1')
        self.service.names_save(row['id'],row['revision'],{'title':'Сейф №1','series':'Протоколы SCP','number':'1'})
        self.inv.launch('Audiobooks',resume=False);finish_scan(self.inv)
        self.assertEqual(self.preview('1')['path'],str(Path('Сборники')/'Протоколы SCP'/'Протоколы SCP - 1 - Сейф №1 - Разные авторы.m4b'),'a new scan uses them')
        row=self.row('1');editor=self.service.names_editor(row['id'],row['revision'])
        self.assertEqual(sorted(r['field'] for r in editor['remembered']),['number','series','title'])
        title=next(r for r in editor['remembered'] if r['field']=='title')
        self.assertEqual((title['from'],title['to']),('Пртоколы SCP. Сейф №1','Сейф №1'))
        self.service.names_forget(row['id'],row['revision'],title['id'])
        self.assertEqual(self.preview('1')['title'],'Пртоколы SCP. Сейф №1','Forget takes the title back')
        self.assertEqual(self.row('1')['entered'],['series','number'])

    def test_approve_with_the_editor_open_saves_the_names_and_the_job_carries_them(self):
        self.scp();row=self.row('2');names={'series':'Протоколы SCP','number':'2'}
        preview=self.service.approval_preview(row['id'],row['revision'],title='Сейф №2',names=names)
        self.assertEqual(preview['place'],{'universe':'','series':'Протоколы SCP','number':'2','collection':True})
        approved=self.service.approve_book(row['id'],row['revision'],title='Сейф №2',path=preview['path'],names=names);self.start_and_wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        self.assertEqual(Path(job['output']['final_path']),self.sorted/'Сборники'/'Протоколы SCP'/'Протоколы SCP - 2 - Сейф №2 - Разные авторы.m4b')
        current=self.service.reviews._row('Audiobooks',approved['row']['id'])
        self.assertEqual(job['manifest']['metadata_facts']['entered_names']['digest'],entered_names.digest_for(self.inv.database,current),'the job\'s names stamp is the book\'s')
        self.assertEqual(entered_names.entered(entered_names.book_values(self.inv.database,current)),['title','series','number'],'Approve records')
        final=Path(job['output']['final_path']);before=hashlib.sha256(final.read_bytes()).hexdigest()
        saved=self.service.names_save(current['id'],current['revision'],{'universe':'SCP Foundation'})
        self.assertEqual(saved['outcome'],'ready_only');self.assertEqual(hashlib.sha256(final.read_bytes()).hexdigest(),before,'the finished audiobook is untouched')

    def test_inline_author_title_series_are_one_book_local_press_waiting_for_start(self):
        # Keep the real long coauthor/series names below the unchanged240-character policy in the deep gate fixture.
        self.sorted=self.base/'S';self.sorted.mkdir()
        title='Мистер Вечный Канун. Уэлихолн'
        for key in ('one','sibling'):
            tone(self.audio/'Unsorted'/key/'01.mp3',self.cover,title=title,album=title,artist='Олег Яковлев; Владимир Торин')
        rows=self.start();row=next(r for r in rows if Path(r['members'][0]['path']).parent.name=='one')
        sibling=next(r for r in rows if Path(r['members'][0]['path']).parent.name=='sibling')
        values={'title':'Уэлихолн','author':'Олег Яковлев, Владимир Торин','names':{'series':'Мистер Вечный Канун','number':'1'}}
        preview=self.service.approval_preview(row['id'],row['revision'],**values)
        self.assertTrue(preview['path'],ascii(preview))
        self.assertIn('Мистер Вечный Канун',preview['path']);self.assertIn(' - 1 - Уэлихолн',preview['path'])
        approved=self.service.approve_book(row['id'],row['revision'],path=preview['path'],**values)
        job=self.service.jobs.status()['jobs'][0]
        self.assertEqual(job['state'],'pending','one Approve saves and queues; it never resumes the queue')
        self.assertTrue(Path(row['members'][0]['path']).exists())
        remembered=entered_names.book_values(self.inv.database,row)
        self.assertTrue({'title','author','series','number'}.issubset(remembered),'combined answer persists before Start')
        self.assertNotIn('series',entered_names.book_values(self.inv.database,sibling),'the sibling is not answered')
        self.start_and_wait();job=self.service.jobs.status()['jobs'][0]
        self.assertEqual(job['state'],'completed',job)
        self.assertEqual(Path(job['output']['final_path']),self.sorted/preview['path'])
        meta=job['manifest']['metadata'];self.assertEqual((meta['title'],meta['series'],meta['number']),('Уэлихолн','Мистер Вечный Канун','1'))
        self.assertIn('Яковлев',meta['canonical_author']);self.assertIn('Торин',meta['canonical_author'])

    def test_m14_the_panels_unsaved_destination_preview_uses_the_rows_names(self):
        # Senua's 0.22.3 review, m14: with the panel dirty, "Unsaved destination preview" was planned from the six hidden
        # name inputs (ruling 40), so it showed names from before a row Edit names Save, never the names the row uses.
        import os
        self.scp();row=self.row('1')
        self.service.names_save(row['id'],row['revision'],{'title':'Сейф №1','series':'Протоколы SCP','number':'1'})
        row=self.row('1');goes=self.preview('1')['path']
        self.assertEqual(goes,str(Path('Сборники')/'Протоколы SCP'/'Протоколы SCP - 1 - Сейф №1 - Разные авторы.m4b'),'positive control: the row\'s Goes to')
        researched=self.service._approval_result(row['id'],row['revision'])[1]['review']
        panel={field:researched.get(field,'') for field in ('original_language','canonical_author','narrator','genre','topic')}
        panel.update(title='Пртоколы SCP. Сейф №1',author='Сборник',series='Старая серия',number='9',universe='',multi_author=False,anthology=False)  # the hidden inputs, stale
        stale=self.service.reviews.routing_preview('Audiobooks',row['id'],row['revision'],panel)
        self.assertNotEqual(os.path.relpath(stale['path'],self.sorted) if stale.get('path') else stale.get('reason'),goes,'positive control: the hidden inputs plan another path')
        preview=self.service.routing_preview(row['id'],row['revision'],panel)
        self.assertEqual(os.path.relpath(preview['path'],self.sorted),goes,'the row\'s names, the panel\'s other values')
        never_saved=dict(panel,title='',author='',series='',number='',original_language='')
        preview=self.service.routing_preview(row['id'],row['revision'],never_saved)
        self.assertEqual(os.path.relpath(preview['path'],self.sorted),goes,'a book never saved: no "Confirm the book title"; an empty field keeps the row\'s')

    def test_a_refused_approve_takes_its_saved_names_back(self):
        self.scp();row=self.row('3')
        with self.assertRaisesRegex(ValueError,'Destination changed'):
            self.service.approve_book(row['id'],row['revision'],path='Elsewhere.m4b',names={'series':'Протоколы SCP','number':'3'})
        self.assertEqual(entered_names.book_values(self.inv.database,row),{},'nothing stays saved');self.assertEqual(self.service.jobs.status()['jobs'],[])

    def test_a_converting_book_refuses_and_nothing_is_saved(self):
        self.scp();row=self.row('1');before=entered_names.stamp(self.inv.database)
        self.service._names_job=lambda identity:{'state':'running','row':None}
        with self.assertRaises(ValueError) as refused:self.service.names_save(row['id'],row['revision'],{'title':'Сейф №1'})
        self.assertEqual((refused.exception.code,str(refused.exception)),('converting',"This book is converting. Its names can't change now."))
        self.assertEqual(entered_names.stamp(self.inv.database),before)

    def test_a_queued_job_is_set_aside_and_its_book_sent_back_to_research_with_the_new_names(self):
        self.scp();row=self.row('1')
        hold=threading.Event();self.addCleanup(hold.set)
        parked=threading.Thread(target=hold.wait,daemon=True);parked.start();self.service.jobs._thread=parked  # the queue looks busy: the job stays queued
        approved=self.service.approve_book(row['id'],row['revision'])
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'pending','positive control: queued, not started')
        calls=[];self.service.automatic.requeue=lambda identity:calls.append(('requeue',identity)) or 'this_run';self.service.automatic.request_start=lambda **kw:calls.append(('start',)) or {'action':'started'}
        current=self.service.reviews._row('Audiobooks',approved['row']['id'])
        self.assertFalse(self.service._names_stale(self.service.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job['job_id'],))[0]),'planned under the names in force')
        saved=self.service.names_save(current['id'],current['revision'],{'series':'Протоколы SCP','number':'1'})
        self.assertEqual(saved['outcome'],'replanned')
        with connect(self.inv.database) as db:
            state=db.execute('SELECT state,reason FROM audio_jobs WHERE job_id=?',(job['job_id'],)).fetchone()
            aside=db.execute('SELECT kind FROM audio_job_set_aside WHERE job_id=?',(job['job_id'],)).fetchone()
            record=db.execute('SELECT state FROM automatic_candidates WHERE id=?',(current['id'],)).fetchone()
        self.assertEqual((state[0],aside[0]),('needs attention','names'),'set aside, kept');self.assertEqual(record[0],'Pending')
        self.assertEqual(calls,[('requeue',current['id']),('start',)])
        self.assertEqual(self.service.jobs.status()['jobs'],[],'the book has no current job: nothing runs under the old names')
        again=self.research(self.service.reviews._row('Audiobooks',current['id']))
        self.assertEqual((again['reasons'],again['review']['series'],again['review']['number']),([],'Протоколы SCP','1'),'research plans it with the new names')
        self.assertEqual(again['metadata_facts']['entered_names']['digest'],entered_names.digest_for(self.inv.database,current))

    def test_a_save_answer_says_where_the_book_goes_and_carries_its_row(self):
        # 0.22.3 (Judy 2.2, 2.3): the strip's "Goes to" and "It left this list: {status}" come from the answer, never guessed.
        self.scp();row=self.row('1')
        saved=self.service.names_save(row['id'],row['revision'],{'title':'Протоколы SCP. Сейф №1'})
        self.assertEqual(saved['destination']['path'],str(Path('Сборники')/'Протоколы SCP. Сейф №1 - Разные авторы.m4b'))
        self.assertEqual(saved['list_row']['id'],row['id']);self.assertIn('status',saved['list_row'])
        self.assertNotIn('members',saved['list_row'],'the track list stays out of the answer')

    def test_an_approve_answer_carries_the_books_row(self):
        self.scp();row=self.row('control')
        approved=self.service.approve_book(row['id'],row['revision']);self.start_and_wait()
        self.assertEqual(approved['list_row']['id'],row['id']);self.assertNotIn('destination',approved)

    def test_m1_a_names_save_whose_extras_fail_still_reports_saved(self):
        # Senua's 0.22.3 review, m1: _press_after "never fails the press", but a RuntimeError in the list row failed it.
        from unittest import mock
        self.scp();row=self.row('1')
        with mock.patch.object(self.service,'restart_row',side_effect=RuntimeError('fixture: the list row is unavailable')):
            saved=self.service.names_save(row['id'],row['revision'],{'title':'Протоколы SCP. Сейф №1'})
        self.assertEqual(saved['outcome'],'saved');self.assertNotIn('list_row',saved)


class ActionQueueTests(unittest.TestCase):
    def test_book_action_names_the_queued_or_running_action_for_a_book(self):
        from action_queue import ActionQueue
        queue=ActionQueue(server=None)
        queue.items=[{'id':'1','action':'retry','book_id':'a','args':{}}];queue.running={'id':'2','action':'delete','book_id':'b','args':{}}
        self.assertEqual((queue.book_action('a'),queue.book_action('b'),queue.book_action('c')),('retry','delete',None))


class ClaimCheckFolderTests(ApproveFixture):
    """Senua 0.24.0 C1: the claim check (_names_stale) and the startup pass (regroup_partial_jobs) judge "part of one
    source folder" with the same decision as grouping (groups.folder_verdict): Sergei's "Keep as separate books" answer
    and ruling 71a's library root and container folders. A book grouping keeps apart is approved, converts as planned and
    is never set aside, at Approve or at any later engine start. (Here, not in test_folder_regroup: gate headroom.)"""

    def rows(self):
        return {row['title_clue']:row for row in self.service.reviews.page()['rows']}

    def approved_and_never_set_aside(self,title):
        """Approve the book titled title; its job starts as planned at every claim and the startup pass leaves it."""
        row=self.rows()[title]
        approved=self.service.approve_book(row['id'],row['revision'])
        def book():
            with connect(self.inv.database) as db:
                group=tuple(db.execute('SELECT approved,review,revision FROM book_groups WHERE id=?',(row['id'],)).fetchone())
                context=db.execute('SELECT * FROM candidate_context WHERE id=?',(row['id'],)).fetchone()
                state=db.execute('SELECT state FROM audio_jobs WHERE job_id=?',(approved['job_id'],)).fetchone()[0]
                aside=db.execute("SELECT count(*) FROM sqlite_master WHERE name='audio_job_set_aside'").fetchone()[0] and \
                    db.execute('SELECT count(*) FROM audio_job_set_aside').fetchone()[0]
            return group,tuple(context) if context else None,state,aside
        before=book()
        self.assertIn('user_approval',json.dumps([str(v) for v in before[1] or ()]),'positive control: his Approve is recorded')
        with connect(self.inv.database) as db:raw=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(approved['job_id'],)).fetchone())
        self.assertEqual((raw['state'],before[2],before[3]),('pending','pending',0))
        self.assertFalse(self.service._names_stale(raw),'the claim check starts it as planned')
        self.assertEqual(self.service.regroup_partial_jobs(),[],'the startup pass leaves it')
        self.assertEqual(book(),before,'its approval and saved values stay; nothing is set aside')
        self.assertFalse(self.service._names_stale(raw),'and again at the next claim (an engine restart)')
        self.assertEqual(self.service.regroup_partial_jobs(),[])
        self.assertEqual(book(),before)

    def test_kept_separate_book_is_approved_and_never_set_aside(self):
        # "Keep as separate books" on the raised folder question, then Approve one of them.
        folder=self.audio/'Unsorted'/'Разное'
        tone(folder/'Альфа.mp3',self.cover,album='Альфа',artist='Сергей Лукьяненко')
        tone(folder/'Бета.mp3',self.cover,album='Бета',artist='Сергей Лукьяненко')
        self.start()
        for row in self.service.reviews.page()['rows']:
            result=self.research(row)
            state='Held' if result.get('reasons') and not result.get('wait') else 'Waiting for source' if result.get('wait') else 'Queued'
            self.service.automatic._record(row,state,dict(result,until_change=state=='Held'),None)
        row=self.service.reviews.page(status='output_attention')['rows'][0]
        self.assertEqual((row['ask']['kind'],row['ask']['cause']),('files_unclear','folder_books'),'positive control: one folder question')
        self.assertEqual(self.service.keep_separate(row['id'],row['revision']),{'kept':2})
        self.approved_and_never_set_aside('Альфа')
        self.assertEqual(sorted(len(r['members']) for r in self.service.reviews.page()['rows']),[1,1])

    def test_loose_books_in_a_library_root_or_a_container_folder_are_never_set_aside(self):
        # Ruling 71a: the library root and a container folder ("Unsorted") hold whole books, one per file. The same two
        # files in an ordinary folder are one held question (the positive control in the test above).
        for folder,names in ((self.audio,('Гамма','Дельта')),(self.audio/'Unsorted',('Альфа','Бета'))):
            for name in names:tone(folder/(name+'.mp3'),self.cover,album=name,artist='Сергей Лукьяненко')
        rows=self.start()
        self.assertEqual(sorted(len(r['members']) for r in rows),[1,1,1,1],'one book per file')
        for title in ('Гамма','Альфа'):
            with self.subTest(title=title):self.approved_and_never_set_aside(title)


if __name__=='__main__':unittest.main()

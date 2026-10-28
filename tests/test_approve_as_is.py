"""Sergei as a source and "Approve as is" (rulings 6a, 6b, 10, 11, 11a; 2026-10-24).

Real private audio fixtures through identity, Approve, conversion, publication and source removal, with a separate
Sorted folder and the production output policy. No network, no library access."""
import json,shutil,subprocess,tempfile,threading,time,unittest,urllib.error
from pathlib import Path
from scanner import Inventory,connect
from scan_wait import finish_scan,finish_thread
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


class ApproveFixture(unittest.TestCase):
    """A separate Sorted folder, the production policy, offline research. No tests of its own: shared by suites."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=automatic_fixtures.AREA);self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.audio=self.base/'audio';self.audio.mkdir();self.sorted=self.base/'Audiobooks Sorted';self.sorted.mkdir()
        self.cover=self.base/'art.png';self.cover.write_bytes(artwork())

    def start(self):
        roots={'Audiobooks':str(self.audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')}
        self.inv=Inventory(self.base/'catalog.sqlite3',roots,output_root=str(self.sorted));self.inv.launch('Audiobooks');finish_scan(self.inv)
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


class ApproveAsIsTests(ApproveFixture):
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

    def stored(self,identity):
        """What the catalog holds about one book: its group, context, research record and entered values."""
        with connect(self.inv.database) as db:
            have={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            one=lambda sql:[tuple(r) for r in db.execute(sql,(identity,))]
            return {'group':one('SELECT revision,review,approved,fingerprint FROM book_groups WHERE id=?'),
                    'context':one('SELECT revision,data FROM candidate_context WHERE id=?') if 'candidate_context' in have else [],
                    'research':one('SELECT revision,state,result FROM automatic_candidates WHERE id=?') if 'automatic_candidates' in have else [],
                    'entered':one('SELECT * FROM manual_metadata_sources WHERE candidate_id=?') if 'manual_metadata_sources' in have else []}

    def test_m9_a_refused_approve_leaves_the_stored_book_as_it_was(self):
        # Futaba's 0.22.0 QA, m-9: a file put at the "Goes to" path after the row was shown. Approve was refused ("Nothing was
        # changed") but the approval had already been written: the book left the to-do list until the next Start.
        for n,name in ((1,'Пролог'),(2,'Финал')):tone(self.audio/'Unsorted'/'Брат мой'/(name+'.mp3'),self.cover,album='Брат мой',artist='Иван Петров')
        row=self.start()[0];self.research(row)
        preview=self.service.approval_preview(row['id'],row['revision'])
        before=self.stored(row['id'])
        taken=Path(preview['absolute']);taken.parent.mkdir(parents=True);taken.write_bytes(b'PREEXISTING')
        with self.assertRaisesRegex(ValueError,'already exists'):self.service.approve_book(row['id'],row['revision'],path=preview['path'])
        self.assertEqual(self.stored(row['id']),before,'refused: nothing was changed, as the row says')
        self.assertEqual((taken.read_bytes(),self.service.jobs.status()['jobs']),(b'PREEXISTING',[]))
        # Control: the same row, at the same revision, approves once the name is free.
        taken.unlink();self.service.approve_book(row['id'],row['revision'],path=preview['path']);self.wait()
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'completed')

    def test_convert_whats_there_leaves_out_the_missing_file(self):
        sources=[tone(self.audio/'Unsorted'/'Новая плоть'/('%02d.mp3'%n),self.cover,album='Новая плоть',title='Рассказ %d'%n,artist='Иван Петров',track='%d/3'%n) for n in (1,2,3)]
        self.start();sources[2].unlink()
        self.inv.launch('Audiobooks');finish_scan(self.inv)
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


class ReviewFindingsTests(ApproveFixture):
    """Senua's early 0.22.0 review (2026-10-24): m1, m2, m3, m4 and m9."""
    def two_files(self,album,artist=None):
        tags={'artist':artist} if artist else {}
        return [tone(self.audio/'Unsorted'/album/('%02d.mp3'%n),self.cover,album=album,title='Глава %d'%n,track='%d/2'%n,**tags) for n in (1,2)]

    def test_m1_approve_refuses_a_destination_other_than_the_goes_to_line_shown(self):
        import author_rules
        self.two_files('Тихий дом','Иван Петров')
        row=self.start()[0]
        shown=self.service.approval_preview(row['id'],row['revision'])['path']
        self.assertEqual(Path(shown).parts[0],'Петров Иван','positive control')
        with connect(self.inv.database) as db:author_rules.append(db,'same_as','Иван Петров',target='Petrov Ivan',actor='user',source='test')
        with self.assertRaisesRegex(ValueError,'Destination changed'):self.service.approve_book(row['id'],row['revision'],path=shown)
        self.assertEqual(self.service.jobs.status()['jobs'],[],'nothing queued')
        now=self.service.approval_preview(row['id'],row['revision'])['path'];self.assertEqual(Path(now).parts[0],'Petrov Ivan')
        self.service.approve_book(row['id'],row['revision'],path=now);self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        self.assertEqual(Path(job['output']['final_path']),self.sorted/now,'the path shown is the path used')

    def test_m2_a_typed_or_entered_author_goes_through_sergeis_same_as_rules(self):
        self.two_files('Мор')
        row=self.start()[0]
        preview=self.service.approval_preview(row['id'],row['revision'],author='Терри Пратчетт')
        self.assertEqual(Path(preview['path']).parts[0],'Pratchett Terry','typed: the same folder the tags go to (ruling 12)')
        with connect(self.inv.database) as db:manual_metadata.append(db,manual_metadata.capture(row,{'title':'Мор','canonical_author':'Терри Пратчетт'},''))
        with connect(self.inv.database) as db:sources=manual_metadata.records(db,row)
        result=self.service.automatic.research.lookup(dict(row,_manual_metadata_sources=sources),str(self.audio),threading.Event())
        self.assertEqual(result['review']['canonical_author'],'Pratchett Terry','entered: the same folder')

    def test_m3_a_same_author_choice_is_not_saved_as_entered_by_you(self):
        from unittest import mock
        self.two_files('Часы','Dean Koonts')
        row=self.start()[0]
        with mock.patch.object(self.service,'answer_same_author',return_value='Koontz Dean'):
            approved=self.service.approve_book(row['id'],row['revision'],choice='same')
        self.wait()
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)
        self.assertEqual(job['manifest']['metadata']['canonical_author'],'Koontz Dean')
        with connect(self.inv.database) as db:entered=manual_metadata.records(db,approved['row'])
        self.assertEqual([e for e in entered if 'canonical_author' in (e.get('values') or {})],[],'his answer is a rule, not a typed value')

    def test_a_refused_approve_keeps_no_same_author_answer(self):
        # 0.22.3 (Sergei 2026-10-27; the m7 pattern): the answer's rule was written, and his other books requeued, before
        # the Approve could be refused; the refusal left the rule in force.
        import author_rules
        self.two_files('Часы','Dean Koonts')
        row=self.start()[0]
        with connect(self.inv.database) as db:
            author_rules.setup(db);author_rules.append(db,'keep','Koontz Dean',actor='user',source='test')  # an author the library has
        result=self.research(row)
        self.assertEqual((result['ask']['kind'],result['ask']['existing']),('same_author','Koontz Dean'),'positive control: asked')
        self.service.automatic._record(row,'Held',dict(result,until_change=True),None)
        def answers():
            # The rule in force for the credit (the rules are append-only: a refused press's answer is retracted by the app).
            rules=author_rules.load(self.inv.database);row=rules.rule('Dean Koonts')
            return [] if row is None or row['kind']==author_rules.RETRACTED else [(row['kind'],row['target'])]
        with self.assertRaisesRegex(ValueError,'Destination changed since it was shown'):
            self.service.approve_book(row['id'],row['revision'],choice='same',path='Elsewhere\\Часы.m4b')
        self.assertEqual(answers(),[],'no rule from a refused Approve')
        self.assertFalse(author_rules.load(self.inv.database).taken_back('Dean Koonts'),'the undo by the app is no Take back of his')
        self.assertEqual(self.research(row)['ask']['kind'],'same_author','still asked')
        self.service.approve_book(row['id'],row['revision'],choice='same');self.wait()
        self.assertEqual(answers(),[('same_as','Koontz Dean')],'the accepted Approve keeps his answer')
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['manifest']['metadata']['canonical_author'],'Koontz Dean')

    def test_m1_an_error_after_the_job_is_queued_keeps_the_answer_and_the_approve(self):
        # Senua's 0.22.3 review, m1: an error in the answer's extras (the list row) after the job was queued reported the
        # Approve as failed and took the Same author? answer back, while the book was filed.
        from unittest import mock
        import author_rules
        self.two_files('Часы','Dean Koonts')
        row=self.start()[0]
        with connect(self.inv.database) as db:
            author_rules.setup(db);author_rules.append(db,'keep','Koontz Dean',actor='user',source='test')
        result=self.research(row);self.service.automatic._record(row,'Held',dict(result,until_change=True),None)
        with mock.patch.object(self.service,'restart_row',side_effect=RuntimeError('fixture: the list row is unavailable')):
            approved=self.service.approve_book(row['id'],row['revision'],choice='same')
        self.wait()
        self.assertTrue(approved['job_id']);self.assertNotIn('list_row',approved,'the extras are left out, the Approve stands')
        self.assertEqual(author_rules.load(self.inv.database).same_as('Dean Koonts'),'Koontz Dean','his answer is kept')
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',job)

    def test_ruling_53_approving_the_first_book_of_a_set_files_the_rest(self):
        # Ruling 53 (Sergei 2026-10-28, "a"): a numbered set that only confirms itself is asked; his Approve of its first
        # book answers the rest, which go back on the run and file by themselves while his job still waits in the queue.
        for n, name in ((1, 'Греция'), (2, 'Рим'), (3, 'Египет')):
            for k in (1, 2):
                tone(self.audio / 'Иван Петров' / 'Курс истории' / str(n) / ('%02d.mp3' % k), self.cover, album='Курс истории. Лекция %d. %s' % (n, name), title='Глава %d' % k, artist='Иван Петров', track='%d/2' % k)
        rows = self.start()
        by = {Path(r['members'][0]['path']).parent.name: r for r in rows}
        for row in rows:
            result = self.research(row)
            self.assertEqual(((result.get('ask') or {}).get('why'), (result.get('ask') or {}).get('split', {}).get('series')), ('title_series', 'Курс истории. Лекция'), 'the set is asked')
            self.service.automatic._record(row, 'Held', dict(result, until_change=True), None)
        calls = []; self.service.automatic.requeue = lambda identity: calls.append(identity) or 'this_run'
        hold = threading.Event(); self.addCleanup(hold.set)
        parked = threading.Thread(target=hold.wait, daemon=True); parked.start(); self.service.jobs._thread = parked  # the job stays queued
        self.service.approve_book(by['1']['id'], by['1']['revision'])
        self.assertEqual(sorted(calls), sorted([by['2']['id'], by['3']['id']]), 'the rest of the set goes back on the run')
        self.assertEqual([j['state'] for j in self.service.jobs.status()['jobs']], ['pending'], 'positive control: his job still waits')
        result = self.research(by['3'])
        self.assertEqual((result['reasons'], result.get('ask'), result['review']['series'], result['review']['number']), ([], None, 'Курс истории. Лекция', '3'))

    def test_m21_an_author_he_entered_alone_does_not_answer_the_series_question(self):
        # Senua's 0.22.3 review, m21: an "Entered by you" title or author (a 0.22.2 panel record) skipped the ruling-52
        # question, so «Курс истории. Лекция 3. Греция» filed silently under the split's junk series.
        self.two_files('Курс истории. Лекция 3. Греция', 'Иван Петров')
        row = self.start()[0]
        with connect(self.inv.database) as db:manual_metadata.append(db, manual_metadata.capture(row, {'canonical_author': 'Иван Петров'}, ''))
        with connect(self.inv.database) as db:sources = manual_metadata.records(db, row)
        result = self.service.automatic.research.lookup(dict(row, _manual_metadata_sources=sources), str(self.audio), threading.Event())
        self.assertEqual(result['local_agreement']['author']['state'], 'entered', 'positive control: his entered author')
        self.assertEqual(((result.get('ask') or {}).get('why'), (result.get('review') or {}).get('series')), ('title_series', None), result['reasons'])

    def test_m15_a_book_researched_under_a_refused_answer_is_put_back_on_the_run(self):
        # Senua's 0.22.3 review, m15: after m13 changed_for marks the book the run researched while the refused press's
        # answer was in force, but the undo put nothing back on the run: it sat in "Still checking" until a new scan.
        from unittest import mock
        import author_rules
        self.two_files('Часы','Dean Koonts');self.two_files('Ночь','Dean Koonts')
        rows=self.start()
        row=next(r for r in rows if 'Часы' in r['members'][0]['path']);other=next(r for r in rows if 'Ночь' in r['members'][0]['path'])
        with connect(self.inv.database) as db:
            author_rules.setup(db);author_rules.append(db,'keep','Koontz Dean',actor='user',source='test')
        result=self.research(row);self.service.automatic._record(row,'Held',dict(result,until_change=True),None)
        self.assertEqual(result['ask']['kind'],'same_author','positive control: asked')
        calls=[];self.service.automatic.requeue=lambda identity:calls.append(identity) or 'this_run'
        real=self.service._approval_result;seen=[]
        def inside(*args,**kwargs):
            # The run researches his other book while the press's answer is in force; it is held for a reason of its own.
            if not seen:
                found=self.research(other);seen.append(found)
                self.service.automatic._record(other,'Held',dict(found,reasons=['fixture hold'],until_change=True),None)
            return real(*args,**kwargs)
        with mock.patch.object(self.service,'_approval_result',side_effect=inside),self.assertRaisesRegex(ValueError,'Destination changed'):
            self.service.approve_book(row['id'],row['revision'],choice='same',path='Elsewhere\\Часы.m4b')
        self.assertEqual(seen[0]['review']['canonical_author'],'Koontz Dean','positive control: researched under the answer')
        self.assertTrue(author_rules.load(self.inv.database).changed_for(seen[0]),'positive control: its research is out of date')
        self.assertEqual(calls,[other['id']],'put back on the run; the refused book itself is not')

    def queued_press(self,interrupt):
        """Senua's 0.22.3 review, M4: an Approve carrying all three answers (Same author?, the English spelling and Edit
        names), with interrupt() run in approve_automatic right after the job is queued. Returns the answer and the row."""
        from unittest import mock
        import author_rules
        self.two_files('Часы','Dean Koonts')
        row=self.start()[0]
        with connect(self.inv.database) as db:
            author_rules.setup(db);author_rules.append(db,'keep','Koontz Dean',actor='user',source='test')
        result=self.research(row);self.service.automatic._record(row,'Held',dict(result,until_change=True),None)
        self.assertEqual(result['ask']['kind'],'same_author','positive control: asked')
        spelling={'kind':'same_as','credit':'Лев Гроссман','target':'Grossman Lev','title':'Часы'}
        real=self.service.jobs.enqueue
        def enqueue(*args,**kwargs):
            job=real(*args,**kwargs);interrupt();return job
        with mock.patch.object(self.service,'_english_spelling_answer',return_value=spelling),mock.patch.object(self.service.jobs,'enqueue',enqueue):
            approved=self.service.approve_book(row['id'],row['revision'],choice='same',names={'series':'Часовщики','number':'2'})
        return approved,row
    def assert_kept(self,approved,row):
        import author_rules,entered_names
        jobs=self.service.jobs.status()['jobs']
        self.assertEqual([(j['job_id'],j['state']) for j in jobs],[(approved['job_id'],'pending')],'the job is queued')
        rules=author_rules.load(self.inv.database)
        self.assertEqual(rules.same_as('Dean Koonts'),'Koontz Dean','his Same author? answer is kept')
        self.assertEqual(rules.same_as('Лев Гроссман'),'Grossman Lev','his English spelling is saved')
        current=self.service.reviews._row('Audiobooks',row['id'])
        self.assertEqual(entered_names.book_values(self.inv.database,current).get('series'),'Часовщики','his names stay saved')
        self.assertEqual(jobs[0]['manifest']['metadata']['canonical_author'],'Koontz Dean')

    def test_m4_an_approve_queued_while_pause_settles_is_accepted_and_keeps_every_answer(self):
        # Pause still reaching the queue checkpoints (_pause_depth 1): resume raised StartRefused after the job was queued,
        # the row said the Approve was refused and the Same author? answer was taken back.
        def settling():self.service._pause_depth=1
        approved,row=self.queued_press(settling)
        self.assertTrue(approved['job_id'])
        self.assert_kept(approved,row)
        self.service._pause_depth=0;self.service.resume(recheck=False);self.wait()
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'completed','Start runs it once Pause settles')

    def test_m4_quit_arriving_just_after_the_job_is_queued_reports_the_approve_accepted(self):
        # drain() sets the press's stop: "Books Arranger is closing. The book was not approved." for a queued book.
        approved,row=self.queued_press(lambda:self.service.drain())
        self.assertTrue(approved['job_id'])
        self.assert_kept(approved,row)

    def test_m4_closing_the_app_stops_an_approve_in_progress(self):
        from unittest import mock
        import audio_pipeline
        self.two_files('Долгая книга','Иван Петров')
        row=self.start()[0];started=threading.Event();outcome={}
        def slow(path,cache,stop=None):
            started.set()
            if stop is None or not stop.wait(20):raise AssertionError('the press was never told to stop')
            raise InterruptedError()
        def press():
            try:self.service.approve_book(row['id'],row['revision'])
            except BaseException as error:outcome['error']=error
        with mock.patch.object(audio_pipeline,'probe',slow):
            worker=threading.Thread(target=press);worker.start()
            self.assertTrue(started.wait(30));t0=time.monotonic();self.service.drain();finish_thread(worker,'The interrupted press')
        self.assertLess(time.monotonic()-t0,5,'Quit does not wait behind the press')
        self.assertIsInstance(outcome.get('error'),ValueError,outcome);self.assertIn('closing',str(outcome['error']))
        self.assertEqual(self.service.jobs.status()['jobs'],[])

    def test_m9_approves_second_safety_filter_refuses_an_unreadable_file_found_at_the_gate(self):
        # approve_book's first check passes; the gate inside approve_automatic then finds the file unreadable.
        from unittest import mock
        import source_identity
        self.two_files('Тихо','Иван Петров')
        row=self.start()[0];real=source_identity.source_gate
        def gate(gate_row,work):return real(gate_row,work)+['Playback order uncertain','Source files unavailable or unreadable']
        with mock.patch.object(source_identity,'source_gate',gate):
            with self.assertRaises(ValueError) as caught:self.service.approve_book(row['id'],row['revision'])
        self.assertEqual(str(caught.exception),'Source files unavailable or unreadable','only the safety reason; his approval overrides the order hold')
        self.assertEqual(self.service.jobs.status()['jobs'],[])


if __name__=='__main__':unittest.main()

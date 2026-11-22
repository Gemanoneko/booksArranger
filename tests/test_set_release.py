"""Rulings 56/57 and Senua M11/M12: approvals stay per book and never start an automatic run.
Private audio, offline research, separate Sorted; the entry check runs this module once."""
import json
import time
import unittest
from pathlib import Path
from unittest import mock
from scanner import connect
from test_approve_as_is import ApproveFixture, tone


class SetReleaseTests(ApproveFixture):
    def books(self, artist='Иван Петров', albums=None):
        albums=albums or [('1','Курс истории. Лекция 1. Греция'),('2','Курс истории. Лекция 2. Рим')]
        for folder,album in albums:
            for k in (1,2):
                tone(self.audio/'Unsorted'/folder/('%02d.mp3'%k),self.cover,album=album,title='Глава %d'%k,artist=artist,track='%d/2'%k)
        rows=self.start()
        return {Path(r['members'][0]['path']).parent.name:r for r in rows}

    def finish_run(self):
        limit=time.monotonic()+120
        while (self.service.automatic.thread and self.service.automatic.thread.is_alive()) or self.service.automatic.status()['state'] in ('Running','Stopping'):
            if time.monotonic()>limit:self.fail('automatic run did not finish')
            time.sleep(.1)
        self.wait()

    def held(self,rows):
        for row in rows.values():
            result=self.research(row)
            self.service.automatic._record(row,'Held',result)

    def ask(self,row):
        current=self.service.reviews._row('Audiobooks',row['id'])
        return (self.service.automatic.candidate(current) or {}).get('ask') or {}

    def test_ruling_57_approve_one_does_not_release_the_other_even_after_start(self):
        # Ruling 57 was about a set that only confirms itself («Курс истории. Лекция 1/2»), each book asked and approved
        # separately. R22 (Sergei 2026-11-22) withdrew that question: the series such a name only looks like is doubtful,
        # treated as not found, and nothing is asked. Each book of the set is filed by itself under the name its files
        # give, with no series, and neither waits for the other. (The test keeps its name.)
        rows=self.books()
        self.service.automatic.start();self.finish_run()
        self.assertEqual([self.ask(rows[k]).get('why') for k in '12'],[None,None],'R22: no series question')
        self.start_and_wait()
        jobs=self.service.jobs.status()['jobs']
        self.assertEqual(sorted((j['manifest']['metadata']['title'],j['manifest']['metadata']['series'],j['state']) for j in jobs),
                         [('Курс истории. Лекция 1. Греция','','completed'),('Курс истории. Лекция 2. Рим','','completed')])

    def test_ruling_56_a_paused_run_stays_paused(self):
        # The books are held for a question that is still asked (no author in the files), since R22 withdrew the set's.
        rows=self.books('');self.service.automatic.start();self.finish_run()
        self.assertTrue(self.ask(rows['1']).get('kind'),'positive control: the book is held for a question')
        run=self.service.automatic._run_row()
        with connect(self.inv.database) as db:
            db.execute("UPDATE automatic_runs SET state='Paused',phase='research',checkpoint=? WHERE id=?",(json.dumps({'pending':[],'done':[r['id'] for r in rows.values()]}),run['id']))
        with mock.patch.object(self.service.automatic,'request_start') as start:
            self.service.approve_book(rows['1']['id'],rows['1']['revision'])
        start.assert_not_called()
        self.assertEqual(self.service.automatic.status()['state'],'Paused')
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'pending')
        self.start_and_wait()
        self.assertEqual(self.service.automatic.status()['state'],'Paused')
        self.assertEqual(len(self.service.jobs.status()['jobs']),1)
        self.assertTrue(self.ask(rows['2']).get('kind'),'the other book is still held for its own question')

    def test_ruling_56_an_approve_leaves_unrelated_paused_jobs_pending_until_start(self):
        rows=self.books();self.held(rows)
        one=self.service.approve_book(rows['1']['id'],rows['1']['revision'])
        self.service.pause()
        with mock.patch.object(self.service,'resume',wraps=self.service.resume) as resume:
            two=self.service.approve_book(rows['2']['id'],rows['2']['revision'])
        resume.assert_not_called()
        self.assertEqual({j['job_id']:j['state'] for j in self.service.jobs.status()['jobs']},{one['job_id']:'pending',two['job_id']:'pending'})
        self.assertTrue(all(Path(m['path']).is_file() for row in rows.values() for m in row['members']),'both source books stay untouched')
        self.assertEqual(self.service.automatic.status()['state'],'Idle')
        self.start_and_wait()
        self.assertEqual([j['state'] for j in self.service.jobs.status()['jobs']],['completed']*2,'explicit Start converts both')

    def test_m12_discworld_correction_does_not_rename_other_folders(self):
        rows=self.books('Terry Pratchett',[('set/19','Discworld 19. Feet of Clay'),('elsewhere/20','Discworld 20. Hogfather'),('elsewhere/21','Discworld 21. Jingo')])
        self.held(rows)
        self.assertEqual([self.ask(rows[k]).get('why') for k in ('19','20','21')],[None]*3,'R22: the series the names look like is not asked about')
        self.service.approve_book(rows['19']['id'],rows['19']['revision'],names={'series':'City Watch','number':'19'});self.start_and_wait()
        self.assertEqual(self.service.jobs.status()['jobs'][0]['manifest']['metadata']['series'],'City Watch','positive control: book19 actually changed (a series he types is his answer)')
        for k,title in [('20','Hogfather'),('21','Jingo')]:
            hint=self.service.automatic.research.identity(rows[k],str(self.audio))[0]['series_hint']
            self.assertEqual({key:hint[key] for key in ('series','number','title')},{'series':'Discworld','number':k,'title':title},'the other books keep what their own names say')
            self.assertEqual(self.service.automatic.research.approved(rows[k],str(self.audio))['review']['series'],'','and are never put in his City Watch, nor in a series nothing confirms')
        self.assertEqual(len(self.service.jobs.status()['jobs']),1)

    def answer_author_as_shown(self,artist):
        rows=self.books(artist)
        self.service.automatic.start();self.finish_run();row=rows['1']
        self.assertTrue(self.service.automatic.candidate(row).get('until_change'),'positive control: actual automatic hold')
        first=self.ask(row)
        sibling_question=(self.ask(rows['2']).get('kind'),self.ask(rows['2']).get('why'))
        self.assertTrue(first.get('kind'),'positive control: the author is asked')
        self.assertNotEqual(first.get('why'),'title_series','the author question, never the series')
        with mock.patch.object(self.service.automatic,'request_start') as start:
            # R22: no series question follows his author answer (it raised SeriesAsked, "Answer saved", until 0.31.0).
            approved=self.service.approve_book(row['id'],row['revision'])
        start.assert_not_called()
        self.assertEqual([(j['job_id'],j['state'],j['manifest']['metadata']['series']) for j in self.service.jobs.status()['jobs']],[(approved['job_id'],'pending','')],
                         'queued without the doubtful series; Approve waits for conversion Start')
        self.assertEqual((self.ask(rows['2']).get('kind'),self.ask(rows['2']).get('why')),sibling_question,'only the clicked book was answered')
        self.start_and_wait()
        self.assertEqual([j['state'] for j in self.service.jobs.status()['jobs']],['completed'],'the saved author answer released no sibling book')

    def test_m11_ruling_33_approve_as_shown(self):
        self.answer_author_as_shown('Ilya Marchenko')

    def test_m11_no_author_approve_as_shown(self):
        self.answer_author_as_shown('')
        self.assertIn('Без автора',self.service.jobs.status()['jobs'][0]['output']['final_path'])

    def test_m11_two_people_approve_as_shown(self):
        self.answer_author_as_shown('Иван Петров - Антон Чехов')

    def test_ruling_59_english_question_needs_an_english_answer(self):
        import author_rules
        rows=self.books('Джеймс Роллинс')
        with connect(self.inv.database) as db:
            author_rules.setup(db);author_rules.append(db,'keep','Джеймс Роллинс',actor='user',source='old answer')
        with mock.patch.object(self.service.automatic.research,'_author_latin',return_value=None) as lookup:
            self.held(rows)
        self.assertGreater(lookup.call_count,0,'the old keep cannot suppress the lookup')
        row=rows['1'];self.assertEqual(self.ask(row)['why'],'english_spelling')
        for author in (None,'','Джеймс Роллинс'):
            with self.subTest(author=author),self.assertRaisesRegex(ValueError,'English name'):
                self.service.approve_book(row['id'],row['revision'],author=author)
        self.assertEqual(self.service.jobs.status()['jobs'],[])
        self.assertEqual(self.ask(row)['why'],'english_spelling')
        approved=self.service.approve_book(row['id'],row['revision'],author='James Rollins')  # R22: no series question follows
        self.assertEqual(author_rules.load(self.inv.database).same_as('Джеймс Роллинс'),'Rollins James')
        job=next(j for j in self.service.jobs.status()['jobs'] if j['job_id']==approved['job_id'])
        self.assertEqual((job['state'],job['manifest']['metadata']['canonical_author'],job['manifest']['metadata']['series']),('pending','Rollins James',''))

    def test_m10_same_author_answer_waits_for_start_then_asks_series(self):
        # Senua's M10 under R22 (the test keeps its name): his "same author" answer is saved as his rule and the book is
        # queued; no automatic run starts, and no series question comes next for it or for the other book.
        import author_rules
        rows=self.books('Dean Koonts')
        with connect(self.inv.database) as db:
            author_rules.setup(db);author_rules.append(db,'keep','Koontz Dean',actor='user',source='test')
        self.held(rows);row=rows['1']
        self.assertEqual(self.ask(row)['kind'],'same_author')
        with mock.patch.object(self.service.automatic,'request_start') as start:
            approved=self.service.approve_book(row['id'],row['revision'],choice='same')
        start.assert_not_called()
        self.assertEqual(author_rules.load(self.inv.database).same_as('Dean Koonts'),'Koontz Dean')
        self.assertEqual([(j['job_id'],j['state']) for j in self.service.jobs.status()['jobs']],[(approved['job_id'],'pending')],'Approve waits for conversion Start')
        self.service.automatic.start();self.finish_run()
        self.assertEqual([self.ask(rows[k]).get('why') for k in '12'],[None,None],'no series question for either book')

    def test_m10_english_spelling_answer_waits_for_start(self):
        import author_rules
        rows=self.books('Джеймс Роллинс')
        with mock.patch.object(self.service.automatic.research,'_author_latin',return_value=None):self.held(rows)
        row=rows['1'];self.assertEqual(self.ask(row)['why'],'english_spelling')
        with mock.patch.object(self.service.automatic,'request_start') as start:
            approved=self.service.approve_book(row['id'],row['revision'],author='James Rollins')  # R22: no series question follows
        start.assert_not_called()
        self.assertEqual(author_rules.load(self.inv.database).same_as('Джеймс Роллинс'),'Rollins James')
        self.assertEqual([(j['job_id'],j['state']) for j in self.service.jobs.status()['jobs']],[(approved['job_id'],'pending')],'Approve waits for conversion Start')
        self.service.automatic.start();self.finish_run()
        self.assertEqual([self.ask(rows[k]).get('why') for k in '12'],[None,None],'no series question for either book')



class SavedSeriesReceiptTests(ApproveFixture):
    def test_saved_answer_then_same_press_title_series_queues_only_until_explicit_start(self):
        # R22 withdrew the series question that followed his answer (it answered SeriesAsked, code series_needed, and
        # queued nothing). What stays: a Series and Number he types are his answer, never a doubt; his Approve with them
        # queues the book exactly where the preview said and starts nothing. (The test keeps its name.)
        from unittest.mock import patch
        for index in (1,2):tone(self.audio/'Unsorted'/'one'/('%02d.mp3'%index),self.cover,album='Оттенки магии01. Темный оттенок магии',title='Глава %d'%index,track='%d/2'%index)
        row=self.start()[0];self.service.automatic.start();SetReleaseTests.finish_run(self)
        research=self.service.automatic.research.approved(self.service.reviews._row('Audiobooks',row['id']),str(self.audio),title='Темный оттенок магии',author='Schwab Victoria')
        self.assertEqual((research['approval']['series_question'],research['review']['series']),(False,''),'no series question, and no series nothing confirms')
        current=self.service.reviews._row('Audiobooks',row['id']);names={'series':'Оттенки магии','number':'1'}
        preview=self.service.approval_preview(current['id'],current['revision'],title='Темный оттенок магии',author='Schwab Victoria',names=names);self.assertTrue(preview['path'],ascii(preview))
        with patch.object(self.service.automatic,'request_start') as auto,patch.object(self.service,'resume') as resume:
            self.service.approve_book(current['id'],current['revision'],title='Темный оттенок магии',author='Schwab Victoria',names=names,path=preview['path']);auto.assert_not_called();resume.assert_not_called()
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'pending');self.start_and_wait();job=self.service.jobs.status()['jobs'][0]
        self.assertEqual(job['state'],'completed',ascii(job));self.assertEqual(Path(job['output']['final_path']),self.sorted/preview['path'])
        self.assertEqual(job['manifest']['metadata']['title'],'Темный оттенок магии');self.assertEqual(job['manifest']['metadata']['canonical_author'],'Schwab Victoria')
        self.assertEqual((job['manifest']['metadata']['series'],job['manifest']['metadata']['number']),('Оттенки магии','1'))

class SavedSeriesTransportTests(unittest.TestCase):
    def test_direct_and_queued_saved_outcomes_are_typed_while_other_failures_stay_failures(self):
        from types import SimpleNamespace
        from merge_service import MergeService
        from web_server import BrowserServer,Handler
        answer=MergeService.SeriesAsked(MergeService.SERIES_ASKED)
        merge=SimpleNamespace(approve_book=mock.Mock(side_effect=answer),reviews=SimpleNamespace(enrich=lambda r:r,_row=lambda *_:{'id':'one'}))
        server=SimpleNamespace(merge=merge,actions=SimpleNamespace(blocker=lambda *_args,**_kw:False,item_blocker=lambda *_args,**_kw:False))  # 0.30.0: run_queued asks by item
        item={'action':'approve','book_id':'one','args':{'revision':1}}
        queued=BrowserServer.run_queued(server,item);self.assertEqual(queued,{'result':'saved','code':'series_needed','answer':answer.payload()})
        handler=Handler.__new__(Handler);handler.server=server;handler.candidate_identity=mock.Mock(return_value=('Audiobooks','one',1));handler.response=mock.Mock()
        handler.merge_request('/api/candidate/approve',{'library':'Audiobooks','id':'one','revision':1});handler.response.assert_called_once_with(200,answer.payload())
        merge.approve_book.side_effect=ValueError('Unexpected fixture refusal');self.assertEqual(BrowserServer.run_queued(server,item)['result'],'refused')
        handler.response.reset_mock();handler.merge_request('/api/candidate/approve',{'library':'Audiobooks','id':'one','revision':1});self.assertEqual(handler.response.call_args.args[0],409)
        merge.approve_book.side_effect=RuntimeError('Unexpected fixture failure')
        with self.assertRaisesRegex(RuntimeError,'Unexpected fixture failure'):BrowserServer.run_queued(server,item)

# 0.31.0 step 2 (rulings R2 and R5): these fixtures predate the look-up before review, and their sources are closed or
# cannot be reached. Under R2 such a book now waits a few tries for them, which is not what this suite tests; the
# look-up has its own tests (test_lookup_before_review_031). tests/original_title_fixture.py.
_no_lookup_before_review = None


def setUpModule():
    global _no_lookup_before_review
    from original_title_fixture import no_lookup
    _no_lookup_before_review = no_lookup()


def tearDownModule():
    _no_lookup_before_review.stop()


if __name__=='__main__':unittest.main()

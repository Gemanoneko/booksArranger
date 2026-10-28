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
        rows=self.books()
        self.service.automatic.start();self.finish_run()
        self.assertEqual([self.ask(rows[k]).get('why') for k in '12'],['title_series']*2)
        with mock.patch.object(self.service.automatic,'request_start') as start:
            self.service.approve_book(rows['1']['id'],rows['1']['revision'])
        start.assert_not_called()
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'pending','Approve waits for conversion Start')
        self.start_and_wait()
        self.assertEqual(len(self.service.jobs.status()['jobs']),1)
        self.assertEqual(self.ask(rows['2']).get('why'),'title_series')
        self.service.automatic.start();self.finish_run()
        self.assertEqual(len(self.service.jobs.status()['jobs']),1,'Start must not answer an already-held sibling')
        self.service.approve_book(rows['2']['id'],rows['2']['revision']);self.start_and_wait()
        self.assertEqual([j['state'] for j in self.service.jobs.status()['jobs']],['completed']*2)

    def test_ruling_56_a_paused_run_stays_paused(self):
        rows=self.books();self.service.automatic.start();self.finish_run()
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
        self.assertEqual(self.ask(rows['2']).get('why'),'title_series')

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
        self.assertEqual([self.ask(rows[k]).get('why') for k in ('19','20','21')],['title_series']*3)
        self.service.approve_book(rows['19']['id'],rows['19']['revision'],names={'series':'City Watch','number':'19'});self.start_and_wait()
        self.assertEqual(self.service.jobs.status()['jobs'][0]['manifest']['metadata']['series'],'City Watch','positive control: book19 actually changed')
        for k,title in [('20','Hogfather'),('21','Jingo')]:
            result=self.research(rows[k])
            self.assertEqual(result['ask']['split'],{'series':'Discworld','number':k,'title':title})
            self.assertEqual(self.service.automatic.research.approved(rows[k],str(self.audio))['review']['series'],'Discworld')
        self.assertEqual(len(self.service.jobs.status()['jobs']),1)

    def answer_author_as_shown(self,artist):
        rows=self.books(artist)
        self.service.automatic.start();self.finish_run();row=rows['1']
        self.assertTrue(self.service.automatic.candidate(row).get('until_change'),'positive control: actual automatic hold')
        first=self.ask(row)
        sibling_question=(self.ask(rows['2']).get('kind'),self.ask(rows['2']).get('why'))
        self.assertNotEqual(first.get('why'),'title_series','author question comes first')
        with mock.patch.object(self.service.automatic,'request_start') as start:
            with self.assertRaisesRegex(ValueError,'series is asked next'):
                self.service.approve_book(row['id'],row['revision'])
        start.assert_not_called()
        self.assertEqual(self.service.jobs.status()['jobs'],[])
        self.service.automatic.start();self.finish_run()
        fresh=self.service.reviews._row('Audiobooks',row['id'])
        self.assertEqual(self.ask(fresh).get('why'),'title_series','the author answer must not loop')
        self.assertEqual((self.ask(rows['2']).get('kind'),self.ask(rows['2']).get('why')),sibling_question,'only the clicked book was invalidated')
        self.assertEqual(self.service.jobs.status()['jobs'],[],'the saved author answer released no sibling book')
        self.service.approve_book(fresh['id'],fresh['revision']);self.start_and_wait()
        self.assertEqual(len(self.service.jobs.status()['jobs']),1)
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'completed')

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
        with self.assertRaisesRegex(ValueError,'series is asked next'):
            self.service.approve_book(row['id'],row['revision'],author='James Rollins')
        self.assertEqual(author_rules.load(self.inv.database).same_as('Джеймс Роллинс'),'Rollins James')

    def test_m10_same_author_answer_waits_for_start_then_asks_series(self):
        import author_rules
        rows=self.books('Dean Koonts')
        with connect(self.inv.database) as db:
            author_rules.setup(db);author_rules.append(db,'keep','Koontz Dean',actor='user',source='test')
        self.held(rows);row=rows['1']
        self.assertEqual(self.ask(row)['kind'],'same_author')
        with mock.patch.object(self.service.automatic,'request_start') as start:
            with self.assertRaisesRegex(ValueError,'series is asked next'):
                self.service.approve_book(row['id'],row['revision'],choice='same')
        start.assert_not_called()
        self.assertEqual(author_rules.load(self.inv.database).same_as('Dean Koonts'),'Koontz Dean')
        self.assertEqual(self.service.jobs.status()['jobs'],[])
        self.service.automatic.start();self.finish_run()
        self.assertEqual([self.ask(rows[k]).get('why') for k in '12'],['title_series']*2)

    def test_m10_english_spelling_answer_waits_for_start(self):
        import author_rules
        rows=self.books('Джеймс Роллинс')
        with mock.patch.object(self.service.automatic.research,'_author_latin',return_value=None):self.held(rows)
        row=rows['1'];self.assertEqual(self.ask(row)['why'],'english_spelling')
        with mock.patch.object(self.service.automatic,'request_start') as start:
            with self.assertRaisesRegex(ValueError,'series is asked next'):
                self.service.approve_book(row['id'],row['revision'],author='James Rollins')
        start.assert_not_called()
        self.assertEqual(author_rules.load(self.inv.database).same_as('Джеймс Роллинс'),'Rollins James')
        self.assertEqual(self.service.jobs.status()['jobs'],[])
        self.service.automatic.start();self.finish_run()
        self.assertEqual([self.ask(rows[k]).get('why') for k in '12'],['title_series']*2)


if __name__=='__main__':unittest.main()

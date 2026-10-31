"""0.24.0 (rulings 68, 71d, 71f, 71m; Judy's 0.23.1 spec sections 3, 5, 6): end to end on private audio, offline.
One folder holds one book after a regroup; an unfinished job of part of a folder is set aside and the folder regroups; a
foreign author in Cyrillic is re-checked once before a job runs; a gap in a settled folder is a Missing files row; the
raised folder question can be answered "Keep as separate books"; list rows say where their files are."""
import json,os,unittest
from pathlib import Path

import test_approve_as_is
from test_approve_as_is import tone
from scanner import connect
from scan_wait import finish_scan


class FolderRegroupTests(test_approve_as_is.ApproveFixture):
    def research_all(self):
        for row in self.service.reviews.page()['rows']:
            result=self.research(row)
            state='Held' if result.get('reasons') and not result.get('wait') else 'Waiting for source' if result.get('wait') else 'Queued'
            self.service.automatic._record(row,state,dict(result,until_change=state=='Held'),None)

    def rows(self):
        return {row['title_clue']:row for row in self.service.reviews.page()['rows']}

    def rescan(self):
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        return self.service.reviews.page()['rows']

    def test_unfinished_job_of_part_of_a_folder_is_set_aside_and_the_folder_regroups(self):
        folder=self.audio/'Unsorted'/'Тихий ветер'
        tone(folder/'01.mp3',self.cover,album='Тихий ветер',artist='Иван Петров',track='1')
        rows=self.start();self.assertEqual(len(rows),1)
        approved=self.service.approve_book(rows[0]['id'],rows[0]['revision'])
        job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'pending')
        # A story tagged with its own album: the 0.23 per-file grouping made it a book of its own, as it did for the 26 jobs.
        tone(folder/'02.mp3',self.cover,album='Рассказ',artist='Иван Петров',track='2')
        rows=self.rescan()
        held=[r for r in rows if (r.get('folder_unit') or {}).get('kind')=='remainder']
        self.assertEqual([len(r['members']) for r in held],[1],'the new file is held beside the queued part, never joined to it')
        with connect(self.inv.database) as db:raw=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(approved['job_id'],)).fetchone())
        self.assertTrue(self.service._names_stale(raw),'the claim check never starts a part of a folder')
        self.assertEqual(self.service.regroup_partial_jobs(),[approved['job_id']])
        with connect(self.inv.database) as db:
            state=db.execute('SELECT state,reason FROM audio_jobs WHERE job_id=?',(approved['job_id'],)).fetchone()
            aside=db.execute('SELECT kind FROM audio_job_set_aside WHERE job_id=?',(approved['job_id'],)).fetchone()
        self.assertEqual((state[0],state[1],aside[0]),('needs attention',self.service.REGROUP_REASON,'regroup'))
        rows=self.service.reviews.page()['rows']
        self.assertEqual([len(r['members']) for r in rows],[2],'the whole folder is one book now')
        self.assertEqual(self.service.regroup_partial_jobs(),[],'once')

    def test_gap_in_a_settled_folder_is_listed_under_missing_files(self):
        folder=self.audio/'Unsorted'/'Око мира'
        for n in (1,2,4):tone(folder/('%02d.mp3'%n),self.cover,album='Око мира',artist='Сергей Лукьяненко')
        self.start();self.research_all()
        needs=self.service.needs_you()
        self.assertEqual([entry['group'] for entry in needs.values()],['files_missing'],needs)
        hold=next(iter(needs.values()))['hold']
        self.assertEqual((hold['kind'],hold['missing'],hold['total']),('missing_parts',[3],4))
        row=self.service.reviews.page(status='output_attention')['rows'][0]
        self.assertEqual(row['ask']['numbers']['skipped'],['03'])
        # Futaba's 0.24.0 QA, m2: the file names number these parts (the tags carry no track numbers here), and the row
        # says so: its hint named "the track tags" for every gap.
        self.assertEqual((row['ask']['missing']['parts'],row['ask']['missing']['source']),([3],'names'))

    def test_order_question_says_membership_is_settled_and_rows_say_where_their_files_are(self):
        folder=self.audio/'Unsorted'/'Око мира'
        for name in ('Пролог.mp3','Глава 1.mp3','Глава 2.mp3'):tone(folder/name,self.cover,album='Око мира',artist='Сергей Лукьяненко',title=name[:-4])
        self.start();self.research_all()
        row=self.service.reviews.page(status='output_attention')['rows'][0]
        self.assertEqual(row['ask']['kind'],'order_unclear');self.assertEqual(row['ask']['membership'],'established')
        self.assertEqual(row['source_directory_count'],1);self.assertEqual(row['source_state'],'present')
        self.assertEqual(row['source_directories'][0]['path'],str(folder));self.assertEqual(row['source_directories'][0]['files'],3)
        opened=[]
        self.service.dispatch_folder=lambda directory:opened.append(directory)
        self.service.open_folder('Audiobooks','candidates',row['id'],directory_id=row['source_directories'][0]['id'])
        self.assertEqual(opened,[str(folder)],'the row id opens that folder')

    def test_a_held_row_says_the_series_approve_files_it_in(self):
        # Judy 0.23.1 section 8.4 (2026-10-29, Tolkien «Властелин Колец» 1): the row carries the series Approve uses.
        folder=self.audio/'Сергей Лукьяненко'/'Дозоры'/'2. Дневной дозор'
        for name in ('Пролог.mp3','Глава 1.mp3','Глава 2.mp3'):tone(folder/name,self.cover,album='Дневной дозор',artist='Сергей Лукьяненко',title=name[:-4])
        self.start();self.research_all()
        row=self.service.reviews.page(status='output_attention')['rows'][0]
        preview=self.service.approval_preview(row['id'],row['revision'])
        self.assertEqual(preview.get('series'),{'name':'Дозоры','number':'2'},'positive control: Approve files it in the series')
        self.assertEqual((row['ask']['kind'],row['ask']['series']),('order_unclear',{'name':'Дозоры','number':'2','basis':'research'}))
        self.assertNotIn('series_clue',row['ask'])

    def test_raised_folder_question_and_keep_as_separate_books(self):
        folder=self.audio/'Unsorted'/'Разное'
        tone(folder/'Альфа.mp3',self.cover,album='Альфа',artist='Сергей Лукьяненко')
        tone(folder/'Бета.mp3',self.cover,album='Бета',artist='Сергей Лукьяненко')
        rows=self.start();self.assertEqual([len(r['members']) for r in rows],[2]);self.research_all()
        row=self.service.reviews.page(status='output_attention')['rows'][0]
        self.assertEqual((row['ask']['kind'],row['ask']['cause']),('files_unclear','folder_books'))
        self.assertEqual(row['ask']['facts']['works'],[{'name':'Альфа','files':1},{'name':'Бета','files':1}])
        self.assertEqual(self.service.keep_separate(row['id'],row['revision']),{'kept':2})
        self.assertEqual(sorted(len(r['members']) for r in self.service.reviews.page()['rows']),[1,1])

    def test_foreign_author_in_cyrillic_is_rechecked_once_before_a_job_runs(self):
        folder=self.audio/'Unsorted'/'Дюна'
        for n in (1,2):tone(folder/('%02d.mp3'%n),self.cover,album='Дюна',artist='Фрэнк Герберт',track='%d/2'%n)
        rows=self.start()
        approved=self.service.approve_book(rows[0]['id'],rows[0]['revision'],author='Herbert Frank')
        with connect(self.inv.database) as db:
            raw=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(approved['job_id'],)).fetchone())
        self.assertFalse(self.service._names_stale(raw),'an English author never needs the re-check')
        self.assertEqual(json.loads(raw['manifest'])['metadata_facts']['research_version'],__import__('public_research').RESEARCH_VERSION)
        # A job planned before 0.24.0 (no research version in its facts) that files the author in Cyrillic:
        manifest=json.loads(raw['manifest']);manifest['metadata']=dict(manifest['metadata'],author='Герберт Фрэнк')
        manifest['metadata_facts']={k:v for k,v in manifest['metadata_facts'].items() if k!='research_version'}
        cyrillic=dict(raw,manifest=json.dumps(manifest,ensure_ascii=False))
        self.assertTrue(self.service._names_stale(cyrillic))
        self.assertEqual(self.service._replan_reasons[approved['job_id']],self.service.RECHECK_REASON)
        with connect(self.inv.database) as db:
            db.execute("CREATE TABLE IF NOT EXISTS audio_job_set_aside(job_id TEXT PRIMARY KEY,candidate_id TEXT NOT NULL,revision INTEGER NOT NULL,kind TEXT NOT NULL,at TEXT NOT NULL)")
            db.execute("INSERT INTO audio_job_set_aside VALUES('older',?,1,'recheck','now')",(manifest['candidate_id'],))
        self.assertFalse(self.service._names_stale(cyrillic),'re-checked once: its research decides after that')
        planned_now=dict(raw,manifest=json.dumps(dict(json.loads(raw['manifest']),metadata=manifest['metadata']),ensure_ascii=False))
        self.assertFalse(self.service._names_stale(planned_now),'a job planned under this research is never re-checked')


if __name__=='__main__':
    unittest.main()

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

    def number_unclear_book(self):
        """Ruling 74b's book on real files: «Хранители. Летопись первая», which FantLab numbers book 2 (FantLab's live answer
        shapes of 2026-10-31, the novels' order changed). Researched twice, as the run does: the first research learns the
        English spelling (a rule deciding the book's own credit), so the run researches it once more before listing it
        (rules_changed_for, Senua's 0.22.0 review G6). Returns its to-do row."""
        import urllib.parse
        from public_research import PublicClient,PublicResearch
        folder=self.audio/'Unsorted'/'Хранители. Летопись первая'
        for n in (1,2):tone(folder/('%02d.mp3'%n),self.cover,album='Хранители. Летопись первая',artist='Джон Рональд Руэл Толкин',track='%d/2'%n)
        self.start()
        def fetch(url,*_):
            parts=urllib.parse.urlsplit(url)
            if parts.hostname=='api.fantlab.ru' and parts.path=='/search-works':
                found=[{'work_id':1667,'name':'The Fellowship of the Ring','rusname':'Братство Кольца','altname':'Хранители кольца; Хранители','all_autor_name':'J. R. R. Tolkien',
                        'all_autor_rusname':'Дж. Р. Р. Толкин'}] if urllib.parse.parse_qs(parts.query)['q'][0]=='Хранители' else []
                return json.dumps(found,ensure_ascii=False).encode()
            if parts.hostname=='api.fantlab.ru' and parts.path=='/work/1693/extended':
                return json.dumps({'work_id':1693,'work_name':'Властелин Колец','work_type_id':13,'children':[{'work_id':n,'work_type_id':1,'deep':1,'plus':None} for n in (1668,1667,1669)]},ensure_ascii=False).encode()
            if parts.hostname=='api.fantlab.ru' and parts.path=='/work/1667/extended':
                return json.dumps({'work_id':1667,'work_name':'Братство Кольца','work_name_orig':'The Fellowship of the Ring','work_type_id':1,'work_type_name':'novel','lang_code':'en',
                                   'authors':[{'type':'autor','name':'Дж. Р. Р. Толкин','name_orig':'J. R. R. Tolkien'}],
                                   'parents':{'cycles':[[{'work_id':1693,'work_name':'Властелин Колец','work_type_id':13}]]}},ensure_ascii=False).encode()
            if parts.hostname=='www.goodreads.com':return b'<html><body><table class="tableList"></table></body></html>'
            if parts.hostname=='www.wikidata.org':return json.dumps({'search':[],'entities':{}}).encode()
            return b'{"items":[],"results":[],"docs":[]}'
        minutes=iter(range(10**6,10**9,60))  # no pacing wait; the cache stays fresh
        self.service.automatic.research=PublicResearch(PublicClient(self.inv.database,fetch=fetch,clock=lambda:next(minutes)),leads=[])
        self.research_all();self.research_all()
        return self.service.reviews.page(status='output_attention')['rows'][0]

    def queued_metadata(self,approved):
        job=next(j for j in self.service.jobs.status()['jobs'] if j['job_id']==approved['job_id'])
        return job['manifest']['metadata'],job['manifest']['destination']

    def test_number_unclear_reaches_the_row_and_approve_as_shown_files_the_series_74b(self):
        """Ruling 74b, both ends: the to-do row (needs_you, ask_payload) carries both numbers and the provider with Series,
        Number and Title filled in; Approve with them untouched (a press that sends none) queues the book with that series
        and the title's number. Senua's 74b review, r2: the disagreeing record's English title is not used."""
        row=self.number_unclear_book();ask=row['ask']
        self.assertEqual((ask['kind'],ask['why'],ask['odd_name']),('title_author','number_unclear',True))
        self.assertEqual(ask['volume'],{'title_number':1,'series_number':'2','provider':'fantlab'})
        self.assertEqual({name:ask['fields'][name]['proposal'] for name in ('title','author','series','number')},
                         {'title':'Хранители. Летопись первая','author':'Tolkien J. R. R.','series':'Властелин колец','number':'1'})
        self.assertEqual(self.service.approval_preview(row['id'],row['revision']).get('series'),{'name':'Властелин колец','number':'1'},'its Goes to line')
        metadata,destination=self.queued_metadata(self.service.approve_book(row['id'],row['revision']))  # nothing typed
        self.assertEqual((metadata['title'],metadata['canonical_author'],metadata['series'],metadata['number']),('Хранители. Летопись первая','Tolkien J. R. R.','Властелин колец','1'))
        self.assertIn(os.path.join('Tolkien J. R. R','Властелин колец',''),destination)

    def test_a_book_held_for_another_reason_never_takes_the_disagreeing_series_r1(self):
        """Senua's 74b review, r1: the same book and the same disagreement in the research cache, but its current question is
        another one (here: one part of a bigger book). An Approve that sends no Series or Number, and its Goes to line, file
        no series: only the "Number unclear" question fills them in."""
        import local_identity
        row=self.number_unclear_book()
        fresh=self.service.reviews._row('Audiobooks',row['id'])
        result=self.research(fresh)
        self.assertEqual((result.get('ask') or {}).get('why'),'number_unclear','positive control: the cache holds the disagreement')
        self.service.automatic._record(fresh,'Held',dict(result,ask=None,reasons=[local_identity.PIECE_REASON],identity_hold={'kind':'piece','detail':''},until_change=True),None)
        self.assertFalse(self.service.approval_preview(row['id'],row['revision']).get('series'),'its Goes to line names no series')
        metadata,_=self.queued_metadata(self.service.approve_book(row['id'],row['revision']))
        self.assertEqual((metadata['title'],metadata['series'],metadata['number']),('Хранители. Летопись первая','',''))

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

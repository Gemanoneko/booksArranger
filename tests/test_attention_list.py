"""The one to-do list (Sergei 2026-10-24, ruling 10; Judy's AttentionTodo_UX spec): every book that only Sergei can
move on is in Output needs attention, grouped by reason, counted by the same predicate that lists it; stale rows are
not listed. Real private audio fixtures; no network, no library access."""
import os,shutil,unittest
from pathlib import Path
import test_approve_as_is
from test_approve_as_is import tone
from scan_wait import finish_scan


class AttentionListTests(test_approve_as_is.ApproveFixture):
    """Reuses the Approve fixture: a separate Sorted folder, the production policy, offline research."""
    def research_all(self):
        for row in self.service.reviews.page()['rows']:
            result=self.research(row)
            state='Held' if result.get('reasons') and not result.get('wait') else 'Waiting for source' if result.get('wait') else 'Queued'
            self.service.automatic._record(row,state,dict(result,until_change=state=='Held'),None)

    def listed(self,group=None):
        page=self.service.reviews.page(status='output_attention',group=group)
        return {row['title_clue']:row for row in page['rows']},page['total']

    def counts(self):return self.service.state()['attention_counts']

    def test_every_book_only_sergei_can_move_on_is_listed_under_its_reason(self):
        tone(self.audio/'Unsorted'/'Утро снайпера'/'01.mp3',self.cover,album='Утро снайпера')                                    # no author
        tone(self.audio/'Unsorted'/'Тайна'/'Тайна.mp3',self.cover,title='Тайна',artist='Лев Толстой',album_artist='Антон Чехов')  # two people
        tone(self.audio/'Unsorted'/'Брат мой'/'Пролог.mp3',self.cover,album='Брат мой',artist='Иван Петров')
        tone(self.audio/'Unsorted'/'Брат мой'/'Финал.mp3',self.cover,album='Брат мой',artist='Иван Петров')                     # order unknown
        tone(self.audio/'Unsorted'/'Ясно'/'Ясно.mp3',self.cover,album='Ясно',artist='Иван Петров')                               # identified
        self.start();self.research_all()
        self.assertEqual(self.listed()[1],3,'positive control: before 0.22.0 the list held only failed jobs, so 0')
        rows,_=self.listed('title_author');self.assertEqual(list(rows),['Утро снайпера'])
        ask=rows['Утро снайпера']['ask'];self.assertEqual(ask['kind'],'title_author')
        self.assertEqual(ask['destination']['path'],str(Path('Без автора')/'Утро снайпера.m4b'));self.assertFalse(ask['destination']['taken'])
        rows,_=self.listed('author_unclear');self.assertEqual(list(rows),['Тайна']);self.assertEqual([c['name'] for c in rows['Тайна']['ask']['candidates']],['Лев Толстой','Антон Чехов'])
        rows,_=self.listed('order_unclear');self.assertEqual(list(rows),['Брат мой'])  # 0.22.0 review (Judy, B3): its own chip, not "Needs you" under Other
        counts=self.counts();self.assertEqual((counts['title_author'],counts['author_unclear'],counts['order_unclear'],counts['other']),(1,1,1,0))
        self.assertEqual(sum(v for v in counts.values() if isinstance(v,int)),self.listed()[1],'All = the sum of the chips')

    def test_inside_a_reason_books_sort_by_folder_then_title_with_numbers_in_natural_order(self):
        # Judy's section 1: the parts of one set sit together, part 2 before part 10.
        for n in (10,2,1):tone(self.audio/'Unsorted'/'Набор'/('Часть %d'%n)/'01.mp3',self.cover,album='Безымянная %d'%n)
        self.start();self.research_all()
        page=self.service.reviews.page(status='output_attention',group='title_author')
        self.assertEqual([r['title_clue'] for r in page['rows']],['Безымянная 1','Безымянная 2','Безымянная 10'])

    def test_an_odd_name_question_is_marked_so_the_page_keeps_it_out_of_bulk_approve(self):
        # 0.22.1 (Judy 11.4, item 2; Jane for Sergei 2026-10-26): the row says it comes from the odd-name check, and the
        # page never takes it into Select all or bulk Approve as is. A book with no author is not marked: bulk Approve as
        # is was built for it (section 5).
        tone(self.audio/'Unsorted'/'Антитела'/'Антитела 128.mp3',self.cover,title='Антитела 128',album='Антитела 128',artist='Кевин Андерсон')
        tone(self.audio/'Unsorted'/'Утро снайпера'/'01.mp3',self.cover,album='Утро снайпера')
        self.start();self.research_all()
        rows,_=self.listed('title_author')
        odd=[row['ask'] for row in rows.values() if row['ask'].get('why')=='title_bitrate']
        self.assertEqual(len(odd),1,'positive control: the bitrate title is asked')
        self.assertIs(odd[0].get('odd_name'),True)
        self.assertIs(rows['Утро снайпера']['ask'].get('odd_name'),False)

    def test_a_suspected_reader_is_never_the_proposed_author_on_the_row(self):
        # Ruling 14: the only credit is a person named in brackets (a reader or uploader). The row asks; its Author
        # field starts empty and Goes to shows Без автора, so "Approve as is" (single or bulk) never files a reader.
        tone(self.audio/'Unsorted'/'Тайна'/'Тайна [Иван Петров].mp3',self.cover,album='Тайна',artist='Иван Петров')
        self.start();self.research_all()
        rows,_=self.listed('author_unclear');ask=rows['Тайна']['ask']
        self.assertEqual((ask['why'],[c['name'] for c in ask['candidates']]),('reader',['Иван Петров']),'positive control: the reader is offered as a choice')
        self.assertEqual(ask['fields']['author']['proposal'],'')
        self.assertEqual(ask['destination']['path'],str(Path('Без автора')/'Тайна.m4b'))

    def test_missing_files_are_listed_first_and_remove_from_list_touches_no_file(self):
        sources=[tone(self.audio/'Unsorted'/'Iron Inferno'/('Iron Inferno %d.mp3'%n),self.cover,album='Iron Inferno',artist='Иван Петров',track='%d/2'%n) for n in (1,2)]
        self.start()
        backup=self.base/'kept';backup.mkdir()
        for source in sources:shutil.copy2(source,backup/source.name);source.unlink()
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        rows,total=self.listed('files_missing');self.assertEqual(list(rows),['Iron Inferno'])
        row=rows['Iron Inferno'];self.assertEqual(row['ask']['missing']['present'],0)
        self.assertEqual(row['ask']['missing']['files'],[str(s) for s in sources],'full paths, even with the folder gone')
        self.assertEqual(row['ask']['missing']['folders'],[str(sources[0].parent)])
        self.assertEqual(self.counts()['files_missing'],1)
        self.assertFalse(self.service.scan_again(row['id'],row['revision'])['found'])
        self.service.dismiss_attention(row['id'],row['revision'])
        self.assertEqual(self.listed('files_missing')[1],0);self.assertEqual(self.counts()['files_missing'],0)
        for source in sources:shutil.copy2(backup/source.name,source)
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        self.assertEqual(self.listed('files_missing')[1],0,'the files are back: not missing any more')

    def test_scan_again_finds_a_restored_file(self):
        sources=[tone(self.audio/'Unsorted'/'Новая плоть'/('%02d.mp3'%n),self.cover,album='Новая плоть',artist='Иван Петров',track='%d/2'%n) for n in (1,2)]
        self.start();data=sources[1].read_bytes();stamp=sources[1].stat();sources[1].unlink()
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        row=self.listed('files_missing')[0]['Новая плоть']
        self.assertFalse(self.service.scan_again(row['id'],row['revision'])['found'])
        sources[1].write_bytes(data);os.utime(sources[1],ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        self.assertTrue(self.service.scan_again(row['id'],row['revision'])['found'])
        self.assertEqual(self.listed('files_missing')[1],0)

    def test_qa_m1_after_a_same_author_answer_the_partner_book_continues_too(self):
        # Futaba's 0.22.0 QA, M-1: two books by the new spelling "Dean Koonts" were asked "Same author?". Answering one
        # filed it, and the strip said "2 books continue", but the partner was never researched again: a run visits a book
        # once, the saved run had already passed it, so it sat held and listed nowhere ("Still checking") for 30+ minutes.
        import json,time,uuid
        from scanner import connect
        tone(self.audio/'Koontz Dean'/'Watchers'/'01.mp3',self.cover,album='Watchers',artist='Koontz Dean')
        known=self.start()[0];self.service.approve_book(known['id'],known['revision']);self.start_and_wait()
        for name in ('Ticktock','Intensity'):tone(self.audio/'Unsorted'/name/'01.mp3',self.cover,album=name,artist='Dean Koonts')
        self.inv.launch('Audiobooks');finish_scan(self.inv);self.research_all()
        rows,_=self.listed('same_author');self.assertEqual(sorted(rows),['Intensity','Ticktock'],'positive control: both asked')
        # The run that researched them is saved (Stop), both visited: Start continues it.
        with connect(self.inv.database) as db:
            db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(str(uuid.uuid4()),'Paused','research',json.dumps({'pending':[],'done':[r['id'] for r in rows.values()],'deferred':[]}),'','t','t'))
        one=rows['Ticktock']
        self.service.approve_book(one['id'],one['revision'],choice='same');self.start_and_wait()
        self.service.automatic.start()
        limit=time.monotonic()+90
        while self.service.automatic.status()['state'] not in ('Completed','Needs attention','Idle'):
            if time.monotonic()>limit:self.fail('automatic processing did not finish: %r'%self.service.automatic.status())
            time.sleep(.2)
        self.wait()
        jobs={job['manifest']['metadata']['title']:job for job in self.service.jobs.status()['jobs']}
        self.assertEqual(sorted(jobs),['Intensity','Ticktock','Watchers'],'the partner continued: researched again and converted')
        self.assertEqual(jobs['Intensity']['manifest']['metadata']['canonical_author'],'Koontz Dean','under the answered author')
        self.assertEqual(self.service.todo_coverage()['still_checking'],0)

    def test_a_job_whose_book_was_converted_since_is_stale_and_never_counted(self):
        tone(self.audio/'Unsorted'/'Ясно'/'Ясно.mp3',self.cover,album='Ясно',artist='Иван Петров')
        row=self.start()[0]
        summary={'old-job':{'group':'retry'},'live-job':{'group':'other'}}
        jobs=[{'job_id':'old-job','state':'needs attention','manifest':{'candidate_id':row['id']}},
              {'job_id':'live-job','state':'needs attention','manifest':{'candidate_id':'not-current'}}]
        self.assertEqual(self.service.stale_attention(summary,jobs,{row['id']}),{},'converted since, and a regrouped book')
        self.assertEqual(self.service.stale_attention(summary,jobs,set()),{'old-job':{'group':'retry'}},'positive control')


if __name__=='__main__':unittest.main()

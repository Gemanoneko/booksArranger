"""The one to-do list (Sergei 2026-10-24, ruling 10; Judy's AttentionTodo_UX spec): every book that only Sergei can
move on is in Output needs attention, grouped by reason, counted by the same predicate that lists it; stale rows are
not listed. Real private audio fixtures; no network, no library access."""
import os,shutil,unittest
from pathlib import Path
import test_approve_as_is
from test_approve_as_is import tone


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
        rows,_=self.listed('other');self.assertEqual(list(rows),['Брат мой'])
        counts=self.counts();self.assertEqual((counts['title_author'],counts['author_unclear'],counts['other']),(1,1,1))
        self.assertEqual(sum(v for v in counts.values() if isinstance(v,int)),self.listed()[1],'All = the sum of the chips')

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
        self.inv.launch('Audiobooks');self.inv.worker.join(10)
        rows,total=self.listed('files_missing');self.assertEqual(list(rows),['Iron Inferno'])
        row=rows['Iron Inferno'];self.assertEqual(row['ask']['missing']['present'],0)
        self.assertEqual(row['ask']['missing']['files'],[str(s) for s in sources],'full paths, even with the folder gone')
        self.assertEqual(row['ask']['missing']['folders'],[str(sources[0].parent)])
        self.assertEqual(self.counts()['files_missing'],1)
        self.assertFalse(self.service.scan_again(row['id'],row['revision'])['found'])
        self.service.dismiss_attention(row['id'],row['revision'])
        self.assertEqual(self.listed('files_missing')[1],0);self.assertEqual(self.counts()['files_missing'],0)
        for source in sources:shutil.copy2(backup/source.name,source)
        self.inv.launch('Audiobooks');self.inv.worker.join(10)
        self.assertEqual(self.listed('files_missing')[1],0,'the files are back: not missing any more')

    def test_scan_again_finds_a_restored_file(self):
        sources=[tone(self.audio/'Unsorted'/'Новая плоть'/('%02d.mp3'%n),self.cover,album='Новая плоть',artist='Иван Петров',track='%d/2'%n) for n in (1,2)]
        self.start();data=sources[1].read_bytes();stamp=sources[1].stat();sources[1].unlink()
        self.inv.launch('Audiobooks');self.inv.worker.join(10)
        row=self.listed('files_missing')[0]['Новая плоть']
        self.assertFalse(self.service.scan_again(row['id'],row['revision'])['found'])
        sources[1].write_bytes(data);os.utime(sources[1],ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        self.assertTrue(self.service.scan_again(row['id'],row['revision'])['found'])
        self.assertEqual(self.listed('files_missing')[1],0)

    def test_a_job_whose_book_was_converted_since_is_stale_and_never_counted(self):
        tone(self.audio/'Unsorted'/'Ясно'/'Ясно.mp3',self.cover,album='Ясно',artist='Иван Петров')
        row=self.start()[0]
        summary={'old-job':{'group':'retry'},'live-job':{'group':'other'}}
        jobs=[{'job_id':'old-job','state':'needs attention','manifest':{'candidate_id':row['id']}},
              {'job_id':'live-job','state':'needs attention','manifest':{'candidate_id':'not-current'}}]
        self.assertEqual(self.service.stale_attention(summary,jobs,{row['id']}),{},'converted since, and a regrouped book')
        self.assertEqual(self.service.stale_attention(summary,jobs,set()),{'old-job':{'group':'retry'}},'positive control')


if __name__=='__main__':unittest.main()

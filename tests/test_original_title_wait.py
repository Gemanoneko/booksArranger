"""Ruling 38 end to end (Sergei 2026-10-27; it replaces the waiting part of ruling 29): a translation with only its Russian
title never waits for its English original title. Automatic processing converts it right away under the title it has,
in the English author folder, and it is never listed under Held. Ruling 39: a foreign author credited only in Cyrillic
whose English spelling research doesn't find is asked once; Sergei's answer is a lasting rule for that author. Real
private audio, offline research, a separate Sorted folder."""
import time
import unittest
from pathlib import Path

from test_approve_as_is import ApproveFixture, tone


class TranslationConvertsNowTests(ApproveFixture):
    def test_automatic_processing_converts_a_translation_with_no_english_title_at_once(self):
        tone(self.audio / 'Roger Zelazny' / 'Джек из Тени' / 'Джек из Тени.mp3', self.cover, album='Джек из Тени', title='Джек из Тени', artist='Roger Zelazny')
        row = self.start()[0]
        result = self.research(row)
        self.assertEqual((result['reasons'], result.get('wait')), ([], None), 'no "Waiting for the original title"')
        self.service.automatic.start()
        limit = time.monotonic() + 90
        while self.service.automatic.status()['state'] not in ('Completed', 'Needs attention', 'Idle'):
            if time.monotonic() > limit:
                self.fail('automatic processing did not finish: %r' % self.service.automatic.status())
            time.sleep(.2)
        self.wait()
        jobs = self.service.jobs.status()['jobs']
        self.assertEqual(len(jobs), 1, 'converted by itself, with no Approve')
        self.assertEqual(jobs[0]['state'], 'completed', jobs[0])
        self.assertEqual(Path(jobs[0]['output']['final_path']), self.sorted / 'Zelazny Roger' / 'Джек из Тени - Zelazny Roger.m4b', 'its title, the English author folder')
        self.assertEqual(jobs[0]['manifest']['metadata_facts']['original_title_lookup'], {'state': 'none', 'title': ''})
        held = [r for r in self.service.reviews.page(status='held')['rows'] if r['id'] == row['id']]
        self.assertEqual(held, [], 'never listed under Held')


class CachedSpellingConvertsTests(ApproveFixture):
    def test_m1_a_book_whose_cached_record_learns_the_english_name_converts_under_it(self):
        # Futaba's 0.22.3 QA, M-1: the research cache's FantLab record for «Волшебники» taught the rule «Лев Гроссман» to
        # Grossman Lev, but the book then stayed Held "Local identity evidence changed" with no question, in every run.
        from unittest.mock import patch
        tone(self.audio / 'Fantasy' / 'Волшебники' / 'Волшебники.mp3', self.cover, album='Волшебники', title='Волшебники', artist='Лев Гроссман')
        self.start()
        research = self.service.automatic.research
        catalog = {'provider': 'fantlab', 'work_id': 'fantlab:1001', 'language': 'en', 'original_title': 'The Magicians', 'title_native': 'Волшебники',
                   'author_native': 'Лев Гроссман', 'author_latin': 'Lev Grossman', 'source_url': 'https://fantlab.ru/work1001'}
        real = research._gap_fill
        gap = lambda local, title, *a, **k: {'catalog': dict(catalog), 'closed': [], 'unfilled': []} if title == 'Волшебники' else real(local, title, *a, **k)
        with patch.object(research, '_gap_fill', side_effect=gap):
            self.service.automatic.start()
            limit = time.monotonic() + 90
            while self.service.automatic.status()['state'] not in ('Completed', 'Needs attention', 'Idle'):
                if time.monotonic() > limit:
                    self.fail('automatic processing did not finish: %r' % self.service.automatic.status())
                time.sleep(.2)
            self.wait()
        jobs = self.service.jobs.status()['jobs']
        held = [(r['status'], (r.get('automatic') or {}).get('reasons')) for r in self.service.reviews.page(status='held')['rows']]
        self.assertEqual(len(jobs), 1, ('converted by itself', held))
        self.assertEqual(jobs[0]['state'], 'completed', jobs[0])
        self.assertEqual(Path(jobs[0]['output']['final_path']).parent, self.sorted / 'Grossman Lev', 'ruling 39: the English folder')


class Ruling49Tests(ApproveFixture):
    def test_approve_files_a_russian_edition_under_the_original_english_title_as_automatic_filing_does(self):
        # Ruling 49 (Sergei 2026-10-27, "The Magicians - Grossman Lev"): Futaba's 0.22.3 QA saw automatic filing use the
        # catalog's original title while a manual Approve of the same book gave «Волшебники - Grossman Lev.m4b».
        from unittest.mock import patch
        import author_rules, contextlib, sqlite3
        tone(self.audio / 'Fantasy' / 'Волшебники' / 'Волшебники.mp3', self.cover, album='Волшебники', title='Волшебники', artist='Лев Гроссман')
        row = self.start()[0]
        with contextlib.closing(sqlite3.connect(self.inv.database)) as db:
            author_rules.setup(db); author_rules.append(db, 'same_as', 'Лев Гроссман', target='Grossman Lev', actor='assistant', source='https://fantlab.ru/work1001'); db.commit()
        research = self.service.automatic.research
        catalog = {'provider': 'fantlab', 'work_id': 'fantlab:1001', 'language': 'en', 'original_title': 'The Magicians', 'title_native': 'Волшебники',
                   'author_native': 'Лев Гроссман', 'author_latin': 'Lev Grossman', 'source_url': 'https://fantlab.ru/work1001'}
        real = research._gap_fill
        gap = lambda local, title, *a, **k: {'catalog': dict(catalog), 'closed': [], 'unfilled': []} if title == 'Волшебники' else real(local, title, *a, **k)
        expected = str(Path('Grossman Lev') / 'The Magicians - Grossman Lev.m4b')
        with patch.object(research, '_gap_fill', side_effect=gap):
            self.assertEqual(self.research(row)['review']['title'], 'The Magicians', 'automatic filing: already the original title')
            typed = self.service.approval_preview(row['id'], row['revision'], title='Волшебники (аудиокнига)')
            self.assertEqual(typed['path'], str(Path('Grossman Lev') / 'Волшебники (аудиокнига) - Grossman Lev.m4b'), 'a title he types wins')
            preview = self.service.approval_preview(row['id'], row['revision'])
            self.assertEqual(preview['path'], expected, 'Approve: the original English title')
            approved = self.service.approve_book(row['id'], row['revision'], path=preview['path']); self.wait()
        job = next(j for j in self.service.jobs.status()['jobs'] if j['job_id'] == approved['job_id'])
        self.assertEqual(job['state'], 'completed', job)
        self.assertEqual(Path(job['output']['final_path']), self.sorted / expected)

    def test_approve_keeps_the_shown_title_without_an_english_original(self):
        # Controls: no catalog record (offline, nothing cached), or a Russian original: the title shown is filed.
        from unittest.mock import patch
        tone(self.audio / 'Fantasy' / 'Волшебники' / 'Волшебники.mp3', self.cover, album='Волшебники', title='Волшебники', artist='Лев Гроссман')
        row = self.start()[0]
        self.assertEqual(Path(self.service.approval_preview(row['id'], row['revision'])['path']).name, 'Волшебники - Гроссман Лев.m4b')
        research = self.service.automatic.research
        catalog = {'provider': 'fantlab', 'work_id': 'fantlab:7', 'language': 'ru', 'original_title': 'Волшебники', 'title_native': 'Волшебники',
                   'author_native': 'Лев Гроссман', 'author_latin': '', 'source_url': 'https://fantlab.ru/work7'}
        with patch.object(research, '_gap_fill', return_value={'catalog': catalog, 'closed': [], 'unfilled': []}):
            self.service.__dict__.pop('_approval_results', None)
            self.assertEqual(Path(self.service.approval_preview(row['id'], row['revision'])['path']).name, 'Волшебники - Гроссман Лев.m4b')


class EnglishSpellingAnswerTests(ApproveFixture):
    """Ruling 39: no English spelling found online for a foreign author credited only in Cyrillic: the row asks (Author
    unclear); Sergei's answer is his lasting rule for that author, so his other books are never asked again."""
    def books(self):
        for title in ('Голиаф', 'Левиафан'):
            tone(self.audio / 'Unsorted' / title / (title + '.mp3'), self.cover, album=title, title=title, artist='Скотт Вестерфельд')
        self.start()
        found = {}
        for row in self.service.reviews.page()['rows']:
            name = 'Голиаф' if 'Голиаф' in row['members'][0]['path'] else 'Левиафан'
            result = self.research(row)
            self.assertEqual((result['ask']['kind'], result['ask']['why']), ('author_unclear', 'english_spelling'), 'positive control: offline, asked')
            self.service.automatic._record(row, 'Held', dict(result, until_change=True), None)
            found[name] = row
        return found

    def rules(self):
        import sqlite3, contextlib
        with contextlib.closing(sqlite3.connect(self.inv.database)) as db:
            return [tuple(r) for r in db.execute("SELECT kind, target, actor FROM author_rules WHERE rule_id NOT LIKE 'seed-%' ORDER BY saved_utc")]

    def test_his_typed_english_spelling_files_this_book_and_becomes_the_rule_for_the_other(self):
        books = self.books()
        row = books['Голиаф']
        approved = self.service.approve_book(row['id'], row['revision'], author='Scott Westerfeld'); self.wait()
        job = next(j for j in self.service.jobs.status()['jobs'] if j['job_id'] == approved['job_id'])
        self.assertEqual(job['state'], 'completed', job)
        self.assertEqual(Path(job['output']['final_path']), self.sorted / 'Westerfeld Scott' / 'Голиаф - Westerfeld Scott.m4b')
        self.assertEqual(self.rules(), [('same_as', 'Westerfeld Scott', 'user')], 'his answer, kept for the author')
        other = self.research(books['Левиафан'])
        self.assertEqual(other['reasons'], [], 'the other book is not asked again')
        self.assertEqual(other['review']['canonical_author'], 'Westerfeld Scott')

    def test_approving_the_name_as_shown_keeps_it_for_the_author(self):
        books = self.books()
        row = books['Голиаф']
        approved = self.service.approve_book(row['id'], row['revision']); self.wait()
        job = next(j for j in self.service.jobs.status()['jobs'] if j['job_id'] == approved['job_id'])
        self.assertEqual(Path(job['output']['final_path']), self.sorted / 'Вестерфельд Скотт' / 'Голиаф - Вестерфельд Скотт.m4b')
        self.assertEqual(self.rules(), [('keep', '', 'user')])
        other = self.research(books['Левиафан'])
        self.assertEqual(other['reasons'], [], 'never asked again')
        preview = self.service.approval_preview(books['Левиафан']['id'], books['Левиафан']['revision'])
        self.assertEqual(Path(preview['path']).parts[0], 'Вестерфельд Скотт', 'the same folder')

    def test_a_refused_approve_saves_no_spelling_rule(self):
        # Senua's 0.22.2 review, m7: the rule was saved (and his other books requeued) before the Approve could be refused.
        books = self.books()
        row = books['Голиаф']
        with self.assertRaisesRegex(ValueError, 'Destination changed since it was shown'):
            self.service.approve_book(row['id'], row['revision'], author='Scott Westerfeld', path='Somewhere Else\\Голиаф.m4b')
        self.assertEqual(self.rules(), [], 'no rule from a refused Approve')
        self.assertEqual(self.research(books['Левиафан'])['ask']['why'], 'english_spelling', 'the other book is still asked')
        # Positive control: the same answer on an accepted Approve is his rule.
        self.service.approve_book(row['id'], row['revision'], author='Scott Westerfeld'); self.wait()
        self.assertEqual(self.rules(), [('same_as', 'Westerfeld Scott', 'user')])


    def test_a_learned_rule_taken_back_is_listed_then_asked_never_looked_up_again(self):
        # 0.22.3 (Judy 4; her question 1, its default): the list shows what research learned online; after Take back the
        # author is asked once (ruling 39's question), and the same online match is never looked up and learned again.
        from unittest.mock import patch
        books = self.books()
        research = self.service.automatic.research
        found = {'state': 'found', 'name': 'Scott Westerfeld', 'source_url': 'https://fantlab.ru/work9', 'title': ''}
        with patch.object(research, '_author_latin', return_value=found) as lookup:
            result = self.research(books['Голиаф'])
        self.assertEqual((result['reasons'], lookup.call_count), ([], 1), 'positive control: looked up and filed')
        learned = self.service.learned_author_rules()
        self.assertEqual([(r['kind'], r['target'], r['source'], r['question']) for r in learned], [('same_as', 'Westerfeld Scott', 'https://fantlab.ru/work9', 'Голиаф')])
        self.assertIn('Вестерфельд', learned[0]['credit'])
        self.assertTrue(learned[0]['saved_utc'].startswith('20'))
        self.service.retract_author_rule(learned[0]['rule_id'])
        self.assertEqual(self.service.learned_author_rules(), [], 'taken back: off the list')
        with patch.object(research, '_author_latin', return_value=found) as lookup:
            result = self.research(books['Левиафан'])
        self.assertEqual(lookup.call_count, 0, 'never looked up again')
        self.assertEqual((result['ask']['kind'], result['ask']['why']), ('author_unclear', 'english_spelling'), 'asked once instead')
        self.assertEqual(self.rules(), [('same_as', 'Westerfeld Scott', 'assistant')], 'nothing new learned')


if __name__ == '__main__':
    unittest.main()

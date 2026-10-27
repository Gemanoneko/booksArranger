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


if __name__ == '__main__':
    unittest.main()

"""Ruling 53 end to end with the real automatic run (Futaba's 0.22.3 QA, M-1; Senua's 0.22.3 review, M10): a numbered set
that only confirms itself is asked; Sergei's Approve of its first book through the series question releases the rest,
which file by themselves under the series he chose, after the run has ended, after a rescan and from a paused run. An
Approve that answered another question ("Same author?", the English spelling) is no answer to the series question.
Real private audio, offline research, a separate Sorted folder."""
import json
import time
import unittest
from pathlib import Path

from scanner import connect
from scan_wait import finish_scan
from test_approve_as_is import ApproveFixture, tone


class SetReleaseTests(ApproveFixture):
    LECTURES = ((1, 'Греция'), (2, 'Рим'), (3, 'Египет'))

    def lecture_set(self, artist='Иван Петров', count=3):
        """«Курс истории. Лекция N. …»: a numbered set that only confirms itself (ruling 53), two files per book."""
        for n, name in self.LECTURES[:count]:
            for k in (1, 2):
                tone(self.audio / artist / 'Курс истории' / str(n) / ('%02d.mp3' % k), self.cover, album='Курс истории. Лекция %d. %s' % (n, name), title='Глава %d' % k, artist=artist, track='%d/2' % k)
        return {Path(r['members'][0]['path']).parent.name: r for r in self.start()}

    def finish_run(self):
        """The real automatic run (started by the test, or by a release) to its end, then the queue."""
        limit = time.monotonic() + 120
        while (self.service.automatic.thread and self.service.automatic.thread.is_alive()) or self.service.automatic.status()['state'] in ('Running', 'Stopping'):
            if time.monotonic() > limit:self.fail('automatic processing did not finish: %r' % self.service.automatic.status())
            time.sleep(.1)
        self.wait()

    def asked_now(self, row):
        current = self.service.reviews._row('Audiobooks', row['id'])
        return (self.service.automatic.candidate(current) or {}).get('ask') or {}

    def filed(self):
        return sorted(str(Path(j['output']['final_path']).relative_to(self.sorted)) for j in self.service.jobs.status()['jobs'] if j['state'] == 'completed')

    def lectures(self, folder, series, count=3):
        return sorted(str(Path(folder) / series / ('%s - %d - %s - %s.m4b' % (series, n, name, folder))) for n, name in self.LECTURES[:count])

    def test_m1_ruling_53_the_first_approved_book_releases_the_rest_after_the_run_has_ended(self):
        # Futaba's 0.22.3 QA, M-1: the run had ended with the set asked; his Approve of book 1 only called requeue, which a
        # finished run ignores, and the next run skipped the held books (an approved job is no rule change).
        by = self.lecture_set()
        self.service.automatic.start(); self.finish_run()
        self.assertEqual([self.asked_now(by[k]).get('why') for k in '123'], ['title_series'] * 3, 'the set is asked; the run has ended')
        self.assertEqual(self.service.jobs.status()['jobs'], [])
        self.service.approve_book(by['1']['id'], by['1']['revision']); self.finish_run()
        self.assertEqual(self.filed(), self.lectures('Петров Иван', 'Курс истории. Лекция'), 'the rest followed his answer')

    def test_m1_ruling_53_after_a_rescan_the_next_run_files_the_rest(self):
        from unittest import mock
        by = self.lecture_set(count=2)
        self.service.automatic.start(); self.finish_run()
        with mock.patch.object(self.service.automatic, 'request_start', return_value={'action': 'blocked'}):  # nothing starts now
            self.service.approve_book(by['1']['id'], by['1']['revision'])
        self.wait()
        self.assertEqual(self.asked_now(by['2']).get('why'), 'title_series', 'positive control: not researched yet')
        self.inv.launch('Audiobooks'); finish_scan(self.inv)
        self.service.automatic.start(); self.finish_run()
        self.assertEqual(self.filed(), self.lectures('Петров Иван', 'Курс истории. Лекция', 2))

    def test_m1_ruling_53_a_paused_run_continues_with_the_rest(self):
        by = self.lecture_set(count=2)
        self.service.automatic.start(); self.finish_run()
        run = self.service.automatic._run_row()
        with connect(self.inv.database) as db:
            db.execute("UPDATE automatic_runs SET state='Paused',phase='research',checkpoint=? WHERE id=?", (json.dumps({'pending': [], 'done': [by['1']['id'], by['2']['id']]}), run['id']))
        self.assertEqual(self.service.automatic.status()['state'], 'Paused', 'positive control: a saved, paused run')
        self.service.approve_book(by['1']['id'], by['1']['revision']); self.finish_run()
        self.assertEqual(self.filed(), self.lectures('Петров Иван', 'Курс истории. Лекция', 2))

    def test_ruling_53_the_rest_of_the_set_takes_the_series_he_corrected(self):
        # Ruling 53, "the rest follow that answer" (Futaba's 0.22.3 QA): «Курс истории» set on book 1 at its Approve.
        by = self.lecture_set()
        self.service.automatic.start(); self.finish_run()
        self.service.approve_book(by['1']['id'], by['1']['revision'], names={'series': 'Курс истории', 'number': '1'}); self.finish_run()
        self.assertEqual(self.filed(), self.lectures('Петров Иван', 'Курс истории'))

    def test_m10_an_approve_that_answered_same_author_is_no_answer_to_the_series_question(self):
        # Senua's 0.22.3 review, M10: the Same author? Approve filed book 1's unconfirmed split, and «Курс истории. Лекция 2.
        # Рим» then filed by itself into `Koontz Dean\Курс истории. Лекция\`, the series never asked.
        import author_rules
        by = self.lecture_set(artist='Dean Koonts', count=2)
        with connect(self.inv.database) as db:
            author_rules.setup(db); author_rules.append(db, 'keep', 'Koontz Dean', actor='user', source='test')
        self.service.automatic.start(); self.finish_run()
        self.assertEqual(self.asked_now(by['1']).get('kind'), 'same_author', 'positive control: the author is asked first')
        with self.assertRaisesRegex(ValueError, 'series is asked next'):
            self.service.approve_book(by['1']['id'], by['1']['revision'], choice='same')
        self.finish_run()
        self.assertEqual(author_rules.load(self.inv.database).same_as('Dean Koonts'), 'Koontz Dean', 'his answer is kept')
        self.assertEqual(self.service.jobs.status()['jobs'], [], 'nothing filed under Koontz Dean\\Курс истории. Лекция')
        for k in '12':
            ask = self.asked_now(by[k])
            self.assertEqual((ask.get('why'), (ask.get('split') or {}).get('series'), ask['fields']['author']['proposal']), ('title_series', 'Курс истории. Лекция', 'Koontz Dean'), k)
        self.service.approve_book(by['1']['id'], by['1']['revision']); self.finish_run()  # his answer to the series question
        self.assertEqual(self.filed(), self.lectures('Koontz Dean', 'Курс истории. Лекция', 2))

    def test_m10_an_approve_that_answered_the_english_spelling_is_no_answer_to_the_series_question(self):
        from unittest import mock
        import author_rules
        by = self.lecture_set(artist='Джеймс Роллинс', count=2)
        with mock.patch.object(self.service.automatic.research, '_author_latin', return_value=None):  # the lookup finds nothing
            self.service.automatic.start(); self.finish_run()
            self.assertEqual(self.asked_now(by['1']).get('why'), 'english_spelling', 'positive control: the spelling is asked first')
            with self.assertRaisesRegex(ValueError, 'series is asked next'):
                self.service.approve_book(by['1']['id'], by['1']['revision'], author='James Rollins')
            self.finish_run()
        self.assertEqual(author_rules.load(self.inv.database).same_as('Джеймс Роллинс'), 'Rollins James', 'his spelling is kept')
        self.assertEqual(self.service.jobs.status()['jobs'], [], 'nothing filed')
        for k in '12':
            ask = self.asked_now(by[k])
            self.assertEqual((ask.get('why'), ask['fields']['author']['proposal']), ('title_series', 'Rollins James'), k)


if __name__ == '__main__':
    unittest.main()

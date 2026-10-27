"""Ruling 38 end to end (Sergei 2026-10-27; it replaces the waiting part of ruling 29): a translation with only its Russian
title never waits for its English original title. Automatic processing converts it right away under the title it has,
in the English author folder, and it is never listed under Held. Real private audio, offline research, a separate
Sorted folder."""
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


if __name__ == '__main__':
    unittest.main()

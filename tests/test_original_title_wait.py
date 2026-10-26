"""Ruling 29 end to end (Judy 0.22.2 section 4): a translation waiting for its English original title is listed under Held
with its fallback destination ("If none is found, goes to") and its own Approve, which files it under the Russian title
at once. Real private audio, offline research, a separate Sorted folder."""
import unittest
from pathlib import Path

from test_approve_as_is import ApproveFixture, tone


class OriginalTitleWaitRowTests(ApproveFixture):
    def test_the_waiting_book_is_listed_under_held_with_its_fallback_path_and_approve_files_it_now(self):
        tone(self.audio / 'Roger Zelazny' / 'Джек из Тени' / 'Джек из Тени.mp3', self.cover, album='Джек из Тени', title='Джек из Тени', artist='Roger Zelazny')
        row = self.start()[0]
        result = self.research(row)
        self.assertEqual(result['reasons'], ['Waiting for the original title'], 'positive control: a translation waits')
        self.service.automatic._record(row, 'Waiting for source', result, result['wait']['retry_at'])
        held = [r for r in self.service.reviews.page(status='held')['rows'] if r['id'] == row['id']]
        self.assertEqual(len(held), 1, 'listed under Held, the automatic waits')
        ask = held[0]['ask']
        self.assertEqual(ask['kind'], 'original_title')
        self.assertIs(ask['odd_name'], True, 'never in a bulk Approve')
        self.assertEqual(ask['destination']['path'], str(Path('Zelazny Roger') / 'Джек из Тени - Zelazny Roger.m4b'), 'what Approve files now')
        self.assertNotIn(row['id'], self.service.needs_you(), 'not on the to-do list: nothing is wrong')
        approved = self.service.approve_book(row['id'], row['revision'], path=ask['destination']['path']); self.wait()
        job = self.service.jobs.status()['jobs'][0]
        self.assertEqual(job['job_id'], approved['job_id']); self.assertEqual(job['state'], 'completed', job)
        self.assertEqual(Path(job['output']['final_path']), self.sorted / 'Zelazny Roger' / 'Джек из Тени - Zelazny Roger.m4b', 'filed as shown, the wait ended')


if __name__ == '__main__':
    unittest.main()

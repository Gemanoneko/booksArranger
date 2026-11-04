"""Private four-book codec continuation probe for pinned Books Arranger f6553e7."""
import hashlib
import json
import os
import pathlib
import sys
import time
import unittest
import uuid

root = pathlib.Path(__file__).resolve().parent
source = root / 'src'
os.chdir(source)
sys.path[:0] = [str(source), str(source / 'tests')]

from test_set_release import SetReleaseTests
import test_automatic_processing as automatic_fixtures

area = pathlib.Path('C:/Antigravity Projects/ba45')
area.mkdir(parents=True, exist_ok=True)
automatic_fixtures.AREA = area


def sha(file):
    return hashlib.sha256(pathlib.Path(file).read_bytes()).hexdigest()


class RealCodecContinuation(SetReleaseTests):
    def test_one_start_skips_retained_producer_and_finishes_three_real_books(self):
        titles = [
            ('1', 'Курс истории. Лекция 1. Греция'),
            ('2', 'Курс истории. Лекция 2. Рим'),
            ('3', 'Курс истории. Лекция 3. Египет'),
            ('4', 'Курс истории. Лекция 4. Персия'),
        ]
        rows = self.books(albums=titles)
        self.assertEqual(set(rows), set('1234'))
        self.held(rows)
        approvals = {}
        for key in '1234':
            row = rows[key]
            approvals[key] = self.service.approve_book(row['id'], row['revision'])
        queued = self.service.jobs.status()['jobs']
        self.assertEqual(len(queued), 4)
        self.assertTrue(all(job['state'] == 'pending' for job in queued))
        ids = {key: approvals[key]['job_id'] for key in '1234'}
        by_id = {job['job_id']: job for job in queued}
        first = by_id[ids['1']]
        retained_sources = {member['path']: sha(member['path']) for member in first['manifest']['sources']}

        attempt = str(uuid.uuid4())
        self.service.jobs._update(first['job_id'], state='running', stage='checking sources',
                                  attempt_id=attempt,
                                  journal=json.dumps({'attempt_id': attempt, 'history': []}), reason='')
        self.service.working.begin(dict(first['manifest'], attempt_id=attempt))
        self.service.jobs._update(first['job_id'], state='pending', stage='queued')

        self.service.resume_press()  # the only Start in this scenario
        deadline = time.monotonic() + 240
        while True:
            jobs = {job['job_id']: job for job in self.service.jobs.status()['jobs']}
            state = self.service.state()
            finished = len(jobs) == 4 and all(jobs[ids[key]]['state'] == 'completed' for key in '234')
            blocked = len(jobs) == 4 and jobs[ids['1']]['state'] == 'needs attention'
            idle = state['state'] not in ('Running', 'Pausing') and not state.get('queued') and not state.get('cleanup_active')
            if finished and blocked and idle:
                break
            if time.monotonic() >= deadline:
                self.fail('Private four-book real-codec continuation exceeded 240 s: ' +
                          json.dumps({'jobs': {key: (jobs.get(ids[key]) or {}).get('state') for key in '1234'},
                                      'service': state['state'], 'queued': state.get('queued'),
                                      'cleanup_active': state.get('cleanup_active')}))
            time.sleep(0.1)

        blocked_job = jobs[ids['1']]
        self.assertEqual(blocked_job['attempt_id'], attempt)
        self.assertIn('not durably closed', blocked_job['reason'])
        self.assertEqual(self.service.working._attempt(ids['1'], attempt)['producer'], 'active')
        self.assertEqual({file: sha(file) for file in retained_sources}, retained_sources)
        outputs = {}
        for key in '234':
            job = jobs[ids[key]]
            output = job['output']
            self.assertTrue(output['validation']['passed'], job)
            final = pathlib.Path(output['final_path'])
            self.assertTrue(final.is_file() and final.is_relative_to(self.sorted), job)
            self.assertEqual(sha(final), output['sha256'])
            cleanup = self.service.cleanup.status(ids[key])
            self.assertEqual(cleanup['state'], 'completed', cleanup)
            self.assertTrue(all(not pathlib.Path(member['path']).exists() for member in job['manifest']['sources']))
            outputs[key] = {'path': str(final), 'size': final.stat().st_size, 'sha256': sha(final)}
        self.assertEqual(len({item['path'] for item in outputs.values()}), 3)
        self.assertFalse(self.service.jobs._stop.is_set())
        print('QA_REAL_CODEC_RESULT ' + json.dumps({
            'source': 'f6553e7b78bf9d7f011b5728b2d219ad48732add',
            'start_count': 1,
            'blocked_job': ids['1'],
            'blocked_attempt': attempt,
            'blocked_reason': blocked_job['reason'],
            'retained_source_sha256': retained_sources,
            'completed_job_ids': [ids[key] for key in '234'],
            'outputs': outputs,
            'automatic_state': self.service.automatic.status()['state'],
        }, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == '__main__':
    suite = unittest.TestSuite([RealCodecContinuation('test_one_start_skips_retained_producer_and_finishes_three_real_books')])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)

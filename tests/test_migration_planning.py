"""Final planning uses private real conversion and exclusive catalog ownership."""
import copy
import tempfile
import os
import sqlite3
import contextlib
import shutil
from unittest.mock import patch
import unittest
from pathlib import Path
from catalog_owner import catalog_lock
from migration_planning import prepare,write_plan,read_pinned_json,_completed_census,_completeness_receipt
import test_merge_service as fixture
from publication_locations import _digest

class MigrationPlanningTests(unittest.TestCase):
    def test_real_series_retag_enrolls_relocates_and_revalidates_original_history(self):
        import json
        from series_backfill import SeriesBackfill,encoded
        from types import SimpleNamespace
        from migration_operation import MigrationOperation
        from publication_binding import PublicationBindings
        f=fixture.MergeTests();f.setUp();self.addCleanup(f.tearDown)
        f.review.update(series='',number='')
        book=f.ready();f.service.create('Audiobooks',book['id'],book['revision']);status=f.wait()
        self.assertEqual(status['completed'],1,status)
        job_id=status['jobs'][0]['job_id']
        with contextlib.closing(sqlite3.connect(f.inv.database)) as db:
            before=db.execute('SELECT journal FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()[0]
        f.service.close()
        # Reproduce the historical pre-hierarchy metadata shape of the affected
        # jobs. Actual media/publication intent stay exactly as converted; the
        # legacy same-parent series producer is then exercised without mocks.
        with contextlib.closing(sqlite3.connect(f.inv.database)) as db:
            manifest=json.loads(db.execute('SELECT manifest FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone()[0])
            for key in ('organization_policy','universe'):manifest['metadata'].pop(key,None)
            text,sha=encoded(manifest)
            db.execute('UPDATE audio_jobs SET manifest=?,manifest_hash=? WHERE job_id=?',(text,sha,job_id))
            db.execute('UPDATE book_groups SET review=? WHERE id=?',(json.dumps(manifest['metadata']),book['id']));db.commit()
        backfill=SeriesBackfill(f.service,research=SimpleNamespace(),stage=f.base/'backfill-proof')
        backfill.apply(job_id,{'name':'Added Series','number':'3','provider':'goodreads','source_url':'https://www.goodreads.com/book/show/private-fixture'})
        self.assertEqual(backfill.entry(job_id)['state'],'done',backfill.entry(job_id))
        target=f.base/'sorted';target.mkdir()
        with catalog_lock(f.inv.database,f.inv.roots):
            plan=prepare(f.inv.database,f.inv.roots,[f.inv.roots['Audiobooks']],str(target))
        self.assertEqual(len(plan['publications']),1,plan);self.assertEqual(plan['held'],[])
        proof=plan['completed_candidate_completeness'];self.assertEqual(proof['completed_candidates'],proof['accounted_candidates'])
        area=Path(tempfile.mkdtemp(dir=f.base.parent));published=write_plan(area/'backfilled-plan.json',plan)
        entry=plan['publications'][0]
        migrated=MigrationOperation(f.inv.database,plan['roots'],published['plan'],published['sha256']).run(entry['publication_id'])
        self.assertEqual(migrated['stage'],'complete');self.assertEqual(migrated['outcome'],'moved')
        with contextlib.closing(sqlite3.connect(f.inv.database)) as db:
            db.row_factory=sqlite3.Row;job=dict(db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,)).fetchone())
            self.assertEqual(job['journal'],before)
            original=json.loads(job['output']);effective,envelope=PublicationBindings(f.inv.database).lookup(db,original,'base')
            self.assertEqual(effective['final_path'],entry['destination']);self.assertEqual(envelope['relocation']['stage'],'complete')
            self.assertEqual(original['final_path'],entry['source'])
        # Re-entry consumes the exact journaled complete relocation and re-proves
        # the destination; it neither reconstructs the old receipt nor recopies.
        repeated=MigrationOperation(f.inv.database,plan['roots'],published['plan'],published['sha256']).run(entry['publication_id'])
        self.assertEqual(repeated['outcome'],'moved');self.assertTrue(Path(entry['destination']).is_file())
        self.assertFalse(Path(entry['source']).exists())
        with contextlib.closing(sqlite3.connect(f.inv.database)) as db:
            saved=json.loads(db.execute('SELECT record FROM series_backfill WHERE job_id=?',(job_id,)).fetchone()[0])
            saved['new_mtime']+=1
            db.execute('UPDATE series_backfill SET record=? WHERE job_id=?',(json.dumps(saved),job_id));db.commit()
        with self.assertRaisesRegex(ValueError,'lineage changed'):
            MigrationOperation(f.inv.database,plan['roots'],published['plan'],published['sha256']).run(entry['publication_id'])
        self.assertTrue(Path(entry['destination']).is_file());self.assertFalse(Path(entry['source']).exists())

    def test_enrollment_refusal_is_an_explicit_completed_outcome(self):
        import publication_locations as locations
        f=fixture.MergeTests();f.setUp();self.addCleanup(f.tearDown)
        book=f.ready();f.service.create('Audiobooks',book['id'],book['revision']);status=f.wait();self.assertEqual(status['completed'],1,status)
        f.service.close();target=f.base/'sorted';target.mkdir()
        with catalog_lock(f.inv.database,f.inv.roots),patch('migration_planning.locations.plan',side_effect=locations.PublicationRefused('fixture','Exact publication proof refused')):
            plan=prepare(f.inv.database,f.inv.roots,[f.inv.roots['Audiobooks']],str(target))
        proof=plan['completed_candidate_completeness']
        self.assertEqual(proof['completed_candidates'],1);self.assertEqual(proof['accounted_candidates'],1)
        self.assertEqual(proof['outcomes'][0]['outcome'],'held');self.assertEqual(plan['planned_bytes'],0)
        self.assertEqual(plan['publications'],[]);self.assertIn('Exact publication proof refused',plan['held'][0]['reason'])

    def test_plan_requires_owner_before_any_catalog_change(self):
        with self.assertRaisesRegex(ValueError,'exclusive catalog owner'):prepare('C:/not-opened/catalog.sqlite',{'Audiobooks':'C:/not-opened/audio'},None,'C:/not-opened/sorted')
    def test_current_completed_book_enrolls_without_changing_receipt_or_sources(self):
        f=fixture.MergeTests();f.setUp();self.addCleanup(f.tearDown)
        book=f.ready();f.service.create('Audiobooks',book['id'],book['revision']);status=f.wait();self.assertEqual(status['completed'],1,status)
        original=copy.deepcopy(status['jobs'][0]['output']);f.service.close()
        destination=f.base/'sorted';destination.mkdir();roots=f.inv.roots
        with contextlib.closing(sqlite3.connect(f.inv.database)) as db:db.execute('DELETE FROM verified_outputs');db.commit()
        with catalog_lock(f.inv.database,roots),patch('migration_planning.time.monotonic',side_effect=[0,541]):
            deferred=prepare(f.inv.database,roots,[roots['Audiobooks']],str(destination))
        self.assertEqual(deferred['publications'],[])
        self.assertEqual(deferred['scope_counts']['verification_deferred'],1,deferred)
        self.assertEqual(deferred['held'][0]['hold_type'],'verification_deferred')
        self.assertTrue(Path(original['final_path']).exists());self.assertEqual(list(destination.iterdir()),[])
        with catalog_lock(f.inv.database,roots):
            result=prepare(f.inv.database,roots,[roots['Audiobooks']],str(destination))
        self.assertEqual(len(result['publications']),1,result);self.assertEqual(result['held'],[])
        self.assertEqual(result['scope_counts']['uncached_variants_fully_hashed'],1)
        with catalog_lock(f.inv.database,roots):
            cached=prepare(f.inv.database,roots,[roots['Audiobooks']],str(destination))
        self.assertEqual(cached['scope_counts']['uncached_variants_fully_hashed'],0)
        self.assertEqual(cached['publications'],result['publications'])
        entry=result['publications'][0];self.assertEqual(entry['source'],original['final_path']);self.assertTrue(Path(entry['source']).exists())
        self.assertFalse(Path(entry['destination']).exists());self.assertEqual(list(destination.iterdir()),[])
        self.assertEqual(status['jobs'][0]['output'],original)
        plan_area=Path(tempfile.mkdtemp(dir=f.base.parent));published=write_plan(plan_area/'reviewed-migration.json',result)
        from migration_operation import MigrationOperation
        operation=MigrationOperation(f.inv.database,result['roots'],published['plan'],published['sha256'])
        migrated=operation.run(entry['publication_id'])
        self.assertEqual(migrated['stage'],'complete',migrated)
        self.assertTrue(Path(entry['destination']).exists())
        # Outcome is reported exactly; no success claim from path presence alone.
        self.assertEqual(migrated['outcome'],'moved',migrated)
        self.assertEqual(Path(entry['source']).exists(),migrated['outcome']!='moved')
        self.assertEqual(status['jobs'][0]['output'],original)

    def test_plan_publication_never_overwrites_and_pinned_read_rejects_change(self):
        base=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/'migration-plan-publication';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as name:
            folder=Path(name);path=folder/'plan.json'
            plan={'database':str(folder/'data'/'catalog.sqlite'),'roots':{'Audiobooks':str(folder/'source')},'publications':[],'held':[]}
            receipt=write_plan(path,plan)
            self.assertEqual(read_pinned_json(path,receipt['sha256']),plan)
            with self.assertRaises(FileExistsError):write_plan(path,dict(plan,held=['changed']))
            self.assertEqual(read_pinned_json(path,receipt['sha256']),plan)
            path.write_text('changed')
            with self.assertRaisesRegex(ValueError,'SHA256 changed'):read_pinned_json(path,receipt['sha256'])

    def test_explicit_later_candidate_progresses_after_earlier_budget_deferral(self):
        f=fixture.MergeTests();f.setUp();self.addCleanup(f.tearDown)
        other=f.audio/'Second';other.mkdir()
        for source in f.sources:shutil.copyfile(source,other/source.name)
        shutil.copyfile(f.audio/'Book'/'cover.png',other/'cover.png')
        original_reader=f.inv.reader
        def reader(path,kind,stop):
            result=original_reader(path,kind,stop)
            if Path(path).parent==other:result=dict(result,title='Second',tags={'album':'Second'})
            return result
        f.inv.reader=reader;f.inv.launch('Audiobooks');f.inv.worker.join(5)
        candidates=f.service.reviews.page()['rows'];self.assertEqual(len(candidates),2,candidates)
        for candidate in candidates:
            reviews=f.service.reviews;row=reviews.covers('Audiobooks',candidate['id'],candidate['revision'])
            title='Second' if Path(row['members'][0]['path']).parent==other else 'Book'
            row=reviews.save('Audiobooks',row['id'],row['revision'],dict(f.review,title=title),True,'Private independent identity proof',cover_id=row['cover_choices'][0]['id'])
            row=reviews.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,True,evidence_note='Exact private membership/order')
            f.service.create('Audiobooks',row['id'],row['revision']);status=f.wait()
        self.assertEqual(status['completed'],2,status);f.service.close()
        target=f.base/'sorted';target.mkdir()
        with contextlib.closing(sqlite3.connect(f.inv.database)) as db:
            db.execute('DELETE FROM verified_outputs');db.commit()
            ordered=[row[0] for row in db.execute('SELECT id FROM book_groups WHERE superseded=0')]
        with catalog_lock(f.inv.database,f.inv.roots),patch('migration_planning.time.monotonic',side_effect=[0,541,541]):
            initial=prepare(f.inv.database,f.inv.roots,[f.inv.roots['Audiobooks']],str(target))
        self.assertEqual(initial['scope_counts']['verification_deferred'],2,initial)
        with catalog_lock(f.inv.database,f.inv.roots):
            selected=prepare(f.inv.database,f.inv.roots,[f.inv.roots['Audiobooks']],str(target),verification_candidates=[ordered[1]])
        self.assertEqual(selected['verification_selection'],[ordered[1]])
        self.assertEqual(selected['scope_counts']['approved_candidates'],2)
        self.assertEqual(selected['scope_counts']['uncached_variants_fully_hashed'],1)
        self.assertEqual([row['candidate_id'] for row in selected['publications']],[ordered[1]])
        self.assertEqual([row['candidate_id'] for row in selected['held']],[ordered[0]])
        self.assertEqual(selected['held'][0]['hold_type'],'verification_deferred')
        with catalog_lock(f.inv.database,f.inv.roots),self.assertRaisesRegex(ValueError,'Unknown current verification'):
            prepare(f.inv.database,f.inv.roots,[f.inv.roots['Audiobooks']],str(target),verification_candidates=['not-current'])
        with catalog_lock(f.inv.database,f.inv.roots):
            final=prepare(f.inv.database,f.inv.roots,[f.inv.roots['Audiobooks']],str(target),verification_candidates=[ordered[0]])
        self.assertEqual(len(final['publications']),2,final);self.assertEqual(final['held'],[])
        self.assertEqual(final['scope_counts']['uncached_variants_fully_hashed'],1)
        self.assertEqual(list(target.iterdir()),[])


class MigrationCompletenessTests(unittest.TestCase):
    """Pure production census/reconciliation functions; no media or catalog IO."""
    def jobs(self):
        return [dict(job_id='job-'+identity,manifest={'candidate_id':identity},manifest_hash='hash-'+identity,
                     created='2026-10-20T00:00:00Z',state='completed') for identity in ('approved','unapproved','missing-context')]
    def census(self):
        return _completed_census([{'id':identity} for identity in ('approved','unapproved','missing-context','pending')],self.jobs()+[
            dict(job_id='pending-job',manifest={'candidate_id':'pending'},manifest_hash='pending-hash',created='2026-10-20T00:00:00Z',state='pending')])
    def outcomes(self):
        return [{'candidate_id':'approved','outcome':'enrolled','reason':'Verified publication enrolled'},
                {'candidate_id':'unapproved','outcome':'held','reason':'Current metadata approval absent'},
                {'candidate_id':'missing-context','outcome':'held','reason':'Current review context missing'}]
    def test_independent_census_accounts_three_completed_including_unapproved_and_missing_context(self):
        census=self.census();receipt=_completeness_receipt(census,self.outcomes())
        self.assertEqual({row['candidate_id'] for row in census},{'approved','unapproved','missing-context'})
        self.assertEqual(receipt['completed_candidates'],3);self.assertEqual(receipt['accounted_candidates'],3)
        self.assertEqual(receipt['schema'],'books-completed-candidate-accounting-v1')
        self.assertNotIn('pending',{row['candidate_id'] for row in receipt['outcomes']})
    def test_missing_outcome_refuses(self):
        with self.assertRaisesRegex(ValueError,'Missing'): _completeness_receipt(self.census(),self.outcomes()[:-1])
    def test_duplicate_outcome_refuses(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'): _completeness_receipt(self.census(),self.outcomes()+[self.outcomes()[0]])
    def test_unknown_outcome_refuses(self):
        with self.assertRaisesRegex(ValueError,'Unknown'): _completeness_receipt(self.census(),self.outcomes()+[dict(candidate_id='other',outcome='held',reason='Unknown')])
    def test_duplicate_census_refuses(self):
        census=self.census()
        with self.assertRaisesRegex(ValueError,'Duplicate'): _completeness_receipt(census+[census[0]],self.outcomes())
        with self.assertRaisesRegex(ValueError,'Duplicate'): _completed_census([{'id':'approved'},{'id':'approved'}],self.jobs())
    def test_reason_and_typed_outcome_required(self):
        for patch_value in ({'reason':''},{'outcome':'moved'},{'outcome':'ready'}):
            outcomes=self.outcomes();outcomes[0].update(patch_value)
            with self.assertRaisesRegex(ValueError,'Explicit'): _completeness_receipt(self.census(),outcomes)
    def test_latest_pending_and_set_aside_never_count_as_completed(self):
        jobs=self.jobs()+[dict(self.jobs()[0],job_id='later',created='2026-10-21T00:00:00Z',state='pending')]
        candidates=[{'id':identity} for identity in ('approved','unapproved','missing-context')]
        self.assertNotIn('approved',{row['candidate_id'] for row in _completed_census(candidates,jobs)})
        self.assertEqual(len(_completed_census(candidates,jobs,['later'])),3)
        self.assertNotIn('unapproved',{row['candidate_id'] for row in _completed_census(candidates,self.jobs(),['job-unapproved'])})
    def test_equal_created_uses_job_id_and_noncurrent_candidate_is_excluded(self):
        jobs=self.jobs()+[dict(self.jobs()[0],job_id='zzzz',state='needs attention'),dict(self.jobs()[0],job_id='foreign',manifest={'candidate_id':'foreign'})]
        census=_completed_census([{'id':identity} for identity in ('approved','unapproved','missing-context')],jobs)
        self.assertEqual({row['candidate_id'] for row in census},{'unapproved','missing-context'})
    def test_deferred_and_already_are_explicit_without_move_success_claim(self):
        outcomes=self.outcomes();outcomes[0]['outcome']='verification_deferred';outcomes[1]['outcome']='already_at_destination'
        receipt=_completeness_receipt(self.census(),outcomes)
        self.assertEqual(receipt['accounted_candidates'],3)
        self.assertFalse(any(row['outcome']=='moved' for row in receipt['outcomes']))

# 0.21.3: this module's fixtures publish inside their own library; see sorted_fixture (Sergei's deletion rule).
def setUpModule():
    global _sorted_fixture
    from sorted_fixture import patch_merge_service
    _sorted_fixture = patch_merge_service()


def tearDownModule():
    _sorted_fixture.stop()


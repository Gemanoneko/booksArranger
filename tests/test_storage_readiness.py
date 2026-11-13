import hashlib,os,sqlite3,unittest,uuid
from pathlib import Path
from storage_readiness import inspect_readiness


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.area=Path(os.environ['BOOKS_QA_FIXTURE_ROOT'])/('readiness-'+uuid.uuid4().hex);self.area.mkdir()
        self.database=self.area/'inventory.sqlite3';db=sqlite3.connect(self.database)
        try:
            db.executescript('CREATE TABLE working_attempts(job_id,attempt_id,state,producer,updated);CREATE TABLE audio_jobs(job_id,attempt_id,state,output,journal);CREATE TABLE producer_origin_facts(job_id,attempt_id);CREATE TABLE producer_recovery_checkpoints(job_id,attempt_id,state);')
            self.job=str(uuid.uuid4());self.attempt=str(uuid.uuid4())
            db.execute('INSERT INTO working_attempts VALUES(?,?,?,?,?)',(self.job,self.attempt,'producing','active','2026-10-29T11:24:39+00:00'))
            db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?)',(self.job,self.attempt,'needs attention',None,'{}'));db.commit()
        finally:db.close()

    def test_read_only_stale_current_attempt_is_eligible_but_never_closed(self):
        before=hashlib.sha256(self.database.read_bytes()).hexdigest()
        result=inspect_readiness(self.database)
        self.assertFalse(result['authority']);self.assertFalse(result['ready_to_freeze'])
        obligation=result['unclosed_producers'][0]
        self.assertTrue(obligation['source_recovery_scope_eligible']);self.assertEqual(obligation['origin_records'],0)
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(),before)
        self.assertEqual({p.name for p in self.area.iterdir()},{'inventory.sqlite3'})

    def test_publication_and_unknown_producer_never_report_recovery_eligible(self):
        db=sqlite3.connect(self.database)
        try:
            db.execute('UPDATE audio_jobs SET output=?',('{"existing":"receipt"}',));db.execute('UPDATE working_attempts SET producer=NULL');db.commit()
        finally:db.close()
        result=inspect_readiness(self.database)
        self.assertEqual(len(result['unclosed_producers']),1)
        self.assertFalse(result['unclosed_producers'][0]['source_recovery_scope_eligible'])

    def test_missing_catalog_never_created(self):
        missing=self.area/'missing.sqlite3'
        with self.assertRaises(sqlite3.OperationalError):inspect_readiness(missing)
        self.assertFalse(missing.exists())

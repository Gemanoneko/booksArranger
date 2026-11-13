"""Old support-owner recovery, with independent producer facts and real crash."""
import json,os,subprocess,sys,unittest,uuid
from pathlib import Path

from native_io import VerifiedFile
from runtime_disposition_owners import recover_support
from storage_relocation_operator import digest


@unittest.skipUnless(os.name=='nt','Native support recovery')
class SupportRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.area=Path(os.environ['BOOKS_QA_FIXTURE_ROOT'])/('support-recovery-'+uuid.uuid4().hex)
        self.area.mkdir();self.file=self.area/'owned-partial-settings.json';self.file.write_bytes(b'original partial settings')
        with VerifiedFile(self.file) as held:self.targets={str(self.file):dict(facts=held.facts(),sha256=held.sha256())}
        self.program=self.area/'crash.py'
        self.program.write_text("import sys,os,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from runtime_disposition_owners import support_dispositions;from runtime_file_disposition import prepare_disposition;from native_io import VerifiedFile\np=Path(sys.argv[2])\nwith support_dispositions(p,[p/'owned-partial-settings.json']) as ctx:\n print(json.dumps({'root':str(ctx.control_root.parent),'sha256':ctx.marker_sha256}),flush=True)\n with VerifiedFile(p/'owned-partial-settings.json',delete=True) as held:\n  guard=prepare_disposition(held,ctx)\n  os._exit(17)\n",encoding='utf8')
        result=subprocess.run([sys.executable,'-I','-B',str(self.program),str(Path(__file__).resolve().parents[1]),str(self.area)],capture_output=True,timeout=30)
        self.assertEqual(result.returncode,17,result.stderr.decode(errors='replace'))
        self.pin=json.loads(result.stdout)

    def test_actual_old_owner_crash_recovers_exact_original_permissions_and_retains_work(self):
        with self.assertRaises(PermissionError):self.file.write_bytes(b'must remain fenced before recovery')
        result=recover_support(self.pin['root'],self.pin['sha256'],targets=self.targets)
        self.assertEqual(result['restored'],[str(self.file)]);self.assertFalse(result['held'])
        self.assertEqual(self.file.read_bytes(),b'original partial settings');self.file.write_bytes(b'writable again')
        result=recover_support(self.pin['root'],self.pin['sha256'],targets=self.targets)
        self.assertEqual(result['retained'],[str(self.file)])
        self.assertEqual(self.file.read_bytes(),b'writable again','terminal history grants no new write/delete authority')

    def test_wrong_pin_unrelated_target_and_replaced_owner_refuse_without_restoration(self):
        with self.assertRaises(Exception):recover_support(self.pin['root'],'0'*64,targets=self.targets)
        wrong={str(self.area/'unrelated.json'):next(iter(self.targets.values()))}
        with self.assertRaisesRegex(Exception,'source-producer'):recover_support(self.pin['root'],self.pin['sha256'],targets=wrong)
        owner=Path(self.pin['root'])/'owner.lock';original=owner.with_suffix('.original');owner.rename(original);owner.write_bytes(b'')
        try:
            with self.assertRaisesRegex(Exception,'owner was replaced'):recover_support(self.pin['root'],self.pin['sha256'],targets=self.targets)
            with self.assertRaises(PermissionError):self.file.write_bytes(b'must still be fenced')
        finally:owner.unlink();original.rename(owner)
        self.assertFalse(recover_support(self.pin['root'],self.pin['sha256'],targets=self.targets)['held'])

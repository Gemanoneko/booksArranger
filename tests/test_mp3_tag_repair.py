"""Finite MP3 tag preservation and actual private staging integration checks."""
import copy,hashlib,json,os,sys,tempfile,threading,unittest,uuid,contextlib,types
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mp3_tag_repair as repair
import audio_pipeline as media

def fixture():return (b'\xff\xfb\x90\xc0'+b'\0'*413)*3+b'TAG'+b'\0'*125
def packets(layout):
    return [dict(pos=str(p),size=str(n),pts_time=str(i),dts_time=str(i),duration_time='1',flags='K_') for i,(p,n) in enumerate(layout.frames)]

class TagPlanTests(unittest.TestCase):
    def test_exact_tail_and_input_immutability(self):
        data=fixture();before=bytes(data);plan=repair.plan(data)
        self.assertEqual(data,before);self.assertEqual(plan.samples,3456)
        self.assertEqual(plan.prefix_size,len(data)-128);self.assertEqual(plan.receipt()['removed_bytes'],128)
    def test_missing_nonterminal_or_extra_bytes_refuse(self):
        for data in (fixture()[:-128],fixture()+b'x',fixture()[:-128]+b'junk'+fixture()[-128:]):
            with self.subTest(size=len(data)),self.assertRaises(repair.UnsupportedProfile):repair.plan(data)
    def test_partial_audio_and_changed_configuration_refuse(self):
        data=fixture()
        for bad in (data[:417]+data[418:],data[:417]+b'\xff\xfb\x94\xc0'+data[421:]):
            with self.assertRaises(repair.UnsupportedProfile):repair.plan(bad)
    def test_encoder_trim_metadata_refuses(self):
        data=fixture()
        for marker in (b'Xing',b'Info',b'LAME',b'VBRI'):
            with self.assertRaises(repair.UnsupportedProfile):repair.plan(data[:20]+marker+data[20+len(marker):])
    def test_packet_timing_and_full_trailer_coverage(self):
        layout=repair.plan(fixture());candidate=packets(layout)
        original=copy.deepcopy(candidate)+[dict(pos=str(layout.prefix_size),size='128')]
        self.assertEqual(repair.verify_packets(original,candidate,layout)['packet_count'],3)
        for mutate in ('time','extent','trim','trailer'):
            before=copy.deepcopy(original);after=copy.deepcopy(candidate)
            if mutate=='time':after[0]['pts_time']='changed'
            if mutate=='extent':after[0]['size']='416';before[0]['size']='416'
            if mutate=='trim':after[0]['side_data_list']=[{}];before[0]['side_data_list']=[{}]
            if mutate=='trailer':before[-1]['size']='127'
            with self.subTest(mutate=mutate),self.assertRaises(repair.UnsupportedProfile):repair.verify_packets(before,after,layout)
    def test_untrusted_json_cannot_mint_assessment(self):
        with self.assertRaises(TypeError):repair.SourceDamageAssessment({'context_completed':True})
        with self.assertRaises(TypeError):repair.CompletedDiagnostic({'context_completed':True})
        with self.assertRaises(repair.UnsupportedProfile):repair.assessment({}, {},repair.plan(fixture()),{'sample_count':1},{'context_completed':True})
    def test_completed_nonzero_and_partial_pcm_never_prove_source_damage(self):
        # Explicit fake completion contexts, not observed media runs or ownership proof.
        layout=repair.plan(fixture())
        for returncode in (1,12,-1073741801):
            completed=repair.CompletedDiagnostic({'context_completed':True,'returncode':returncode},repair._INTERNAL)
            for samples in (1,1152,layout.samples-1):
                with self.subTest(returncode=returncode,samples=samples),self.assertRaises(repair.UnsupportedProfile):
                    repair.assessment({}, {},layout,{'sample_count':samples},completed)
    def test_nonmedia_failure_never_attempts_repair(self):
        for error in (media.ValidationError('drain failed'),TimeoutError('deadline'),media.Paused('paused')):
            with patch.object(media,'decoded_duration',side_effect=error),patch.object(media,'_mp3_tag_copy') as attempt:
                with self.assertRaises(type(error)):media._source_duration({}, {},Path('source.mp3'),Path('.'),threading.Event(),1)
                attempt.assert_not_called()
    def test_media_failure_preserves_original_when_profile_unavailable(self):
        failure=media.ValidationError('decode failed');failure.media_decode_failed=True
        with patch.object(media,'decoded_duration',side_effect=failure),patch.object(media,'_mp3_tag_copy',side_effect=media.ValidationError('unsupported')):
            with self.assertRaises(media.ValidationError) as caught:media._source_duration({}, {},Path('source.mp3'),Path('.'),threading.Event(),1)
            self.assertIs(caught.exception,failure)
    def test_derived_input_mapping_keeps_original_provenance_and_frozen_manifest(self):
        manifest={'sources':[{'path':'original.mp3','sha256':'original-hash'}]};before=copy.deepcopy(manifest)
        stage=Path('private-stage');proof={'affected_audio_seconds':0}
        with media.generated_artifacts(stage):
            media._ARTIFACTS.current[4][('original.mp3','original-hash')]={'name':'derived.mp3','sha256':'derived-hash','proof':proof}
            def consume(m,s,c,d,cover,stop,progress,encoding,original,feed):
                self.assertEqual(c,['derived.mp3']);self.assertEqual(original,['source00000.mp3']);return 'out',{}
            with patch.object(media,'digest',return_value='derived-hash'),patch.object(media,'ProtectedFiles',side_effect=lambda _:contextlib.nullcontext()),patch.object(media,'_encode_inputs',side_effect=consume):
                _,validation=media._encode_private(manifest,stage,['source00000.mp3'],[1],None,threading.Event(),None,{})
            self.assertEqual(validation['source_working_repairs'],[proof])
            with patch.object(media,'digest',return_value='changed'),patch.object(media,'_encode_inputs') as encode:
                with self.assertRaises(media.ValidationError):media._encode_private(manifest,stage,['source00000.mp3'],[1],None,threading.Event(),None,{})
                encode.assert_not_called()
        self.assertEqual(manifest,before)
    def test_completion_callback_distinguishes_media_exit_from_context_and_bounds_failure(self):
        area=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT','C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared'))/('mp3-completion-'+uuid.uuid4().hex)
        area.mkdir(parents=True)
        @contextlib.contextmanager
        def failed_context(_):
            yield
            raise media.ValidationError('context closure failed')
        for mode in ('media_nonzero','context_failure','output_overflow'):
            folder=area/mode;folder.mkdir();completed=[]
            def fake_process(*args,**kwargs):
                if mode=='output_overflow':kwargs['stderr'].write(b'x'*(1024*1024+1))
                return types.SimpleNamespace(returncode=1,poll=lambda:1)
            context=failed_context if mode=='context_failure' else lambda _:contextlib.nullcontext()
            with patch.object(media.subprocess,'Popen',side_effect=fake_process),patch.object(media,'closed_media_job',side_effect=context):
                with self.assertRaises(media.ValidationError):media.run_owned([sys.executable],folder,threading.Event(),diagnostic=lambda *args:completed.append(args))
            self.assertEqual(len(completed),1 if mode=='media_nonzero' else 0)
            if completed:self.assertTrue(completed[0][0].data['context_completed'])

@unittest.skipUnless(os.environ.get('BOOKS_MP3_REAL_FIXTURE'),'Explicit private fixture opt-in required')
class ActualPrivateStagingTests(unittest.TestCase):
    def test_verified_tag_copy_used_only_as_derived_encoder_input(self):
        source=Path(os.environ['BOOKS_MP3_REAL_FIXTURE']);data=source.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),'e2deceb321010a2b3f7e813c3bfceccf2f4213ec7d83a17019c81f55f77047ed')
        stage_parent=Path(os.environ.get('BOOKS_QA_FIXTURE_ROOT',str(source.parent)));stage_parent.mkdir(parents=True,exist_ok=True)
        # The staging folder is removed when the test ends: a direct run (no BOOKS_QA_FIXTURE_ROOT) stages beside the
        # private fixture, and a 2026-10-24 run left a 117 MB app-staging folder there.
        temp=tempfile.TemporaryDirectory(prefix='app-staging-',dir=stage_parent,ignore_cleanup_errors=True);self.addCleanup(temp.cleanup);stage=Path(temp.name)
        item={'path':str(source),'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'modified':str(source.stat().st_mtime_ns)}
        manifest={'job_id':'private-diagnostic','candidate_id':'private-candidate','candidate_revision':1,'sources':[item],
            'metadata_facts':{'source_fingerprint':'private'},'root':str(source.parent)}
        before=copy.deepcopy(manifest);stop=threading.Event()
        with media.generated_artifacts(stage) as artifacts:
            value=media._mp3_tag_copy(manifest,item,source,stage,stop,2182)
            self.assertEqual(value['proof']['affected_audio_seconds'],0)
            self.assertEqual(value['proof']['frame_count'],83499)
            self.assertEqual(value['proof']['native_pcm']['sample_count'],96190848)
            self.assertEqual(value['sha256'],'c76279acb6f2d0896b745daf814a969b047ccc2ceca8a9e0fd53382c360aa959')
            alias=stage/'source00000.mp3';alias.write_bytes(data)
            # The frozen original snapshot remains the receipt/provenance input.
            def encode(manifest_,stage_,copies,durations,cover,stop_,progress,encoding,original_copies,feed):
                self.assertEqual(copies,[value['name']]);self.assertEqual(original_copies,[alias.name])
                self.assertEqual(media.digest(alias),item['sha256'])
                return stage/'not-created.m4b',{}
            with patch.object(media,'_encode_inputs',side_effect=encode):
                _,validation=media._encode_private(manifest,stage,[alias.name],[value['duration']],None,stop,lambda *a:None,{'mode':'private-check'})
            self.assertEqual(validation['source_working_repairs'][0]['affected_audio_seconds'],0)
            self.assertIn(value['name'],artifacts)
            self.assertEqual(media._source_duration(manifest,item,alias,stage,stop,1),value['duration'])
            repaired=stage/value['name']
            with repaired.open('ab') as stream:stream.write(b'x')
            with self.assertRaises(media.ValidationError):media._mp3_tag_copy(manifest,item,alias,stage,stop,1)
        self.assertEqual(manifest,before);self.assertEqual(source.read_bytes(),data)

if __name__=='__main__':unittest.main()

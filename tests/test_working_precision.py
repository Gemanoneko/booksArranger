"""Private complete-stream precision, volume admission and queue-hold fixtures."""
import errno,hashlib,json,math,shutil,struct,tempfile,threading,unittest,uuid
from pathlib import Path
from unittest.mock import Mock,patch
import audio_pipeline as pipeline
from audio_jobs import AudioJobs

AREA=Path(__file__).resolve().parents[1]/'scratch'/'cleanup-precision-tests'
AREA.mkdir(parents=True,exist_ok=True)

class ExpandedPcmTests(unittest.TestCase):
    def test_fragmented_integer_and_float_samples_match_all_canonical_doubles(self):
        for kind,width,values in (('s16',2,[-32768,-1,0,1,16384,32767]),('s24',3,[-8388608,-1,0,1,4194304,8388607]),('s32',4,[-2147483648,-1,0,1,1073741825,2147483647]),('f32',4,[-0.0,0.0,0.5,-0.5,2**-140,float('inf')])):
            with self.subTest(kind=kind):
                if kind=='s24':raw=b''.join(v.to_bytes(3,'little',signed=True) for v in values)
                else:raw=struct.pack('<'+{'s16':'h','s32':'i','f32':'f'}[kind]*len(values),*values)
                scale={'s16':32768,'s24':8388608,'s32':2147483648,'f32':1}[kind]
                if kind=='f32':values=list(struct.unpack('<'+'f'*len(values),raw))
                expected=pipeline.NativePcmHash(2);expected.feed(b''.join(struct.pack('<d',v/scale) for v in values))
                actual=pipeline.ExpandedPcmHash(2,kind)
                for index in range(0,len(raw),5):actual.feed(raw[index:index+5])
                self.assertEqual(actual.result(),expected.result())
    def test_nan_payload_and_signed_zero_have_byte_precise_proof(self):
        raw=struct.pack('<III',0x7fc00001,0x80000000,0)
        values=struct.unpack('<fff',raw);expected=pipeline.NativePcmHash(1)
        expected.feed(b''.join(struct.pack('<d',value) for value in values))
        actual=pipeline.ExpandedPcmHash(1,'f32');actual.feed(raw)
        self.assertEqual(actual.result(),expected.result())
        self.assertNotEqual(struct.pack('<d',values[1]),struct.pack('<d',values[2]))
    def test_incomplete_bytes_and_incomplete_multichannel_frames_refuse(self):
        for raw,channels,kind in ((b'\x01',1,'s16'),(b'\x00'*3,2,'s24'),(b'',1,'f32')):
            with self.subTest(raw=raw,channels=channels):
                proof=pipeline.ExpandedPcmHash(channels,kind);proof.feed(raw)
                with self.assertRaises(pipeline.ValidationError):proof.result()


def wav(path,kind,values,rate=48000,channels=1):
    bits={'s16':16,'s24':24,'s32':32,'f32':32,'f64':64}[kind]
    repeated=(values*max(1,2400//len(values)))
    if kind=='s24':raw=b''.join(value.to_bytes(3,'little',signed=True) for value in repeated)
    else:raw=struct.pack('<'+{'s16':'h','s32':'i','f32':'f','f64':'d'}[kind]*len(repeated),*repeated)
    block=channels*bits//8;fmt=struct.pack('<HHIIHH',3 if kind.startswith('f') else 1,channels,rate,rate*block,block,bits)
    data=b'WAVEfmt '+struct.pack('<I',len(fmt))+fmt+b'data'+struct.pack('<I',len(raw))+raw
    path.write_bytes(b'RIFF'+struct.pack('<I',len(data))+data)
    return len(repeated)//channels/rate

class RealPrecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup);self.stage=Path(self.temp.name)
        self.stop=threading.Event();self.encoding={'mode':'normalize','sample_rate':48000,'channels':1,'bitrate':128000}
    def streamed(self,source,duration):
        """The real streamed proof path: reference decode, then the bytes actually handed to the encoder."""
        fed=[]
        with pipeline.generated_artifacts(self.stage):
            references,joined=pipeline.normalized_references(self.stage,[source.name],self.encoding,self.stop,[duration])
            pipeline.stream_normalized(fed.append,self.stage,[source.name],[duration],self.encoding,self.stop,references,joined)
        raw=b''.join(fed);proof=pipeline.NativePcmHash(self.encoding['channels']);proof.feed(raw)
        self.assertEqual(proof.result(),joined,'the encoder is fed exactly the proven PCM')
        self.assertEqual(list(self.stage.glob('normalized*.wav')),[],'no uncompressed copy is written')
        return raw
    def check(self,kind,values,expected,rate=48000,channels=1):
        source=self.stage/'source00000.wav';duration=wav(source,kind,values,rate,channels)
        self.encoding['channels']=channels
        raw=self.streamed(source,duration)
        fed=[value[0] for value in struct.iter_unpack('<d',raw)]
        if kind=='s24':exact=[value/8388608 for value in values]
        elif kind in ('f32','f64'):exact=list(struct.unpack('<'+kind[1]*0+('f' if kind=='f32' else 'd')*len(values),struct.pack('<'+('f' if kind=='f32' else 'd')*len(values),*values)))
        else:exact=[value/{'s16':32768,'s32':2147483648}[kind] for value in values]
        repeated=(exact*max(1,2400//len(values)))
        self.assertEqual([struct.pack('<d',v) for v in fed],[struct.pack('<d',v) for v in repeated],'every low bit, subnormal and signed zero survives into the encoder input')
    def test_smallest_exact_pcm16(self):self.check('s16',[-32768,-1,0,1,16384,32767],'pcm_s16le')
    def test_smallest_exact_pcm24(self):self.check('s24',[-8388607,-1,0,1,4194305],'pcm_s24le')
    def test_pcm32_low_bits_remain_exact(self):self.check('s32',[-2147483647,-1,0,1,1073741825],'pcm_s32le')
    def test_float32_subnormals_and_signed_zero_remain_exact(self):self.check('f32',[-0.0,0.0,2**-140,0.25,-0.3],'pcm_f32le')
    def test_float64_low_bits_never_rounded(self):self.check('f64',[0.1,0.5+2**-45,-0.25-2**-43],'pcm_f64le')
    def test_resampled_stereo_uses_full_exact_reference(self):
        source=self.stage/'source00000.wav';duration=wav(source,'s16',[0,1,1000,-7000,12000,-2000],44100,2)
        self.encoding['channels']=2
        raw=self.streamed(source,duration);self.assertEqual(len(raw)%16,0)
    def mixed_join(self,recipes,expected_codec,label):
        stage=self.stage/label;stage.mkdir();copies=[];durations=[];expected=pipeline.NativePcmHash(1)
        for index,(kind,values) in enumerate(recipes):
            source=stage/f'source{index:05d}.wav';durations.append(wav(source,kind,values));copies.append(source.name)
            raw=source.read_bytes()[44:]
            if kind=='s24':values=[int.from_bytes(raw[i:i+3],'little',signed=True)/8388608 for i in range(0,len(raw),3)]
            else:
                fmt={'s16':'h','s32':'i','f32':'f','f64':'d'}[kind];scale={'s16':32768,'s32':2147483648,'f32':1,'f64':1}[kind]
                values=[value[0]/scale for value in struct.iter_unpack('<'+fmt,raw)]
            expected.feed(b''.join(struct.pack('<d',value) for value in values))
        from test_automatic_media_policy import PrivateMediaTests
        manifest=PrivateMediaTests.manifest(type('RootFixture',(),{'root':stage})(),[stage/name for name in copies])
        before=[pipeline.digest(stage/name) for name in copies]
        output,validation=pipeline.create_private(manifest,stage/'actual-app-stage',self.stop)
        self.assertTrue(output.is_file());self.assertEqual(validation['checks'],'Output checks passed')
        self.assertEqual(validation['normalized_pcm_codec'],'pcm_f64le')  # the encoder reads the exact f64 stream
        self.assertEqual(validation['normalized_joined_pcm'],expected.result())
        self.assertEqual(list((stage/'actual-app-stage').rglob('normalized*.wav')),[]);self.assertEqual(list((stage/'actual-app-stage').rglob('inputs.txt')),[])
        self.assertEqual(before,[pipeline.digest(stage/name) for name in copies])
    def test_mixed_s32_f32_join_is_exact_in_both_orders(self):
        recipes=[('s32',[-2147483647,-1,0,1,1073741825]),('f32',[2**-140,0.5,-0.3,-0.0])]
        self.mixed_join(recipes,'pcm_f64le','integer_first');self.mixed_join(list(reversed(recipes)),'pcm_f64le','float_first')
    def test_different_integer_widths_join_is_exact_in_both_orders(self):
        recipes=[('s16',[-1,0,1,16384]),('s24',[-8388607,-1,0,1,4194305])]
        self.mixed_join(recipes,'pcm_s24le','short_first');self.mixed_join(list(reversed(recipes)),'pcm_s24le','long_first')
    def test_real_create_private_refuses_a_stream_that_differs_from_its_proof(self):
        from test_automatic_media_policy import PrivateMediaTests
        first=self.stage/'first.wav';second=self.stage/'second.wav'
        wav(first,'s32',[1,1073741825,-2147483647]);wav(second,'f32',[2**-140,0.3,-0.0])
        manifest=PrivateMediaTests.manifest(type('RootFixture',(),{'root':self.stage})(),[first,second])
        before=[pipeline.digest(first),pipeline.digest(second)];original=pipeline.normalized_references
        def altered(*args,**kwargs):
            references,joined=original(*args,**kwargs)
            return [references[0],dict(references[1],sha256='0'*64)],joined
        with patch.object(pipeline,'normalized_references',side_effect=altered):
            with self.assertRaisesRegex(pipeline.ValidationError,'Streamed normalized PCM differs'):
                pipeline.create_private(manifest,self.stage/'actual-app-stage',self.stop)
        self.assertEqual(before,[pipeline.digest(first),pipeline.digest(second)]);self.assertFalse(Path(manifest['destination']).exists())
        self.assertEqual(list((self.stage/'actual-app-stage').rglob('normalized*.wav')),[])

class SpaceEstimateTests(unittest.TestCase):
    def test_estimate_reserves_snapshots_and_three_outputs_without_any_pcm_copy(self):
        encoding={'mode':'normalize','sample_rate':96000,'channels':2,'bitrate':256000};durations=[100,200];source=1000000
        output=pipeline.output_space_required(source,durations,encoding,2)
        self.assertEqual(pipeline.working_space_required(source,durations,encoding,2),source+3*output+64*1024*1024)
    def test_the_lost_symbol_shape_needs_a_small_multiple_of_its_sources(self):
        # 155 M4B parts, 1.28 GB, about 22 h of 44.1 kHz stereo at 128 kbit/s: v0.16.6 asked for 62.7 GB.
        encoding={'mode':'normalize','sample_rate':44100,'channels':2,'bitrate':128000};source=1283446143;durations=[22.11*3600/155]*155
        required=pipeline.working_space_required(source,durations,encoding,155)
        self.assertLess(required,6*source);self.assertLess(required,8*1024**3)
    def test_copy_has_no_normalized_pcm_reservation(self):
        encoding={'mode':'copy','sample_rate':48000,'channels':6}
        output=pipeline.output_space_required(2000,[1],encoding,1)
        self.assertEqual(pipeline.working_space_required(2000,[1],encoding,1),2000+3*output+64*1024*1024)
    def test_unknown_nonfinite_durations_refuse(self):
        for durations in ([],[0],[-1],[float('nan')],[float('inf')]):
            with self.subTest(durations=durations),self.assertRaises(pipeline.ValidationError):pipeline.working_space_required(1,durations,{'mode':'normalize','sample_rate':48000,'channels':1,'bitrate':128000},1)
    def test_initial_floor_holds_without_decoding_or_copying(self):
        with patch.object(pipeline.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(10,10,0)),patch.object(pipeline,'probe') as probe:
            with self.assertRaises(OSError) as caught:pipeline.check_working_space({'sources':[{'size':1000000}]},None,None)
        self.assertEqual(caught.exception.errno,errno.ENOSPC);probe.assert_not_called()

class QueueSpaceHoldTests(unittest.TestCase):
    def test_enospc_parks_the_rest_of_queue_after_one_attempt(self):
        with tempfile.TemporaryDirectory(dir=AREA) as directory:
            runner=Mock(side_effect=OSError(errno.ENOSPC,'private short space'));jobs=AudioJobs(Path(directory)/'queue.sqlite',runner,Mock(return_value=True),Mock(return_value=True));self.addCleanup(jobs.close)
            callback=Mock();jobs.on_space_hold=callback
            for index in range(3):
                manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'sources':[{'path':'fixture'+str(index)+'.mp3','sha256':'a'*64,'fingerprint':{}}],'metadata':{},'destination':'fixture'+str(index)+'.m4b','profile':'fixture','evidence':{},'cover':{}}
                jobs.enqueue(manifest)
            jobs._work();status=jobs.status()
            self.assertEqual(runner.call_count,1);callback.assert_called_once()
            self.assertEqual(status['state'],'Paused');self.assertEqual(status['queued'],2);self.assertEqual(status['failed'],1)
            self.assertTrue(jobs._stop.is_set())

if __name__=='__main__':unittest.main()

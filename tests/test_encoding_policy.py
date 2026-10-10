import base64,json,os,random,shutil,struct,subprocess,tempfile,threading,unittest,uuid,zlib
from pathlib import Path
from encoding_policy import PROFILE,LEGACY_PROFILE,freeze_policy,choose_encoding
from audio_pipeline import create_private,digest,fingerprint
from merge_service import MergeService
from native_io import DirectoryBoundary

AREA=Path(__file__).resolve().parents[1]/'scratch'/'quality-tests';AREA.mkdir(parents=True,exist_ok=True)
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')

class PolicyTests(unittest.TestCase):
    def test_128k_mono_is_preserved(self):
        v=choose_encoding([('mp3','44100',1,'128000')]*2)
        self.assertEqual((v['bitrate'],v['channels'],v['sample_rate']),(128000,1,44100))
    def test_highest_track_bitrate_no_160k_cap(self):
        v=choose_encoding([('mp3','48000',2,'128000'),('mp3','48000',2,'256000')])
        self.assertEqual(v['bitrate'],256000)
    def test_low_rate_is_not_raised_to_an_artificial_floor(self):
        self.assertEqual(choose_encoding([('mp3','22050',1,'32000')])['bitrate'],32000)
    def test_unknown_or_invalid_bitrate_requires_review(self):
        for value in [None,'','N/A',0,-1,True,'99999999']:
            with self.subTest(value=value),self.assertRaises(ValueError):choose_encoding([('mp3','44100',1,value)])
    def test_mixed_layouts_rates_and_raw_pcm_block(self):
        for profiles in [[('mp3','44100',1,'128000'),('mp3','48000',1,'128000')],[('mp3','44100',1,'128000'),('mp3','44100',2,'128000')],[('pcm_s16le','44100',1,'705600')],[('mp3','44100',6,'128000')]]:
            with self.subTest(profiles=profiles),self.assertRaises(ValueError):choose_encoding(profiles)
    def test_aac_capacity_is_not_silently_clamped(self):
        with self.assertRaises(ValueError):choose_encoding([('mp3','44100',1,'320000')])
    def test_frozen_policy_has_no_size_gate_or_retry(self):
        v=freeze_policy([{'size':100}]);self.assertEqual(v['source_bytes'],100)
        self.assertNotIn('max_bytes',v);self.assertNotIn('max_retries',v)

class ActualMediaTests(unittest.TestCase):
    def build(self,root,channels,rate,bitrate,legacy=False,duration=1):
        sources=[]
        for i in range(2):
            path=root/(str(i)+'.mp3')
            subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i',f'sine=frequency=440:duration={duration}','-ar',str(rate),'-ac',str(channels),'-c:a','libmp3lame','-b:a',str(bitrate),str(path)],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            sources.append({'path':str(path),**fingerprint(path),'sha256':digest(path),'metadata':{'tags':{'comment':'Чтец'}}})
        cover=root/'cover.png';cover.write_bytes(PNG)
        m={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'root':str(root),'destination':str(root/'final.m4b'),'profile':LEGACY_PROFILE if legacy else PROFILE,'sources':sources,'cover':{'path':str(cover),'sha256':digest(cover)},'comments':'Чтец','chapters':[],
           'metadata':{'title':'Test Book','canonical_author':'Name Author','narrator':'Чтец','series':'Series','number':'9'}}
        if not legacy:m['encoding_policy']=freeze_policy(sources)
        return m
    def test_real_mono_and_high_bitrate_stereo_targets(self):
        for channels,rate,bitrate in [(1,44100,128000),(2,48000,256000)]:
            with self.subTest(channels=channels),tempfile.TemporaryDirectory(dir=AREA) as name:
                root=Path(name);m=self.build(root,channels,rate,bitrate);before=[digest(x['path']) for x in m['sources']]
                output,v=create_private(m,root/'stage',threading.Event())
                self.assertEqual((v['encoding']['bitrate'],v['encoding']['channels'],v['encoding']['sample_rate']),(bitrate,channels,rate))
                self.assertAlmostEqual(v['expected_duration'],v['decoded_duration'],delta=.1)
                self.assertEqual(v['tags']['artist'],'Name Author');self.assertEqual(v['tags']['track'],'9')
                self.assertEqual(before,[digest(x['path']) for x in m['sources']])
                self.assertFalse((output.parent/'checked-retry.m4b').exists())
    def test_small_book_may_grow_without_lower_bitrate_retry(self):
        with tempfile.TemporaryDirectory(dir=AREA) as name:
            root=Path(name);m=self.build(root,1,44100,128000,duration=.1)
            rng=random.Random(7)
            pixels=b''.join(b'\0'+rng.randbytes(32*3) for _ in range(32))
            def chunk(kind,value):return struct.pack('>I',len(value))+kind+value+struct.pack('>I',zlib.crc32(kind+value))
            cover=Path(m['cover']['path']);cover.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',32,32,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b''))
            m['cover']['sha256']=digest(cover)
            output,v=create_private(m,root/'stage',threading.Event())
            self.assertGreater(v['size'],sum(x['size'] for x in m['sources']))
            self.assertEqual(v['encoding']['bitrate'],128000);self.assertFalse((output.parent/'checked-retry.m4b').exists())
    def test_historical_completed_record_remains_valid(self):
        with tempfile.TemporaryDirectory(dir=AREA) as name:
            root=Path(name);m=self.build(root,1,44100,128000,legacy=True);output,v=create_private(m,root/'stage',threading.Event())
            self.assertEqual(v['profile'],LEGACY_PROFILE);self.assertEqual(v['encoding']['channels'],2)
            record={'root':str(root),'final_path':str(output),'size':v['size'],'sha256':v['sha256'],'validation':v}
            with DirectoryBoundary(root,output.parent) as boundary:record['parent_identity']=boundary.identities
            fake=type('OldService',(),{'inventory':type('Inv',(),{'roots':{'Audiobooks':str(root)}})()})()
            self.assertTrue(MergeService._output_valid(fake,record))

if __name__=='__main__':unittest.main()

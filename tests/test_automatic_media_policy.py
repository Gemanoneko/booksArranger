import base64, shutil, subprocess, tempfile, threading, unittest, uuid
from pathlib import Path
from encoding_policy import AUTOMATIC_PROFILE, choose_automatic_encoding, freeze_automatic_policy
from audio_pipeline import create_private, digest, fingerprint, source_chapters, ValidationError

AREA=Path(__file__).resolve().parents[1]/'scratch'/'automatic-media-tests'
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')

class AutomaticPolicyTests(unittest.TestCase):
    def test_mixed_rates_channels_preserve_highest(self):
        value=choose_automatic_encoding([('mp3','22050',1,'32000'),('mp3','48000',2,'192000')])
        self.assertEqual((value['mode'],value['sample_rate'],value['channels'],value['bitrate']),('normalize',48000,2,192000))
    def test_lossless_uses_explicit_quality_target(self):
        self.assertEqual(choose_automatic_encoding([('flac','44100',2,'1411200')])['bitrate'],256000)
    def test_existing_m4b_preserves_codec(self):
        for codec in ('aac','alac'):
            self.assertEqual(choose_automatic_encoding([(codec,'44100',2,'128000')],True)['mode'],'copy')
    def test_common_timing_origin_preserves_pts_dts_offset(self):
        from audio_pipeline import PacketTimingHash
        original=PacketTimingHash();original.feed(b'pts=0|dts=-1|duration=1\npts=1|dts=0|duration=1\n')
        shifted=PacketTimingHash();shifted.feed(b'pts=5|dts=4|duration=1\npts=6|dts=5|duration=1\n')
        changed=PacketTimingHash();changed.feed(b'pts=0|dts=0|duration=1\npts=1|dts=1|duration=1\n')
        self.assertEqual(original.result(),shifted.result());self.assertNotEqual(original.result(),changed.result())
    def test_no_guessed_downmix_or_bad_profiles(self):
        for profile in [('mp3','44100',6,'128000'),('unknown','44100',2,'128000'),('mp3','999999',1,'128000')]:
            with self.assertRaises(ValueError):choose_automatic_encoding([profile])

class PrivateMediaTests(unittest.TestCase):
    def setUp(self):
        AREA.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
    def media(self,name,codec,rate=44100,channels=1):
        path=self.root/name
        from audio_pipeline import run_owned
        run_owned([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=1',
            '-ar',str(rate),'-ac',str(channels),'-c:a',codec,str(path)],self.root,threading.Event(),30)
        return path
    def manifest(self,paths):
        cover=self.root/'custom.png';cover.write_bytes(PNG)
        sources=[{'path':str(path),**fingerprint(path),'sha256':digest(path),'metadata':{'tags':{}}} for path in paths]
        return {'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,'root':str(self.root),
            'destination':str(self.root/'final.m4b'),'profile':AUTOMATIC_PROFILE,'encoding_policy':freeze_automatic_policy(sources),
            'sources':sources,'cover':{'path':str(cover),'sha256':digest(cover)},'comments':'','chapters':[],
            'metadata':{'title':'Private Book','canonical_author':'Verified Author'}}
    def assert_preserved_source(self,source,output,proof):
        """Check the new receipt against independent actual file and codec reads."""
        import hashlib
        from audio_pipeline import audio_packet_hash,copied_audio_evidence,native_pcm_evidence
        receipt=proof['metadata_preservation'];original=source.read_bytes();candidate=output.read_bytes()
        self.assertTrue(receipt['all_retained_bytes_verified']);self.assertTrue(receipt['pcm_verified'])
        self.assertEqual(receipt['source_sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(receipt['sha256'],hashlib.sha256(candidate).hexdigest())
        self.assertEqual(receipt['size'],len(candidate));offset=receipt['old_moov_offset']
        self.assertEqual(original[offset+4:offset+8],b'moov')
        expected=original[:offset+4]+b'free'+original[offset+8:]
        self.assertEqual(candidate[:len(original)],expected)
        self.assertEqual(receipt['old_moov_sha256'],hashlib.sha256(original[offset:offset+receipt['old_moov_size']]).hexdigest())
        self.assertEqual(receipt['appended_moov_sha256'],hashlib.sha256(candidate[len(original):]).hexdigest())
        self.assertGreater(len(candidate),len(original));self.assertTrue(receipt['track_sha256'])
        stop=threading.Event();duration=proof['expected_duration'];encoding=proof['encoding']
        self.assertEqual(audio_packet_hash(source,self.root,stop,duration),audio_packet_hash(output,self.root,stop,duration))
        first=copied_audio_evidence(source,self.root,stop,duration,source_relative=True)
        second=copied_audio_evidence(output,self.root,stop,duration,source_relative=True)
        self.assertEqual(first,second);self.assertEqual(second,proof['copied_audio_evidence'])
        self.assertGreater(second['relative_packet_timing']['packet_count'],0)
        first_pcm=native_pcm_evidence(source,self.root,stop,duration,encoding)
        second_pcm=native_pcm_evidence(output,self.root,stop,duration,encoding)
        self.assertEqual(first_pcm,second_pcm);self.assertEqual(second_pcm,proof['native_pcm_evidence'])
        self.assertGreater(second_pcm['sample_count'],0)
        self.assertEqual(source_chapters(source,self.root,stop,duration),source_chapters(output,self.root,stop,duration))
        self.assertEqual(digest(source),receipt['source_sha256'])
    def test_actual_mixed_audio_custom_cover_verified(self):
        paths=[self.media('first.mp3','libmp3lame',22050,1),self.media('second.flac','flac',48000,2)]
        manifest=self.manifest(paths);before=[digest(path) for path in paths]
        output,proof=create_private(manifest,self.root/'stage',threading.Event())
        self.assertEqual(proof['encoding']['mode'],'normalize')
        self.assertEqual(proof['encoding']['channels'],2)
        self.assertAlmostEqual(proof['expected_duration'],proof['decoded_duration'],delta=.1)
        self.assertEqual(before,[digest(path) for path in paths]);self.assertTrue(output.is_file())
    def test_actual_m4b_copy_preserves_all_chapters_packets(self):
        path=self.media('existing.m4b','aac')
        from audio_pipeline import run_owned
        chapter_file=self.root/'chapters.txt'
        chapter_file.write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=500\ntitle=First\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=500\nEND=1000\ntitle=Second\n',encoding='utf8')
        chaptered=self.root/'chaptered.m4b'
        run_owned([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-i',str(path),'-f','ffmetadata','-i',str(chapter_file),'-map','0:a:0','-map_chapters','1','-c:a','copy',str(chaptered)],self.root,threading.Event(),30)
        manifest=self.manifest([chaptered]);manifest['source_chapters']=source_chapters(chaptered,self.root,threading.Event(),1)
        before=digest(chaptered)
        output,proof=create_private(manifest,self.root/'stage',threading.Event())
        self.assertEqual(proof['encoding']['mode'],'copy');self.assertEqual(len(proof['chapters']),2)
        self.assertEqual(proof['preserved_source_chapters'],manifest['source_chapters'])
        self.assert_preserved_source(chaptered,output,proof);self.assertEqual(before,digest(chaptered))
        self.assertGreater(proof['native_pcm_evidence']['sample_count'],0)
        self.assertEqual(proof['native_pcm_evidence']['channels'],1)
    def test_actual_missing_cover_gets_truthful_neutral_art(self):
        from neutral_cover import neutral_cover
        art=neutral_cover('Частная книга',['Проверенный Автор'])
        path=self.media('source.flac','flac');manifest=self.manifest([path])
        cover=Path(manifest['cover']['path']);cover.write_bytes(art['bytes']);manifest['cover']['sha256']=digest(cover)
        output,proof=create_private(manifest,self.root/'stage',threading.Event())
        self.assertEqual(art['kind'],'neutral');self.assertEqual(art['title'],'Частная книга')
        self.assertEqual(proof['encoding']['mode'],'normalize');self.assertTrue(output.is_file())
    def test_actual_multichannel_m4b_copy_preserves_layout(self):
        path=self.media('surround.m4b','aac',48000,6);manifest=self.manifest([path]);manifest['source_chapters']=[]
        output,proof=create_private(manifest,self.root/'stage',threading.Event())
        self.assertEqual(proof['encoding']['mode'],'copy');self.assertEqual(proof['encoding']['channels'],6)
        self.assertEqual(proof['encoding']['channel_layout'],'5.1');self.assert_preserved_source(path,output,proof)
    def test_real_edit_trim_changes_native_pcm_proof_without_payload_change(self):
        import struct
        from quicktime_chapters import boxes,box,CONTAINERS
        from audio_pipeline import native_pcm_evidence,audio_packet_hash
        path=self.media('untrimmed.m4b','aac');changed=self.root/'changed-edit.m4b';edits=[]
        def edit(data):
            output=[]
            for kind,value in boxes(data):
                if kind in CONTAINERS:value=box(kind,edit(value[8:]))
                elif kind==b'elst':
                    raw=bytearray(value)
                    self.assertEqual(raw[8],0);self.assertEqual(int.from_bytes(raw[12:16],'big'),1)
                    old=struct.unpack_from('>i',raw,20)[0];struct.pack_into('>i',raw,20,old+1);value=bytes(raw);edits.append(1)
                output.append(value)
            return b''.join(output)
        changed.write_bytes(edit(path.read_bytes()));self.assertEqual(len(edits),1)
        encoding={'sample_rate':44100,'channels':1,'channel_layout':'mono'};stop=threading.Event()
        self.assertEqual(audio_packet_hash(path,self.root,stop,1),audio_packet_hash(changed,self.root,stop,1))
        first=native_pcm_evidence(path,self.root,stop,1,encoding);second=native_pcm_evidence(changed,self.root,stop,1,encoding)
        self.assertNotEqual(first['sample_count'],second['sample_count']);self.assertNotEqual(first['sha256'],second['sha256'])
    def test_actual_alac_copy_has_complete_native_pcm_proof(self):
        path=self.media('lossless.m4b','alac');manifest=self.manifest([path]);manifest['source_chapters']=[]
        output,proof=create_private(manifest,self.root/'stage',threading.Event())
        self.assertEqual(proof['encoding']['codec'],'alac');self.assertEqual(proof['native_pcm_evidence']['sample_count'],44100)
        self.assertEqual(len(proof['native_pcm_evidence']['sha256']),64);self.assertTrue(output.is_file())
    def test_final_output_cannot_be_written_during_verification(self):
        path=self.media('existing.m4b','aac');manifest=self.manifest([path]);manifest['source_chapters']=[];attempts=[]
        def progress(phase,details):
            if phase=='Checking output':
                output=next((self.root/'stage').rglob('checked.m4b'))
                with self.assertRaises(PermissionError):output.write_bytes(b'replaced')
                attempts.append(1)
        output,proof=create_private(manifest,self.root/'stage',threading.Event(),progress)
        self.assertEqual(attempts,[1]);self.assertEqual(digest(output),proof['sha256'])
    def leading_gap_source(self):
        from audio_pipeline import run_owned
        path=self.media('source.m4b','aac');offset=self.root/'leading-gap.m4b'
        run_owned([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-itsoffset','0.25','-i',str(path),'-map','0:a:0','-c:a','copy',str(offset)],self.root,threading.Event(),30)
        return offset
    def test_actual_existing_leading_gap_preserved_but_ordinary_remux_refused(self):
        from audio_pipeline import copied_audio_evidence
        offset=self.leading_gap_source();manifest=self.manifest([offset]);manifest['source_chapters']=[]
        output,proof=create_private(manifest,self.root/'stage',threading.Event())
        self.assertGreater(int(proof['copied_audio_evidence']['presentation']['start_pts']),0)
        self.assert_preserved_source(offset,output,proof)
        # The same actual source remains ineligible for the ordinary remux path.
        with self.assertRaisesRegex(ValidationError,'leading gaps|presentation'):
            copied_audio_evidence(offset,self.root,threading.Event(),1,source_relative=False)
    def test_actual_preservation_refuses_contradictory_output_presentation(self):
        import copy,audio_pipeline
        from unittest.mock import patch
        offset=self.leading_gap_source();manifest=self.manifest([offset]);manifest['source_chapters']=[]
        before=digest(offset);actual=audio_pipeline.copied_audio_evidence;reached=[]
        def contradictory(path,*args,**kwargs):
            evidence=actual(path,*args,**kwargs)
            if Path(path).name=='checked.m4b':
                self.assertTrue(kwargs['source_relative']);reached.append(str(path))
                evidence=copy.deepcopy(evidence);evidence['presentation']['start_pts']+=1
            return evidence
        with patch('audio_pipeline.copied_audio_evidence',side_effect=contradictory):
            with self.assertRaisesRegex(ValidationError,'Preservation changed decoder, packets or presentation'):
                create_private(manifest,self.root/'stage',threading.Event())
        self.assertEqual(len(reached),1);self.assertEqual(digest(offset),before)
        self.assertFalse(Path(manifest['destination']).exists())
    def test_streamed_pcm_that_differs_from_its_proof_is_refused_unpublished(self):
        from unittest.mock import patch
        import audio_pipeline
        path=self.media('source.flac','flac');manifest=self.manifest([path]);before=digest(path);original=audio_pipeline.normalized_references
        def substituted(*args,**kwargs):
            references,joined=original(*args,**kwargs)
            return [dict(references[0],sha256='f'*64)],joined
        with patch('audio_pipeline.normalized_references',side_effect=substituted):
            with self.assertRaisesRegex(ValidationError,'Streamed normalized PCM differs'):
                create_private(manifest,self.root/'stage',threading.Event())
        self.assertEqual(digest(path),before);self.assertFalse(Path(manifest['destination']).exists())
        self.assertFalse(any((self.root/'stage').rglob('normalized*.wav')))
    def test_changed_m4b_chapters_fail_closed(self):
        path=self.media('existing.m4b','aac');manifest=self.manifest([path]);manifest['source_chapters']=[{'start':0,'end':1000,'title':'Invented'}]
        with self.assertRaises(ValidationError):create_private(manifest,self.root/'stage',threading.Event())

if __name__=='__main__':unittest.main()

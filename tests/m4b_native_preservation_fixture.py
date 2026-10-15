"""Private real AAC fixtures; native codec proof, never the user's library."""
import hashlib
import json
import os
import re
import shutil
import threading
import uuid
import unittest
from unittest.mock import patch
from pathlib import Path
import audio_pipeline as pipeline
from m4b_preservation import boxes,build,plan,stream_candidate,verify_candidate


class NativeM4BPreservationTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(os.environ['BOOKS_M4B_FIXTURE_ROOT'])/self._testMethodName
        self.root.mkdir();self.stop=threading.Event()
        self.cover=self.root/'cover.png'
        # Generate and decode a real small cover, rather than a magic-byte stub.
        pipeline.run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-nostdin','-n',
          '-f','lavfi','-i','color=c=blue:s=32x32:d=0.04','-frames:v','1','-threads','1',str(self.cover)],self.root,self.stop,30)
        self.chapters=self.root/'chapters.txt'
        self.chapters.write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=250\ntitle=First chapter\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=250\nEND=500\ntitle=Second chapter\n',encoding='utf8')
        self.source=self.root/'source00000.m4b'
        pipeline.run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-n',
          '-f','lavfi','-i','sine=frequency=997:sample_rate=44100:duration=0.5','-f','ffmetadata','-i',str(self.chapters),
          '-map','0:a:0','-map_chapters','1','-c:a','aac','-b:a','64000','-movflags','+faststart',str(self.source)],self.root,self.stop,30)

    def test_real_aac_pipeline_preserves_complete_pcm_clocks_chapters_and_tags(self):
        raw=pipeline.probe(self.source,self.root,self.stop)
        duration,profile=pipeline.audio_info(raw)
        stream=next(s for s in raw['streams'] if s.get('codec_type')=='audio')
        encoding={'mode':'copy','codec':'aac','sample_rate':int(profile[1]),'channels':profile[2],
                  'channel_layout':stream.get('channel_layout')}
        facts=self.source.stat()
        manifest={'sources':[{'path':str(self.source),'sha256':pipeline.digest(self.source),
                              'size':facts.st_size,'modified':str(facts.st_mtime_ns)}],
          'metadata':{'title':'Private Книга','canonical_author':'Fixture Author'},
          'cover':{'path':str(self.cover),'sha256':pipeline.digest(self.cover)},
          'source_chapters':pipeline.source_chapters(self.source,self.root,self.stop,duration)}
        output,validation=pipeline._encode_inputs(manifest,self.root,[self.source.name],[duration],
          self.cover,self.stop,lambda *_:None,encoding,[self.source.name])
        self.assertEqual(output.name,'checked.m4b')
        self.assertFalse((self.root/'compatible.m4b').exists())
        self.assertEqual({path.name for path in self.root.glob('*.m4b')},{'source00000.m4b','checked.m4b'})
        self.assertTrue(validation['metadata_preservation']['pcm_verified'])
        self.assertTrue(validation['metadata_preservation']['all_retained_bytes_verified'])
        self.assertEqual(len(validation['chapters']),2)
        self.assertEqual(validation['tags']['album'],'Private Книга')
        self.assertGreater(validation['native_pcm_evidence']['sample_count'],0)
        self.assertEqual(pipeline.digest(self.source),manifest['sources'][0]['sha256'])

    def test_real_aac_exact_source_clock_and_decoder_proof_rejects_payload_corruption(self):
        source=self.source.read_bytes();read=lambda at,count:source[at:at+count]
        preservation=plan(len(source),read,{'title':'Private title'},self.cover.read_bytes())
        output=[];receipt=stream_candidate(preservation,read,output.append)
        candidate=bytearray(b''.join(output))
        start=preservation.mdat_extents[0][0];candidate[start]^=1
        with self.assertRaisesRegex(ValueError,'retained source bytes'):
            verify_candidate(preservation,read,len(candidate),lambda at,count:bytes(candidate[at:at+count]))
        self.assertFalse(receipt['pcm_verified'])

    def test_pipeline_refuses_independent_pcm_metadata_profile_and_chapter_mismatch(self):
        raw=pipeline.probe(self.source,self.root,self.stop);duration,profile=pipeline.audio_info(raw)
        stream=next(s for s in raw['streams'] if s.get('codec_type')=='audio')
        encoding={'mode':'copy','codec':'aac','sample_rate':int(profile[1]),'channels':profile[2],
                  'channel_layout':stream.get('channel_layout')}
        facts=self.source.stat();chapters=pipeline.source_chapters(self.source,self.root,self.stop,duration)
        source_item={'path':str(self.source),'sha256':pipeline.digest(self.source),'size':facts.st_size,'modified':str(facts.st_mtime_ns)}
        manifest={'sources':[source_item],'metadata':{'title':'Private title','canonical_author':'Fixture Author'},
          'cover':{'path':str(self.cover),'sha256':pipeline.digest(self.cover)},'source_chapters':chapters}
        tags={'title':'Private title','artist':'Fixture Author','album_artist':'Fixture Author','media_type':'2'}
        # Each independent verifier must still reject contradictory evidence.
        for mismatch in ('pcm','metadata','profile','chapters'):
            with self.subTest(mismatch=mismatch):
                attempt=self.root/mismatch;attempt.mkdir()
                shutil.copyfile(self.source,attempt/self.source.name)
                real_probe=pipeline.probe;real_chapters=pipeline.source_chapters
                def probe(path,*args):
                    result=real_probe(path,*args)
                    if Path(path).name=='checked.m4b':
                        if mismatch=='metadata':result['format']['tags']['title']='wrong'
                        if mismatch=='profile':next(s for s in result['streams'] if s.get('codec_type')=='audio')['sample_rate']='12345'
                    return result
                def chapter_probe(path,*args):
                    result=real_chapters(path,*args)
                    return [] if mismatch=='chapters' and Path(path).name=='checked.m4b' else result
                pcm=[{'sha256':'a'},{'sha256':'b' if mismatch=='pcm' else 'a'}]
                # Source/native success is proved in the other native case;
                # this is deliberately contradictory injected verifier evidence.
                if mismatch!='pcm':pcm=[{'sha256':'a','sample_count':22050,'sample_rate':44100}]*2
                reasons={'pcm':'Preservation changed complete native decoded audio','metadata':'Preserved output approved metadata differs',
                         'profile':'Preserved output audio profile is incorrect','chapters':'Preserved source chapter presentation changed'}
                with patch.object(pipeline,'probe',side_effect=probe) as probes,patch.object(pipeline,'source_chapters',side_effect=chapter_probe) as chapter_probes,patch.object(pipeline,'native_pcm_evidence',side_effect=pcm) as pcm_probes:
                    with self.assertRaisesRegex(pipeline.ValidationError,re.escape(reasons[mismatch])):
                        pipeline._preserve_single_m4b(manifest,attempt,self.source.name,[duration],self.cover,self.stop,lambda *_:None,encoding,tags)
                    self.assertEqual(pcm_probes.call_count,2)
                    if mismatch!='pcm':self.assertTrue(any(Path(call.args[0]).name=='checked.m4b' for call in probes.call_args_list))
                    if mismatch=='chapters':self.assertTrue(any(Path(call.args[0]).name=='checked.m4b' for call in chapter_probes.call_args_list))
                self.assertEqual(pipeline.digest(self.source),source_item['sha256'])

    def test_actual_copy_branch_closes_ledger_and_retires_its_one_candidate(self):
        from audio_jobs import AudioJobs
        from working_lifecycle import WorkingLifecycle
        from encoding_policy import AUTOMATIC_PROFILE
        from source_cleanup import packed
        raw=pipeline.probe(self.source,self.root,self.stop);duration,profile=pipeline.audio_info(raw)
        audio=next(stream for stream in raw['streams'] if stream.get('codec_type')=='audio')
        encoding=pipeline.choose_automatic_encoding([(*profile,audio.get('bit_rate'),audio.get('channel_layout'))],single_m4b=True)
        facts=self.source.stat();source_sha=pipeline.digest(self.source);cover_sha=pipeline.digest(self.cover)
        job_id=str(uuid.uuid4());attempt_id=str(uuid.uuid4())
        manifest={'job_id':job_id,'candidate_id':str(uuid.uuid4()),'candidate_revision':1,
          'root':str(self.root),'destination':str(self.root/'final.m4b'),'profile':AUTOMATIC_PROFILE,'evidence':[],
          'sources':[{'path':str(self.source),'size':facts.st_size,'modified':str(facts.st_mtime_ns),'sha256':source_sha,
                      'fingerprint':{'size':facts.st_size,'modified':str(facts.st_mtime_ns)}}],
          'metadata':{'title':'Private ledger fixture','canonical_author':'Fixture Author'},
          'cover':{'path':str(self.cover),'sha256':cover_sha},
          'source_chapters':pipeline.source_chapters(self.source,self.root,self.stop,duration)}
        database=self.root/'ledger.sqlite3';stage_root=self.root/'cache'/'audio-staging';stage_root.mkdir(parents=True)
        queue=AudioJobs(database,None,lambda _:True,lambda _:True)
        try:
            queue.enqueue(manifest);queue._update(job_id,state='running',attempt_id=attempt_id,journal=json.dumps({'attempt_id':attempt_id,'history':[]}))
            life=WorkingLifecycle(database,stage_root);life.begin(dict(manifest,attempt_id=attempt_id))
            job=stage_root/job_id;job.mkdir();(job/'ownership.json').write_text(packed({'job_id':job_id,'manifest':manifest}),encoding='utf8')
            stage=job/attempt_id;stage.mkdir()
            with pipeline.generated_artifacts(stage,life) as receipts:
                pipeline.copy_owned(self.source,stage/'source00000.m4b',source_sha,self.stop)
                pipeline.copy_owned(self.cover,stage/'cover.png',cover_sha,self.stop)
                output,validation=pipeline._encode_inputs(manifest,stage,['source00000.m4b'],[duration],stage/'cover.png',self.stop,lambda *_:None,encoding,['source00000.m4b'])
            self.assertEqual(output.name,'checked.m4b');self.assertIn('checked.m4b',receipts)
            self.assertEqual(receipts['checked.m4b']['sha256'],validation['sha256'])
            self.assertFalse((stage/'compatible.m4b').exists())
            self.assertEqual(life._attempt(job_id,attempt_id)['producer'],'closed')
            # No publication occurred: close this private fixture as a failed
            # attempt, exercising genuine cleanup with original survival proof.
            queue._update(job_id,state='needs attention',reason='Private fixture completed; no publication intended')
            life.terminal(job_id,attempt_id)
            self.assertEqual(list(stage.iterdir()),[])
            self.assertEqual(life._attempt(job_id,attempt_id)['state'],'retired')
            self.assertEqual(pipeline.digest(self.source),source_sha);self.assertEqual(pipeline.digest(self.cover),cover_sha)
        finally:queue.close()


if __name__=='__main__':unittest.main()

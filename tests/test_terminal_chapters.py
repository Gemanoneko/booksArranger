"""Bounded final-end correction: deterministic rejection cases plus opt-in private native fixtures.

Set BOOKS_TERMINAL_FIXTURE_ROOT to an owned test directory to run the native cases.
No live library, app, UI, network, or profile is opened. Native children use run_owned.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

import audio_pipeline as pipeline


def chapter(start,end,title='Final',identity=7):
    return {'id':identity,'start_time':str(start),'end_time':str(end),'tags':{'title':title}}


class TerminalChapterTests(unittest.TestCase):
    def setUp(self):
        self.path=Path('C:/private-fixture/part.m4b');self.stop=threading.Event()
        self.chapters=[chapter(0,2,'First',3),chapter(2,999999,'Last',7)]
        self.raw={'chapters':self.chapters,'format':{'duration':'4'},'streams':[
          {'codec_type':'audio','codec_name':'aac','sample_rate':'44100','channels':1,'duration':'4','channel_layout':'mono'}]}
        self.facts={'size':4,'modified':123,'dev':1,'ino':2}
        self.data=b'abcd';owner=self
        class Lease:
            def __init__(self,path):self.path=path
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def facts(self):return dict(owner.facts)
            def refresh(self):return dict(owner.facts)
            def chunks(self):yield owner.data
            def read_at(self,at,count):return owner.data[at:at+count]
        self.plan=SimpleNamespace(tracks=({'handler':b'soun','samples':173,'sha256':'track-proof'},))
        self.packets={'relative_packet_timing':{'packet_count':173,'sha256':'packet-proof'}}
        self.pcm={'sample_count':176400,'sample_rate':44100,'channels':1,'sha256':'pcm-proof'}
        self.probe=self.enterContext(patch.object(pipeline,'probe',return_value=self.raw))
        self.enterContext(patch.object(pipeline,'VerifiedFile',Lease))
        def checked_plan(size,read_at,tags):
            # Retain the real planner's required metadata contract in the fake
            # container. Empty tags must fail here as they do on real media.
            pipeline.m4b_preservation.approved_items(tags,None)
            return self.plan
        self.container=self.enterContext(patch.object(pipeline.m4b_preservation,'plan',side_effect=checked_plan))
        self.packet_probe=self.enterContext(patch.object(pipeline,'copied_audio_evidence',return_value=self.packets))
        self.decoder=self.enterContext(patch.object(pipeline,'native_pcm_evidence',return_value=self.pcm))

    def check(self,**kwargs):
        return pipeline.verified_source_chapters(self.path,self.path.parent,self.stop,4,**kwargs)

    def refusal(self,predicate,**kwargs):
        with self.assertRaises(pipeline.ChapterValidationError) as caught:self.check(**kwargs)
        self.assertEqual(caught.exception.chapter_diagnostic['predicate'],predicate)
        return caught.exception.chapter_diagnostic

    def test_strict_default_never_decodes_or_corrects(self):
        with self.assertRaises(pipeline.ChapterValidationError) as caught:
            pipeline.source_chapters(self.path,self.path.parent,self.stop,4)
        diagnostic=caught.exception.chapter_diagnostic
        self.assertEqual(diagnostic['predicate'],'end_exceeds_audio')
        self.assertEqual((diagnostic['file'],diagnostic['chapter_id'],diagnostic['chapter_title']),('part.m4b',7,'Last'))
        self.assertEqual((diagnostic['start'],diagnostic['end'],diagnostic['duration']),(2,999999,4))
        self.decoder.assert_not_called()

    def test_correction_keeps_every_title_start_order_and_original_probe(self):
        before=copy.deepcopy(self.raw);events=[]
        result=self.check(on_check=events.append)
        self.assertEqual(result['chapters'],[{'start':0,'end':2000,'title':'First'},{'start':2000,'end':4000,'title':'Last'}])
        self.assertEqual(self.raw,before)
        receipt=result['terminal_end_correction']
        self.assertEqual(receipt['source_sha256'],hashlib.sha256(self.data).hexdigest())
        self.assertEqual((receipt['original_end'],receipt['corrected_end']),(999999,4))
        self.assertEqual(receipt['native_pcm_evidence'],self.pcm)
        self.assertEqual(events[0]['reason'],'terminal_chapter_end')
        self.assertEqual(set(self.container.call_args.args[2]),{'title'})
        self.assertEqual(self.container.call_args.kwargs,{})  # No repair permissions.
        self.packet_probe.assert_called_once_with(self.path,self.path.parent,self.stop,4,source_relative=True)
        json.dumps(result,allow_nan=False)

    def test_small_offset_remains_valid_without_correction(self):
        self.chapters[-1]['end_time']='4.0481'
        result=self.check()
        self.assertIsNone(result['terminal_end_correction'])
        self.assertEqual(result['chapters'][-1]['end'],4048)
        self.container.assert_not_called();self.decoder.assert_not_called()

    def test_invalid_earlier_boundaries_never_enter_proof(self):
        cases=[([chapter(-1,2),chapter(2,999999)],'start_before_audio'),
          ([chapter(0,0),chapter(2,999999)],'end_not_after_start'),
          ([chapter(0,3,'Previous'),chapter(2,999999)],'overlap'),
          ([chapter(0,999999),chapter(2,999999)],'end_exceeds_audio'),
          ([chapter(0,2),chapter(4,999999)],'start_beyond_audio'),
          ([chapter(0,2),chapter('nan',999999)],'unreadable_time'),
          ([chapter(0,2),chapter(2,'inf')],'unreadable_time')]
        for chapters,predicate in cases:
            with self.subTest(predicate=predicate):
                self.raw['chapters']=chapters
                self.refusal(predicate)
        self.container.assert_not_called();self.decoder.assert_not_called()

    def test_missing_time_and_invalid_title_are_specific(self):
        del self.chapters[-1]['end_time']
        self.refusal('unreadable_time')
        self.chapters[-1]['end_time']='999999';self.chapters[-1]['tags']['title']=None
        self.refusal('invalid_title')
        self.decoder.assert_not_called()

    def test_title_absence_retains_id_and_nonfinite_diagnostics_serialize(self):
        self.chapters[-1]['tags']={};self.chapters[-1]['end_time']='nan'
        diagnostic=self.refusal('unreadable_time')
        self.assertEqual(diagnostic['chapter_id'],7)
        self.assertEqual(diagnostic['chapter_title'],'')
        self.assertEqual(diagnostic['end'],'nan')
        json.dumps(diagnostic,allow_nan=False)

    def test_overlap_identifies_previous_chapter(self):
        self.chapters[0]['end_time']='3'
        diagnostic=self.refusal('overlap')
        self.assertEqual((diagnostic['previous_chapter_title'],diagnostic['previous_end']),('First',3))

    def test_missing_audio_packets_do_not_authorize_correction(self):
        self.packets['relative_packet_timing']['packet_count']=172
        diagnostic=self.refusal('complete_audio_unverified')
        self.assertIn('complete intact source sample table',diagnostic['reason'])
        self.decoder.assert_not_called()

    def test_container_refusal_does_not_request_repair_or_decode(self):
        self.container.side_effect=pipeline.m4b_preservation.Refused('Top-level extent invalid')
        diagnostic=self.refusal('complete_audio_unverified')
        self.assertEqual(diagnostic['reason'],'Top-level extent invalid')
        self.decoder.assert_not_called()

    def test_full_decoder_failure_preserves_specific_reason(self):
        self.decoder.side_effect=pipeline.ValidationError('decoder rejected packet 91')
        diagnostic=self.refusal('complete_audio_unverified')
        self.assertEqual(diagnostic['reason'],'decoder rejected packet 91')
        self.assertEqual(diagnostic['chapter_title'],'Last')

    def test_missing_or_disagreeing_complete_duration_refuses(self):
        self.pcm['sample_count']=44100
        self.refusal('complete_audio_unverified')
        self.pcm['sample_count']=176400;del self.raw['streams'][0]['duration']
        self.refusal('complete_audio_unverified')

    def test_fresh_native_endpoint_is_used_and_final_start_must_fit_it(self):
        self.pcm['sample_count']=174195  # 3.95 s; retain the real decoded end.
        self.assertEqual(self.check()['chapters'][-1]['end'],3950)
        self.chapters[-1]['start_time']='3.96'
        self.refusal('start_beyond_audio')

    def test_revision_binding_precedes_any_native_proof(self):
        source={'size':4,'modified':'123','sha256':hashlib.sha256(self.data).hexdigest()}
        for key,value in [('size',5),('modified','124'),('sha256','0'*64)]:
            with self.subTest(key=key):self.refusal('source_changed',source=source|{key:value})
        self.container.assert_not_called();self.decoder.assert_not_called()
        self.assertIsNotNone(self.check(source=source)['terminal_end_correction'])

    def test_same_size_same_mtime_byte_change_during_decode_is_rejected(self):
        def decode(*args,**kwargs):self.data=b'abce';return self.pcm
        self.decoder.side_effect=decode
        self.refusal('source_changed')

    def test_a_receipt_is_not_reused_as_permission_for_later_bytes(self):
        first=self.check()
        self.data=b'new!'
        second=self.check()
        self.assertNotEqual(first['terminal_end_correction']['source_sha256'],second['terminal_end_correction']['source_sha256'])
        self.assertEqual(self.decoder.call_count,2)

    def test_timeout_and_pause_remain_transient_and_do_not_claim_source_damage(self):
        self.decoder.side_effect=pipeline.MediaTimeout('timed out')
        with self.assertRaises(pipeline.MediaTimeout):self.check()
        self.decoder.reset_mock();self.stop.set()
        with self.assertRaises(pipeline.Paused):self.check()
        self.decoder.assert_not_called()

    def test_long_titles_and_three_digit_hours_are_not_truncated(self):
        self.chapters[-1]['tags']['title']='Длинная глава '*100
        self.chapters[-1]['end_time']=str(123*3600)
        with self.assertRaises(pipeline.ChapterValidationError) as caught:
            pipeline.source_chapters(self.path,self.path.parent,self.stop,4)
        self.assertIn(self.chapters[-1]['tags']['title'],str(caught.exception))
        self.assertEqual(caught.exception.chapter_diagnostic['end'],442800)


@unittest.skipUnless(os.environ.get('BOOKS_TERMINAL_FIXTURE_ROOT'),'Requires an explicitly owned native fixture directory')
class NativeTerminalChapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['BOOKS_TERMINAL_FIXTURE_ROOT'])/('native-'+uuid.uuid4().hex)
        cls.root.mkdir(parents=True);cls.stop=threading.Event()
        cls.source=cls.root/'terminal.m4b';metadata=cls.root/'chapters.txt'
        metadata.write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=750\ntitle=First\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=750\nEND=2000\ntitle=Last\n',encoding='utf-8')
        pipeline.run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-n',
          '-f','lavfi','-i','sine=frequency=997:sample_rate=44100:duration=2','-f','ffmetadata','-i',str(metadata),
          '-map','0:a:0','-map_chapters','1','-c:a','aac','-b:a','64000','-movflags','+faststart+disable_chpl',str(cls.source)],cls.root,cls.stop,30)
        # Change only this private fixture's final text-sample duration and matching
        # text media/presentation clocks. FFmpeg's generated edit list otherwise caps
        # the chapter at two seconds despite an enlarged stts/mdhd. Audio bytes,
        # movie clock, chapter starts/titles and offsets stay exact.
        before=cls.source.read_bytes();changed=bytearray(before)
        movie=next(b for b in pipeline.m4b_preservation.boxes(before) if b.kind==b'moov')
        movie_parts=pipeline.m4b_preservation.boxes(movie.payload)
        mvhd=next(b for b in movie_parts if b.kind==b'mvhd')
        if mvhd.payload[0]!=0:raise AssertionError('Expected generated version-0 movie clock')
        movie_scale=int.from_bytes(mvhd.payload[12:16],'big')
        for track in movie_parts:
            if track.kind!=b'trak':continue
            track_parts=pipeline.m4b_preservation.boxes(track.payload)
            media=next(b for b in track_parts if b.kind==b'mdia')
            media_parts=pipeline.m4b_preservation.boxes(media.payload)
            handler=next(b for b in media_parts if b.kind==b'hdlr')
            if handler.payload[8:12]!=b'text':continue
            mdhd=next(b for b in media_parts if b.kind==b'mdhd')
            minf=next(b for b in media_parts if b.kind==b'minf')
            stbl=next(b for b in pipeline.m4b_preservation.boxes(minf.payload) if b.kind==b'stbl')
            stts=next(b for b in pipeline.m4b_preservation.boxes(stbl.payload) if b.kind==b'stts')
            media_base=movie.start+movie.header+track.start+track.header+media.start+media.header
            timing_base=media_base+minf.start+minf.header+stbl.start+stbl.header+stts.start+stts.header
            rows=int.from_bytes(stts.payload[4:8],'big')
            last_count=int.from_bytes(stts.payload[-8:-4],'big')
            if rows<1 or last_count!=1:raise AssertionError('Fixture requires a separate final chapter timing run')
            old_delta=int.from_bytes(stts.payload[-4:],'big');new_delta=1_800_000_000
            struct.pack_into('>I',changed,timing_base+len(stts.payload)-4,new_delta)
            if mdhd.payload[0]!=0:raise AssertionError('Expected generated version-0 text media clock')
            old_duration=int.from_bytes(mdhd.payload[16:20],'big')
            text_duration=old_duration+new_delta-old_delta
            struct.pack_into('>I',changed,media_base+mdhd.start+mdhd.header+16,text_duration)
            text_scale=int.from_bytes(mdhd.payload[12:16],'big')
            if not text_scale or text_duration*movie_scale%text_scale:raise AssertionError('Fixture requires exact text/movie clock conversion')
            presentation_duration=text_duration*movie_scale//text_scale
            track_base=movie.start+movie.header+track.start+track.header
            tkhd=next(b for b in track_parts if b.kind==b'tkhd')
            edts=next(b for b in track_parts if b.kind==b'edts')
            elst=next(b for b in pipeline.m4b_preservation.boxes(edts.payload) if b.kind==b'elst')
            if tkhd.payload[0]!=0 or elst.payload[:8]!=bytes(4)+struct.pack('>I',1) or int.from_bytes(elst.payload[12:16],'big')!=0:
                raise AssertionError('Fixture requires one version-0 text edit beginning at zero')
            struct.pack_into('>I',changed,track_base+tkhd.start+tkhd.header+20,presentation_duration)
            struct.pack_into('>I',changed,track_base+edts.start+edts.header+elst.start+elst.header+8,presentation_duration)
            break
        else:raise AssertionError('Generated fixture has no QuickTime text chapter track')
        cls.source.write_bytes(changed)
        cls.raw=pipeline.probe(cls.source,cls.root,cls.stop)
        cls.duration=float(next(s for s in cls.raw['streams'] if s['codec_type']=='audio')['duration'])
        if float(cls.raw['chapters'][-1]['end_time'])<=cls.duration+.25:
            raise AssertionError('Generated terminal endpoint is still capped; the correction branch would not be tested')
        cls.cover=cls.root/'cover.png'
        pipeline.run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-nostdin','-n','-f','lavfi','-i',
          'color=c=blue:s=32x32:d=0.04','-frames:v','1','-threads','1',str(cls.cover)],cls.root,cls.stop,30)

    def test_real_full_audio_proof_preserves_source_bytes_and_chapter_identity(self):
        before=pipeline.digest(self.source);events=[]
        with self.assertRaises(pipeline.ChapterValidationError):
            pipeline.source_chapters(self.source,self.root,self.stop,self.duration)
        result=pipeline.verified_source_chapters(self.source,self.root,self.stop,self.duration,
            source={'sha256':before,**pipeline.fingerprint(self.source)},on_check=events.append)
        self.assertEqual(pipeline.digest(self.source),before)
        self.assertEqual([c['title'] for c in result['chapters']],['First','Last'])
        self.assertEqual([c['start'] for c in result['chapters']],[0,750])
        self.assertGreater(result['terminal_end_correction']['original_end'],100000)
        self.assertEqual(result['chapters'][-1]['end'],round(result['terminal_end_correction']['decoded_duration']*1000))
        self.assertEqual(len(events),1)

    def test_real_truncated_container_does_not_authorize_correction(self):
        damaged=self.root/'missing-tail.m4b';damaged.write_bytes(self.source.read_bytes()[:-2])
        before=pipeline.digest(damaged)
        with self.assertRaises(pipeline.ValidationError):
            pipeline.verified_source_chapters(damaged,self.root,self.stop,self.duration)
        self.assertEqual(pipeline.digest(damaged),before)

    def test_real_join_reproves_parts_and_validates_output_chapters(self):
        from encoding_policy import AUTOMATIC_PROFILE,freeze_automatic_policy
        other=self.root/'second.m4b';shutil.copyfile(self.source,other)
        sources=[{'path':str(p),'sha256':pipeline.digest(p),**pipeline.fingerprint(p),'metadata':{'tags':{}}} for p in (self.source,other)]
        parts=[{'name':str(i),'chapters':pipeline.verified_source_chapters(item['path'],self.root,self.stop,self.duration,source=item)['chapters']}
          for i,item in enumerate(sources)]
        manifest={'job_id':str(uuid.uuid4()),'candidate_id':str(uuid.uuid4()),'candidate_revision':1,
          'root':str(self.root),'destination':str(self.root/'final.m4b'),'profile':AUTOMATIC_PROFILE,
          'encoding_policy':freeze_automatic_policy(sources),'sources':sources,
          'cover':{'path':str(self.cover),'sha256':pipeline.digest(self.cover)},'comments':'','chapters':[],
          'part_chapters':parts,'metadata':{'title':'Private joined book','canonical_author':'Fixture Author'}}
        output,validation=pipeline.create_private(manifest,self.root/'stage',self.stop)
        self.assertEqual([c['title'] for c in validation['chapters']],['First','Last','First','Last'])
        self.assertEqual(len(validation['terminal_end_corrections']),2)
        self.assertEqual([c['source_sha256'] for c in validation['terminal_end_corrections']],[s['sha256'] for s in sources])
        self.assertEqual([pipeline.digest(s['path']) for s in sources],[s['sha256'] for s in sources])
        self.assertEqual(pipeline.source_chapters(output,self.root,self.stop,validation['decoded_duration']),validation['chapters'])


if __name__=='__main__':unittest.main()

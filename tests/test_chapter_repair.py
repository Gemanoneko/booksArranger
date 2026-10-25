import json
import threading
import subprocess,shutil,uuid
from pathlib import Path
from unittest.mock import patch
from test_merge_service import MergeTests
from audio_pipeline import digest
from chapter_repair import restore,recover
from scan_wait import finish_scan

class Repair(MergeTests):
    def test_stream_copy_preserves_full_presentation_and_collision(self):
        # Different beginning/end tones make presentation preservation concrete.
        subprocess.run([shutil.which('ffmpeg'),'-v','error','-nostdin','-y','-f','lavfi','-i','sine=frequency=880:duration=0.3','-ar','44100','-ac','1','-c:a','libmp3lame','-b:a','128k',str(self.sources[1])],check=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.hashes=[digest(p) for p in self.sources]
        self.inv.launch('Audiobooks');finish_scan(self.inv)
        row=self.ready()
        # A chapterless original is intentionally created, then corrected separately.
        row=self.service.reviews.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,False,evidence_note='Verified fixture source files')
        # This repair fixture specifically requires original source tracks for
        # exact navigation evidence. Conversion retirement is covered elsewhere.
        build=self.service.reviews.build_manifest
        def keep_fixture_sources(*args,**kwargs):
            manifest=build(*args,**kwargs);manifest['cleanup_policy']['enabled']=False;return manifest
        with patch.object(self.service.reviews,'build_manifest',side_effect=keep_fixture_sources):
            self.service.create('Audiobooks',row['id'],row['revision']);status=self.wait();self.assertEqual(status['completed'],1,status)
        parent=status['jobs'][0];manifest=parent['manifest'];validation=parent['output']['validation']
        self.assertEqual(validation['chapters'],[]);self.assertEqual(len(validation['source_durations']),2)
        boundary={'tracks':[{'source_path':s['path'],'sha256':s['sha256'],'pcm_frames':round(d*44100),'pcm_rate':44100,'title':'Вступление \\ =;#' if i==0 else 'Track 02'} for i,(s,d) in enumerate(zip(manifest['sources'],validation['source_durations']))]}
        self.assertEqual(boundary['tracks'][0]['pcm_frames'],13230)
        original=digest(parent['output']['final_path'])
        result=restore(parent,boundary,self.base/'repair',threading.Event(),lambda:True)
        self.assertEqual(len(result['validation']['chapters']),2)
        self.assertEqual(digest(parent['output']['final_path']),original)
        self.assertTrue(Path(result['output']).name.endswith(' - Chapters v2.m4b'))
        self.assertEqual(json.loads(Path(result['journal']).read_text().splitlines()[0])['state'],'intent')
        self.assertTrue(recover(result['journal'],self.base/'repair',threading.Event(),lambda:True)['recovered_from_owned_intent'])
        # The prior v0.4.2 suffix remains recognizable only through its owned intent.
        old_output=Path(parent['output']['final_path']).with_name(Path(parent['output']['final_path']).stem+' - Chapters.m4b')
        shutil.copy2(result['output'],old_output)
        old_id=str(uuid.uuid4());old_dir=self.base/'repair'/old_id;old_dir.mkdir()
        events=[json.loads(line) for line in Path(result['journal']).read_text(encoding='utf-8').splitlines()]
        for event in events:
            event['job_id']=old_id
            if 'destination' in event['data']:event['data']['destination']=str(old_output)
        old_journal=old_dir/'corrected-artifact.jsonl';old_journal.write_text(''.join(json.dumps(e)+'\n' for e in events),encoding='utf-8')
        self.assertEqual(recover(old_journal,self.base/'repair',threading.Event(),lambda:True)['output'],str(old_output))
        with self.assertRaises(FileExistsError):restore(parent,boundary,self.base/'repair',threading.Event(),lambda:True)
        self.assertEqual([digest(p) for p in self.sources],self.hashes)

    def test_api_default_is_not_a_saved_choice(self):
        row=self.service.reviews.page()['rows'][0]
        self.assertTrue(row['creation']['chapters_default'])
        self.assertFalse(row['review_context']['chapters_choice_saved'])
        row=self.ready()
        row=self.service.reviews.tracks('Audiobooks',row['id'],row['revision'],row['track_order'],row['included'],True,True,False,evidence_note='Source navigation intentionally unchecked')
        self.assertTrue(row['review_context']['chapters_choice_saved'])
        self.assertFalse(row['review_context']['chapters'])
        self.assertEqual(self.service.reviews.build_manifest('Audiobooks',row['id'],row['revision'])['chapters'],[])

if __name__=='__main__':
    import unittest
    unittest.main()

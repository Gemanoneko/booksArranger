"""Ruling64 named anthology volumes: grouping is membership, never a guessed playback order."""
import copy,json,sqlite3,threading,unittest
from pathlib import Path
from types import SimpleNamespace
import groups,local_identity,anthology_volumes,chapter_plan,manual_metadata
from public_research import PublicResearch
from source_identity import source_gate

ROOT=str(Path('X:/private-fixture'))
def row(volume,author,title,track=None,family='Калейдоскоп'):
    path=str(Path(ROOT)/(family+' '+str(volume))/(author+'-'+title+'.mp3'))
    tags={'album':family+' '+str(volume),'artist':author,'title':title}
    if track is not None:tags['track']=str(track)
    metadata={'title':tags['album'],'author':author,'artist':author,'tags':tags,'track_title':title,'probe':{'format':{'duration':'1'}}}
    return {'root':ROOT,'path':path,'kind':'audiobook','size':10,'modified':10,'metadata':json.dumps(metadata),'error':'','missing':0}
def stories(volume=4,tracks=False,family='Калейдоскоп'):
    return [row(volume,'Виктор Глебов','Первый рассказ',1 if tracks else None,family),row(volume,'Юрий Молчан','Второй рассказ',2 if tracks else None,family)]
def work(group):
    return {'policy_version':'standing-17-v1','identity_basis':'local_agreement','identity_rule':local_identity.IDENTITY_VERSION,
            'titles':[group['title_clue']],'author_aliases':['Разные авторы'],'full_author_verified':True}

class AnthologyVolumeTests(unittest.TestCase):
    def test_named_mixed_authors_are_one_book_with_original_member_credits(self):
        built=groups.build(stories());self.assertEqual(len(built),1);group=next(iter(built.values()))
        self.assertEqual(group['anthology_volume']['number'],'4');self.assertEqual(len(group['members']),2)
        self.assertEqual({m['metadata']['tags']['artist'] for m in group['members']},{'Виктор Глебов','Юрий Молчан'})
        self.assertTrue(anthology_volumes.identity(group));self.assertNotIn('Mixed recordings in this group',source_gate(group,work(group)))
        self.assertIn('Playback order uncertain',source_gate(group,work(group)))
    def test_other_mixed_author_folders_remain_separate(self):
        built=groups.build(stories(family='Other anthology'));self.assertEqual(len(built),2)
        self.assertTrue(all(len(g['members'])==1 and not g.get('anthology_volume') for g in built.values()))
    def test_an_existing_whole_m4b_volume_is_classified_without_joining_or_replacing_its_chapters(self):
        file=stories()[0];file['path']=str(Path(ROOT)/'Калейдоскоп 4'/'whole-volume.m4b')
        group=next(iter(groups.build([file]).values()))
        self.assertEqual(len(group['members']),1);self.assertTrue(anthology_volumes.identity(group))
        self.assertNotIn('anthology_story',group['members'][0],'whole-file chapters remain under existing M4B preservation')
        local=local_identity.identify(group,ROOT);self.assertTrue(local['route']);self.assertEqual(local['series']['number'],'4')

    def test_numbered_volumes_remain_distinct(self):
        built=groups.build(stories(4)+stories(5));self.assertEqual(len(built),2)
        self.assertEqual({g['anthology_volume']['number'] for g in built.values()},{'4','5'})
    def test_numbered_source_tracks_can_prove_order_without_global_guard_relaxation(self):
        group=next(iter(groups.build(stories(tracks=True)).values()))
        self.assertEqual(source_gate(group,work(group)),[])
        group=dict(group,fingerprint='private-fixture-fingerprint')
        local=local_identity.identify(group,ROOT)
        self.assertTrue(local['accepted']);self.assertEqual(local['series'],{'name':'Калейдоскоп','number':'4','folder':True})
        result=PublicResearch(SimpleNamespace(database='unused-private.sqlite'),leads=[])._local_collection(group,local,{'sources':[],'evidence':[]})
        self.assertEqual((result['review']['anthology'],result['review']['series'],result['review']['number']),(True,'Калейдоскоп','4'))
    def test_story_chapter_labels_preserve_existing_credit_or_add_observed_author(self):
        group=next(iter(groups.build(stories()).values()));labels=chapter_plan.names(group['members'])
        self.assertEqual(set(labels),{'Виктор Глебов. Первый рассказ','Юрий Молчан. Второй рассказ'})
        member=group['members'][0];member['metadata']['track_title']='1. Виктор Глебов. Первый рассказ';member['metadata']['tags']['artist']='Виктор Глебов'
        self.assertEqual(chapter_plan.names([member]),['1. Виктор Глебов. Первый рассказ'])
        member['metadata']['track_title']='Первый рассказ (Читает Виктор Глебов)'
        self.assertEqual(chapter_plan.names([member]),['Виктор Глебов. Первый рассказ (Читает Виктор Глебов)'],'a reader credit at the end is not the author credit at the front')
    def test_one_protected_story_blocks_the_entire_new_volume_not_a_partial_join(self):
        files=stories();old=next(iter(groups._legacy_build([files[0]]).values()));old['scope']='legacy-reviewed-story'
        built=groups.build(files,protected={old['scope']:old})
        self.assertEqual(sum(len(g['members']) for g in built.values()),2)
        free=[g for scope,g in built.items() if scope!=old['scope']]
        self.assertEqual(len(free),1);self.assertTrue(free[0]['anthology_ownership_conflict']);self.assertNotIn('anthology_volume',free[0])
        self.assertIn('Collection source/component binding changed',source_gate(free[0],work(free[0])))
        frozen=groups.build(files[1:],blocked_members=[groups.member(files[0])]);self.assertTrue(next(iter(frozen.values()))['anthology_ownership_conflict'])
    def test_binding_rejects_subset_changed_tags_and_forged_marker(self):
        group=next(iter(groups.build(stories()).values()))
        for changed in (dict(group,members=group['members'][:1]),dict(group,anthology_volume=dict(group['anthology_volume'],number='5'))):
            self.assertIn('Collection source/component binding changed',source_gate(changed,work(changed)))
        bad=copy.deepcopy(group);bad['members'][0]['metadata']['tags']['album']='Other book'
        self.assertFalse(anthology_volumes.identity(bad));self.assertIn('Collection source/component binding changed',source_gate(bad,work(bad)))
    def test_protected_whole_volume_retains_its_complete_evidence(self):
        files=stories();first=groups.build(files);again=groups.build(files,protected=first)
        self.assertEqual(first,again,'reviewed/job-owned whole volume is not re-created or stripped of its binding')
    def test_any_job_owned_story_blocks_partial_volume_even_when_completed(self):
        for state,absent in (('pending',False),('completed',False),('completed',True)):
            with self.subTest(state=state,protected_source_absent=absent):
                db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
                try:
                    db.execute('CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,kind TEXT,metadata TEXT,error TEXT,missing INTEGER)')
                    groups.setup(db);files=stories();old={}
                    for i,file in enumerate(files):
                        db.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)',tuple(file[k] for k in ('root','path','size','modified','kind','metadata','error','missing')))
                        group=next(iter(groups._legacy_build([file]).values()));scope='legacy-'+str(i);group['scope']=scope;old[scope]=group
                    base={'retired':{},'archived':set(),'frozen':{},'protected':{}};groups._sync_write(db,ROOT,1,old,base)
                    owned=db.execute('SELECT id FROM book_groups WHERE scope=?',('legacy-0',)).fetchone()[0]
                    db.execute('CREATE TABLE audio_jobs(manifest TEXT,state TEXT)');db.execute('INSERT INTO audio_jobs VALUES(?,?)',(json.dumps({'candidate_id':owned}),state))
                    if absent:db.execute('DELETE FROM files WHERE path=?',(files[0]['path'],))  # completed story already retired/gone from ACTIVE catalog
                    inputs=groups._sync_inputs(db,ROOT);self.assertIn('legacy-0',inputs['protected'])
                    rebuilt=groups._sync_build(db,ROOT,inputs)
                    self.assertEqual(sum(len(g['members']) for g in rebuilt.values()),1 if absent else 2)
                    self.assertFalse(any(g.get('anthology_volume') for g in rebuilt.values()))
                    self.assertTrue(any(g.get('anthology_ownership_conflict') for g in rebuilt.values()))
                finally:db.close()

    def test_regroup_supersedes_old_unapproved_stories_without_copying_manual_evidence(self):
        db=sqlite3.connect(':memory:');self.addCleanup(db.close);db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,kind TEXT,metadata TEXT,error TEXT,missing INTEGER)')
        groups.setup(db);manual_metadata.initialize(db)
        files=stories();old={}
        for i,file in enumerate(files):
            group=next(iter(groups._legacy_build([file]).values()));scope='old-story-'+str(i);group['scope']=scope;old[scope]=group
        inputs={'retired':{},'archived':set(),'frozen':{},'protected':{}}
        groups._sync_write(db,ROOT,1,old,inputs);prior=db.execute('SELECT * FROM book_groups ORDER BY scope').fetchall()
        record=manual_metadata.capture(dict(prior[0]),{'title':'Prior individual story'},'');manual_metadata.append(db,record)
        built=groups.build(files);groups._sync_write(db,ROOT,2,built,inputs)
        current=dict(db.execute('SELECT * FROM book_groups WHERE superseded=0').fetchone())
        self.assertNotIn(current['id'],[r['id'] for r in prior]);self.assertEqual(current['approved'],0);self.assertEqual(current['review'],'')
        self.assertEqual(db.execute('SELECT count(*) FROM book_groups WHERE superseded=1').fetchone()[0],2)
        self.assertEqual(manual_metadata.records(db,current),[],'old individual manual identity never silently becomes the whole volume\'s')

# One real-media regression through the production automatic hold and explicit existing order review.
from test_approve_as_is import ApproveFixture,tone
class AnthologyVolumeMediaTests(ApproveFixture):
    def test_unnumbered_volume_waits_for_explicit_order_then_preserves_story_credits(self):
        from review_backend import member_key
        import test_set_release
        for author,title in [('Виктор Глебов','Первый рассказ'),('Юрий Молчан','Второй рассказ')]:
            tone(self.audio/'Калейдоскоп 4'/(author+'-'+title+'.mp3'),self.cover,album='Калейдоскоп 4',title=title,artist=author)
        rows=self.start();self.assertEqual(len(rows),1);row=rows[0]
        self.service.automatic.start();test_set_release.SetReleaseTests.finish_run(self)
        self.assertEqual(self.service.jobs.status()['jobs'],[],'no alphabetical automatic concatenation')
        current=self.service.reviews._row('Audiobooks',row['id']);held=self.service.automatic.candidate(current)
        self.assertEqual(self.service.needs_you()[current['id']]['group'],'order_unclear',ascii(held))
        self.assertEqual(len(current['members']),2)
        original=[m['path'] for m in current['members']];self.assertTrue(all(Path(p).exists() for p in original),'hold preserves both sources')
        ordered=list(reversed(current['members']));keys=[member_key(m['path']) for m in ordered]
        self.service.reviews.tracks('Audiobooks',current['id'],current['revision'],keys,keys,True,True,True)
        current=self.service.reviews._row('Audiobooks',row['id'])  # the existing track Save advances the row revision
        preview=self.service.approval_preview(current['id'],current['revision'])
        self.assertTrue(preview['path'],ascii(preview))
        self.service.approve_book(current['id'],current['revision'],path=preview['path'])
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'pending','Approve never resumes the queue')
        self.start_and_wait();job=self.service.jobs.status()['jobs'][0]
        self.assertEqual(job['state'],'completed',ascii(job))
        self.assertEqual(Path(job['output']['final_path']),self.sorted/preview['path'])
        self.assertEqual([s['path'] for s in job['manifest']['sources']],[m['path'] for m in ordered],'explicit reverse order is honored')
        chapters=job['manifest']['chapters'];labels=[c['title'] if isinstance(c,dict) else c for c in chapters]
        self.assertIn('Юрий Молчан',labels[0]);self.assertIn('Второй рассказ',labels[0]);self.assertIn('Виктор Глебов',labels[1]);self.assertIn('Первый рассказ',labels[1])
        self.assertEqual((job['manifest']['metadata']['anthology'],job['manifest']['metadata']['series'],job['manifest']['metadata']['number']),(True,'Калейдоскоп','4'))

if __name__=='__main__':unittest.main()

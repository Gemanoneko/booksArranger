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

def annual_stories(year=2025,numbered=False,reader='Илья Дементьев'):
    files=stories(year,family='Самая страшная книга')
    for i,file in enumerate(files,1):
        file['path']=str(Path(ROOT)/'Самая Страшная Книга'/('Сборник - Самая страшная книга '+str(year)+' ['+reader+']')/(('%02d.mp3'%i) if numbered else Path(file['path']).name))
    return files


def horror_stories(volume=1,author=None):
    files=stories(volume,family=anthology_volumes.STORY_FAMILY)
    for file in files:
        file['path']=str(Path(ROOT)/anthology_volumes.STORY_FOLDER/('Сборник' if volume==1 else 'Сборник '+str(volume))/Path(file['path']).name)
        metadata=json.loads(file['metadata']);metadata['tags'].pop('album');metadata['tags']['artist']=author if author is not None else '';metadata['artist']=metadata['author']=metadata['tags']['artist'];file['metadata']=json.dumps(metadata)
    return files

def work(group):
    return {'policy_version':'standing-17-v1','identity_basis':'local_agreement','identity_rule':local_identity.IDENTITY_VERSION,
            'titles':[group['title_clue']],'author_aliases':['Разные авторы'],'full_author_verified':True}

class AnthologyVolumeTests(unittest.TestCase):


    def test_confirmed_horror_four_blank_album_volumes_are_separate_complete_books(self):
        built=groups.build(sum((horror_stories(n) for n in range(1,5)),[]))
        self.assertEqual(len(built),4);self.assertEqual({g['anthology_volume']['number'] for g in built.values()},{'1','2','3','4'})
        destinations=[]
        for group in built.values():
            self.assertEqual(len(group['members']),2);self.assertTrue(anthology_volumes.identity(group));self.assertIn('Playback order uncertain',source_gate(group,work(group)))
            self.assertNotIn('Mixed recordings in this group',source_gate(group,work(group)))
            from metadata import propose
            group=dict(group,fingerprint='private-four-volumes');local=local_identity.identify(group,ROOT)
            result=PublicResearch(SimpleNamespace(database='unused-private.sqlite'),leads=[])._local_collection(group,local,{'sources':[],'evidence':[]})
            destination=propose(group['members'][0]['path'],ROOT,'audiobook',group['metadata'],dict(result['review'],organization_policy='books-hierarchy-v2'),automatic_facts=result['metadata_facts'])['path'];destinations.append(destination)
            number=group['anthology_volume']['number'];title=anthology_volumes.STORY_FAMILY+' '+number
            self.assertEqual((result['review']['title'],result['review']['series'],result['review']['number']),(title,anthology_volumes.STORY_FAMILY,number))
            self.assertEqual(Path(destination),Path(ROOT)/'Сборники'/anthology_volumes.STORY_FAMILY/(title+' - Разные авторы.m4b'))
        self.assertTrue(all(destinations));self.assertEqual(len(set(destinations)),4,'four anthology volumes never claim one destination')

    def test_concise_horror_filename_is_exact_family_only_and_keeps_explicit_title(self):
        from organization import plan
        review={'title':'Other cycle 2','series':'Other cycle','number':'2','author':'Разные авторы','anthology':True}
        self.assertEqual(Path(plan(ROOT,review)['path']).name,'Other cycle - 2 - Other cycle 2 - Разные авторы.m4b')
        review.update(title='My explicit anthology title',series=anthology_volumes.STORY_FAMILY)
        self.assertEqual(Path(plan(ROOT,review)['path']).name,anthology_volumes.STORY_FAMILY+' - 2 - My explicit anthology title - Разные авторы.m4b')

    def test_horror_family_requires_exact_parent_and_confirmed_volume_boundary(self):
        files=horror_stories(2)
        for file in files:file['path']=file['path'].replace(anthology_volumes.STORY_FOLDER,'Other collection')
        self.assertEqual(len(groups.build(files)),2)
        files=horror_stories(5);self.assertEqual(len(groups.build(files)),2,'unconfirmed child5 receives no named exception')
        files=horror_stories(2);meta=json.loads(files[0]['metadata']);meta['tags']['album']='Other book';files[0]['metadata']=json.dumps(meta)
        self.assertTrue(all(g.get('anthology_ownership_conflict') for g in groups.build(files).values()))
    def test_horror_uploader_is_not_writer_and_placeholder_titles_keep_actual_story_names(self):
        files=horror_stories(2,author='home2');meta=json.loads(files[0]['metadata']);meta['track_title']='Без имени 2';files[0]['metadata']=json.dumps(meta)
        group=next(iter(groups.build(files).values()));labels=chapter_plan.names(group['members'])
        self.assertTrue(all('home2' not in label for label in labels));self.assertIn(Path(files[0]['path']).stem,labels)
        self.assertEqual(group['members'][0]['metadata']['tags']['artist'],'home2','raw uploader evidence remains untouched')
        files=horror_stories(2,author='Виктор Глебов');group=next(iter(groups.build(files).values()))
        self.assertTrue(all(label.startswith('Виктор Глебов. ') for label in chapter_plan.names(group['members'])))
    def test_horror_owned_or_retired_story_blocks_entire_volume_with_other_volumes_unaffected(self):
        files=horror_stories();old=next(iter(groups._legacy_build([files[0]]).values()));old['scope']='existing-owned-story'
        for active,blocked in ((files,[]),(files[1:],[]),(files[1:],[groups.member(files[0])])):
            with self.subTest(active=len(active),frozen=bool(blocked)):
                built=groups.build(active+horror_stories(2),protected={old['scope']:old} if not blocked else {},blocked_members=blocked)
                named=[g for g in built.values() if g.get('anthology_volume')]
                self.assertEqual(len(named),1);self.assertEqual(named[0]['anthology_volume']['number'],'2')
                self.assertTrue(any(g.get('anthology_ownership_conflict') for g in built.values()))


    def test_horror_regroup_supersedes_fragment_ids_and_rejects_stale_candidate_lookup(self):
        from scanner import Inventory
        db=sqlite3.connect(':memory:');self.addCleanup(db.close);db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE files(root TEXT,path TEXT,size INTEGER,modified INTEGER,kind TEXT,metadata TEXT,error TEXT,missing INTEGER)');groups.setup(db)
        files=horror_stories(2);old={}
        for index,file in enumerate(files):
            group=next(iter(groups._legacy_build([file]).values()));group['scope']='fragment-'+str(index);old[group['scope']]=group
        inputs={'retired':{},'archived':set(),'frozen':{},'protected':{}};groups._sync_write(db,ROOT,1,old,inputs)
        prior=[r[0] for r in db.execute('SELECT id FROM book_groups')];groups._sync_write(db,ROOT,2,groups.build(files),inputs)
        for identity in prior:
            with self.assertRaisesRegex(ValueError,'Candidate no longer current'):Inventory._candidate_row(db,ROOT,identity)
        current=db.execute('SELECT * FROM book_groups WHERE superseded=0').fetchall();self.assertEqual(len(current),1)
        self.assertEqual(current[0]['approved'],0);self.assertNotIn(current[0]['id'],prior)
        self.assertEqual(set(m['path'] for m in json.loads(current[0]['evidence'])['members']),set(f['path'] for f in files))

    def test_annual_anthology_with_numbered_filenames_is_one_book_not_a_series_year(self):
        group=next(iter(groups.build(annual_stories(numbered=True)).values()))
        self.assertEqual(len(group['members']),2);self.assertTrue(anthology_volumes.identity(group))
        self.assertEqual(source_gate(group,work(group)),[],'existing clean filename numbering proves playback order')
        self.assertEqual(set(chapter_plan.names(group['members'])),{'Виктор Глебов. Первый рассказ','Юрий Молчан. Второй рассказ'})
        group=dict(group,fingerprint='annual-private-fingerprint');local=local_identity.identify(group,ROOT)
        result=PublicResearch(SimpleNamespace(database='unused-private.sqlite'),leads=[])._local_collection(group,local,{'sources':[],'evidence':[]})
        self.assertEqual(result['review']['title'],'Самая страшная книга 2025');self.assertTrue(result['review']['anthology'])
        self.assertEqual((result['review']['series'],result['review']['number']),('',''),'calendar year is not a guessed narrative series position')

    def test_confirmed_annual_collection_suffix_retains_one_book_context(self):
        files=annual_stories(2021)
        for file in files:file['path']=str(Path(ROOT)/'Самая Страшная Книга'/'Самая страшная книга 2021 (Сборник)'/Path(file['path']).name)
        group=next(iter(groups.build(files).values()));self.assertTrue(anthology_volumes.identity(group));self.assertEqual(len(group['members']),2)
        self.assertEqual(source_gate(group,work(group)),['Playback order uncertain'])

    def test_annual_membership_does_not_guess_an_unnumbered_order(self):
        group=next(iter(groups.build(annual_stories()).values()));self.assertEqual(len(group['members']),2)
        self.assertIn('Playback order uncertain',source_gate(group,work(group)))
    def test_annual_years_and_recording_folders_remain_separate(self):
        built=groups.build(annual_stories(2024)+annual_stories(2025)+annual_stories(2025,reader='Другой чтец'))
        self.assertEqual(len(built),3);self.assertEqual(sorted(len(g['members']) for g in built.values()),[2,2,2])
    def test_annual_name_alone_or_contradictory_album_cannot_grant_membership(self):
        files=annual_stories()
        wrong=copy.deepcopy(files)
        for file in wrong:file['path']=file['path'].replace('Самая Страшная Книга','Other shelf')
        self.assertEqual(len(groups.build(wrong)),2,'generic same-title mixed authors do not gain a named exception')
        bad=copy.deepcopy(files);metadata=json.loads(bad[0]['metadata']);metadata['tags']['album']='Самая страшная книга 2024';bad[0]['metadata']=json.dumps(metadata)
        built=groups.build(bad);self.assertFalse(any(g.get('anthology_volume') for g in built.values()))
        self.assertTrue(all(g.get('anthology_ownership_conflict') for g in built.values()),'known folder with contradictory membership stays held in full')
    def test_annual_protected_missing_story_reserves_entire_known_book(self):
        files=annual_stories();old=next(iter(groups._legacy_build([files[0]]).values()));old['scope']='old-completed-story'
        built=groups.build(files[1:],protected={old['scope']:old})
        self.assertFalse(any(g.get('anthology_volume') for g in built.values()))
        self.assertTrue(all(g.get('anthology_ownership_conflict') for g in built.values()))

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


    def test_numbered_annual_anthology_queues_until_start_and_keeps_story_credits(self):
        folder=self.audio/'Самая Страшная Книга'/'Сборник - Самая страшная книга 2025 [Илья Дементьев]'
        sources=[]
        for index,(author,title) in enumerate([('Виктор Глебов','Первый рассказ'),('Юрий Молчан','Второй рассказ')],1):
            sources.append(tone(folder/('%02d.mp3'%index),self.cover,album='Самая страшная книга 2025',title=title,artist=author))
        rows=self.start();self.assertEqual(len(rows),1);row=rows[0]
        preview=self.service.approval_preview(row['id'],row['revision']);self.assertTrue(preview['path'],ascii(preview))
        self.service.approve_book(row['id'],row['revision'],path=preview['path'])
        self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'pending');self.assertTrue(all(p.exists() for p in sources))
        self.start_and_wait();job=self.service.jobs.status()['jobs'][0]
        self.assertEqual(job['state'],'completed',ascii(job));self.assertEqual(Path(job['output']['final_path']),self.sorted/preview['path'])
        labels=[c['title'] if isinstance(c,dict) else c for c in job['manifest']['chapters']]
        self.assertEqual(labels,['Виктор Глебов. Первый рассказ','Юрий Молчан. Второй рассказ'])
        self.assertEqual(job['manifest']['metadata']['title'],'Самая страшная книга 2025');self.assertTrue(job['manifest']['metadata']['anthology'])
        self.assertEqual((job['manifest']['metadata']['series'],job['manifest']['metadata']['number']),('',''))


    def test_horror_blank_tags_require_explicit_order_then_convert_without_uploader_writer(self):
        # A short private destination leaves room for the real long anthology/volume names under the unchanged240 limit.
        self.sorted=self.base/'S';self.sorted.mkdir()
        from review_backend import member_key
        import test_set_release
        folder=self.audio/anthology_volumes.STORY_FOLDER/'Сборник 2';sources=[]
        for name,title in [('Первый рассказ','Без имени'),('Второй рассказ','Второй рассказ')]:
            sources.append(tone(folder/(name+'.mp3'),self.cover,title=title,artist='home2'))
        rows=self.start();self.assertEqual(len(rows),1);row=rows[0]
        self.service.automatic.start();test_set_release.SetReleaseTests.finish_run(self)
        self.assertEqual(self.service.jobs.status()['jobs'],[]);current=self.service.reviews._row('Audiobooks',row['id'])
        self.assertEqual(self.service.needs_you()[row['id']]['group'],'order_unclear')
        ordered=list(reversed(current['members']));keys=[member_key(m['path']) for m in ordered]
        self.service.reviews.tracks('Audiobooks',current['id'],current['revision'],keys,keys,True,True,True);current=self.service.reviews._row('Audiobooks',row['id'])
        preview=self.service.approval_preview(current['id'],current['revision']);self.assertTrue(preview['path'],ascii(preview))
        self.service.approve_book(current['id'],current['revision'],path=preview['path']);self.assertEqual(self.service.jobs.status()['jobs'][0]['state'],'pending');self.assertTrue(all(p.exists() for p in sources))
        self.start_and_wait();job=self.service.jobs.status()['jobs'][0];self.assertEqual(job['state'],'completed',ascii(job))
        labels=[c['title'] if isinstance(c,dict) else c for c in job['manifest']['chapters']]
        self.assertEqual(labels,[Path(m['path']).stem for m in ordered]);self.assertTrue(all('home2' not in label for label in labels))
        self.assertEqual(Path(job['output']['final_path']),self.sorted/preview['path']);self.assertTrue(job['manifest']['metadata']['anthology'])

if __name__=='__main__':unittest.main()

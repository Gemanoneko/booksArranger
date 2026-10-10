"""Private automatic public pilot fixtures; never read or write real libraries."""
import copy,json,threading,time,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import groups
from scanner import Inventory,connect
from source_identity import source_gate,clues,filename_identity
from public_research import PublicClient,PublicResearch,ResearchWait,allowed_url,parse_page,credited_pair,strict_json
from automatic_processing import AutomaticProcessing

AREA=Path(__file__).resolve().parents[1]/'scratch'/'automatic-processing-2026-10-10'/'test-fixtures';AREA.mkdir(parents=True,exist_ok=True)

def row(path,title,author='John Writer',track='1',album=None):
    metadata={'title':title,'artist':author,'tags':{'title':title,'artist':author,'album':title if album is None else album,'track':track},'probe':{'format':{'duration':'1'}}}
    return {'root':str(Path(path).parent),'path':str(path),'kind':'audiobook','size':10,'modified':10,'metadata':json.dumps(metadata),'error':'','missing':0}

WORK={'id':'fantlab:42','titles':['A Book','Книга'],'author_aliases':['John Writer','Джон Писатель'],'original_language':'en'}
def fixture_payload(language='en',cycles=None):
    return {'work_id':42,'work_name':'Книга','work_name_orig':'A Book','work_name_alts':[],
        'authors':[{'type':'autor','name':'Джон Писатель','name_orig':'John Writer'}],
        'lang_code':language,'work_type_name':'novel','parents':{'cycles':[] if cycles is None else cycles,'digest':[]},'work_root_saga':[],
        'image':'https://fantlab.ru/images/cover.jpg','translations':[]}

class AutoTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.base=Path(self.temp.name);self.db=self.base/'catalog.sqlite3';self.controllers=[]
    def tearDown(self):
        for auto in self.controllers:auto.close()
        self.temp.cleanup()
    def candidate(self,title='A Book',author='John Writer'):
        return next(iter(groups.build([row(self.base/(author+' – '+title+'.mp3'),title,author)]) .values()))
    def client(self,work=None,page=b'<p>John Writer. A Book</p>'):
        work=work or fixture_payload();calls=[]
        def fetch(url,*_):
            calls.append(url)
            if '/search-works?' in url:return json.dumps([{'work_id':42,'name':'A Book','rusname':'Книга','all_autor_name':'John Writer','all_autor_rusname':'Джон Писатель'}]).encode()
            if '/work/42/extended' in url:return json.dumps(work).encode()
            if 'duckduckgo.com' in url:return b'<a class="result__a" href="https://ast.ru/book/example/">Search snippet</a>'
            if 'ast.ru' in url:return page
            raise AssertionError('Unexpected public fixture URL '+url)
        client=PublicClient(self.db,fetch=fetch,clock=lambda:100000)
        return client,calls
    def test_root_standalone_works_split_and_all_three_clues_retained(self):
        rows=[row(self.base/'Кабир Максим – Классные рога, чувак! [НЕОСФЕРА].mp3','Классные рога, чувак!','Максим Кабир'),row(self.base/'Масахико Симада – Дельфин в пустыне -1991.mp3','Дельфин в пустыне','Масахико Симада')]
        built=groups.build(rows);self.assertEqual(len(built),2)
        self.assertEqual(sorted(len(g['members']) for g in built.values()),[1,1])
        self.assertEqual(filename_identity(rows[1]['path'])['title'],'Дельфин в пустыне')
        kinds={c['kind'] for g in built.values() for c in clues(g['members'][0],str(self.base.parent))}
        self.assertEqual(kinds,{'embedded','filename','folder'})
    def test_numbered_embedded_recording_preserves_chapters_and_exact_order(self):
        built=groups.build([row(self.base/'02.mp3','A Book',track='2/2'),row(self.base/'01.mp3','A Book',track='1/2')]);self.assertEqual(len(built),1)
        group=next(iter(built.values()));self.assertEqual([m['track'] for m in group['members']],[1,2]);self.assertEqual(source_gate(group,WORK),[])
    def test_unrelated_filename_work_without_album_also_splits(self):
        self.assertEqual(len(groups.build([row(self.base/'One Author – First Tale.mp3','First Tale','One Author',album=''),row(self.base/'Two Author – Second Tale.mp3','Second Tale','Two Author',album='')])),2)
    def test_missing_order_gap_and_filename_only_do_not_approve(self):
        for tracks in (('1','3'),('1','1'),('','')):
            group=next(iter(groups.build([row(self.base/'01.mp3','A Book',track=tracks[0]),row(self.base/'02.mp3','A Book',track=tracks[1])]).values()))
            self.assertIn('Playback order uncertain',source_gate(group,WORK))
        candidate=self.candidate();candidate['members'][0]['metadata']['tags']={}
        self.assertIn('Source membership uncertain',source_gate(candidate,WORK))
    def test_conflicting_source_title_or_format_held(self):
        candidate=self.candidate();candidate['members'][0]['metadata']['tags']['album']='Other work'
        self.assertIn('Sources disagree on the title or author',source_gate(candidate,WORK))
        candidate['members'][0]['path']=str(self.base/'file.flac')
        self.assertIn('Audio format needs an encoding decision',source_gate(candidate,WORK))
    def test_original_combined_credit_can_be_local_clue_without_guess(self):
        candidate=self.candidate();candidate['members'][0]['metadata']['tags']['album']='J.WriterA BOOK'
        self.assertEqual(source_gate(candidate,WORK),[])
    def test_approved_identity_revision_and_evidence_survive_grouping_resync(self):
        path=self.base/'01.mp3';metadata=row(path,'A Book',track='1')['metadata']
        with connect(self.db) as db:
            db.execute('INSERT INTO files(root,path,size,modified,kind,metadata) VALUES(?,?,?,?,?,?)',(str(self.base),str(path),10,10,'audiobook',metadata));groups.sync(db,str(self.base))
            before=dict(db.execute('SELECT * FROM book_groups').fetchone());db.execute("UPDATE book_groups SET approved=1,review='{}' WHERE id=?",(before['id'],))
            db.execute('UPDATE book_catalog_revision SET revision=revision+1');groups.sync(db,str(self.base));after=dict(db.execute('SELECT * FROM book_groups WHERE id=?',(before['id'],)).fetchone())
        self.assertEqual((before['id'],before['revision'],before['fingerprint']),(after['id'],after['revision'],after['fingerprint']));self.assertTrue(after['approved'])
    def test_old_unapproved_mixed_group_superseded_without_source_changes(self):
        rows=[row(self.base/'a.mp3','A Book'),row(self.base/'b.mp3','Other Book')]
        with connect(self.db) as db:
            groups.setup(db)
            for r in rows:db.execute('INSERT INTO files(root,path,size,modified,kind,metadata) VALUES(?,?,?,?,?,?)',(str(self.base),r['path'],10,10,'audiobook',r['metadata']))
            evidence=next(iter(groups._legacy_build(rows).values()));id=str(uuid.uuid4())
            db.execute('INSERT INTO book_groups(id,root,scope,revision,fingerprint,evidence) VALUES(?,?,?,?,?,?)',(id,str(self.base),evidence['scope'],1,'legacy',json.dumps(evidence)))
            groups.sync(db,str(self.base));self.assertEqual(groups.page(db,str(self.base))['total'],2)
            self.assertEqual(db.execute('SELECT superseded FROM book_groups WHERE id=?',(id,)).fetchone()[0],1);self.assertEqual(db.execute('SELECT count(*) FROM files').fetchone()[0],2)
    def test_public_match_needs_fetched_independent_credit_and_original_language(self):
        client,calls=self.client();result=PublicResearch(client).lookup(self.candidate(),str(self.base))
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['review']['title'],'A Book');self.assertEqual(result['review']['author'],'Writer John')
        self.assertTrue(any('ast.ru' in u for u in calls));self.assertTrue(any(s.get('verified_identity') for s in result['sources']))
        self.assertEqual(result['review']['narrator'],'');self.assertFalse(result['review']['anthology'])
    def test_search_snippet_and_distant_page_cooccurrence_are_not_evidence(self):
        client,_=self.client(page=b'<p>John Writer</p><p>Another writer. A Book</p>')
        result=PublicResearch(client).lookup(self.candidate(),str(self.base))
        self.assertIn('Author and work not independently verified',result['reasons'])
        self.assertIsNone(credited_pair(parse_page(b'<script>John WriterA Book</script>'),['A Book'],['John Writer']))
    def test_language_and_series_unknown_held_and_anthology_not_fiction_cycle(self):
        payload=fixture_payload();payload['lang_code']='';payload['parents']['cycles']=[{'id':8}]
        client,_=self.client(payload);result=PublicResearch(client).lookup(self.candidate(),str(self.base))
        self.assertIn('Original work language unverified',result['reasons']);self.assertIn('Series position uncertain',result['reasons'])
        payload=fixture_payload();payload['parents']['digest']=[{'name':'Collection'}]
        with connect(self.db) as db:db.execute('DELETE FROM public_research_cache')
        # Contained story is modeled separately and never retitled to its collection.
        result=PublicResearch(self.client(payload)[0]).lookup(self.candidate(),str(self.base));self.assertEqual(result['review']['title'],'A Book');self.assertTrue(result['work']['contained_story']);self.assertFalse(result['review']['anthology'])
    def test_public_cache_budget_safe_urls_and_sanitized_errors(self):
        client,calls=self.client();url='https://ast.ru/book/example/';a=client.read(url);b=client.read(url);self.assertEqual(a,b);self.assertEqual(len(calls),1)
        for bad in ('http://ast.ru/book/x','https://127.0.0.1/x','https://ast.ru@localhost/x','https://ast.ru:444/x','https://evil.example/x'):
            with self.assertRaises(ValueError):allowed_url(bad)
        other=PublicClient(self.base/'errors.sqlite',fetch=lambda *_:(_ for _ in ()).throw(OSError('secret=TOKEN')))
        with self.assertRaises(ResearchWait) as caught:other.read(url)
        self.assertNotIn('TOKEN',str(caught.exception));self.assertGreater(caught.exception.retry_at,time.time())
    def test_short_title_explicit_credit_and_narrative_boundaries(self):
        self.assertIsNotNone(credited_pair(parse_page(b'<p>Stephen King. It</p>'),['It'],['Stephen King']))
        self.assertIsNone(credited_pair(parse_page(b'<p>Stephen King visited another publisher.</p>'),['It'],['Stephen King']))
        self.assertIsNone(credited_pair(parse_page(b'<p>Stephen King wrote about It.</p>'),['It'],['Stephen King']))
    def test_single_track_and_missing_disc_denominators_hold(self):
        candidate=self.candidate();candidate['members'][0]['metadata']['tags']['track']='1/67'
        self.assertIn('Source membership uncertain',source_gate(candidate,WORK))
        candidate=next(iter(groups.build([row(self.base/'01.mp3','A Book',track='1'),row(self.base/'02.mp3','A Book',track='2')]).values()))
        for member in candidate['members']:member['metadata']['tags']['disc']='1/2'
        self.assertIn('Source membership uncertain',source_gate(candidate,WORK))
    def test_blocked_search_known_citation_still_requires_fetched_pair(self):
        client,_=self.client();old=client.discover;client.discover=lambda *args:(_ for _ in ()).throw(ResearchWait('free search','unavailable',time.time()+300))
        research=PublicResearch(client,leads=[{'work_id':'fantlab:42','urls':['https://ast.ru/book/example/']}])
        result=research.lookup(self.candidate(),str(self.base));self.assertEqual(result['reasons'],[],result)
        with connect(self.db) as db:db.execute("DELETE FROM public_research_cache WHERE url='https://ast.ru/book/example/'")
        original=client.fetch;client.fetch=lambda url,*args:b'<p>Different Author. A Book</p>' if 'ast.ru' in url else original(url,*args)
        result=research.lookup(self.candidate(),str(self.base));self.assertIn('Author and work not independently verified',result['reasons'])

    def test_wikipedia_fetched_revision_and_primary_references_are_leads_only(self):
        pages={'query':{'pages':[{'pageid':101,'ns':0,'title':'A Book','revisions':[{'revid':202}],'langlinks':[{'lang':'ru','title':'Книга'}],'extlinks':[{'url':'https://ast.ru/book/example/'},{'url':'https://localhost/private'}]}]}}
        client=PublicClient(self.db,fetch=lambda *_:json.dumps(pages).encode(),clock=lambda:100000)
        result=client.wikipedia('A Book John Writer',threading.Event(),{'remaining':2})
        self.assertEqual(result['leads'],['https://ast.ru/book/example/']);source=result['sources'][0]
        self.assertFalse(source['verified_identity']);self.assertEqual(source['revision_id'],202);self.assertEqual(source['language_links'],[{'language':'ru','title':'Книга'}])
        self.assertEqual(source['sha256'],__import__('hashlib').sha256(json.dumps(pages).encode()).hexdigest())
        # An encyclopedia result never replaces the independently fetched publisher credit.
        fixture,_=self.client(page=b'<p>Unrelated Writer. A Book</p>');fixture.wikipedia=lambda *_:result
        result=PublicResearch(fixture).lookup(self.candidate(),str(self.base))
        self.assertIn('Author and work not independently verified',result['reasons'])
    def test_typed_author_credit_accepts_publisher_name_order_without_distant_match(self):
        from public_research import author_variants
        names=author_variants(['Масахико Симада'])
        self.assertIsNotNone(credited_pair(parse_page('<p>Симада Масахико Дельфин в пустыне. Перевод Т. Соколовой-Делюсиной</p>'.encode()),['Дельфин в пустыне'],names))
        self.assertIsNone(credited_pair(parse_page('<p>Симада Масахико</p><p>Другой автор. Дельфин в пустыне</p>'.encode()),['Дельфин в пустыне'],names))
    def test_duplicate_and_nonfinite_public_evidence_refused(self):
        for raw in (b'{"work_id":42,"work_id":99}',b'{"confidence":NaN}',b'{"number":Infinity}'):
            with self.assertRaises(ValueError):strict_json(raw)

    def test_expired_raw_cache_removed_without_losing_compact_candidate_evidence(self):
        client,_=self.client();url='https://ast.ru/book/example/';client.read(url)
        with connect(self.db) as db:db.execute('UPDATE public_research_cache SET fetched=?',(100000-8*86400,))
        second=PublicClient(self.db,fetch=lambda *_:b'<p>fresh bytes</p>',clock=lambda:100000)
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT count(*) FROM public_research_cache').fetchone()[0],0)
        self.assertEqual(second.read(url),b'<p>fresh bytes</p>');self.assertEqual(second.receipt(url)['sha256'],__import__('hashlib').sha256(b'<p>fresh bytes</p>').hexdigest())

    def test_all_normalized_disc_subgroups_remain_visible_and_held(self):
        first=row(self.base/'CD1'/'01.mp3','A Book',track='1');second=row(self.base/'CD2'/'01.mp3','A-Book',track='1')
        built=groups.build([first,second]);self.assertEqual(len(built),2)
        self.assertEqual({m['path'] for g in built.values() for m in g['members']},{first['path'],second['path']})
        for group in built.values():self.assertIn('Source membership uncertain',source_gate(group,WORK))
        with connect(self.db) as db:
            for value in (first,second):db.execute('INSERT INTO files(root,path,size,modified,kind,metadata) VALUES(?,?,?,?,?,?)',(str(self.base),value['path'],10,10,'audiobook',value['metadata']))
            page=groups.page(db,str(self.base));self.assertEqual(page['total'],2)
            self.assertEqual(sum(len(g['members']) for g in page['rows']),2)
    def test_translator_or_conflicting_typed_author_never_approves(self):
        for page in (b'<p>A Book - John Writer, translator. Author: Other Writer.</p>',b'<p>Translator: John Writer. A Book</p>',b'<p>A Book - John Writer, reader.</p>'):
            self.assertIsNone(credited_pair(parse_page(page),['A Book'],['John Writer']))
        for value in ('A Book — John Writer — translator.','A Book — John Writer: narrator.','A Book — John Writer. Translator.'):
            self.assertIsNone(credited_pair(parse_page(('<p>'+value+'</p>').encode()),['A Book'],['John Writer']))
        self.assertIsNotNone(credited_pair(parse_page(b'<p>Author: John Writer. A Book</p>'),['A Book'],['John Writer']))
        client,_=self.client(page=b'<p>A Book - John Writer, translator. Author: Other Writer.</p>')
        self.assertIn('Author and work not independently verified',PublicResearch(client).lookup(self.candidate(),str(self.base))['reasons'])
    def test_waiting_source_keeps_saved_pending_and_explicit_start_retries(self):
        calls=[]
        def lookup(*_):
            calls.append(1)
            return {'reasons':['Book identity uncertain'],'sources':[],'wait':{'source':'Public fixture','reason':'Unavailable','retry_at':time.time()+300}} if len(calls)==1 else {'reasons':['Book identity uncertain'],'sources':[]}
        auto,merge,inv=self.fake_merge(lookup);auto.start();state=self.wait_auto(auto)
        self.assertEqual(state['state'],'Paused');self.assertEqual(state['research']['waiting'],1)
        saved=json.loads(auto._run_row()['checkpoint']);self.assertEqual(len(saved['pending']),1)
        with connect(self.db) as db:db.execute("UPDATE automatic_candidates SET retry_at=0 WHERE state='Waiting for source'")
        auto.start();state=self.wait_auto(auto);self.assertEqual(state['state'],'Completed');self.assertEqual(len(calls),2);self.assertEqual(state['research']['held'],1)
    def test_automatic_drain_waits_required_working_cleanup(self):
        auto,merge,inv=self.fake_merge();original=merge.state;merge.state=lambda:original()|{'cleanup_active':True}
        self.assertFalse(auto._idle_jobs());merge.state=lambda:original()|{'cleanup_active':False};self.assertTrue(auto._idle_jobs())

    def test_owned_resolver_result_timeout_and_stop_without_network(self):
        import public_research
        body="import json; print(json.dumps([[2,1,6,'',['8.8.8.8',443]]]))"
        with patch.object(public_research,'DNS_CODE',body):
            self.assertEqual(public_research._resolve('ast.ru',time.monotonic()+5)[0][4],('8.8.8.8',443))
        body='import time; time.sleep(5)'
        begin=time.monotonic()
        with patch.object(public_research,'DNS_CODE',body),self.assertRaises(TimeoutError):public_research._resolve('ast.ru',time.monotonic()+.2)
        self.assertLess(time.monotonic()-begin,2)
        stop=threading.Event();timer=threading.Timer(.2,stop.set);timer.start()
        try:
            with patch.object(public_research,'DNS_CODE',body),self.assertRaises(InterruptedError):public_research._resolve('ast.ru',time.monotonic()+5,stop)
        finally:timer.cancel();timer.join()

    def test_stale_automatic_stop_does_not_stop_unowned_scan(self):
        auto,merge,inv=self.fake_merge()
        with patch.object(inv,'stop') as scanner,patch.object(merge,'pause') as converter:
            self.assertEqual(auto.stop()['state'],'Idle');scanner.assert_not_called();converter.assert_not_called()
    def test_source_hash_honors_stop_between_read_chunks(self):
        from review_backend import source_hash
        path=self.base/'private-hash-fixture.bin';path.write_bytes(b'x'*(2*1024*1024));stop=threading.Event();real_open=open
        class Reader:
            def __init__(self):self.file=real_open(path,'rb')
            def __enter__(self):return self
            def __exit__(self,*_):self.file.close()
            def fileno(self):return self.file.fileno()
            def read(self,size):value=self.file.read(size);stop.set();return value
        with patch('builtins.open',lambda *args,**kwargs:Reader()),self.assertRaises(InterruptedError):source_hash(path,path.stat(),stop)
        self.assertEqual(path.stat().st_size,2*1024*1024)

    def test_public_cover_wait_saves_candidate_and_continues_other_books(self):
        auto,merge,inv=self.fake_merge(lambda row,*_:{'reasons':[],'work':WORK,'review':{},'sources':[]})
        second=self.base/'audio'/'John Writer – B Book.mp3';second.write_bytes(b'private second book fixture')
        inv.reader=lambda p,k,s:json.loads(row(p,filename_identity(p)['title'])['metadata'])
        calls=[]
        def admit(current,*_):
            calls.append(current['id'])
            if len(calls)==1:raise ResearchWait('Public cover fixture','Unavailable',time.time()+300)
            return current,'private-second-job'
        merge.approve_automatic.side_effect=admit;auto.start();state=self.wait_auto(auto)
        self.assertEqual(len(calls),2);self.assertEqual(state['state'],'Paused');self.assertEqual(state['research']['waiting'],1);self.assertEqual(state['research']['researching'],0)
        self.assertEqual(len(json.loads(auto._run_row()['checkpoint'])['pending']),1)

    def test_long_unicode_public_query_holds_one_candidate_and_continues(self):
        auto,merge,inv=self.fake_merge();audio=self.base/'audio'
        (audio/'John Writer – A Book.mp3').unlink()
        for name in ('A','Z'):
            directory=audio/name;directory.mkdir();(directory/'01.mp3').write_bytes(b'private input-boundary fixture')
        long_title='漢'*300
        inv.reader=lambda p,k,s:json.loads(row(p,long_title if Path(p).parent.name=='A' else 'B Book')['metadata'])
        calls=[]
        def fetch(url,*_):
            calls.append(url);raise AssertionError('Overlong URLs must be refused before fetching')
        client=PublicClient(self.db,fetch=fetch);research=PublicResearch(client,leads=[])
        auto.research.client=client
        auto.research.lookup=lambda current,root,stop,progress:research.lookup(current,root,stop,progress) if current['members'][0]['metadata']['tags']['album']==long_title else {'reasons':[],'work':WORK,'review':{},'sources':[]}
        auto.start();state=self.wait_auto(auto)
        self.assertEqual(state['state'],'Completed');self.assertEqual(state['research']['held'],1)
        merge.approve_automatic.assert_called_once();self.assertEqual(merge.approve_automatic.call_args.args[0]['members'][0]['metadata']['tags']['album'],'B Book')
        held=[auto.candidate(current) for current in inv.candidates('Audiobooks')['rows'] if current['members'][0]['metadata']['tags']['album']==long_title]
        self.assertEqual(len(held),1);self.assertEqual(held[0]['state'],'Held')
        self.assertEqual(held[0]['reasons'],['Public research input or evidence exceeds supported limits']);self.assertEqual(calls,[])

    def fake_merge(self,lookup=None):
        audio=self.base/'audio';audio.mkdir(exist_ok=True);path=audio/'John Writer – A Book.mp3';path.write_bytes(b'fixture only')
        inv=Inventory(self.db,{'Audiobooks':str(audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')},lambda p,k,s:json.loads(row(p,'A Book')['metadata']))
        state={'state':'Completed','queued':0};reviews=SimpleNamespace(_context=lambda row:{},_row=lambda lib,id,revision=None:inv.candidate(lib,id))
        merge=SimpleNamespace(inventory=inv,reviews=reviews,_no_scan=lambda:None,state=lambda:dict(state),pause=lambda:state.update(state='Paused'),resume=Mock(),candidate_status=lambda id:None)
        merge.approve_automatic=Mock(side_effect=lambda row,result,stop,client:(row,'fixture-job'))
        research=SimpleNamespace(client=Mock(),lookup=lookup or (lambda *args:{'reasons':['Book identity uncertain'],'sources':[]}))
        auto=AutomaticProcessing(merge,research);merge.automatic=auto;self.controllers.append(auto)
        return auto,merge,inv
    def wait_auto(self,auto):
        auto.thread.join(5);self.assertFalse(auto.thread.is_alive());return auto.status()
    def test_construction_and_inventory_only_never_approve(self):
        auto,merge,inv=self.fake_merge();self.assertEqual(auto.status()['state'],'Idle');merge.approve_automatic.assert_not_called();inv.launch('Audiobooks');inv.worker.join(5);merge.approve_automatic.assert_not_called();auto.close()
    def test_uncertain_work_held_and_pass_completes(self):
        auto,merge,inv=self.fake_merge();auto.start();status=self.wait_auto(auto)
        self.assertEqual(status['state'],'Completed');self.assertEqual(status['research']['held'],1);merge.approve_automatic.assert_not_called();auto.close()
    def test_full_confident_decision_reaches_private_admission(self):
        auto,merge,inv=self.fake_merge(lambda *_:{'reasons':[],'work':WORK,'review':{},'sources':[]});auto.start();self.wait_auto(auto);merge.approve_automatic.assert_called_once();auto.close()
    def test_stop_saves_pending_and_restart_never_starts_it(self):
        entered=threading.Event();release=threading.Event()
        def lookup(row,root,stop,progress):entered.set();release.wait(2);return {'reasons':[]}
        auto,merge,inv=self.fake_merge(lookup);auto.start();self.assertTrue(entered.wait(2));self.assertEqual(auto.stop()['state'],'Stopping');release.set();self.assertEqual(self.wait_auto(auto)['state'],'Paused');merge.approve_automatic.assert_not_called()
        second=AutomaticProcessing(merge,auto.research);self.assertEqual(second.status()['state'],'Paused');self.assertIsNone(second.thread);merge.resume.assert_not_called();auto.close();second.close()
    def test_unsaved_manual_draft_lease_blocks_only_candidate(self):
        auto,merge,inv=self.fake_merge();inv.launch('Audiobooks');inv.worker.join(5);candidate=inv.candidates('Audiobooks')['rows'][0]
        auto.draft(candidate['id'],candidate['revision'],True);self.assertTrue(auto.manual_draft(candidate));auto.start();self.wait_auto(auto)
        self.assertEqual(auto.candidate(inv.candidate('Audiobooks',candidate['id']))['reasons'],['Manual draft retained']);merge.approve_automatic.assert_not_called();auto.close()

if __name__=='__main__':unittest.main()

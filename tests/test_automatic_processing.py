"""Private automatic public pilot fixtures; never read or write real libraries."""
import copy,json,threading,time,tempfile,unittest,uuid,urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import groups
from scanner import Inventory,connect
from source_identity import source_gate,clues,filename_identity
from public_research import PublicClient,PublicResearch,ResearchWait,allowed_url,parse_page,credited_pair,strict_json,APP_LIMIT_REASON,LEGACY_APP_LIMIT_REASON,SOURCE_PAUSE_REASON
from automatic_processing import AutomaticProcessing
from audio_jobs import AudioJobs
from merge_service import MergeService

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
    # Internet-path cases pin local agreement off; test_local_identity reruns their holds with the default rule.
    local_agreement_default=True
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.base=Path(self.temp.name);self.db=self.base/'catalog.sqlite3';self.controllers=[]
        # These cases exercise the Internet research path; local agreement is tested in test_local_identity.
        research_path=patch.object(PublicResearch,'local_agreement',self.local_agreement_default);research_path.start();self.addCleanup(research_path.stop)
    def tearDown(self):
        for auto in self.controllers:auto.close()
        self.temp.cleanup()
    def candidate(self,title='A Book',author='John Writer'):
        # Author only in the tags (file named by title alone): local sources do not agree, so the
        # default rule sends this book to the Internet research path these cases exercise.
        return next(iter(groups.build([row(self.base/(title+'.mp3'),title,author)]) .values()))|{'fingerprint':'private-fixture-fingerprint'}
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
        self.assertEqual(result['reasons'],[],result);self.assertEqual(result['review']['title'],'A Book');self.assertEqual(result['review']['author'],'John Writer')
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
        self.assertEqual(result['review']['original_language'],'Unknown');self.assertEqual(result['metadata_facts']['series_state'],'omitted_unknown');self.assertNotIn('standalone',{e['field'] for e in result['evidence']})
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
    def test_host_request_limit_preserves_cache_other_hosts_and_oldest_expiry(self):
        import base64,hashlib
        now=[100000];calls=[];client=PublicClient(self.db,fetch=lambda url,*_:(calls.append(url) or b'fixture'),clock=lambda:now[0])
        cached='https://ast.ru/book/cached';raw=b'known cached evidence'
        with connect(self.db) as db:
            db.executemany('INSERT INTO public_research_requests VALUES(?,?)',[('ast.ru',now[0]-3590+i) for i in range(100)])
            db.execute('INSERT INTO public_research_cache VALUES(?,?,?,?)',(cached,base64.b64encode(raw).decode(),hashlib.sha256(raw).hexdigest(),now[0]))
        budget={'remaining':3}
        with self.assertRaises(ResearchWait) as caught:client.read('https://ast.ru/book/new',budget=budget)
        wait=caught.exception;self.assertEqual((wait.kind,wait.scope,wait.retry_at),('app_limit','host',100010));self.assertEqual(budget['remaining'],3)
        self.assertEqual(client.read(cached,budget={'remaining':0}),raw)
        self.assertEqual(client.read('https://api.fantlab.ru/work/fixture',budget=budget),b'fixture');self.assertEqual(budget['remaining'],2)
        now[0]=100010;self.assertEqual(client.read('https://ast.ru/book/new',budget=budget),b'fixture');self.assertEqual(budget['remaining'],1)
        self.assertEqual(len(calls),2)
    def test_host_request_reservation_is_atomic_across_clients(self):
        now=100000;calls=[];barrier=threading.Barrier(2);results=[]
        clients=[PublicClient(self.db,fetch=lambda url,*_:(calls.append(url) or b'fixture'),clock=lambda:now) for _ in range(2)]
        with connect(self.db) as db:db.executemany('INSERT INTO public_research_requests VALUES(?,?)',[('ast.ru',now-100)]*99)
        def request(index):
            barrier.wait()
            try:clients[index].read('https://ast.ru/book/'+str(index));results.append('fetched')
            except ResearchWait as wait:results.append(wait.kind)
        children=[threading.Thread(target=request,args=(i,)) for i in range(2)]
        for child in children:child.start()
        for child in children:child.join(3);self.assertFalse(child.is_alive())
        self.assertCountEqual(results,['fetched','app_limit']);self.assertEqual(len(calls),1)
        with connect(self.db) as db:self.assertEqual(db.execute("SELECT count(*) FROM public_research_requests WHERE host='ast.ru'").fetchone()[0],100)
    def test_source_http_pause_honors_retry_after_without_exposing_error(self):
        from email.utils import format_datetime
        import datetime as dt
        for index,(code,header,duration) in enumerate(((429,'7200',7200),(403,format_datetime(dt.datetime.fromtimestamp(108000,dt.timezone.utc),usegmt=True),8000),(429,'invalid',3600),(503,'7200',7200),(500,'invalid',300))):
            def fetch(*_):raise urllib.error.HTTPError('https://ast.ru/private?token=PRIVATE',code,'PRIVATE',{'Retry-After':header},None)
            client=PublicClient(self.base/('pause'+str(index)+'.sqlite3'),fetch=fetch,clock=lambda:100000)
            with self.assertRaises(ResearchWait) as caught:client.read('https://ast.ru/book/fixture')
            wait=caught.exception;self.assertEqual(wait.retry_at,100000+duration);self.assertNotIn('PRIVATE',str(wait))
            self.assertEqual(wait.kind,'source_pause' if code in (403,429,503) else 'source_unavailable')
            # An explicit website pause survives local-budget migration and later reads.
            with self.assertRaises(ResearchWait) as again:client.read('https://ast.ru/book/another')
            self.assertEqual(again.exception.retry_at,wait.retry_at);self.assertEqual(again.exception.kind,wait.kind)
    def test_later_inflight_failure_cannot_shorten_a_shared_source_pause(self):
        first_entered=threading.Event();second_entered=threading.Event();first_finished=threading.Event();results=[]
        def first_fetch(*_):
            first_entered.set()
            if not second_entered.wait(3):raise AssertionError('Second owned request did not enter')
            raise urllib.error.HTTPError('https://ast.ru/book/first',429,'Unavailable',{'Retry-After':'7200'},None)
        def second_fetch(*_):
            second_entered.set()
            if not first_finished.wait(3):raise AssertionError('First owned pause did not finish')
            raise urllib.error.HTTPError('https://ast.ru/book/second',500,'Unavailable',{},None)
        clients=[PublicClient(self.db,fetch=first_fetch,clock=lambda:100000),PublicClient(self.db,fetch=second_fetch,clock=lambda:100000)]
        def request(index):
            try:clients[index].read('https://ast.ru/book/'+str(index))
            except ResearchWait as wait:results.append((index,wait.retry_at,wait.kind,wait.reason))
            finally:
                if index==0:first_finished.set()
        children=[threading.Thread(target=request,args=(i,)) for i in range(2)];children[0].start();self.assertTrue(first_entered.wait(3));children[1].start()
        for child in children:child.join(5);self.assertFalse(child.is_alive())
        self.assertCountEqual(results,[(0,107200,'source_pause',SOURCE_PAUSE_REASON),(1,107200,'source_pause',SOURCE_PAUSE_REASON)])
        with connect(self.db) as db:
            limit=db.execute("SELECT next_at,reason FROM public_research_limits WHERE host='ast.ru'").fetchone();self.assertEqual((limit['next_at'],limit['reason']),(107200,SOURCE_PAUSE_REASON))
    def test_only_known_legacy_app_limit_is_recalculated_and_actual_pause_preserved(self):
        client=PublicClient(self.db,fetch=lambda *_:b'fixture',clock=lambda:100000)
        legacy={'source':'ast.ru','reason':LEGACY_APP_LIMIT_REASON,'retry_at':180000}
        with connect(self.db) as db:db.executemany('INSERT INTO public_research_requests VALUES(?,?)',[('ast.ru',96410+i) for i in range(100)])
        revised=client.retry_wait(legacy);self.assertEqual(revised['retry_at'],100010);self.assertEqual(revised['kind'],'app_limit')
        for untouched in ({'source':'ast.ru','reason':'Public source unavailable; no bypass attempted','retry_at':180000}, {'source':'ast.ru','reason':'Public research request bound reached','retry_at':180000,'kind':'app_limit','scope':'candidate'}, {'source':'unknown','reason':LEGACY_APP_LIMIT_REASON,'retry_at':180000}):
            self.assertEqual(client.retry_wait(untouched),untouched)
        with connect(self.db) as db:db.execute('INSERT OR REPLACE INTO public_research_limits VALUES(?,?,?)',('ast.ru',108000,SOURCE_PAUSE_REASON))
        revised=client.retry_wait(legacy);self.assertEqual((revised['kind'],revised['retry_at'],revised['reason']),('source_pause',108000,SOURCE_PAUSE_REASON))
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
    def test_waiting_source_retries_automatically_at_earliest_opportunity(self):
        calls=[];now=[100000];observed=[]
        def lookup(*_):
            calls.append(1)
            return {'reasons':['Book identity uncertain'],'sources':[],'wait':{'source':'Public fixture','reason':'Unavailable','retry_at':now[0]+5}} if len(calls)==1 else {'reasons':['Book identity uncertain'],'sources':[]}
        auto,merge,inv=self.fake_merge(lookup);auto.clock=lambda:now[0];original=auto.stop_event.wait
        def advance(delay):
            state=auto.status()
            if delay>=1 and len(calls)>=2:
                # The first source opportunity was consumed; stop at the later uncertainty backoff.
                self.assertEqual(state['phase'],'waiting');self.assertEqual(state['research']['held'],1)
                auto.stop_event.set();return True
            if delay>=1:
                observed.append(auto.status());self.assertEqual(len(json.loads(auto._run_row()['checkpoint'])['pending']),1);now[0]+=delay;return False
            return original(delay)
        with patch.object(auto.stop_event,'wait',side_effect=advance):auto.start();state=self.wait_auto(auto,stop_when_held=False)
        self.assertEqual(state['state'],'Paused');self.assertEqual(len(calls),2);self.assertEqual(state['research']['held'],1)
        self.assertEqual(len(observed),1);waiting=observed[0]
        self.assertEqual((waiting['state'],waiting['phase'],waiting['next_retry_at']),('Running','waiting',100005));self.assertTrue(waiting['automatic_retry_enabled']);self.assertFalse(waiting['can_start']);self.assertTrue(waiting['can_stop']);self.assertIsNone(waiting['current'])
        self.assertFalse(state['automatic_retry_enabled']);self.assertIsNone(state['next_retry_at']);merge.approve_automatic.assert_not_called()
        self.assertEqual(len(json.loads(auto._run_row()['checkpoint'])['done']),1)
    def test_waiting_uses_earliest_candidate_and_does_not_revisit_later_source_early(self):
        now=[100000];attempts={};wakes=[]
        def lookup(current,*_):
            title=current['title_clue'];attempts[title]=attempts.get(title,0)+1
            return {'reasons':['Uncertain'],'wait':{'source':'Public fixture','reason':'Unavailable','retry_at':now[0]+(5 if title=='A Book' else 20)}} if attempts[title]==1 else {'reasons':['Uncertain']}
        auto,merge,inv=self.fake_merge(lookup);auto.clock=lambda:now[0]
        (self.base/'audio'/'John Writer – B Book.mp3').write_bytes(b'private second fixture');inv.reader=lambda p,k,s:json.loads(row(p,filename_identity(p)['title'])['metadata'])
        original=auto.stop_event.wait
        def advance(delay):
            if delay<1:return original(delay)
            # Fake clock with Event.wait semantics: any Stop (this fake or wait_auto's) ends the wait
            # unrecorded. The final stop is decided from research counts, which a concurrent Stop
            # does not change, and every recorded wake comes from the same single snapshot.
            state=auto.status()
            if auto.stop_event.is_set() or (state['research']['held'] and not state['research']['waiting']):
                auto.stop_event.set();return True
            wakes.append(state['next_retry_at']);now[0]+=delay;return False
        with patch.object(auto.stop_event,'wait',side_effect=advance):auto.start();state=self.wait_auto(auto,stop_when_held=False)
        self.assertEqual(wakes,[100005,100020]);self.assertEqual(attempts,{'A Book':2,'B Book':2});self.assertEqual(state['state'],'Paused');merge.approve_automatic.assert_not_called()
    def test_stop_during_armed_wait_preserves_pending_and_restart_stays_paused(self):
        auto,merge,inv=self.fake_merge(lambda *_:{'reasons':['Uncertain'],'wait':{'source':'Public fixture','reason':'Unavailable','retry_at':time.time()+3600}})
        auto.start();deadline=time.monotonic()+3
        while not auto.status()['automatic_retry_enabled'] and auto.thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue(auto.status()['automatic_retry_enabled']);begin=time.monotonic();auto.stop();state=self.wait_auto(auto)
        self.assertLess(time.monotonic()-begin,1);self.assertEqual(state['state'],'Paused');self.assertFalse(state['automatic_retry_enabled']);self.assertIsNone(state['next_retry_at'])
        pending=json.loads(auto._run_row()['checkpoint'])['pending'];self.assertEqual(len(pending),1)
        restarted=AutomaticProcessing(merge,auto.research);self.controllers.append(restarted)
        self.assertIsNone(restarted.thread);self.assertEqual(restarted.status()['state'],'Paused');self.assertFalse(restarted.status()['automatic_retry_enabled']);self.assertEqual(json.loads(restarted._run_row()['checkpoint'])['pending'],pending)
        merge.approve_automatic.assert_not_called()
    def test_required_working_cleanup_drains_before_retry_is_armed(self):
        now=[100000];visits=[];cleanup=[False];drained=[]
        def lookup(*_):
            visits.append(1);cleanup[0]=len(visits)==1
            return {'reasons':['Uncertain'],'wait':{'source':'Public fixture','reason':'Unavailable','retry_at':now[0]+5}} if len(visits)==1 else {'reasons':['Uncertain']}
        auto,merge,inv=self.fake_merge(lookup);auto.clock=lambda:now[0];original_state=merge.state;merge.state=lambda:original_state()|{'cleanup_active':cleanup[0]};original_wait=auto.stop_event.wait
        def advance(delay):
            if cleanup[0]:
                state=auto.status()
                self.assertFalse(state['automatic_retry_enabled']);self.assertIsNone(state['current']);drained.append(True);cleanup[0]=False;return False
            if delay<1:return original_wait(delay)
            # Event.wait semantics: wait_auto's concurrent Stop ends the wait instead of tripping the
            # armed-retry assertion inside the worker; the final stop is decided from research counts.
            state=auto.status()
            if auto.stop_event.is_set() or (state['research']['held'] and not state['research']['waiting']):
                auto.stop_event.set();return True
            self.assertTrue(state['automatic_retry_enabled']);now[0]+=delay;return False
        with patch.object(auto.stop_event,'wait',side_effect=advance):auto.start();state=self.wait_auto(auto,stop_when_held=False)
        self.assertEqual(drained,[True]);self.assertEqual(len(visits),2);self.assertEqual(state['state'],'Paused');merge.approve_automatic.assert_not_called()
    def test_restart_of_waiting_running_checkpoint_does_not_arm_retry(self):
        auto,merge,inv=self.fake_merge();run_id=str(uuid.uuid4());now='2026-10-11T00:00:00Z'
        with connect(self.db) as db:db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(run_id,'Running','research',json.dumps({'pending':[str(uuid.uuid4())],'done':[]}),'Waiting for metadata sources',now,now))
        restarted=AutomaticProcessing(merge,auto.research);self.controllers.append(restarted);state=restarted.status()
        self.assertEqual(state['state'],'Paused');self.assertTrue(state['restart_paused']);self.assertFalse(state['automatic_retry_enabled']);self.assertIsNone(restarted.thread);merge.approve_automatic.assert_not_called()
    def test_legacy_wait_migration_retains_all_evidence_and_does_not_approve(self):
        auto,merge,inv=self.fake_merge();inv.launch('Audiobooks');inv.worker.join(3);candidate=inv.candidates('Audiobooks')['rows'][0]
        client=PublicClient(self.db,fetch=lambda *_:b'fixture',clock=lambda:100000);auto.research.client=client
        result={'sources':[{'sha256':'fixture unique proof'}],'work':WORK,'reasons':['Uncertain'],'wait':{'source':'ast.ru','reason':LEGACY_APP_LIMIT_REASON,'retry_at':180000}}
        auto._record(candidate,'Waiting for source',result,180000);record=auto._refresh_wait(candidate,auto.candidate(candidate))
        self.assertEqual(record['retry_at'],100000);self.assertEqual(record['wait']['kind'],'app_limit')
        with connect(self.db) as db:stored=json.loads(db.execute('SELECT result FROM automatic_candidates').fetchone()[0])
        self.assertEqual(stored['sources'],result['sources']);self.assertEqual(stored['work'],WORK);self.assertEqual(stored['reasons'],result['reasons']);merge.approve_automatic.assert_not_called()
    def test_new_identity_sources_reconsider_old_wait_once_without_erasing_host_pause(self):
        auto,merge,inv=self.fake_merge();inv.launch('Audiobooks');inv.worker.join(3);candidate=inv.candidates('Audiobooks')['rows'][0]
        result={'reasons':['Book identity uncertain'],'wait':{'source':'api.fantlab.ru','kind':'app_limit','reason':APP_LIMIT_REASON,'retry_at':180000}}
        auto._record(candidate,'Waiting for source',result,180000)
        with connect(self.db) as db:
            db.execute("UPDATE automatic_candidates SET result=?",(json.dumps(result),))
            db.execute("CREATE TABLE IF NOT EXISTS public_research_limits(host TEXT PRIMARY KEY,next_at REAL,reason TEXT)")
            db.execute("INSERT INTO public_research_limits VALUES(?,?,?)",('api.fantlab.ru',180000,SOURCE_PAUSE_REASON))
        old=auto.candidate(candidate);reconsidered=auto._refresh_wait(candidate,old)
        self.assertIsNone(reconsidered['retry_at']);merge.approve_automatic.assert_not_called()
        auto._record(candidate,'Waiting for source',result,180000)
        current=auto._refresh_wait(candidate,auto.candidate(candidate));self.assertEqual(current['retry_at'],180000)
        with connect(self.db) as db:self.assertEqual(db.execute("SELECT next_at FROM public_research_limits WHERE host='api.fantlab.ru'").fetchone()[0],180000)

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
        calls=[];now=[100000];auto.clock=lambda:now[0];observed=[];original=auto.stop_event.wait
        def admit(current,*_):
            calls.append(current['id'])
            if len(calls)==1:raise ResearchWait('Public cover fixture','Unavailable',now[0]+5)
            return current,'private-second-job'
        def advance(delay):
            state=auto.status()
            if delay>=1 and state['automatic_retry_enabled'] and state['research']['held'] and not state['research']['waiting']:
                auto.stop_event.set();return True
            if delay>=1:
                observed.append((list(calls),auto.status()));now[0]+=delay;return False
            return original(delay)
        merge.approve_automatic.side_effect=admit
        with patch.object(auto.stop_event,'wait',side_effect=advance):auto.start();state=self.wait_auto(auto)
        self.assertEqual(len(calls),3);self.assertEqual(state['state'],'Completed');self.assertEqual(state['research']['waiting'],0)
        self.assertEqual(len(observed[0][0]),2);self.assertEqual(observed[0][1]['research']['waiting'],1);self.assertEqual(observed[0][1]['research']['researching'],0)
        self.assertEqual(calls[0],calls[2]);self.assertNotEqual(calls[1],calls[2])

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
        self.assertEqual(state['state'],'Paused');self.assertEqual(state['research']['held'],1)
        merge.approve_automatic.assert_called_once();self.assertEqual(merge.approve_automatic.call_args.args[0]['members'][0]['metadata']['tags']['album'],'B Book')
        held=[auto.candidate(current) for current in inv.candidates('Audiobooks')['rows'] if current['members'][0]['metadata']['tags']['album']==long_title]
        self.assertEqual(len(held),1);self.assertEqual(held[0]['state'],'Held')
        self.assertEqual(held[0]['reasons'],['Public research input or evidence exceeds supported limits']);self.assertEqual(calls,[])


    def test_unexpected_research_failure_is_durable_private_and_never_approves(self):
        secret='PRIVATE_TOKEN_ABC';path='Z:\\Audiobooks\\private-source-name.mp3'
        def lookup(*_):raise RuntimeError('api_key='+secret+' https://ast.ru/private?token='+secret+' '+path+' '+'x'*20000)
        auto,merge,inv=self.fake_merge(lookup);auto.start();status=self.wait_auto(auto)
        run=auto._run_row();pending=json.loads(run['checkpoint'])['pending'];candidate=inv.candidate('Audiobooks',pending[0])
        self.assertEqual(status['state'],'Needs attention');self.assertEqual(status['research']['researching'],0);self.assertIsNone(status['current'])
        self.assertEqual(auto.candidate(candidate)['state'],'Needs attention');self.assertEqual(auto.candidate(candidate)['reasons'][0],'Metadata research failed')
        error=status['failure'];self.assertTrue(status['failure_durable']);self.assertEqual(error['exception_class'],'RuntimeError')
        self.assertEqual((error['run_id'],error['phase'],error['candidate_id']),(run['id'],'research',candidate['id']))
        packed=json.dumps(error);self.assertLessEqual(len(packed.encode()),8192);self.assertLessEqual(len(error['stack']),8)
        for value in (secret,path,'https://ast.ru','private-source-name'):self.assertNotIn(value,packed)
        self.assertTrue(error['message_truncated']);self.assertTrue(error['stack']);self.assertNotIn('source',error['stack'][-1])
        self.assertIn('Source files for this book were preserved.',status['reason']);merge.approve_automatic.assert_not_called();merge.resume.assert_not_called()
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT count(*) FROM automatic_errors').fetchone()[0],1)
        second=AutomaticProcessing(merge,auto.research);self.controllers.append(second)
        self.assertIsNone(second.thread);self.assertEqual(second.status()['failure'],error);self.assertEqual(second.status()['state'],'Needs attention')
        self.assertEqual(json.loads(second._run_row()['checkpoint'])['pending'],pending);merge.approve_automatic.assert_not_called()
        second.research.lookup=lambda *_:{'reasons':['Book identity uncertain'],'sources':[]}
        with patch.object(inv,'launch') as discovery:
            second.start();retried=self.wait_auto(second);discovery.assert_not_called()
        self.assertEqual(second._run_row()['id'],run['id']);self.assertEqual(retried['state'],'Paused');self.assertEqual(retried['research']['held'],1)
        merge.approve_automatic.assert_not_called()

    def test_historical_missing_failure_detail_is_not_invented_or_left_researching(self):
        auto,merge,inv=self.fake_merge(lambda *_:(_ for _ in ()).throw(RuntimeError('lost historical message')))
        auto.start();self.wait_auto(auto);run=auto._run_row();candidate_id=json.loads(run['checkpoint'])['pending'][0]
        with connect(self.db) as db:
            db.execute('DELETE FROM automatic_errors');db.execute("UPDATE automatic_candidates SET state='Researching',result='{}' WHERE id=?",(candidate_id,))
        restarted=AutomaticProcessing(merge,auto.research);self.controllers.append(restarted)
        state=restarted.status();candidate=inv.candidate('Audiobooks',candidate_id);record=restarted.candidate(candidate)
        self.assertIsNone(restarted.thread);self.assertIsNone(state['failure']);self.assertFalse(state['failure_durable'])
        self.assertEqual(state['research']['researching'],0);self.assertEqual(record['state'],'Needs attention')
        self.assertIn('Failure details were not recorded.',record['reasons']);self.assertIn('retry this book',state['retry_help'])
        merge.approve_automatic.assert_not_called();merge.resume.assert_not_called()

    def test_interruption_is_saved_pause_without_an_app_failure_record(self):
        auto,merge,inv=self.fake_merge(lambda *_:(_ for _ in ()).throw(InterruptedError()))
        auto.start();state=self.wait_auto(auto);self.assertEqual(state['state'],'Paused');self.assertIsNone(state['failure'])
        self.assertEqual(state['research']['researching'],0);self.assertEqual(len(json.loads(auto._run_row()['checkpoint'])['pending']),1)
        with connect(self.db) as db:self.assertEqual(db.execute('SELECT count(*) FROM automatic_errors').fetchone()[0],0)
        restarted=AutomaticProcessing(merge,auto.research);self.controllers.append(restarted)
        self.assertIsNone(restarted.thread);self.assertEqual(restarted.status()['state'],'Paused');merge.approve_automatic.assert_not_called()

    def test_failure_checkpoint_refusal_blocks_retry_without_claiming_durability(self):
        import sqlite3
        auto,merge,inv=self.fake_merge();inv.launch('Audiobooks');inv.worker.join(5)
        candidate=inv.candidates('Audiobooks')['rows'][0];run_id=str(uuid.uuid4());now='2026-10-11T00:00:00+00:00'
        with connect(self.db) as db:db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(run_id,'Running','research',json.dumps({'pending':[candidate['id']],'done':[]}),'',now,now))
        auto._record(candidate,'Researching')
        with patch('sqlite_retry.connect',side_effect=sqlite3.OperationalError('PRIVATE_DATABASE_PATH')):
            auto._failure(run_id,RuntimeError('PRIVATE_ERROR'), 'research',candidate['id'],candidate,True)
        state=auto.status();self.assertEqual(state['state'],'Needs attention');self.assertFalse(state['failure_durable']);self.assertFalse(state['can_start'])
        self.assertEqual(state['research']['researching'],0);self.assertEqual(auto.candidate(candidate)['state'],'Needs attention')
        self.assertEqual(state['reason'],'Retry progress could not be saved; Start is unavailable.');self.assertEqual(state['retry_help'],'')
        self.assertNotIn('PRIVATE_',json.dumps(state['failure']))
        with self.assertRaisesRegex(ValueError,'checkpoint could not be saved'):auto.start()
        merge.approve_automatic.assert_not_called();merge.resume.assert_not_called()

    def test_structural_type_error_diagnostic_keeps_safe_message_and_code_location(self):
        from automatic_processing import failure_diagnostic
        try:None.get('PRIVATE_FIELD')
        except AttributeError as error:record=failure_diagnostic(error,str(uuid.uuid4()),'research',str(uuid.uuid4()))
        self.assertEqual(record['exception_class'],'AttributeError');self.assertEqual(record['message'],"'NoneType' object has no attribute 'get'")
        self.assertNotIn('PRIVATE_FIELD',json.dumps(record));self.assertTrue(record['stack'])

    def fake_merge(self,lookup=None):
        audio=self.base/'audio';audio.mkdir(exist_ok=True);path=audio/'John Writer – A Book.mp3';path.write_bytes(b'fixture only')
        inv=Inventory(self.db,{'Audiobooks':str(audio),'Podcasts':str(self.base/'podcasts'),'Ebooks':str(self.base/'ebooks')},lambda p,k,s:json.loads(row(p,'A Book')['metadata']))
        state={'state':'Completed','queued':0};reviews=SimpleNamespace(_context=lambda row:{},_row=lambda lib,id,revision=None:inv.candidate(lib,id))
        merge=SimpleNamespace(inventory=inv,reviews=reviews,_no_scan=lambda:None,state=lambda:dict(state),pause=lambda:state.update(state='Paused'),resume=Mock(),candidate_status=lambda id:None)
        merge.approve_automatic=Mock(side_effect=lambda row,result,stop,client:(row,'fixture-job'))
        research=SimpleNamespace(client=SimpleNamespace(retry_wait=lambda wait:dict(wait)),lookup=lookup or (lambda *args:{'reasons':['Book identity uncertain'],'sources':[]}))
        auto=AutomaticProcessing(merge,research);merge.automatic=auto;self.controllers.append(auto)
        return auto,merge,inv
    def wait_auto(self,auto,stop_when_held=True):
        # stop_when_held=False: the test's fake stop_event.wait is the single stopper, so no second
        # thread can Stop between that fake's status snapshot and its assertions (the old race).
        deadline=time.monotonic()+5
        while auto.thread.is_alive() and time.monotonic()<deadline:
            state=auto.status()
            if stop_when_held and state['automatic_retry_enabled'] and state['research']['held'] and not state['research']['waiting']:auto.stop()
            auto.thread.join(.01)
        self.assertFalse(auto.thread.is_alive());return auto.status()
    def test_construction_and_inventory_only_never_approve(self):
        auto,merge,inv=self.fake_merge();self.assertEqual(auto.status()['state'],'Idle');merge.approve_automatic.assert_not_called();inv.launch('Audiobooks');inv.worker.join(5);merge.approve_automatic.assert_not_called();auto.close()
    def test_uncertain_work_is_revisited_until_user_stop(self):
        auto,merge,inv=self.fake_merge();auto.start();status=self.wait_auto(auto)
        self.assertEqual(status['state'],'Paused');self.assertEqual(status['research']['held'],1);merge.approve_automatic.assert_not_called()
        checkpoint=json.loads(auto._run_row()['checkpoint']);self.assertEqual(len(checkpoint['pending']),1)
        saved=auto.candidate(inv.candidates('Audiobooks')['rows'][0]);self.assertEqual(saved['research_attempt'],1);self.assertGreater(saved['retry_at'],time.time());self.assertEqual(saved['research_history'][0]['state'],'Held');auto.close()
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

    def test_repaired_observed_source_is_refreshed_then_researched_at_new_revision(self):
        lookup=Mock(return_value={'reasons':[],'sources':[]})
        auto,merge,inv=self.fake_merge(lookup);inv.launch('Audiobooks');inv.worker.join(5)
        original=inv.candidates('Audiobooks')['rows'][0];path=Path(original['members'][0]['path'])
        auto._record(original,'Held',{'reasons':['Source files changed'],'sources':[{'url':'https://ast.ru/book/old','sha256':'a'*64,'kind':'publisher_or_journal'}]},time.time()-1)
        run_id=str(uuid.uuid4())
        with connect(self.db) as db:
            db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(run_id,'Paused','research',json.dumps({'pending':[original['id']],'done':[]}), '', '2026-10-11T00:00:00Z','2026-10-11T00:00:00Z'))
            scan_before=dict(db.execute('SELECT * FROM jobs WHERE root=?',(inv.roots['Audiobooks'],)).fetchone())
        path.write_bytes(b'repaired complete observed source')
        with patch.object(inv,'refresh_candidate_sources',wraps=inv.refresh_candidate_sources) as refresh:
            auto.start();state=self.wait_auto(auto)
        self.assertEqual(state['state'],'Completed');refresh.assert_called_once()
        self.assertTrue(refresh.call_args.kwargs['force']);lookup.assert_called_once();merge.approve_automatic.assert_called_once()
        current=merge.approve_automatic.call_args.args[0]
        self.assertGreater(current['revision'],original['revision']);self.assertNotEqual(current['fingerprint'],original['fingerprint'])
        saved=auto.candidate(current)
        self.assertEqual(saved['state'],'Queued')
        archived=next(entry for entry in saved['research_history'] if entry.get('fingerprint')==original['fingerprint'])
        self.assertEqual(archived['revision'],original['revision']);self.assertEqual(archived['sources'][0]['sha256'],'a'*64)
        with connect(self.db) as db:
            stored=json.loads(db.execute('SELECT result FROM automatic_candidates WHERE id=?',(current['id'],)).fetchone()[0])
            self.assertEqual(stored['source_refresh']['old_fingerprint'],original['fingerprint'])
            self.assertEqual(dict(db.execute('SELECT * FROM jobs WHERE root=?',(inv.roots['Audiobooks'],)).fetchone()),scan_before)
        self.assertTrue(path.exists())
    def test_source_refresh_hold_does_not_query_or_approve_and_keeps_checkpoint(self):
        lookup=Mock(return_value={'reasons':[]});auto,merge,inv=self.fake_merge(lookup)
        inv.launch('Audiobooks');inv.worker.join(5);original=inv.candidates('Audiobooks')['rows'][0]
        auto._record(original,'Held',{'reasons':['Source files changed']},time.time()-1)
        with connect(self.db) as db:db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(str(uuid.uuid4()),'Paused','research',json.dumps({'pending':[original['id']],'done':[]}), '', '2026-10-11T00:00:00Z','2026-10-11T00:00:00Z'))
        with patch.object(inv,'refresh_candidate_sources',return_value={'state':'held','reason':'Observed source remains unreadable'}) as refresh:
            auto.start();state=self.wait_auto(auto)
        refresh.assert_called_once();lookup.assert_not_called();merge.approve_automatic.assert_not_called()
        self.assertEqual(state['state'],'Paused');self.assertEqual(auto.candidate(original)['reasons'],['Observed source remains unreadable'])
        checkpoint=json.loads(auto._run_row()['checkpoint']);self.assertIn(original['id'],checkpoint['pending']+checkpoint.get('deferred',[]))
        self.assertTrue(Path(original['members'][0]['path']).exists())
    def test_manual_draft_prevents_stale_source_refresh_before_any_read(self):
        lookup=Mock(return_value={'reasons':[]});auto,merge,inv=self.fake_merge(lookup)
        inv.launch('Audiobooks');inv.worker.join(5);original=inv.candidates('Audiobooks')['rows'][0]
        auto._record(original,'Held',{'reasons':['Source files changed']},time.time()-1);auto.draft(original['id'],original['revision'],True)
        with connect(self.db) as db:db.execute('INSERT INTO automatic_runs VALUES(?,?,?,?,?,?,?,0)',(str(uuid.uuid4()),'Paused','research',json.dumps({'pending':[original['id']],'done':[]}), '', '2026-10-11T00:00:00Z','2026-10-11T00:00:00Z'))
        with patch.object(inv,'refresh_candidate_sources',wraps=inv.refresh_candidate_sources) as refresh:
            auto.start();state=self.wait_auto(auto)
        refresh.assert_not_called();lookup.assert_not_called();merge.approve_automatic.assert_not_called()
        self.assertEqual(auto.candidate(original)['reasons'],['Manual draft retained']);self.assertEqual(state['state'],'Paused')
    def between_books_run(self,admit):
        """Research admits 'A Book' (admit) and leaves 'B Book' deferred, so the run reaches the wait for queued books."""
        lookup=lambda current,*_:{'reasons':[],'work':WORK,'review':{},'sources':[]} if current['title_clue']=='A Book' else {'reasons':['Uncertain']}
        auto,merge,inv=self.fake_merge(lookup)
        (self.base/'audio'/'John Writer – B Book.mp3').write_bytes(b'private second fixture');inv.reader=lambda p,k,s:json.loads(row(p,filename_identity(p)['title'])['metadata'])
        fx=BetweenBooks(self.base);self.addCleanup(fx.release)
        merge.state=fx.merge.state;merge.approve_automatic=Mock(side_effect=lambda row,result,stop,client:(admit(fx),(row,'fixture-job'))[1])
        user_stop=threading.Event();pauses=[]
        def pause():
            pauses.append('user stop' if user_stop.is_set() else 'no stop request');return fx.merge.pause()
        merge.pause=pause
        return auto,fx,user_stop,pauses
    def test_between_books_cleanup_gap_does_not_pause_the_run_or_stop_the_next_book(self):
        # v0.16.1 live: research exhausted, the run waits for queued books. One book's originals finish
        # moving to recovery, the next book starts, and a status read straddling that gap said Paused:
        # the run paused itself and stopped the just-started book. Every step below waits on an Event.
        auto,fx,user_stop,pauses=self.between_books_run(lambda fx:fx.start())
        original=auto.stop_event.wait;waits=[]
        def wait(delay):
            if fx.thread is None:return original(delay) # Discovery: the converter has no work yet.
            if delay>=1:user_stop.set();auto.stop_event.set();return True # The later retry wait: Sergei's Stop.
            waits.append(delay)
            if len(waits)==1:fx.removing.wait(5);fx.straddle.set() # The next queue read straddles the cleanup's end.
            elif len(waits)==2:fx.started.wait(5);fx.wake.set();fx.thread.join(5) # Book 2 then finishes normally.
            return False
        with patch.object(auto.stop_event,'wait',side_effect=wait):auto.start();state=self.wait_auto(auto,stop_when_held=False)
        self.assertTrue(fx.started.is_set(),'the next book started after the cleanup')
        self.assertEqual(fx.outcome,'completed','the just-started book was stopped by a between-books state')
        self.assertEqual(pauses[:1],['user stop'],'the run paused the queue without a stop request')
        self.assertEqual(state['state'],'Paused');self.assertGreaterEqual(len(waits),2)
    def test_stalled_queue_with_no_worker_still_pauses_the_run(self):
        # Safety kept: queued work that no converter or cleanup worker will pick up still ends the wait.
        auto,fx,user_stop,pauses=self.between_books_run(lambda fx:fx.admit())
        original=auto.stop_event.wait
        def wait(delay):
            if delay>=1:user_stop.set();auto.stop_event.set();return True
            return original(delay)
        with patch.object(auto.stop_event,'wait',side_effect=wait):auto.start();state=self.wait_auto(auto,stop_when_held=False)
        self.assertIsNone(fx.thread);self.assertFalse(user_stop.is_set())
        self.assertEqual(pauses[:1],['no stop request']);self.assertEqual(state['state'],'Paused');self.assertEqual(state['reason'],'Paused — pending work saved')
        self.assertEqual(fx.merge.state()['state'],'Paused')


class BetweenBooks:
    """The v0.16.1 between-books sequence around the real MergeService._after_completed and _state.

    A real AudioJobs ledger answers the converter state; fx.thread stands in for its worker. Book 1 is
    converted; its inline source cleanup sets and clears cleanup.current around cleanup.run, then book 2
    starts. Only that cleanup run and the next book are fakes, and every step waits on an Event.
    """
    def __init__(self,folder,jobs=('book-1','book-2'),hold_enrolment=False):
        self.queue=AudioJobs(Path(folder)/'between-books-queue.sqlite3',Mock(),Mock(),Mock());self.stop=self.queue._stop
        self.jobs=jobs;self.next_book=len(jobs)>1;self.thread=None;self.outcome=None;self.lock=threading.Lock();self.rows={}
        self.enrolled,self.hold_enrolment=threading.Event(),threading.Event()
        if not hold_enrolment:self.hold_enrolment.set()
        self.removing,self.finish_removal,self.cleared,self.gap=threading.Event(),threading.Event(),threading.Event(),threading.Event();self.gap.set()
        self.started,self.wake,self.straddle=threading.Event(),threading.Event(),threading.Event()
        merge=MergeService.__new__(MergeService);merge.jobs=self.queue;merge._post_current=None
        merge.cleanup=SimpleNamespace(current=None,thread=None,stop=self.stop,status=self.cleanup_status,run=self.run,run_with_retry=self.run,pause=self.pause_cleanup,_set=Mock(),hold=Mock())
        merge.storage_cleanup=SimpleNamespace(status=lambda:[],folder_status=lambda:[]);merge.working=SimpleNamespace(discharge_published=Mock())
        merge._prune_working=Mock();merge.enroll_cleanup=self.enroll;merge._prune_completed=self.pruned
        merge.progress_books=lambda *args:{'approved':0,'converted':0,'converted_ids':set()}
        pause_jobs=self.queue.pause
        def pause():
            result=pause_jobs();self.wake.set();return result
        self.queue.pause=pause;self.merge=merge
    def admit(self):
        for index,job_id in enumerate(self.jobs):
            state,stage=('completed','completed') if index==0 else ('pending','queued');created='2026-10-17T04:01:0'+str(index)
            manifest=json.dumps({'cleanup_policy':{'enabled':True},'metadata':{'title':job_id}})
            with self.queue._db() as db:db.execute('INSERT INTO audio_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',(job_id,manifest,'',state,stage,None,'{}',None,'',created,created))
    def start(self):
        self.admit();self.thread=threading.Thread(target=self.work,name='between-books-converter');self.queue._thread=self.thread;self.thread.start()
    def work(self):
        self.merge._after_completed(self.jobs[0]) # Real code: cleanup.current is set, cleanup.run, then cleared.
        if not self.next_book or self.stop.is_set():return # audio_jobs._work checks Stop before the next book.
        self.queue._update(self.jobs[1],state='running',stage='checking sources');self.started.set();self.wake.wait(10)
        if self.stop.is_set():self.queue._update(self.jobs[1],state='pending',stage='queued');self.outcome='interrupted'
        else:self.queue._update(self.jobs[1],state='completed',stage='completed');self.outcome='completed'
    def set_cleanup(self,id,job_id,state):
        with self.lock:self.rows[id]={'id':id,'job_id':job_id,'state':state,'status':'Fixture cleanup '+state,'removed':0,'total':2,'reason':''}
    def enroll(self,job_id):
        self.set_cleanup('cleanup-1',job_id,'waiting');self.enrolled.set();self.hold_enrolment.wait(10)
        return {'cleanup_id':'cleanup-1'}
    def run(self,id):
        job_id=self.rows[id]['job_id'];self.set_cleanup(id,job_id,'checking');self.set_cleanup(id,job_id,'removing');self.removing.set()
        self.finish_removal.wait(10);self.set_cleanup(id,job_id,'paused' if self.stop.is_set() else 'completed')
    def pruned(self,job_id):
        self.cleared.set();self.gap.wait(10) # _after_completed cleared cleanup.current before this call.
    def pause_cleanup(self):
        self.stop.set();self.finish_removal.set()
    def cleanup_status(self):
        with self.lock:rows=[dict(r) for r in self.rows.values()]
        if self.straddle.is_set() and any(r['state']=='removing' for r in rows):
            # This read saw 'removing'. The cleanup now ends, and the next book starts (or the
            # converter exits after the last book), before _state looks at the in-memory marker.
            self.straddle.clear();self.finish_removal.set();self.cleared.wait(10)
            if self.next_book:self.started.wait(10)
            else:self.thread.join(10)
        return rows
    def release(self):
        for event in (self.hold_enrolment,self.finish_removal,self.gap,self.wake):event.set()
        if self.thread:self.thread.join(10)


class BetweenBooksStateTests(unittest.TestCase):
    """v0.16.2: the queue state never reads Paused between two books while their worker is alive."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.fixtures=[]
    def tearDown(self):
        for fx in self.fixtures:fx.release()
        self.temp.cleanup()
    def fixture(self,**options):
        fx=BetweenBooks(self.temp.name,**options);self.fixtures.append(fx);return fx
    def test_cleanup_ending_during_a_status_read_is_not_a_pause(self):
        fx=self.fixture();fx.start();self.assertTrue(fx.removing.wait(5))
        fx.straddle.set();state=fx.merge.state()
        self.assertTrue(fx.started.is_set(),'the read straddled the end of the cleanup and the start of book 2')
        self.assertEqual(state['state'],'Running')
        fx.wake.set();fx.thread.join(5);self.assertEqual(fx.outcome,'completed')
    def test_cleanup_enrolled_before_its_marker_is_set_is_not_a_pause(self):
        fx=self.fixture(hold_enrolment=True);fx.start();self.assertTrue(fx.enrolled.wait(5))
        self.assertIsNone(fx.merge.cleanup.current);self.assertEqual(fx.rows['cleanup-1']['state'],'waiting')
        self.assertEqual(fx.merge.state()['state'],'Running')
    def test_last_book_cleanup_ending_during_a_status_read_is_not_a_pause(self):
        fx=self.fixture(jobs=('book-1',));fx.start();self.assertTrue(fx.removing.wait(5))
        fx.straddle.set();state=fx.merge.state()
        self.assertFalse(fx.thread.is_alive(),'the converter exited during the read')
        self.assertEqual(state['state'],'Running')
        self.assertEqual(fx.merge.state()['state'],'Completed')
    def test_cleanup_worker_handing_back_to_the_converter_is_not_a_pause(self):
        # CleanupJobs._work runs on_completed, then after_drain resumes the converter, from its own thread.
        fx=self.fixture();fx.admit();fx.set_cleanup('cleanup-1','book-1','completed')
        handing,release=threading.Event(),threading.Event()
        worker=threading.Thread(target=lambda:(handing.set(),release.wait(10)));fx.merge.cleanup.thread=worker;worker.start()
        try:
            self.assertTrue(handing.wait(5));self.assertEqual(fx.merge.state()['state'],'Running')
        finally:release.set();worker.join(5)
        self.assertEqual(fx.merge.state()['state'],'Paused','queued work with no worker alive still reads Paused')
    def test_cleanup_resumed_during_a_status_read_reads_running(self):
        # Kept from v0.16.1: the after-read check still sees a worker that a Resume started mid-read.
        fx=self.fixture();fx.admit();fx.set_cleanup('cleanup-1','book-1','paused');release=threading.Event()
        worker=threading.Thread(target=lambda:release.wait(10));read=fx.cleanup_status
        def resumed_mid_read():
            rows=read();fx.merge.cleanup.thread=worker;worker.start();return rows
        fx.merge.cleanup.status=resumed_mid_read
        try:self.assertEqual(fx.merge.state()['state'],'Running')
        finally:release.set();worker.join(5)
        fx.merge.cleanup.status=read;self.assertEqual(fx.merge.state()['state'],'Paused')
    def test_pause_during_cleanup_reads_pausing_until_the_converter_exits(self):
        fx=self.fixture();fx.gap.clear();fx.start();self.assertTrue(fx.removing.wait(5))
        fx.merge.pause();self.assertTrue(fx.cleared.wait(5))
        self.assertTrue(fx.thread.is_alive());self.assertIsNone(fx.merge.cleanup.current)
        self.assertEqual(fx.merge.state()['state'],'Pausing')
        fx.gap.set();fx.thread.join(5)
        self.assertFalse(fx.started.is_set());self.assertEqual(fx.rows['cleanup-1']['state'],'paused')
        self.assertEqual(fx.merge.state()['state'],'Paused')
    def test_pause_during_the_next_book_still_stops_it(self):
        fx=self.fixture();fx.start();self.assertTrue(fx.removing.wait(5))
        fx.finish_removal.set();self.assertTrue(fx.started.wait(5));self.assertEqual(fx.merge.state()['state'],'Running')
        fx.merge.pause();fx.thread.join(5)
        self.assertEqual(fx.outcome,'interrupted');self.assertEqual(fx.merge.state()['state'],'Paused')

if __name__=='__main__':unittest.main()

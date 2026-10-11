import copy,json,tempfile,unittest
from pathlib import Path
from collection_identity import parse_contents,bind_collection
from public_research import PublicClient,PublicResearch
from source_identity import source_gate

TITLE='Созвездие Льва'
PAGE=('<h1>'+TITLE+'</h1><p>Самодельная аудиокнига</p><table><tr><td>1.</td><td><a href="/autor1">John Writer</a></td><td><a href="/work101">First Tale</a></td></tr><tr><td>2.</td><td><a href="/autor2">Other Writer</a></td><td><a href="/work102">Second Tale</a></td></tr></table>').encode()
WORKS={101:{'work_id':101,'work_name':'First Tale','work_name_orig':'First Tale','work_name_alts':[],'authors':[{'type':'autor','name':'John Writer','name_orig':'John Writer'}],'lang_code':'en'},102:{'work_id':102,'work_name':'Second Tale','work_name_orig':'Second Tale','work_name_alts':[],'authors':[{'type':'autor','name':'Other Writer','name_orig':'Other Writer'}],'lang_code':'en'}}

def candidate():
    members=[]
    for i,title in enumerate(('First Tale','Second Tale'),1):
        members.append({'path':f'C:/books/{TITLE}/{i:02d} {title}.mp3','filename':f'{i:02d} {title}.mp3','duration':20+i,'track':i,'disc':1,'metadata':{'tags':{'album':TITLE,'title':title,'artist':'Narrator Person','track':str(i)}}})
    return {'fingerprint':'private-collection-source','members':members}

class CollectionTests(unittest.TestCase):
    def test_fetched_ordered_manifest_binds_every_local_track(self):
        records,_=parse_contents(PAGE,TITLE);collection,authors=bind_collection(candidate(),TITLE,records,WORKS)
        self.assertEqual(collection['component_count'],2);self.assertEqual(authors,['John Writer','Other Writer'])
        self.assertEqual([c['work_id'] for c in collection['components']],['fantlab:101','fantlab:102'])
        self.assertEqual(collection['components'][1]['source_spans'][0]['end_ms'],22000)
    def test_conflicting_manifest_author_cannot_be_copied_as_whole_host_truth(self):
        records,_=parse_contents(PAGE,TITLE);records[1]['authors']=['Ray Bradbury']
        with self.assertRaisesRegex(ValueError,'author role conflicts'):bind_collection(candidate(),TITLE,records,WORKS)
    def test_gap_missing_and_unmatched_sources_are_held(self):
        records,_=parse_contents(PAGE,TITLE)
        for mode in ('gap','missing','other'):
            r=candidate()
            if mode=='gap':r['members'][1]['track']=3
            if mode=='missing':r['members'].pop()
            if mode=='other':r['members'][1]['metadata']['tags']['title']='Unrelated story';r['members'][1]['filename']='02 Other Story.mp3'
            with self.subTest(mode=mode),self.assertRaises(ValueError):bind_collection(r,TITLE,records,WORKS)
    def test_catalog_miss_or_anthology_word_does_not_establish_fan_provenance(self):
        for page in (PAGE.replace('Самодельная аудиокнига'.encode(),b'Official anthology'),PAGE.replace(('<h1>'+TITLE+'</h1>').encode(),b'<h1>Other Book</h1>')):
            with self.assertRaises(ValueError):parse_contents(page,TITLE)
    def test_duplicate_component_or_bad_manifest_order_refused(self):
        for page in (PAGE.replace(b'/work102',b'/work101'),PAGE.replace(b'<td>2.</td>',b'<td>3.</td>')):
            with self.assertRaises(ValueError):parse_contents(page,TITLE)
    def test_lookup_fetches_components_not_just_collection_headline(self):
        area=Path(__file__).resolve().parents[1]/'scratch'/'source-fallback-2026-10-11';calls=[]
        with tempfile.TemporaryDirectory(dir=area) as temp:
            def fetch(url,*_):
                calls.append(url)
                if '/search-works?' in url:return json.dumps([{'work_id':900,'name':TITLE,'rusname':TITLE}]).encode()
                if '/work/900/extended' in url:return json.dumps({'work_id':900,'work_name':TITLE,'work_name_orig':TITLE,'authors':[],'work_name_alts':[],'parents':{},'work_type_name':'anthology'}).encode()
                if url=='https://fantlab.ru/work900':return PAGE
                for id in WORKS:
                    if '/work/'+str(id)+'/extended' in url:return json.dumps(WORKS[id]).encode()
                raise AssertionError('Unexpected fixture URL '+url)
            result=PublicResearch(PublicClient(Path(temp)/'fixture.sqlite3',fetch=fetch,clock=lambda:100000),leads=[]).lookup(candidate(),'C:/books')
            self.assertEqual(result['reasons'],[],result);self.assertEqual(result['metadata_facts']['collection']['component_count'],2)
            self.assertEqual(result['review']['canonical_author'],'John Writer; Other Writer')
            self.assertTrue(all(any('/work/'+str(id)+'/extended' in u for u in calls) for id in WORKS))
            self.assertEqual(source_gate(candidate(),result['work']),[])
            changed=candidate();changed['members'][1]['metadata']['tags']['author']='Ray Bradbury'
            self.assertTrue(source_gate(changed,result['work']))

    def test_unrelated_footer_or_other_heading_cannot_supply_collection_provenance(self):
        official=PAGE.replace('Самодельная аудиокнига'.encode(),b'Official anthology')
        for page in (official+b'<footer>fan-made archive</footer>',official+b'<h2>Other anthology</h2><p>Fan-made collection</p>'):
            with self.subTest(page=page),self.assertRaises(ValueError):parse_contents(page,TITLE)
    def test_unsupported_last_numbered_component_cannot_disappear(self):
        last=b'<tr><td>3.</td><td>Unlinked author</td><td>Unlinked third story</td></tr>'
        with self.assertRaisesRegex(ValueError,'component row unsupported'):
            parse_contents(PAGE.replace(b'</table>',last+b'</table>'),TITLE)
    def test_negated_fan_provenance_is_not_positive_evidence(self):
        with self.assertRaisesRegex(ValueError,'provenance'):
            parse_contents(PAGE.replace('Самодельная аудиокнига'.encode(),b'Not a fan-made anthology'),TITLE)

    def test_a_matching_clue_cannot_override_a_conflicting_constituent_title(self):
        records,_=parse_contents(PAGE,TITLE)
        for mode in ('embedded','filename'):
            changed=candidate()
            if mode=='embedded':changed['members'][0]['metadata']['tags']['title']='Second Tale'
            else:changed['members'][0]['filename']='01 Second Tale.mp3'
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'title conflicts'):
                bind_collection(changed,TITLE,records,WORKS)

    def test_correct_explicit_component_author_and_filename_credit_are_accepted(self):
        records,_=parse_contents(PAGE,TITLE);current=candidate()
        current['members'][0]['metadata']['tags']['author']='John Writer'
        current['members'][0]['filename']='John Writer - First Tale.mp3'
        current['members'][0]['path']=str(Path(current['members'][0]['path']).parent/current['members'][0]['filename'])
        collection,authors=bind_collection(current,TITLE,records,WORKS)
        self.assertEqual(collection['components'][0]['authors'],['John Writer'])
        self.assertEqual(collection['component_count'],2)

if __name__=='__main__':unittest.main()

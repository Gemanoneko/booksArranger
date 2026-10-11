import copy
import unittest
from standing_metadata import build_policy,validate_policy
from metadata import propose
from source_identity import source_gate

def row(title='Русское название',language=None):
    tags={'album':title,'artist':'John Writer'}
    if language:tags['language']=language
    return {'id':'candidate','fingerprint':'source-fingerprint','members':[{'path':'C:/books/book.mp3','filename':'John Writer - '+title+'.mp3','metadata':{'tags':tags},'duration':30,'track':1,'disc':1}],'metadata':{'tags':tags}}

def work(language=None):return {'id':'wd:Q1','titles':['Original Title','Русское название'],'author_aliases':['John Writer'],'original_language':language,'original_title':'Original Title','policy_version':'standing-17-v1'}

class StandingPolicyTests(unittest.TestCase):
    def test_unknown_original_language_russian_source_title_and_series_omission(self):
        review,facts,reasons=build_policy(row(),work(),'Original Title',['John Writer'])
        self.assertFalse(reasons);self.assertEqual(review['title'],'Русское название');self.assertEqual(review['original_language'],'Unknown')
        self.assertEqual(facts['original_language'],{'value':None,'status':'unknown'});self.assertEqual(facts['recording_language']['value'],'ru')
        self.assertEqual(facts['series_state'],'omitted_unknown');self.assertEqual((review['series'],review['number']),('',''))
    def test_published_english_and_source_russian_remain_distinct(self):
        review,facts,_=build_policy(row(),work('ja'),'Published Title',['John Writer'],english_verified=True)
        self.assertEqual(review['title'],'Published Title');self.assertEqual(facts['title_basis'],'published_english')
        review,facts,_=build_policy(row(),work('ja'),'English label only',['John Writer'])
        self.assertEqual(review['title'],'Русское название');self.assertEqual(facts['title_basis'],'source_russian')
    def test_full_author_name_and_native_credit_not_guessed_surname(self):
        review,facts,_=build_policy(row(),work('ja'),'Original Title',['山田 太郎'])
        self.assertEqual(review['author'],'山田 太郎');self.assertEqual(facts['author_folder_basis'],'verified_full_name')
    def test_conflicting_recording_language_is_held(self):
        r=row(language='ru');r['members'].append(dict(r['members'][0],path='C:/books/2.mp3',metadata={'tags':{'album':'Русское название','language':'en'}}))
        _,_,reasons=build_policy(r,work(),'Original Title',['John Writer'])
        self.assertIn('Recording languages conflict',reasons)
    def test_source_title_binding_is_revalidated(self):
        r=row();review,facts,_=build_policy(r,work(),'Original Title',['John Writer']);review['title']='Invented Title'
        with self.assertRaises(ValueError):validate_policy(r,review,facts)
    def test_manual_unknown_language_still_refused_private_policy_arranges(self):
        r=row();review,facts,_=build_policy(r,work(),'Original Title',['John Writer'])
        self.assertFalse(propose(r['members'][0]['path'],'C:/books','audiobook',r['metadata'],review)['path'])
        self.assertTrue(propose(r['members'][0]['path'],'C:/books','audiobook',r['metadata'],review,automatic_facts=facts)['path'].endswith('.m4b'))
    def test_original_and_recording_language_cannot_be_confused(self):
        r=row(language='ru');review,facts,_=build_policy(r,work('en'),'Original Title',['John Writer']);review['original_language']='Russian'
        with self.assertRaises(ValueError):validate_policy(r,review,facts)
    def test_existing_m4b_source_passes_same_identity_gate(self):
        r=row('Original Title');r['members'][0]['path']='C:/books/book.m4b';r['members'][0]['filename']='John Writer - Original Title.m4b'
        self.assertEqual(source_gate(r,work('en')),[])
    def test_filename_order_needs_common_identity_and_no_gaps(self):
        r=row('Original Title');r['members']=[dict(r['members'][0],path='C:/books/Original Title/'+str(i)+'.mp3',filename=f'{i:02d} chapter.mp3',track=None,metadata={'tags':{'album':'Original Title','artist':'John Writer'}}) for i in (1,2)]
        self.assertEqual(source_gate(r,work('en')),[])
        r['members'][1]['filename']='03 chapter.mp3'
        self.assertIn('Playback order uncertain',source_gate(r,work('en')))
    def test_mixed_independent_source_titles_are_held(self):
        r=row('Original Title');r['members'].append(dict(r['members'][0],path='C:/books/other.mp3',filename='Other Writer - Other Book.mp3',metadata={'tags':{'album':'Other Book','artist':'Other Writer'}}))
        self.assertTrue(source_gate(r,work('en')))

    def test_unbridged_russian_album_is_not_added_as_work_alias(self):
        r=row();w=work('ja');w['titles']=['Original Title']
        _,_,reasons=build_policy(r,w,'Original Title',['John Writer'])
        self.assertIn('Russian recording alias needs a verified original-work bridge',reasons)
    def test_surname_clue_uses_verified_full_name_folder(self):
        r=row('Original Title');r['members'][0]['filename']='Writer - Original Title.mp3'
        review,facts,_=build_policy(r,work('en'),'Original Title',['John Writer'])
        self.assertEqual(review['author'],'John Writer');self.assertEqual(facts['author_folder_basis'],'verified_full_name')
    def test_explicit_series_ordinal_is_used_without_inventing_unknown_position(self):
        from public_work_identity import series_position
        entity={'id':'Q1','claims':{'P179':[{'rank':'normal','mainsnak':{'snaktype':'value','property':'P179','datavalue':{'value':{'id':'Q2'}}},'qualifiers':{'P1545':[{'property':'P1545','snaktype':'value','datavalue':{'value':'3'}}]}}]}}
        series=series_position(entity,{'Q2':{'labels':{'en':{'value':'Verified Series'}}}})
        review,facts,_=build_policy(row(),work('en'),'Original Title',['John Writer'],series=series['name'],number=series['number'])
        self.assertEqual((review['series'],review['number'],facts['series_state']),('Verified Series','3','verified'))
        entity['claims']['P179'][0]['qualifiers']={};self.assertIsNone(series_position(entity,{}))
    def test_unofficial_alias_needs_explicit_fetched_translation_bridge(self):
        from public_research import recording_alias,parse_page
        w=work('ja');w['titles']=['Original Title']
        good=parse_page('<p>Русское название — John Writer. Original title: Original Title. Unofficial translation.</p>'.encode())
        bad=parse_page('<p>Русское название — John Writer. Another book: Original Title.</p>'.encode())
        self.assertIsNotNone(recording_alias(good,'Русское название',w));self.assertIsNone(recording_alias(bad,'Русское название',w))

    def test_two_latin_tokens_do_not_prove_family_name_order(self):
        for name in ('Higashino Keigo','Keigo Higashino','John Writer'):
            with self.subTest(name=name):
                review,facts,_=build_policy(row(),work(),'Original Title',[name])
                self.assertEqual(review['author'],name)
                self.assertEqual(facts['author_folder_basis'],'verified_full_name')

    def test_verified_series_conflicts_hold_but_unknown_series_is_not_invented(self):
        r=row('Original Title');w=work('en');w['verified_series']={'name':'Known Series','number':'1','source_url':'https://www.wikidata.org/wiki/Q1'}
        for key,value in (('series','Different Series'),('series-part','2'),('series_part','2')):
            changed=copy.deepcopy(r);changed['members'][0]['metadata']['tags'][key]=value
            with self.subTest(key=key):
                self.assertIn('Source series or position conflicts with verified work',source_gate(changed,w))
        matched=copy.deepcopy(r);matched['members'][0]['metadata']['tags'].update({'series':'Known Series','series-part':'1'})
        self.assertEqual(source_gate(matched,w),[])
        unknown=work('en');review,facts,_=build_policy(matched,unknown,'Original Title',['John Writer'])
        self.assertEqual(review['series'],'');self.assertEqual(facts['series_state'],'omitted_unknown')

if __name__=='__main__':unittest.main()

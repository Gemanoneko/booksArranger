"""Tiny private complete/partial dump fixtures. No production dump or catalog writes."""
import copy,gzip,hashlib,json,tempfile,unittest,sqlite3,contextlib
from pathlib import Path
from openlibrary_index import official_manifest,import_slice,lookup

AREA=Path(__file__).resolve().parents[1]/'scratch'/'openlibrary-index-tests'
AREA.mkdir(parents=True,exist_ok=True)

class IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=AREA);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).absolute();self.index=self.root/'index';self.date='2026-09-30'
        self.dumps=self.root/'dumps';self.dumps.mkdir()
        self.work={'key':'/works/OL1W','type':{'key':'/type/work'},'title':'A Book','authors':[{'author':{'key':'/authors/OL1A'}}],'links':[{'url':'https://ast.ru/book/example/'}]}
        self.person={'key':'/authors/OL1A','type':{'key':'/type/author'},'name':'John Writer','alternate_names':['J. Writer']}
        self.edition={'key':'/books/OL1M','type':{'key':'/type/edition'},'title':'A Book','works':[{'key':'/works/OL1W'}],'authors':[{'key':'/authors/OL1A'}],'isbn_13':['9780375823466'],'series':['Publisher collection 99']}
        files=[]
        for kind,rows in (('works',[self.work]),('authors',[self.person]),('editions',[self.edition])):
            path=self.dumps/('ol_dump_'+kind+'_'+self.date+'.txt.gz')
            raw=b''.join(('/type/'+kind+'\t'+row['key']+'\t1\t2026-01-01\t'+json.dumps(row)+'\n').encode() for row in rows)
            path.write_bytes(gzip.compress(raw,mtime=0));data=path.read_bytes()
            files.append({'name':path.name,'size':str(len(data)),'sha1':hashlib.sha1(data).hexdigest(),'md5':hashlib.md5(data).hexdigest()})
        self.raw=json.dumps({'metadata':{'identifier':'ol_dump_'+self.date},'files':files}).encode()
        self.receipt={'url':'https://archive.org/metadata/ol_dump_'+self.date,'sha256':hashlib.sha256(self.raw).hexdigest(),'retrieved_utc':'2026-10-18T16:00:00Z'}
        self.manifest=official_manifest(self.raw,self.receipt,self.date,self.dumps)
    def build(self,**kw):return import_slice(self.manifest,['A Book'],self.index,**kw)
    def replace_dump(self,kind,rows):
        path=self.dumps/('ol_dump_'+kind+'_'+self.date+'.txt.gz')
        payload=b''.join(('/type/'+kind+'\t'+row['key']+'\t1\t2026-01-01\t'+json.dumps(row)+'\n').encode() for row in rows)
        raw=gzip.compress(payload,mtime=0);path.write_bytes(raw);metadata=json.loads(self.raw)
        for entry in metadata['files']:
            if entry['name']==path.name:entry.update(size=str(len(raw)),sha1=hashlib.sha1(raw).hexdigest(),md5=hashlib.md5(raw).hexdigest())
        self.raw=json.dumps(metadata).encode();self.receipt=dict(self.receipt,sha256=hashlib.sha256(self.raw).hexdigest())
        self.manifest=official_manifest(self.raw,self.receipt,self.date,self.dumps)
    def test_official_metadata_schema_and_policy(self):
        from public_research import allowed_url
        self.assertEqual(allowed_url(self.receipt['url']),self.receipt['url'])
        for url in ('https://archive.org/download/ol_dump_2026-09-30/a.gz','https://archive.org/metadata/ol_dump_2026-09-30?x=1','https://archive.org:443/metadata/ol_dump_2026-09-30','https://archive.org/metadata/ol_dump_2026-02-30','https://archive.org/metadata/ol_dump_2026-09-30#x','https://archive.org/metadata/ol_dump_%32%30%32%36-09-30'):
            with self.assertRaises(ValueError):allowed_url(url)
        self.assertEqual(set(self.manifest['sources']),{'works','authors'});self.assertIn('editions',self.manifest['pending_editions']['path'])
        for change in ('duplicate','wrong_snapshot','missing_sha','invalid_size'):
            data=json.loads(self.raw)
            if change=='duplicate':data['files'].append(data['files'][0])
            elif change=='wrong_snapshot':data['metadata']['identifier']='ol_dump_2025-09-30'
            elif change=='missing_sha':del data['files'][0]['sha1']
            else:data['files'][0]['size']='99999999999999999999999999999999'
            raw=json.dumps(data).encode();receipt=dict(self.receipt,sha256=hashlib.sha256(raw).hexdigest())
            with self.assertRaises(ValueError):official_manifest(raw,receipt,self.date,self.root)
        with self.assertRaises(ValueError):official_manifest(self.raw,dict(self.receipt,sha256='0'*64),self.date,self.root)
    def test_resumes_private_checkpoint_then_activates_only_complete_generation(self):
        first=self.build(max_records=1);self.assertEqual(first['status'],'pending');self.assertEqual(lookup(self.index,'A Book')['status'],'unavailable')
        for _ in range(5):
            result=self.build(max_records=1)
            if result['status']=='ready':break
        self.assertEqual(result['status'],'ready')
        found=lookup(self.index,'A Book');self.assertEqual(found['status'],'covered');self.assertEqual(found['works'][0]['authors'][0]['names'],['John Writer','J. Writer'])
        self.assertEqual(lookup(self.index,'Another Book')['status'],'outside_coverage')
        self.assertEqual(lookup(self.index,'A Book')['works'][0]['editions'],[])
    def test_cli_reports_unicode_ready_on_legacy_windows_stdout(self):
        import io,runpy,sys
        from unittest.mock import patch
        self.work['title']='Björk';self.replace_dump('works',[self.work])
        manifest=self.root/'manifest.json';manifest.write_text(json.dumps(self.manifest),encoding='utf-8')
        targets=self.root/'targets.json';targets.write_text(json.dumps(['Björk']),encoding='utf-8')
        with self.assertRaises(UnicodeEncodeError):'Björk'.encode('cp1251')
        raw=io.BytesIO();stdout=io.TextIOWrapper(raw,encoding='cp1251')
        argv=['openlibrary_index.py','--manifest',str(manifest),'--targets',str(targets),'--directory',str(self.index)]
        with patch.object(sys,'argv',argv),patch.object(sys,'stdout',stdout):
            runpy.run_path(str(Path(__file__).resolve().parents[1]/'openlibrary_index.py'),run_name='__main__')
        stdout.flush();reported=json.loads(raw.getvalue().decode('ascii'))
        self.assertEqual(reported['status'],'ready');self.assertIn('björk',reported['receipt']['targets'])
        found=lookup(self.index,'Björk');self.assertEqual(found['status'],'covered');self.assertEqual(found['works'][0]['title'],'Björk')
        self.assertEqual(reported['receipt'],found['receipt'])
        from openlibrary_index import _json
        self.assertEqual(_json({'title':'Björk'}),'{"title":"Björk"}')
    def test_changed_same_size_source_cannot_mix_with_retained_prefix(self):
        self.build(max_records=1);path=Path(self.manifest['sources']['works']['path']);data=bytearray(path.read_bytes());data[15]^=1;path.write_bytes(data)
        with self.assertRaisesRegex(ValueError,'checksum'):self.build()
        self.assertEqual(lookup(self.index,'A Book')['status'],'unavailable')
    def test_partial_or_truncated_dump_never_activates(self):
        bad=copy.deepcopy(self.manifest);bad['sources']['works']['path']+='.crdownload'
        with self.assertRaisesRegex(ValueError,'Partial'):import_slice(bad,['A Book'],self.index)
        path=Path(self.manifest['sources']['works']['path']);path.write_bytes(path.read_bytes()[:-3])
        with self.assertRaisesRegex(ValueError,'incomplete'):self.build()
        self.assertEqual(lookup(self.index,'A Book')['status'],'unavailable')
    def test_authenticated_but_invalid_gzip_crc_is_not_ready(self):
        path=Path(self.manifest['sources']['works']['path']);data=bytearray(path.read_bytes());data[-8]^=1;path.write_bytes(data)
        metadata=json.loads(self.raw)
        for row in metadata['files']:
            if row['name']==path.name:row.update(sha1=hashlib.sha1(data).hexdigest(),md5=hashlib.md5(data).hexdigest())
        raw=json.dumps(metadata).encode();receipt=dict(self.receipt,sha256=hashlib.sha256(raw).hexdigest())
        self.manifest=official_manifest(raw,receipt,self.date,self.dumps)
        with self.assertRaises((gzip.BadGzipFile,EOFError)):self.build()
        self.assertEqual(lookup(self.index,'A Book')['status'],'unavailable')
    def test_editions_are_identity_and_discovery_only_and_old_activation_survives_partial(self):
        self.build();old=(self.index/'active.sqlite3').read_bytes()
        self.manifest['sources']['editions']=self.manifest['pending_editions'];path=Path(self.manifest['sources']['editions']['path']);data=path.read_bytes();path.write_bytes(data[:-1])
        with self.assertRaises(ValueError):self.build()
        self.assertEqual((self.index/'active.sqlite3').read_bytes(),old)
        path.write_bytes(data);self.build();edition=lookup(self.index,'A Book')['works'][0]['editions'][0]
        self.assertEqual(edition['series_discovery'],['Publisher collection 99']);self.assertFalse(edition['narrative_order_verified']);self.assertNotIn('number',edition)
    def test_activated_database_tamper_and_duplicate_official_entry_are_rejected(self):
        self.build()
        with contextlib.closing(sqlite3.connect(self.index/'active.sqlite3')) as db:receipt=json.loads(db.execute('SELECT receipt FROM active').fetchone()[0])
        path=self.index/receipt['file']
        with path.open('ab') as stream:stream.write(b'tamper')
        self.assertEqual(lookup(self.index,'A Book')['status'],'invalid')
        data=json.loads(self.raw);data['files'].append(data['files'][0]);raw=json.dumps(data).encode();receipt=dict(self.receipt,sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(ValueError,'duplicate'):official_manifest(raw,receipt,self.date,self.root)
    def test_unknown_sqlite_leaf_and_hardlink_cannot_mutate_outside_file(self):
        import os
        first=self.build(max_records=1);pending=self.index/('pending-'+first['token']+'.sqlite3')
        alias=self.root/'outside-alias.sqlite3';os.link(pending,alias);before=alias.read_bytes()
        with self.assertRaisesRegex(ValueError,'linked'):self.build()
        self.assertEqual(alias.read_bytes(),before)
        # A registry alias must be refused before any registry DDL/write.
        other=self.root/'other-index';other.mkdir();outside=self.root/'outside.txt';outside.write_bytes(b'outside unique bytes')
        os.link(outside,other/'active.sqlite3')
        with self.assertRaisesRegex(ValueError,'Unknown SQLite'):
            import_slice(self.manifest,['A Book'],other)
        self.assertEqual(outside.read_bytes(),b'outside unique bytes')
    def test_owned_mutable_sqlite_cannot_be_renamed_and_unknown_journal_is_refused(self):
        from openlibrary_index import _owned_sqlite
        from native_io import DirectoryBoundary
        self.index.mkdir();path=self.index/'test.sqlite3'
        with DirectoryBoundary(self.index,self.index) as boundary:
            with _owned_sqlite(path,'fixture',boundary) as db:
                db.execute('CREATE TABLE test(value TEXT)')
                with self.assertRaises(OSError):path.rename(self.index/'moved.sqlite3')
            journal=self.index/'unknown.sqlite3-journal';journal.write_bytes(b'unowned journal')
            with self.assertRaisesRegex(ValueError,'Unknown SQLite'):
                with _owned_sqlite(self.index/'unknown.sqlite3','unknown',boundary):pass
            self.assertEqual(journal.read_bytes(),b'unowned journal')
    def test_junction_output_refused_before_creating_any_outside_child(self):
        import _winapi
        from native_io import BoundaryError
        outside=self.root/'outside';outside.mkdir();marker=outside/'keep';marker.write_bytes(b'keep')
        link=self.root/'link';_winapi.CreateJunction(str(outside),str(link))
        try:
            with self.assertRaises(BoundaryError):import_slice(self.manifest,['A Book'],link/'new-index')
            self.assertEqual(list(outside.iterdir()),[marker]);self.assertEqual(marker.read_bytes(),b'keep')
        finally:link.rmdir()
    def test_crash_before_owner_receipt_refuses_orphans_without_adoption(self):
        from unittest.mock import patch
        with patch('openlibrary_index._publish_json',side_effect=RuntimeError('simulated crash before receipt')):
            with self.assertRaises(RuntimeError):self.build()
        with self.assertRaisesRegex(ValueError,'Unknown SQLite'):self.build()
        self.assertEqual(lookup(self.index,'A Book')['status'],'unavailable')
    def test_valid_sqlite_tamper_cannot_be_blessed_on_ready_reuse(self):
        self.build();old=(self.index/'active.sqlite3').read_bytes()
        with contextlib.closing(sqlite3.connect(self.index/'active.sqlite3')) as db:receipt=json.loads(db.execute('SELECT receipt FROM active').fetchone()[0])
        path=self.index/receipt['file']
        with contextlib.closing(sqlite3.connect(path)) as db,db:db.execute('UPDATE authors SET names=?',(json.dumps(['Wrong Person']),))
        with self.assertRaisesRegex(ValueError,'completion receipt'):self.build()
        self.assertEqual((self.index/'active.sqlite3').read_bytes(),old)
        self.assertEqual(lookup(self.index,'A Book')['status'],'invalid')
    def test_download_zone_marker_is_ignored_preserved_and_not_allowed_by_destructive_guard(self):
        from source_cleanup import single_stream
        from native_io import BoundaryError
        path=Path(self.manifest['sources']['works']['path']);marker=Path(str(path)+':Zone.Identifier');raw=b'[ZoneTransfer]\r\nZoneId=3\r\n'
        marker.write_bytes(raw);before=path.read_bytes();result=self.build()
        self.assertEqual(result['status'],'ready');self.assertEqual(path.read_bytes(),before);self.assertEqual(marker.read_bytes(),raw)
        self.assertIn({'name':':Zone.Identifier:$DATA','size':len(raw)},result['receipt']['source_streams']['works'])
        with self.assertRaises(BoundaryError):single_stream(path)
    def test_unknown_download_stream_refuses_new_build_without_changing_active_index(self):
        self.build();old=(self.index/'active.sqlite3').read_bytes()
        path=Path(self.manifest['sources']['works']['path']);marker=Path(str(path)+':Unrecognized');marker.write_bytes(b'keep unknown metadata')
        with self.assertRaisesRegex(ValueError,'Unsupported downloaded dump stream'):
            import_slice(self.manifest,['A Book','Another accepted title'],self.index)
        self.assertEqual((self.index/'active.sqlite3').read_bytes(),old);self.assertEqual(marker.read_bytes(),b'keep unknown metadata')
    def test_one_matched_stub_holds_whole_title_while_independent_title_activates(self):
        stub={'key':'/works/OL2W','type':{'key':'/type/work'},'title':'A Book'}
        other=copy.deepcopy(self.work);other.update(key='/works/OL3W',title='Other Book')
        self.replace_dump('works',[self.work,stub,other])
        result=import_slice(self.manifest,['A Book','Other Book'],self.index)
        self.assertEqual(result['status'],'ready');self.assertEqual(lookup(self.index,'A Book')['status'],'identity_incomplete')
        self.assertEqual(lookup(self.index,'A Book')['detail']['authors_count'],0)
        self.assertEqual(lookup(self.index,'Other Book')['works'][0]['id'],'/works/OL3W')
        self.assertIn('book',result['receipt']['held_titles']);self.assertNotEqual(result['receipt']['coverage_sha256'],result['receipt']['eligible_coverage_sha256'])
    def test_unresolved_or_unusable_author_holds_its_title_without_blocking_other_author(self):
        for failure in ('missing','name','aliases','bad_then_valid'):
            with self.subTest(failure=failure):
                other=copy.deepcopy(self.work);other.update(key='/works/OL3W',title='Other Book',authors=[{'author':{'key':'/authors/OL3A'}}])
                person={'key':'/authors/OL3A','type':{'key':'/type/author'},'name':'Other Writer'}
                bad=copy.deepcopy(self.person)
                if failure=='name':bad['name']=None
                elif failure in ('aliases','bad_then_valid'):bad['alternate_names']=42
                self.replace_dump('works',[self.work,other]);self.replace_dump('authors',[person] if failure=='missing' else [bad,person]+([self.person] if failure=='bad_then_valid' else []))
                directory=self.root/(failure+'-index');result=import_slice(self.manifest,['A Book','Other Book'],directory)
                self.assertEqual(result['status'],'ready');self.assertEqual(lookup(directory,'A Book')['status'],'identity_incomplete')
                self.assertEqual(lookup(directory,'Other Book')['works'][0]['authors'][0]['names'],['Other Writer'])
    def test_qualified_author_hold_can_become_covered_only_in_new_authenticated_generation(self):
        from openlibrary_index import generation
        bad=copy.deepcopy(self.work);bad['authors'][0]['role']='editor';self.replace_dump('works',[bad]);self.build();old=generation(self.index)
        self.assertEqual(lookup(self.index,'A Book')['status'],'identity_incomplete')
        self.replace_dump('works',[self.work]);self.build();self.assertNotEqual(generation(self.index),old)
        self.assertEqual(lookup(self.index,'A Book')['status'],'covered')

if __name__=='__main__':unittest.main()

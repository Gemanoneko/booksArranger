import json, os
from pathlib import Path
import unittest
import test_inventory
from scanner import Inventory, connect

REVIEW={'title':'Book','author':'Writer Jane','canonical_author':'Jane Writer','narrator':'Reader Person',
 'original_language':'Other','series':'','number':'','genre':'','topic':'','multi_author':False,'anthology':False}

class GroupFilterTests(unittest.TestCase):
    setUp=test_inventory.InventoryTests.setUp
    file=test_inventory.InventoryTests.file
    run_scan=test_inventory.InventoryTests.run_scan

    def catalog(self,relative,tags=None,error='',kind='audiobook',modified=1700000000000000101):
        path=str(self.base/relative)
        metadata={'title':(tags or {}).get('album','Book'),'author':(tags or {}).get('artist','Reader Person'),
          'artist':(tags or {}).get('artist','Reader Person'),'tags':tags or {},'notes':[],
          'probe':{'format':{'duration':'2.5'}},'method':'fixture'}
        with connect(self.database) as connection:
            connection.execute('INSERT INTO files(root,path,size,modified,seen,kind,arrival,metadata,error) VALUES(?,?,?,?,?,?,?,?,?)',
              (self.roots['Audiobooks'],path,10,modified,1,kind,0,json.dumps(metadata),error))
        return path

    def test_numeric_track_zero_introduction_and_repeated_titles_preserved(self):
        inventory=Inventory(self.database,self.roots,self.reader)
        for number in [10,2,1,0]:self.catalog(f'audio/Book/{number}.mp3',{'album':'Book','track':str(number),'title':'Repeated title'})
        row=inventory.candidates('Audiobooks')['rows'][0]
        self.assertEqual([member['track'] for member in row['members']],[0,1,2,10])
        self.assertEqual(len(row['members']),4)
        self.assertTrue(all(member['modified']=='1700000000000000101' for member in row['members']))
        self.assertFalse(row['metadata_approved'])
        self.assertIsNone(row['review'])
        self.assertTrue(row['completeness_unverified'])

    def test_disc_siblings_require_matching_album(self):
        inventory=Inventory(self.database,self.roots,self.reader)
        self.catalog('audio/Book/Disc 2/1.mp3',{'album':'Book','track':'1'})
        self.catalog('audio/Book/Disc 1/1.mp3',{'album':'Book','track':'1'})
        rows=inventory.candidates('Audiobooks')['rows']
        self.assertEqual(len(rows),1)
        self.assertEqual([m['disc'] for m in rows[0]['members']],[1,2])
        self.catalog('audio/Book/Disc 3/1.mp3',{'album':'Other Book','track':'1'})
        self.assertEqual(inventory.candidates('Audiobooks')['total'],2)

    def test_mixed_works_or_recordings_split_before_any_approval(self):
        inventory=Inventory(self.database,self.roots,self.reader)
        self.catalog('audio/Mixed/1.mp3',{'album':'One','artist':'Reader One'})
        self.catalog('audio/Mixed/2.mp3',{'album':'Two','artist':'Reader Two'})
        rows=inventory.candidates('Audiobooks')['rows']
        self.assertEqual(len(rows),2)
        self.assertEqual(sorted(len(row['members']) for row in rows),[1,1])
        self.assertTrue(all(not row['metadata_approved'] for row in rows))

    def test_order_only_ambiguity_is_separate_from_metadata_approval(self):
        inventory=Inventory(self.database,self.roots,self.reader)
        # Names without a numbering (0.22.1, item 9: a clean 01, 02 file-name sequence would decide the order).
        self.catalog('audio/Book/Part A.mp3',{'album':'Book','track':'2','artist':'Reader Person'})
        self.catalog('audio/Book/Part B.mp3',{'album':'Book','track':'2','artist':'Reader Person'})
        row=inventory.candidates('Audiobooks')['rows'][0]
        saved=inventory.save_candidate('Audiobooks',row['id'],row['revision'],REVIEW,True)
        self.assertTrue(saved['metadata_approved'])
        self.assertEqual(saved['status'],'Metadata approved; tracks need review')
        self.assertTrue(any(m['order_conflict'] for m in saved['members']))
        self.assertEqual(saved['tag_preview']['ARTIST'],'Jane Writer')
        self.assertNotEqual(saved['tag_preview']['ARTIST'],'Reader Person')

    def test_candidate_changes_invalidate_approval_and_stale_revision(self):
        inventory=Inventory(self.database,self.roots,self.reader)
        self.catalog('audio/Book/1.mp3',{'album':'Book','track':'1'})
        row=inventory.candidates('Audiobooks')['rows'][0]
        saved=inventory.save_candidate('Audiobooks',row['id'],row['revision'],REVIEW,True)
        reopened=Inventory(self.database,self.roots,self.reader)
        self.assertTrue(reopened.candidates('Audiobooks')['rows'][0]['metadata_approved'])
        self.catalog('audio/Book/2.mp3',{'album':'Book','track':'2'})
        changed=reopened.candidates('Audiobooks')['rows'][0]
        self.assertEqual(changed['id'],saved['id'])
        self.assertFalse(changed['metadata_approved'])
        self.assertGreater(changed['revision'],saved['revision'])
        with self.assertRaisesRegex(ValueError,'Candidate changed'):
            reopened.save_candidate('Audiobooks',saved['id'],saved['revision'],REVIEW,True)

    def test_saved_review_edits_invalidate_approval_and_revision(self):
        inventory=Inventory(self.database,self.roots,self.reader)
        self.catalog('audio/Book/1.mp3',{'album':'Book'})
        row=inventory.candidates('Audiobooks')['rows'][0]
        approved=inventory.save_candidate('Audiobooks',row['id'],row['revision'],REVIEW,True)
        changed=inventory.save_candidate('Audiobooks',row['id'],approved['revision'],REVIEW|{'title':'Another title'},False)
        self.assertFalse(changed['metadata_approved'])
        self.assertGreater(changed['revision'],approved['revision'])

    def test_single_m4b_companion_preservation_and_non_audio_exclusion(self):
        inventory=Inventory(self.database,self.roots,self.reader)
        self.catalog('audio/Book/Book.m4b',{'album':'Book'})
        self.catalog('audio/Book/cover.jpg',kind='companion')
        row=inventory.candidates('Audiobooks')['rows'][0]
        self.assertEqual(len(row['members']),1)
        self.assertEqual(len(row['companions']),1)
        with self.assertRaises(ValueError):inventory.candidates('Podcasts')
        with self.assertRaises(ValueError):inventory.candidates('Ebooks')

    def test_whole_library_error_filter_before_pagination(self):
        inventory=Inventory(self.database,self.roots,self.reader)
        for i in range(130):self.catalog(f'audio/Healthy/{i:03}.mp3')
        for i in range(125):self.catalog(f'audio/Zerrors/{i:03}.mp3',error='unreadable')
        page=inventory.rows('Audiobooks',100,0,'','errors',page=True)
        self.assertEqual(page['total'],125)
        self.assertEqual(len(page['rows']),100)
        self.assertTrue(all(row['error']=='unreadable' for row in page['rows']))
        second=inventory.rows('Audiobooks',100,100,'','errors',page=True)
        self.assertEqual(len(second['rows']),25)
        self.assertEqual(inventory.status('Audiobooks')['unresolved_errors'],125)
        self.assertEqual(inventory.rows('Audiobooks',100,0,'Healthy','errors',page=True)['total'],0)

    def test_gone_files_are_not_read_errors(self):
        # Judy, MissingFiles UX 2026-10-24 (Sergei's ruling): read error = error AND not gone, for the status count, the
        # Files "Read errors" filter and the candidates "Source read errors" filter. A gone file shows "No longer found".
        import groups
        inventory=Inventory(self.database,self.roots,self.reader)
        present=self.catalog('audio/Present/bad.m4b',error='moov atom not found')
        gone_error=self.catalog('audio/Gone/old.m4b',error='moov atom not found')
        gone_clean=self.catalog('audio/Gone/clean.m4b')
        self.catalog('audio/Mixed/01.mp3',{'album':'Mixed','artist':'Writer','track':'1/2'})
        mixed_gone=self.catalog('audio/Mixed/02.mp3',{'album':'Mixed','artist':'Writer','track':'2/2'},error='moov atom not found')
        status=lambda:inventory.status('Audiobooks')['unresolved_errors']
        self.assertEqual(status(),3,'positive control: before anything is gone, all three errors count')
        with connect(self.database) as connection:
            connection.executemany('UPDATE files SET missing=1 WHERE path=?',[(gone_error,),(gone_clean,),(mixed_gone,)])
        self.assertEqual(status(),1)
        errors=inventory.rows('Audiobooks',100,0,'','errors',page=True)
        self.assertEqual(([r['path'] for r in errors['rows']],errors['total']),([present],1),'count and list agree')
        self.assertEqual((errors['rows'][0]['preview']['confidence'],errors['rows'][0]['preview']['reason']),('Read error','moov atom not found'))
        gone=inventory.rows('Audiobooks',100,0,'','missing',page=True)
        self.assertEqual(sorted(r['path'] for r in gone['rows']),sorted([gone_error,gone_clean,mixed_gone]))
        for row in gone['rows']:
            self.assertEqual((row['preview']['confidence'],row['preview']['reason']),('No longer found','Not found in the last complete scan.'))
        self.assertEqual(next(r for r in gone['rows'] if r['path']==gone_error)['error'],'moov atom not found','the old error stays in the catalog')
        # Candidates: a book whose only flagged member is gone is not listed; a present unreadable member is.
        def flagged(result):return sorted(p for row in result['rows'] for p in [m['path'] for m in row['members']] if p in (present,gone_error,mixed_gone))
        self.assertEqual(flagged(inventory.candidates('Audiobooks',100,0,'','errors')),[present])
        with connect(self.database) as connection:
            self.assertEqual(flagged(groups.page_sources(connection,[self.roots['Audiobooks']],100,0,'','errors')),[present],'the multi-source page agrees')
            connection.execute('UPDATE files SET missing=0 WHERE path=?',(mixed_gone,))
        self.assertEqual(status(),2,'a file back and still unreadable counts again')
        self.assertEqual(flagged(inventory.candidates('Audiobooks',100,0,'','errors')),sorted([present,mixed_gone]))

    def test_reuse_new_changed_error_retry_and_failure_scope(self):
        good=self.file('audio/Book/good.mp3')
        bad=self.file('audio/Book/bad.mp3')
        failed=True;calls=[]
        def reader(path,kind,stop):
            calls.append(path)
            if path==str(bad) and failed:raise ValueError('Reader error')
            return {'title':'Book','tags':{'album':'Book'}}
        inventory=Inventory(self.database,self.roots,reader)
        self.run_scan(inventory)
        self.assertEqual(inventory.status('Audiobooks')['errors'],1)
        self.assertEqual(inventory.status('Audiobooks')['unresolved_errors'],1)
        calls.clear();failed=False
        self.run_scan(inventory)
        self.assertEqual(calls,[str(bad)])
        self.assertEqual(inventory.status('Audiobooks')['reused'],1)
        self.assertEqual(inventory.status('Audiobooks')['unresolved_errors'],0)
        calls.clear();good.write_bytes(b'changed bytes');new=self.file('audio/Book/new.mp3')
        self.run_scan(inventory)
        self.assertEqual(set(calls),{str(good),str(new)})

    def test_changed_during_read_captures_ns_and_counts_failed_file(self):
        path=self.file('audio/Book/1.mp3')
        def reader(source,kind,stop):
            Path(source).write_bytes(b'changed fixture source')
            return {'title':'Book','tags':{}}
        inventory=Inventory(self.database,self.roots,reader)
        self.run_scan(inventory)
        status=inventory.status('Audiobooks')
        self.assertEqual(status['checked'],1)
        self.assertEqual(status['errors'],1)
        self.assertEqual(status['unresolved_errors'],1)
        error=inventory.rows('Audiobooks')[0]['error']
        self.assertIn('before size=',error)
        self.assertIn('modified_ns=',error)
        self.assertIn('after size=',error)
        self.assertTrue(inventory.rows('Audiobooks')[0]['error_time'])

if __name__=='__main__':unittest.main()

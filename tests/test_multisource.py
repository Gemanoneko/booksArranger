"""Synthetic source-boundary fixtures; all files stay in the shared session scratch."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scanner import Inventory, connect
from source_config import load_source_config, normalize_sources

SCRATCH=Path('C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared')


class MultiSourceTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True,exist_ok=True)
        self.base=Path(tempfile.mkdtemp(prefix='multisource-',dir=SCRATCH))
        self.primary=self.base/'audio'
        self.extra=self.base/'old-audio'
        self.output=self.base/'sorted'
        self.roots={'Audiobooks':str(self.primary),'Podcasts':str(self.primary/'Podcasts'),
                    'Ebooks':str(self.base/'ebooks')}
        for root in (*self.roots.values(),str(self.extra),str(self.output)):
            Path(root).mkdir(parents=True,exist_ok=True)
        self.db=self.base/'state'/'inventory.sqlite3'
        self.calls=[]
        def reader(path,kind,stop):
            self.calls.append(path)
            return {'title':'Same book','author':'Same author','tags':{'album':'Same book','artist':'Same author'}}
        self.reader=reader

    def inventory(self,extra=True,output=None):
        return Inventory(self.db,self.roots,self.reader,
                         audiobook_sources=[str(self.primary),str(self.extra)] if extra else None,
                         output_root=str(output or self.output))

    def file(self,root,name='Author/Book/01.mp3',data=b'fixture'):
        path=Path(root)/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
        return path

    def scan(self,inv,root=None,resume=False):
        if root:inv.launch_source(str(root),resume)
        else:inv.launch('Audiobooks',resume)
        inv.worker.join(20)
        self.assertFalse(inv.worker.is_alive(),'Synthetic scan exceeded its deadline')
        self.assertEqual(inv.last_error,'')

    def test_legacy_id_revision_and_review_survive_additive_configuration(self):
        self.file(self.primary)
        old=self.inventory(extra=False)
        self.scan(old)
        before=old.candidates('Audiobooks')['rows'][0]
        old.save_candidate('Audiobooks',before['id'],before['revision'],{'title':'Manual title','author':'Manual author'})
        before=old.candidate('Audiobooks',before['id'])
        self.file(self.extra,data=b'different bytes')
        added=self.inventory()
        self.scan(added,root=self.extra)
        after=added.candidate('Audiobooks',before['id'])
        for key in ('id','revision','fingerprint','review'):
            self.assertEqual(after[key],before[key])
        self.assertEqual(after['source_root'],str(self.primary))
        self.assertEqual(added.candidates('Audiobooks')['total'],2)

    def test_identical_names_and_metadata_never_cross_group_sources(self):
        a=self.file(self.primary,data=b'a')
        b=self.file(self.extra,data=b'bbbb')
        inv=self.inventory();self.scan(inv)
        rows=inv.candidates('Audiobooks')['rows']
        self.assertEqual(len(rows),2)
        self.assertEqual(len({r['id'] for r in rows}),2)
        self.assertEqual({r['source_root'] for r in rows},{str(self.primary),str(self.extra)})
        self.assertEqual({tuple(m['path'] for m in r['members']) for r in rows},{(str(a),),(str(b),)})
        for row in rows:
            self.assertEqual(inv.source_root_for_candidate(row['id']),row['source_root'])
            self.assertEqual(inv.source_root_for_path(row['members'][0]['path']),row['source_root'])

    def test_global_pagination_ids_and_file_rows_share_sources(self):
        self.file(self.primary);self.file(self.extra)
        inv=self.inventory();self.scan(inv)
        first=inv.candidates('Audiobooks',limit=1)
        last=inv.candidates('Audiobooks',limit=1,offset=1)
        self.assertEqual(first['total'],last['total'])
        self.assertEqual(first['total'],2)
        self.assertNotEqual(first['rows'][0]['id'],last['rows'][0]['id'])
        chosen=inv.candidates('Audiobooks',ids={last['rows'][0]['id']})
        self.assertEqual([r['id'] for r in chosen['rows']],[last['rows'][0]['id']])
        files=inv.rows('Audiobooks',page=True)
        self.assertEqual(files['total'],2)
        self.assertEqual(len({r['source_root'] for r in files['rows']}),2)

    def test_offline_source_preserves_catalog_group_id_review_and_missing_flag(self):
        self.file(self.primary);self.file(self.extra)
        inv=self.inventory();self.scan(inv)
        before={r['id']:(r['revision'],r['fingerprint']) for r in inv.candidates('Audiobooks')['rows']}
        real_isdir=os.path.isdir
        with patch('scanner.os.path.isdir',side_effect=lambda p:False if str(p)==str(self.extra) else real_isdir(p)):
            self.scan(inv)
        self.assertEqual(inv.source_status(str(self.extra))['state'],'offline')
        self.assertEqual(inv.status('Audiobooks')['state'],'offline')
        self.assertEqual(before,{r['id']:(r['revision'],r['fingerprint']) for r in inv.candidates('Audiobooks')['rows']})
        with connect(self.db) as db:
            self.assertEqual(db.execute('SELECT sum(missing) FROM files WHERE root=?',(str(self.extra),)).fetchone()[0],0)
        self.scan(inv,resume=True)
        self.assertEqual(inv.status('Audiobooks')['state'],'completed')

    def test_failed_enumeration_does_not_mark_saved_rows_missing(self):
        self.file(self.extra)
        inv=self.inventory();self.scan(inv)
        real_scandir=os.scandir
        with patch('scanner.os.scandir',side_effect=lambda p:(_ for _ in ()).throw(PermissionError('fixture unavailable')) if str(p)==str(self.extra) else real_scandir(p)):
            self.scan(inv)
        self.assertEqual(inv.source_status(str(self.extra))['state'],'completed with errors')
        self.assertEqual(inv.candidates('Audiobooks')['total'],1)
        self.assertFalse(inv.rows('Audiobooks')[0]['missing'])

    def test_output_and_podcast_trees_are_excluded_from_each_source(self):
        nested=self.extra/'Sorted'
        self.file(self.primary);self.file(self.extra)
        self.file(nested,'Do not scan.mp3')
        self.file(self.roots['Podcasts'],'Do not scan.mp3')
        inv=self.inventory(output=nested);self.scan(inv)
        self.assertEqual(inv.candidates('Audiobooks')['total'],2)
        self.assertEqual(len(self.calls),2)
        for path in (nested/'Do not scan.mp3',Path(self.roots['Podcasts'])/'Do not scan.mp3',self.base/'escaped.mp3'):
            with self.assertRaises(ValueError):inv.source_root_for_path(path)

    def test_recorded_output_and_recovery_are_not_discovered(self):
        a=self.file(self.primary)
        output=self.file(self.extra,'published.m4b')
        recovery=self.file(self.extra,'recovery.m4b')
        inv=self.inventory()
        with connect(self.db) as db:
            db.execute('CREATE TABLE owned_artifacts(path TEXT,kind TEXT)')
            db.executemany('INSERT INTO owned_artifacts VALUES(?,?)',[(str(output),'output'),(str(recovery),'recovery')])
        self.scan(inv)
        self.assertEqual(self.calls,[str(a)])
        self.assertEqual(inv.candidates('Audiobooks')['total'],1)

    def test_relocation_copy_excluded_from_directory_and_saved_file_queue(self):
        a=self.file(self.primary)
        destination=self.file(self.extra,'future-relocation.m4b')
        inv=self.inventory()
        with connect(self.db) as db:
            db.execute('CREATE TABLE output_relocations(publication_id TEXT,planned_destination TEXT,stage TEXT)')
            db.execute('INSERT INTO output_relocations VALUES(?,?,?)',('synthetic-publication',str(destination),'copy_intent'))
        self.scan(inv)
        self.assertEqual(self.calls,[str(a)])
        with connect(self.db) as db:
            inv._file(db,'Audiobooks',str(self.extra),1,str(destination))
            self.assertIsNone(db.execute('SELECT 1 FROM files WHERE path=?',(str(destination),)).fetchone())
        self.assertEqual(destination.read_bytes(),b'fixture')

    def test_output_exclusion_preserves_historical_catalog_identity(self):
        nested=self.extra/'Sorted'
        self.file(nested)
        old=self.inventory();self.scan(old)
        before=old.candidates('Audiobooks')['rows'][0]
        new=self.inventory(output=nested);self.scan(new)
        after=new.candidate('Audiobooks',before['id'])
        self.assertEqual(after['revision'],before['revision'])
        self.assertEqual(after['fingerprint'],before['fingerprint'])
        self.assertFalse(new.rows('Audiobooks')[0]['missing'])

    def test_source_rescan_does_not_mark_other_source_missing_or_remove_its_file(self):
        a=self.file(self.primary);b=self.file(self.extra)
        inv=self.inventory();self.scan(inv)
        before=b.read_bytes()
        # Simulate one missing original by moving a synthetic fixture only.
        a.rename(a.with_suffix('.fixture-offline'))
        self.scan(inv,root=self.primary)
        with connect(self.db) as db:
            self.assertEqual(db.execute('SELECT missing FROM files WHERE root=? AND path=?',(str(self.extra),str(b))).fetchone()[0],0)
        self.assertEqual(b.read_bytes(),before)
        self.assertEqual(inv.source_status(str(self.extra))['generation'],1)

    def test_cross_source_saved_queue_and_review_are_refused(self):
        a=self.file(self.primary);b=self.file(self.extra)
        inv=self.inventory();self.scan(inv)
        with self.assertRaises(ValueError):inv.save_review(str(self.primary),str(b),{'title':'Wrong source'})
        with connect(self.db) as db:
            generation=inv.source_status(str(self.primary))['generation']
            with self.assertRaises(ValueError):inv._file(db,'Audiobooks',str(self.primary),generation,str(b))
            with self.assertRaises(ValueError):inv._directory(db,'Audiobooks',str(self.primary),generation,str(b.parent))
        self.assertEqual(a.read_bytes(),b'fixture')
        self.assertEqual(b.read_bytes(),b'fixture')

    def test_ids_and_search_are_intersection_and_only_page_is_rendered(self):
        self.file(self.primary);self.file(self.extra)
        inv=self.inventory();self.scan(inv)
        rows=inv.candidates('Audiobooks')['rows']
        self.assertEqual(inv.candidates('Audiobooks',ids={rows[0]['id']},search='not-a-real-title')['total'],0)
        import groups
        original=groups.render
        with patch('groups.render',wraps=original) as render:
            page=inv.candidates('Audiobooks',limit=1)
        self.assertEqual(page['total'],2)
        self.assertEqual(render.call_count,1)

    def test_additive_settings_round_trip_and_original_source_required(self):
        fields=normalize_sources(self.roots,[str(self.primary),str(self.extra)],str(self.output)).to_fields()
        self.assertEqual(load_source_config(json.loads(json.dumps(fields)),self.roots).to_fields(),fields)
        with self.assertRaises(ValueError):normalize_sources(self.roots,[str(self.extra),str(self.primary)])

    def test_overlaps_aliases_relative_and_output_containing_source_refused(self):
        invalid=([str(self.primary),str(self.primary/'Nested')],
                 [str(self.primary),str(self.primary/'..'/'audio')],
                 [str(self.primary),'relative'],
                 [str(self.primary),str(self.roots['Ebooks'])])
        for sources in invalid:
            with self.subTest(sources=sources),self.assertRaises(ValueError):normalize_sources(self.roots,sources)
        with self.assertRaises(ValueError):normalize_sources(self.roots,output_root=str(self.base))
        with self.assertRaises(ValueError):Inventory(self.extra/'catalog.sqlite',self.roots,self.reader,audiobook_sources=[str(self.primary),str(self.extra)])


if __name__=='__main__':unittest.main()

"""Typed installer bridge to reviewed old-copy retirement, never recursive cleanup.

The grouped target is the exact already-fenced app-data scopes of one explicit
relocation generation. Selecting one group authorizes all displayed scopes; it
never grants ownership of the shared original root or its other projects.
"""
import os
import contextlib
import sqlite3
from pathlib import Path

from storage_relocation import RelocationRefused,_inside,parse_manifest
from storage_relocation_operator import digest,packed,pinned_receipt
from storage_source_finalization import plan_source_finalization,apply_source_finalization,verify_source_finalization


def _need(value,message):
    if not value:raise RelocationRefused(message)


def _protected(scopes,protected_paths):
    # Operator has already retained ordinary physical ancestry/native identities
    # of these exact scopes. Never infer old ownership from a lexical C prefix.
    for protected in protected_paths:
        physical=os.path.realpath(os.path.abspath(protected))
        _need(not any(_inside(physical,scope) or _inside(scope,physical) for scope in scopes),
              'Selected retained source overlaps a protected current location: '+physical)


def review_source_retirement(manifest_path,manifest_sha256,*,protected_paths=()):
    path=Path(manifest_path).absolute()
    # Pin the explicitly selected descriptor before consulting any sidecar; the
    # operator validates native roots, target owner/generation and source fence.
    with pinned_receipt(path,manifest_sha256):
        descriptor=parse_manifest(path.read_bytes(),manifest_sha256)
        catalogs=[r for r in descriptor.files.values() if 'catalog-storage' in r.receipt_classes]
        _need(len(catalogs)==1,'Selected relocation must bind one exact target catalog')
        database=Path(descriptor.target_root)/catalogs[0].relative
        with contextlib.closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA temp_store=MEMORY')
            table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='storage_relocation_source_finalization'").fetchone()
            registrations=db.execute('SELECT * FROM storage_relocation_source_finalization').fetchall() if table else []
        _need(len(registrations)<=1,'Multiple retained-source cleanup registrations are not supported')
        previous=registrations[0] if registrations else None
        if previous:
            _need(previous[:2]==(descriptor.catalog_id,descriptor.generation),'Retained-source cleanup belongs to another generation')
            with verify_source_finalization(previous[4],previous[5],database=database) as lease:
                record=dict(lease.receipt)
                if previous[6]=='retired':
                    scopes=[str(Path(record['source_original'])/relative) for relative in record['scopes']]
                    return {'path':scopes[0],'group_id':'retained-source:'+descriptor.generation,
                        'resolved_path':scopes[0],'scope_paths':scopes,'bytes':0,'role':'retained-source',
                        'state':'already_removed','can_remove':False,'review':None,'review_sha256':None,
                        'warning_code':None,'receipt_path':previous[4],'receipt_sha256':previous[5]}
                plan=record
        else:plan=plan_source_finalization(path,manifest_sha256)
    scopes=[str(Path(plan['source_original'])/relative) for relative in plan['scopes']]
    _need(scopes and len(scopes)<=32,'Retained source review has no bounded application data scopes')
    _protected(scopes,protected_paths)
    review={'schema':'books-lifecycle-source-retirement-v1','manifest_path':str(path),
        'manifest_sha256':manifest_sha256,'source_plan':plan,'source_plan_sha256':digest(packed(plan)),
        'scope_paths':scopes,'group_id':'retained-source:'+plan['generation']}
    return {'path':scopes[0],'group_id':review['group_id'],'resolved_path':scopes[0],
        'scope_paths':scopes,'bytes':plan['bytes'],'role':'retained-source',
        'state':'available','can_remove':True,
        'review':review,'review_sha256':digest(packed(review)),
        'warning_code':'permanently_delete_retained_source_forfeit_rollback'}


def execute_source_retirement(review,review_sha256,*,selected_roots,forfeit_rollback=False,protected_paths=()):
    _need(isinstance(review,dict) and digest(packed(review))==review_sha256 and
        set(review)=={'schema','manifest_path','manifest_sha256','source_plan','source_plan_sha256','scope_paths','group_id'} and
        review['schema']=='books-lifecycle-source-retirement-v1','Retained source review changed')
    plan=review['source_plan']
    _need(digest(packed(plan))==review['source_plan_sha256'] and
        review['group_id']=='retained-source:'+plan['generation'] and
        review['scope_paths']==[str(Path(plan['source_original'])/scope) for scope in plan['scopes']],
        'Retained source scopes differ from the reviewed generation')
    selected=list(selected_roots)
    # A grouped entry cannot be used to guess or partially authorize siblings.
    _need(selected==[review['group_id']] or sorted(map(os.path.normcase,selected))==
        sorted(map(os.path.normcase,review['scope_paths'])),
        'Select the complete explicitly reviewed retained-source group')
    _need(forfeit_rollback is True,'Retained-source deletion requires explicit forfeiture of rollback')
    _protected(review['scope_paths'],protected_paths)
    # Fresh operator preflight holds source and actual target owners again.
    # It compares the reviewed plan SHA before any destructive member action.
    result=apply_source_finalization(review['manifest_path'],review['manifest_sha256'],
        review['source_plan_sha256'],forfeit_rollback=True)
    _need(result['complete'] is True and not result['folder_holds'],
        'Selected retained-source cleanup is incomplete; retain its exact result for review')
    return dict(result,scope_paths=review['scope_paths'],group_id=review['group_id'])

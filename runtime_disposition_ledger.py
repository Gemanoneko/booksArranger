"""Finite closed-ledger membership for migration and data cleanup.

An outstanding intent is never translated into permission to restore a copied
file's ACL. All records stay immutable; only independently closed histories
can enter a new storage generation.
"""
from pathlib import Path
import re


def closed_ledger_members(root):
    from runtime_file_disposition import _load,SCHEMA
    from storage_relocation_operator import need,packed,digest,Security
    root=Path(root)
    if not root.exists():return []
    files=list(root.iterdir())
    need(all(p.is_file() and not p.is_symlink() for p in files),'Runtime ledger has an unknown directory/member')
    byname={p.name:p for p in files}
    need('context.json' in byname,'Runtime ledger has no native owner marker')
    marker,marker_sha=_load(byname['context.json'])
    need(marker.get('schema')==SCHEMA and marker.get('phase')=='context' and marker.get('owner_kind') in ('catalog','support'),
         'Runtime ledger owner marker is unsupported')
    operations={}
    result=[]
    for path in files:
        record,sha=_load(path)
        if path.name!='context.json':
            match=re.fullmatch('([a-f0-9]{32})\\.(intent|fenced|pending|closed|held|retained)\\.json',path.name)
            need(match is not None,'Runtime ledger filename is not a finite owned record')
            operation,phase=match.groups()
            need(record.get('schema')==SCHEMA and record.get('operation_id')==operation and record.get('phase')==phase,
                 'Runtime ledger record identity/schema differs')
            operations.setdefault(operation,{})[phase]=(record,sha)
        result.append(dict(path=str(path),sha256=sha,size=path.stat().st_size))
    for phases in operations.values():
        need('intent' in phases and ('closed' in phases or 'retained' in phases),
             'Outstanding runtime disposition prevents storage relocation/cleanup')
        intent,sha=phases['intent']
        need(intent.get('context_sha256')==marker_sha and
             intent.get('facts',{}).get('links')==1 and isinstance(intent.get('path'),str),
             'Runtime ledger intent lacks its exact native owner/content binding')
        Security().validate_capture(intent.get('original_security'))
        for phase,(record,_) in phases.items():
            if phase=='intent':continue
            need(record.get('intent_sha256')==sha,'Runtime ledger record changed its intent')
            if phase in ('closed','pending','retained'):
                need(record.get('facts')==intent['facts'] and record.get('sha256')==intent['sha256'],
                     'Runtime ledger exact content proof differs')
        if 'retained' in phases:
            retained,_=phases['retained']
            need('closed' not in phases and 'pending' not in phases and
                 not phases.get('held',({},None))[0].get('restore_forbidden') and
                 retained.get('original_security_sha256')==digest(packed(intent['original_security'])) and
                 retained.get('observed_remaining') is True and retained.get('original_acl_verified') is True,
                 'Retained recovery cannot reinterpret native-success/unknown disposition')
            continue
        closed,_=phases['closed'];actual=closed.get('closed_native_facts',{})
        need(closed.get('native_close') is True and closed.get('observed_absent') is True and
             actual.get('links') in (0,1) and dict(actual,links=1)==intent['facts'],
             'Runtime ledger has no positive exact native close proof')
    return result
